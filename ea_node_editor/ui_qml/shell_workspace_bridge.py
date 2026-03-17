from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow
    from ea_node_editor.ui_qml.console_model import ConsoleModel
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
    from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge
    from ea_node_editor.ui_qml.workspace_tabs_model import WorkspaceTabsModel


def _copy_list(value: object) -> list[Any]:
    return list(value) if isinstance(value, list) else []


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

        self._project_display_name: Callable[[], str] = lambda: ""
        self._graphics_tab_strip_density: Callable[[], str] = lambda: "compact"
        self._active_workspace_id: Callable[[], str] = lambda: ""
        self._active_scope_breadcrumb_items: Callable[[], list[dict[str, str]]] = lambda: []
        self._active_view_items: Callable[[], list[dict[str, Any]]] = lambda: []
        self._workspace_tabs: Callable[[], list[dict[str, Any]]] = lambda: []
        self._output_text: Callable[[], str] = lambda: ""
        self._errors_text: Callable[[], str] = lambda: ""
        self._warnings_text: Callable[[], str] = lambda: ""
        self._warning_count_value: Callable[[], int] = lambda: 0
        self._error_count_value: Callable[[], int] = lambda: 0

        self._request_run_workflow: Callable[[], None] = lambda: None
        self._request_toggle_run_pause: Callable[[], None] = lambda: None
        self._request_stop_workflow: Callable[[], None] = lambda: None
        self._show_workflow_settings_dialog: Callable[[bool], None] = lambda _checked=False: None
        self._set_script_editor_panel_visible: Callable[[bool | None], None] = (
            lambda _checked=None: None
        )
        self._request_open_scope_breadcrumb: Callable[[str], bool] = lambda _node_id: False
        self._request_switch_view: Callable[[str], None] = lambda _view_id: None
        self._request_move_view_tab: Callable[[int, int], bool] = lambda _from_index, _to_index: False
        self._request_rename_view: Callable[[str], bool] = lambda _view_id: False
        self._request_close_view: Callable[[str], bool] = lambda _view_id: False
        self._request_create_view: Callable[[], None] = lambda: None
        self._activate_workspace: Callable[[str], None] = lambda _workspace_id: None
        self._request_move_workspace_tab: Callable[[int, int], bool] = (
            lambda _from_index, _to_index: False
        )
        self._request_rename_workspace_by_id: Callable[[str], bool] = lambda _workspace_id: False
        self._request_close_workspace_by_id: Callable[[str], bool] = lambda _workspace_id: False
        self._request_create_workspace: Callable[[], None] = lambda: None
        self._clear_all: Callable[[], None] = lambda: None

        if shell_window is not None:
            self._project_display_name = lambda: str(shell_window.project_display_name)
            self._graphics_tab_strip_density = lambda: str(shell_window.graphics_tab_strip_density)
            self._active_workspace_id = lambda: str(shell_window.active_workspace_id)
            self._active_scope_breadcrumb_items = (
                lambda: _copy_list(shell_window.active_scope_breadcrumb_items)
            )
            self._active_view_items = lambda: _copy_list(shell_window.active_view_items)

            self._request_run_workflow = shell_window.request_run_workflow
            self._request_toggle_run_pause = shell_window.request_toggle_run_pause
            self._request_stop_workflow = shell_window.request_stop_workflow
            self._show_workflow_settings_dialog = shell_window.show_workflow_settings_dialog
            self._set_script_editor_panel_visible = shell_window.set_script_editor_panel_visible
            self._request_open_scope_breadcrumb = shell_window.request_open_scope_breadcrumb
            self._request_switch_view = shell_window.request_switch_view
            self._request_move_view_tab = shell_window.request_move_view_tab
            self._request_rename_view = shell_window.request_rename_view
            self._request_close_view = shell_window.request_close_view
            self._request_create_view = shell_window.request_create_view
            self._request_move_workspace_tab = shell_window.request_move_workspace_tab
            self._request_rename_workspace_by_id = shell_window.request_rename_workspace_by_id
            self._request_close_workspace_by_id = shell_window.request_close_workspace_by_id
            self._request_create_workspace = shell_window.request_create_workspace

            shell_window.project_meta_changed.connect(self.project_meta_changed.emit)
            shell_window.workspace_state_changed.connect(self.workspace_state_changed.emit)
            shell_window.graphics_preferences_changed.connect(self.graphics_preferences_changed.emit)

        if scene_bridge is not None:
            scene_bridge.scope_changed.connect(self.workspace_state_changed.emit)

        if workspace_tabs_bridge is not None:
            self._workspace_tabs = lambda: _copy_list(workspace_tabs_bridge.tabs)
            self._activate_workspace = workspace_tabs_bridge.activate_workspace
            workspace_tabs_bridge.tabs_changed.connect(self.workspace_tabs_changed.emit)

        if console_bridge is not None:
            self._output_text = lambda: str(console_bridge.output_text)
            self._errors_text = lambda: str(console_bridge.errors_text)
            self._warnings_text = lambda: str(console_bridge.warnings_text)
            self._warning_count_value = lambda: int(console_bridge.warning_count_value)
            self._error_count_value = lambda: int(console_bridge.error_count_value)
            self._clear_all = console_bridge.clear_all

            console_bridge.output_changed.connect(self.console_output_changed.emit)
            console_bridge.errors_changed.connect(self.console_errors_changed.emit)
            console_bridge.warnings_changed.connect(self.console_warnings_changed.emit)
            console_bridge.counts_changed.connect(self.console_counts_changed.emit)

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
        return self._project_display_name()

    @pyqtProperty(str, notify=graphics_preferences_changed)
    def graphics_tab_strip_density(self) -> str:
        return self._graphics_tab_strip_density()

    @pyqtProperty(str, notify=workspace_state_changed)
    def active_workspace_id(self) -> str:
        return self._active_workspace_id()

    @pyqtProperty("QVariantList", notify=workspace_state_changed)
    def active_scope_breadcrumb_items(self) -> list[dict[str, str]]:
        return self._active_scope_breadcrumb_items()

    @pyqtProperty("QVariantList", notify=workspace_state_changed)
    def active_view_items(self) -> list[dict[str, Any]]:
        return self._active_view_items()

    @pyqtProperty("QVariantList", notify=workspace_tabs_changed)
    def workspace_tabs(self) -> list[dict[str, Any]]:
        return self._workspace_tabs()

    @pyqtProperty(str, notify=console_output_changed)
    def output_text(self) -> str:
        return self._output_text()

    @pyqtProperty(str, notify=console_errors_changed)
    def errors_text(self) -> str:
        return self._errors_text()

    @pyqtProperty(str, notify=console_warnings_changed)
    def warnings_text(self) -> str:
        return self._warnings_text()

    @pyqtProperty(int, notify=console_counts_changed)
    def warning_count_value(self) -> int:
        return self._warning_count_value()

    @pyqtProperty(int, notify=console_counts_changed)
    def error_count_value(self) -> int:
        return self._error_count_value()

    @pyqtSlot()
    def request_run_workflow(self) -> None:
        self._request_run_workflow()

    @pyqtSlot()
    def request_toggle_run_pause(self) -> None:
        self._request_toggle_run_pause()

    @pyqtSlot()
    def request_stop_workflow(self) -> None:
        self._request_stop_workflow()

    @pyqtSlot()
    @pyqtSlot(bool)
    def show_workflow_settings_dialog(self, checked: bool = False) -> None:
        self._show_workflow_settings_dialog(checked)

    @pyqtSlot()
    @pyqtSlot(bool)
    def set_script_editor_panel_visible(self, checked: bool | None = None) -> None:
        if checked is None:
            self._set_script_editor_panel_visible()
            return
        self._set_script_editor_panel_visible(checked)

    @pyqtSlot(str, result=bool)
    def request_open_scope_breadcrumb(self, node_id: str) -> bool:
        return bool(self._request_open_scope_breadcrumb(node_id))

    @pyqtSlot(str)
    def request_switch_view(self, view_id: str) -> None:
        self._request_switch_view(view_id)

    @pyqtSlot(int, int, result=bool)
    def request_move_view_tab(self, from_index: int, to_index: int) -> bool:
        return bool(self._request_move_view_tab(from_index, to_index))

    @pyqtSlot(str, result=bool)
    def request_rename_view(self, view_id: str) -> bool:
        return bool(self._request_rename_view(view_id))

    @pyqtSlot(str, result=bool)
    def request_close_view(self, view_id: str) -> bool:
        return bool(self._request_close_view(view_id))

    @pyqtSlot()
    def request_create_view(self) -> None:
        self._request_create_view()

    @pyqtSlot(str)
    def activate_workspace(self, workspace_id: str) -> None:
        self._activate_workspace(workspace_id)

    @pyqtSlot(int, int, result=bool)
    def request_move_workspace_tab(self, from_index: int, to_index: int) -> bool:
        return bool(self._request_move_workspace_tab(from_index, to_index))

    @pyqtSlot(str, result=bool)
    def request_rename_workspace_by_id(self, workspace_id: str) -> bool:
        return bool(self._request_rename_workspace_by_id(workspace_id))

    @pyqtSlot(str, result=bool)
    def request_close_workspace_by_id(self, workspace_id: str) -> bool:
        return bool(self._request_close_workspace_by_id(workspace_id))

    @pyqtSlot()
    def request_create_workspace(self) -> None:
        self._request_create_workspace()

    @pyqtSlot()
    def clear_all(self) -> None:
        self._clear_all()


__all__ = ["ShellWorkspaceBridge"]
