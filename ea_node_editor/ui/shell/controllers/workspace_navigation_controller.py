from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from PyQt6.QtCore import QRectF

from ea_node_editor.ui.shell.controllers.workspace_view_nav_ops import WorkspaceViewNavOps

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow


class _WorkspaceNavigationControllerProtocol(Protocol):
    def save_active_view_state(self) -> None: ...

    def restore_active_view_state(self) -> None: ...

    def refresh_workspace_tabs(self) -> None: ...

    def switch_workspace(self, workspace_id: str) -> None: ...

    def rename_workspace_by_id(self, workspace_id: str) -> bool: ...

    def on_workspace_tab_close(self, index: int) -> None: ...

    def reveal_parent_chain(self, workspace_id: str, node_id: str) -> list[str]: ...

    def center_on_node(self, node_id: str) -> bool: ...

    def center_on_selection(self) -> bool: ...


class WorkspaceNavigationController:
    def __init__(
        self,
        host: ShellWindow,
        controller: _WorkspaceNavigationControllerProtocol,
    ) -> None:
        self._host = host
        self._controller = controller
        self._ops = WorkspaceViewNavOps(host, controller)

    def switch_workspace_by_offset(self, offset: int) -> None:
        self._ops.switch_workspace_by_offset(offset)

    def refresh_workspace_tabs(self) -> None:
        self._ops.refresh_workspace_tabs()

    def switch_workspace(self, workspace_id: str) -> None:
        self._ops.switch_workspace(workspace_id)

    def move_workspace(self, from_index: int, to_index: int) -> bool:
        refs = self._host.workspace_manager.list_workspaces()
        if len(refs) < 2:
            return False
        if from_index < 0 or from_index >= len(refs):
            return False
        bounded_index = max(0, min(int(to_index), len(refs) - 1))
        if from_index == bounded_index:
            return False
        self._host.workspace_manager.move_workspace(from_index, bounded_index)
        self._controller.refresh_workspace_tabs()
        return True

    def save_active_view_state(self) -> None:
        self._ops.save_active_view_state()

    def restore_active_view_state(self) -> None:
        self._ops.restore_active_view_state()

    def visible_scene_rect(self) -> QRectF:
        return self._ops.visible_scene_rect()

    def current_workspace_scene_bounds(self) -> QRectF | None:
        return self._ops.current_workspace_scene_bounds()

    def selection_bounds(self) -> QRectF | None:
        return self._ops.selection_bounds()

    def frame_all(self) -> bool:
        return self._ops.frame_all()

    def frame_selection(self) -> bool:
        return self._ops.frame_selection()

    def frame_node(self, node_id: str) -> bool:
        return self._ops.frame_node(node_id)

    def center_on_node(self, node_id: str) -> bool:
        return self._ops.center_on_node(node_id)

    def center_on_selection(self) -> bool:
        return self._ops.center_on_selection()

    def frame_scene_bounds(self, bounds: QRectF | None) -> bool:
        return self._ops.frame_scene_bounds(bounds)

    @staticmethod
    def graph_search_rank(
        query: str,
        *,
        title: str,
        display_name: str,
        type_id: str,
    ) -> int | None:
        return WorkspaceViewNavOps.graph_search_rank(
            query,
            title=title,
            display_name=display_name,
            type_id=type_id,
        )

    def search_graph_nodes(
        self,
        query: str,
        limit: int,
        *,
        enabled_scopes: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        return self._ops.search_graph_nodes(query, limit, enabled_scopes=enabled_scopes)

    def jump_to_graph_node(self, workspace_id: str, node_id: str) -> bool:
        return self._ops.jump_to_graph_node(workspace_id, node_id)

    def create_view(self) -> None:
        self._ops.create_view()

    def switch_view(self, view_id: str) -> None:
        self._ops.switch_view(view_id)

    def create_workspace(self) -> None:
        from PyQt6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(self._host, "New Workspace", "Workspace name:")
        if not ok:
            return
        workspace_id = self._host.workspace_manager.create_workspace(name=name or None)
        self._host.runtime_history.clear_workspace(workspace_id)
        self._controller.refresh_workspace_tabs()
        self._controller.switch_workspace(workspace_id)

    def rename_active_workspace(self) -> None:
        index = self._host.workspace_tabs.currentIndex()
        if index < 0:
            return
        workspace_id = self._host.workspace_tabs.tabData(index)
        self._controller.rename_workspace_by_id(workspace_id)

    def rename_workspace_by_id(self, workspace_id: str) -> bool:
        from PyQt6.QtWidgets import QInputDialog

        normalized_workspace_id = str(workspace_id or "").strip()
        if not normalized_workspace_id:
            return False
        workspace = self._host.model.project.workspaces.get(normalized_workspace_id)
        if workspace is None:
            return False
        name, ok = QInputDialog.getText(self._host, "Rename Workspace", "New name:", text=workspace.name)
        normalized_name = str(name or "").strip()
        if not ok or not normalized_name or normalized_name == workspace.name:
            return False
        self._host.workspace_manager.rename_workspace(normalized_workspace_id, normalized_name)
        self._controller.refresh_workspace_tabs()
        return True

    def duplicate_active_workspace(self) -> None:
        index = self._host.workspace_tabs.currentIndex()
        if index < 0:
            return
        workspace_id = self._host.workspace_tabs.tabData(index)
        if not workspace_id:
            return
        duplicated_id = self._host.workspace_manager.duplicate_workspace(workspace_id)
        self._host.runtime_history.clear_workspace(duplicated_id)
        self._controller.refresh_workspace_tabs()
        self._controller.switch_workspace(duplicated_id)

    def close_active_workspace(self) -> None:
        index = self._host.workspace_tabs.currentIndex()
        if index >= 0:
            self._controller.on_workspace_tab_close(index)

    def close_workspace_by_id(self, workspace_id: str) -> bool:
        normalized_workspace_id = str(workspace_id or "").strip()
        if not normalized_workspace_id:
            return False
        target_index = -1
        for index in range(self._host.workspace_tabs.count()):
            if self._host.workspace_tabs.tabData(index) != normalized_workspace_id:
                continue
            target_index = index
            break
        if target_index < 0:
            return False
        self._controller.on_workspace_tab_close(target_index)
        return normalized_workspace_id not in self._host.model.project.workspaces

    def close_view(self, view_id: str) -> bool:
        from PyQt6.QtWidgets import QMessageBox

        workspace_id = self._host.workspace_manager.active_workspace_id()
        workspace = self._host.model.project.workspaces.get(workspace_id)
        normalized_view_id = str(view_id or "").strip()
        if workspace is None or not normalized_view_id:
            return False
        workspace.ensure_default_view()
        if normalized_view_id not in workspace.views:
            return False
        if len(workspace.views) == 1:
            QMessageBox.warning(self._host, "View", "Cannot close the last view.")
            return False

        active_view_closed = workspace.active_view_id == normalized_view_id
        self._host.workspace_manager.close_view(workspace_id, normalized_view_id)
        if active_view_closed:
            self._controller.restore_active_view_state()
            self._host.scene.sync_scope_with_active_view()
            self._host.search_scope_controller.restore_scope_camera()

        self._host.search_scope_controller.discard_scope_camera_for_view(workspace_id, normalized_view_id)
        self._host.workspace_state_changed.emit()
        return True

    def rename_view(self, view_id: str) -> bool:
        from PyQt6.QtWidgets import QInputDialog

        workspace_id = self._host.workspace_manager.active_workspace_id()
        workspace = self._host.model.project.workspaces.get(workspace_id)
        normalized_view_id = str(view_id or "").strip()
        if workspace is None or not normalized_view_id:
            return False
        workspace.ensure_default_view()
        view = workspace.views.get(normalized_view_id)
        if view is None:
            return False

        name, ok = QInputDialog.getText(self._host, "Rename View", "New name:", text=view.name)
        if not ok:
            return False
        normalized_name = str(name or "").strip()
        if not normalized_name or normalized_name == view.name:
            return False

        self._host.workspace_manager.rename_view(workspace_id, normalized_view_id, normalized_name)
        self._host.workspace_state_changed.emit()
        return True

    def move_view(self, from_index: int, to_index: int) -> bool:
        workspace_id = self._host.workspace_manager.active_workspace_id()
        workspace = self._host.model.project.workspaces.get(workspace_id)
        if workspace is None:
            return False
        workspace.ensure_default_view()
        if len(workspace.views) < 2:
            return False
        if from_index < 0 or from_index >= len(workspace.views):
            return False
        bounded_index = max(0, min(int(to_index), len(workspace.views) - 1))
        if from_index == bounded_index:
            return False
        self._host.workspace_manager.move_view(workspace_id, from_index, bounded_index)
        self._host.workspace_state_changed.emit()
        return True

    def on_workspace_tab_changed(self, index: int) -> None:
        if index < 0:
            return
        workspace_id = self._host.workspace_tabs.tabData(index)
        if workspace_id:
            self._controller.switch_workspace(workspace_id)

    def on_workspace_tab_close(self, index: int) -> None:
        from PyQt6.QtWidgets import QMessageBox

        workspace_id = self._host.workspace_tabs.tabData(index)
        if not workspace_id:
            return
        workspace = self._host.model.project.workspaces[workspace_id]
        if workspace.dirty:
            reply = QMessageBox.question(
                self._host,
                "Unsaved Changes",
                f"Workspace '{workspace.name}' has unsaved changes. Close anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        try:
            self._host.workspace_manager.close_workspace(workspace_id)
        except ValueError:
            QMessageBox.warning(self._host, "Workspace", "Cannot close the last workspace.")
            return
        self._host.runtime_history.clear_workspace(workspace_id)
        self._controller.refresh_workspace_tabs()
        self._controller.switch_workspace(self._host.workspace_manager.active_workspace_id())

    def focus_failed_node(self, workspace_id: str, node_id: str, error: str) -> None:
        self._ops.focus_failed_node(workspace_id, node_id, error)

    def reveal_parent_chain(self, workspace_id: str, node_id: str) -> list[str]:
        return self._ops.reveal_parent_chain(workspace_id, node_id)
