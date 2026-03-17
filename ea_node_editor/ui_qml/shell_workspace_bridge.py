from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow
    from ea_node_editor.ui_qml.console_model import ConsoleModel
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
    from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge
    from ea_node_editor.ui_qml.workspace_tabs_model import WorkspaceTabsModel


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

        self._connect_signal(self._shell_window, "project_meta_changed", self.project_meta_changed.emit)
        self._connect_signal(self._shell_window, "workspace_state_changed", self.workspace_state_changed.emit)
        self._connect_signal(
            self._shell_window,
            "graphics_preferences_changed",
            self.graphics_preferences_changed.emit,
        )
        self._connect_signal(self._scene_bridge, "scope_changed", self.workspace_state_changed.emit)
        self._connect_signal(self._workspace_tabs_bridge, "tabs_changed", self.workspace_tabs_changed.emit)
        self._connect_signal(self._console_bridge, "output_changed", self.console_output_changed.emit)
        self._connect_signal(self._console_bridge, "errors_changed", self.console_errors_changed.emit)
        self._connect_signal(self._console_bridge, "warnings_changed", self.console_warnings_changed.emit)
        self._connect_signal(self._console_bridge, "counts_changed", self.console_counts_changed.emit)

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

    def _connect_signal(self, source: QObject | None, signal_name: str, callback) -> None:  # noqa: ANN001
        if source is None:
            return
        signal = getattr(source, signal_name, None)
        if signal is not None and hasattr(signal, "connect"):
            signal.connect(callback)

    @staticmethod
    def _source_value(source: QObject | None, name: str, default):
        if source is None:
            return default
        return getattr(source, name, default)

    @staticmethod
    def _call_source(source: QObject | None, name: str, *args):
        if source is None:
            return None
        method = getattr(source, name, None)
        if method is None:
            return None
        return method(*args)

    def _shell_value(self, name: str, default):
        return self._source_value(self._shell_window, name, default)

    def _call_shell(self, name: str, *args):
        return self._call_source(self._shell_window, name, *args)

    def _workspace_tabs_value(self, name: str, default):
        return self._source_value(self._workspace_tabs_bridge, name, default)

    def _call_workspace_tabs(self, name: str, *args):
        return self._call_source(self._workspace_tabs_bridge, name, *args)

    def _console_value(self, name: str, default):
        return self._source_value(self._console_bridge, name, default)

    def _call_console(self, name: str, *args):
        return self._call_source(self._console_bridge, name, *args)

    @pyqtProperty(str, notify=project_meta_changed)
    def project_display_name(self) -> str:
        return str(self._shell_value("project_display_name", ""))

    @pyqtProperty(str, notify=graphics_preferences_changed)
    def graphics_tab_strip_density(self) -> str:
        return str(self._shell_value("graphics_tab_strip_density", "compact"))

    @pyqtProperty(str, notify=workspace_state_changed)
    def active_workspace_id(self) -> str:
        return str(self._shell_value("active_workspace_id", ""))

    @pyqtProperty("QVariantList", notify=workspace_state_changed)
    def active_scope_breadcrumb_items(self) -> list[dict[str, str]]:
        items = self._shell_value("active_scope_breadcrumb_items", [])
        return list(items) if isinstance(items, list) else []

    @pyqtProperty("QVariantList", notify=workspace_state_changed)
    def active_view_items(self) -> list[dict[str, Any]]:
        items = self._shell_value("active_view_items", [])
        return list(items) if isinstance(items, list) else []

    @pyqtProperty("QVariantList", notify=workspace_tabs_changed)
    def workspace_tabs(self) -> list[dict[str, Any]]:
        tabs = self._workspace_tabs_value("tabs", [])
        return list(tabs) if isinstance(tabs, list) else []

    @pyqtProperty(str, notify=console_output_changed)
    def output_text(self) -> str:
        return str(self._console_value("output_text", ""))

    @pyqtProperty(str, notify=console_errors_changed)
    def errors_text(self) -> str:
        return str(self._console_value("errors_text", ""))

    @pyqtProperty(str, notify=console_warnings_changed)
    def warnings_text(self) -> str:
        return str(self._console_value("warnings_text", ""))

    @pyqtProperty(int, notify=console_counts_changed)
    def warning_count_value(self) -> int:
        return int(self._console_value("warning_count_value", 0))

    @pyqtProperty(int, notify=console_counts_changed)
    def error_count_value(self) -> int:
        return int(self._console_value("error_count_value", 0))

    @pyqtSlot()
    def request_run_workflow(self) -> None:
        self._call_shell("request_run_workflow")

    @pyqtSlot()
    def request_toggle_run_pause(self) -> None:
        self._call_shell("request_toggle_run_pause")

    @pyqtSlot()
    def request_stop_workflow(self) -> None:
        self._call_shell("request_stop_workflow")

    @pyqtSlot()
    @pyqtSlot(bool)
    def show_workflow_settings_dialog(self, checked: bool = False) -> None:
        self._call_shell("show_workflow_settings_dialog", checked)

    @pyqtSlot()
    @pyqtSlot(bool)
    def set_script_editor_panel_visible(self, checked: bool | None = None) -> None:
        if checked is None:
            self._call_shell("set_script_editor_panel_visible")
            return
        self._call_shell("set_script_editor_panel_visible", checked)

    @pyqtSlot(str, result=bool)
    def request_open_scope_breadcrumb(self, node_id: str) -> bool:
        return bool(self._call_shell("request_open_scope_breadcrumb", node_id))

    @pyqtSlot(str)
    def request_switch_view(self, view_id: str) -> None:
        self._call_shell("request_switch_view", view_id)

    @pyqtSlot(int, int, result=bool)
    def request_move_view_tab(self, from_index: int, to_index: int) -> bool:
        return bool(self._call_shell("request_move_view_tab", from_index, to_index))

    @pyqtSlot(str, result=bool)
    def request_rename_view(self, view_id: str) -> bool:
        return bool(self._call_shell("request_rename_view", view_id))

    @pyqtSlot(str, result=bool)
    def request_close_view(self, view_id: str) -> bool:
        return bool(self._call_shell("request_close_view", view_id))

    @pyqtSlot()
    def request_create_view(self) -> None:
        self._call_shell("request_create_view")

    @pyqtSlot(str)
    def activate_workspace(self, workspace_id: str) -> None:
        self._call_workspace_tabs("activate_workspace", workspace_id)

    @pyqtSlot(int, int, result=bool)
    def request_move_workspace_tab(self, from_index: int, to_index: int) -> bool:
        return bool(self._call_shell("request_move_workspace_tab", from_index, to_index))

    @pyqtSlot(str, result=bool)
    def request_rename_workspace_by_id(self, workspace_id: str) -> bool:
        return bool(self._call_shell("request_rename_workspace_by_id", workspace_id))

    @pyqtSlot(str, result=bool)
    def request_close_workspace_by_id(self, workspace_id: str) -> bool:
        return bool(self._call_shell("request_close_workspace_by_id", workspace_id))

    @pyqtSlot()
    def request_create_workspace(self) -> None:
        self._call_shell("request_create_workspace")

    @pyqtSlot()
    def clear_all(self) -> None:
        self._call_console("clear_all")


__all__ = ["ShellWorkspaceBridge"]
