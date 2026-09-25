# Purpose: Normalize loaded graph state against the current registry without persistence IO.
# Map: subsystems/graph_domain.md
# Tests: tests/test_graph_registry_normalization.py
from __future__ import annotations

from ea_node_editor.graph.hierarchy import sanitize_workspace_held_member_ids, sanitize_workspace_parent_links
from ea_node_editor.graph.node_port_state import normalize_node_port_state
from ea_node_editor.graph.invariant_kernel import GraphInvariantKernel, RegistryValidationPassMemo
from ea_node_editor.graph.project_state import ProjectData
from ea_node_editor.nodes.registry import NodeRegistry


def normalize_project_for_registry(project: ProjectData, registry: NodeRegistry) -> None:
    """Normalize live graph content against the current registry."""
    for workspace in project.workspaces.values():
        workspace_changed = False
        kernel = GraphInvariantKernel(
            registry=registry,
            workspace_nodes=workspace.nodes,
            workspace_edges=workspace.edges.values(),
        )
        memo = RegistryValidationPassMemo()
        resolved_nodes = kernel.resolve_registry_nodes(memo=memo)
        unknown_node_ids = set(workspace.nodes) - set(resolved_nodes)
        for resolution in resolved_nodes.values():
            node = resolution.node
            try:
                normalized_properties = registry.normalize_properties(
                    node.type_id,
                    node.properties,
                    include_defaults=False,
                )
            except ValueError as exc:
                if "unknown data-type ID" not in str(exc):
                    raise
                normalized_properties = node.properties
            if node.properties != normalized_properties:
                node.properties = normalized_properties
                workspace_changed = True
            requested_settings_group_ids = set(node.expanded_settings_group_ids)
            normalized_settings_group_ids = tuple(
                group.group_id for group in resolution.spec.settings_groups if group.group_id in requested_settings_group_ids
            )
            if node.expanded_settings_group_ids != normalized_settings_group_ids:
                node.expanded_settings_group_ids = normalized_settings_group_ids
                workspace_changed = True

        for node_id in sorted(unknown_node_ids):
            if workspace.nodes.pop(node_id, None) is not None:
                workspace_changed = True

        for edge_id, edge in list(workspace.edges.items()):
            if edge.source_node_id in unknown_node_ids or edge.target_node_id in unknown_node_ids:
                if workspace.edges.pop(edge_id, None) is not None:
                    memo.invalidate_edges()
                    workspace_changed = True

        parent_links_before = {
            node_id: node.parent_node_id
            for node_id, node in workspace.nodes.items()
        }
        sanitize_workspace_parent_links(workspace)
        for node_id, node in workspace.nodes.items():
            if parent_links_before.get(node_id) != node.parent_node_id:
                workspace_changed = True
                break
        if sanitize_workspace_held_member_ids(workspace):
            workspace_changed = True

        for resolution in resolved_nodes.values():
            node = resolution.node
            ports = kernel.effective_ports_for(
                resolution, workspace_nodes=workspace.nodes, memo=memo,
            )
            state = normalize_node_port_state(node, resolution.spec, ports)
            if node.exposed_ports != state.exposed_ports:
                node.exposed_ports = state.exposed_ports
                workspace_changed = True
            if node.port_labels != state.port_labels:
                node.port_labels = state.port_labels
                workspace_changed = True
            if node.port_modifiers != state.port_modifiers:
                node.port_modifiers = state.port_modifiers
                workspace_changed = True
            if node.principal_input_port_id != state.principal_input_port_id:
                node.principal_input_port_id = state.principal_input_port_id
                workspace_changed = True

        for edge_id in kernel.prunable_edge_ids(memo=memo):
            workspace.edges.pop(edge_id, None)
            workspace_changed = True

        input_groups: dict[tuple[str, str], list] = {}
        for edge in workspace.edges.values():
            input_groups.setdefault((edge.target_node_id, edge.target_port_key), []).append(edge)
        for edges in input_groups.values():
            ordered = sorted(edges, key=lambda edge: (edge.input_order, edge.edge_id))
            for input_order, edge in enumerate(ordered):
                if edge.input_order != input_order:
                    edge.input_order = input_order
                    workspace_changed = True

        if workspace_changed:
            workspace.mark_dirty()


__all__ = ["normalize_project_for_registry"]
