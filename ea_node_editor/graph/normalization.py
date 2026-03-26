from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ea_node_editor.graph.effective_ports import (
    EffectivePort,
    are_port_kinds_compatible,
    effective_ports,
    find_port,
    is_flow_edge_port,
    port_supports_incoming_edge,
    port_supports_outgoing_edge,
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
    sanitize_workspace_parent_links,
)
from ea_node_editor.graph.subnode_contract import (
    SUBNODE_PIN_KIND_PROPERTY,
    is_subnode_pin_type,
)
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import NodeTypeSpec

GRAPH_FRAGMENT_KIND = "ea-node-editor/graph-fragment"
GRAPH_FRAGMENT_VERSION = 1


def build_graph_fragment_payload(
    *,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "kind": GRAPH_FRAGMENT_KIND,
        "version": GRAPH_FRAGMENT_VERSION,
        "nodes": nodes,
        "edges": edges,
    }


def normalize_graph_fragment_payload(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    if payload.get("kind") != GRAPH_FRAGMENT_KIND:
        return None
    if int(payload.get("version", -1)) != GRAPH_FRAGMENT_VERSION:
        return None

    raw_nodes = payload.get("nodes")
    raw_edges = payload.get("edges")
    if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
        return None

    normalized_nodes: list[dict[str, Any]] = []
    seen_node_ids: set[str] = set()
    for raw_node in raw_nodes:
        normalized_node = _normalize_fragment_node_entry(raw_node)
        if normalized_node is None:
            return None
        ref_id = normalized_node["ref_id"]
        if ref_id in seen_node_ids:
            return None
        seen_node_ids.add(ref_id)
        normalized_nodes.append(normalized_node)
    if not normalized_nodes:
        return None

    normalized_edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str, str, str]] = set()
    for raw_edge in raw_edges:
        normalized_edge = _normalize_fragment_edge_entry(raw_edge)
        if normalized_edge is None:
            return None
        source_ref_id = normalized_edge["source_ref_id"]
        target_ref_id = normalized_edge["target_ref_id"]
        if source_ref_id not in seen_node_ids or target_ref_id not in seen_node_ids:
            return None
        edge_key = (
            source_ref_id,
            normalized_edge["source_port_key"],
            target_ref_id,
            normalized_edge["target_port_key"],
        )
        if edge_key in seen_edges:
            continue
        seen_edges.add(edge_key)
        normalized_edges.append(normalized_edge)

    return build_graph_fragment_payload(nodes=normalized_nodes, edges=normalized_edges)


def normalize_edge_label(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def normalize_visual_style_payload(value: Any) -> dict[str, Any]:
    normalized = _normalize_visual_style_value(value)
    if isinstance(normalized, dict):
        return normalized
    return {}


def _normalize_fragment_node_entry(raw_node: Any) -> dict[str, Any] | None:
    if not isinstance(raw_node, dict):
        return None

    ref_id = str(raw_node.get("ref_id", "")).strip()
    type_id = str(raw_node.get("type_id", "")).strip()
    if not ref_id or not type_id:
        return None

    try:
        x = float(raw_node.get("x", 0.0))
        y = float(raw_node.get("y", 0.0))
    except (TypeError, ValueError):
        return None
    try:
        custom_width = float(raw_node["custom_width"]) if raw_node.get("custom_width") is not None else None
        custom_height = float(raw_node["custom_height"]) if raw_node.get("custom_height") is not None else None
    except (TypeError, ValueError):
        return None

    raw_exposed_ports = raw_node.get("exposed_ports", {})
    if not isinstance(raw_exposed_ports, dict):
        return None
    normalized_exposed_ports: dict[str, bool] = {}
    for key, value in raw_exposed_ports.items():
        normalized_key = str(key).strip()
        if not normalized_key:
            return None
        normalized_exposed_ports[normalized_key] = bool(value)

    raw_properties = raw_node.get("properties", {})
    if not isinstance(raw_properties, dict):
        return None

    raw_parent = raw_node.get("parent_node_id")
    parent_node_id: str | None = None
    if raw_parent is not None:
        normalized_parent = str(raw_parent).strip()
        parent_node_id = normalized_parent or None

    return {
        "ref_id": ref_id,
        "type_id": type_id,
        "title": str(raw_node.get("title", "")),
        "x": x,
        "y": y,
        "collapsed": bool(raw_node.get("collapsed", False)),
        "properties": copy.deepcopy(raw_properties),
        "exposed_ports": normalized_exposed_ports,
        "visual_style": normalize_visual_style_payload(raw_node.get("visual_style")),
        "parent_node_id": parent_node_id,
        "custom_width": custom_width,
        "custom_height": custom_height,
    }


def _normalize_fragment_edge_entry(raw_edge: Any) -> dict[str, Any] | None:
    if not isinstance(raw_edge, dict):
        return None
    source_ref_id = str(raw_edge.get("source_ref_id", "")).strip()
    source_port_key = str(raw_edge.get("source_port_key", "")).strip()
    target_ref_id = str(raw_edge.get("target_ref_id", "")).strip()
    target_port_key = str(raw_edge.get("target_port_key", "")).strip()
    if not source_ref_id or not source_port_key or not target_ref_id or not target_port_key:
        return None
    return {
        "source_ref_id": source_ref_id,
        "source_port_key": source_port_key,
        "target_ref_id": target_ref_id,
        "target_port_key": target_port_key,
        "label": normalize_edge_label(raw_edge.get("label")),
        "visual_style": normalize_visual_style_payload(raw_edge.get("visual_style")),
    }


def _normalize_visual_style_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, child in value.items():
            normalized_key = str(key).strip()
            if not normalized_key:
                continue
            normalized[normalized_key] = _normalize_visual_style_value(child)
        return normalized
    if isinstance(value, list):
        return [_normalize_visual_style_value(item) for item in value]
    if isinstance(value, tuple):
        return [_normalize_visual_style_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return copy.deepcopy(value)
    return str(value)


@dataclass(slots=True, frozen=True)
class RegistryNodeResolution:
    node: NodeInstance
    spec: NodeTypeSpec


@dataclass(slots=True)
class GraphInvariantKernel:
    registry: NodeRegistry
    workspace_nodes: dict[str, NodeInstance]
    workspace_edges: object | None = None

    def _workspace_edge_values(self) -> tuple[EdgeInstance, ...]:
        if self.workspace_edges is None:
            return ()
        return tuple(self.workspace_edges)

    def resolve_registry_nodes(self) -> dict[str, RegistryNodeResolution]:
        resolved: dict[str, RegistryNodeResolution] = {}
        for node_id, node in self.workspace_nodes.items():
            spec = self.registry.spec_or_none(node.type_id)
            if spec is None:
                continue
            resolved[node_id] = RegistryNodeResolution(node=node, spec=spec)
        return resolved

    def normalized_exposed_ports(self, resolution: RegistryNodeResolution) -> dict[str, bool]:
        return {
            port.key: bool(resolution.node.exposed_ports.get(port.key, port.exposed))
            for port in effective_ports(
                node=resolution.node,
                spec=resolution.spec,
                workspace_nodes=self.workspace_nodes,
            )
        }

    def validate_registry_edge(
        self,
        *,
        source_node_id: str,
        source_port_key: str,
        target_node_id: str,
        target_port_key: str,
        resolved_nodes: dict[str, RegistryNodeResolution] | None = None,
        require_source_output: bool,
        require_target_input: bool = True,
        require_exposed_ports: bool = False,
        require_compatible_ports: bool = False,
    ) -> RegistryEdgeResolution | None:
        if resolved_nodes is None:
            resolved_nodes = self.resolve_registry_nodes()
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
        if require_source_output and not port_supports_outgoing_edge(source_port):
            return None
        if require_target_input and not port_supports_incoming_edge(target_port):
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

    def add_edge_or_raise(
        self,
        *,
        source_node_id: str,
        source_port_key: str,
        target_node_id: str,
        target_port_key: str,
    ) -> RegistryEdgeResolution:
        if source_node_id not in self.workspace_nodes:
            raise KeyError(f"Unknown source node: {source_node_id}")
        if target_node_id not in self.workspace_nodes:
            raise KeyError(f"Unknown target node: {target_node_id}")
        source_node, source_spec, source_port = self._resolved_port(source_node_id, source_port_key)
        target_node, target_spec, target_port = self._resolved_port(target_node_id, target_port_key)
        if source_node_id == target_node_id and is_flow_edge_port(source_port) and is_flow_edge_port(target_port):
            raise ValueError("Flow edges cannot connect ports on the same node.")
        if not port_supports_outgoing_edge(source_port):
            raise ValueError(f"Source port must support outgoing edges: {source_node_id}.{source_port_key}")
        if not port_supports_incoming_edge(target_port):
            raise ValueError(f"Target port must support incoming edges: {target_node_id}.{target_port_key}")
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
            edges=self._workspace_edge_values(),
            node=target_node,
            spec=target_spec,
            workspace_nodes=self.workspace_nodes,
            port_key=target_port_key,
        ):
            raise ValueError(f"Target input port already has a connection: {target_node_id}.{target_port_key}")
        return RegistryEdgeResolution(
            source_node_id=source_node_id,
            source_port_key=source_port_key,
            target_node_id=target_node_id,
            target_port_key=target_port_key,
            source_port=source_port,
            target_port=target_port,
        )

    @staticmethod
    def build_graph_fragment_payload(
        *,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return build_graph_fragment_payload(nodes=nodes, edges=edges)

    @staticmethod
    def normalize_graph_fragment_payload(payload: Any) -> dict[str, Any] | None:
        return normalize_graph_fragment_payload(payload)

    @staticmethod
    def normalize_edge_label(value: Any) -> str:
        return normalize_edge_label(value)

    @staticmethod
    def normalize_visual_style_payload(value: Any) -> dict[str, Any]:
        return normalize_visual_style_payload(value)

    @staticmethod
    def fragment_node_from_payload(node_payload: Mapping[str, Any]) -> NodeInstance:
        return NodeInstance(
            node_id=str(node_payload.get("ref_id", "")),
            type_id=str(node_payload.get("type_id", "")),
            title=str(node_payload.get("title", "")),
            x=float(node_payload.get("x", 0.0)),
            y=float(node_payload.get("y", 0.0)),
            collapsed=bool(node_payload.get("collapsed", False)),
            properties=dict(node_payload.get("properties", {})),
            exposed_ports=dict(node_payload.get("exposed_ports", {})),
            visual_style=copy.deepcopy(node_payload.get("visual_style", {})),
            parent_node_id=node_payload.get("parent_node_id"),
            custom_width=float(node_payload["custom_width"]) if node_payload.get("custom_width") is not None else None,
            custom_height=float(node_payload["custom_height"]) if node_payload.get("custom_height") is not None else None,
        )

    @classmethod
    def graph_fragment_payload_is_valid(
        cls,
        *,
        fragment_payload: Mapping[str, Any],
        registry: NodeRegistry,
    ) -> bool:
        raw_nodes = fragment_payload.get("nodes")
        raw_edges = fragment_payload.get("edges")
        if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
            return False

        node_specs: dict[str, NodeTypeSpec] = {}
        fragment_nodes: dict[str, NodeInstance] = {}
        for node_payload in raw_nodes:
            normalized_node = _normalize_fragment_node_entry(node_payload)
            if normalized_node is None:
                return False
            ref_id = normalized_node["ref_id"]
            type_id = normalized_node["type_id"]
            try:
                node_specs[ref_id] = registry.get_spec(type_id)
            except KeyError:
                return False
            fragment_nodes[ref_id] = cls.fragment_node_from_payload(normalized_node)

        seen_connections: set[tuple[str, str, str, str]] = set()
        occupied_single_target_ports: set[tuple[str, str]] = set()
        for edge_payload in raw_edges:
            normalized_edge = _normalize_fragment_edge_entry(edge_payload)
            if normalized_edge is None:
                return False
            source_ref_id = normalized_edge["source_ref_id"]
            target_ref_id = normalized_edge["target_ref_id"]
            source_node = fragment_nodes.get(source_ref_id)
            target_node = fragment_nodes.get(target_ref_id)
            source_spec = node_specs.get(source_ref_id)
            target_spec = node_specs.get(target_ref_id)
            if source_node is None or target_node is None or source_spec is None or target_spec is None:
                return False
            source_port = find_port(
                node=source_node,
                spec=source_spec,
                workspace_nodes=fragment_nodes,
                port_key=normalized_edge["source_port_key"],
            )
            target_port = find_port(
                node=target_node,
                spec=target_spec,
                workspace_nodes=fragment_nodes,
                port_key=normalized_edge["target_port_key"],
            )
            if source_port is None or target_port is None:
                return False
            if not port_supports_outgoing_edge(source_port) or not port_supports_incoming_edge(target_port):
                return False
            if not cls.accept_registry_edge(
                RegistryEdgeResolution(
                    source_node_id=source_ref_id,
                    source_port_key=normalized_edge["source_port_key"],
                    target_node_id=target_ref_id,
                    target_port_key=normalized_edge["target_port_key"],
                    source_port=source_port,
                    target_port=target_port,
                ),
                seen_connections=seen_connections,
                occupied_single_target_ports=occupied_single_target_ports,
            ):
                return False
        return True

    @classmethod
    def normalize_project_for_registry(cls, project: ProjectData, registry: NodeRegistry) -> None:
        """Normalize resolved content while preserving unresolved authored payloads."""
        for workspace in project.workspaces.values():
            persistence_state = workspace.capture_persistence_state()
            kernel = cls(registry=registry, workspace_nodes=workspace.nodes, workspace_edges=workspace.edges.values())
            resolved_nodes = kernel.resolve_registry_nodes()
            unknown_node_ids = set(workspace.nodes) - set(resolved_nodes)
            for resolution in resolved_nodes.values():
                node = resolution.node
                node.properties = registry.normalize_properties(
                    node.type_id,
                    node.properties,
                    include_defaults=False,
                )

            for node_id in sorted(unknown_node_ids):
                node = workspace.nodes.pop(node_id, None)
                if node is None:
                    continue
                persistence_state.unresolved_node_docs[node_id] = node_instance_to_mapping(node)

            resolved_nodes = kernel.resolve_registry_nodes()
            for edge_id, edge in list(workspace.edges.items()):
                if edge.source_node_id in unknown_node_ids or edge.target_node_id in unknown_node_ids:
                    persistence_state.unresolved_edge_docs[edge_id] = edge_instance_to_mapping(edge)
                    workspace.edges.pop(edge_id, None)

            sanitize_workspace_parent_links(workspace, persistence_state)

            for resolution in resolved_nodes.values():
                resolution.node.exposed_ports = kernel.normalized_exposed_ports(resolution)

            seen_connections: set[tuple[str, str, str, str]] = set()
            occupied_single_target_ports: set[tuple[str, str]] = set()
            for edge_id, edge in list(workspace.edges.items()):
                resolution = kernel.validate_registry_edge(
                    source_node_id=edge.source_node_id,
                    source_port_key=edge.source_port_key,
                    target_node_id=edge.target_node_id,
                    target_port_key=edge.target_port_key,
                    resolved_nodes=resolved_nodes,
                    require_source_output=True,
                    require_target_input=True,
                    require_exposed_ports=True,
                )
                if resolution is None or not cls.accept_registry_edge(
                    resolution,
                    seen_connections=seen_connections,
                    occupied_single_target_ports=occupied_single_target_ports,
                ):
                    workspace.edges.pop(edge_id, None)
            workspace.restore_persistence_state(persistence_state)

    def _resolved_port(self, node_id: str, port_key: str) -> tuple[NodeInstance, NodeTypeSpec, EffectivePort]:
        node = self.workspace_nodes[node_id]
        spec = self.registry.get_spec(node.type_id)
        port = find_port(
            node=node,
            spec=spec,
            workspace_nodes=self.workspace_nodes,
            port_key=port_key,
        )
        if port is None:
            raise KeyError(f"Port {port_key} not found on node type {spec.type_id}")
        return node, spec, port

    @staticmethod
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


@dataclass(slots=True)
class ValidatedGraphMutation:
    model: GraphModel
    workspace_id: str
    registry: NodeRegistry

    @property
    def workspace(self) -> WorkspaceData:
        return self.model.project.workspaces[self.workspace_id]

    @property
    def kernel(self) -> GraphInvariantKernel:
        return GraphInvariantKernel(
            registry=self.registry,
            workspace_nodes=self.workspace.nodes,
            workspace_edges=self.workspace.edges.values(),
        )

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
        self.kernel.add_edge_or_raise(
            source_node_id=source_node_id,
            source_port_key=source_port_key,
            target_node_id=target_node_id,
            target_port_key=target_port_key,
        )
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

    def set_port_label(self, node_id: str, port_key: str, label: str) -> None:
        self.model.set_port_label(self.workspace_id, node_id, port_key, label)

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
        return self.kernel._resolved_port(node_id, port_key)

    def _normalized_exposed_ports(self, node_id: str) -> dict[str, bool]:
        resolved_nodes = self.kernel.resolve_registry_nodes()
        resolution = resolved_nodes[node_id]
        return self.kernel.normalized_exposed_ports(resolution)

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
        kernel = self.kernel
        resolved_nodes = kernel.resolve_registry_nodes()
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
            resolution = kernel.validate_registry_edge(
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
            kernel.accept_registry_edge(
                resolution,
                seen_connections=seen_connections,
                occupied_single_target_ports=occupied_single_target_ports,
            )

        removed_edge_ids: list[str] = []
        for edge_id, edge in affected_edges:
            resolution = kernel.validate_registry_edge(
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
            if resolution is None or not kernel.accept_registry_edge(
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
    return GraphInvariantKernel(registry=registry, workspace_nodes=workspace_nodes).resolve_registry_nodes()


def normalized_exposed_ports(
    resolution: RegistryNodeResolution,
    *,
    workspace_nodes: dict[str, NodeInstance],
) -> dict[str, bool]:
    return GraphInvariantKernel(
        registry=NodeRegistry(),
        workspace_nodes=workspace_nodes,
    ).normalized_exposed_ports(resolution)


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
    kernel = GraphInvariantKernel(
        registry=NodeRegistry(),
        workspace_nodes={node_id: resolution.node for node_id, resolution in resolved_nodes.items()},
    )
    return kernel.validate_registry_edge(
        source_node_id=source_node_id,
        source_port_key=source_port_key,
        target_node_id=target_node_id,
        target_port_key=target_port_key,
        resolved_nodes=resolved_nodes,
        require_source_output=require_source_output,
        require_target_input=require_target_input,
        require_exposed_ports=require_exposed_ports,
        require_compatible_ports=require_compatible_ports,
    )


def accept_registry_edge(
    edge: RegistryEdgeResolution,
    *,
    seen_connections: set[tuple[str, str, str, str]],
    occupied_single_target_ports: set[tuple[str, str]],
) -> bool:
    return GraphInvariantKernel.accept_registry_edge(
        edge,
        seen_connections=seen_connections,
        occupied_single_target_ports=occupied_single_target_ports,
    )


def normalize_project_for_registry(project: ProjectData, registry: NodeRegistry) -> None:
    GraphInvariantKernel.normalize_project_for_registry(project, registry)
