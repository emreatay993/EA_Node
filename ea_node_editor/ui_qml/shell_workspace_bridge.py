from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow
    from ea_node_editor.ui_qml.console_model import ConsoleModel
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
    from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge
    from ea_node_editor.ui_qml.workspace_tabs_model import WorkspaceTabsModel


def _copy_list(value: object) -> list[Any]:
    return list(value) if isinstance(value, list) else []


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


class ShellWorkspaceBridge(QObject):
    project_meta_changed = pyqtSignal()
    workspace_state_changed = pyqtSignal()
    graphics_preferences_changed = pyqtSignal()
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
        self._workspace_source = getattr(shell_window, "shell_workspace_presenter", shell_window)

        _connect_signal(self._workspace_source, "project_meta_changed", self.project_meta_changed.emit)
        _connect_signal(self._workspace_source, "workspace_state_changed", self.workspace_state_changed.emit)
        _connect_signal(
            self._workspace_source,
            "graphics_preferences_changed",
            self.graphics_preferences_changed.emit,
        )
        _connect_signal(scene_bridge, "scope_changed", self.workspace_state_changed.emit)
        _connect_signal(workspace_tabs_bridge, "tabs_changed", self.workspace_tabs_changed.emit)
        _connect_signal(console_bridge, "output_changed", self.console_output_changed.emit)
        _connect_signal(console_bridge, "errors_changed", self.console_errors_changed.emit)
        _connect_signal(console_bridge, "warnings_changed", self.console_warnings_changed.emit)
        _connect_signal(console_bridge, "counts_changed", self.console_counts_changed.emit)

    @property
    def shell_window(self) -> "ShellWindow | None":
        return self._shell_window

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
        return str(_source_attr(self._workspace_source, "project_display_name", ""))

    @pyqtProperty(str, notify=graphics_preferences_changed)
    def graphics_tab_strip_density(self) -> str:
        return str(_source_attr(self._workspace_source, "graphics_tab_strip_density", "compact"))

    @pyqtProperty(str, notify=workspace_state_changed)
    def active_workspace_id(self) -> str:
        return str(_source_attr(self._workspace_source, "active_workspace_id", ""))

    @pyqtProperty("QVariantList", notify=workspace_state_changed)
    def active_scope_breadcrumb_items(self) -> list[dict[str, str]]:
        return _copy_list(_source_attr(self._workspace_source, "active_scope_breadcrumb_items", []))

    @pyqtProperty("QVariantList", notify=workspace_state_changed)
    def active_view_items(self) -> list[dict[str, Any]]:
        return _copy_list(_source_attr(self._workspace_source, "active_view_items", []))

    @pyqtProperty("QVariantList", notify=workspace_tabs_changed)
    def workspace_tabs(self) -> list[dict[str, Any]]:
        return _copy_list(_source_attr(self._workspace_tabs_bridge, "tabs", []))

    @pyqtProperty(str, notify=console_output_changed)
    def output_text(self) -> str:
        return str(_source_attr(self._console_bridge, "output_text", ""))

    @pyqtProperty(str, notify=console_errors_changed)
    def errors_text(self) -> str:
        return str(_source_attr(self._console_bridge, "errors_text", ""))

    @pyqtProperty(str, notify=console_warnings_changed)
    def warnings_text(self) -> str:
        return str(_source_attr(self._console_bridge, "warnings_text", ""))

    @pyqtProperty(int, notify=console_counts_changed)
    def warning_count_value(self) -> int:
        return int(_source_attr(self._console_bridge, "warning_count_value", 0))

    @pyqtProperty(int, notify=console_counts_changed)
    def error_count_value(self) -> int:
        return int(_source_attr(self._console_bridge, "error_count_value", 0))

    @pyqtSlot()
    def request_run_workflow(self) -> None:
        _invoke(self._workspace_source, "request_run_workflow")

    @pyqtSlot()
    def request_toggle_run_pause(self) -> None:
        _invoke(self._workspace_source, "request_toggle_run_pause")

    @pyqtSlot()
    def request_stop_workflow(self) -> None:
        _invoke(self._workspace_source, "request_stop_workflow")

    @pyqtSlot()
    @pyqtSlot(bool)
    def show_workflow_settings_dialog(self, checked: bool = False) -> None:
        _invoke(self._workspace_source, "show_workflow_settings_dialog", checked)

    @pyqtSlot()
    @pyqtSlot(bool)
    def set_script_editor_panel_visible(self, checked: bool | None = None) -> None:
        if checked is None:
            _invoke(self._workspace_source, "set_script_editor_panel_visible")
            return
        _invoke(self._workspace_source, "set_script_editor_panel_visible", checked)

    @pyqtSlot(str, result=bool)
    def request_open_scope_breadcrumb(self, node_id: str) -> bool:
        return bool(
            _invoke(self._workspace_source, "request_open_scope_breadcrumb", node_id, default=False)
        )

    @pyqtSlot(str)
    def request_switch_view(self, view_id: str) -> None:
        _invoke(self._workspace_source, "request_switch_view", view_id)

    @pyqtSlot(int, int, result=bool)
    def request_move_view_tab(self, from_index: int, to_index: int) -> bool:
        return bool(
            _invoke(self._workspace_source, "request_move_view_tab", from_index, to_index, default=False)
        )

    @pyqtSlot(str, result=bool)
    def request_rename_view(self, view_id: str) -> bool:
        return bool(_invoke(self._workspace_source, "request_rename_view", view_id, default=False))

    @pyqtSlot(str, result=bool)
    def request_close_view(self, view_id: str) -> bool:
        return bool(_invoke(self._workspace_source, "request_close_view", view_id, default=False))

    @pyqtSlot()
    def request_create_view(self) -> None:
        _invoke(self._workspace_source, "request_create_view")

    @pyqtSlot(str)
    def activate_workspace(self, workspace_id: str) -> None:
        _invoke(self._workspace_tabs_bridge, "activate_workspace", workspace_id)

    @pyqtSlot(int, int, result=bool)
    def request_move_workspace_tab(self, from_index: int, to_index: int) -> bool:
        return bool(
            _invoke(self._workspace_source, "request_move_workspace_tab", from_index, to_index, default=False)
        )

    @pyqtSlot(str, result=bool)
    def request_rename_workspace_by_id(self, workspace_id: str) -> bool:
        return bool(
            _invoke(self._workspace_source, "request_rename_workspace_by_id", workspace_id, default=False)
        )

    @pyqtSlot(str, result=bool)
    def request_close_workspace_by_id(self, workspace_id: str) -> bool:
        return bool(
            _invoke(self._workspace_source, "request_close_workspace_by_id", workspace_id, default=False)
        )

    @pyqtSlot()
    def request_create_workspace(self) -> None:
        _invoke(self._workspace_source, "request_create_workspace")

    @pyqtSlot()
    def clear_all(self) -> None:
        _invoke(self._console_bridge, "clear_all")


__all__ = ["ShellWorkspaceBridge"]
