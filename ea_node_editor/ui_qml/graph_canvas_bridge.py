from __future__ import annotations

"""QML-facing graph-canvas facade."""

from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from ea_node_editor.ui_qml.bridge_runtime import (
    connect_signal as _connect_signal,
)
from ea_node_editor.ui_qml.graph_canvas_command import GraphCanvasCommandBridge
from ea_node_editor.ui_qml.graph_canvas_state import GraphCanvasStateBridge

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
    from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge


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
        self._shell_window = shell_window
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
        return self._shell_window

    @property
    def scene_bridge(self) -> "GraphSceneBridge | None":
        return self._state_bridge.scene_bridge or self._command_bridge.scene_bridge

    @property
    def view_bridge(self) -> "ViewportBridge | None":
        return self._state_bridge.view_bridge or self._command_bridge.view_bridge

    @pyqtProperty(QObject, constant=True)
    def state(self) -> GraphCanvasStateBridge:
        return self._state_bridge

    @pyqtProperty(QObject, constant=True)
    def commands(self) -> GraphCanvasCommandBridge:
        return self._command_bridge

    @pyqtProperty(QObject, constant=True)
    def viewport(self) -> "ViewportBridge | None":
        return self.view_bridge

    @pyqtProperty(QObject, constant=True)
    def mutation(self) -> GraphCanvasCommandBridge:
        return self._command_bridge

    @pyqtProperty(QObject, constant=True)
    def lifecycle(self) -> GraphCanvasStateBridge:
        return self._state_bridge

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

    @pyqtProperty(str, notify=graphics_preferences_changed)
    def graphics_canvas_background_variant(self) -> str:
        return self._state_bridge.graphics_canvas_background_variant

    @pyqtProperty(str, notify=graphics_preferences_changed)
    def graphics_grid_style(self) -> str:
        return self._state_bridge.graphics_grid_style

    @pyqtProperty(str, notify=graphics_preferences_changed)
    def graphics_edge_crossing_style(self) -> str:
        return self._state_bridge.graphics_edge_crossing_style

    @pyqtProperty(int, notify=graphics_preferences_changed)
    def graphics_graph_label_pixel_size(self) -> int:
        return self._state_bridge.graphics_graph_label_pixel_size

    @pyqtProperty("QVariant", notify=graphics_preferences_changed)
    def graphics_graph_node_icon_pixel_size_override(self) -> int | None:
        return self._state_bridge.graphics_graph_node_icon_pixel_size_override

    @pyqtProperty(int, notify=graphics_preferences_changed)
    def graphics_node_title_icon_pixel_size(self) -> int:
        return self._state_bridge.graphics_node_title_icon_pixel_size

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_show_minimap(self) -> bool:
        return self._state_bridge.graphics_show_minimap

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_show_canvas_options_button(self) -> bool:
        return self._state_bridge.graphics_show_canvas_options_button

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_show_port_labels(self) -> bool:
        return self._state_bridge.graphics_show_port_labels

    @pyqtProperty(str, notify=graphics_preferences_changed)
    def graphics_node_elapsed_time_unit(self) -> str:
        return self._state_bridge.graphics_node_elapsed_time_unit

    @pyqtProperty(str, notify=graphics_preferences_changed)
    def graphics_node_elapsed_time_visibility(self) -> str:
        return self._state_bridge.graphics_node_elapsed_time_visibility

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def selected_run_preview_before_run(self) -> bool:
        return self._state_bridge.selected_run_preview_before_run

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_show_tooltips(self) -> bool:
        return self._state_bridge.graphics_show_tooltips

    @pyqtProperty("QVariantMap", notify=graphics_preferences_changed)
    def graphics_tooltip_categories(self) -> dict[str, bool]:
        return self._state_bridge.graphics_tooltip_categories

    @pyqtProperty("QVariantMap", notify=graphics_preferences_changed)
    def graphics_tooltip_category_visibility(self) -> dict[str, bool]:
        return self._state_bridge.graphics_tooltip_category_visibility

    @pyqtSlot(str, result=bool)
    def tooltip_category_enabled(self, category: str) -> bool:
        return self._state_bridge.tooltip_category_enabled(category)

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
    def graphics_floating_toolbar_style(self) -> str:
        return self._state_bridge.graphics_floating_toolbar_style

    @pyqtProperty(str, notify=graphics_preferences_changed)
    def graphics_floating_toolbar_size(self) -> str:
        return self._state_bridge.graphics_floating_toolbar_size

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_node_floating_toolbar_opens_on_hover(self) -> bool:
        return self._state_bridge.graphics_node_floating_toolbar_opens_on_hover

    @pyqtProperty(str, notify=graphics_preferences_changed)
    def graphics_selection_toolbar_mode(self) -> str:
        return self._state_bridge.graphics_selection_toolbar_mode

    @pyqtProperty(str, notify=graphics_preferences_changed)
    def graphics_selection_toolbar_minimal_menu_trigger(self) -> str:
        return self._state_bridge.graphics_selection_toolbar_minimal_menu_trigger

    @pyqtProperty(str, notify=graphics_preferences_changed)
    def active_theme_id(self) -> str:
        return self._state_bridge.active_theme_id

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_graph_follow_shell_theme(self) -> bool:
        return self._state_bridge.graphics_graph_follow_shell_theme

    @pyqtProperty(str, notify=graphics_preferences_changed)
    def graphics_selected_graph_theme_id(self) -> str:
        return self._state_bridge.graphics_selected_graph_theme_id

    @pyqtProperty("QVariantMap", notify=graphics_preferences_changed)
    def graphics_folder_explorer_column_widths(self) -> dict[str, int]:
        return self._state_bridge.graphics_folder_explorer_column_widths

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

    @pyqtProperty(bool, notify=scene_nodes_changed)
    def hide_optional_ports(self) -> bool:
        return self._state_bridge.hide_optional_ports

    @pyqtProperty("QVariantList", notify=scene_nodes_changed)
    def nodes_model(self) -> list[dict]:
        return self._state_bridge.nodes_model

    @pyqtProperty("QVariantList", notify=scene_nodes_changed)
    def backdrop_nodes_model(self) -> list[dict]:
        return self._state_bridge.backdrop_nodes_model

    @pyqtProperty("QVariantList", notify=scene_nodes_changed)
    def minimap_nodes_model(self) -> list[dict]:
        return self._state_bridge.minimap_nodes_model

    @pyqtProperty("QVariantMap", notify=scene_nodes_changed)
    def workspace_scene_bounds_payload(self) -> dict[str, Any]:
        return self._state_bridge.workspace_scene_bounds_payload

    @pyqtProperty("QVariantList", notify=scene_edges_changed)
    def edges_model(self) -> list[dict]:
        return self._state_bridge.edges_model

    @pyqtProperty("QVariantMap", notify=scene_edges_changed)
    def edge_delta_payload(self) -> dict[str, Any]:
        return self._state_bridge.edge_delta_payload

    @pyqtProperty("QVariantMap", notify=scene_selection_changed)
    def selected_node_lookup(self) -> dict[str, bool]:
        return self._state_bridge.selected_node_lookup

    @pyqtSlot(bool, result=bool)
    def set_hide_optional_ports(self, hide_optional_ports: bool) -> bool:
        return self._state_bridge.set_hide_optional_ports(hide_optional_ports)

    @pyqtSlot(bool)
    def set_graphics_minimap_expanded(self, expanded: bool) -> None:
        self._command_bridge.set_graphics_minimap_expanded(expanded)

    @pyqtSlot(bool)
    def set_graphics_show_port_labels(self, show_port_labels: bool) -> None:
        self._command_bridge.set_graphics_show_port_labels(show_port_labels)

    @pyqtSlot(str)
    def set_graphics_node_elapsed_time_unit(self, unit: str) -> None:
        self._command_bridge.set_graphics_node_elapsed_time_unit(unit)

    @pyqtSlot(str)
    def set_graphics_node_elapsed_time_visibility(self, visibility: str) -> None:
        self._command_bridge.set_graphics_node_elapsed_time_visibility(visibility)

    @pyqtSlot(bool)
    def set_selected_run_preview_before_run(self, enabled: bool) -> None:
        self._command_bridge.set_selected_run_preview_before_run(enabled)

    @pyqtSlot(str)
    def set_graphics_floating_toolbar_style(self, style: str) -> None:
        self._command_bridge.set_graphics_floating_toolbar_style(style)

    @pyqtSlot(str)
    def set_graphics_floating_toolbar_size(self, size: str) -> None:
        self._command_bridge.set_graphics_floating_toolbar_size(size)

    @pyqtSlot(str)
    def set_graphics_selection_toolbar_mode(self, mode: str) -> None:
        self._command_bridge.set_graphics_selection_toolbar_mode(mode)

    @pyqtSlot(str)
    def set_graphics_selection_toolbar_minimal_menu_trigger(self, trigger: str) -> None:
        self._command_bridge.set_graphics_selection_toolbar_minimal_menu_trigger(trigger)

    @pyqtSlot("QVariantMap")
    def set_folder_explorer_column_widths(self, widths: dict[str, Any]) -> None:
        self._command_bridge.set_folder_explorer_column_widths(widths)

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

    @pyqtSlot(str, result=bool)
    def trigger_node(self, node_id: str) -> bool:
        return self._command_bridge.trigger_node(node_id)

    @pyqtSlot(str, str, str, result=str)
    @pyqtSlot(str, str, str, str, result=str)
    def browse_node_property_path(self, node_id: str, key: str, current_path: str, source_mode: str = "") -> str:
        return self._command_bridge.browse_node_property_path(node_id, key, current_path, source_mode)

    @pyqtSlot(str, str, str, result=str)
    def internalize_node_property_path(self, node_id: str, key: str, current_path: str) -> str:
        return self._command_bridge.internalize_node_property_path(node_id, key, current_path)

    @pyqtSlot(str, str, str, result=str)
    def pick_node_property_color(self, node_id: str, key: str, current_value: str) -> str:
        return self._command_bridge.pick_node_property_color(node_id, key, current_value)

    @pyqtSlot("QVariantMap", result=bool)
    def copy_text_annotation_style(self, style: dict[str, Any]) -> bool:
        return self._command_bridge.copy_text_annotation_style(style)

    @pyqtSlot(result="QVariantMap")
    def paste_text_annotation_style(self) -> dict[str, Any]:
        return self._command_bridge.paste_text_annotation_style()

    @pyqtSlot(result=bool)
    def has_text_annotation_style(self) -> bool:
        return self._command_bridge.has_text_annotation_style()

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

    @pyqtSlot(str, float, float, "QVariantMap", result=bool)
    def request_drop_node_from_library_with_properties(
        self,
        type_id: str,
        scene_x: float,
        scene_y: float,
        properties: dict[str, Any],
    ) -> bool:
        return self._command_bridge.request_drop_node_from_library_with_properties(
            type_id,
            scene_x,
            scene_y,
            properties,
        )

    @pyqtSlot(str, int, result=str)
    def video_frame_capture_path(self, video_node_id: str, position_ms: int) -> str:
        return self._command_bridge.video_frame_capture_path(video_node_id, position_ms)

    @pyqtSlot(str, "QVariantMap", result="QVariantMap")
    def request_save_image_crop_replace(
        self,
        image_node_id: str,
        crop_rect: dict[str, Any],
    ) -> dict[str, Any]:
        return self._command_bridge.request_save_image_crop_replace(image_node_id, crop_rect)

    @pyqtSlot(str, str, int, float, float, float, float, result="QVariantMap")
    def request_create_video_frame_image_node(
        self,
        video_node_id: str,
        frame_path: str,
        position_ms: int,
        scene_x: float,
        scene_y: float,
        capture_width: float,
        capture_height: float,
    ) -> dict[str, Any]:
        return self._command_bridge.request_create_video_frame_image_node(
            video_node_id,
            frame_path,
            position_ms,
            scene_x,
            scene_y,
            capture_width,
            capture_height,
        )

    @pyqtSlot(str, int, float, float, result="QVariantMap")
    def request_create_video_timestamp_annotation(
        self,
        video_node_id: str,
        position_ms: int,
        scene_x: float,
        scene_y: float,
    ) -> dict[str, Any]:
        return self._command_bridge.request_create_video_timestamp_annotation(
            video_node_id,
            position_ms,
            scene_x,
            scene_y,
        )

    @pyqtSlot(str, int, int, "QVariantMap", result="QVariantMap")
    def request_trim_video_clip_replace(
        self,
        video_node_id: str,
        start_ms: int,
        end_ms: int,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        return self._command_bridge.request_trim_video_clip_replace(
            video_node_id,
            start_ms,
            end_ms,
            state,
        )

    @pyqtSlot(str, int, int, float, float, "QVariantMap", result="QVariantMap")
    def request_trim_video_clip_copy(
        self,
        video_node_id: str,
        start_ms: int,
        end_ms: int,
        scene_x: float,
        scene_y: float,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        return self._command_bridge.request_trim_video_clip_copy(
            video_node_id,
            start_ms,
            end_ms,
            scene_x,
            scene_y,
            state,
        )

    @pyqtSlot(str, str, str, str, bool, result=bool)
    def request_connect_ports(
        self,
        source_node_id: str,
        source_port_key: str,
        target_node_id: str,
        target_port_key: str,
        append_requested: bool = False,
    ) -> bool:
        return self._command_bridge.request_connect_ports(
            source_node_id,
            source_port_key,
            target_node_id,
            target_port_key,
            append_requested,
        )

    @pyqtSlot(str, str, str, str, bool, result=bool)
    def request_move_edge_endpoint(
        self,
        edge_id: str,
        endpoint: str,
        node_id: str,
        port_key: str,
        append_requested: bool = False,
    ) -> bool:
        return self._command_bridge.request_move_edge_endpoint(
            edge_id,
            endpoint,
            node_id,
            port_key,
            append_requested,
        )

    @pyqtSlot(str, str, float, float, float, float, bool, result=bool)
    def request_open_connection_quick_insert(
        self,
        node_id: str,
        port_key: str,
        cursor_scene_x: float,
        cursor_scene_y: float,
        overlay_x: float,
        overlay_y: float,
        append_requested: bool = False,
    ) -> bool:
        return self._command_bridge.request_open_connection_quick_insert(
            node_id,
            port_key,
            cursor_scene_x,
            cursor_scene_y,
            overlay_x,
            overlay_y,
            append_requested,
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

    @pyqtSlot(str, str, str, str, str, str, result=str)
    @pyqtSlot(str, str, str, str, str, str, str, str, result=str)
    def upsert_node_link(
        self,
        node_id: str,
        link_id: str,
        kind: str,
        title: str,
        target: str,
        subtitle: str = "",
        target_workspace_id: str = "",
        target_node_id: str = "",
    ) -> str:
        return self._command_bridge.upsert_node_link(
            node_id,
            link_id,
            kind,
            title,
            target,
            subtitle,
            target_workspace_id,
            target_node_id,
        )

    @pyqtSlot(str, str, result=bool)
    def remove_node_link(self, node_id: str, link_id: str) -> bool:
        return self._command_bridge.remove_node_link(node_id, link_id)

    @pyqtSlot(str, str, int, result=bool)
    def move_node_link(self, node_id: str, link_id: str, offset: int) -> bool:
        return self._command_bridge.move_node_link(node_id, link_id, offset)

    @pyqtSlot(str, result="QVariantList")
    def parameter_setup_link_options(self, pool_node_id: str) -> list[dict[str, Any]]:
        return self._command_bridge.parameter_setup_link_options(pool_node_id)

    @pyqtSlot(str, result="QVariantMap")
    def parameter_setup_link_status(self, pool_node_id: str) -> dict[str, Any]:
        return self._command_bridge.parameter_setup_link_status(pool_node_id)

    @pyqtSlot(str, str, result=bool)
    def link_parameter_setup(self, pool_node_id: str, setup_node_id: str) -> bool:
        return self._command_bridge.link_parameter_setup(
            pool_node_id,
            setup_node_id,
        )

    @pyqtSlot(str, result=bool)
    def unlink_parameter_setup(self, pool_node_id: str) -> bool:
        return self._command_bridge.unlink_parameter_setup(pool_node_id)

    @pyqtSlot(str, str, str, result=str)
    @pyqtSlot(str, str, str, str, str, bool, bool, bool, result=str)
    def upsert_node_comment(
        self,
        node_id: str,
        comment_id: str,
        body: str,
        author: str = "",
        parent_id: str = "",
        resolved: bool = False,
        unread: bool = True,
        pinned: bool = False,
    ) -> str:
        return self._command_bridge.upsert_node_comment(
            node_id,
            comment_id,
            body,
            author,
            parent_id,
            resolved,
            unread,
            pinned,
        )

    @pyqtSlot(str, str, result=bool)
    def remove_node_comment(self, node_id: str, comment_id: str) -> bool:
        return self._command_bridge.remove_node_comment(node_id, comment_id)

    @pyqtSlot(str, str, bool, result=bool)
    def set_node_comment_resolved(self, node_id: str, comment_id: str, resolved: bool) -> bool:
        return self._command_bridge.set_node_comment_resolved(node_id, comment_id, resolved)

    @pyqtSlot(str, str, bool, result=bool)
    def set_node_comment_pinned(self, node_id: str, comment_id: str, pinned: bool) -> bool:
        return self._command_bridge.set_node_comment_pinned(node_id, comment_id, pinned)

    @pyqtSlot(str, result=bool)
    def resolve_all_node_comments(self, node_id: str) -> bool:
        return self._command_bridge.resolve_all_node_comments(node_id)

    @pyqtSlot(str, result=bool)
    def mark_node_comments_read(self, node_id: str) -> bool:
        return self._command_bridge.mark_node_comments_read(node_id)

    @pyqtSlot(str, str, result=bool)
    def open_node_link(self, node_id: str, link_id: str) -> bool:
        return self._command_bridge.open_node_link(node_id, link_id)

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

    @pyqtSlot(str, result="QVariantMap")
    def describe_image_preview(self, source: str) -> dict[str, Any]:
        return self._command_bridge.describe_image_preview(source)

    @pyqtSlot(str, result="QVariantMap")
    def describe_mail_preview(self, source: str) -> dict[str, Any]:
        return self._command_bridge.describe_mail_preview(source)

    @pyqtSlot(str, bool, result="QVariantMap")
    def open_local_file_source(self, source: str, chooser: bool) -> dict[str, Any]:
        return self._command_bridge.open_local_file_source(source, chooser)

    @pyqtSlot("QVariantMap", "QVariantMap", result="QVariantMap")
    def describe_tabular_preview(
        self,
        properties: dict[str, Any],
        request: dict[str, Any],
    ) -> dict[str, Any]:
        return self._command_bridge.describe_tabular_preview(properties, request)

    @pyqtSlot(str, result=str)
    def resolve_local_file_source_url(self, source: str) -> str:
        return self._command_bridge.resolve_local_file_source_url(source)


__all__ = ["GraphCanvasBridge"]
