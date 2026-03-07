from __future__ import annotations

from ea_node_editor.graph.model import ProjectData
from ea_node_editor.graph.rules import find_port
from ea_node_editor.nodes.registry import NodeRegistry


def normalize_project_for_registry(project: ProjectData, registry: NodeRegistry) -> None:
    """Normalize node properties/ports and prune invalid references for a registry."""
    for workspace in project.workspaces.values():
        unknown_node_ids: set[str] = set()
        for node_id, node in list(workspace.nodes.items()):
            try:
                spec = registry.get_spec(node.type_id)
            except KeyError:
                unknown_node_ids.add(node_id)
                continue

            node.properties = registry.normalize_properties(node.type_id, node.properties)
            node.exposed_ports = {
                port.key: bool(node.exposed_ports.get(port.key, port.exposed))
                for port in spec.ports
            }

        for node_id in unknown_node_ids:
            workspace.nodes.pop(node_id, None)

        for edge_id, edge in list(workspace.edges.items()):
            source_node = workspace.nodes.get(edge.source_node_id)
            target_node = workspace.nodes.get(edge.target_node_id)
            if source_node is None or target_node is None:
                workspace.edges.pop(edge_id, None)
                continue
            source_spec = registry.get_spec(source_node.type_id)
            target_spec = registry.get_spec(target_node.type_id)
            if find_port(source_spec, edge.source_port_key) is None:
                workspace.edges.pop(edge_id, None)
                continue
            if find_port(target_spec, edge.target_port_key) is None:
                workspace.edges.pop(edge_id, None)
                continue
