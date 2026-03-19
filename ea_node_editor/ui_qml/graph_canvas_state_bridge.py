from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
    from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge


def _copy_list(value: object) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _copy_dict(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _source_attr(source: object | None, name: str, default: Any) -> Any:
    if source is None:
        return default
    return getattr(source, name, default)


def _connect_signal(source: object | None, name: str, slot) -> None:  # noqa: ANN001
    signal = getattr(source, name, None) if source is not None else None
    if signal is not None and hasattr(signal, "connect"):
        signal.connect(slot)


class GraphCanvasStateBridge(QObject):
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

    @pyqtProperty("QVariantMap", notify=view_state_changed)
    def visible_scene_rect_payload(self) -> dict[str, Any]:
        return _copy_dict(_source_attr(self._view_bridge, "visible_scene_rect_payload", {}))

    @pyqtProperty("QVariantList", notify=scene_nodes_changed)
    def nodes_model(self) -> list[dict]:
        return _copy_list(_source_attr(self._scene_bridge, "nodes_model", []))

    @pyqtProperty("QVariantList", notify=scene_nodes_changed)
    def minimap_nodes_model(self) -> list[dict]:
        return _copy_list(_source_attr(self._scene_bridge, "minimap_nodes_model", []))

    @pyqtProperty("QVariantMap", notify=scene_nodes_changed)
    def workspace_scene_bounds_payload(self) -> dict[str, Any]:
        return _copy_dict(_source_attr(self._scene_bridge, "workspace_scene_bounds_payload", {}))

    @pyqtProperty("QVariantList", notify=scene_edges_changed)
    def edges_model(self) -> list[dict]:
        return _copy_list(_source_attr(self._scene_bridge, "edges_model", []))

    @pyqtProperty("QVariantMap", notify=scene_selection_changed)
    def selected_node_lookup(self) -> dict[str, bool]:
        return _copy_dict(_source_attr(self._scene_bridge, "selected_node_lookup", {}))


__all__ = ["GraphCanvasStateBridge"]
