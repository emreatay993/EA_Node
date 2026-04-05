from __future__ import annotations

import os
from typing import Any

from PyQt6.QtCore import QEvent, QTimer, Qt, QUrl, pyqtProperty, pyqtSignal
from PyQt6.QtQuick import QQuickWindow, QSGRendererInterface
from PyQt6.QtQuickWidgets import QQuickWidget
from PyQt6.QtWidgets import QApplication, QFileDialog, QMainWindow

from ea_node_editor.execution.client import ProcessExecutionClient
from ea_node_editor.nodes.builtins.subnode import (
    SUBNODE_INPUT_TYPE_ID,
    SUBNODE_OUTPUT_TYPE_ID,
)
from ea_node_editor.persistence.session_store import SessionAutosaveStore
from ea_node_editor.settings import autosave_project_path, recent_session_path
from ea_node_editor.ui.shell import window_state_helpers as state_helpers
from ea_node_editor.ui.shell.composition import (
    ShellWindowComposition,
    bootstrap_shell_window,
    build_shell_window_composition,
)
from ea_node_editor.ui_qml.embedded_viewer_overlay_manager import EmbeddedViewerOverlayManager


def _configure_qtquick_backend() -> None:
    force_value = os.environ.get("EA_NODE_EDITOR_FORCE_SOFTWARE_QML", "").strip().lower()
    force_env = force_value in {"1", "true", "yes", "on"}
    platform = os.environ.get("QT_QPA_PLATFORM", "").strip().lower()
    force_platform = platform in {"offscreen", "minimal"}
    if not (force_env or force_platform):
        return
    os.environ.setdefault("QT_QUICK_BACKEND", "software")
    os.environ.setdefault("QSG_RHI_BACKEND", "software")
    QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.Software)


_configure_qtquick_backend()
_PASSIVE_NODE_STYLE_CLIPBOARD_KIND = "passive-node-style"
_FLOW_EDGE_STYLE_CLIPBOARD_KIND = "flow-edge-style"
_STYLE_CLIPBOARD_APP_PROPERTY = "eaNodeEditorStyleClipboard"


class ShellWindow(QMainWindow):
    execution_event = pyqtSignal(dict)
    node_library_changed = pyqtSignal()
    library_pane_reset_requested = pyqtSignal(name="libraryPaneResetRequested")
    workspace_state_changed = pyqtSignal()
    run_controls_changed = pyqtSignal()
    selected_node_changed = pyqtSignal()
    project_meta_changed = pyqtSignal()
    graph_search_changed = pyqtSignal()
    connection_quick_insert_changed = pyqtSignal()
    graph_hint_changed = pyqtSignal()
    run_failure_changed = pyqtSignal()
    node_execution_state_changed = pyqtSignal()
    snap_to_grid_changed = pyqtSignal()
    graphics_preferences_changed = pyqtSignal()

    _RUN_SCOPED_EVENT_TYPES = {
        "run_started",
        "run_state",
        "run_completed",
        "run_failed",
        "run_stopped",
        "node_started",
        "node_completed",
        "log",
    }
    _GRAPH_SEARCH_LIMIT = 10
    _CONNECTION_QUICK_INSERT_LIMIT = 12
    _CONNECTION_QUICK_INSERT_OFFSET = 36.0
    _SNAP_GRID_SIZE = 20.0
    _SUBNODE_PIN_TYPE_IDS = {
        SUBNODE_INPUT_TYPE_ID,
        SUBNODE_OUTPUT_TYPE_ID,
    }

    project_display_name = pyqtProperty(
        str,
        fget=state_helpers._qt_project_display_name,
        notify=project_meta_changed,
    )
    filtered_node_library_items = pyqtProperty(
        "QVariantList",
        fget=state_helpers._qt_filtered_node_library_items,
        notify=node_library_changed,
    )
    grouped_node_library_items = pyqtProperty(
        "QVariantList",
        fget=state_helpers._qt_grouped_node_library_items,
        notify=node_library_changed,
    )
    library_category_options = pyqtProperty(
        "QVariantList",
        fget=state_helpers._qt_library_category_options,
        notify=node_library_changed,
    )
    library_direction_options = pyqtProperty(
        "QVariantList",
        fget=state_helpers._qt_library_direction_options,
        notify=node_library_changed,
    )
    library_data_type_options = pyqtProperty(
        "QVariantList",
        fget=state_helpers._qt_library_data_type_options,
        notify=node_library_changed,
    )
    pin_data_type_options = pyqtProperty(
        "QVariantList",
        fget=state_helpers._qt_pin_data_type_options,
        notify=workspace_state_changed,
    )
    graph_search_open = pyqtProperty(
        bool,
        fget=state_helpers._qt_graph_search_open,
        notify=graph_search_changed,
    )
    graph_search_query = pyqtProperty(
        str,
        fget=state_helpers._qt_graph_search_query,
        notify=graph_search_changed,
    )
    graph_search_enabled_scopes = pyqtProperty(
        "QVariantList",
        fget=state_helpers._qt_graph_search_enabled_scopes,
        notify=graph_search_changed,
    )
    graph_search_results = pyqtProperty(
        "QVariantList",
        fget=state_helpers._qt_graph_search_results,
        notify=graph_search_changed,
    )
    graph_search_highlight_index = pyqtProperty(
        int,
        fget=state_helpers._qt_graph_search_highlight_index,
        notify=graph_search_changed,
    )
    connection_quick_insert_open = pyqtProperty(
        bool,
        fget=state_helpers._qt_connection_quick_insert_open,
        notify=connection_quick_insert_changed,
    )
    connection_quick_insert_query = pyqtProperty(
        str,
        fget=state_helpers._qt_connection_quick_insert_query,
        notify=connection_quick_insert_changed,
    )
    connection_quick_insert_results = pyqtProperty(
        "QVariantList",
        fget=state_helpers._qt_connection_quick_insert_results,
        notify=connection_quick_insert_changed,
    )
    connection_quick_insert_highlight_index = pyqtProperty(
        int,
        fget=state_helpers._qt_connection_quick_insert_highlight_index,
        notify=connection_quick_insert_changed,
    )
    connection_quick_insert_overlay_x = pyqtProperty(
        float,
        fget=state_helpers._qt_connection_quick_insert_overlay_x,
        notify=connection_quick_insert_changed,
    )
    connection_quick_insert_overlay_y = pyqtProperty(
        float,
        fget=state_helpers._qt_connection_quick_insert_overlay_y,
        notify=connection_quick_insert_changed,
    )
    connection_quick_insert_source_summary = pyqtProperty(
        str,
        fget=state_helpers._qt_connection_quick_insert_source_summary,
        notify=connection_quick_insert_changed,
    )
    connection_quick_insert_is_canvas_mode = pyqtProperty(
        bool,
        fget=state_helpers._qt_connection_quick_insert_is_canvas_mode,
        notify=connection_quick_insert_changed,
    )
    graph_hint_message = pyqtProperty(
        str,
        fget=state_helpers._qt_graph_hint_message,
        notify=graph_hint_changed,
    )
    graph_hint_visible = pyqtProperty(
        bool,
        fget=state_helpers._qt_graph_hint_visible,
        notify=graph_hint_changed,
    )
    graphics_show_grid = pyqtProperty(
        bool,
        fget=state_helpers._qt_graphics_show_grid,
        notify=graphics_preferences_changed,
    )
    graphics_grid_style = pyqtProperty(
        str,
        fget=state_helpers._qt_graphics_grid_style,
        notify=graphics_preferences_changed,
    )
    graphics_edge_crossing_style = pyqtProperty(
        str,
        fget=state_helpers._qt_graphics_edge_crossing_style,
        notify=graphics_preferences_changed,
    )
    graphics_show_minimap = pyqtProperty(
        bool,
        fget=state_helpers._qt_graphics_show_minimap,
        notify=graphics_preferences_changed,
    )
    graphics_show_port_labels = pyqtProperty(
        bool,
        fget=state_helpers._qt_graphics_show_port_labels,
        notify=graphics_preferences_changed,
    )
    graphics_minimap_expanded = pyqtProperty(
        bool,
        fget=state_helpers._qt_graphics_minimap_expanded,
        notify=graphics_preferences_changed,
    )
    graphics_node_shadow = pyqtProperty(
        bool,
        fget=state_helpers._qt_graphics_node_shadow,
        notify=graphics_preferences_changed,
    )
    graphics_shadow_strength = pyqtProperty(
        int,
        fget=state_helpers._qt_graphics_shadow_strength,
        notify=graphics_preferences_changed,
    )
    graphics_shadow_softness = pyqtProperty(
        int,
        fget=state_helpers._qt_graphics_shadow_softness,
        notify=graphics_preferences_changed,
    )
    graphics_shadow_offset = pyqtProperty(
        int,
        fget=state_helpers._qt_graphics_shadow_offset,
        notify=graphics_preferences_changed,
    )
    graphics_performance_mode = pyqtProperty(
        str,
        fget=state_helpers._qt_graphics_performance_mode,
        notify=graphics_preferences_changed,
    )
    graphics_tab_strip_density = pyqtProperty(
        str,
        fget=state_helpers._qt_graphics_tab_strip_density,
        notify=graphics_preferences_changed,
    )
    active_theme_id = pyqtProperty(
        str,
        fget=state_helpers._qt_active_theme_id,
        notify=graphics_preferences_changed,
    )
    snap_to_grid_enabled = pyqtProperty(
        bool,
        fget=state_helpers._qt_snap_to_grid_enabled,
        notify=snap_to_grid_changed,
    )
    snap_grid_size = pyqtProperty(float, fget=state_helpers._qt_snap_grid_size, constant=True)
    active_workspace_id = pyqtProperty(
        str,
        fget=state_helpers._qt_active_workspace_id,
        notify=workspace_state_changed,
    )
    active_workspace_name = pyqtProperty(
        str,
        fget=state_helpers._qt_active_workspace_name,
        notify=workspace_state_changed,
    )
    active_view_name = pyqtProperty(
        str,
        fget=state_helpers._qt_active_view_name,
        notify=workspace_state_changed,
    )
    active_view_items = pyqtProperty(
        "QVariantList",
        fget=state_helpers._qt_active_view_items,
        notify=workspace_state_changed,
    )
    active_scope_breadcrumb_items = pyqtProperty(
        "QVariantList",
        fget=state_helpers._qt_active_scope_breadcrumb_items,
        notify=workspace_state_changed,
    )
    selected_node_title = pyqtProperty(
        str,
        fget=state_helpers._qt_selected_node_title,
        notify=selected_node_changed,
    )
    selected_node_subtitle = pyqtProperty(
        str,
        fget=state_helpers._qt_selected_node_subtitle,
        notify=selected_node_changed,
    )
    selected_node_header_items = pyqtProperty(
        "QVariantList",
        fget=state_helpers._qt_selected_node_header_items,
        notify=selected_node_changed,
    )
    selected_node_summary = pyqtProperty(
        str,
        fget=state_helpers._qt_selected_node_summary,
        notify=selected_node_changed,
    )
    has_selected_node = pyqtProperty(
        bool,
        fget=state_helpers._qt_has_selected_node,
        notify=selected_node_changed,
    )
    selected_node_collapsible = pyqtProperty(
        bool,
        fget=state_helpers._qt_selected_node_collapsible,
        notify=selected_node_changed,
    )
    selected_node_collapsed = pyqtProperty(
        bool,
        fget=state_helpers._qt_selected_node_collapsed,
        notify=selected_node_changed,
    )
    selected_node_is_subnode_pin = pyqtProperty(
        bool,
        fget=state_helpers._qt_selected_node_is_subnode_pin,
        notify=selected_node_changed,
    )
    selected_node_is_subnode_shell = pyqtProperty(
        bool,
        fget=state_helpers._qt_selected_node_is_subnode_shell,
        notify=selected_node_changed,
    )
    can_publish_custom_workflow_from_scope = pyqtProperty(
        bool,
        fget=state_helpers._qt_can_publish_custom_workflow_from_scope,
        notify=workspace_state_changed,
    )
    selected_node_property_items = pyqtProperty(
        "QVariantList",
        fget=state_helpers._qt_selected_node_property_items,
        notify=selected_node_changed,
    )
    selected_node_port_items = pyqtProperty(
        "QVariantList",
        fget=state_helpers._qt_selected_node_port_items,
        notify=selected_node_changed,
    )

    locals().update(state_helpers.SHELL_WINDOW_FACADE_BINDINGS)

    def __init__(self, composition: ShellWindowComposition | None = None, *, _defer_bootstrap: bool = False) -> None:
        super().__init__()
        self._viewer_window_active = True
        self._application_state_signal_connected = False
        self._shell_teardown_started = False
        if _defer_bootstrap:
            return
        resolved_composition = composition or build_shell_window_composition(self)
        bootstrap_shell_window(self, resolved_composition)
        self._connect_application_state_signal()

    @property
    def embedded_viewer_overlay_manager(self) -> EmbeddedViewerOverlayManager | None:
        return self._ensure_embedded_viewer_overlay_manager()

    def _ensure_embedded_viewer_overlay_manager(
        self,
        quick_widget: QQuickWidget | None = None,
    ) -> EmbeddedViewerOverlayManager | None:
        resolved_quick_widget = quick_widget
        if resolved_quick_widget is None:
            candidate = getattr(self, "quick_widget", None)
            resolved_quick_widget = candidate if isinstance(candidate, QQuickWidget) else None
        if resolved_quick_widget is None:
            return None

        manager = getattr(self, "_embedded_viewer_overlay_manager", None)
        if manager is not None and manager.quick_widget is resolved_quick_widget:
            host_service = getattr(self, "viewer_host_service", None)
            if host_service is not None:
                host_service.set_overlay_manager(manager)
            return manager
        if manager is not None:
            host_service = getattr(self, "viewer_host_service", None)
            if host_service is not None:
                host_service.set_overlay_manager(None)
            manager.deleteLater()

        manager = EmbeddedViewerOverlayManager(
            resolved_quick_widget,
            quick_widget=resolved_quick_widget,
            shell_window=self,
            scene_bridge=self.scene,
            view_bridge=self.view,
        )
        self._embedded_viewer_overlay_manager = manager
        host_service = getattr(self, "viewer_host_service", None)
        if host_service is not None:
            host_service.set_overlay_manager(manager)
        return manager

    def setCentralWidget(self, widget) -> None:  # noqa: ANN001, N802
        existing_quick_widget = getattr(self, "quick_widget", None)
        if isinstance(existing_quick_widget, QQuickWidget) and widget is not existing_quick_widget:
            manager = getattr(self, "_embedded_viewer_overlay_manager", None)
            if manager is not None:
                host_service = getattr(self, "viewer_host_service", None)
                if host_service is not None:
                    host_service.set_overlay_manager(None)
                manager.deleteLater()
                self._embedded_viewer_overlay_manager = None
        super().setCentralWidget(widget)
        if isinstance(widget, QQuickWidget):
            self.quick_widget = widget
            self._ensure_embedded_viewer_overlay_manager(widget)

    def _wire_signals(self) -> None:
        self.scene.node_selected.connect(self._on_scene_node_selected)
        self.scene.scope_changed.connect(self._on_scene_scope_changed)
        self.script_editor.script_apply_requested.connect(self._on_node_property_changed)
        self.workspace_tabs.current_index_changed.connect(self._on_workspace_tab_changed)
        self.project_meta_changed.connect(self._on_project_meta_changed)

    def _create_session_store(self, serializer: Any) -> SessionAutosaveStore:
        return SessionAutosaveStore(
            serializer=serializer,
            session_path_provider=recent_session_path,
            autosave_path_provider=autosave_project_path,
        )

    def _create_execution_client(self):
        return ProcessExecutionClient()

    def _reset_viewer_session_bridge(self, *, reason: str) -> None:
        host_service = getattr(self, "viewer_host_service", None)
        if host_service is not None:
            host_service.reset(reason=reason)
        bridge = getattr(self, "viewer_session_bridge", None)
        if bridge is None:
            return
        bridge.reset_all_sessions(reason=reason)

    def _open_logs(self) -> None:
        return

    def _handle_window_deactivate(self) -> None:
        if not getattr(self, "_viewer_window_active", True):
            return
        self._viewer_window_active = False
        bridge = getattr(self, "viewer_session_bridge", None)
        clear_focus = getattr(bridge, "clear_viewer_focus", None)
        if not callable(clear_focus):
            return
        try:
            clear_focus()
        except Exception:  # noqa: BLE001
            return

    def _connect_application_state_signal(self) -> None:
        if self._application_state_signal_connected:
            return
        app = QApplication.instance()
        signal = getattr(app, "applicationStateChanged", None) if app is not None else None
        if signal is not None and hasattr(signal, "connect"):
            signal.connect(self._handle_application_state_changed)
            self._application_state_signal_connected = True

    def _disconnect_application_state_signal(self) -> None:
        if not self._application_state_signal_connected:
            return
        app = QApplication.instance()
        signal = getattr(app, "applicationStateChanged", None) if app is not None else None
        if signal is None or not hasattr(signal, "disconnect"):
            self._application_state_signal_connected = False
            return
        try:
            signal.disconnect(self._handle_application_state_changed)
        except (TypeError, RuntimeError):
            pass
        self._application_state_signal_connected = False

    def _teardown_qml_surface(self) -> None:
        host_service = getattr(self, "viewer_host_service", None)
        shutdown = getattr(host_service, "shutdown", None)
        if callable(shutdown):
            shutdown(reason="window_close")

        manager = getattr(self, "_embedded_viewer_overlay_manager", None)
        if manager is not None:
            manager.deleteLater()
            self._embedded_viewer_overlay_manager = None

        quick_widget = getattr(self, "quick_widget", None)
        if not isinstance(quick_widget, QQuickWidget):
            return
        try:
            quick_widget.setUpdatesEnabled(False)
        except Exception:  # noqa: BLE001
            pass
        try:
            quick_widget.setSource(QUrl())
        except Exception:  # noqa: BLE001
            return

    def _handle_application_state_changed(self, state) -> None:  # noqa: ANN001
        if state == Qt.ApplicationState.ApplicationActive:
            self._viewer_window_active = True
            return
        self._handle_window_deactivate()

    def event(self, event):  # noqa: ANN001
        if event is not None and event.type() == QEvent.Type.WindowDeactivate:
            self._handle_window_deactivate()
        return super().event(event)

    def changeEvent(self, event) -> None:  # noqa: ANN001
        if event is not None and event.type() == QEvent.Type.ActivationChange:
            if self.isActiveWindow():
                self._viewer_window_active = True
            else:
                self._handle_window_deactivate()
        super().changeEvent(event)

    def showEvent(self, event) -> None:  # noqa: ANN001
        self._viewer_window_active = True
        super().showEvent(event)
        if self._autosave_recovery_deferred:
            QTimer.singleShot(0, self._process_deferred_autosave_recovery_if_open)

    def _process_deferred_autosave_recovery_if_open(self) -> None:
        if self._shell_teardown_started:
            return
        self._process_deferred_autosave_recovery()

    def closeEvent(self, event) -> None:  # noqa: ANN001
        if self._shell_teardown_started:
            super().closeEvent(event)
            return
        self._shell_teardown_started = True
        for timer_name in ("metrics_timer", "graph_hint_timer", "autosave_timer"):
            timer = getattr(self, timer_name, None)
            if timer is not None:
                timer.stop()
        try:
            if hasattr(self, "run_state"):
                self.clear_run_failure_focus()
            self._reset_viewer_session_bridge(reason="project_close")
            project_session_controller = getattr(self, "project_session_controller", None)
            if project_session_controller is not None:
                project_session_controller.close_session()
            self._disconnect_application_state_signal()
            self._teardown_qml_surface()
        finally:
            execution_client = getattr(self, "execution_client", None)
            if execution_client is not None:
                execution_client.shutdown()
            super().closeEvent(event)
