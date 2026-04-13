from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, cast

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot
from ea_node_editor.app_preferences import (
    effective_graph_node_icon_pixel_size,
    normalize_graph_node_icon_pixel_size_override,
)
from ea_node_editor.settings import DEFAULT_GRAPH_LABEL_PIXEL_SIZE, DEFAULT_GRAPHICS_SETTINGS

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
    from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge


class _SignalLike(Protocol):
    def connect(self, slot) -> object: ...  # noqa: ANN001


class _GraphCanvasStateSource(Protocol):
    graphics_preferences_changed: _SignalLike
    snap_to_grid_changed: _SignalLike
    graphics_minimap_expanded: bool
    graphics_show_grid: bool
    graphics_grid_style: str
    graphics_edge_crossing_style: str
    graphics_graph_label_pixel_size: int
    graphics_graph_node_icon_pixel_size_override: int | None
    graphics_node_title_icon_pixel_size: int
    graphics_show_minimap: bool
    graphics_show_port_labels: bool
    graphics_node_shadow: bool
    graphics_shadow_strength: int
    graphics_shadow_softness: int
    graphics_shadow_offset: int
    graphics_performance_mode: str
    graphics_expand_collision_avoidance: dict[str, Any]
    snap_to_grid_enabled: bool
    snap_grid_size: float


class _GraphCanvasSceneStateSource(Protocol):
    nodes_changed: _SignalLike
    edges_changed: _SignalLike
    selection_changed: _SignalLike
    workspace_changed: _SignalLike
    workspace_id: str
    nodes_model: list[dict[str, Any]]
    minimap_nodes_model: list[dict[str, Any]]
    backdrop_nodes_model: list[dict[str, Any]]
    workspace_scene_bounds_payload: dict[str, Any]
    edges_model: list[dict[str, Any]]
    selected_node_lookup: dict[str, bool]
    hide_locked_ports: bool
    hide_optional_ports: bool


class _GraphCanvasScenePolicySource(Protocol):
    def are_port_kinds_compatible(self, source_kind: str, target_kind: str) -> bool: ...

    def are_data_types_compatible(self, source_type: str, target_type: str) -> bool: ...


def _copy_list(value: object) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _copy_dict(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _source_attr(source: object | None, name: str, default: Any) -> Any:
    if source is None:
        return default
    return getattr(source, name, default)


def _invoke_bool(source: object | None, name: str, *args) -> bool:
    callback = getattr(source, name, None) if source is not None else None
    if not callable(callback):
        return False
    return bool(callback(*args))


def _invoke_value(source: object | None, name: str, *args) -> Any:
    callback = getattr(source, name, None) if source is not None else None
    if not callable(callback):
        return None
    return callback(*args)


def _connect_signal(source: object | None, name: str, slot) -> None:  # noqa: ANN001
    signal = getattr(source, name, None) if source is not None else None
    if signal is not None and hasattr(signal, "connect"):
        signal.connect(slot)


def _resolve_canvas_source(
    shell_window: "ShellWindow | None",
    canvas_source: _GraphCanvasStateSource | None,
) -> _GraphCanvasStateSource | None:
    if canvas_source is not None:
        return canvas_source
    if shell_window is None:
        return None
    return cast(_GraphCanvasStateSource, shell_window)


def _resolve_scene_state_source(scene_bridge: object | None) -> _GraphCanvasSceneStateSource | None:
    if scene_bridge is None:
        return None
    return cast(
        _GraphCanvasSceneStateSource,
        getattr(scene_bridge, "state_bridge", scene_bridge),
    )


def _resolve_scene_policy_source(scene_bridge: object | None) -> _GraphCanvasScenePolicySource | None:
    if scene_bridge is None:
        return None
    return cast(
        _GraphCanvasScenePolicySource,
        getattr(scene_bridge, "policy_bridge", scene_bridge),
    )


class GraphCanvasStateBridge(QObject):
    graphics_preferences_changed = pyqtSignal()
    snap_to_grid_changed = pyqtSignal()
    scene_nodes_changed = pyqtSignal()
    scene_edges_changed = pyqtSignal()
    scene_selection_changed = pyqtSignal()
    failure_highlight_changed = pyqtSignal()
    node_execution_state_changed = pyqtSignal()
    view_state_changed = pyqtSignal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        shell_window: "ShellWindow | None" = None,
        canvas_source: _GraphCanvasStateSource | None = None,
        scene_bridge: "GraphSceneBridge | None" = None,
        view_bridge: "ViewportBridge | None" = None,
    ) -> None:
        super().__init__(parent)
        self._shell_window = shell_window
        self._scene_bridge = scene_bridge
        self._view_bridge = view_bridge
        self._canvas_source = _resolve_canvas_source(shell_window, canvas_source)
        self._scene_state_source = _resolve_scene_state_source(scene_bridge)
        self._scene_policy_source = _resolve_scene_policy_source(scene_bridge)

        _connect_signal(
            self._canvas_source,
            "graphics_preferences_changed",
            self.graphics_preferences_changed.emit,
        )
        _connect_signal(self._canvas_source, "snap_to_grid_changed", self.snap_to_grid_changed.emit)
        _connect_signal(self._scene_state_source, "nodes_changed", self.scene_nodes_changed.emit)
        _connect_signal(self._scene_state_source, "edges_changed", self.scene_edges_changed.emit)
        _connect_signal(self._scene_state_source, "selection_changed", self.scene_selection_changed.emit)
        _connect_signal(self._scene_state_source, "workspace_changed", self.failure_highlight_changed.emit)
        _connect_signal(self._scene_state_source, "workspace_changed", self.node_execution_state_changed.emit)
        _connect_signal(shell_window, "run_failure_changed", self.failure_highlight_changed.emit)
        _connect_signal(shell_window, "node_execution_state_changed", self.node_execution_state_changed.emit)
        _connect_signal(view_bridge, "view_state_changed", self.view_state_changed.emit)

    @property
    def shell_window(self) -> "ShellWindow | None":
        return self._shell_window

    @property
    def canvas_source(self) -> _GraphCanvasStateSource | None:
        return self._canvas_source

    @property
    def scene_bridge(self) -> "GraphSceneBridge | None":
        return self._scene_bridge

    @property
    def scene_state_source(self) -> _GraphCanvasSceneStateSource | None:
        return self._scene_state_source

    @property
    def scene_policy_source(self) -> _GraphCanvasScenePolicySource | None:
        return self._scene_policy_source

    @property
    def view_bridge(self) -> "ViewportBridge | None":
        return self._view_bridge

    @pyqtProperty(QObject, constant=True)
    def viewport_bridge(self) -> "ViewportBridge | None":
        return self._view_bridge

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_minimap_expanded(self) -> bool:
        return bool(_source_attr(self._canvas_source, "graphics_minimap_expanded", True))

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_show_grid(self) -> bool:
        return bool(_source_attr(self._canvas_source, "graphics_show_grid", True))

    @pyqtProperty(str, notify=graphics_preferences_changed)
    def graphics_grid_style(self) -> str:
        return str(_source_attr(self._canvas_source, "graphics_grid_style", "lines"))

    @pyqtProperty(str, notify=graphics_preferences_changed)
    def graphics_edge_crossing_style(self) -> str:
        return str(_source_attr(self._canvas_source, "graphics_edge_crossing_style", "none"))

    @pyqtProperty(int, notify=graphics_preferences_changed)
    def graphics_graph_label_pixel_size(self) -> int:
        return int(
            _source_attr(
                self._canvas_source,
                "graphics_graph_label_pixel_size",
                DEFAULT_GRAPH_LABEL_PIXEL_SIZE,
            )
        )

    @pyqtProperty("QVariant", notify=graphics_preferences_changed)
    def graphics_graph_node_icon_pixel_size_override(self) -> int | None:
        value = _source_attr(
            self._canvas_source,
            "graphics_graph_node_icon_pixel_size_override",
            _source_attr(self._shell_window, "graphics_graph_node_icon_pixel_size_override", None),
        )
        return normalize_graph_node_icon_pixel_size_override(value)

    @pyqtProperty(int, notify=graphics_preferences_changed)
    def graphics_node_title_icon_pixel_size(self) -> int:
        value = _source_attr(
            self._canvas_source,
            "graphics_node_title_icon_pixel_size",
            _source_attr(self._shell_window, "graphics_node_title_icon_pixel_size", None),
        )
        return effective_graph_node_icon_pixel_size(
            self.graphics_graph_label_pixel_size,
            self.graphics_graph_node_icon_pixel_size_override if value is None else value,
        )

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_show_minimap(self) -> bool:
        return bool(_source_attr(self._canvas_source, "graphics_show_minimap", True))

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_show_port_labels(self) -> bool:
        return bool(_source_attr(self._canvas_source, "graphics_show_port_labels", True))

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

    @pyqtProperty(str, notify=graphics_preferences_changed)
    def graphics_performance_mode(self) -> str:
        return str(_source_attr(self._canvas_source, "graphics_performance_mode", "full_fidelity"))

    @pyqtProperty("QVariantMap", notify=graphics_preferences_changed)
    def graphics_expand_collision_avoidance(self) -> dict[str, Any]:
        default = DEFAULT_GRAPHICS_SETTINGS["interaction"]["expand_collision_avoidance"]
        value = _source_attr(self._canvas_source, "graphics_expand_collision_avoidance", None)
        if value is None:
            value = _source_attr(self._shell_window, "graphics_expand_collision_avoidance", default)
        return _copy_dict(value)

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
        payload = _source_attr(self._view_bridge, "visible_scene_rect_payload_cached", None)
        if payload is None:
            payload = _source_attr(self._view_bridge, "visible_scene_rect_payload", {})
        return _copy_dict(payload)

    @pyqtProperty("QVariantMap", notify=view_state_changed)
    def visible_scene_rect_payload_cached(self) -> dict[str, Any]:
        return self.visible_scene_rect_payload

    def _active_view_filters(self) -> tuple[bool, bool]:
        state_source = self._scene_state_source
        hide_locked_ports = getattr(state_source, "hide_locked_ports", None) if state_source is not None else None
        hide_optional_ports = getattr(state_source, "hide_optional_ports", None) if state_source is not None else None
        if hide_locked_ports is not None or hide_optional_ports is not None:
            return bool(hide_locked_ports), bool(hide_optional_ports)

        workspace = _invoke_value(self._scene_bridge, "_workspace_or_none")
        if workspace is None:
            try:
                workspace = _invoke_value(self._scene_bridge, "current_workspace")
            except RuntimeError:
                return False, False
        if workspace is None:
            return False, False
        views = getattr(workspace, "views", None)
        if not isinstance(views, dict) or not views:
            return False, False
        active_view_id = str(getattr(workspace, "active_view_id", "") or "")
        active_view = views.get(active_view_id)
        if active_view is None:
            active_view = next(iter(views.values()), None)
        if active_view is None:
            return False, False
        return (
            bool(getattr(active_view, "hide_locked_ports", False)),
            bool(getattr(active_view, "hide_optional_ports", False)),
        )

    def _set_active_view_filter(self, name: str, value: bool) -> bool:
        scene_bridge = self._scene_bridge
        if scene_bridge is None:
            return False
        command_source = getattr(scene_bridge, "command_bridge", scene_bridge)
        return _invoke_bool(command_source, name, bool(value))

    @pyqtProperty(bool, notify=scene_nodes_changed)
    def hide_locked_ports(self) -> bool:
        hide_locked_ports, _hide_optional_ports = self._active_view_filters()
        return hide_locked_ports

    @pyqtProperty(bool, notify=scene_nodes_changed)
    def hide_optional_ports(self) -> bool:
        _hide_locked_ports, hide_optional_ports = self._active_view_filters()
        return hide_optional_ports

    @pyqtProperty("QVariantList", notify=scene_nodes_changed)
    def nodes_model(self) -> list[dict]:
        return _copy_list(_source_attr(self._scene_state_source, "nodes_model", []))

    @pyqtProperty("QVariantList", notify=scene_nodes_changed)
    def minimap_nodes_model(self) -> list[dict]:
        return _copy_list(_source_attr(self._scene_state_source, "minimap_nodes_model", []))

    @pyqtProperty("QVariantList", notify=scene_nodes_changed)
    def backdrop_nodes_model(self) -> list[dict]:
        return _copy_list(_source_attr(self._scene_state_source, "backdrop_nodes_model", []))

    @pyqtProperty("QVariantMap", notify=scene_nodes_changed)
    def workspace_scene_bounds_payload(self) -> dict[str, Any]:
        return _copy_dict(_source_attr(self._scene_state_source, "workspace_scene_bounds_payload", {}))

    @pyqtProperty("QVariantList", notify=scene_edges_changed)
    def edges_model(self) -> list[dict]:
        return _copy_list(_source_attr(self._scene_state_source, "edges_model", []))

    @pyqtProperty("QVariantMap", notify=scene_selection_changed)
    def selected_node_lookup(self) -> dict[str, bool]:
        return _copy_dict(_source_attr(self._scene_state_source, "selected_node_lookup", {}))

    @pyqtSlot(bool, result=bool)
    def set_hide_locked_ports(self, hide_locked_ports: bool) -> bool:
        return self._set_active_view_filter("set_hide_locked_ports", hide_locked_ports)

    @pyqtSlot(bool, result=bool)
    def set_hide_optional_ports(self, hide_optional_ports: bool) -> bool:
        return self._set_active_view_filter("set_hide_optional_ports", hide_optional_ports)

    @pyqtProperty("QVariantMap", notify=failure_highlight_changed)
    def failed_node_lookup(self) -> dict[str, bool]:
        shell_window = self._shell_window
        if shell_window is None:
            return {}
        run_state = getattr(shell_window, "run_state", None)
        workspace_manager = getattr(shell_window, "workspace_manager", None)
        if run_state is None or workspace_manager is None:
            return {}
        failed_node_id = str(getattr(run_state, "failed_node_id", "") or "").strip()
        failed_workspace_id = str(getattr(run_state, "failed_workspace_id", "") or "").strip()
        active_workspace_id = str(workspace_manager.active_workspace_id() or "").strip()
        if not failed_node_id or failed_workspace_id != active_workspace_id:
            return {}
        return {failed_node_id: True}

    @pyqtProperty(int, notify=failure_highlight_changed)
    def failed_node_revision(self) -> int:
        shell_window = self._shell_window
        if shell_window is None:
            return 0
        run_state = getattr(shell_window, "run_state", None)
        if run_state is None:
            return 0
        return int(getattr(run_state, "failure_focus_revision", 0))

    @pyqtProperty(str, notify=failure_highlight_changed)
    def failed_node_title(self) -> str:
        shell_window = self._shell_window
        if shell_window is None:
            return ""
        run_state = getattr(shell_window, "run_state", None)
        if run_state is None:
            return ""
        return str(getattr(run_state, "failed_node_title", "") or "")

    def _active_workspace_id(self) -> str:
        workspace_id = str(_source_attr(self._scene_state_source, "workspace_id", "") or "").strip()
        if workspace_id:
            return workspace_id
        shell_window = self._shell_window
        if shell_window is None:
            return ""
        workspace_manager = getattr(shell_window, "workspace_manager", None)
        if workspace_manager is None:
            return ""
        return str(workspace_manager.active_workspace_id() or "").strip()

    def _run_state_lookup(self, workspace_attribute_name: str, ids_attribute_name: str) -> dict[str, bool]:
        shell_window = self._shell_window
        if shell_window is None:
            return {}
        run_state = getattr(shell_window, "run_state", None)
        if run_state is None:
            return {}
        active_workspace_id = self._active_workspace_id()
        execution_workspace_id = str(getattr(run_state, workspace_attribute_name, "") or "").strip()
        if not active_workspace_id or execution_workspace_id != active_workspace_id:
            return {}
        ids = getattr(run_state, ids_attribute_name, ())
        if not isinstance(ids, (set, frozenset, list, tuple)):
            return {}
        lookup: dict[str, bool] = {}
        for value in ids:
            normalized_value = str(value or "").strip()
            if normalized_value:
                lookup[normalized_value] = True
        return lookup

    def _node_execution_lookup(self, attribute_name: str) -> dict[str, bool]:
        return self._run_state_lookup("node_execution_workspace_id", attribute_name)

    def _node_execution_timing_lookup(self, attribute_name: str) -> dict[str, Any]:
        shell_window = self._shell_window
        if shell_window is None:
            return {}
        run_state = getattr(shell_window, "run_state", None)
        if run_state is None:
            return {}
        active_workspace_id = self._active_workspace_id()
        execution_workspace_id = str(getattr(run_state, "node_execution_workspace_id", "") or "").strip()
        if not active_workspace_id or execution_workspace_id != active_workspace_id:
            return {}
        return _copy_dict(getattr(run_state, attribute_name, {}))

    def _active_workspace_lookup(self, attribute_name: str) -> dict[str, Any]:
        shell_window = self._shell_window
        if shell_window is None:
            return {}
        run_state = getattr(shell_window, "run_state", None)
        if run_state is None:
            return {}
        active_workspace_id = self._active_workspace_id()
        if not active_workspace_id:
            return {}
        lookup_by_workspace = getattr(run_state, attribute_name, None)
        if not isinstance(lookup_by_workspace, dict):
            return {}
        return _copy_dict(lookup_by_workspace.get(active_workspace_id, {}))

    @pyqtProperty("QVariantMap", notify=node_execution_state_changed)
    def running_node_lookup(self) -> dict[str, bool]:
        return self._node_execution_lookup("running_node_ids")

    @pyqtProperty("QVariantMap", notify=node_execution_state_changed)
    def completed_node_lookup(self) -> dict[str, bool]:
        return self._node_execution_lookup("completed_node_ids")

    @pyqtProperty("QVariantMap", notify=node_execution_state_changed)
    def running_node_started_at_ms_lookup(self) -> dict[str, Any]:
        return self._node_execution_timing_lookup("running_node_started_at_epoch_ms_by_node_id")

    @pyqtProperty("QVariantMap", notify=node_execution_state_changed)
    def node_elapsed_ms_lookup(self) -> dict[str, Any]:
        return self._active_workspace_lookup("cached_node_elapsed_ms_by_workspace_id")

    @pyqtProperty("QVariantMap", notify=node_execution_state_changed)
    def progressed_execution_edge_lookup(self) -> dict[str, bool]:
        return self._run_state_lookup(
            "execution_edge_workspace_id",
            "progressed_execution_edge_ids",
        )

    @pyqtProperty(int, notify=node_execution_state_changed)
    def node_execution_revision(self) -> int:
        shell_window = self._shell_window
        if shell_window is None:
            return 0
        run_state = getattr(shell_window, "run_state", None)
        if run_state is None:
            return 0
        return int(getattr(run_state, "node_execution_revision", 0))

    @pyqtSlot(str, str, result=bool)
    def are_port_kinds_compatible(self, source_kind: str, target_kind: str) -> bool:
        return _invoke_bool(
            self._scene_policy_source,
            "are_port_kinds_compatible",
            source_kind,
            target_kind,
        )

    @pyqtSlot(str, str, result=bool)
    def are_data_types_compatible(self, source_type: str, target_type: str) -> bool:
        return _invoke_bool(
            self._scene_policy_source,
            "are_data_types_compatible",
            source_type,
            target_type,
        )


__all__ = ["GraphCanvasStateBridge"]
