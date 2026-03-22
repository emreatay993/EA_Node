from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from ea_node_editor.ui_qml.graph_canvas_command_bridge import GraphCanvasCommandBridge
from ea_node_editor.ui_qml.graph_canvas_state_bridge import GraphCanvasStateBridge

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
    from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge


def _connect_signal(source: object | None, name: str, slot) -> None:  # noqa: ANN001
    signal = getattr(source, name, None) if source is not None else None
    if signal is not None and hasattr(signal, "connect"):
        signal.connect(slot)


def _invoke_chain(sources: tuple[object | None, ...], name: str, *args) -> bool:
    for source in sources:
        callback = getattr(source, name, None) if source is not None else None
        if callable(callback):
            callback(*args)
            return True
    return False


class GraphCanvasBridge(QObject):
    graphics_preferences_changed = pyqtSignal()
    snap_to_grid_changed = pyqtSignal()
    scene_nodes_changed = pyqtSignal()
    scene_edges_changed = pyqtSignal()
    scene_selection_changed = pyqtSignal()
    view_state_changed = pyqtSignal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        shell_window: "ShellWindow | None" = None,
        scene_bridge: "GraphSceneBridge | None" = None,
        view_bridge: "ViewportBridge | None" = None,
        state_bridge: GraphCanvasStateBridge | None = None,
        command_bridge: GraphCanvasCommandBridge | None = None,
    ) -> None:
        super().__init__(parent)
        self._state_bridge = state_bridge or GraphCanvasStateBridge(
            self,
            shell_window=shell_window,
            scene_bridge=scene_bridge,
            view_bridge=view_bridge,
        )
        self._command_bridge = command_bridge or GraphCanvasCommandBridge(
            self,
            shell_window=shell_window,
            scene_bridge=scene_bridge,
            view_bridge=view_bridge,
        )

        _connect_signal(
            self._state_bridge,
            "graphics_preferences_changed",
            self.graphics_preferences_changed.emit,
        )
        _connect_signal(
            self._state_bridge,
            "snap_to_grid_changed",
            self.snap_to_grid_changed.emit,
        )
        _connect_signal(
            self._state_bridge,
            "scene_nodes_changed",
            self.scene_nodes_changed.emit,
        )
        _connect_signal(
            self._state_bridge,
            "scene_edges_changed",
            self.scene_edges_changed.emit,
        )
        _connect_signal(
            self._state_bridge,
            "scene_selection_changed",
            self.scene_selection_changed.emit,
        )
        _connect_signal(
            self._state_bridge,
            "view_state_changed",
            self.view_state_changed.emit,
        )

    @property
    def shell_window(self) -> "ShellWindow | None":
        return self._state_bridge.shell_window or self._command_bridge.shell_window

    @property
    def scene_bridge(self) -> "GraphSceneBridge | None":
        return self._state_bridge.scene_bridge or self._command_bridge.scene_bridge

    @property
    def view_bridge(self) -> "ViewportBridge | None":
        return self._state_bridge.view_bridge or self._command_bridge.view_bridge

    @pyqtProperty(QObject, constant=True)
    def viewport_bridge(self) -> "ViewportBridge | None":
        return self.view_bridge

    @property
    def state_bridge(self) -> GraphCanvasStateBridge:
        return self._state_bridge

    @property
    def command_bridge(self) -> GraphCanvasCommandBridge:
        return self._command_bridge

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_minimap_expanded(self) -> bool:
        return self._state_bridge.graphics_minimap_expanded

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_show_grid(self) -> bool:
        return self._state_bridge.graphics_show_grid

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_show_minimap(self) -> bool:
        return self._state_bridge.graphics_show_minimap

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_show_port_labels(self) -> bool:
        return self._state_bridge.graphics_show_port_labels

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_node_shadow(self) -> bool:
        return self._state_bridge.graphics_node_shadow

    @pyqtProperty(int, notify=graphics_preferences_changed)
    def graphics_shadow_strength(self) -> int:
        return self._state_bridge.graphics_shadow_strength

    @pyqtProperty(int, notify=graphics_preferences_changed)
    def graphics_shadow_softness(self) -> int:
        return self._state_bridge.graphics_shadow_softness

    @pyqtProperty(int, notify=graphics_preferences_changed)
    def graphics_shadow_offset(self) -> int:
        return self._state_bridge.graphics_shadow_offset

    @pyqtProperty(str, notify=graphics_preferences_changed)
    def graphics_performance_mode(self) -> str:
        return self._state_bridge.graphics_performance_mode

    @pyqtProperty(bool, notify=snap_to_grid_changed)
    def snap_to_grid_enabled(self) -> bool:
        return self._state_bridge.snap_to_grid_enabled

    @pyqtProperty(float, notify=snap_to_grid_changed)
    def snap_grid_size(self) -> float:
        return self._state_bridge.snap_grid_size

    @pyqtProperty(float, notify=view_state_changed)
    def center_x(self) -> float:
        return self._state_bridge.center_x

    @pyqtProperty(float, notify=view_state_changed)
    def center_y(self) -> float:
        return self._state_bridge.center_y

    @pyqtProperty(float, notify=view_state_changed)
    def zoom_value(self) -> float:
        return self._state_bridge.zoom_value

    @pyqtProperty("QVariantMap", notify=view_state_changed)
    def visible_scene_rect_payload(self) -> dict[str, Any]:
        return self._state_bridge.visible_scene_rect_payload

    @pyqtProperty("QVariantMap", notify=view_state_changed)
    def visible_scene_rect_payload_cached(self) -> dict[str, Any]:
        return self._state_bridge.visible_scene_rect_payload_cached

    @pyqtProperty("QVariantList", notify=scene_nodes_changed)
    def nodes_model(self) -> list[dict]:
        return self._state_bridge.nodes_model

    @pyqtProperty("QVariantList", notify=scene_nodes_changed)
    def minimap_nodes_model(self) -> list[dict]:
        return self._state_bridge.minimap_nodes_model

    @pyqtProperty("QVariantMap", notify=scene_nodes_changed)
    def workspace_scene_bounds_payload(self) -> dict[str, Any]:
        return self._state_bridge.workspace_scene_bounds_payload

    @pyqtProperty("QVariantList", notify=scene_edges_changed)
    def edges_model(self) -> list[dict]:
        return self._state_bridge.edges_model

    @pyqtProperty("QVariantMap", notify=scene_selection_changed)
    def selected_node_lookup(self) -> dict[str, bool]:
        return self._state_bridge.selected_node_lookup

    @pyqtSlot(bool)
    def set_graphics_minimap_expanded(self, expanded: bool) -> None:
        self._command_bridge.set_graphics_minimap_expanded(expanded)

    @pyqtSlot(bool)
    def set_graphics_show_port_labels(self, show_port_labels: bool) -> None:
        _invoke_chain(
            (
                getattr(self.shell_window, "graph_canvas_presenter", None),
                self.shell_window,
            ),
            "set_graphics_show_port_labels",
            show_port_labels,
        )

    @pyqtSlot(str)
    def set_graphics_performance_mode(self, mode: str) -> None:
        _invoke_chain(
            (
                getattr(self.shell_window, "graph_canvas_presenter", None),
                self.shell_window,
            ),
            "set_graphics_performance_mode",
            mode,
        )

    @pyqtSlot(float)
    def adjust_zoom(self, factor: float) -> None:
        self._command_bridge.adjust_zoom(factor)

    @pyqtSlot(float, float, float, result=bool)
    def adjust_zoom_at_viewport_point(self, factor: float, viewport_x: float, viewport_y: float) -> bool:
        return self._command_bridge.adjust_zoom_at_viewport_point(factor, viewport_x, viewport_y)

    @pyqtSlot(float, float)
    def pan_by(self, delta_x: float, delta_y: float) -> None:
        self._command_bridge.pan_by(delta_x, delta_y)

    @pyqtSlot(float, float, float, result=bool)
    def set_view_state(self, zoom: float, center_x: float, center_y: float) -> bool:
        return self._command_bridge.set_view_state(zoom, center_x, center_y)

    @pyqtSlot(float, float)
    def set_viewport_size(self, width: float, height: float) -> None:
        self._command_bridge.set_viewport_size(width, height)

    @pyqtSlot(float, float)
    def center_on_scene_point(self, x: float, y: float) -> None:
        self._command_bridge.center_on_scene_point(x, y)

    @pyqtSlot(str, result=bool)
    def request_open_subnode_scope(self, node_id: str) -> bool:
        return self._command_bridge.request_open_subnode_scope(node_id)

    @pyqtSlot(str, str, str, result=str)
    def browse_node_property_path(self, node_id: str, key: str, current_path: str) -> str:
        return self._command_bridge.browse_node_property_path(node_id, key, current_path)

    @pyqtSlot(
        str,
        float,
        float,
        str,
        str,
        str,
        str,
        result=bool,
    )
    def request_drop_node_from_library(
        self,
        type_id: str,
        scene_x: float,
        scene_y: float,
        target_mode: str,
        target_node_id: str,
        target_port_key: str,
        target_edge_id: str,
    ) -> bool:
        return self._command_bridge.request_drop_node_from_library(
            type_id,
            scene_x,
            scene_y,
            target_mode,
            target_node_id,
            target_port_key,
            target_edge_id,
        )

    @pyqtSlot(str, str, str, str, result=bool)
    def request_connect_ports(
        self,
        source_node_id: str,
        source_port_key: str,
        target_node_id: str,
        target_port_key: str,
    ) -> bool:
        return self._command_bridge.request_connect_ports(
            source_node_id,
            source_port_key,
            target_node_id,
            target_port_key,
        )

    @pyqtSlot(str, str, float, float, float, float, result=bool)
    def request_open_connection_quick_insert(
        self,
        node_id: str,
        port_key: str,
        cursor_scene_x: float,
        cursor_scene_y: float,
        overlay_x: float,
        overlay_y: float,
    ) -> bool:
        return self._command_bridge.request_open_connection_quick_insert(
            node_id,
            port_key,
            cursor_scene_x,
            cursor_scene_y,
            overlay_x,
            overlay_y,
        )

    @pyqtSlot(float, float, float, float)
    def request_open_canvas_quick_insert(
        self,
        scene_x: float,
        scene_y: float,
        overlay_x: float,
        overlay_y: float,
    ) -> None:
        self._command_bridge.request_open_canvas_quick_insert(
            scene_x,
            scene_y,
            overlay_x,
            overlay_y,
        )

    @pyqtSlot("QVariantList", result=bool)
    def request_delete_selected_graph_items(self, edge_ids: list) -> bool:
        return self._command_bridge.request_delete_selected_graph_items(edge_ids)

    @pyqtSlot(result=bool)
    def request_navigate_scope_parent(self) -> bool:
        return self._command_bridge.request_navigate_scope_parent()

    @pyqtSlot(result=bool)
    def request_navigate_scope_root(self) -> bool:
        return self._command_bridge.request_navigate_scope_root()

    @pyqtSlot(str, bool)
    def select_node(self, node_id: str, additive: bool = False) -> None:
        self._command_bridge.select_node(node_id, additive)

    @pyqtSlot()
    def clear_selection(self) -> None:
        self._command_bridge.clear_selection()

    @pyqtSlot(float, float, float, float)
    @pyqtSlot(float, float, float, float, bool)
    def select_nodes_in_rect(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        additive: bool = False,
    ) -> None:
        self._command_bridge.select_nodes_in_rect(x1, y1, x2, y2, additive)

    @pyqtSlot(str, str, str)
    def set_node_port_label(self, node_id: str, port_key: str, label: str) -> None:
        self._command_bridge.set_node_port_label(node_id, port_key, label)

    @pyqtSlot(str, str, "QVariant")
    def set_node_property(self, node_id: str, key: str, value: object) -> None:
        self._command_bridge.set_node_property(node_id, key, value)

    @pyqtSlot(str)
    def set_pending_surface_action(self, node_id: str) -> None:
        self._command_bridge.set_pending_surface_action(node_id)

    @pyqtSlot(str, result=bool)
    def consume_pending_surface_action(self, node_id: str) -> bool:
        return self._command_bridge.consume_pending_surface_action(node_id)

    @pyqtSlot(str, "QVariantMap", result=bool)
    def set_node_properties(self, node_id: str, values: dict[str, Any]) -> bool:
        return self._command_bridge.set_node_properties(node_id, values)

    @pyqtSlot(str, str, result=bool)
    def are_port_kinds_compatible(self, source_kind: str, target_kind: str) -> bool:
        return self._command_bridge.are_port_kinds_compatible(source_kind, target_kind)

    @pyqtSlot(str, str, result=bool)
    def are_data_types_compatible(self, source_type: str, target_type: str) -> bool:
        return self._command_bridge.are_data_types_compatible(source_type, target_type)

    @pyqtSlot("QVariantList", float, float, result=bool)
    def move_nodes_by_delta(self, node_ids: list, delta_x: float, delta_y: float) -> bool:
        return self._command_bridge.move_nodes_by_delta(node_ids, delta_x, delta_y)

    @pyqtSlot(str, float, float)
    def move_node(self, node_id: str, x: float, y: float) -> None:
        self._command_bridge.move_node(node_id, x, y)

    @pyqtSlot(str, float, float)
    def resize_node(self, node_id: str, width: float, height: float) -> None:
        self._command_bridge.resize_node(node_id, width, height)

    @pyqtSlot(str, float, float, float, float)
    def set_node_geometry(self, node_id: str, x: float, y: float, width: float, height: float) -> None:
        self._command_bridge.set_node_geometry(node_id, x, y, width, height)

    @pyqtSlot(int)
    def set_graph_cursor_shape(self, cursor_shape: int) -> None:
        self._command_bridge.set_graph_cursor_shape(cursor_shape)

    @pyqtSlot()
    def clear_graph_cursor_shape(self) -> None:
        self._command_bridge.clear_graph_cursor_shape()

    @pyqtSlot(str, "QVariant", result="QVariantMap")
    def describe_pdf_preview(self, source: str, page_number: Any) -> dict[str, Any]:
        return self._command_bridge.describe_pdf_preview(source, page_number)

    @pyqtSlot(str, result=bool)
    def request_edit_flow_edge_style(self, edge_id: str) -> bool:
        return self._command_bridge.request_edit_flow_edge_style(edge_id)

    @pyqtSlot(str, result=bool)
    def request_edit_flow_edge_label(self, edge_id: str) -> bool:
        return self._command_bridge.request_edit_flow_edge_label(edge_id)

    @pyqtSlot(str, result=bool)
    def request_reset_flow_edge_style(self, edge_id: str) -> bool:
        return self._command_bridge.request_reset_flow_edge_style(edge_id)

    @pyqtSlot(str, result=bool)
    def request_copy_flow_edge_style(self, edge_id: str) -> bool:
        return self._command_bridge.request_copy_flow_edge_style(edge_id)

    @pyqtSlot(str, result=bool)
    def request_paste_flow_edge_style(self, edge_id: str) -> bool:
        return self._command_bridge.request_paste_flow_edge_style(edge_id)

    @pyqtSlot(str, result=bool)
    def request_remove_edge(self, edge_id: str) -> bool:
        return self._command_bridge.request_remove_edge(edge_id)

    @pyqtSlot(str, result=bool)
    def request_publish_custom_workflow_from_node(self, node_id: str) -> bool:
        return self._command_bridge.request_publish_custom_workflow_from_node(node_id)

    @pyqtSlot(str, result=bool)
    def request_edit_passive_node_style(self, node_id: str) -> bool:
        return self._command_bridge.request_edit_passive_node_style(node_id)

    @pyqtSlot(str, result=bool)
    def request_reset_passive_node_style(self, node_id: str) -> bool:
        return self._command_bridge.request_reset_passive_node_style(node_id)

    @pyqtSlot(str, result=bool)
    def request_copy_passive_node_style(self, node_id: str) -> bool:
        return self._command_bridge.request_copy_passive_node_style(node_id)

    @pyqtSlot(str, result=bool)
    def request_paste_passive_node_style(self, node_id: str) -> bool:
        return self._command_bridge.request_paste_passive_node_style(node_id)

    @pyqtSlot(str, result=bool)
    def request_rename_node(self, node_id: str) -> bool:
        return self._command_bridge.request_rename_node(node_id)

    @pyqtSlot(str, result=bool)
    def request_ungroup_node(self, node_id: str) -> bool:
        return self._command_bridge.request_ungroup_node(node_id)

    @pyqtSlot(str, result=bool)
    def request_remove_node(self, node_id: str) -> bool:
        return self._command_bridge.request_remove_node(node_id)


__all__ = ["GraphCanvasBridge"]
