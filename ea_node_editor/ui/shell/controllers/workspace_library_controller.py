from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any
from pathlib import Path

from PyQt6.QtCore import QMimeData, QRectF, Qt

from ea_node_editor.custom_workflows import (
    CUSTOM_WORKFLOW_FILE_EXTENSION,
    custom_workflow_library_items,
    export_custom_workflow_file,
    import_custom_workflow_file,
    normalize_custom_workflow_metadata,
    upsert_custom_workflow_definition,
)
from ea_node_editor.graph.effective_ports import is_subnode_pin_type
from ea_node_editor.graph.hierarchy import scope_parent_id
from ea_node_editor.graph.model import NodeInstance
from ea_node_editor.graph.transforms import (
    build_subnode_custom_workflow_snapshot_data,
)
from ea_node_editor.nodes.builtins.subnode import (
    SUBNODE_PIN_DATA_TYPE_PROPERTY,
    SUBNODE_PIN_KIND_PROPERTY,
    SUBNODE_PIN_LABEL_PROPERTY,
    SUBNODE_TYPE_ID,
)
from ea_node_editor.nodes.types import NodeTypeSpec
from ea_node_editor.ui.shell.runtime_clipboard import (
    GRAPH_FRAGMENT_MIME_TYPE,
    build_graph_fragment_payload,
    normalize_graph_fragment_payload,
    parse_graph_fragment_payload,
    serialize_graph_fragment_payload,
)
from ea_node_editor.ui.shell.inspector_flow import coerce_editor_input_value
from ea_node_editor.ui.shell.library_flow import pick_connection_candidate
from ea_node_editor.ui.shell.controllers.workspace_drop_connect_ops import WorkspaceDropConnectOps
from ea_node_editor.ui.shell.controllers.result import ControllerResult
from ea_node_editor.ui.shell.controllers.workspace_view_nav_ops import WorkspaceViewNavOps

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow

_GRAPH_SEARCH_LIMIT = 10
_PASTE_CASCADE_OFFSET_X = 40.0
_PASTE_CASCADE_OFFSET_Y = 40.0
_PIN_REFRESH_PROPERTIES = {
    SUBNODE_PIN_LABEL_PROPERTY,
    SUBNODE_PIN_KIND_PROPERTY,
    SUBNODE_PIN_DATA_TYPE_PROPERTY,
}
_CUSTOM_WORKFLOW_DESCRIPTION = "Project-local custom workflow snapshot."


class WorkspaceLibraryController:
    def __init__(self, host: ShellWindow) -> None:
        self._host = host
        self._view_nav_ops = WorkspaceViewNavOps(host, self)
        self._drop_connect_ops = WorkspaceDropConnectOps(host, self)
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
        selected = self.selected_node_context()
        if selected is None:
            return
        node, spec = selected
        property_spec = next((prop for prop in spec.properties if prop.key == key), None)
        if property_spec is None:
            return
        coerced = coerce_editor_input_value(property_spec.type, value, property_spec.default)
        self.on_node_property_changed(node.node_id, property_spec.key, coerced)

    def set_selected_port_exposed(self, key: str, exposed: bool) -> None:
        selected = self.selected_node_context()
        if selected is None:
            return
        node, _spec = selected
        self.on_port_exposed_changed(node.node_id, str(key), bool(exposed))

    def set_selected_node_collapsed(self, collapsed: bool) -> None:
        selected = self.selected_node_context()
        if selected is None:
            return
        node, spec = selected
        if not spec.collapsible:
            return
        self.on_node_collapse_changed(node.node_id, bool(collapsed))

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
        self._host.scene.set_node_property(node_id, key, value)
        workspace = self.active_workspace()
        should_refresh_shell_payload = (
            workspace is not None
            and str(key) in _PIN_REFRESH_PROPERTIES
            and self._is_direct_child_pin_node(workspace.nodes.get(node_id), workspace.nodes)
        )
        if should_refresh_shell_payload and workspace is not None:
            self._host.scene.refresh_workspace_from_model(workspace.workspace_id)
        if key == "script" and self._host.script_editor.current_node_id == node_id:
            workspace = self._host.model.project.workspaces[self._host.workspace_manager.active_workspace_id()]
            self._host.script_editor.set_node(workspace.nodes.get(node_id))
        self._host.selected_node_changed.emit()
        self.refresh_workspace_tabs()

    @staticmethod
    def _is_direct_child_pin_node(
        node: NodeInstance | None,
        workspace_nodes: dict[str, NodeInstance],
    ) -> bool:
        if node is None or not is_subnode_pin_type(node.type_id):
            return False
        parent_node_id = str(node.parent_node_id or "").strip()
        if not parent_node_id:
            return False
        parent_node = workspace_nodes.get(parent_node_id)
        if parent_node is None:
            return False
        return parent_node.type_id == SUBNODE_TYPE_ID

    def on_port_exposed_changed(self, node_id: str, key: str, exposed: bool) -> None:
        self._host.scene.set_exposed_port(node_id, key, exposed)
        self._host.selected_node_changed.emit()
        self.refresh_workspace_tabs()

    def on_node_collapse_changed(self, node_id: str, collapsed: bool) -> None:
        self._host.scene.set_node_collapsed(node_id, collapsed)
        self._host.selected_node_changed.emit()
        self.refresh_workspace_tabs()

    def connect_selected_nodes(self) -> None:
        from PyQt6.QtWidgets import QMessageBox

        selected = [item for item in self._host.scene.selectedItems() if hasattr(item, "node")]
        if len(selected) != 2:
            QMessageBox.information(self._host, "Connect", "Select exactly two nodes to connect.")
            return
        first_item = selected[0]
        second_item = selected[1]
        try:
            self._host.scene.connect_nodes(first_item.node.node_id, second_item.node.node_id)
        except (KeyError, ValueError):
            QMessageBox.warning(self._host, "Connect", "No compatible ports found on selected nodes.")
            return
        self.refresh_workspace_tabs()

    def duplicate_selected_nodes(self) -> bool:
        duplicated = bool(self._host.scene.duplicate_selected_subgraph())
        if not duplicated:
            return False
        self._host.selected_node_changed.emit()
        self.refresh_workspace_tabs()
        return True

    def group_selected_nodes(self) -> bool:
        grouped = bool(self._host.scene.group_selected_nodes())
        if not grouped:
            return False
        self._host.selected_node_changed.emit()
        self.refresh_workspace_tabs()
        return True

    def ungroup_selected_nodes(self) -> bool:
        ungrouped = bool(self._host.scene.ungroup_selected_subnode())
        if not ungrouped:
            return False
        self._host.selected_node_changed.emit()
        self.refresh_workspace_tabs()
        return True

    def _run_layout_action(self, action: str | None = None, orientation: str | None = None) -> bool:
        before_overlap_pairs = 0
        normalized_action = str(action).strip().lower() if action is not None else None
        if normalized_action is not None:
            before_overlap_pairs = self._count_overlap_pairs(self._selected_node_bounds_payload())

        snap_enabled = bool(self._host.snap_to_grid_enabled)
        if normalized_action is not None:
            moved = bool(self._host.scene.align_selected_nodes(normalized_action, snap_to_grid=snap_enabled))
        else:
            moved = bool(self._host.scene.distribute_selected_nodes(orientation, snap_to_grid=snap_enabled))
        if not moved:
            return False

        if normalized_action is not None:
            after_overlap_pairs = self._count_overlap_pairs(self._selected_node_bounds_payload())
            created_overlap_pairs = max(0, after_overlap_pairs - before_overlap_pairs)
            if created_overlap_pairs > 0:
                tidy_action = "Distribute Vertically" if normalized_action in {"left", "right"} else "Distribute Horizontally"
                overlap_word = "overlap" if created_overlap_pairs == 1 else "overlaps"
                self._host.show_graph_hint(
                    f"{created_overlap_pairs} {overlap_word} created. Press {tidy_action} to tidy."
                )

        self._host.selected_node_changed.emit()
        self.refresh_workspace_tabs()
        return True

    def _selected_node_bounds_payload(self) -> list[tuple[float, float, float, float]]:
        bounds_payload: list[tuple[float, float, float, float]] = []
        for node_payload in self._host.scene.nodes_model:
            if not bool(node_payload.get("selected", False)):
                continue
            width = float(node_payload.get("width", 0.0))
            height = float(node_payload.get("height", 0.0))
            if width <= 0.0 or height <= 0.0:
                continue
            x = float(node_payload.get("x", 0.0))
            y = float(node_payload.get("y", 0.0))
            bounds_payload.append((x, y, x + width, y + height))
        return bounds_payload

    @staticmethod
    def _rectangles_overlap(
        first: tuple[float, float, float, float],
        second: tuple[float, float, float, float],
    ) -> bool:
        return (
            first[0] < second[2]
            and first[2] > second[0]
            and first[1] < second[3]
            and first[3] > second[1]
        )

    def _count_overlap_pairs(self, bounds_payload: list[tuple[float, float, float, float]]) -> int:
        overlap_pairs = 0
        for left_index in range(len(bounds_payload)):
            for right_index in range(left_index + 1, len(bounds_payload)):
                if self._rectangles_overlap(bounds_payload[left_index], bounds_payload[right_index]):
                    overlap_pairs += 1
        return overlap_pairs

    def align_selection_left(self) -> bool:
        return self._run_layout_action("left")

    def align_selection_right(self) -> bool:
        return self._run_layout_action("right")

    def align_selection_top(self) -> bool:
        return self._run_layout_action("top")

    def align_selection_bottom(self) -> bool:
        return self._run_layout_action("bottom")

    def distribute_selection_horizontally(self) -> bool:
        return self._run_layout_action(orientation="horizontal")

    def distribute_selection_vertically(self) -> bool:
        return self._run_layout_action(orientation="vertical")

    def _clipboard(self):
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return None
        return app.clipboard()

    def _write_graph_fragment_to_clipboard(self, fragment_payload: dict[str, Any]) -> bool:
        serialized = serialize_graph_fragment_payload(fragment_payload)
        if serialized is None:
            return False
        clipboard = self._clipboard()
        if clipboard is None:
            return False
        mime_data = QMimeData()
        mime_data.setData(GRAPH_FRAGMENT_MIME_TYPE, serialized.encode("utf-8"))
        clipboard.setMimeData(mime_data)
        return True

    def _read_graph_fragment_from_clipboard(self) -> dict[str, Any] | None:
        clipboard = self._clipboard()
        if clipboard is None:
            return None
        mime_data = clipboard.mimeData()
        if mime_data is None:
            return None
        if mime_data.hasFormat(GRAPH_FRAGMENT_MIME_TYPE):
            raw_data = bytes(mime_data.data(GRAPH_FRAGMENT_MIME_TYPE))
            try:
                serialized = raw_data.decode("utf-8")
            except UnicodeDecodeError:
                return None
            payload = parse_graph_fragment_payload(serialized)
            if payload is not None:
                return payload
        return parse_graph_fragment_payload(mime_data.text())

    def copy_selected_nodes_to_clipboard(self) -> bool:
        fragment_payload = self._host.scene.serialize_selected_subgraph_fragment()
        if fragment_payload is None:
            return False
        copied = self._write_graph_fragment_to_clipboard(fragment_payload)
        if not copied:
            return False
        self._last_clipboard_fragment_signature = (
            serialize_graph_fragment_payload(fragment_payload) or ""
        )
        self._clipboard_paste_count = 0
        return True

    def cut_selected_nodes_to_clipboard(self) -> bool:
        if not self.copy_selected_nodes_to_clipboard():
            return False
        return bool(self.request_delete_selected_graph_items([]).payload)

    def paste_nodes_from_clipboard(self) -> bool:
        fragment_payload = self._read_graph_fragment_from_clipboard()
        if fragment_payload is None:
            return False
        fragment_signature = serialize_graph_fragment_payload(fragment_payload)
        if fragment_signature is None:
            return False
        if fragment_signature != self._last_clipboard_fragment_signature:
            self._last_clipboard_fragment_signature = fragment_signature
            self._clipboard_paste_count = 0
        cascade_x = float(self._clipboard_paste_count) * _PASTE_CASCADE_OFFSET_X
        cascade_y = float(self._clipboard_paste_count) * _PASTE_CASCADE_OFFSET_Y
        center = self._host.view.mapToScene(self._host.view.viewport().rect().center())
        pasted = bool(
            self._host.scene.paste_subgraph_fragment(
                fragment_payload,
                center.x() + cascade_x,
                center.y() + cascade_y,
            )
        )
        if not pasted:
            return False
        self._clipboard_paste_count += 1
        self._host.selected_node_changed.emit()
        self.refresh_workspace_tabs()
        return True

    def undo(self) -> bool:
        workspace_id = self._host.workspace_manager.active_workspace_id()
        workspace = self._host.model.project.workspaces.get(workspace_id)
        if workspace is None:
            return False
        entry = self._host.runtime_history.undo_workspace(workspace_id, workspace)
        if entry is None:
            return False
        self._host.scene.refresh_workspace_from_model(workspace_id)
        self.refresh_workspace_tabs()
        return True

    def redo(self) -> bool:
        workspace_id = self._host.workspace_manager.active_workspace_id()
        workspace = self._host.model.project.workspaces.get(workspace_id)
        if workspace is None:
            return False
        entry = self._host.runtime_history.redo_workspace(workspace_id, workspace)
        if entry is None:
            return False
        self._host.scene.refresh_workspace_from_model(workspace_id)
        self.refresh_workspace_tabs()
        return True

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
        result = self._host._graph_interactions.connect_ports(node_a_id, port_a, node_b_id, port_b)
        if result.ok:
            self.refresh_workspace_tabs()
        return ControllerResult(result.ok, result.message, payload=result.ok)

    def request_remove_edge(self, edge_id: str) -> ControllerResult[bool]:
        result = self._host._graph_interactions.remove_edge(edge_id)
        if result.ok:
            self.refresh_workspace_tabs()
        return ControllerResult(result.ok, result.message, payload=result.ok)

    def request_remove_node(self, node_id: str) -> ControllerResult[bool]:
        result = self._host._graph_interactions.remove_node(node_id)
        if result.ok:
            self._host.selected_node_changed.emit()
            self.refresh_workspace_tabs()
        return ControllerResult(result.ok, result.message, payload=result.ok)

    def request_rename_node(self, node_id: str) -> ControllerResult[bool]:
        from PyQt6.QtWidgets import QInputDialog

        workspace = self._host.model.project.workspaces.get(self._host.workspace_manager.active_workspace_id())
        if workspace is None:
            return ControllerResult(False, payload=False)
        node = workspace.nodes.get(str(node_id).strip())
        if node is None:
            return ControllerResult(False, payload=False)
        new_title, ok = QInputDialog.getText(self._host, "Rename Node", "New name:", text=node.title)
        if not ok:
            return ControllerResult(False, payload=False)
        result = self._host._graph_interactions.rename_node(node.node_id, new_title)
        if result.ok:
            self._host.selected_node_changed.emit()
            self.refresh_workspace_tabs()
        return ControllerResult(result.ok, result.message, payload=result.ok)

    def request_delete_selected_graph_items(self, edge_ids: list[Any]) -> ControllerResult[bool]:
        result = self._host._graph_interactions.delete_selected_items(edge_ids)
        if result.ok:
            self._host.selected_node_changed.emit()
            self.refresh_workspace_tabs()
        return ControllerResult(result.ok, result.message, payload=result.ok)

    def focus_failed_node(self, workspace_id: str, node_id: str, error: str) -> None:
        self._view_nav_ops.focus_failed_node(workspace_id, node_id, error)

    def reveal_parent_chain(self, workspace_id: str, node_id: str) -> list[str]:
        return self._view_nav_ops.reveal_parent_chain(workspace_id, node_id)

    @staticmethod
    def _custom_workflow_export_label(definition: dict[str, Any]) -> str:
        name = str(definition.get("name", "")).strip() or "Custom Workflow"
        revision = int(definition.get("revision", 1))
        return f"{name} (rev {revision})"

    @staticmethod
    def _custom_workflow_default_filename(name: object) -> str:
        normalized_name = str(name).strip()
        if not normalized_name:
            normalized_name = "custom_workflow"
        invalid_chars = '<>:"/\\|?*'
        safe_name = "".join("_" if character in invalid_chars else character for character in normalized_name)
        safe_name = safe_name.strip().strip(".")
        if not safe_name:
            safe_name = "custom_workflow"
        return f"{safe_name}{CUSTOM_WORKFLOW_FILE_EXTENSION}"

    def import_custom_workflow(self) -> None:
        from PyQt6.QtWidgets import QFileDialog, QMessageBox

        path, _ = QFileDialog.getOpenFileName(
            self._host,
            "Import Custom Workflow",
            "",
            "Custom Workflow (*.eawf)",
        )
        if not path:
            return
        try:
            imported_definition = import_custom_workflow_file(Path(path))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self._host, "Import Failed", f"Could not import custom workflow.\n{exc}")
            return

        definitions = self._custom_workflow_definitions()
        workflow_id = imported_definition["workflow_id"]
        replaced_existing = False
        for index, definition in enumerate(definitions):
            if definition["workflow_id"] != workflow_id:
                continue
            definitions[index] = imported_definition
            replaced_existing = True
            break
        if not replaced_existing:
            definitions.append(imported_definition)

        self._set_custom_workflow_definitions(definitions)
        self._host.project_meta_changed.emit()
        self._host.node_library_changed.emit()
        action = "Updated" if replaced_existing else "Imported"
        QMessageBox.information(
            self._host,
            "Import Successful",
            f"{action} custom workflow '{imported_definition['name']}' (rev {imported_definition['revision']}).",
        )

    def export_custom_workflow(self) -> None:
        from PyQt6.QtWidgets import QFileDialog, QMessageBox

        definitions = sorted(
            self._custom_workflow_definitions(),
            key=lambda definition: (
                str(definition.get("name", "")).lower(),
                str(definition.get("workflow_id", "")).lower(),
            ),
        )
        if not definitions:
            QMessageBox.information(self._host, "Export Custom Workflow", "No custom workflows are available to export.")
            return

        selected_definition = self._prompt_custom_workflow_export_definition(definitions)
        if selected_definition is None:
            return
        default_name = self._custom_workflow_default_filename(selected_definition.get("name"))
        path, _ = QFileDialog.getSaveFileName(
            self._host,
            "Export Custom Workflow",
            default_name,
            "Custom Workflow (*.eawf)",
        )
        if not path:
            return
        try:
            saved_path = export_custom_workflow_file(selected_definition, Path(path))
            QMessageBox.information(self._host, "Export Successful", f"Custom workflow saved to {saved_path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self._host, "Export Failed", f"Could not export custom workflow.\n{exc}")

    def _prompt_custom_workflow_export_definition(self, definitions: list[dict[str, Any]]) -> dict[str, Any] | None:
        from PyQt6.QtWidgets import (
            QDialog,
            QDialogButtonBox,
            QLabel,
            QListWidget,
            QListWidgetItem,
            QVBoxLayout,
        )

        if not definitions:
            return None
        if len(definitions) == 1:
            return definitions[0]

        dialog = QDialog(self._host)
        dialog.setWindowTitle("Export Custom Workflow")
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Workflow:", dialog))

        list_widget = QListWidget(dialog)
        for index, definition in enumerate(definitions):
            item = QListWidgetItem(self._custom_workflow_export_label(definition))
            item.setData(Qt.ItemDataRole.UserRole, index)
            list_widget.addItem(item)
        list_widget.setCurrentRow(0)
        list_widget.itemDoubleClicked.connect(lambda _item: dialog.accept())
        layout.addWidget(list_widget)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != int(QDialog.DialogCode.Accepted):
            return None
        current_item = list_widget.currentItem()
        if current_item is None:
            return None
        try:
            selected_index = int(current_item.data(Qt.ItemDataRole.UserRole))
        except (TypeError, ValueError):
            return None
        if selected_index < 0 or selected_index >= len(definitions):
            return None
        return definitions[selected_index]

    def import_node_package(self) -> None:
        from PyQt6.QtWidgets import QFileDialog, QMessageBox

        from ea_node_editor.nodes.package_manager import import_package
        from ea_node_editor.nodes.plugin_loader import discover_and_load_plugins

        path, _ = QFileDialog.getOpenFileName(
            self._host, "Import Node Package", "", "Node Package (*.eanp)"
        )
        if not path:
            return
        try:
            manifest = import_package(Path(path))
            discover_and_load_plugins(self._host.registry)
            self._host.node_library_changed.emit()
            QMessageBox.information(
                self._host,
                "Import Successful",
                f"Installed '{manifest.name}' v{manifest.version} "
                f"with {len(manifest.nodes)} node(s).\n\n"
                "The nodes are now available in the Node Library.",
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self._host, "Import Failed", f"Could not import package.\n{exc}")

    def export_node_package(self) -> None:
        from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

        from ea_node_editor.nodes.package_manager import PackageManifest, export_package

        name, ok = QInputDialog.getText(self._host, "Export Node Package", "Package name:")
        if not ok or not name.strip():
            return
        path, _ = QFileDialog.getSaveFileName(
            self._host, "Export Node Package", f"{name.strip()}.eanp", "Node Package (*.eanp)"
        )
        if not path:
            return
        manifest = PackageManifest(
            name=name.strip(),
            nodes=[spec.type_id for spec in self._host.registry.all_specs()],
        )
        try:
            export_package([], manifest, Path(path))
            QMessageBox.information(self._host, "Export Successful", f"Package saved to {path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self._host, "Export Failed", f"Could not export package.\n{exc}")
