from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from PyQt6.QtCore import QMimeData

from ea_node_editor.graph.effective_ports import is_subnode_pin_type
from ea_node_editor.graph.model import NodeInstance
from ea_node_editor.nodes.builtins.subnode import (
    SUBNODE_INPUT_TYPE_ID,
    SUBNODE_OUTPUT_TYPE_ID,
    SUBNODE_PIN_DATA_TYPE_PROPERTY,
    SUBNODE_PIN_KIND_PROPERTY,
    SUBNODE_PIN_LABEL_PROPERTY,
    SUBNODE_TYPE_ID,
)
from ea_node_editor.ui.shell.controllers.result import ControllerResult
from ea_node_editor.ui.shell.inspector_flow import coerce_editor_input_value
from ea_node_editor.ui.shell.runtime_clipboard import (
    GRAPH_FRAGMENT_MIME_TYPE,
    parse_graph_fragment_payload,
    serialize_graph_fragment_payload,
)

if TYPE_CHECKING:
    from ea_node_editor.nodes.types import NodeTypeSpec
    from ea_node_editor.ui.shell.window import ShellWindow

_PASTE_CASCADE_OFFSET_X = 40.0
_PASTE_CASCADE_OFFSET_Y = 40.0
_PIN_REFRESH_PROPERTIES = {
    SUBNODE_PIN_LABEL_PROPERTY,
    SUBNODE_PIN_KIND_PROPERTY,
    SUBNODE_PIN_DATA_TYPE_PROPERTY,
}


class _WorkspaceEditControllerProtocol(Protocol):
    def selected_node_context(self) -> tuple[NodeInstance, NodeTypeSpec] | None: ...

    def active_workspace(self): ...

    def on_node_property_changed(self, node_id: str, key: str, value: Any) -> None: ...

    def on_port_exposed_changed(self, node_id: str, key: str, exposed: bool) -> None: ...

    def on_node_collapse_changed(self, node_id: str, collapsed: bool) -> None: ...

    def refresh_workspace_tabs(self) -> None: ...

    def _write_graph_fragment_to_clipboard(self, fragment_payload: dict[str, Any]) -> bool: ...

    def _read_graph_fragment_from_clipboard(self) -> dict[str, Any] | None: ...

    def copy_selected_nodes_to_clipboard(self) -> bool: ...

    def request_delete_selected_graph_items(self, edge_ids: list[Any]) -> ControllerResult[bool]: ...

    def clipboard_fragment_signature(self) -> str: ...

    def set_clipboard_fragment_signature(self, signature: str) -> None: ...

    def clipboard_paste_count(self) -> int: ...

    def set_clipboard_paste_count(self, count: int) -> None: ...


class WorkspaceEditOps:
    def __init__(
        self,
        host: ShellWindow,
        controller: _WorkspaceEditControllerProtocol,
    ) -> None:
        self._host = host
        self._controller = controller

    @property
    def _graph_interactions(self):
        graph_interactions = getattr(self._host, "graph_interactions", None)
        if graph_interactions is not None:
            return graph_interactions
        return self._host._graph_interactions

    def set_selected_node_property(self, key: str, value: Any) -> None:
        selected = self._controller.selected_node_context()
        if selected is None:
            return
        node, spec = selected
        property_spec = next((prop for prop in spec.properties if prop.key == key), None)
        if property_spec is None:
            return
        coerced = coerce_editor_input_value(property_spec.type, value, property_spec.default)
        self._controller.on_node_property_changed(node.node_id, property_spec.key, coerced)

    def set_selected_port_exposed(self, key: str, exposed: bool) -> None:
        selected = self._controller.selected_node_context()
        if selected is None:
            return
        node, _spec = selected
        self._controller.on_port_exposed_changed(node.node_id, str(key), bool(exposed))

    def set_selected_node_collapsed(self, collapsed: bool) -> None:
        selected = self._controller.selected_node_context()
        if selected is None:
            return
        node, spec = selected
        if not spec.collapsible:
            return
        self._controller.on_node_collapse_changed(node.node_id, bool(collapsed))

    def request_add_selected_subnode_pin(self, direction: str) -> ControllerResult[str]:
        selected = self._controller.selected_node_context()
        if selected is None:
            return ControllerResult(False, "No node selected.", payload="")
        node, _spec = selected
        if node.type_id != SUBNODE_TYPE_ID:
            return ControllerResult(False, "Selected node is not a subnode shell.", payload="")

        normalized_direction = str(direction).strip().lower()
        if normalized_direction == "in":
            pin_type_id = SUBNODE_INPUT_TYPE_ID
        elif normalized_direction == "out":
            pin_type_id = SUBNODE_OUTPUT_TYPE_ID
        else:
            return ControllerResult(False, "Unknown subnode port direction.", payload="")

        created_node_id = self._host.scene.add_subnode_shell_pin(node.node_id, pin_type_id)
        if not created_node_id:
            return ControllerResult(False, "Subnode port could not be created.", payload="")
        self._host.selected_node_changed.emit()
        self._controller.refresh_workspace_tabs()
        return ControllerResult(True, payload=created_node_id)

    def _selected_shell_pin_node(self, key: str) -> NodeInstance | None:
        selected = self._controller.selected_node_context()
        if selected is None:
            return None
        node, _spec = selected
        if node.type_id != SUBNODE_TYPE_ID:
            return None

        workspace = self._controller.active_workspace()
        if workspace is None:
            return None

        port_node_id = str(key or "").strip()
        if not port_node_id:
            return None
        pin_node = workspace.nodes.get(port_node_id)
        if pin_node is None or not self._is_direct_child_pin_node(pin_node, workspace.nodes):
            return None
        if str(pin_node.parent_node_id or "").strip() != str(node.node_id):
            return None
        return pin_node

    def set_selected_port_label(self, key: str, label: Any) -> bool:
        pin_node = self._selected_shell_pin_node(key)
        if pin_node is not None:
            normalized_label = str(label or "").strip()
            if not normalized_label:
                return False
            current_label = str(pin_node.properties.get(SUBNODE_PIN_LABEL_PROPERTY, "")).strip()
            if not current_label:
                current_label = "Input" if pin_node.type_id == SUBNODE_INPUT_TYPE_ID else "Output"
            if normalized_label == current_label:
                return False
            self.on_node_property_changed(pin_node.node_id, SUBNODE_PIN_LABEL_PROPERTY, normalized_label)
            return True

        context = self._controller.selected_node_context()
        if context is None:
            return False
        node, spec = context
        port_key = str(key or "").strip()
        if not port_key:
            return False
        port_spec = next((p for p in spec.ports if p.key == port_key), None)
        if port_spec is None:
            return False
        if port_spec.kind in ("exec", "completed", "failed"):
            return False
        normalized_label = str(label or "").strip()
        default_label = port_spec.label or port_spec.key
        current_label = node.port_labels.get(port_key) or default_label
        if normalized_label == current_label:
            return False
        store_label = "" if normalized_label == default_label else normalized_label
        workspace = self._controller.active_workspace()
        if workspace is None:
            return False
        self._host.scene.set_port_label(workspace.workspace_id, node.node_id, port_key, store_label)
        self._host.selected_node_changed.emit()
        self._controller.refresh_workspace_tabs()
        return True

    def request_rename_selected_port(self, key: str) -> ControllerResult[bool]:
        from PyQt6.QtWidgets import QInputDialog

        pin_node = self._selected_shell_pin_node(key)
        if pin_node is None:
            return ControllerResult(False, "Subnode port not found.", payload=False)

        current_label = str(pin_node.properties.get(SUBNODE_PIN_LABEL_PROPERTY, "")).strip()
        if not current_label:
            current_label = "Input" if pin_node.type_id == SUBNODE_INPUT_TYPE_ID else "Output"
        new_label, ok = QInputDialog.getText(
            self._host,
            "Rename Port",
            "Port name:",
            text=current_label,
        )
        if not ok:
            return ControllerResult(False, payload=False)

        renamed = self.set_selected_port_label(key, new_label)
        if not renamed:
            normalized_label = str(new_label).strip()
            if not normalized_label:
                return ControllerResult(False, "Port name cannot be empty.", payload=False)
            return ControllerResult(False, payload=False)
        return ControllerResult(True, payload=True)

    def request_remove_selected_port(self, key: str) -> ControllerResult[bool]:
        pin_node = self._selected_shell_pin_node(key)
        if pin_node is None:
            return ControllerResult(False, "Subnode port not found.", payload=False)

        removed = bool(self._host.scene.remove_workspace_node(pin_node.node_id))
        if not removed:
            return ControllerResult(False, "Subnode port could not be removed.", payload=False)

        self._host.selected_node_changed.emit()
        self._controller.refresh_workspace_tabs()
        return ControllerResult(True, payload=True)

    def on_node_property_changed(self, node_id: str, key: str, value: Any) -> None:
        self._host.scene.set_node_property(node_id, key, value)
        workspace = self._controller.active_workspace()
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
        self._controller.refresh_workspace_tabs()

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
        self._controller.refresh_workspace_tabs()

    def on_node_collapse_changed(self, node_id: str, collapsed: bool) -> None:
        self._host.scene.set_node_collapsed(node_id, collapsed)
        self._host.selected_node_changed.emit()
        self._controller.refresh_workspace_tabs()

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
        self._controller.refresh_workspace_tabs()

    def duplicate_selected_nodes(self) -> bool:
        duplicated = bool(self._host.scene.duplicate_selected_subgraph())
        if not duplicated:
            return False
        self._host.selected_node_changed.emit()
        self._controller.refresh_workspace_tabs()
        return True

    def wrap_selected_nodes_in_comment_backdrop(self) -> bool:
        wrapped = bool(self._host.scene.wrap_selected_nodes_in_comment_backdrop())
        if not wrapped:
            return False
        self._host.selected_node_changed.emit()
        self._controller.refresh_workspace_tabs()
        return True

    def group_selected_nodes(self) -> bool:
        grouped = bool(self._host.scene.group_selected_nodes())
        if not grouped:
            return False
        self._host.selected_node_changed.emit()
        self._controller.refresh_workspace_tabs()
        return True

    def ungroup_selected_nodes(self) -> bool:
        ungrouped = bool(self._host.scene.ungroup_selected_subnode())
        if not ungrouped:
            return False
        self._host.selected_node_changed.emit()
        self._controller.refresh_workspace_tabs()
        return True

    def run_layout_action(self, action: str | None = None, orientation: str | None = None) -> bool:
        before_overlap_pairs = 0
        normalized_action = str(action).strip().lower() if action is not None else None
        if normalized_action is not None:
            before_overlap_pairs = self.count_overlap_pairs(self.selected_node_bounds_payload())

        snap_enabled = bool(self._host.snap_to_grid_enabled)
        if normalized_action is not None:
            moved = bool(self._host.scene.align_selected_nodes(normalized_action, snap_to_grid=snap_enabled))
        else:
            moved = bool(self._host.scene.distribute_selected_nodes(orientation, snap_to_grid=snap_enabled))
        if not moved:
            return False

        if normalized_action is not None:
            after_overlap_pairs = self.count_overlap_pairs(self.selected_node_bounds_payload())
            created_overlap_pairs = max(0, after_overlap_pairs - before_overlap_pairs)
            if created_overlap_pairs > 0:
                tidy_action = "Distribute Vertically" if normalized_action in {"left", "right"} else "Distribute Horizontally"
                overlap_word = "overlap" if created_overlap_pairs == 1 else "overlaps"
                self._host.show_graph_hint(
                    f"{created_overlap_pairs} {overlap_word} created. Press {tidy_action} to tidy."
                )

        self._host.selected_node_changed.emit()
        self._controller.refresh_workspace_tabs()
        return True

    def selected_node_bounds_payload(self) -> list[tuple[float, float, float, float]]:
        bounds_payload: list[tuple[float, float, float, float]] = []
        selected_node_lookup = self._host.scene.selected_node_lookup
        for node_payload in self._host.scene.nodes_model:
            node_id = str(node_payload.get("node_id", "")).strip()
            if not node_id or not bool(selected_node_lookup.get(node_id, False)):
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
    def rectangles_overlap(
        first: tuple[float, float, float, float],
        second: tuple[float, float, float, float],
    ) -> bool:
        return (
            first[0] < second[2]
            and first[2] > second[0]
            and first[1] < second[3]
            and first[3] > second[1]
        )

    def count_overlap_pairs(self, bounds_payload: list[tuple[float, float, float, float]]) -> int:
        overlap_pairs = 0
        for left_index in range(len(bounds_payload)):
            for right_index in range(left_index + 1, len(bounds_payload)):
                if self.rectangles_overlap(bounds_payload[left_index], bounds_payload[right_index]):
                    overlap_pairs += 1
        return overlap_pairs

    def align_selection_left(self) -> bool:
        return self.run_layout_action("left")

    def align_selection_right(self) -> bool:
        return self.run_layout_action("right")

    def align_selection_top(self) -> bool:
        return self.run_layout_action("top")

    def align_selection_bottom(self) -> bool:
        return self.run_layout_action("bottom")

    def distribute_selection_horizontally(self) -> bool:
        return self.run_layout_action(orientation="horizontal")

    def distribute_selection_vertically(self) -> bool:
        return self.run_layout_action(orientation="vertical")

    def clipboard(self):
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return None
        return app.clipboard()

    def write_graph_fragment_to_clipboard(self, fragment_payload: dict[str, Any]) -> bool:
        serialized = serialize_graph_fragment_payload(fragment_payload)
        if serialized is None:
            return False
        clipboard = self.clipboard()
        if clipboard is None:
            return False
        mime_data = QMimeData()
        mime_data.setData(GRAPH_FRAGMENT_MIME_TYPE, serialized.encode("utf-8"))
        clipboard.setMimeData(mime_data)
        return True

    def read_graph_fragment_from_clipboard(self) -> dict[str, Any] | None:
        clipboard = self.clipboard()
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
        return None

    def copy_selected_nodes_to_clipboard(self) -> bool:
        fragment_payload = self._host.scene.serialize_selected_subgraph_fragment()
        if fragment_payload is None:
            return False
        copied = self._controller._write_graph_fragment_to_clipboard(fragment_payload)
        if not copied:
            return False
        self._controller.set_clipboard_fragment_signature(
            serialize_graph_fragment_payload(fragment_payload) or ""
        )
        self._controller.set_clipboard_paste_count(0)
        return True

    def cut_selected_nodes_to_clipboard(self) -> bool:
        if not self._controller.copy_selected_nodes_to_clipboard():
            return False
        return bool(self._controller.request_delete_selected_graph_items([]).payload)

    def paste_nodes_from_clipboard(self) -> bool:
        fragment_payload = self._controller._read_graph_fragment_from_clipboard()
        if fragment_payload is None:
            return False
        fragment_signature = serialize_graph_fragment_payload(fragment_payload)
        if fragment_signature is None:
            return False
        if fragment_signature != self._controller.clipboard_fragment_signature():
            self._controller.set_clipboard_fragment_signature(fragment_signature)
            self._controller.set_clipboard_paste_count(0)
        frag_center = self._host.scene.fragment_bounds_center(fragment_payload)
        if frag_center is None:
            return False
        paste_index = self._controller.clipboard_paste_count() + 1
        cascade_x = float(paste_index) * _PASTE_CASCADE_OFFSET_X
        cascade_y = float(paste_index) * _PASTE_CASCADE_OFFSET_Y
        pasted = bool(
            self._host.scene.paste_subgraph_fragment(
                fragment_payload,
                frag_center[0] + cascade_x,
                frag_center[1] + cascade_y,
            )
        )
        if not pasted:
            return False
        self._controller.set_clipboard_paste_count(self._controller.clipboard_paste_count() + 1)
        self._host.selected_node_changed.emit()
        self._controller.refresh_workspace_tabs()
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
        self._controller.refresh_workspace_tabs()
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
        self._controller.refresh_workspace_tabs()
        return True

    def request_connect_ports(self, node_a_id: str, port_a: str, node_b_id: str, port_b: str) -> ControllerResult[bool]:
        result = self._graph_interactions.connect_ports(node_a_id, port_a, node_b_id, port_b)
        if result.ok:
            self._controller.refresh_workspace_tabs()
        return ControllerResult(result.ok, result.message, payload=result.ok)

    def request_remove_edge(self, edge_id: str) -> ControllerResult[bool]:
        result = self._graph_interactions.remove_edge(edge_id)
        if result.ok:
            self._controller.refresh_workspace_tabs()
        return ControllerResult(result.ok, result.message, payload=result.ok)

    def request_remove_node(self, node_id: str) -> ControllerResult[bool]:
        result = self._graph_interactions.remove_node(node_id)
        if result.ok:
            self._host.selected_node_changed.emit()
            self._controller.refresh_workspace_tabs()
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
        result = self._graph_interactions.rename_node(node.node_id, new_title)
        if result.ok:
            self._host.selected_node_changed.emit()
            self._controller.refresh_workspace_tabs()
        return ControllerResult(result.ok, result.message, payload=result.ok)

    def request_delete_selected_graph_items(self, edge_ids: list[Any]) -> ControllerResult[bool]:
        result = self._graph_interactions.delete_selected_items(edge_ids)
        if result.ok:
            self._host.selected_node_changed.emit()
            self._controller.refresh_workspace_tabs()
        return ControllerResult(result.ok, result.message, payload=result.ok)
