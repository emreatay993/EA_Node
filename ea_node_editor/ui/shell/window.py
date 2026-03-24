from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any, Callable, Literal

from PyQt6.QtCore import QTimer, Qt, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QCursor
from PyQt6.QtQuick import QQuickWindow, QSGRendererInterface
from PyQt6.QtQuickWidgets import QQuickWidget
from PyQt6.QtWidgets import QApplication, QFileDialog, QInputDialog, QMainWindow, QMessageBox

from ea_node_editor.execution.client import ProcessExecutionClient
from ea_node_editor.graph.effective_ports import find_port, port_kind
from ea_node_editor.graph.model import GraphModel, ProjectData
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.builtins.subnode import (
    SUBNODE_INPUT_TYPE_ID,
    SUBNODE_OUTPUT_TYPE_ID,
    SUBNODE_PIN_DATA_TYPE_PROPERTY,
    SUBNODE_TYPE_ID,
)
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.persistence.session_store import SessionAutosaveStore
from ea_node_editor.settings import (
    AUTOSAVE_INTERVAL_MS,
    autosave_project_path,
    DEFAULT_GRAPHICS_SETTINGS,
    recent_session_path,
)
from ea_node_editor.telemetry.frame_rate import FrameRateSampler
from ea_node_editor.telemetry.system_metrics import read_system_metrics
from ea_node_editor.ui.graph_interactions import GraphInteractions
from ea_node_editor.ui.graph_theme import (
    default_graph_theme_id_for_shell_theme,
    resolve_graph_theme_id,
    serialize_custom_graph_themes,
)
from ea_node_editor.ui.icon_registry import UiIconImageProvider, UiIconRegistryBridge
from ea_node_editor.ui.media_preview_provider import LocalMediaPreviewImageProvider
from ea_node_editor.ui.pdf_preview_provider import (
    LocalPdfPreviewImageProvider,
    describe_pdf_preview,
)
from ea_node_editor.ui.dialogs.passive_style_controls import (
    normalize_flow_edge_style_payload,
    normalize_passive_node_style_payload,
)
from ea_node_editor.ui.passive_style_presets import normalize_passive_style_presets
from ea_node_editor.ui.shell.composition import (
    ShellWindowComposition,
    bootstrap_shell_window,
    build_shell_window_composition,
)
from ea_node_editor.ui.shell.controllers import (
    AppPreferencesController,
    ProjectSessionController,
    RunController,
    WorkspaceLibraryController,
)
from ea_node_editor.ui.shell.controllers.app_preferences_controller import normalize_graph_theme_settings
from ea_node_editor.ui.shell.presenters import (
    GraphCanvasPresenter,
    ShellInspectorPresenter,
    ShellLibraryPresenter,
    ShellWorkspacePresenter,
    build_default_shell_workspace_ui_state,
)
from ea_node_editor.ui.shell.runtime_history import RuntimeGraphHistory
from ea_node_editor.ui.shell.state import ShellState
from ea_node_editor.ui.shell.window_actions import build_window_menu_bar, create_window_actions
from ea_node_editor.ui.shell.window_library_inspector import (
    build_canvas_quick_insert_items,
    build_connection_quick_insert_items,
    build_combined_library_items,
    build_filtered_library_items,
    build_grouped_library_items,
    build_library_category_options,
    build_library_data_type_options,
    build_library_direction_options,
    build_pin_data_type_options,
    build_registry_library_items,
    build_selected_node_header_data,
    build_selected_node_port_items,
    build_selected_node_property_items,
    library_item_matches_filters,
)
from ea_node_editor.ui.shell.window_search_scope_state import WindowSearchScopeController
from ea_node_editor.ui.theme import build_theme_stylesheet
from ea_node_editor.ui_qml.console_model import ConsoleModel
from ea_node_editor.ui_qml.graph_canvas_command_bridge import GraphCanvasCommandBridge
from ea_node_editor.ui_qml.graph_canvas_state_bridge import GraphCanvasStateBridge
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge
from ea_node_editor.ui_qml.script_editor_model import ScriptEditorModel
from ea_node_editor.ui_qml.shell_context_bootstrap import (
    ShellContextBridges,
    bootstrap_shell_qml_context,
    create_shell_context_bridges,
)
from ea_node_editor.ui_qml.shell_inspector_bridge import ShellInspectorBridge
from ea_node_editor.ui_qml.shell_library_bridge import ShellLibraryBridge
from ea_node_editor.ui_qml.shell_workspace_bridge import ShellWorkspaceBridge
from ea_node_editor.ui_qml.status_model import StatusItemModel
from ea_node_editor.ui_qml.syntax_bridge import QmlScriptSyntaxBridge
from ea_node_editor.ui_qml.theme_bridge import ThemeBridge
from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge
from ea_node_editor.ui_qml.workspace_tabs_model import WorkspaceTabsModel
from ea_node_editor.workspace.manager import WorkspaceManager


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
_UNSET = object()
_PASSIVE_NODE_STYLE_CLIPBOARD_KIND = "passive-node-style"
_FLOW_EDGE_STYLE_CLIPBOARD_KIND = "flow-edge-style"
_STYLE_CLIPBOARD_APP_PROPERTY = "eaNodeEditorStyleClipboard"


class ShellWindow(QMainWindow):
    execution_event = pyqtSignal(dict)
    node_library_changed = pyqtSignal()
    library_pane_reset_requested = pyqtSignal(name="libraryPaneResetRequested")
    workspace_state_changed = pyqtSignal()
    selected_node_changed = pyqtSignal()
    project_meta_changed = pyqtSignal()
    graph_search_changed = pyqtSignal()
    connection_quick_insert_changed = pyqtSignal()
    graph_hint_changed = pyqtSignal()
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

    def __init__(self, composition: ShellWindowComposition | None = None, *, _defer_bootstrap: bool = False) -> None:
        super().__init__()
        if _defer_bootstrap:
            return
        resolved_composition = composition or build_shell_window_composition(self)
        bootstrap_shell_window(self, resolved_composition)

    @property
    def workflow_library_controller(self):
        return self.workspace_library_controller.workflow_library_controller

    @property
    def workspace_navigation_controller(self):
        return self.workspace_library_controller.workspace_navigation_controller

    @property
    def workspace_graph_edit_controller(self):
        return self.workspace_library_controller.workspace_graph_edit_controller

    @property
    def workspace_package_io_controller(self):
        return self.workspace_library_controller.workspace_package_io_controller

    @property
    def graph_canvas_state_bridge(self) -> GraphCanvasStateBridge | None:
        bridges = getattr(self, "_shell_context_bridges", None)
        if bridges is None:
            return None
        return bridges.graph_canvas_state_bridge

    @property
    def graph_canvas_command_bridge(self) -> GraphCanvasCommandBridge | None:
        bridges = getattr(self, "_shell_context_bridges", None)
        if bridges is None:
            return None
        return bridges.graph_canvas_command_bridge

    @property
    def project_path(self) -> str:
        return self.project_session_state.project_path

    @project_path.setter
    def project_path(self, value: str) -> None:
        self.project_session_state.project_path = str(value)

    @property
    def recent_project_paths(self) -> list[str]:
        return list(self.project_session_state.recent_project_paths)

    @recent_project_paths.setter
    def recent_project_paths(self, value: list[str]) -> None:
        self.project_session_state.recent_project_paths = [str(path) for path in value]

    @property
    def _library_query(self) -> str:
        return self.library_filter_state.library_query

    @_library_query.setter
    def _library_query(self, value: str) -> None:
        self.library_filter_state.library_query = str(value)

    @property
    def _library_category(self) -> str:
        return self.library_filter_state.library_category

    @_library_category.setter
    def _library_category(self, value: str) -> None:
        self.library_filter_state.library_category = str(value)

    @property
    def _library_data_type(self) -> str:
        return self.library_filter_state.library_data_type

    @_library_data_type.setter
    def _library_data_type(self, value: str) -> None:
        self.library_filter_state.library_data_type = str(value)

    @property
    def _library_direction(self) -> str:
        return self.library_filter_state.library_direction

    @_library_direction.setter
    def _library_direction(self, value: str) -> None:
        self.library_filter_state.library_direction = str(value)

    @property
    def _active_run_id(self) -> str:
        return self.run_state.active_run_id

    @_active_run_id.setter
    def _active_run_id(self, value: str) -> None:
        self.run_state.active_run_id = str(value)

    @property
    def _active_run_workspace_id(self) -> str:
        return self.run_state.active_run_workspace_id

    @_active_run_workspace_id.setter
    def _active_run_workspace_id(self, value: str) -> None:
        self.run_state.active_run_workspace_id = str(value)

    @property
    def _engine_state_value(self) -> Literal["ready", "running", "paused", "error"]:
        return self.run_state.engine_state_value

    @_engine_state_value.setter
    def _engine_state_value(self, value: Literal["ready", "running", "paused", "error"] | str) -> None:
        normalized = str(value)
        if normalized not in {"ready", "running", "paused", "error"}:
            normalized = "ready"
        self.run_state.engine_state_value = normalized  # type: ignore[assignment]

    @property
    def _last_manual_save_ts(self) -> float:
        return self.project_session_state.last_manual_save_ts

    @_last_manual_save_ts.setter
    def _last_manual_save_ts(self, value: float) -> None:
        self.project_session_state.last_manual_save_ts = float(value)

    @property
    def _last_autosave_fingerprint(self) -> str:
        return self.project_session_state.last_autosave_fingerprint

    @_last_autosave_fingerprint.setter
    def _last_autosave_fingerprint(self, value: str) -> None:
        self.project_session_state.last_autosave_fingerprint = str(value)

    @property
    def _autosave_recovery_deferred(self) -> bool:
        return self.project_session_state.autosave_recovery_deferred

    @_autosave_recovery_deferred.setter
    def _autosave_recovery_deferred(self, value: bool) -> None:
        self.project_session_state.autosave_recovery_deferred = bool(value)

    def _create_actions(self) -> None:
        create_window_actions(self)

    def _build_menu_bar(self) -> None:
        build_window_menu_bar(self)

    @staticmethod
    def _format_recent_project_menu_label(index: int, project_path: str) -> str:
        path = Path(project_path)
        parent = str(path.parent)
        if not parent or parent == ".":
            return f"{index}. {path.name}"
        return f"{index}. {path.name} [{parent}]"

    def _refresh_recent_projects_menu(self) -> None:
        menu = getattr(self, "menu_recent_projects", None)
        if menu is None:
            return
        menu.clear()
        recent_paths = list(self.recent_project_paths)
        if not recent_paths:
            empty_action = menu.addAction("No Recent Files")
            empty_action.setEnabled(False)
            return

        current_project_path = self.project_session_controller._normalize_project_path(self.project_path)
        for index, project_path in enumerate(recent_paths, start=1):
            action = menu.addAction(self._format_recent_project_menu_label(index, project_path))
            action.setToolTip(project_path)
            action.setStatusTip(project_path)
            action.triggered.connect(
                lambda _checked=False, selected_path=project_path: self._open_project_path(selected_path)
            )
            if current_project_path and project_path == current_project_path:
                action.setEnabled(False)
        menu.addSeparator()
        menu.addAction(self.action_clear_recent_projects)

    def _wire_signals(self) -> None:
        self.scene.node_selected.connect(self._on_scene_node_selected)
        self.scene.scope_changed.connect(self._on_scene_scope_changed)
        self.script_editor.script_apply_requested.connect(self._on_node_property_changed)
        self.workspace_tabs.current_index_changed.connect(self._on_workspace_tab_changed)

    def _create_session_store(self, serializer: Any) -> SessionAutosaveStore:
        return SessionAutosaveStore(
            serializer=serializer,
            session_path_provider=recent_session_path,
            autosave_path_provider=autosave_project_path,
        )

    def _create_execution_client(self):
        return ProcessExecutionClient()

    @pyqtProperty(str, notify=project_meta_changed)
    def project_display_name(self) -> str:
        return self.shell_workspace_presenter.project_display_name

    def _registry_library_items(self) -> list[dict[str, Any]]:
        return self.shell_library_presenter._registry_library_items()

    def _combined_library_items(self) -> list[dict[str, Any]]:
        return self.shell_library_presenter._combined_library_items()

    def _library_item_matches_filters(
        self,
        item: dict[str, Any],
        *,
        query: str,
        category: str,
        data_type: str,
        direction: str,
    ) -> bool:
        return self.shell_library_presenter._library_item_matches_filters(
            item,
            query=query,
            category=category,
            data_type=data_type,
            direction=direction,
        )

    @pyqtProperty("QVariantList", notify=node_library_changed)
    def filtered_node_library_items(self) -> list[dict[str, Any]]:
        return self.shell_library_presenter.filtered_node_library_items

    @pyqtProperty("QVariantList", notify=node_library_changed)
    def grouped_node_library_items(self) -> list[dict[str, Any]]:
        return self.shell_library_presenter.grouped_node_library_items

    @pyqtProperty("QVariantList", notify=node_library_changed)
    def library_category_options(self) -> list[dict[str, str]]:
        return self.shell_library_presenter.library_category_options

    @pyqtProperty("QVariantList", notify=node_library_changed)
    def library_direction_options(self) -> list[dict[str, str]]:
        return self.shell_library_presenter.library_direction_options

    @pyqtProperty("QVariantList", notify=node_library_changed)
    def library_data_type_options(self) -> list[dict[str, str]]:
        return self.shell_library_presenter.library_data_type_options

    @pyqtProperty("QVariantList", notify=workspace_state_changed)
    def pin_data_type_options(self) -> list[str]:
        return self.shell_inspector_presenter.pin_data_type_options

    @pyqtProperty(bool, notify=graph_search_changed)
    def graph_search_open(self) -> bool:
        return self.shell_library_presenter.graph_search_open

    @pyqtProperty(str, notify=graph_search_changed)
    def graph_search_query(self) -> str:
        return self.shell_library_presenter.graph_search_query

    @pyqtProperty("QVariantList", notify=graph_search_changed)
    def graph_search_enabled_scopes(self) -> list[str]:
        return self.shell_library_presenter.graph_search_enabled_scopes

    @pyqtProperty("QVariantList", notify=graph_search_changed)
    def graph_search_results(self) -> list[dict[str, Any]]:
        return self.shell_library_presenter.graph_search_results

    @pyqtProperty(int, notify=graph_search_changed)
    def graph_search_highlight_index(self) -> int:
        return self.shell_library_presenter.graph_search_highlight_index

    @pyqtProperty(bool, notify=connection_quick_insert_changed)
    def connection_quick_insert_open(self) -> bool:
        return self.shell_library_presenter.connection_quick_insert_open

    @pyqtProperty(str, notify=connection_quick_insert_changed)
    def connection_quick_insert_query(self) -> str:
        return self.shell_library_presenter.connection_quick_insert_query

    @pyqtProperty("QVariantList", notify=connection_quick_insert_changed)
    def connection_quick_insert_results(self) -> list[dict[str, Any]]:
        return self.shell_library_presenter.connection_quick_insert_results

    @pyqtProperty(int, notify=connection_quick_insert_changed)
    def connection_quick_insert_highlight_index(self) -> int:
        return self.shell_library_presenter.connection_quick_insert_highlight_index

    @pyqtProperty(float, notify=connection_quick_insert_changed)
    def connection_quick_insert_overlay_x(self) -> float:
        return self.shell_library_presenter.connection_quick_insert_overlay_x

    @pyqtProperty(float, notify=connection_quick_insert_changed)
    def connection_quick_insert_overlay_y(self) -> float:
        return self.shell_library_presenter.connection_quick_insert_overlay_y

    @pyqtProperty(str, notify=connection_quick_insert_changed)
    def connection_quick_insert_source_summary(self) -> str:
        return self.shell_library_presenter.connection_quick_insert_source_summary

    @pyqtProperty(bool, notify=connection_quick_insert_changed)
    def connection_quick_insert_is_canvas_mode(self) -> bool:
        return self.shell_library_presenter.connection_quick_insert_is_canvas_mode

    @pyqtProperty(str, notify=graph_hint_changed)
    def graph_hint_message(self) -> str:
        return self.shell_library_presenter.graph_hint_message

    @pyqtProperty(bool, notify=graph_hint_changed)
    def graph_hint_visible(self) -> bool:
        return self.shell_library_presenter.graph_hint_visible

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_show_grid(self) -> bool:
        return self.graph_canvas_presenter.graphics_show_grid

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_show_minimap(self) -> bool:
        return self.graph_canvas_presenter.graphics_show_minimap

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_show_port_labels(self) -> bool:
        return self.graph_canvas_presenter.graphics_show_port_labels

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_minimap_expanded(self) -> bool:
        return self.graph_canvas_presenter.graphics_minimap_expanded

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_node_shadow(self) -> bool:
        return self.graph_canvas_presenter.graphics_node_shadow

    @pyqtProperty(int, notify=graphics_preferences_changed)
    def graphics_shadow_strength(self) -> int:
        return self.graph_canvas_presenter.graphics_shadow_strength

    @pyqtProperty(int, notify=graphics_preferences_changed)
    def graphics_shadow_softness(self) -> int:
        return self.graph_canvas_presenter.graphics_shadow_softness

    @pyqtProperty(int, notify=graphics_preferences_changed)
    def graphics_shadow_offset(self) -> int:
        return self.graph_canvas_presenter.graphics_shadow_offset

    @pyqtProperty(str, notify=graphics_preferences_changed)
    def graphics_performance_mode(self) -> str:
        return self.shell_workspace_presenter.graphics_performance_mode

    @pyqtProperty(str, notify=graphics_preferences_changed)
    def graphics_tab_strip_density(self) -> str:
        return self.shell_workspace_presenter.graphics_tab_strip_density

    @pyqtProperty(str, notify=graphics_preferences_changed)
    def active_theme_id(self) -> str:
        return self.shell_workspace_presenter.active_theme_id

    @pyqtProperty(bool, notify=snap_to_grid_changed)
    def snap_to_grid_enabled(self) -> bool:
        return self.graph_canvas_presenter.snap_to_grid_enabled

    @pyqtProperty(float, constant=True)
    def snap_grid_size(self) -> float:
        return self.graph_canvas_presenter.snap_grid_size

    @pyqtProperty(str, notify=workspace_state_changed)
    def active_workspace_id(self) -> str:
        return self.shell_workspace_presenter.active_workspace_id

    @pyqtProperty(str, notify=workspace_state_changed)
    def active_workspace_name(self) -> str:
        return self.shell_workspace_presenter.active_workspace_name

    @pyqtProperty(str, notify=workspace_state_changed)
    def active_view_name(self) -> str:
        return self.shell_workspace_presenter.active_view_name

    @pyqtProperty("QVariantList", notify=workspace_state_changed)
    def active_view_items(self) -> list[dict[str, Any]]:
        return self.shell_workspace_presenter.active_view_items

    @pyqtProperty("QVariantList", notify=workspace_state_changed)
    def active_scope_breadcrumb_items(self) -> list[dict[str, str]]:
        return self.shell_workspace_presenter.active_scope_breadcrumb_items

    def _selected_node_header_data(self) -> dict[str, Any]:
        return self.shell_inspector_presenter._selected_node_header_data()

    @pyqtProperty(str, notify=selected_node_changed)
    def selected_node_title(self) -> str:
        return self.shell_inspector_presenter.selected_node_title

    @pyqtProperty(str, notify=selected_node_changed)
    def selected_node_subtitle(self) -> str:
        return self.shell_inspector_presenter.selected_node_subtitle

    @pyqtProperty("QVariantList", notify=selected_node_changed)
    def selected_node_header_items(self) -> list[dict[str, str]]:
        return self.shell_inspector_presenter.selected_node_header_items

    @pyqtProperty(str, notify=selected_node_changed)
    def selected_node_summary(self) -> str:
        return self.shell_inspector_presenter.selected_node_summary

    @pyqtProperty(bool, notify=selected_node_changed)
    def has_selected_node(self) -> bool:
        return self.shell_inspector_presenter.has_selected_node

    @pyqtProperty(bool, notify=selected_node_changed)
    def selected_node_collapsible(self) -> bool:
        return self.shell_inspector_presenter.selected_node_collapsible

    @pyqtProperty(bool, notify=selected_node_changed)
    def selected_node_collapsed(self) -> bool:
        return self.shell_inspector_presenter.selected_node_collapsed

    @pyqtProperty(bool, notify=selected_node_changed)
    def selected_node_is_subnode_pin(self) -> bool:
        return self.shell_inspector_presenter.selected_node_is_subnode_pin

    @pyqtProperty(bool, notify=selected_node_changed)
    def selected_node_is_subnode_shell(self) -> bool:
        return self.shell_inspector_presenter.selected_node_is_subnode_shell

    @pyqtProperty(bool, notify=workspace_state_changed)
    def can_publish_custom_workflow_from_scope(self) -> bool:
        return self.shell_workspace_presenter.can_publish_custom_workflow_from_scope

    @pyqtProperty("QVariantList", notify=selected_node_changed)
    def selected_node_property_items(self) -> list[dict[str, Any]]:
        return self.shell_inspector_presenter.selected_node_property_items

    def _node_property_spec(self, node_id: str, key: str):
        return self.shell_inspector_presenter._node_property_spec(node_id, key)

    def _selected_node_property_spec(self, key: str):
        return self.shell_inspector_presenter._selected_node_property_spec(key)

    def _path_dialog_start_path(self, current_path: str) -> str:
        return self.shell_inspector_presenter._path_dialog_start_path(current_path)

    @pyqtProperty("QVariantList", notify=selected_node_changed)
    def selected_node_port_items(self) -> list[dict[str, Any]]:
        return self.shell_inspector_presenter.selected_node_port_items

    def _set_graph_search_state(
        self,
        *,
        open_: bool | None = None,
        query: str | None = None,
        enabled_scopes: list[str] | None = None,
        results: list[dict[str, Any]] | None = None,
        highlight_index: int | None = None,
    ) -> None:
        self.shell_library_presenter._set_graph_search_state(
            open_=open_,
            query=query,
            enabled_scopes=enabled_scopes,
            results=results,
            highlight_index=highlight_index,
        )

    def _refresh_graph_search_results(self, query: str) -> None:
        self.shell_library_presenter._refresh_graph_search_results(query)

    def _set_connection_quick_insert_state(
        self,
        *,
        open_: bool | None = None,
        query: str | None = None,
        results: list[dict[str, Any]] | None = None,
        highlight_index: int | None = None,
        context: dict[str, Any] | None | object = _UNSET,
    ) -> None:
        self.shell_library_presenter._set_connection_quick_insert_state(
            open_=open_,
            query=query,
            results=results,
            highlight_index=highlight_index,
            context=context,
        )

    def _connection_quick_insert_context_for_port(
        self,
        node_id: str,
        port_key: str,
    ) -> dict[str, Any] | None:
        return self.shell_library_presenter._connection_quick_insert_context_for_port(node_id, port_key)

    def _refresh_connection_quick_insert_results(self, query: str) -> None:
        self.shell_library_presenter._refresh_connection_quick_insert_results(query)

    def _active_scope_camera_key(self, scope_path: tuple[str, ...] | None = None) -> tuple[str, str, tuple[str, ...]] | None:
        return self.search_scope_controller.active_scope_camera_key(scope_path)

    def _remember_scope_camera(self, scope_path: tuple[str, ...] | None = None) -> None:
        self.search_scope_controller.remember_scope_camera(scope_path)

    def _restore_scope_camera(self, scope_path: tuple[str, ...] | None = None) -> bool:
        return bool(self.search_scope_controller.restore_scope_camera(scope_path))

    def _navigate_scope(self, navigate_fn: Callable[[], bool]) -> bool:
        return bool(self.search_scope_controller.navigate_scope(navigate_fn))

    def _on_scene_scope_changed(self) -> None:
        self.request_close_connection_quick_insert()
        self.workspace_state_changed.emit()
        self.selected_node_changed.emit()

    @pyqtSlot(str)
    def set_library_query(self, query: str) -> None:
        self.shell_library_presenter.set_library_query(query)

    @pyqtSlot(str)
    def set_library_category(self, category: str) -> None:
        self.shell_library_presenter.set_library_category(category)

    @pyqtSlot(str)
    def set_library_data_type(self, data_type: str) -> None:
        self.shell_library_presenter.set_library_data_type(data_type)

    @pyqtSlot(str)
    def set_library_direction(self, direction: str) -> None:
        self.shell_library_presenter.set_library_direction(direction)

    @pyqtSlot(bool)
    def set_snap_to_grid_enabled(self, enabled: bool) -> None:
        self.graph_canvas_presenter.set_snap_to_grid_enabled(enabled)

    @pyqtSlot(bool)
    def set_graphics_minimap_expanded(self, expanded: bool) -> None:
        self.graph_canvas_presenter.set_graphics_minimap_expanded(expanded)

    @pyqtSlot(bool)
    def set_graphics_show_port_labels(self, show_port_labels: bool) -> None:
        self.app_preferences_controller.update_graphics_settings(
            {
                "canvas": {
                    "show_port_labels": show_port_labels,
                }
            },
            host=self,
        )

    def _sync_graphics_show_port_labels_action(self, show_port_labels: bool) -> None:
        action = getattr(self, "action_show_port_labels", None)
        if action is None or action.isChecked() == show_port_labels:
            return
        blocked = action.blockSignals(True)
        action.setChecked(show_port_labels)
        action.blockSignals(blocked)

    def _refresh_active_workspace_scene_payload(self) -> None:
        workspace_manager = getattr(self, "workspace_manager", None)
        scene = getattr(self, "scene", None)
        if workspace_manager is None or scene is None:
            return
        workspace_id = str(workspace_manager.active_workspace_id() or "").strip()
        if not workspace_id:
            return
        scene.refresh_workspace_from_model(workspace_id)

    @pyqtSlot(str)
    def set_graphics_performance_mode(self, mode: str) -> None:
        self.app_preferences_controller.update_graphics_settings(
            {
                "performance": {
                    "mode": mode,
                }
            },
            host=self,
        )

    @pyqtSlot(str)
    @pyqtSlot(str, int)
    def show_graph_hint(self, message: str, timeout_ms: int = 3600) -> None:
        self.shell_library_presenter.show_graph_hint(message, timeout_ms)

    @pyqtSlot()
    def clear_graph_hint(self) -> None:
        self.shell_library_presenter.clear_graph_hint()

    def _apply_graph_cursor(self, cursor_shape: Qt.CursorShape) -> None:
        self.shell_host_presenter.apply_graph_cursor(cursor_shape)

    @pyqtSlot(int)
    def set_graph_cursor_shape(self, cursor_shape: int) -> None:
        self.shell_host_presenter.set_graph_cursor_shape(cursor_shape)

    @pyqtSlot()
    def clear_graph_cursor_shape(self) -> None:
        self.shell_host_presenter.clear_graph_cursor_shape()

    def _apply_theme(self, theme_id: Any) -> str:
        return self.shell_host_presenter.apply_theme(theme_id)

    def preview_graph_theme_settings(self, graph_theme_settings: Any) -> str:
        return self.shell_host_presenter.preview_graph_theme_settings(graph_theme_settings)

    def apply_graphics_preferences(self, graphics: Any) -> dict[str, Any]:
        previous_show_port_labels = bool(
            getattr(getattr(self, "workspace_ui_state", None), "show_port_labels", True)
        )
        resolved = self.shell_workspace_presenter.apply_graphics_preferences(graphics)
        canvas = resolved.get("canvas", {}) if isinstance(resolved, dict) else {}
        current_show_port_labels = bool(canvas.get("show_port_labels", previous_show_port_labels))
        self._sync_graphics_show_port_labels_action(current_show_port_labels)
        if previous_show_port_labels != current_show_port_labels:
            self._refresh_active_workspace_scene_payload()
        return resolved

    @pyqtSlot()
    def request_open_graph_search(self) -> None:
        self.shell_library_presenter.request_open_graph_search()

    @pyqtSlot()
    def request_close_graph_search(self) -> None:
        self.shell_library_presenter.request_close_graph_search()

    @pyqtSlot(str, str, float, float, float, float, result=bool)
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
            self.graph_canvas_presenter.request_open_connection_quick_insert(
                node_id,
                port_key,
                scene_x,
                scene_y,
                overlay_x,
                overlay_y,
            )
        )

    @pyqtSlot(float, float, float, float)
    def request_open_canvas_quick_insert(
        self,
        scene_x: float,
        scene_y: float,
        overlay_x: float,
        overlay_y: float,
    ) -> None:
        self.graph_canvas_presenter.request_open_canvas_quick_insert(
            scene_x,
            scene_y,
            overlay_x,
            overlay_y,
        )

    @pyqtSlot()
    def request_close_connection_quick_insert(self) -> None:
        self.shell_library_presenter.request_close_connection_quick_insert()

    @pyqtSlot(str)
    def set_connection_quick_insert_query(self, query: str) -> None:
        self.shell_library_presenter.set_connection_quick_insert_query(query)

    @pyqtSlot(int)
    def request_connection_quick_insert_move(self, delta: int) -> None:
        self.shell_library_presenter.request_connection_quick_insert_move(delta)

    @pyqtSlot(int)
    def request_connection_quick_insert_highlight(self, index: int) -> None:
        self.shell_library_presenter.request_connection_quick_insert_highlight(index)

    @pyqtSlot(result=bool)
    def request_connection_quick_insert_accept(self) -> bool:
        return bool(self.shell_library_presenter.request_connection_quick_insert_accept())

    @pyqtSlot(int, result=bool)
    def request_connection_quick_insert_choose(self, index: int) -> bool:
        return bool(self.shell_library_presenter.request_connection_quick_insert_choose(index))

    @pyqtSlot(str)
    def set_graph_search_query(self, query: str) -> None:
        self.shell_library_presenter.set_graph_search_query(query)

    @pyqtSlot(str, bool)
    def set_graph_search_scope_enabled(self, scope_id: str, enabled: bool) -> None:
        self.shell_library_presenter.set_graph_search_scope_enabled(scope_id, enabled)

    @pyqtSlot(int)
    def request_graph_search_move(self, delta: int) -> None:
        self.shell_library_presenter.request_graph_search_move(delta)

    @pyqtSlot(int)
    def request_graph_search_highlight(self, index: int) -> None:
        self.shell_library_presenter.request_graph_search_highlight(index)

    @pyqtSlot(result=bool)
    def request_graph_search_accept(self) -> bool:
        return bool(self.shell_library_presenter.request_graph_search_accept())

    @pyqtSlot(int, result=bool)
    def request_graph_search_jump(self, index: int) -> bool:
        return bool(self.shell_library_presenter.request_graph_search_jump(index))

    @pyqtSlot(str)
    def request_add_node_from_library(self, type_id: str) -> None:
        self.shell_library_presenter.request_add_node_from_library(type_id)

    @pyqtSlot(result=bool)
    def request_publish_custom_workflow_from_selected(self) -> bool:
        return bool(self.shell_library_presenter.request_publish_custom_workflow_from_selected())

    @pyqtSlot(result=bool)
    def request_publish_custom_workflow_from_scope(self) -> bool:
        return bool(self.shell_library_presenter.request_publish_custom_workflow_from_scope())

    @pyqtSlot(str, result=bool)
    def request_publish_custom_workflow_from_node(self, node_id: str) -> bool:
        return bool(self.shell_library_presenter.request_publish_custom_workflow_from_node(node_id))

    @pyqtSlot(str, result=bool)
    @pyqtSlot(str, str, result=bool)
    def request_delete_custom_workflow_from_library(self, workflow_id: str, workflow_scope: str = "") -> bool:
        return bool(
            self.shell_library_presenter.request_delete_custom_workflow_from_library(
                workflow_id,
                workflow_scope,
            )
        )

    @pyqtSlot(str, result=bool)
    @pyqtSlot(str, str, result=bool)
    def request_rename_custom_workflow_from_library(self, workflow_id: str, workflow_scope: str = "") -> bool:
        return bool(
            self.shell_library_presenter.request_rename_custom_workflow_from_library(
                workflow_id,
                workflow_scope,
            )
        )

    @pyqtSlot(str, str, result=bool)
    def request_set_custom_workflow_scope(self, workflow_id: str, workflow_scope: str) -> bool:
        return bool(self.shell_library_presenter.request_set_custom_workflow_scope(workflow_id, workflow_scope))

    @pyqtSlot(str, float, float, str, str, str, str, result=bool)
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
            self.graph_canvas_presenter.request_drop_node_from_library(
                type_id,
                scene_x,
                scene_y,
                target_mode,
                target_node_id,
                target_port_key,
                target_edge_id,
            )
        )

    @pyqtSlot()
    def request_run_workflow(self) -> None:
        self.shell_workspace_presenter.request_run_workflow()

    @pyqtSlot()
    def request_toggle_run_pause(self) -> None:
        self.shell_workspace_presenter.request_toggle_run_pause()

    @pyqtSlot()
    def request_stop_workflow(self) -> None:
        self.shell_workspace_presenter.request_stop_workflow()

    @pyqtSlot()
    def request_create_workspace(self) -> None:
        self.shell_workspace_presenter.request_create_workspace()

    @pyqtSlot()
    def request_create_view(self) -> None:
        self.shell_workspace_presenter.request_create_view()

    @pyqtSlot(str)
    def request_switch_view(self, view_id: str) -> None:
        self.shell_workspace_presenter.request_switch_view(view_id)

    @pyqtSlot(str, result=bool)
    def request_open_subnode_scope(self, node_id: str) -> bool:
        return bool(self.graph_canvas_presenter.request_open_subnode_scope(node_id))

    @pyqtSlot(str, result=bool)
    def request_open_scope_breadcrumb(self, node_id: str) -> bool:
        return bool(self.shell_workspace_presenter.request_open_scope_breadcrumb(node_id))

    @pyqtSlot(result=bool)
    def request_navigate_scope_parent(self) -> bool:
        return bool(self._navigate_scope(self.scene.navigate_scope_parent))

    @pyqtSlot(result=bool)
    def request_navigate_scope_root(self) -> bool:
        return bool(self._navigate_scope(self.scene.navigate_scope_root))

    @pyqtSlot()
    def request_save_project(self) -> None:
        self._save_project()

    @pyqtSlot()
    def request_save_project_as(self) -> None:
        self._save_project_as()

    @pyqtSlot()
    def request_open_project(self) -> None:
        self._open_project()

    @pyqtSlot()
    def request_rename_workspace(self) -> None:
        self._rename_active_workspace()

    @pyqtSlot(str, result=bool)
    def request_rename_workspace_by_id(self, workspace_id: str) -> bool:
        return bool(self.shell_workspace_presenter.request_rename_workspace_by_id(workspace_id))

    @pyqtSlot()
    def request_duplicate_workspace(self) -> None:
        self._duplicate_active_workspace()

    @pyqtSlot()
    def request_close_workspace(self) -> None:
        self._close_active_workspace()

    @pyqtSlot(str, result=bool)
    def request_close_workspace_by_id(self, workspace_id: str) -> bool:
        return bool(self.shell_workspace_presenter.request_close_workspace_by_id(workspace_id))

    @pyqtSlot(str, result=bool)
    def request_close_view(self, view_id: str) -> bool:
        return bool(self.shell_workspace_presenter.request_close_view(view_id))

    @pyqtSlot(str, result=bool)
    def request_rename_view(self, view_id: str) -> bool:
        return bool(self.shell_workspace_presenter.request_rename_view(view_id))

    @pyqtSlot(int, int, result=bool)
    def request_move_workspace_tab(self, from_index: int, to_index: int) -> bool:
        return bool(self.shell_workspace_presenter.request_move_workspace_tab(from_index, to_index))

    @pyqtSlot(int, int, result=bool)
    def request_move_view_tab(self, from_index: int, to_index: int) -> bool:
        return bool(self.shell_workspace_presenter.request_move_view_tab(from_index, to_index))

    @pyqtSlot(result=bool)
    def request_align_selection_left(self) -> bool:
        return bool(self._align_selection_left())

    @pyqtSlot(result=bool)
    def request_align_selection_right(self) -> bool:
        return bool(self._align_selection_right())

    @pyqtSlot(result=bool)
    def request_align_selection_top(self) -> bool:
        return bool(self._align_selection_top())

    @pyqtSlot(result=bool)
    def request_align_selection_bottom(self) -> bool:
        return bool(self._align_selection_bottom())

    @pyqtSlot(result=bool)
    def request_distribute_selection_horizontally(self) -> bool:
        return bool(self._distribute_selection_horizontally())

    @pyqtSlot(result=bool)
    def request_distribute_selection_vertically(self) -> bool:
        return bool(self._distribute_selection_vertically())

    @pyqtSlot(result=bool)
    def request_toggle_snap_to_grid(self) -> bool:
        self.set_snap_to_grid_enabled(not self.search_scope_state.snap_to_grid_enabled)
        return bool(self.search_scope_state.snap_to_grid_enabled)

    @pyqtSlot()
    def request_connect_selected_nodes(self) -> None:
        self._connect_selected_nodes()

    @pyqtSlot(result=bool)
    def request_duplicate_selected_nodes(self) -> bool:
        return bool(self._duplicate_selected_nodes())

    @pyqtSlot(result=bool)
    def request_wrap_selected_nodes_in_comment_backdrop(self) -> bool:
        return bool(self._wrap_selected_nodes_in_comment_backdrop())

    @pyqtSlot(result=bool)
    def request_group_selected_nodes(self) -> bool:
        return bool(self._group_selected_nodes())

    @pyqtSlot(result=bool)
    def request_ungroup_selected_nodes(self) -> bool:
        return bool(self.shell_inspector_presenter.request_ungroup_selected_nodes())

    @pyqtSlot(result=bool)
    def request_copy_selected_nodes(self) -> bool:
        return bool(self._copy_selected_nodes_to_clipboard())

    @pyqtSlot(result=bool)
    def request_cut_selected_nodes(self) -> bool:
        return bool(self._cut_selected_nodes_to_clipboard())

    @pyqtSlot(result=bool)
    def request_paste_selected_nodes(self) -> bool:
        return bool(self._paste_nodes_from_clipboard())

    @pyqtSlot(result=bool)
    def request_undo(self) -> bool:
        return bool(self._undo())

    @pyqtSlot(result=bool)
    def request_redo(self) -> bool:
        return bool(self._redo())

    @pyqtSlot(str, str, str, str, result=bool)
    def request_connect_ports(
        self,
        node_a_id: str,
        port_a: str,
        node_b_id: str,
        port_b: str,
    ) -> bool:
        return bool(self.graph_canvas_presenter.request_connect_ports(node_a_id, port_a, node_b_id, port_b))

    @pyqtSlot(str, result=bool)
    def request_remove_edge(self, edge_id: str) -> bool:
        return bool(self.workspace_library_controller.request_remove_edge(edge_id).payload)

    @pyqtSlot(str, result=bool)
    def request_ungroup_node(self, node_id: str) -> bool:
        if not node_id:
            return False
        scene = self.scene
        if scene is None:
            return False
        scene.select_node(node_id)
        return self.request_ungroup_selected_nodes()

    @pyqtSlot(str, result=bool)
    def request_remove_node(self, node_id: str) -> bool:
        return bool(self.workspace_library_controller.request_remove_node(node_id).payload)

    @pyqtSlot(str, result=str)
    def request_add_selected_subnode_pin(self, direction: str) -> str:
        return self.shell_inspector_presenter.request_add_selected_subnode_pin(direction)

    @pyqtSlot(str, result=bool)
    def request_rename_node(self, node_id: str) -> bool:
        return bool(self.workspace_library_controller.request_rename_node(node_id).payload)

    @pyqtSlot(str, result=bool)
    def request_rename_selected_port(self, key: str) -> bool:
        return bool(self.workspace_library_controller.request_rename_selected_port(key).payload)

    @pyqtSlot(str, result=bool)
    def request_remove_selected_port(self, key: str) -> bool:
        return bool(self.workspace_library_controller.request_remove_selected_port(key).payload)

    @pyqtSlot(str, result=bool)
    def request_edit_passive_node_style(self, node_id: str) -> bool:
        return bool(self.shell_host_presenter.request_edit_passive_node_style(node_id))

    @pyqtSlot(str, result=bool)
    def request_reset_passive_node_style(self, node_id: str) -> bool:
        return bool(self.shell_host_presenter.request_reset_passive_node_style(node_id))

    @pyqtSlot(str, result=bool)
    def request_copy_passive_node_style(self, node_id: str) -> bool:
        return bool(self.shell_host_presenter.request_copy_passive_node_style(node_id))

    @pyqtSlot(str, result=bool)
    def request_paste_passive_node_style(self, node_id: str) -> bool:
        return bool(self.shell_host_presenter.request_paste_passive_node_style(node_id))

    @pyqtSlot(str, result=bool)
    def request_edit_flow_edge_style(self, edge_id: str) -> bool:
        return bool(self.shell_host_presenter.request_edit_flow_edge_style(edge_id))

    @pyqtSlot(str, result=bool)
    def request_edit_flow_edge_label(self, edge_id: str) -> bool:
        return bool(self.shell_host_presenter.request_edit_flow_edge_label(edge_id))

    @pyqtSlot(str, result=bool)
    def request_reset_flow_edge_style(self, edge_id: str) -> bool:
        return bool(self.shell_host_presenter.request_reset_flow_edge_style(edge_id))

    @pyqtSlot(str, result=bool)
    def request_copy_flow_edge_style(self, edge_id: str) -> bool:
        return bool(self.shell_host_presenter.request_copy_flow_edge_style(edge_id))

    @pyqtSlot(str, result=bool)
    def request_paste_flow_edge_style(self, edge_id: str) -> bool:
        return bool(self.shell_host_presenter.request_paste_flow_edge_style(edge_id))

    @pyqtSlot("QVariantList", result=bool)
    def request_delete_selected_graph_items(self, edge_ids: list[Any]) -> bool:
        return bool(self.workspace_library_controller.request_delete_selected_graph_items(edge_ids).payload)

    @pyqtSlot(str, "QVariant")
    def set_selected_node_property(self, key: str, value: Any) -> None:
        self.shell_inspector_presenter.set_selected_node_property(key, value)

    @pyqtSlot(str, "QVariant", result="QVariantMap")
    def describe_pdf_preview(self, source: str, page_number: Any) -> dict[str, Any]:
        return describe_pdf_preview(source, page_number)

    @pyqtSlot(str, str, result=str)
    def browse_selected_node_property_path(self, key: str, current_path: str) -> str:
        return self.shell_inspector_presenter.browse_selected_node_property_path(key, current_path)

    @pyqtSlot(str, str, str, result=str)
    def browse_node_property_path(self, node_id: str, key: str, current_path: str) -> str:
        return self.graph_canvas_presenter.browse_node_property_path(node_id, key, current_path)

    def _browse_property_path_dialog(self, property_label: str, current_path: str) -> str:
        return self.shell_host_presenter.browse_property_path_dialog(property_label, current_path)

    @pyqtSlot(str, bool)
    def set_selected_port_exposed(self, key: str, exposed: bool) -> None:
        self.shell_inspector_presenter.set_selected_port_exposed(key, exposed)

    @pyqtSlot(str, str, result=bool)
    def set_selected_port_label(self, key: str, label: str) -> bool:
        return bool(self.shell_inspector_presenter.set_selected_port_label(key, label))

    @pyqtSlot(bool)
    def set_selected_node_collapsed(self, collapsed: bool) -> None:
        self.shell_inspector_presenter.set_selected_node_collapsed(collapsed)

    # Explicit project session controller delegation
    def _ensure_project_metadata_defaults(self):
        return self.project_session_controller.ensure_project_metadata_defaults()

    def _workflow_settings_payload(self):
        return self.project_session_controller.workflow_settings_payload()

    def _persist_script_editor_state(self):
        return self.project_session_controller.persist_script_editor_state()

    def _restore_script_editor_state(self):
        return self.project_session_controller.restore_script_editor_state()

    def _save_project(self):
        return self.project_session_controller.save_project()

    def _save_project_as(self):
        return self.project_session_controller.save_project_as()

    def _new_project(self):
        return self.project_session_controller.new_project()

    def _open_project(self):
        return self.project_session_controller.open_project()

    def _open_project_path(self, path):
        return self.project_session_controller.open_project_path(path)

    def _clear_recent_projects(self):
        return self.project_session_controller.clear_recent_projects()

    def _restore_session(self):
        return self.project_session_controller.restore_session()

    def _discard_autosave_snapshot(self):
        return self.project_session_controller.discard_autosave_snapshot()

    def _recover_autosave_if_newer(self):
        return self.project_session_controller.recover_autosave_if_newer()

    def _process_deferred_autosave_recovery(self):
        return self.project_session_controller.process_deferred_autosave_recovery()

    def _autosave_tick(self):
        return self.project_session_controller.autosave_tick()

    def _persist_session(self, project_doc=None):
        return self.project_session_controller.persist_session(project_doc)

    # Explicit workspace library controller delegation
    def _switch_workspace_by_offset(self, offset):
        return self.workspace_library_controller.switch_workspace_by_offset(offset)

    def _refresh_workspace_tabs(self):
        return self.workspace_library_controller.refresh_workspace_tabs()

    def _switch_workspace(self, workspace_id):
        return self.workspace_library_controller.switch_workspace(workspace_id)

    def _save_active_view_state(self):
        return self.workspace_library_controller.save_active_view_state()

    def _restore_active_view_state(self):
        return self.workspace_library_controller.restore_active_view_state()

    def _visible_scene_rect(self):
        return self.workspace_library_controller.visible_scene_rect()

    def _current_workspace_scene_bounds(self):
        return self.workspace_library_controller.current_workspace_scene_bounds()

    def _selection_bounds(self):
        return self.workspace_library_controller.selection_bounds()

    def _frame_all(self):
        return self.workspace_library_controller.frame_all()

    def _frame_selection(self):
        return self.workspace_library_controller.frame_selection()

    def _frame_node(self, node_id):
        return self.workspace_library_controller.frame_node(node_id)

    def _center_on_node(self, node_id):
        return self.workspace_library_controller.center_on_node(node_id)

    def _center_on_selection(self):
        return self.workspace_library_controller.center_on_selection()

    def _search_graph_nodes(self, query, limit=_GRAPH_SEARCH_LIMIT, enabled_scopes=None):
        return self.workspace_library_controller.search_graph_nodes(
            query,
            limit,
            enabled_scopes=enabled_scopes,
        )

    def _jump_to_graph_node(self, workspace_id, node_id):
        return self.workspace_library_controller.jump_to_graph_node(workspace_id, node_id)

    def _create_view(self):
        return self.workspace_library_controller.create_view()

    def _switch_view(self, view_id):
        return self.workspace_library_controller.switch_view(view_id)

    def _rename_view(self, view_id):
        return self.workspace_library_controller.rename_view(view_id)

    def _create_workspace(self):
        return self.workspace_library_controller.create_workspace()

    def _rename_active_workspace(self):
        return self.workspace_library_controller.rename_active_workspace()

    def _duplicate_active_workspace(self):
        return self.workspace_library_controller.duplicate_active_workspace()

    def _close_active_workspace(self):
        return self.workspace_library_controller.close_active_workspace()

    def _on_workspace_tab_changed(self, index):
        return self.workspace_library_controller.on_workspace_tab_changed(index)

    def _on_workspace_tab_close(self, index):
        return self.workspace_library_controller.on_workspace_tab_close(index)

    def _add_node_from_library(self, type_id):
        return self.workspace_library_controller.add_node_from_library(type_id)

    def _insert_library_node(self, type_id, x, y):
        return self.workspace_library_controller.insert_library_node(type_id, x, y)

    def _active_workspace(self):
        return self.workspace_library_controller.active_workspace()

    def _prompt_connection_candidate(self, *, title, label, candidates):
        return self.workspace_library_controller.prompt_connection_candidate(
            title=title,
            label=label,
            candidates=candidates,
        )

    def _auto_connect_dropped_node_to_port(self, new_node_id, target_node_id, target_port_key):
        return self.workspace_library_controller.auto_connect_dropped_node_to_port(
            new_node_id,
            target_node_id,
            target_port_key,
        )

    def _auto_connect_dropped_node_to_edge(self, new_node_id, target_edge_id):
        return self.workspace_library_controller.auto_connect_dropped_node_to_edge(new_node_id, target_edge_id)

    def _on_scene_node_selected(self, node_id):
        return self.workspace_library_controller.on_scene_node_selected(node_id)

    def _on_node_property_changed(self, node_id, key, value):
        return self.workspace_library_controller.on_node_property_changed(node_id, key, value)

    def _on_port_exposed_changed(self, node_id, key, exposed):
        return self.workspace_library_controller.on_port_exposed_changed(node_id, key, exposed)

    def _on_node_collapse_changed(self, node_id, collapsed):
        return self.workspace_library_controller.on_node_collapse_changed(node_id, collapsed)

    def _connect_selected_nodes(self):
        return self.workspace_library_controller.connect_selected_nodes()

    def _duplicate_selected_nodes(self):
        return self.workspace_library_controller.duplicate_selected_nodes()

    def _wrap_selected_nodes_in_comment_backdrop(self):
        return self.workspace_graph_edit_controller.wrap_selected_nodes_in_comment_backdrop()

    def _group_selected_nodes(self):
        return self.workspace_library_controller.group_selected_nodes()

    def _ungroup_selected_nodes(self):
        return self.workspace_library_controller.ungroup_selected_nodes()

    def _align_selection_left(self):
        return self.workspace_library_controller.align_selection_left()

    def _align_selection_right(self):
        return self.workspace_library_controller.align_selection_right()

    def _align_selection_top(self):
        return self.workspace_library_controller.align_selection_top()

    def _align_selection_bottom(self):
        return self.workspace_library_controller.align_selection_bottom()

    def _distribute_selection_horizontally(self):
        return self.workspace_library_controller.distribute_selection_horizontally()

    def _distribute_selection_vertically(self):
        return self.workspace_library_controller.distribute_selection_vertically()

    def _copy_selected_nodes_to_clipboard(self):
        return self.workspace_library_controller.copy_selected_nodes_to_clipboard()

    def _cut_selected_nodes_to_clipboard(self):
        return self.workspace_library_controller.cut_selected_nodes_to_clipboard()

    def _paste_nodes_from_clipboard(self):
        return self.workspace_library_controller.paste_nodes_from_clipboard()

    def _undo(self):
        return self.workspace_library_controller.undo()

    def _redo(self):
        return self.workspace_library_controller.redo()

    def _selected_node_context(self):
        return self.workspace_library_controller.selected_node_context()

    def _active_workspace_data(self):
        return self.shell_host_presenter._active_workspace_data()

    def _passive_node_context(self, node_id: str):
        return self.shell_host_presenter._passive_node_context(node_id)

    def _flow_edge_context(self, edge_id: str):
        return self.shell_host_presenter._flow_edge_context(edge_id)

    def _project_passive_style_presets(self) -> dict[str, list[dict[str, Any]]]:
        return self.shell_host_presenter._project_passive_style_presets()

    def _set_project_passive_style_presets(
        self,
        *,
        node_presets: Any = _UNSET,
        edge_presets: Any = _UNSET,
    ) -> None:
        self.shell_host_presenter._set_project_passive_style_presets(
            node_presets=node_presets,
            edge_presets=edge_presets,
        )

    def edit_passive_node_style(self, node_id: str) -> dict[str, Any] | None:
        return self.shell_host_presenter.edit_passive_node_style(node_id)

    def edit_flow_edge_style(self, edge_id: str) -> dict[str, Any] | None:
        return self.shell_host_presenter.edit_flow_edge_style(edge_id)

    def _write_style_clipboard(self, *, kind: str, style: dict[str, Any]) -> None:
        self.shell_host_presenter._write_style_clipboard(kind=kind, style=style)

    def _read_style_clipboard(self, *, kind: str) -> dict[str, Any] | None:
        return self.shell_host_presenter._read_style_clipboard(kind=kind)

    def _normalize_style_clipboard_payload(self, payload: Any, *, kind: str) -> dict[str, Any] | None:
        return self.shell_host_presenter._normalize_style_clipboard_payload(payload, kind=kind)

    def _focus_failed_node(self, workspace_id, node_id, error):
        return self.workspace_library_controller.focus_failed_node(workspace_id, node_id, error)

    def _reveal_parent_chain(self, workspace_id, node_id):
        return self.workspace_library_controller.reveal_parent_chain(workspace_id, node_id)

    def _import_custom_workflow(self):
        return self.workspace_library_controller.import_custom_workflow()

    def _export_custom_workflow(self):
        return self.workspace_library_controller.export_custom_workflow()

    def _import_node_package(self):
        return self.workspace_library_controller.import_node_package()

    def _export_node_package(self):
        return self.workspace_library_controller.export_node_package()

    # Explicit run controller delegation
    def _run_workflow(self):
        return self.run_controller.run_workflow()

    def _toggle_pause_resume(self):
        return self.run_controller.toggle_pause_resume()

    def _pause_workflow(self):
        return self.run_controller.pause_workflow()

    def _resume_workflow(self):
        return self.run_controller.resume_workflow()

    def _stop_workflow(self):
        return self.run_controller.stop_workflow()

    def _handle_execution_event(self, event):
        return self.run_controller.handle_execution_event(event)

    def _clear_active_run(self):
        return self.run_controller.clear_active_run()

    def _set_run_ui_state(self, state, details, running, queued, done, failed, *, clear_run=False):
        return self.run_controller.set_run_ui_state(
            state,
            details,
            running,
            queued,
            done,
            failed,
            clear_run=clear_run,
        )

    def _update_run_actions(self):
        return self.run_controller.update_run_actions()

    @pyqtSlot()
    @pyqtSlot(bool)
    def show_workflow_settings_dialog(self, _checked: bool = False) -> None:
        self.shell_workspace_presenter.show_workflow_settings_dialog(_checked)

    @pyqtSlot()
    @pyqtSlot(bool)
    def show_graphics_settings_dialog(self, _checked: bool = False) -> None:
        self.shell_host_presenter.show_graphics_settings_dialog(_checked)

    def edit_graph_theme_settings(
        self,
        graph_theme_settings: Any,
        *,
        enable_live_apply: bool = False,
    ) -> dict[str, Any] | None:
        return self.shell_host_presenter.edit_graph_theme_settings(
            graph_theme_settings,
            enable_live_apply=enable_live_apply,
        )

    @pyqtSlot()
    @pyqtSlot(bool)
    def show_graph_theme_editor_dialog(self, _checked: bool = False) -> None:
        self.shell_host_presenter.show_graph_theme_editor_dialog(_checked)

    @pyqtSlot()
    @pyqtSlot(bool)
    def set_script_editor_panel_visible(self, checked: bool | None = None) -> None:
        self.shell_workspace_presenter.set_script_editor_panel_visible(checked)

    def _prompt_recover_autosave(self):
        return self.project_session_controller.prompt_recover_autosave()

    @pyqtSlot()
    def _record_render_frame(self) -> None:
        self._frame_rate_sampler.record_frame()

    def _update_metrics(self) -> None:
        self.shell_host_presenter.update_metrics()

    def _open_logs(self) -> None:
        return

    def showEvent(self, event) -> None:  # noqa: ANN001
        super().showEvent(event)
        if self._autosave_recovery_deferred:
            QTimer.singleShot(0, self._process_deferred_autosave_recovery)

    def closeEvent(self, event) -> None:  # noqa: ANN001
        self.autosave_timer.stop()
        try:
            self.project_session_controller.close_session()
        finally:
            self.execution_client.shutdown()
            super().closeEvent(event)

    def update_engine_status(
        self,
        state: Literal["ready", "running", "paused", "error"],
        details: str = "",
    ) -> None:
        self.shell_host_presenter.update_engine_status(state, details)

    def update_job_counters(self, running: int, queued: int, done: int, failed: int) -> None:
        self.shell_host_presenter.update_job_counters(running, queued, done, failed)

    def update_system_metrics(
        self,
        cpu_percent: float,
        ram_used_gb: float,
        ram_total_gb: float,
        fps: float | None = None,
    ) -> None:
        self.shell_host_presenter.update_system_metrics(
            cpu_percent,
            ram_used_gb,
            ram_total_gb,
            fps=fps,
        )

    def update_notification_counters(self, warnings: int, errors: int) -> None:
        self.shell_host_presenter.update_notification_counters(warnings, errors)
