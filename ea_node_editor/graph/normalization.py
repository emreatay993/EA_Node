from __future__ import annotations

from dataclasses import dataclass

from ea_node_editor.graph.effective_ports import (
    EffectivePort,
    are_port_kinds_compatible,
    effective_ports,
    find_port,
    ports_compatible,
    target_port_has_capacity,
)
from ea_node_editor.graph.model import (
    EdgeInstance,
    GraphModel,
    NodeInstance,
    ProjectData,
    WorkspaceData,
    edge_instance_to_mapping,
    node_instance_to_mapping,
)
from ea_node_editor.graph.subnode_contract import (
    SUBNODE_PIN_KIND_PROPERTY,
    is_subnode_pin_type,
)
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import NodeTypeSpec


@dataclass(slots=True, frozen=True)
class RegistryNodeResolution:
    node: NodeInstance
    spec: NodeTypeSpec


@dataclass(slots=True)
class ValidatedGraphMutation:
    model: GraphModel
    workspace_id: str
    registry: NodeRegistry

    @property
    def workspace(self) -> WorkspaceData:
        return self.model.project.workspaces[self.workspace_id]

    def add_node(
        self,
        *,
        type_id: str,
        title: str,
        x: float,
        y: float,
        properties: dict[str, object] | None = None,
        exposed_ports: dict[str, bool] | None = None,
        visual_style: dict[str, object] | None = None,
        parent_node_id: str | None = None,
    ) -> NodeInstance:
        spec = self.registry.get_spec(type_id)
        normalized_title = str(title or spec.display_name).strip() or spec.display_name
        normalized_properties = self.registry.normalize_properties(
            type_id,
            dict(properties or {}),
            include_defaults=True,
        )
        requested_exposed_ports = {
            str(key): bool(value)
            for key, value in dict(exposed_ports or {}).items()
            if str(key).strip()
        }
        node = self.model.add_node(
            self.workspace_id,
            type_id=type_id,
            title=normalized_title,
            x=float(x),
            y=float(y),
            properties=normalized_properties,
            exposed_ports=requested_exposed_ports,
            visual_style=dict(visual_style or {}),
        )
        node.parent_node_id = self._validated_parent_node_id(node.node_id, parent_node_id)
        node.exposed_ports = self._normalized_exposed_ports(node.node_id)
        return node

    def set_node_parent(self, node_id: str, parent_node_id: str | None) -> bool:
        node = self.workspace.nodes[node_id]
        normalized_parent_id = self._validated_parent_node_id(node_id, parent_node_id)
        current_parent_id = str(node.parent_node_id or "").strip() or None
        if current_parent_id == normalized_parent_id:
            return False
        affected_node_ids = {node_id}
        if current_parent_id:
            affected_node_ids.add(current_parent_id)
        if normalized_parent_id:
            affected_node_ids.add(normalized_parent_id)
        node.parent_node_id = normalized_parent_id
        self.workspace.dirty = True
        self._prune_edges_for_nodes(affected_node_ids)
        return True

    def add_edge(
        self,
        *,
        source_node_id: str,
        source_port_key: str,
        target_node_id: str,
        target_port_key: str,
        label: str = "",
        visual_style: dict[str, object] | None = None,
    ) -> EdgeInstance:
        workspace = self.workspace
        if source_node_id not in workspace.nodes:
            raise KeyError(f"Unknown source node: {source_node_id}")
        if target_node_id not in workspace.nodes:
            raise KeyError(f"Unknown target node: {target_node_id}")
        for existing in workspace.edges.values():
            if (
                existing.source_node_id == source_node_id
                and existing.source_port_key == source_port_key
                and existing.target_node_id == target_node_id
                and existing.target_port_key == target_port_key
            ):
                return existing
        source_node, source_spec, source_port = self._resolved_port(source_node_id, source_port_key)
        target_node, target_spec, target_port = self._resolved_port(target_node_id, target_port_key)
        if source_port.direction != "out":
            raise ValueError(f"Source port must be an output: {source_node_id}.{source_port_key}")
        if target_port.direction != "in":
            raise ValueError(f"Target port must be an input: {target_node_id}.{target_port_key}")
        if not are_port_kinds_compatible(source_port.kind, target_port.kind):
            raise ValueError(
                "Incompatible ports: "
                f"{source_node_id}.{source_port_key} -> {target_node_id}.{target_port_key}"
            )
        if not source_port.exposed:
            raise ValueError(f"Source port is hidden: {source_node_id}.{source_port_key}")
        if not target_port.exposed:
            raise ValueError(f"Target port is hidden: {target_node_id}.{target_port_key}")
        if not target_port_has_capacity(
            edges=workspace.edges.values(),
            node=target_node,
            spec=target_spec,
            workspace_nodes=workspace.nodes,
            port_key=target_port_key,
        ):
            raise ValueError(f"Target input port already has a connection: {target_node_id}.{target_port_key}")
        return self.model.add_edge(
            self.workspace_id,
            source_node_id=source_node_id,
            source_port_key=source_port_key,
            target_node_id=target_node_id,
            target_port_key=target_port_key,
            label=label,
            visual_style=dict(visual_style or {}),
        )

    def ports_compatible(
        self,
        *,
        source_node_id: str,
        source_port_key: str,
        target_node_id: str,
        target_port_key: str,
    ) -> bool:
        try:
            _source_node, _source_spec, source_port = self._resolved_port(source_node_id, source_port_key)
            _target_node, _target_spec, target_port = self._resolved_port(target_node_id, target_port_key)
        except (KeyError, ValueError):
            return False
        return ports_compatible(source_port, target_port)

    def set_node_property(self, node_id: str, key: str, value: object) -> object:
        node = self.workspace.nodes[node_id]
        normalized = self.registry.normalize_property_value(node.type_id, key, value)
        if key in node.properties and node.properties[key] == normalized:
            return normalized
        self.model.set_node_property(self.workspace_id, node_id, key, normalized)
        if self._property_change_affects_ports(node, key):
            self._prune_edges_for_nodes(self._affected_node_ids_for_port_semantics(node))
        return normalized

    def set_node_properties(self, node_id: str, values: dict[str, object]) -> dict[str, object]:
        node = self.workspace.nodes[node_id]
        normalized_updates: dict[str, object] = {}
        for raw_key, raw_value in dict(values or {}).items():
            key = str(raw_key or "")
            if not key:
                continue
            try:
                normalized = self.registry.normalize_property_value(node.type_id, key, raw_value)
            except KeyError:
                continue
            if key in node.properties and node.properties[key] == normalized:
                continue
            normalized_updates[key] = normalized
        if not normalized_updates:
            return {}
        for key, normalized in normalized_updates.items():
            self.model.set_node_property(self.workspace_id, node_id, key, normalized)
        if any(self._property_change_affects_ports(node, key) for key in normalized_updates):
            self._prune_edges_for_nodes(self._affected_node_ids_for_port_semantics(node))
        return normalized_updates

    def set_exposed_port(self, node_id: str, key: str, exposed: bool) -> bool:
        node, _spec, _port = self._resolved_port(node_id, key)
        normalized_exposed = bool(exposed)
        if key in node.exposed_ports and bool(node.exposed_ports[key]) == normalized_exposed:
            return False
        self.model.set_exposed_port(self.workspace_id, node_id, key, normalized_exposed)
        if not normalized_exposed:
            self._prune_edges_for_nodes({node_id})
        return True

    def remove_edge(self, edge_id: str) -> None:
        self.model.remove_edge(self.workspace_id, edge_id)

    def remove_node(self, node_id: str) -> None:
        self.model.remove_node(self.workspace_id, node_id)

    def set_node_collapsed(self, node_id: str, collapsed: bool) -> None:
        self.model.set_node_collapsed(self.workspace_id, node_id, collapsed)

    def set_node_position(self, node_id: str, x: float, y: float) -> None:
        self.model.set_node_position(self.workspace_id, node_id, x, y)

    def set_node_geometry(
        self,
        node_id: str,
        x: float,
        y: float,
        width: float | None,
        height: float | None,
    ) -> None:
        self.model.set_node_geometry(self.workspace_id, node_id, x, y, width, height)

    def set_node_title(self, node_id: str, title: str) -> None:
        self.model.set_node_title(self.workspace_id, node_id, title)

    def set_node_visual_style(self, node_id: str, visual_style: dict[str, object] | None) -> None:
        self.model.set_node_visual_style(self.workspace_id, node_id, None if visual_style is None else dict(visual_style))

    def set_edge_label(self, edge_id: str, label: str) -> None:
        self.model.set_edge_label(self.workspace_id, edge_id, label)

    def set_edge_visual_style(self, edge_id: str, visual_style: dict[str, object] | None) -> None:
        self.model.set_edge_visual_style(self.workspace_id, edge_id, None if visual_style is None else dict(visual_style))

    def _resolved_port(self, node_id: str, port_key: str) -> tuple[NodeInstance, NodeTypeSpec, EffectivePort]:
        workspace = self.workspace
        node = workspace.nodes[node_id]
        spec = self.registry.get_spec(node.type_id)
        port = find_port(
            node=node,
            spec=spec,
            workspace_nodes=workspace.nodes,
            port_key=port_key,
        )
        if port is None:
            raise KeyError(f"Port {port_key} not found on node type {spec.type_id}")
        return node, spec, port

    def _normalized_exposed_ports(self, node_id: str) -> dict[str, bool]:
        resolved_nodes = resolve_registry_nodes(self.workspace.nodes, self.registry)
        resolution = resolved_nodes[node_id]
        return normalized_exposed_ports(
            resolution,
            workspace_nodes=self.workspace.nodes,
        )

    def _validated_parent_node_id(self, node_id: str, parent_node_id: str | None) -> str | None:
        normalized_parent_id = str(parent_node_id or "").strip() or None
        if normalized_parent_id is None:
            return None
        if normalized_parent_id == node_id:
            raise ValueError("Node cannot parent itself.")
        if normalized_parent_id not in self.workspace.nodes:
            raise KeyError(f"Unknown parent node: {normalized_parent_id}")
        return normalized_parent_id

    @staticmethod
    def _property_change_affects_ports(node: NodeInstance, key: str) -> bool:
        if not is_subnode_pin_type(node.type_id):
            return False
        return key == SUBNODE_PIN_KIND_PROPERTY

    @staticmethod
    def _affected_node_ids_for_port_semantics(node: NodeInstance) -> set[str]:
        affected = {node.node_id}
        parent_node_id = str(node.parent_node_id or "").strip()
        if parent_node_id:
            affected.add(parent_node_id)
        return affected

    def _prune_edges_for_nodes(self, affected_node_ids: set[str]) -> list[str]:
        if not affected_node_ids:
            return []
        workspace = self.workspace
        resolved_nodes = resolve_registry_nodes(workspace.nodes, self.registry)
        seen_connections: set[tuple[str, str, str, str]] = set()
        occupied_single_target_ports: set[tuple[str, str]] = set()
        affected_edges: list[tuple[str, EdgeInstance]] = []
        for edge_id, edge in list(workspace.edges.items()):
            touches_affected_node = (
                edge.source_node_id in affected_node_ids
                or edge.target_node_id in affected_node_ids
            )
            if touches_affected_node:
                affected_edges.append((edge_id, edge))
                continue
            resolution = validate_registry_edge(
                source_node_id=edge.source_node_id,
                source_port_key=edge.source_port_key,
                target_node_id=edge.target_node_id,
                target_port_key=edge.target_port_key,
                resolved_nodes=resolved_nodes,
                require_source_output=True,
                require_target_input=True,
                require_exposed_ports=True,
                require_compatible_ports=True,
            )
            if resolution is None:
                continue
            accept_registry_edge(
                resolution,
                seen_connections=seen_connections,
                occupied_single_target_ports=occupied_single_target_ports,
            )

        removed_edge_ids: list[str] = []
        for edge_id, edge in affected_edges:
            resolution = validate_registry_edge(
                source_node_id=edge.source_node_id,
                source_port_key=edge.source_port_key,
                target_node_id=edge.target_node_id,
                target_port_key=edge.target_port_key,
                resolved_nodes=resolved_nodes,
                require_source_output=True,
                require_target_input=True,
                require_exposed_ports=True,
                require_compatible_ports=True,
            )
            if resolution is None or not accept_registry_edge(
                resolution,
                seen_connections=seen_connections,
                occupied_single_target_ports=occupied_single_target_ports,
            ):
                workspace.edges.pop(edge_id, None)
                removed_edge_ids.append(edge_id)
        if removed_edge_ids:
            workspace.dirty = True
        return removed_edge_ids


@dataclass(slots=True, frozen=True)
class RegistryEdgeResolution:
    source_node_id: str
    source_port_key: str
    target_node_id: str
    target_port_key: str
    source_port: EffectivePort
    target_port: EffectivePort

    @property
    def connection_key(self) -> tuple[str, str, str, str]:
        return (
            self.source_node_id,
            self.source_port_key,
            self.target_node_id,
            self.target_port_key,
        )

    @property
    def target_input_key(self) -> tuple[str, str]:
        return (
            self.target_node_id,
            self.target_port_key,
        )


def resolve_registry_nodes(
    workspace_nodes: dict[str, NodeInstance],
    registry: NodeRegistry,
) -> dict[str, RegistryNodeResolution]:
    resolved: dict[str, RegistryNodeResolution] = {}
    for node_id, node in workspace_nodes.items():
        spec = registry.spec_or_none(node.type_id)
        if spec is None:
            continue
        resolved[node_id] = RegistryNodeResolution(node=node, spec=spec)
    return resolved


def normalized_exposed_ports(
    resolution: RegistryNodeResolution,
    *,
    workspace_nodes: dict[str, NodeInstance],
) -> dict[str, bool]:
    return {
        port.key: bool(resolution.node.exposed_ports.get(port.key, port.exposed))
        for port in effective_ports(
            node=resolution.node,
            spec=resolution.spec,
            workspace_nodes=workspace_nodes,
        )
    }


def validate_registry_edge(
    *,
    source_node_id: str,
    source_port_key: str,
    target_node_id: str,
    target_port_key: str,
    resolved_nodes: dict[str, RegistryNodeResolution],
    require_source_output: bool,
    require_target_input: bool = True,
    require_exposed_ports: bool = False,
    require_compatible_ports: bool = False,
) -> RegistryEdgeResolution | None:
    source_resolution = resolved_nodes.get(source_node_id)
    target_resolution = resolved_nodes.get(target_node_id)
    if source_resolution is None or target_resolution is None:
        return None
    workspace_nodes = {node_id: resolution.node for node_id, resolution in resolved_nodes.items()}
    source_port = find_port(
        node=source_resolution.node,
        spec=source_resolution.spec,
        workspace_nodes=workspace_nodes,
        port_key=source_port_key,
    )
    if source_port is None:
        return None
    target_port = find_port(
        node=target_resolution.node,
        spec=target_resolution.spec,
        workspace_nodes=workspace_nodes,
        port_key=target_port_key,
    )
    if target_port is None:
        return None
    if require_source_output and source_port.direction != "out":
        return None
    if require_target_input and target_port.direction != "in":
        return None
    if require_exposed_ports and (not source_port.exposed or not target_port.exposed):
        return None
    if require_compatible_ports and not are_port_kinds_compatible(source_port.kind, target_port.kind):
        return None
    return RegistryEdgeResolution(
        source_node_id=source_node_id,
        source_port_key=source_port_key,
        target_node_id=target_node_id,
        target_port_key=target_port_key,
        source_port=source_port,
        target_port=target_port,
    )


def accept_registry_edge(
    edge: RegistryEdgeResolution,
    *,
    seen_connections: set[tuple[str, str, str, str]],
    occupied_single_target_ports: set[tuple[str, str]],
) -> bool:
    if edge.connection_key in seen_connections:
        return False
    if (
        not edge.target_port.allow_multiple_connections
        and edge.target_input_key in occupied_single_target_ports
    ):
        return False
    seen_connections.add(edge.connection_key)
    if not edge.target_port.allow_multiple_connections:
        occupied_single_target_ports.add(edge.target_input_key)
    return True


def _sanitize_live_parent_links(workspace) -> None:  # noqa: ANN001
    for node in workspace.nodes.values():
        parent_id = str(node.parent_node_id or "").strip() or None
        override_parent_id = (
            str(workspace.authored_node_overrides.get(node.node_id, {}).get("parent_node_id", "")).strip()
            or None
        )
        if parent_id is None:
            if override_parent_id in workspace.unresolved_node_docs:
                continue
            workspace.authored_node_overrides.pop(node.node_id, None)
            continue
        if parent_id == node.node_id:
            node.parent_node_id = None
            workspace.authored_node_overrides.pop(node.node_id, None)
            continue
        if parent_id in workspace.nodes:
            workspace.authored_node_overrides.pop(node.node_id, None)
            continue
        if parent_id in workspace.unresolved_node_docs:
            workspace.authored_node_overrides[node.node_id] = {"parent_node_id": parent_id}
        else:
            workspace.authored_node_overrides.pop(node.node_id, None)
        node.parent_node_id = None


def normalize_project_for_registry(project: ProjectData, registry: NodeRegistry) -> None:
    """Normalize resolved content while preserving unresolved authored payloads."""
    for workspace in project.workspaces.values():
        resolved_nodes = resolve_registry_nodes(workspace.nodes, registry)
        unknown_node_ids = set(workspace.nodes) - set(resolved_nodes)
        for resolution in resolved_nodes.values():
            node = resolution.node
            node.properties = registry.normalize_properties(node.type_id, node.properties)

        for node_id in sorted(unknown_node_ids):
            node = workspace.nodes.pop(node_id, None)
            if node is None:
                continue
            workspace.unresolved_node_docs[node_id] = node_instance_to_mapping(node)

        resolved_nodes = resolve_registry_nodes(workspace.nodes, registry)
        for edge_id, edge in list(workspace.edges.items()):
            if edge.source_node_id in unknown_node_ids or edge.target_node_id in unknown_node_ids:
                workspace.unresolved_edge_docs[edge_id] = edge_instance_to_mapping(edge)
                workspace.edges.pop(edge_id, None)

        _sanitize_live_parent_links(workspace)

        for resolution in resolved_nodes.values():
            resolution.node.exposed_ports = normalized_exposed_ports(
                resolution,
                workspace_nodes=workspace.nodes,
            )

        seen_connections: set[tuple[str, str, str, str]] = set()
        occupied_single_target_ports: set[tuple[str, str]] = set()
        for edge_id, edge in list(workspace.edges.items()):
            resolution = validate_registry_edge(
                source_node_id=edge.source_node_id,
                source_port_key=edge.source_port_key,
                target_node_id=edge.target_node_id,
                target_port_key=edge.target_port_key,
                resolved_nodes=resolved_nodes,
                require_source_output=False,
                require_target_input=True,
                require_exposed_ports=False,
            )
            if resolution is None or not accept_registry_edge(
                resolution,
                seen_connections=seen_connections,
                occupied_single_target_ports=occupied_single_target_ports,
            ):
                workspace.edges.pop(edge_id, None)
