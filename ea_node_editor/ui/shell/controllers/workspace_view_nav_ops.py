from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from PyQt6.QtCore import QRectF

from ea_node_editor.ui.support.node_presentation import build_user_facing_node_instance_number
from ea_node_editor.ui.shell.workspace_flow import build_workspace_tab_items, next_workspace_tab_index
from ea_node_editor.ui_qml.viewport_bridge import FRAME_PADDING_PX

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow


class _WorkspaceViewNavControllerProtocol(Protocol):
    def save_active_view_state(self) -> None: ...

    def restore_active_view_state(self) -> None: ...

    def refresh_workspace_tabs(self) -> None: ...

    def switch_workspace(self, workspace_id: str) -> None: ...

    def reveal_parent_chain(self, workspace_id: str, node_id: str) -> list[str]: ...

    def center_on_node(self, node_id: str) -> bool: ...

    def center_on_selection(self) -> bool: ...


class WorkspaceViewNavOps:
    def __init__(
        self,
        host: ShellWindow,
        controller: _WorkspaceViewNavControllerProtocol,
    ) -> None:
        self._host = host
        self._controller = controller

    def switch_workspace_by_offset(self, offset: int) -> None:
        target = next_workspace_tab_index(
            self._host.workspace_tabs.count(),
            self._host.workspace_tabs.currentIndex(),
            offset,
        )
        if target is None:
            return
        self._host.workspace_tabs.setCurrentIndex(target)

    def refresh_workspace_tabs(self) -> None:
        current_workspace = self._host.workspace_manager.active_workspace_id()
        tabs = build_workspace_tab_items(self._host.workspace_manager.list_workspaces())
        self._host.workspace_tabs.set_tabs(tabs, current_workspace)
        self._host.workspace_state_changed.emit()

    def switch_workspace(self, workspace_id: str) -> None:
        self._controller.save_active_view_state()
        if workspace_id not in self._host.model.project.workspaces:
            return
        self._host.workspace_manager.set_active_workspace(workspace_id)
        self._host.scene.set_workspace(self._host.model, self._host.registry, workspace_id)
        self._controller.restore_active_view_state()
        self._controller.refresh_workspace_tabs()
        self._host.script_editor.set_node(None)
        self._host.workspace_state_changed.emit()

    def save_active_view_state(self) -> None:
        workspace_id = str(self._host.scene.workspace_id or "").strip()
        if not workspace_id:
            return
        if workspace_id not in self._host.model.project.workspaces:
            return
        mutation_service = self._host.model.mutation_service(workspace_id)
        center = self._host.view.mapToScene(self._host.view.viewport().rect().center())
        mutation_service.save_active_view_state(
            zoom=self._host.view.zoom,
            pan_x=center.x(),
            pan_y=center.y(),
        )

    def restore_active_view_state(self) -> None:
        workspace_id = self._host.workspace_manager.active_workspace_id()
        if workspace_id not in self._host.model.project.workspaces:
            return
        view_state = self._host.model.mutation_service(workspace_id).active_view_state()
        self._host.view.set_zoom(max(0.1, min(3.0, view_state.zoom)))
        self._host.view.centerOn(view_state.pan_x, view_state.pan_y)

    def visible_scene_rect(self) -> QRectF:
        return self._host.view.visible_scene_rect()

    def current_workspace_scene_bounds(self) -> QRectF | None:
        return self._host.scene.workspace_scene_bounds()

    def selection_bounds(self) -> QRectF | None:
        return self._host.scene.selection_bounds()

    def frame_all(self) -> bool:
        return self.frame_scene_bounds(self.current_workspace_scene_bounds())

    def frame_selection(self) -> bool:
        return self.frame_scene_bounds(self.selection_bounds())

    def frame_node(self, node_id: str) -> bool:
        return self.frame_scene_bounds(self._host.scene.node_bounds(str(node_id).strip()))

    def center_on_node(self, node_id: str) -> bool:
        bounds = self._host.scene.node_bounds(str(node_id).strip())
        if bounds is None:
            return False
        return self._host.view.center_on_scene_rect(bounds)

    def center_on_selection(self) -> bool:
        bounds = self.selection_bounds()
        if bounds is None:
            return False
        return self._host.view.center_on_scene_rect(bounds)

    def frame_scene_bounds(self, bounds: QRectF | None) -> bool:
        if bounds is None:
            return False
        if bounds.width() <= 0.0 or bounds.height() <= 0.0:
            return False
        return self._host.view.frame_scene_rect(bounds, padding_px=FRAME_PADDING_PX)

    @staticmethod
    def graph_search_rank(
        query: str,
        *,
        title: str,
        display_name: str,
        type_id: str,
    ) -> int | None:
        if not query:
            return None
        if title.startswith(query) or display_name.startswith(query):
            return 0
        if query in title or query in display_name:
            return 1
        if query in type_id:
            return 2
        return None

    def search_graph_nodes(self, query: str, limit: int) -> list[dict[str, Any]]:
        normalized_query = str(query).strip().lower()
        if not normalized_query:
            return []

        max_results = max(0, int(limit))
        ranked: list[tuple[int, str, str, dict[str, Any]]] = []
        for workspace_ref in self._host.workspace_manager.list_workspaces():
            workspace = self._host.model.project.workspaces.get(workspace_ref.workspace_id)
            if workspace is None:
                continue
            workspace_name_lower = workspace.name.lower()
            for node in workspace.nodes.values():
                spec = self._host.registry.get_spec(node.type_id)
                node_title = str(node.title)
                node_title_lower = node_title.lower()
                display_name = str(spec.display_name)
                display_name_lower = display_name.lower()
                type_id = str(node.type_id)
                type_id_lower = type_id.lower()
                node_id = str(node.node_id)
                instance_number = build_user_facing_node_instance_number(
                    node=node,
                    workflow_nodes=workspace.nodes,
                )
                rank = self.graph_search_rank(
                    normalized_query,
                    title=node_title_lower,
                    display_name=display_name_lower,
                    type_id=type_id_lower,
                )
                if rank is None:
                    continue
                ranked.append(
                    (
                        rank,
                        workspace_name_lower,
                        node_title_lower,
                        {
                            "workspace_id": workspace.workspace_id,
                            "workspace_name": workspace.name,
                            "node_id": node_id,
                            "node_title": node_title,
                            "display_name": display_name,
                            "instance_number": int(instance_number),
                            "instance_label": f"ID {instance_number}",
                            "type_id": type_id,
                        },
                    )
                )

        ranked.sort(key=lambda item: (item[0], item[1], item[2]))
        return [item[3] for item in ranked[:max_results]]

    def jump_to_graph_node(self, workspace_id: str, node_id: str) -> bool:
        normalized_workspace_id = str(workspace_id).strip()
        normalized_node_id = str(node_id).strip()
        if not normalized_workspace_id or not normalized_node_id:
            return False

        workspace = self._host.model.project.workspaces.get(normalized_workspace_id)
        if workspace is None or normalized_node_id not in workspace.nodes:
            return False

        if normalized_workspace_id != self._host.workspace_manager.active_workspace_id():
            self._controller.switch_workspace(normalized_workspace_id)

        self._controller.reveal_parent_chain(normalized_workspace_id, normalized_node_id)
        self._host.scene.open_scope_for_node(normalized_node_id)
        if self._host.scene.focus_node(normalized_node_id) is None:
            return False
        return self._controller.center_on_selection()

    def create_view(self) -> None:
        from PyQt6.QtWidgets import QInputDialog

        workspace_id = self._host.workspace_manager.active_workspace_id()
        self._controller.save_active_view_state()
        if workspace_id not in self._host.model.project.workspaces:
            return
        mutation_service = self._host.model.mutation_service(workspace_id)
        source_view_id = mutation_service.active_view_state().view_id
        name, ok = QInputDialog.getText(self._host, "New View", "View name:")
        if not ok:
            return
        normalized_name = str(name).strip()
        view = mutation_service.create_view(
            name=normalized_name or None,
            source_view_id=source_view_id,
        )
        mutation_service.set_active_view(view.view_id)
        self._controller.restore_active_view_state()
        self._host.workspace_state_changed.emit()

    def switch_view(self, view_id: str) -> None:
        workspace_id = self._host.workspace_manager.active_workspace_id()
        self._controller.save_active_view_state()
        if workspace_id not in self._host.model.project.workspaces:
            return
        self._host.model.mutation_service(workspace_id).set_active_view(view_id)
        self._controller.restore_active_view_state()
        self._host.workspace_state_changed.emit()

    def focus_failed_node(self, workspace_id: str, node_id: str, error: str) -> None:
        from PyQt6.QtWidgets import QMessageBox

        if workspace_id and workspace_id != self._host.workspace_manager.active_workspace_id():
            self._controller.switch_workspace(workspace_id)

        focus_candidates: list[str] = []
        if node_id:
            focus_candidates.append(node_id)
        focus_candidates.extend(self._controller.reveal_parent_chain(workspace_id, node_id))

        focused_node_id = ""
        for target_node_id in focus_candidates:
            self._host.scene.open_scope_for_node(target_node_id)
            if self._host.scene.focus_node(target_node_id) is not None:
                focused_node_id = target_node_id
                break
        if focused_node_id:
            self._controller.center_on_node(focused_node_id)
        if error:
            QMessageBox.critical(self._host, "Workflow Error", error)

    def reveal_parent_chain(self, workspace_id: str, node_id: str) -> list[str]:
        if not workspace_id or not node_id:
            return []
        workspace = self._host.model.project.workspaces.get(workspace_id)
        if workspace is None:
            return []
        node = workspace.nodes.get(node_id)
        if node is None:
            return []

        chain: list[str] = []
        seen: set[str] = set()
        parent_id = node.parent_node_id
        while parent_id and parent_id not in seen:
            seen.add(parent_id)
            parent_node = workspace.nodes.get(parent_id)
            if parent_node is None:
                break
            chain.append(parent_id)
            parent_id = parent_node.parent_node_id

        for candidate_id in reversed(chain):
            parent_node = workspace.nodes.get(candidate_id)
            if parent_node is not None and parent_node.collapsed:
                self._host.scene.set_node_collapsed(candidate_id, False)
        return chain
