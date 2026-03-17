from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

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
        scene_bridge: "GraphSceneBridge | None" = None,
        view_bridge: "ViewportBridge | None" = None,
    ) -> None:
        super().__init__(parent)
        self._scene_bridge = scene_bridge
        self._view_bridge = view_bridge

        self._connect_scene_signal("nodes_changed", self.scene_nodes_changed.emit)
        self._connect_scene_signal("edges_changed", self.scene_edges_changed.emit)
        if not self._connect_scene_signal("selection_changed", self.scene_selection_changed.emit):
            self._connect_scene_signal("nodes_changed", self.scene_selection_changed.emit)
        if not self._connect_view_signal("view_state_changed", self.view_state_changed.emit):
            self._connect_view_signal("zoom_changed", self.view_state_changed.emit)
            self._connect_view_signal("center_changed", self.view_state_changed.emit)
        self._connect_shell_signal("graphics_preferences_changed", self.graphics_preferences_changed.emit)
        self._connect_shell_signal("snap_to_grid_changed", self.snap_to_grid_changed.emit)

    @property
    def shell_window(self) -> "ShellWindow | None":
        return self._shell_host()

    @property
    def scene_bridge(self) -> "GraphSceneBridge | None":
        return self._scene_bridge

    @property
    def view_bridge(self) -> "ViewportBridge | None":
        return self._view_bridge

    def _shell_host(self) -> "ShellWindow | None":
        parent = self.parent()
        if parent is None:
            return None
        direct_host = self._shell_candidate(parent)
        if direct_host is not None:
            return direct_host
        return self._shell_candidate(getattr(parent, "shell_window", None))

    @staticmethod
    def _shell_candidate(candidate: object | None) -> "ShellWindow | None":
        if candidate is None:
            return None
        if any(hasattr(candidate, name) for name in ("graphics_preferences_changed", "request_open_subnode_scope")):
            return candidate
        return None

    @staticmethod
    def _connect_signal(source: object | None, signal_name: str, callback) -> bool:  # noqa: ANN001
        if source is None:
            return False
        signal = getattr(source, signal_name, None)
        if signal is not None and hasattr(signal, "connect"):
            signal.connect(callback)
            return True
        return False

    def _connect_shell_signal(self, signal_name: str, callback) -> bool:  # noqa: ANN001
        return self._connect_signal(self.shell_window, signal_name, callback)

    def _connect_scene_signal(self, signal_name: str, callback) -> bool:  # noqa: ANN001
        return self._connect_signal(self._scene_bridge, signal_name, callback)

    def _connect_view_signal(self, signal_name: str, callback) -> bool:  # noqa: ANN001
        return self._connect_signal(self._view_bridge, signal_name, callback)

    @staticmethod
    def _source_value(source: object | None, name: str, default):
        if source is None:
            return default
        return getattr(source, name, default)

    @staticmethod
    def _call_source(source: object | None, name: str, *args):
        if source is None:
            return None
        method = getattr(source, name, None)
        if method is None:
            return None
        return method(*args)

    def _shell_value(self, name: str, default):
        return self._source_value(self.shell_window, name, default)

    def _scene_value(self, name: str, default):
        return self._source_value(self._scene_bridge, name, default)

    def _view_value(self, name: str, default):
        return self._source_value(self._view_bridge, name, default)

    def _call_shell(self, name: str, *args):
        return self._call_source(self.shell_window, name, *args)

    def _call_scene(self, name: str, *args):
        return self._call_source(self._scene_bridge, name, *args)

    def _call_view(self, name: str, *args):
        return self._call_source(self._view_bridge, name, *args)

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_minimap_expanded(self) -> bool:
        return bool(self._shell_value("graphics_minimap_expanded", True))

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_show_grid(self) -> bool:
        return bool(self._shell_value("graphics_show_grid", True))

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_show_minimap(self) -> bool:
        return bool(self._shell_value("graphics_show_minimap", True))

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_node_shadow(self) -> bool:
        return bool(self._shell_value("graphics_node_shadow", True))

    @pyqtProperty(int, notify=graphics_preferences_changed)
    def graphics_shadow_strength(self) -> int:
        return int(self._shell_value("graphics_shadow_strength", 70))

    @pyqtProperty(int, notify=graphics_preferences_changed)
    def graphics_shadow_softness(self) -> int:
        return int(self._shell_value("graphics_shadow_softness", 50))

    @pyqtProperty(int, notify=graphics_preferences_changed)
    def graphics_shadow_offset(self) -> int:
        return int(self._shell_value("graphics_shadow_offset", 4))

    @pyqtProperty(bool, notify=snap_to_grid_changed)
    def snap_to_grid_enabled(self) -> bool:
        return bool(self._shell_value("snap_to_grid_enabled", False))

    @pyqtProperty(float, notify=snap_to_grid_changed)
    def snap_grid_size(self) -> float:
        return float(self._shell_value("snap_grid_size", 20.0))

    @pyqtProperty(float, notify=view_state_changed)
    def center_x(self) -> float:
        return float(self._view_value("center_x", 0.0))

    @pyqtProperty(float, notify=view_state_changed)
    def center_y(self) -> float:
        return float(self._view_value("center_y", 0.0))

    @pyqtProperty(float, notify=view_state_changed)
    def zoom_value(self) -> float:
        return float(self._view_value("zoom_value", 1.0))

    @pyqtProperty("QVariantList", notify=scene_nodes_changed)
    def nodes_model(self) -> list[dict]:
        nodes = self._scene_value("nodes_model", [])
        return list(nodes) if isinstance(nodes, list) else []

    @pyqtProperty("QVariantList", notify=scene_edges_changed)
    def edges_model(self) -> list[dict]:
        edges = self._scene_value("edges_model", [])
        return list(edges) if isinstance(edges, list) else []

    @pyqtProperty("QVariantMap", notify=scene_selection_changed)
    def selected_node_lookup(self) -> dict[str, bool]:
        lookup = self._scene_value("selected_node_lookup", {})
        return dict(lookup) if isinstance(lookup, dict) else {}

    @pyqtSlot(bool)
    def set_graphics_minimap_expanded(self, expanded: bool) -> None:
        self._call_shell("set_graphics_minimap_expanded", bool(expanded))

    @pyqtSlot(float)
    def adjust_zoom(self, factor: float) -> None:
        self._call_view("adjust_zoom", float(factor))

    @pyqtSlot(float, float)
    def pan_by(self, delta_x: float, delta_y: float) -> None:
        self._call_view("pan_by", float(delta_x), float(delta_y))

    @pyqtSlot(float, float)
    def set_viewport_size(self, width: float, height: float) -> None:
        self._call_view("set_viewport_size", float(width), float(height))

    @pyqtSlot(str, result=bool)
    def request_open_subnode_scope(self, node_id: str) -> bool:
        return bool(self._call_shell("request_open_subnode_scope", str(node_id)))

    @pyqtSlot(str, str, str, result=str)
    def browse_node_property_path(self, node_id: str, key: str, current_path: str) -> str:
        return str(
            self._call_shell(
                "browse_node_property_path",
                str(node_id),
                str(key),
                str(current_path),
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
            self._call_shell(
                "request_drop_node_from_library",
                str(type_id),
                float(scene_x),
                float(scene_y),
                str(target_mode),
                str(target_node_id),
                str(target_port_key),
                str(target_edge_id),
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
            self._call_shell(
                "request_connect_ports",
                str(source_node_id),
                str(source_port_key),
                str(target_node_id),
                str(target_port_key),
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
            self._call_shell(
            "request_open_connection_quick_insert",
            str(node_id),
            str(port_key),
            float(cursor_scene_x),
            float(cursor_scene_y),
            float(overlay_x),
            float(overlay_y),
        )
        )

    @pyqtSlot(str)
    @pyqtSlot(str, bool)
    def select_node(self, node_id: str, additive: bool = False) -> None:
        self._call_scene("select_node", str(node_id), bool(additive))

    @pyqtSlot(str, str, "QVariant")
    def set_node_property(self, node_id: str, key: str, value) -> None:
        self._call_scene("set_node_property", str(node_id), str(key), value)

    @pyqtSlot(str, str, result=bool)
    def are_port_kinds_compatible(self, source_kind: str, target_kind: str) -> bool:
        return bool(
            self._call_scene(
                "are_port_kinds_compatible",
                str(source_kind),
                str(target_kind),
            )
        )

    @pyqtSlot(str, str, result=bool)
    def are_data_types_compatible(self, source_type: str, target_type: str) -> bool:
        return bool(
            self._call_scene(
                "are_data_types_compatible",
                str(source_type),
                str(target_type),
            )
        )

    @pyqtSlot("QVariantList", float, float, result=bool)
    def move_nodes_by_delta(self, node_ids: list, delta_x: float, delta_y: float) -> bool:
        result = self._call_scene(
            "move_nodes_by_delta",
            node_ids,
            float(delta_x),
            float(delta_y),
        )
        return bool(result)

    @pyqtSlot(str, float, float)
    def move_node(self, node_id: str, x: float, y: float) -> None:
        self._call_scene("move_node", str(node_id), float(x), float(y))

    @pyqtSlot(str, float, float)
    def resize_node(self, node_id: str, width: float, height: float) -> None:
        self._call_scene("resize_node", str(node_id), float(width), float(height))


__all__ = ["GraphCanvasBridge"]
