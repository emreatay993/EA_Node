from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

from ea_node_editor.graph.model import WorkspaceData, WorkspaceSnapshot

ACTION_ADD_NODE = "add-node"
ACTION_REMOVE_NODE = "remove-node"
ACTION_ADD_EDGE = "add-edge"
ACTION_REMOVE_EDGE = "remove-edge"
ACTION_RENAME_NODE = "rename-node"
ACTION_TOGGLE_COLLAPSED = "toggle-collapsed"
ACTION_TOGGLE_EXPOSED_PORT = "toggle-exposed-port"
ACTION_EDIT_NODE_PROPERTY = "edit-node-property"
ACTION_EDIT_NODE_STYLE = "edit-node-style"
ACTION_EDIT_EDGE_LABEL = "edit-edge-label"
ACTION_EDIT_EDGE_STYLE = "edit-edge-style"
ACTION_EDIT_PORT_LABEL = "edit-port-label"
ACTION_DUPLICATE_SUBGRAPH = "duplicate-subgraph"
ACTION_PASTE_SUBGRAPH = "paste-subgraph"
ACTION_GROUP_SELECTED_NODES = "group-selected-nodes"
ACTION_UNGROUP_SELECTED_SUBNODE = "ungroup-selected-subnode"
ACTION_WRAP_COMMENT_BACKDROP = "wrap-comment-backdrop"
ACTION_EDIT_PROPERTY = ACTION_EDIT_NODE_PROPERTY
ACTION_DELETE_SELECTED = "delete-selected"
ACTION_MOVE_NODE = "move-node"
ACTION_RESIZE_NODE = "resize-node"

@dataclass(slots=True)
class HistoryEntry:
    action_type: str
    before: WorkspaceSnapshot
    after: WorkspaceSnapshot


@dataclass(slots=True)
class _OpenGroup:
    action_type: str
    before: WorkspaceSnapshot
    after: WorkspaceSnapshot


class RuntimeGraphHistory:
    def __init__(self) -> None:
        self._undo_stacks: dict[str, list[HistoryEntry]] = {}
        self._redo_stacks: dict[str, list[HistoryEntry]] = {}
        self._groups: dict[str, list[_OpenGroup]] = {}

    @staticmethod
    def capture_workspace(workspace: WorkspaceData) -> WorkspaceSnapshot:
        return workspace.capture_snapshot()

    def clear_all(self) -> None:
        self._undo_stacks.clear()
        self._redo_stacks.clear()
        self._groups.clear()

    def clear_workspace(self, workspace_id: str) -> None:
        normalized_id = str(workspace_id).strip()
        if not normalized_id:
            return
        self._undo_stacks.pop(normalized_id, None)
        self._redo_stacks.pop(normalized_id, None)
        self._groups.pop(normalized_id, None)

    def undo_depth(self, workspace_id: str) -> int:
        normalized_id = str(workspace_id).strip()
        if not normalized_id:
            return 0
        return len(self._undo_stacks.get(normalized_id, []))

    def redo_depth(self, workspace_id: str) -> int:
        normalized_id = str(workspace_id).strip()
        if not normalized_id:
            return 0
        return len(self._redo_stacks.get(normalized_id, []))

    def can_undo(self, workspace_id: str) -> bool:
        return self.undo_depth(workspace_id) > 0

    def can_redo(self, workspace_id: str) -> bool:
        return self.redo_depth(workspace_id) > 0

    @contextmanager
    def grouped_action(self, workspace_id: str, action_type: str, workspace: WorkspaceData) -> Iterator[None]:
        normalized_id = str(workspace_id).strip()
        if not normalized_id:
            yield
            return
        initial_snapshot = self.capture_workspace(workspace)
        stack = self._groups.setdefault(normalized_id, [])
        stack.append(
            _OpenGroup(
                action_type=str(action_type).strip() or "grouped-action",
                before=initial_snapshot,
                after=initial_snapshot,
            )
        )
        try:
            yield
        finally:
            completed = stack.pop()
            completed.after = self.capture_workspace(workspace)
            if stack:
                stack[-1].after = completed.after
            else:
                self._groups.pop(normalized_id, None)
                self._commit(normalized_id, completed.action_type, completed.before, completed.after)

    def record_action(
        self,
        workspace_id: str,
        action_type: str,
        before_snapshot: WorkspaceSnapshot,
        workspace_after: WorkspaceData,
    ) -> bool:
        normalized_id = str(workspace_id).strip()
        if not normalized_id:
            return False
        after_snapshot = self.capture_workspace(workspace_after)
        return self._record_with_snapshots(normalized_id, action_type, before_snapshot, after_snapshot)

    def undo_workspace(self, workspace_id: str, workspace: WorkspaceData) -> HistoryEntry | None:
        normalized_id = str(workspace_id).strip()
        if not normalized_id:
            return None
        undo_stack = self._undo_stacks.get(normalized_id)
        if not undo_stack:
            return None
        entry = undo_stack.pop()
        workspace.restore_snapshot(entry.before)
        self._redo_stacks.setdefault(normalized_id, []).append(entry)
        return entry

    def redo_workspace(self, workspace_id: str, workspace: WorkspaceData) -> HistoryEntry | None:
        normalized_id = str(workspace_id).strip()
        if not normalized_id:
            return None
        redo_stack = self._redo_stacks.get(normalized_id)
        if not redo_stack:
            return None
        entry = redo_stack.pop()
        workspace.restore_snapshot(entry.after)
        self._undo_stacks.setdefault(normalized_id, []).append(entry)
        return entry

    def _record_with_snapshots(
        self,
        workspace_id: str,
        action_type: str,
        before_snapshot: WorkspaceSnapshot,
        after_snapshot: WorkspaceSnapshot,
    ) -> bool:
        if before_snapshot == after_snapshot:
            return False
        open_groups = self._groups.get(workspace_id)
        if open_groups:
            open_groups[-1].after = after_snapshot
            return True
        self._commit(workspace_id, action_type, before_snapshot, after_snapshot)
        return True

    def _commit(
        self,
        workspace_id: str,
        action_type: str,
        before_snapshot: WorkspaceSnapshot,
        after_snapshot: WorkspaceSnapshot,
    ) -> None:
        if before_snapshot == after_snapshot:
            return
        entry = HistoryEntry(
            action_type=str(action_type).strip() or "mutation",
            before=before_snapshot,
            after=after_snapshot,
        )
        self._undo_stacks.setdefault(workspace_id, []).append(entry)
        self._redo_stacks[workspace_id] = []


__all__ = [
    "ACTION_ADD_EDGE",
    "ACTION_ADD_NODE",
    "ACTION_DELETE_SELECTED",
    "ACTION_DUPLICATE_SUBGRAPH",
    "ACTION_EDIT_EDGE_LABEL",
    "ACTION_EDIT_EDGE_STYLE",
    "ACTION_EDIT_NODE_PROPERTY",
    "ACTION_EDIT_NODE_STYLE",
    "ACTION_EDIT_PROPERTY",
    "ACTION_EDIT_PORT_LABEL",
    "ACTION_GROUP_SELECTED_NODES",
    "ACTION_MOVE_NODE",
    "ACTION_PASTE_SUBGRAPH",
    "ACTION_RESIZE_NODE",
    "ACTION_REMOVE_EDGE",
    "ACTION_REMOVE_NODE",
    "ACTION_RENAME_NODE",
    "ACTION_TOGGLE_COLLAPSED",
    "ACTION_TOGGLE_EXPOSED_PORT",
    "ACTION_UNGROUP_SELECTED_SUBNODE",
    "ACTION_WRAP_COMMENT_BACKDROP",
    "HistoryEntry",
    "RuntimeGraphHistory",
    "WorkspaceSnapshot",
]
