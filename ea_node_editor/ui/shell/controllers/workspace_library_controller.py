from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QRectF

from ea_node_editor.custom_workflows import (
    custom_workflow_library_items,
    normalize_custom_workflow_metadata,
    upsert_custom_workflow_definition,
)
from ea_node_editor.graph.hierarchy import scope_parent_id
from ea_node_editor.graph.model import NodeInstance
from ea_node_editor.graph.transforms import (
    build_subnode_custom_workflow_snapshot_data,
)
from ea_node_editor.nodes.builtins.subnode import (
    SUBNODE_TYPE_ID,
)
from ea_node_editor.nodes.types import NodeTypeSpec
from ea_node_editor.ui.shell.runtime_clipboard import (
    build_graph_fragment_payload,
    normalize_graph_fragment_payload,
)
from ea_node_editor.ui.shell.library_flow import pick_connection_candidate
from ea_node_editor.ui.shell.controllers.workspace_io_ops import WorkspaceIOOps
from ea_node_editor.ui.shell.controllers.workspace_edit_ops import WorkspaceEditOps
from ea_node_editor.ui.shell.controllers.workspace_drop_connect_ops import WorkspaceDropConnectOps
from ea_node_editor.ui.shell.controllers.result import ControllerResult
from ea_node_editor.ui.shell.controllers.workspace_view_nav_ops import WorkspaceViewNavOps

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow

_GRAPH_SEARCH_LIMIT = 10
_CUSTOM_WORKFLOW_DESCRIPTION = "Project-local custom workflow snapshot."


class WorkspaceLibraryController:
    def __init__(self, host: ShellWindow) -> None:
        self._host = host
        self._view_nav_ops = WorkspaceViewNavOps(host, self)
        self._drop_connect_ops = WorkspaceDropConnectOps(host, self)
        self._edit_ops = WorkspaceEditOps(host, self)
        self._io_ops = WorkspaceIOOps(host, self)
        self._last_clipboard_fragment_signature = ""
        self._clipboard_paste_count = 0

    def _project_metadata(self) -> dict[str, Any]:
        metadata = self._host.model.project.metadata
        if isinstance(metadata, dict):
            return metadata
        self._host.model.project.metadata = {}
        return self._host.model.project.metadata

    def _custom_workflow_definitions(self) -> list[dict[str, Any]]:
        metadata = self._project_metadata()
        normalized = normalize_custom_workflow_metadata(metadata.get("custom_workflows"))
        if metadata.get("custom_workflows") != normalized:
            metadata["custom_workflows"] = normalized
            self._host.model.project.metadata = metadata
        return normalized

    def _set_custom_workflow_definitions(self, definitions: list[dict[str, Any]]) -> None:
        metadata = self._project_metadata()
        metadata["custom_workflows"] = normalize_custom_workflow_metadata(definitions)
        self._host.model.project.metadata = metadata

    def custom_workflow_library_items(self) -> list[dict[str, Any]]:
        return custom_workflow_library_items(self._custom_workflow_definitions())

    def publish_custom_workflow_from_selected_subnode(self) -> ControllerResult[bool]:
        selected = self.selected_node_context()
        if selected is None:
            return ControllerResult(False, "Select a subnode shell to publish.", payload=False)
        node, _spec = selected
        if node.type_id != SUBNODE_TYPE_ID:
            return ControllerResult(False, "Selected node is not a subnode shell.", payload=False)
        return self._publish_custom_workflow_from_shell(node.node_id)

    def publish_custom_workflow_from_current_scope(self) -> ControllerResult[bool]:
        scope_shell_id = scope_parent_id(self._host.scene.active_scope_path)
        if not scope_shell_id:
            return ControllerResult(False, "Open a subnode scope to publish.", payload=False)
        return self._publish_custom_workflow_from_shell(scope_shell_id)

    def publish_custom_workflow_from_node(self, node_id: str) -> ControllerResult[bool]:
        node_id = str(node_id or "").strip()
        if not node_id:
            return ControllerResult(False, "No node ID provided.", payload=False)
        return self._publish_custom_workflow_from_shell(node_id)

    def _publish_custom_workflow_from_shell(self, shell_node_id: str) -> ControllerResult[bool]:
        workspace = self.active_workspace()
        if workspace is None:
            return ControllerResult(False, "Workspace not found.", payload=False)
        shell_node = workspace.nodes.get(str(shell_node_id).strip())
        if shell_node is None or shell_node.type_id != SUBNODE_TYPE_ID:
            return ControllerResult(False, "Subnode shell not found in workspace.", payload=False)

        snapshot = build_subnode_custom_workflow_snapshot_data(
            workspace=workspace,
            registry=self._host.registry,
            shell_node_id=shell_node.node_id,
        )
        if snapshot is None:
            return ControllerResult(False, "Could not build subnode snapshot.", payload=False)

        fragment = snapshot.get("fragment")
        if not isinstance(fragment, dict):
            return ControllerResult(False, "Subnode snapshot fragment is invalid.", payload=False)
        nodes_payload = fragment.get("nodes")
        edges_payload = fragment.get("edges")
        if not isinstance(nodes_payload, list) or not isinstance(edges_payload, list):
            return ControllerResult(False, "Subnode snapshot fragment is invalid.", payload=False)

        graph_fragment_payload = build_graph_fragment_payload(
            nodes=copy.deepcopy(nodes_payload),
            edges=copy.deepcopy(edges_payload),
        )
        normalized_fragment = normalize_graph_fragment_payload(graph_fragment_payload)
        if normalized_fragment is None:
            return ControllerResult(False, "Subnode snapshot fragment is invalid.", payload=False)

        updated_definitions, _saved_definition = upsert_custom_workflow_definition(
            self._custom_workflow_definitions(),
            name=shell_node.title,
            description=_CUSTOM_WORKFLOW_DESCRIPTION,
            ports=copy.deepcopy(snapshot.get("ports", [])),
            fragment=normalized_fragment,
            source_shell_ref_id=shell_node.node_id,
        )
        self._set_custom_workflow_definitions(updated_definitions)
        self._host.project_meta_changed.emit()
        self._host.node_library_changed.emit()
        return ControllerResult(True, payload=True)

    def selected_node_context(self) -> tuple[NodeInstance, NodeTypeSpec] | None:
        node_id = self._host.scene.selected_node_id()
        if not node_id:
            return None
        workspace = self._host.model.project.workspaces.get(self._host.active_workspace_id)
        if workspace is None:
            return None
        node = workspace.nodes.get(node_id)
        if node is None:
            return None
        spec = self._host.registry.get_spec(node.type_id)
        return node, spec

    def set_selected_node_property(self, key: str, value: Any) -> None:
        self._edit_ops.set_selected_node_property(key, value)

    def set_selected_port_exposed(self, key: str, exposed: bool) -> None:
        self._edit_ops.set_selected_port_exposed(key, exposed)

    def set_selected_node_collapsed(self, collapsed: bool) -> None:
        self._edit_ops.set_selected_node_collapsed(collapsed)

    def switch_workspace_by_offset(self, offset: int) -> None:
        self._view_nav_ops.switch_workspace_by_offset(offset)

    def refresh_workspace_tabs(self) -> None:
        self._view_nav_ops.refresh_workspace_tabs()

    def switch_workspace(self, workspace_id: str) -> None:
        self._view_nav_ops.switch_workspace(workspace_id)

    def save_active_view_state(self) -> None:
        self._view_nav_ops.save_active_view_state()

    def restore_active_view_state(self) -> None:
        self._view_nav_ops.restore_active_view_state()

    def visible_scene_rect(self) -> QRectF:
        return self._view_nav_ops.visible_scene_rect()

    def current_workspace_scene_bounds(self) -> QRectF | None:
        return self._view_nav_ops.current_workspace_scene_bounds()

    def selection_bounds(self) -> QRectF | None:
        return self._view_nav_ops.selection_bounds()

    def frame_all(self) -> bool:
        return self._view_nav_ops.frame_all()

    def frame_selection(self) -> bool:
        return self._view_nav_ops.frame_selection()

    def frame_node(self, node_id: str) -> bool:
        return self._view_nav_ops.frame_node(node_id)

    def center_on_node(self, node_id: str) -> bool:
        return self._view_nav_ops.center_on_node(node_id)

    def center_on_selection(self) -> bool:
        return self._view_nav_ops.center_on_selection()

    def _frame_scene_bounds(self, bounds: QRectF | None) -> bool:
        return self._view_nav_ops.frame_scene_bounds(bounds)

    @staticmethod
    def _graph_search_rank(
        query: str,
        *,
        title: str,
        display_name: str,
        type_id: str,
        node_id: str,
    ) -> int | None:
        return WorkspaceViewNavOps.graph_search_rank(
            query,
            title=title,
            display_name=display_name,
            type_id=type_id,
            node_id=node_id,
        )

    def search_graph_nodes(self, query: str, limit: int = _GRAPH_SEARCH_LIMIT) -> list[dict[str, Any]]:
        return self._view_nav_ops.search_graph_nodes(query, limit)

    def jump_to_graph_node(self, workspace_id: str, node_id: str) -> bool:
        return self._view_nav_ops.jump_to_graph_node(workspace_id, node_id)

    def create_view(self) -> None:
        self._view_nav_ops.create_view()

    def switch_view(self, view_id: str) -> None:
        self._view_nav_ops.switch_view(view_id)

    def create_workspace(self) -> None:
        from PyQt6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(self._host, "New Workspace", "Workspace name:")
        if not ok:
            return
        workspace_id = self._host.workspace_manager.create_workspace(name=name or None)
        self._host.runtime_history.clear_workspace(workspace_id)
        self.refresh_workspace_tabs()
        self.switch_workspace(workspace_id)

    def rename_active_workspace(self) -> None:
        from PyQt6.QtWidgets import QInputDialog

        index = self._host.workspace_tabs.currentIndex()
        if index < 0:
            return
        workspace_id = self._host.workspace_tabs.tabData(index)
        if not workspace_id:
            return
        workspace = self._host.model.project.workspaces[workspace_id]
        name, ok = QInputDialog.getText(self._host, "Rename Workspace", "New name:", text=workspace.name)
        if ok and name.strip():
            self._host.workspace_manager.rename_workspace(workspace_id, name.strip())
            self.refresh_workspace_tabs()

    def duplicate_active_workspace(self) -> None:
        index = self._host.workspace_tabs.currentIndex()
        if index < 0:
            return
        workspace_id = self._host.workspace_tabs.tabData(index)
        if not workspace_id:
            return
        duplicated_id = self._host.workspace_manager.duplicate_workspace(workspace_id)
        self._host.runtime_history.clear_workspace(duplicated_id)
        self.refresh_workspace_tabs()
        self.switch_workspace(duplicated_id)

    def close_active_workspace(self) -> None:
        index = self._host.workspace_tabs.currentIndex()
        if index >= 0:
            self.on_workspace_tab_close(index)

    def on_workspace_tab_changed(self, index: int) -> None:
        if index < 0:
            return
        workspace_id = self._host.workspace_tabs.tabData(index)
        if workspace_id:
            self.switch_workspace(workspace_id)

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
        self.refresh_workspace_tabs()
        self.switch_workspace(self._host.workspace_manager.active_workspace_id())

    def add_node_from_library(self, type_id: str) -> None:
        center = self._host.view.mapToScene(self._host.view.viewport().rect().center())
        if self.insert_library_node(type_id, center.x(), center.y()):
            self.refresh_workspace_tabs()

    def insert_library_node(self, type_id: str, x: float, y: float) -> str:
        return self._drop_connect_ops.insert_library_node(type_id, x, y)

    def _insert_custom_workflow_snapshot(self, workflow_id: str, x: float, y: float) -> str:
        return self._drop_connect_ops._insert_custom_workflow_snapshot(workflow_id, x, y)

    @staticmethod
    def _normalize_custom_workflow_fragment_payload(fragment_payload: Any) -> dict[str, Any] | None:
        return WorkspaceDropConnectOps._normalize_custom_workflow_fragment_payload(fragment_payload)

    @staticmethod
    def _retarget_fragment_roots(
        fragment_payload: dict[str, Any],
        *,
        target_parent_id: str | None,
    ) -> dict[str, Any]:
        return WorkspaceDropConnectOps._retarget_fragment_roots(
            fragment_payload,
            target_parent_id=target_parent_id,
        )

    @staticmethod
    def _find_inserted_root_subnode_shell_id(
        workspace_nodes: dict[str, NodeInstance],
        inserted_node_ids: set[str],
    ) -> str:
        return WorkspaceDropConnectOps._find_inserted_root_subnode_shell_id(workspace_nodes, inserted_node_ids)

    def active_workspace(self):
        workspace_id = self._host.workspace_manager.active_workspace_id()
        return self._host.model.project.workspaces.get(workspace_id)

    def clipboard_fragment_signature(self) -> str:
        return self._last_clipboard_fragment_signature

    def set_clipboard_fragment_signature(self, signature: str) -> None:
        self._last_clipboard_fragment_signature = str(signature or "")

    def clipboard_paste_count(self) -> int:
        return int(self._clipboard_paste_count)

    def set_clipboard_paste_count(self, count: int) -> None:
        self._clipboard_paste_count = max(0, int(count))

    def prompt_connection_candidate(
        self,
        *,
        title: str,
        label: str,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        return pick_connection_candidate(
            parent=self._host,
            title=title,
            label=label,
            candidates=candidates,
        )

    def auto_connect_dropped_node_to_port(
        self,
        new_node_id: str,
        target_node_id: str,
        target_port_key: str,
    ) -> bool:
        return self._drop_connect_ops.auto_connect_dropped_node_to_port(
            new_node_id,
            target_node_id,
            target_port_key,
        )

    def auto_connect_dropped_node_to_edge(self, new_node_id: str, target_edge_id: str) -> bool:
        return self._drop_connect_ops.auto_connect_dropped_node_to_edge(new_node_id, target_edge_id)

    def on_scene_node_selected(self, node_id: str) -> None:
        workspace = self._host.model.project.workspaces[self._host.workspace_manager.active_workspace_id()]
        node = workspace.nodes.get(node_id)
        self._host.script_editor.set_node(node)
        if self._host.script_editor.visible:
            self._host.script_editor.focus_editor()
        self._host.selected_node_changed.emit()

    def on_node_property_changed(self, node_id: str, key: str, value: Any) -> None:
        self._edit_ops.on_node_property_changed(node_id, key, value)

    @staticmethod
    def _is_direct_child_pin_node(
        node: NodeInstance | None,
        workspace_nodes: dict[str, NodeInstance],
    ) -> bool:
        return WorkspaceEditOps._is_direct_child_pin_node(node, workspace_nodes)

    def on_port_exposed_changed(self, node_id: str, key: str, exposed: bool) -> None:
        self._edit_ops.on_port_exposed_changed(node_id, key, exposed)

    def on_node_collapse_changed(self, node_id: str, collapsed: bool) -> None:
        self._edit_ops.on_node_collapse_changed(node_id, collapsed)

    def connect_selected_nodes(self) -> None:
        self._edit_ops.connect_selected_nodes()

    def duplicate_selected_nodes(self) -> bool:
        return self._edit_ops.duplicate_selected_nodes()

    def group_selected_nodes(self) -> bool:
        return self._edit_ops.group_selected_nodes()

    def ungroup_selected_nodes(self) -> bool:
        return self._edit_ops.ungroup_selected_nodes()

    def _run_layout_action(self, action: str | None = None, orientation: str | None = None) -> bool:
        return self._edit_ops.run_layout_action(action, orientation)

    def _selected_node_bounds_payload(self) -> list[tuple[float, float, float, float]]:
        return self._edit_ops.selected_node_bounds_payload()

    @staticmethod
    def _rectangles_overlap(
        first: tuple[float, float, float, float],
        second: tuple[float, float, float, float],
    ) -> bool:
        return WorkspaceEditOps.rectangles_overlap(first, second)

    def _count_overlap_pairs(self, bounds_payload: list[tuple[float, float, float, float]]) -> int:
        return self._edit_ops.count_overlap_pairs(bounds_payload)

    def align_selection_left(self) -> bool:
        return self._edit_ops.align_selection_left()

    def align_selection_right(self) -> bool:
        return self._edit_ops.align_selection_right()

    def align_selection_top(self) -> bool:
        return self._edit_ops.align_selection_top()

    def align_selection_bottom(self) -> bool:
        return self._edit_ops.align_selection_bottom()

    def distribute_selection_horizontally(self) -> bool:
        return self._edit_ops.distribute_selection_horizontally()

    def distribute_selection_vertically(self) -> bool:
        return self._edit_ops.distribute_selection_vertically()

    def _clipboard(self):
        return self._edit_ops.clipboard()

    def _write_graph_fragment_to_clipboard(self, fragment_payload: dict[str, Any]) -> bool:
        return self._edit_ops.write_graph_fragment_to_clipboard(fragment_payload)

    def _read_graph_fragment_from_clipboard(self) -> dict[str, Any] | None:
        return self._edit_ops.read_graph_fragment_from_clipboard()

    def copy_selected_nodes_to_clipboard(self) -> bool:
        return self._edit_ops.copy_selected_nodes_to_clipboard()

    def cut_selected_nodes_to_clipboard(self) -> bool:
        return self._edit_ops.cut_selected_nodes_to_clipboard()

    def paste_nodes_from_clipboard(self) -> bool:
        return self._edit_ops.paste_nodes_from_clipboard()

    def undo(self) -> bool:
        return self._edit_ops.undo()

    def redo(self) -> bool:
        return self._edit_ops.redo()

    def request_drop_node_from_library(
        self,
        type_id: str,
        scene_x: float,
        scene_y: float,
        target_mode: str,
        target_node_id: str,
        target_port_key: str,
        target_edge_id: str,
    ) -> ControllerResult[bool]:
        return self._drop_connect_ops.request_drop_node_from_library(
            type_id,
            scene_x,
            scene_y,
            target_mode,
            target_node_id,
            target_port_key,
            target_edge_id,
        )

    def request_connect_ports(self, node_a_id: str, port_a: str, node_b_id: str, port_b: str) -> ControllerResult[bool]:
        return self._edit_ops.request_connect_ports(node_a_id, port_a, node_b_id, port_b)

    def request_remove_edge(self, edge_id: str) -> ControllerResult[bool]:
        return self._edit_ops.request_remove_edge(edge_id)

    def request_remove_node(self, node_id: str) -> ControllerResult[bool]:
        return self._edit_ops.request_remove_node(node_id)

    def request_rename_node(self, node_id: str) -> ControllerResult[bool]:
        return self._edit_ops.request_rename_node(node_id)

    def request_delete_selected_graph_items(self, edge_ids: list[Any]) -> ControllerResult[bool]:
        return self._edit_ops.request_delete_selected_graph_items(edge_ids)

    def focus_failed_node(self, workspace_id: str, node_id: str, error: str) -> None:
        self._view_nav_ops.focus_failed_node(workspace_id, node_id, error)

    def reveal_parent_chain(self, workspace_id: str, node_id: str) -> list[str]:
        return self._view_nav_ops.reveal_parent_chain(workspace_id, node_id)

    @staticmethod
    def _custom_workflow_export_label(definition: dict[str, Any]) -> str:
        return WorkspaceIOOps.custom_workflow_export_label(definition)

    @staticmethod
    def _custom_workflow_default_filename(name: object) -> str:
        return WorkspaceIOOps.custom_workflow_default_filename(name)

    def import_custom_workflow(self) -> None:
        self._io_ops.import_custom_workflow()

    def export_custom_workflow(self) -> None:
        self._io_ops.export_custom_workflow()

    def _prompt_custom_workflow_export_definition(self, definitions: list[dict[str, Any]]) -> dict[str, Any] | None:
        return self._io_ops.prompt_custom_workflow_export_definition(definitions)

    def import_node_package(self) -> None:
        self._io_ops.import_node_package()

    def export_node_package(self) -> None:
        self._io_ops.export_node_package()
