from __future__ import annotations

from dataclasses import dataclass

from ea_node_editor.graph.effective_ports import EffectivePort, effective_ports, find_port
from ea_node_editor.graph.model import (
    NodeInstance,
    ProjectData,
    edge_instance_to_mapping,
    node_instance_to_mapping,
)
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import NodeTypeSpec


@dataclass(slots=True, frozen=True)
class RegistryNodeResolution:
    node: NodeInstance
    spec: NodeTypeSpec


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
