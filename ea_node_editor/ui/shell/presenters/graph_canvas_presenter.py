from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal

from .contracts import _GraphCanvasPresenterHostProtocol, _presenter_parent

if TYPE_CHECKING:
    from .inspector_presenter import ShellInspectorPresenter
    from .library_presenter import ShellLibraryPresenter
    from .workspace_presenter import ShellWorkspacePresenter


class GraphCanvasPresenter(QObject):
    graphics_preferences_changed = pyqtSignal()
    snap_to_grid_changed = pyqtSignal()

    def __init__(
        self,
        host: _GraphCanvasPresenterHostProtocol,
        *,
        parent: QObject | None = None,
        workspace_presenter: "ShellWorkspacePresenter",
        library_presenter: "ShellLibraryPresenter",
        inspector_presenter: "ShellInspectorPresenter",
    ) -> None:
        super().__init__(_presenter_parent(host, parent))
        self._host = host
        self._workspace_presenter = workspace_presenter
        self._library_presenter = library_presenter
        self._inspector_presenter = inspector_presenter
        host.graphics_preferences_changed.connect(self.graphics_preferences_changed.emit)
        host.snap_to_grid_changed.connect(self.snap_to_grid_changed.emit)

    @property
    def graphics_minimap_expanded(self) -> bool: return bool(self._host.search_scope_state.graphics_minimap_expanded)

    @property
    def graphics_show_grid(self) -> bool: return bool(self._host.workspace_ui_state.show_grid)

    @property
    def graphics_grid_style(self) -> str: return str(self._host.workspace_ui_state.grid_style)

    @property
    def graphics_show_minimap(self) -> bool: return bool(self._host.workspace_ui_state.show_minimap)

    @property
    def graphics_edge_crossing_style(self) -> str: return str(self._host.workspace_ui_state.edge_crossing_style)

    @property
    def graphics_graph_label_pixel_size(self) -> int:
        return int(self._host.workspace_ui_state.graph_label_pixel_size)

    @property
    def graphics_graph_node_icon_pixel_size_override(self) -> int | None:
        return self._host.workspace_ui_state.graph_node_icon_pixel_size_override

    @property
    def graphics_node_title_icon_pixel_size(self) -> int:
        return int(self._host.workspace_ui_state.node_title_icon_pixel_size)

    @property
    def graphics_show_port_labels(self) -> bool: return bool(self._host.workspace_ui_state.show_port_labels)

    @property
    def graphics_node_shadow(self) -> bool: return bool(self._host.workspace_ui_state.node_shadow)

    @property
    def graphics_shadow_strength(self) -> int: return int(self._host.workspace_ui_state.shadow_strength)

    @property
    def graphics_shadow_softness(self) -> int: return int(self._host.workspace_ui_state.shadow_softness)

    @property
    def graphics_shadow_offset(self) -> int: return int(self._host.workspace_ui_state.shadow_offset)

    @property
    def graphics_performance_mode(self) -> str: return str(self._host.workspace_ui_state.graphics_performance_mode)

    @property
    def snap_to_grid_enabled(self) -> bool: return bool(self._host.search_scope_state.snap_to_grid_enabled)

    @property
    def snap_grid_size(self) -> float: return float(self._host._SNAP_GRID_SIZE)

    def set_snap_to_grid_enabled(self, enabled: bool) -> None:
        self._host.search_scope_controller.set_snap_to_grid_enabled(enabled)

    def set_graphics_minimap_expanded(self, expanded: bool) -> None:
        self._host.search_scope_controller.set_graphics_minimap_expanded(expanded)

    def set_graphics_show_port_labels(self, show_port_labels: bool) -> None:
        self._host.app_preferences_controller.update_graphics_settings(
            {"canvas": {"show_port_labels": bool(show_port_labels)}},
            host=self._host,
        )

    def set_graphics_performance_mode(self, mode: str) -> None:
        self._host.app_preferences_controller.update_graphics_settings(
            {"performance": {"mode": str(mode)}},
            host=self._host,
        )

    def request_open_subnode_scope(self, node_id: str) -> bool:
        normalized_node_id = str(node_id).strip()
        if not normalized_node_id:
            return False
        return bool(
            self._host.search_scope_controller.navigate_scope(
                lambda: self._host.scene.open_subnode_scope(normalized_node_id)
            )
        )

    def browse_node_property_path(self, node_id: str, key: str, current_path: str) -> str:
        return self._inspector_presenter.browse_node_property_path(node_id, key, current_path)

    def pick_node_property_color(self, node_id: str, key: str, current_value: str) -> str:
        return self._inspector_presenter.pick_node_property_color(node_id, key, current_value)

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
        result = self._host.workspace_library_controller.request_drop_node_from_library(
            type_id,
            scene_x,
            scene_y,
            target_mode,
            target_node_id,
            target_port_key,
            target_edge_id,
        )
        return bool(result.payload)

    def request_connect_ports(self, node_a_id: str, port_a: str, node_b_id: str, port_b: str) -> bool:
        result = self._host.workspace_library_controller.request_connect_ports(node_a_id, port_a, node_b_id, port_b)
        if not result.payload and str(result.message or "").strip():
            self.show_graph_hint(str(result.message), 2400)
        return bool(result.payload)

    def show_graph_hint(self, message: str, timeout_ms: int = 3600) -> None:
        self._host.show_graph_hint(message, timeout_ms)

    def clear_graph_hint(self) -> None:
        self._host.clear_graph_hint()

    def request_open_connection_quick_insert(
        self,
        node_id: str,
        port_key: str,
        scene_x: float,
        scene_y: float,
        overlay_x: float,
        overlay_y: float,
    ) -> bool:
        return bool(
            self._library_presenter.request_open_connection_quick_insert(
                node_id,
                port_key,
                scene_x,
                scene_y,
                overlay_x,
                overlay_y,
            )
        )

    def request_open_canvas_quick_insert(
        self,
        scene_x: float,
        scene_y: float,
        overlay_x: float,
        overlay_y: float,
    ) -> None:
        self._library_presenter.request_open_canvas_quick_insert(scene_x, scene_y, overlay_x, overlay_y)


__all__ = ["GraphCanvasPresenter"]
