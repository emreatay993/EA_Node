from __future__ import annotations

from typing import Any, Protocol

from PyQt6.QtCore import QObject


class _SignalLike(Protocol):
    def connect(self, slot) -> object: ...  # noqa: ANN001


def _presenter_parent(host: object, parent: QObject | None) -> QObject | None:
    if parent is not None:
        return parent
    return host if isinstance(host, QObject) else None


class _ShellLibraryPresenterHostProtocol(Protocol):
    node_library_changed: _SignalLike
    library_pane_reset_requested: _SignalLike
    graph_search_changed: _SignalLike
    connection_quick_insert_changed: _SignalLike
    graph_hint_changed: _SignalLike
    registry: Any
    workspace_library_controller: Any
    library_filter_state: Any
    search_scope_controller: Any
    search_scope_state: Any
    model: Any
    workspace_manager: Any
    scene: Any
    _CONNECTION_QUICK_INSERT_LIMIT: int
    _CONNECTION_QUICK_INSERT_OFFSET: float


class _ShellWorkspacePresenterHostProtocol(Protocol):
    project_meta_changed: _SignalLike
    workspace_state_changed: _SignalLike
    graphics_preferences_changed: _SignalLike
    run_controls_changed: _SignalLike
    project_path: str
    workspace_ui_state: Any
    workspace_manager: Any
    model: Any
    scene: Any
    run_state: Any
    run_controller: Any
    project_session_controller: Any
    search_scope_controller: Any
    search_scope_state: Any
    workspace_library_controller: Any
    shell_host_presenter: Any
    shell_inspector_presenter: Any
    graph_theme_bridge: Any

    def set_graphics_performance_mode(self, mode: str) -> None: ...

    def set_graphics_floating_toolbar_style(self, style: str) -> None: ...

    def set_graphics_floating_toolbar_size(self, size: str) -> None: ...


class _ShellInspectorPresenterHostProtocol(Protocol):
    selected_node_changed: _SignalLike
    workspace_state_changed: _SignalLike
    workspace_library_controller: Any
    model: Any
    workspace_manager: Any
    registry: Any
    _SUBNODE_PIN_TYPE_IDS: set[str]
    project_path: str
    shell_host_presenter: Any

    def _repair_property_path_dialog(
        self,
        *,
        node_type_id: str,
        property_key: str,
        property_label: str,
        current_path: str,
    ) -> str: ...


class _GraphCanvasPresenterHostProtocol(Protocol):
    graphics_preferences_changed: _SignalLike
    snap_to_grid_changed: _SignalLike
    search_scope_state: Any
    workspace_ui_state: Any
    _SNAP_GRID_SIZE: float
    search_scope_controller: Any
    app_preferences_controller: Any
    scene: Any
    workspace_library_controller: Any

    def show_graph_hint(self, message: str, timeout_ms: int = 3600) -> None: ...

    def clear_graph_hint(self) -> None: ...


class _GraphCanvasHostPresenterHostProtocol(Protocol):
    search_scope_controller: Any
    scene: Any
    shell_host_presenter: Any
    workspace_library_controller: Any
