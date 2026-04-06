from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow
    from ea_node_editor.ui_qml.console_model import ConsoleModel
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
    from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge
    from ea_node_editor.ui_qml.workspace_tabs_model import WorkspaceTabsModel


class _SignalLike(Protocol):
    def connect(self, slot) -> object: ...  # noqa: ANN001


class _ShellWorkspaceSource(Protocol):
    project_meta_changed: _SignalLike
    workspace_state_changed: _SignalLike
    graphics_preferences_changed: _SignalLike
    run_controls_changed: _SignalLike
    project_display_name: str
    graphics_tab_strip_density: str
    active_workspace_id: str
    active_scope_breadcrumb_items: list[dict[str, str]]
    active_view_items: list[dict[str, Any]]
    active_workspace_can_run: bool
    active_workspace_can_pause: bool
    active_workspace_can_stop: bool

    def request_run_workflow(self) -> None: ...

    def request_toggle_run_pause(self) -> None: ...

    def request_stop_workflow(self) -> None: ...

    def show_workflow_settings_dialog(self, checked: bool = False) -> None: ...

    def set_script_editor_panel_visible(self, checked: bool | None = None) -> None: ...

    def request_open_scope_breadcrumb(self, node_id: str) -> bool: ...

    def request_switch_view(self, view_id: str) -> None: ...

    def request_move_view_tab(self, from_index: int, to_index: int) -> bool: ...

    def request_rename_view(self, view_id: str) -> bool: ...

    def request_close_view(self, view_id: str) -> bool: ...

    def request_create_view(self) -> None: ...

    def request_move_workspace_tab(self, from_index: int, to_index: int) -> bool: ...

    def request_rename_workspace_by_id(self, workspace_id: str) -> bool: ...

    def request_close_workspace_by_id(self, workspace_id: str) -> bool: ...

    def request_create_workspace(self) -> None: ...


class _ShellWindowWorkspaceSourceAdapter:
    def __init__(self, shell_window: "ShellWindow") -> None:
        self._shell_window = shell_window

    @property
    def _source(self) -> object:
        presenter = getattr(self._shell_window, "shell_workspace_presenter", None)
        return presenter if presenter is not None else self._shell_window

    def __getattr__(self, name: str) -> Any:
        return getattr(self._source, name)


def _copy_list(value: object) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _resolve_workspace_source(
    shell_window: "ShellWindow | None",
    workspace_source: _ShellWorkspaceSource | None,
) -> _ShellWorkspaceSource:
    if workspace_source is not None:
        return workspace_source
    if shell_window is None:
        raise TypeError("ShellWorkspaceBridge requires a shell window or explicit workspace source contract.")
    return _ShellWindowWorkspaceSourceAdapter(shell_window)


class ShellWorkspaceBridge(QObject):
    project_meta_changed = pyqtSignal()
    workspace_state_changed = pyqtSignal()
    graphics_preferences_changed = pyqtSignal()
    run_controls_changed = pyqtSignal()
    workspace_tabs_changed = pyqtSignal()
    console_output_changed = pyqtSignal()
    console_errors_changed = pyqtSignal()
    console_warnings_changed = pyqtSignal()
    console_counts_changed = pyqtSignal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        shell_window: "ShellWindow | None" = None,
        workspace_source: _ShellWorkspaceSource | None = None,
        scene_bridge: "GraphSceneBridge | None" = None,
        view_bridge: "ViewportBridge | None" = None,
        console_bridge: "ConsoleModel | None" = None,
        workspace_tabs_bridge: "WorkspaceTabsModel | None" = None,
    ) -> None:
        super().__init__(parent)
        self._shell_window = shell_window
        self._scene_bridge = scene_bridge
        self._view_bridge = view_bridge
        self._console_bridge = console_bridge
        self._workspace_tabs_bridge = workspace_tabs_bridge
        self._workspace_source = _resolve_workspace_source(shell_window, workspace_source)

        self._workspace_source.project_meta_changed.connect(self.project_meta_changed.emit)
        self._workspace_source.workspace_state_changed.connect(self.workspace_state_changed.emit)
        self._workspace_source.graphics_preferences_changed.connect(self.graphics_preferences_changed.emit)
        self._workspace_source.run_controls_changed.connect(self.run_controls_changed.emit)
        if scene_bridge is not None:
            scene_bridge.scope_changed.connect(self.workspace_state_changed.emit)
        if workspace_tabs_bridge is not None:
            workspace_tabs_bridge.tabs_changed.connect(self.workspace_tabs_changed.emit)
        if console_bridge is not None:
            console_bridge.output_changed.connect(self.console_output_changed.emit)
            console_bridge.errors_changed.connect(self.console_errors_changed.emit)
            console_bridge.warnings_changed.connect(self.console_warnings_changed.emit)
            console_bridge.counts_changed.connect(self.console_counts_changed.emit)

    @property
    def shell_window(self) -> "ShellWindow | None":
        return self._shell_window

    @property
    def workspace_source(self) -> _ShellWorkspaceSource:
        return self._workspace_source

    @property
    def scene_bridge(self) -> "GraphSceneBridge | None":
        return self._scene_bridge

    @property
    def view_bridge(self) -> "ViewportBridge | None":
        return self._view_bridge

    @property
    def console_bridge(self) -> "ConsoleModel | None":
        return self._console_bridge

    @property
    def workspace_tabs_bridge(self) -> "WorkspaceTabsModel | None":
        return self._workspace_tabs_bridge

    @pyqtProperty(str, notify=project_meta_changed)
    def project_display_name(self) -> str:
        return str(self._workspace_source.project_display_name)

    @pyqtProperty(str, notify=graphics_preferences_changed)
    def graphics_tab_strip_density(self) -> str:
        return str(self._workspace_source.graphics_tab_strip_density)

    @pyqtProperty(str, notify=workspace_state_changed)
    def active_workspace_id(self) -> str:
        return str(self._workspace_source.active_workspace_id)

    @pyqtProperty("QVariantList", notify=workspace_state_changed)
    def active_scope_breadcrumb_items(self) -> list[dict[str, str]]:
        return _copy_list(self._workspace_source.active_scope_breadcrumb_items)

    @pyqtProperty("QVariantList", notify=workspace_state_changed)
    def active_view_items(self) -> list[dict[str, Any]]:
        return _copy_list(self._workspace_source.active_view_items)

    @pyqtProperty(bool, notify=run_controls_changed)
    def active_workspace_can_run(self) -> bool:
        return bool(self._workspace_source.active_workspace_can_run)

    @pyqtProperty(bool, notify=run_controls_changed)
    def active_workspace_can_pause(self) -> bool:
        return bool(self._workspace_source.active_workspace_can_pause)

    @pyqtProperty(bool, notify=run_controls_changed)
    def active_workspace_can_stop(self) -> bool:
        return bool(self._workspace_source.active_workspace_can_stop)

    @pyqtProperty("QVariantList", notify=workspace_tabs_changed)
    def workspace_tabs(self) -> list[dict[str, Any]]:
        if self._workspace_tabs_bridge is None:
            return []
        return _copy_list(self._workspace_tabs_bridge.tabs)

    @pyqtProperty(str, notify=console_output_changed)
    def output_text(self) -> str:
        if self._console_bridge is None:
            return ""
        return str(self._console_bridge.output_text)

    @pyqtProperty(str, notify=console_errors_changed)
    def errors_text(self) -> str:
        if self._console_bridge is None:
            return ""
        return str(self._console_bridge.errors_text)

    @pyqtProperty(str, notify=console_warnings_changed)
    def warnings_text(self) -> str:
        if self._console_bridge is None:
            return ""
        return str(self._console_bridge.warnings_text)

    @pyqtProperty(int, notify=console_counts_changed)
    def warning_count_value(self) -> int:
        if self._console_bridge is None:
            return 0
        return int(self._console_bridge.warning_count_value)

    @pyqtProperty(int, notify=console_counts_changed)
    def error_count_value(self) -> int:
        if self._console_bridge is None:
            return 0
        return int(self._console_bridge.error_count_value)

    @pyqtSlot()
    def request_run_workflow(self) -> None:
        self._workspace_source.request_run_workflow()

    @pyqtSlot()
    def request_toggle_run_pause(self) -> None:
        self._workspace_source.request_toggle_run_pause()

    @pyqtSlot()
    def request_stop_workflow(self) -> None:
        self._workspace_source.request_stop_workflow()

    @pyqtSlot()
    @pyqtSlot(bool)
    def show_workflow_settings_dialog(self, checked: bool = False) -> None:
        self._workspace_source.show_workflow_settings_dialog(checked)

    @pyqtSlot()
    @pyqtSlot(bool)
    def set_script_editor_panel_visible(self, checked: bool | None = None) -> None:
        self._workspace_source.set_script_editor_panel_visible(checked)

    @pyqtSlot(str, result=bool)
    def request_open_scope_breadcrumb(self, node_id: str) -> bool:
        return bool(self._workspace_source.request_open_scope_breadcrumb(node_id))

    @pyqtSlot(str)
    def request_switch_view(self, view_id: str) -> None:
        self._workspace_source.request_switch_view(view_id)

    @pyqtSlot(int, int, result=bool)
    def request_move_view_tab(self, from_index: int, to_index: int) -> bool:
        return bool(self._workspace_source.request_move_view_tab(from_index, to_index))

    @pyqtSlot(str, result=bool)
    def request_rename_view(self, view_id: str) -> bool:
        return bool(self._workspace_source.request_rename_view(view_id))

    @pyqtSlot(str, result=bool)
    def request_close_view(self, view_id: str) -> bool:
        return bool(self._workspace_source.request_close_view(view_id))

    @pyqtSlot()
    def request_create_view(self) -> None:
        self._workspace_source.request_create_view()

    @pyqtSlot(str)
    def activate_workspace(self, workspace_id: str) -> None:
        if self._workspace_tabs_bridge is not None:
            self._workspace_tabs_bridge.activate_workspace(workspace_id)

    @pyqtSlot(int, int, result=bool)
    def request_move_workspace_tab(self, from_index: int, to_index: int) -> bool:
        return bool(self._workspace_source.request_move_workspace_tab(from_index, to_index))

    @pyqtSlot(str, result=bool)
    def request_rename_workspace_by_id(self, workspace_id: str) -> bool:
        return bool(self._workspace_source.request_rename_workspace_by_id(workspace_id))

    @pyqtSlot(str, result=bool)
    def request_close_workspace_by_id(self, workspace_id: str) -> bool:
        return bool(self._workspace_source.request_close_workspace_by_id(workspace_id))

    @pyqtSlot()
    def request_create_workspace(self) -> None:
        self._workspace_source.request_create_workspace()

    @pyqtSlot()
    def clear_all(self) -> None:
        if self._console_bridge is not None:
            self._console_bridge.clear_all()


__all__ = ["ShellWorkspaceBridge"]
