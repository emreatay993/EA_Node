from __future__ import annotations

from typing import Any

from ea_node_editor.ui.shell.runtime_history import ACTION_ADD_NODE


def wrap_nodes_in_comment_backdrop(self, node_ids: list[Any]) -> str:
    model = self._scene_context.model
    if model is None:
        return ""
    workspace = model.project.workspaces.get(self._scene_context.workspace_id)
    if workspace is None:
        return ""
    transactions = self._authoring_transactions()
    if transactions is None:
        return ""

    history_group = self._scene_context.grouped_history_action(ACTION_ADD_NODE, workspace)
    wrapped = None
    with history_group:
        wrapped = transactions.wrap_selection_in_comment_backdrop(
            selected_node_ids=node_ids,
            scope_path=self._scene_context.scope_path,
        )
    if wrapped is None:
        return ""

    self._scope_selection.set_selected_node_ids([wrapped.backdrop_node_id], workspace=workspace)
    self._scene_context.rebuild_models()
    return wrapped.backdrop_node_id


def wrap_selected_nodes_in_comment_backdrop(self) -> bool:
    model = self._scene_context.model
    if model is None:
        return False
    workspace = model.project.workspaces.get(self._scene_context.workspace_id)
    if workspace is None:
        return False
    selected_node_ids = self._selected_node_ids_in_workspace(workspace)
    if not selected_node_ids:
        return False
    return bool(self.wrap_nodes_in_comment_backdrop(selected_node_ids))


__all__ = ["wrap_nodes_in_comment_backdrop", "wrap_selected_nodes_in_comment_backdrop"]
