from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, cast

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSlot

if TYPE_CHECKING:
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
    from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge


class _GraphCanvasCommandSource(Protocol):
    def set_graphics_minimap_expanded(self, expanded: bool) -> None: ...

    def set_graphics_show_port_labels(self, show_port_labels: bool) -> None: ...

    def set_graphics_performance_mode(self, mode: str) -> None: ...

    def set_graphics_floating_toolbar_style(self, style: str) -> None: ...

    def request_open_subnode_scope(self, node_id: str) -> bool: ...

    def browse_node_property_path(self, node_id: str, key: str, current_path: str) -> str: ...

    def pick_node_property_color(self, node_id: str, key: str, current_value: str) -> str: ...

    def request_drop_node_from_library(
        self,
        type_id: str,
        scene_x: float,
        scene_y: float,
        target_mode: str,
        target_node_id: str,
        target_port_key: str,
        target_edge_id: str,
    ) -> bool: ...

    def request_connect_ports(
        self,
        source_node_id: str,
        source_port_key: str,
        target_node_id: str,
        target_port_key: str,
    ) -> bool: ...

    def request_open_connection_quick_insert(
        self,
        node_id: str,
        port_key: str,
        cursor_scene_x: float,
        cursor_scene_y: float,
        overlay_x: float,
        overlay_y: float,
    ) -> bool: ...

    def request_open_canvas_quick_insert(
        self,
        scene_x: float,
        scene_y: float,
        overlay_x: float,
        overlay_y: float,
    ) -> None: ...


class _GraphCanvasHostSource(Protocol):
    def request_delete_selected_graph_items(self, edge_ids: list[object]) -> bool: ...

    def request_navigate_scope_parent(self) -> bool: ...

    def request_navigate_scope_root(self) -> bool: ...

    def set_graph_cursor_shape(self, cursor_shape: int) -> None: ...

    def clear_graph_cursor_shape(self) -> None: ...

    def describe_pdf_preview(self, source: str, page_number: Any) -> dict[str, Any]: ...


class _GraphCanvasSceneCommandSource(Protocol):
    def select_node(self, node_id: str, additive: bool = False) -> None: ...

    def clear_selection(self) -> None: ...

    def select_nodes_in_rect(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        additive: bool = False,
    ) -> None: ...

    def set_node_port_label(self, node_id: str, port_key: str, label: str) -> None: ...

    def set_node_property(self, node_id: str, key: str, value: object) -> None: ...

    def set_pending_surface_action(self, node_id: str) -> None: ...

    def consume_pending_surface_action(self, node_id: str) -> bool: ...

    def set_node_properties(self, node_id: str, values: dict[str, Any]) -> bool: ...

    def move_nodes_by_delta(self, node_ids: list[Any], dx: float, dy: float) -> bool: ...

    def move_node(self, node_id: str, x: float, y: float) -> None: ...

    def resize_node(self, node_id: str, width: float, height: float) -> None: ...

    def set_node_geometry(self, node_id: str, x: float, y: float, width: float, height: float) -> None: ...

    def set_port_locked(self, node_id: str, key: str, locked: bool) -> bool: ...


class _GraphCanvasScenePolicySource(Protocol):
    def are_port_kinds_compatible(self, source_kind: str, target_kind: str) -> bool: ...

    def are_data_types_compatible(self, source_type: str, target_type: str) -> bool: ...


def _invoke(source: object | None, name: str, *args, default: Any = None) -> Any:
    callback = getattr(source, name, None) if source is not None else None
    if not callable(callback):
        return default
    return callback(*args)


def _copy_dict(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _resolve_scene_command_source(scene_bridge: object | None) -> _GraphCanvasSceneCommandSource | None:
    if scene_bridge is None:
        return None
    return cast(
        _GraphCanvasSceneCommandSource,
        getattr(scene_bridge, "command_bridge", scene_bridge),
    )


def _resolve_scene_policy_source(scene_bridge: object | None) -> _GraphCanvasScenePolicySource | None:
    if scene_bridge is None:
        return None
    return cast(
        _GraphCanvasScenePolicySource,
        getattr(scene_bridge, "policy_bridge", scene_bridge),
    )


class GraphCanvasCommandBridge(QObject):
    def __init__(
        self,
        parent: QObject | None = None,
        *,
        shell_window: object | None = None,
        canvas_source: _GraphCanvasCommandSource | None = None,
        host_source: _GraphCanvasHostSource | None = None,
        scene_bridge: "GraphSceneBridge | None" = None,
        view_bridge: "ViewportBridge | None" = None,
    ) -> None:
        super().__init__(parent)
        _ = shell_window
        self._scene_bridge = scene_bridge
        self._view_bridge = view_bridge
        self._canvas_source = canvas_source
        self._host_source = host_source
        self._scene_command_source = _resolve_scene_command_source(scene_bridge)
        self._scene_policy_source = _resolve_scene_policy_source(scene_bridge)

    @property
    def shell_window(self) -> None:
        return None

    @property
    def canvas_source(self) -> _GraphCanvasCommandSource | None:
        return self._canvas_source

    @property
    def host_source(self) -> _GraphCanvasHostSource | None:
        return self._host_source

    @property
    def scene_bridge(self) -> "GraphSceneBridge | None":
        return self._scene_bridge

    @property
    def scene_command_source(self) -> _GraphCanvasSceneCommandSource | None:
        return self._scene_command_source

    @property
    def scene_policy_source(self) -> _GraphCanvasScenePolicySource | None:
        return self._scene_policy_source

    @property
    def view_bridge(self) -> "ViewportBridge | None":
        return self._view_bridge

    @pyqtProperty(QObject, constant=True)
    def viewport_bridge(self) -> "ViewportBridge | None":
        return self._view_bridge

    @pyqtSlot(bool)
    def set_graphics_minimap_expanded(self, expanded: bool) -> None:
        _invoke(self._canvas_source, "set_graphics_minimap_expanded", bool(expanded))

    @pyqtSlot(bool)
    def set_graphics_show_port_labels(self, show_port_labels: bool) -> None:
        _invoke(self._canvas_source, "set_graphics_show_port_labels", bool(show_port_labels))

    @pyqtSlot(str)
    def set_graphics_performance_mode(self, mode: str) -> None:
        _invoke(self._canvas_source, "set_graphics_performance_mode", mode)

    @pyqtSlot(str)
    def set_graphics_floating_toolbar_style(self, style: str) -> None:
        _invoke(self._canvas_source, "set_graphics_floating_toolbar_style", style)

    @pyqtSlot(str)
    def set_graphics_floating_toolbar_size(self, size: str) -> None:
        _invoke(self._canvas_source, "set_graphics_floating_toolbar_size", size)

    @pyqtSlot(float)
    def adjust_zoom(self, factor: float) -> None:
        _invoke(self._view_bridge, "adjust_zoom", float(factor))

    @pyqtSlot(float, float, float, result=bool)
    def adjust_zoom_at_viewport_point(self, factor: float, viewport_x: float, viewport_y: float) -> bool:
        return bool(
            _invoke(
                self._view_bridge,
                "adjust_zoom_at_viewport_point",
                float(factor),
                float(viewport_x),
                float(viewport_y),
                default=False,
            )
        )

    @pyqtSlot(float, float)
    def pan_by(self, delta_x: float, delta_y: float) -> None:
        _invoke(self._view_bridge, "pan_by", float(delta_x), float(delta_y))

    @pyqtSlot(float, float, float, result=bool)
    def set_view_state(self, zoom: float, center_x: float, center_y: float) -> bool:
        return bool(
            _invoke(
                self._view_bridge,
                "set_view_state",
                float(zoom),
                float(center_x),
                float(center_y),
                default=False,
            )
        )

    @pyqtSlot(float, float)
    def set_viewport_size(self, width: float, height: float) -> None:
        _invoke(self._view_bridge, "set_viewport_size", float(width), float(height))

    @pyqtSlot(float, float)
    def center_on_scene_point(self, x: float, y: float) -> None:
        _invoke(self._view_bridge, "center_on_scene_point", float(x), float(y))

    @pyqtSlot(str, result=bool)
    def request_open_subnode_scope(self, node_id: str) -> bool:
        return bool(
            _invoke(
                self._canvas_source,
                "request_open_subnode_scope",
                node_id,
                default=False,
            )
        )

    @pyqtSlot(str, result=bool)
    def can_open_comment_peek(self, node_id: str) -> bool:
        return bool(_invoke(self._scene_bridge, "can_open_comment_peek", node_id, default=False))

    @pyqtSlot(result=bool)
    def request_close_comment_peek(self) -> bool:
        return bool(_invoke(self._scene_bridge, "close_comment_peek", default=False))

    @pyqtSlot(result=str)
    def active_comment_peek_node_id(self) -> str:
        return str(getattr(self._scene_bridge, "active_comment_peek_node_id", "") or "")

    @pyqtSlot(str, str, str, result=str)
    def browse_node_property_path(self, node_id: str, key: str, current_path: str) -> str:
        return str(
            _invoke(
                self._canvas_source,
                "browse_node_property_path",
                node_id,
                key,
                current_path,
                default="",
            )
            or ""
        )

    @pyqtSlot(str, str, str, result=str)
    def pick_node_property_color(self, node_id: str, key: str, current_value: str) -> str:
        return str(
            _invoke(
                self._canvas_source,
                "pick_node_property_color",
                node_id,
                key,
                current_value,
                default="",
            )
            or ""
        )

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
        return bool(
            _invoke(
                self._canvas_source,
                "request_drop_node_from_library",
                type_id,
                float(scene_x),
                float(scene_y),
                target_mode,
                target_node_id,
                target_port_key,
                target_edge_id,
                default=False,
            )
        )

    @pyqtSlot(str, str, str, str, result=bool)
    def request_connect_ports(
        self,
        source_node_id: str,
        source_port_key: str,
        target_node_id: str,
        target_port_key: str,
    ) -> bool:
        return bool(
            _invoke(
                self._canvas_source,
                "request_connect_ports",
                source_node_id,
                source_port_key,
                target_node_id,
                target_port_key,
                default=False,
            )
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
        return bool(
            _invoke(
                self._canvas_source,
                "request_open_connection_quick_insert",
                node_id,
                port_key,
                float(cursor_scene_x),
                float(cursor_scene_y),
                float(overlay_x),
                float(overlay_y),
                default=False,
            )
        )

    @pyqtSlot(float, float, float, float)
    def request_open_canvas_quick_insert(
        self,
        scene_x: float,
        scene_y: float,
        overlay_x: float,
        overlay_y: float,
    ) -> None:
        _invoke(
            self._canvas_source,
            "request_open_canvas_quick_insert",
            float(scene_x),
            float(scene_y),
            float(overlay_x),
            float(overlay_y),
        )

    @pyqtSlot("QVariantList", result=bool)
    def request_delete_selected_graph_items(self, edge_ids: list) -> bool:
        return bool(
            _invoke(
                self._host_source,
                "request_delete_selected_graph_items",
                edge_ids,
                default=False,
            )
        )

    @pyqtSlot(result=bool)
    def request_navigate_scope_parent(self) -> bool:
        return bool(
            _invoke(
                self._host_source,
                "request_navigate_scope_parent",
                default=False,
            )
        )

    @pyqtSlot(result=bool)
    def request_navigate_scope_root(self) -> bool:
        return bool(
            _invoke(
                self._host_source,
                "request_navigate_scope_root",
                default=False,
            )
        )

    @pyqtSlot(str, bool)
    def select_node(self, node_id: str, additive: bool = False) -> None:
        _invoke(self._scene_command_source, "select_node", node_id, bool(additive))

    @pyqtSlot()
    def clear_selection(self) -> None:
        _invoke(self._scene_command_source, "clear_selection")

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
        _invoke(
            self._scene_command_source,
            "select_nodes_in_rect",
            float(x1),
            float(y1),
            float(x2),
            float(y2),
            bool(additive),
        )

    @pyqtSlot(str, str, str)
    def set_node_port_label(self, node_id: str, port_key: str, label: str) -> None:
        _invoke(self._scene_command_source, "set_node_port_label", node_id, port_key, label)

    @pyqtSlot(str, str, "QVariant")
    def set_node_property(self, node_id: str, key: str, value: object) -> None:
        _invoke(self._scene_command_source, "set_node_property", node_id, key, value)

    @pyqtSlot(str)
    def set_pending_surface_action(self, node_id: str) -> None:
        _invoke(self._scene_command_source, "set_pending_surface_action", node_id)

    @pyqtSlot(str, result=bool)
    def consume_pending_surface_action(self, node_id: str) -> bool:
        return bool(
            _invoke(
                self._scene_command_source,
                "consume_pending_surface_action",
                node_id,
                default=False,
            )
        )

    @pyqtSlot(str, "QVariantMap", result=bool)
    def set_node_properties(self, node_id: str, values: dict[str, Any]) -> bool:
        return bool(
            _invoke(
                self._scene_command_source,
                "set_node_properties",
                node_id,
                dict(values or {}),
                default=False,
            )
        )

    @pyqtSlot(str, str, result=bool)
    def are_port_kinds_compatible(self, source_kind: str, target_kind: str) -> bool:
        return bool(
            _invoke(
                self._scene_policy_source,
                "are_port_kinds_compatible",
                source_kind,
                target_kind,
                default=False,
            )
        )

    @pyqtSlot(str, str, result=bool)
    def are_data_types_compatible(self, source_type: str, target_type: str) -> bool:
        return bool(
            _invoke(
                self._scene_policy_source,
                "are_data_types_compatible",
                source_type,
                target_type,
                default=False,
            )
        )

    @pyqtSlot("QVariantList", float, float, result=bool)
    def move_nodes_by_delta(self, node_ids: list, delta_x: float, delta_y: float) -> bool:
        return bool(
            _invoke(
                self._scene_command_source,
                "move_nodes_by_delta",
                node_ids,
                float(delta_x),
                float(delta_y),
                default=False,
            )
        )

    @pyqtSlot(str, float, float)
    def move_node(self, node_id: str, x: float, y: float) -> None:
        _invoke(self._scene_command_source, "move_node", node_id, float(x), float(y))

    @pyqtSlot(str, float, float)
    def resize_node(self, node_id: str, width: float, height: float) -> None:
        _invoke(self._scene_command_source, "resize_node", node_id, float(width), float(height))

    @pyqtSlot(str, float, float, float, float)
    def set_node_geometry(self, node_id: str, x: float, y: float, width: float, height: float) -> None:
        _invoke(
            self._scene_command_source,
            "set_node_geometry",
            node_id,
            float(x),
            float(y),
            float(width),
            float(height),
        )

    @pyqtSlot(str, str, bool, result=bool)
    def set_port_locked(self, node_id: str, port_key: str, locked: bool) -> bool:
        return bool(
            _invoke(
                self._scene_command_source,
                "set_port_locked",
                node_id,
                port_key,
                bool(locked),
                default=False,
            )
        )

    @pyqtSlot(int)
    def set_graph_cursor_shape(self, cursor_shape: int) -> None:
        _invoke(self._host_source, "set_graph_cursor_shape", int(cursor_shape))

    @pyqtSlot()
    def clear_graph_cursor_shape(self) -> None:
        _invoke(self._host_source, "clear_graph_cursor_shape")

    @pyqtSlot(str, "QVariant", result="QVariantMap")
    def describe_pdf_preview(self, source: str, page_number: Any) -> dict[str, Any]:
        return _copy_dict(
            _invoke(
                self._host_source,
                "describe_pdf_preview",
                source,
                page_number,
                default={},
            )
        )


__all__ = ["GraphCanvasCommandBridge"]
