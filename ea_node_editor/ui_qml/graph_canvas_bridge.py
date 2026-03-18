from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
    from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge


def _copy_list(value: object) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _copy_dict(value: object) -> dict[str, bool]:
    return dict(value) if isinstance(value, dict) else {}


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

        self._graphics_minimap_expanded: Callable[[], bool] = lambda: True
        self._graphics_show_grid: Callable[[], bool] = lambda: True
        self._graphics_show_minimap: Callable[[], bool] = lambda: True
        self._graphics_node_shadow: Callable[[], bool] = lambda: True
        self._graphics_shadow_strength: Callable[[], int] = lambda: 70
        self._graphics_shadow_softness: Callable[[], int] = lambda: 50
        self._graphics_shadow_offset: Callable[[], int] = lambda: 4
        self._snap_to_grid_enabled: Callable[[], bool] = lambda: False
        self._snap_grid_size: Callable[[], float] = lambda: 20.0
        self._center_x: Callable[[], float] = lambda: 0.0
        self._center_y: Callable[[], float] = lambda: 0.0
        self._zoom_value: Callable[[], float] = lambda: 1.0
        self._nodes_model: Callable[[], list[dict[str, Any]]] = lambda: []
        self._edges_model: Callable[[], list[dict[str, Any]]] = lambda: []
        self._selected_node_lookup: Callable[[], dict[str, bool]] = lambda: {}

        self._set_graphics_minimap_expanded: Callable[[bool], None] = lambda _expanded: None
        self._adjust_zoom: Callable[[float], None] = lambda _factor: None
        self._pan_by: Callable[[float, float], None] = lambda _delta_x, _delta_y: None
        self._set_viewport_size: Callable[[float, float], None] = (
            lambda _width, _height: None
        )
        self._request_open_subnode_scope: Callable[[str], bool] = lambda _node_id: False
        self._browse_node_property_path: Callable[[str, str, str], str] = (
            lambda _node_id, _key, _current_path: ""
        )
        self._request_drop_node_from_library: Callable[[str, float, float, str, str, str, str], bool] = (
            lambda _type_id, _scene_x, _scene_y, _target_mode, _target_node_id, _target_port_key, _target_edge_id: False
        )
        self._request_connect_ports: Callable[[str, str, str, str], bool] = (
            lambda _source_node_id, _source_port_key, _target_node_id, _target_port_key: False
        )
        self._request_open_connection_quick_insert: Callable[[str, str, float, float, float, float], bool] = (
            lambda _node_id, _port_key, _cursor_scene_x, _cursor_scene_y, _overlay_x, _overlay_y: False
        )
        self._select_node: Callable[[str, bool], None] = lambda _node_id, _additive=False: None
        self._set_node_property: Callable[[str, str, object], None] = (
            lambda _node_id, _key, _value: None
        )
        self._are_port_kinds_compatible: Callable[[str, str], bool] = (
            lambda _source_kind, _target_kind: False
        )
        self._are_data_types_compatible: Callable[[str, str], bool] = (
            lambda _source_type, _target_type: False
        )
        self._move_nodes_by_delta: Callable[[list, float, float], bool] = (
            lambda _node_ids, _delta_x, _delta_y: False
        )
        self._move_node: Callable[[str, float, float], None] = lambda _node_id, _x, _y: None
        self._resize_node: Callable[[str, float, float], None] = (
            lambda _node_id, _width, _height: None
        )
        self._set_node_geometry: Callable[[str, float, float, float, float], None] = (
            lambda _node_id, _x, _y, _width, _height: None
        )

        if shell_window is not None:
            self._graphics_minimap_expanded = lambda: bool(shell_window.graphics_minimap_expanded)
            self._graphics_show_grid = lambda: bool(shell_window.graphics_show_grid)
            self._graphics_show_minimap = lambda: bool(shell_window.graphics_show_minimap)
            self._graphics_node_shadow = lambda: bool(shell_window.graphics_node_shadow)
            self._graphics_shadow_strength = lambda: int(shell_window.graphics_shadow_strength)
            self._graphics_shadow_softness = lambda: int(shell_window.graphics_shadow_softness)
            self._graphics_shadow_offset = lambda: int(shell_window.graphics_shadow_offset)
            self._snap_to_grid_enabled = lambda: bool(shell_window.snap_to_grid_enabled)
            self._snap_grid_size = lambda: float(shell_window.snap_grid_size)

            self._set_graphics_minimap_expanded = shell_window.set_graphics_minimap_expanded
            self._request_open_subnode_scope = shell_window.request_open_subnode_scope
            self._browse_node_property_path = shell_window.browse_node_property_path
            self._request_drop_node_from_library = shell_window.request_drop_node_from_library
            self._request_connect_ports = shell_window.request_connect_ports
            self._request_open_connection_quick_insert = shell_window.request_open_connection_quick_insert

            shell_window.graphics_preferences_changed.connect(self.graphics_preferences_changed.emit)
            shell_window.snap_to_grid_changed.connect(self.snap_to_grid_changed.emit)

        if scene_bridge is not None:
            self._nodes_model = lambda: _copy_list(scene_bridge.nodes_model)
            self._edges_model = lambda: _copy_list(scene_bridge.edges_model)
            self._selected_node_lookup = lambda: _copy_dict(scene_bridge.selected_node_lookup)

            self._select_node = scene_bridge.select_node
            self._set_node_property = scene_bridge.set_node_property
            self._are_port_kinds_compatible = scene_bridge.are_port_kinds_compatible
            self._are_data_types_compatible = scene_bridge.are_data_types_compatible
            self._move_nodes_by_delta = scene_bridge.move_nodes_by_delta
            self._move_node = scene_bridge.move_node
            self._resize_node = scene_bridge.resize_node
            self._set_node_geometry = scene_bridge.set_node_geometry

            scene_bridge.nodes_changed.connect(self.scene_nodes_changed.emit)
            scene_bridge.edges_changed.connect(self.scene_edges_changed.emit)
            scene_bridge.selection_changed.connect(self.scene_selection_changed.emit)

        if view_bridge is not None:
            self._center_x = lambda: float(view_bridge.center_x)
            self._center_y = lambda: float(view_bridge.center_y)
            self._zoom_value = lambda: float(view_bridge.zoom_value)

            self._adjust_zoom = view_bridge.adjust_zoom
            self._pan_by = view_bridge.pan_by
            self._set_viewport_size = view_bridge.set_viewport_size

            view_bridge.view_state_changed.connect(self.view_state_changed.emit)

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
        return self._graphics_minimap_expanded()

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_show_grid(self) -> bool:
        return self._graphics_show_grid()

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_show_minimap(self) -> bool:
        return self._graphics_show_minimap()

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_node_shadow(self) -> bool:
        return self._graphics_node_shadow()

    @pyqtProperty(int, notify=graphics_preferences_changed)
    def graphics_shadow_strength(self) -> int:
        return self._graphics_shadow_strength()

    @pyqtProperty(int, notify=graphics_preferences_changed)
    def graphics_shadow_softness(self) -> int:
        return self._graphics_shadow_softness()

    @pyqtProperty(int, notify=graphics_preferences_changed)
    def graphics_shadow_offset(self) -> int:
        return self._graphics_shadow_offset()

    @pyqtProperty(bool, notify=snap_to_grid_changed)
    def snap_to_grid_enabled(self) -> bool:
        return self._snap_to_grid_enabled()

    @pyqtProperty(float, notify=snap_to_grid_changed)
    def snap_grid_size(self) -> float:
        return self._snap_grid_size()

    @pyqtProperty(float, notify=view_state_changed)
    def center_x(self) -> float:
        return self._center_x()

    @pyqtProperty(float, notify=view_state_changed)
    def center_y(self) -> float:
        return self._center_y()

    @pyqtProperty(float, notify=view_state_changed)
    def zoom_value(self) -> float:
        return self._zoom_value()

    @pyqtProperty("QVariantList", notify=scene_nodes_changed)
    def nodes_model(self) -> list[dict]:
        return self._nodes_model()

    @pyqtProperty("QVariantList", notify=scene_edges_changed)
    def edges_model(self) -> list[dict]:
        return self._edges_model()

    @pyqtProperty("QVariantMap", notify=scene_selection_changed)
    def selected_node_lookup(self) -> dict[str, bool]:
        return self._selected_node_lookup()

    @pyqtSlot(bool)
    def set_graphics_minimap_expanded(self, expanded: bool) -> None:
        self._set_graphics_minimap_expanded(bool(expanded))

    @pyqtSlot(float)
    def adjust_zoom(self, factor: float) -> None:
        self._adjust_zoom(float(factor))

    @pyqtSlot(float, float)
    def pan_by(self, delta_x: float, delta_y: float) -> None:
        self._pan_by(float(delta_x), float(delta_y))

    @pyqtSlot(float, float)
    def set_viewport_size(self, width: float, height: float) -> None:
        self._set_viewport_size(float(width), float(height))

    @pyqtSlot(str, result=bool)
    def request_open_subnode_scope(self, node_id: str) -> bool:
        return bool(self._request_open_subnode_scope(str(node_id)))

    @pyqtSlot(str, str, str, result=str)
    def browse_node_property_path(self, node_id: str, key: str, current_path: str) -> str:
        return str(self._browse_node_property_path(str(node_id), str(key), str(current_path)) or "")

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
            self._request_drop_node_from_library(
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
            self._request_connect_ports(
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
            self._request_open_connection_quick_insert(
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
        self._select_node(str(node_id), bool(additive))

    @pyqtSlot(str, str, "QVariant")
    def set_node_property(self, node_id: str, key: str, value) -> None:
        self._set_node_property(str(node_id), str(key), value)

    @pyqtSlot(str, str, result=bool)
    def are_port_kinds_compatible(self, source_kind: str, target_kind: str) -> bool:
        return bool(self._are_port_kinds_compatible(str(source_kind), str(target_kind)))

    @pyqtSlot(str, str, result=bool)
    def are_data_types_compatible(self, source_type: str, target_type: str) -> bool:
        return bool(self._are_data_types_compatible(str(source_type), str(target_type)))

    @pyqtSlot("QVariantList", float, float, result=bool)
    def move_nodes_by_delta(self, node_ids: list, delta_x: float, delta_y: float) -> bool:
        result = self._move_nodes_by_delta(
            node_ids,
            float(delta_x),
            float(delta_y),
        )
        return bool(result)

    @pyqtSlot(str, float, float)
    def move_node(self, node_id: str, x: float, y: float) -> None:
        self._move_node(str(node_id), float(x), float(y))

    @pyqtSlot(str, float, float)
    def resize_node(self, node_id: str, width: float, height: float) -> None:
        self._resize_node(str(node_id), float(width), float(height))

    @pyqtSlot(str, float, float, float, float)
    def set_node_geometry(self, node_id: str, x: float, y: float, width: float, height: float) -> None:
        self._set_node_geometry(
            str(node_id),
            float(x),
            float(y),
            float(width),
            float(height),
        )


__all__ = ["GraphCanvasBridge"]
