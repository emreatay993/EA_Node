from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
    from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge


def _copy_list(value: object) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _copy_dict(value: object) -> dict[str, bool]:
    return dict(value) if isinstance(value, dict) else {}


def _source_attr(source: object | None, name: str, default: Any) -> Any:
    if source is None:
        return default
    return getattr(source, name, default)


def _invoke(source: object | None, name: str, *args, default: Any = None) -> Any:
    callback = getattr(source, name, None) if source is not None else None
    if not callable(callback):
        return default
    return callback(*args)


def _connect_signal(source: object | None, name: str, slot) -> None:  # noqa: ANN001
    signal = getattr(source, name, None) if source is not None else None
    if signal is not None and hasattr(signal, "connect"):
        signal.connect(slot)


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
    ) -> None:
        super().__init__(parent)
        self._shell_window = shell_window
        self._scene_bridge = scene_bridge
        self._view_bridge = view_bridge
        self._canvas_source = getattr(shell_window, "graph_canvas_presenter", shell_window)

        _connect_signal(
            self._canvas_source,
            "graphics_preferences_changed",
            self.graphics_preferences_changed.emit,
        )
        _connect_signal(self._canvas_source, "snap_to_grid_changed", self.snap_to_grid_changed.emit)
        _connect_signal(scene_bridge, "nodes_changed", self.scene_nodes_changed.emit)
        _connect_signal(scene_bridge, "edges_changed", self.scene_edges_changed.emit)
        _connect_signal(scene_bridge, "selection_changed", self.scene_selection_changed.emit)
        _connect_signal(view_bridge, "view_state_changed", self.view_state_changed.emit)

    @property
    def shell_window(self) -> "ShellWindow | None":
        return self._shell_window

    @property
    def scene_bridge(self) -> "GraphSceneBridge | None":
        return self._scene_bridge

    @property
    def view_bridge(self) -> "ViewportBridge | None":
        return self._view_bridge

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_minimap_expanded(self) -> bool:
        return bool(_source_attr(self._canvas_source, "graphics_minimap_expanded", True))

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_show_grid(self) -> bool:
        return bool(_source_attr(self._canvas_source, "graphics_show_grid", True))

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_show_minimap(self) -> bool:
        return bool(_source_attr(self._canvas_source, "graphics_show_minimap", True))

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_node_shadow(self) -> bool:
        return bool(_source_attr(self._canvas_source, "graphics_node_shadow", True))

    @pyqtProperty(int, notify=graphics_preferences_changed)
    def graphics_shadow_strength(self) -> int:
        return int(_source_attr(self._canvas_source, "graphics_shadow_strength", 70))

    @pyqtProperty(int, notify=graphics_preferences_changed)
    def graphics_shadow_softness(self) -> int:
        return int(_source_attr(self._canvas_source, "graphics_shadow_softness", 50))

    @pyqtProperty(int, notify=graphics_preferences_changed)
    def graphics_shadow_offset(self) -> int:
        return int(_source_attr(self._canvas_source, "graphics_shadow_offset", 4))

    @pyqtProperty(bool, notify=snap_to_grid_changed)
    def snap_to_grid_enabled(self) -> bool:
        return bool(_source_attr(self._canvas_source, "snap_to_grid_enabled", False))

    @pyqtProperty(float, notify=snap_to_grid_changed)
    def snap_grid_size(self) -> float:
        return float(_source_attr(self._canvas_source, "snap_grid_size", 20.0))

    @pyqtProperty(float, notify=view_state_changed)
    def center_x(self) -> float:
        return float(_source_attr(self._view_bridge, "center_x", 0.0))

    @pyqtProperty(float, notify=view_state_changed)
    def center_y(self) -> float:
        return float(_source_attr(self._view_bridge, "center_y", 0.0))

    @pyqtProperty(float, notify=view_state_changed)
    def zoom_value(self) -> float:
        return float(_source_attr(self._view_bridge, "zoom_value", 1.0))

    @pyqtProperty("QVariantList", notify=scene_nodes_changed)
    def nodes_model(self) -> list[dict]:
        return _copy_list(_source_attr(self._scene_bridge, "nodes_model", []))

    @pyqtProperty("QVariantList", notify=scene_edges_changed)
    def edges_model(self) -> list[dict]:
        return _copy_list(_source_attr(self._scene_bridge, "edges_model", []))

    @pyqtProperty("QVariantMap", notify=scene_selection_changed)
    def selected_node_lookup(self) -> dict[str, bool]:
        return _copy_dict(_source_attr(self._scene_bridge, "selected_node_lookup", {}))

    @pyqtSlot(bool)
    def set_graphics_minimap_expanded(self, expanded: bool) -> None:
        _invoke(self._canvas_source, "set_graphics_minimap_expanded", bool(expanded))

    @pyqtSlot(float)
    def adjust_zoom(self, factor: float) -> None:
        _invoke(self._view_bridge, "adjust_zoom", float(factor))

    @pyqtSlot(float, float)
    def pan_by(self, delta_x: float, delta_y: float) -> None:
        _invoke(self._view_bridge, "pan_by", float(delta_x), float(delta_y))

    @pyqtSlot(float, float)
    def set_viewport_size(self, width: float, height: float) -> None:
        _invoke(self._view_bridge, "set_viewport_size", float(width), float(height))

    @pyqtSlot(str, result=bool)
    def request_open_subnode_scope(self, node_id: str) -> bool:
        return bool(_invoke(self._canvas_source, "request_open_subnode_scope", node_id, default=False))

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

    @pyqtSlot(str, bool)
    def select_node(self, node_id: str, additive: bool = False) -> None:
        _invoke(self._scene_bridge, "select_node", node_id, bool(additive))

    @pyqtSlot(str, str, "QVariant")
    def set_node_property(self, node_id: str, key: str, value: object) -> None:
        _invoke(self._scene_bridge, "set_node_property", node_id, key, value)

    @pyqtSlot(str, str, result=bool)
    def are_port_kinds_compatible(self, source_kind: str, target_kind: str) -> bool:
        return bool(
            _invoke(
                self._scene_bridge,
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
                self._scene_bridge,
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
                self._scene_bridge,
                "move_nodes_by_delta",
                node_ids,
                float(delta_x),
                float(delta_y),
                default=False,
            )
        )

    @pyqtSlot(str, float, float)
    def move_node(self, node_id: str, x: float, y: float) -> None:
        _invoke(self._scene_bridge, "move_node", node_id, float(x), float(y))

    @pyqtSlot(str, float, float)
    def resize_node(self, node_id: str, width: float, height: float) -> None:
        _invoke(self._scene_bridge, "resize_node", node_id, float(width), float(height))

    @pyqtSlot(str, float, float, float, float)
    def set_node_geometry(self, node_id: str, x: float, y: float, width: float, height: float) -> None:
        _invoke(
            self._scene_bridge,
            "set_node_geometry",
            node_id,
            float(x),
            float(y),
            float(width),
            float(height),
        )


__all__ = ["GraphCanvasBridge"]
