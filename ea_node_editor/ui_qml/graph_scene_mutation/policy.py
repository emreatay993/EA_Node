from __future__ import annotations

from ea_node_editor.graph.effective_ports import find_port, ports_compatible


def are_ports_compatible(
    self,
    source_node_id: str,
    source_port: str,
    target_node_id: str,
    target_port: str,
) -> bool:
    model = self._scene_context.model
    registry = self._scene_context.registry
    if registry is None or model is None:
        return False
    workspace = model.project.workspaces.get(self._scene_context.workspace_id)
    if workspace is None:
        return False
    source_node = self._scene_context.node(source_node_id)
    target_node = self._scene_context.node(target_node_id)
    if source_node is None or target_node is None:
        return False
    source_spec = registry.get_spec(source_node.type_id)
    target_spec = registry.get_spec(target_node.type_id)
    source_port_doc = find_port(
        node=source_node,
        spec=source_spec,
        workspace_nodes=workspace.nodes,
        port_key=source_port,
    )
    target_port_doc = find_port(
        node=target_node,
        spec=target_spec,
        workspace_nodes=workspace.nodes,
        port_key=target_port,
    )
    if source_port_doc is None or target_port_doc is None:
        return False
    return ports_compatible(source_port_doc, target_port_doc)


def are_port_kinds_compatible(source_kind: str, target_kind: str) -> bool:
    from ea_node_editor.graph.effective_ports import are_port_kinds_compatible

    return are_port_kinds_compatible(str(source_kind), str(target_kind))


def are_data_types_compatible(source_type: str, target_type: str) -> bool:
    from ea_node_editor.graph.effective_ports import are_data_types_compatible

    return are_data_types_compatible(str(source_type), str(target_type))


__all__ = [
    "are_data_types_compatible",
    "are_port_kinds_compatible",
    "are_ports_compatible",
]

