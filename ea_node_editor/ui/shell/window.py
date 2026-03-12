from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Literal

from PyQt6.QtCore import QTimer, Qt, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtQuick import QQuickWindow, QSGRendererInterface
from PyQt6.QtQuickWidgets import QQuickWidget
from PyQt6.QtWidgets import QMainWindow, QMessageBox

from ea_node_editor.graph.effective_ports import find_port
from ea_node_editor.execution.client import ProcessExecutionClient
from ea_node_editor.graph.model import GraphModel, ProjectData
from ea_node_editor.nodes.builtins.subnode import (
    SUBNODE_INPUT_TYPE_ID,
    SUBNODE_OUTPUT_TYPE_ID,
    SUBNODE_PIN_DATA_TYPE_PROPERTY,
    SUBNODE_TYPE_ID,
)
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.persistence.session_store import SessionAutosaveStore
from ea_node_editor.settings import (
    AUTOSAVE_INTERVAL_MS,
    autosave_project_path,
    DEFAULT_GRAPHICS_SETTINGS,
    recent_session_path,
)
from ea_node_editor.telemetry.system_metrics import read_system_metrics
from ea_node_editor.ui.graph_interactions import GraphInteractions
from ea_node_editor.ui.icon_registry import UI_ICON_PROVIDER_ID, UiIconImageProvider, UiIconRegistryBridge
from ea_node_editor.ui.shell.controllers import (
    AppPreferencesController,
    ProjectSessionController,
    RunController,
    WorkspaceLibraryController,
)
from ea_node_editor.ui.shell.runtime_history import RuntimeGraphHistory
from ea_node_editor.ui.shell.state import ShellState
from ea_node_editor.ui.shell.window_actions import build_window_menu_bar, create_window_actions
from ea_node_editor.ui.shell.window_library_inspector import (
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
from ea_node_editor.ui.shell import window_search_scope_state
from ea_node_editor.ui_qml.console_model import ConsoleModel
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from ea_node_editor.ui_qml.script_editor_model import ScriptEditorModel
from ea_node_editor.ui_qml.status_model import StatusItemModel
from ea_node_editor.ui_qml.syntax_bridge import QmlScriptSyntaxBridge
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

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("EA Node Editor")
        self.resize(1600, 900)

        self.state = ShellState()
        self.registry: NodeRegistry = build_default_registry()
        self.serializer = JsonProjectSerializer(self.registry)
        self._session_store = SessionAutosaveStore(
            serializer=self.serializer,
            session_path_provider=recent_session_path,
            autosave_path_provider=autosave_project_path,
        )
        self.model = GraphModel(ProjectData(project_id="proj_local", name="untitled"))
        self.workspace_manager = WorkspaceManager(self.model)
        self.runtime_history = RuntimeGraphHistory()

        self.scene = GraphSceneBridge(self)
        self.scene.bind_runtime_history(self.runtime_history)
        self.view = ViewportBridge(self)
        self._graph_interactions = GraphInteractions(
            scene=self.scene,
            registry=self.registry,
            history=self.runtime_history,
        )
        self.console_panel = ConsoleModel(self)
        self.script_editor = ScriptEditorModel(self)
        self.script_highlighter = QmlScriptSyntaxBridge(self)
        self.workspace_tabs = WorkspaceTabsModel(self)
        self.ui_icons = UiIconRegistryBridge(self)
        self._ui_icon_image_provider = UiIconImageProvider()
        self.status_engine = StatusItemModel("E", "Ready", self)
        self.status_jobs = StatusItemModel("J", "R:0 Q:0 D:0 F:0", self)
        self.status_metrics = StatusItemModel("M", "CPU:0% RAM:0/0 GB", self)
        self.status_notifications = StatusItemModel("N", "W:0 E:0", self)
        self._graph_search_open = False
        self._graph_search_query = ""
        self._graph_search_results: list[dict[str, Any]] = []
        self._graph_search_highlight_index = -1
        self._connection_quick_insert_open = False
        self._connection_quick_insert_query = ""
        self._connection_quick_insert_results: list[dict[str, Any]] = []
        self._connection_quick_insert_highlight_index = -1
        self._connection_quick_insert_context: dict[str, Any] | None = None
        self._graph_hint_message = ""
        self._graphics_show_grid = bool(DEFAULT_GRAPHICS_SETTINGS["canvas"]["show_grid"])
        self._graphics_show_minimap = bool(DEFAULT_GRAPHICS_SETTINGS["canvas"]["show_minimap"])
        self._graphics_minimap_expanded = bool(DEFAULT_GRAPHICS_SETTINGS["canvas"]["minimap_expanded"])
        self._snap_to_grid_enabled = bool(DEFAULT_GRAPHICS_SETTINGS["interaction"]["snap_to_grid"])
        self._active_theme_id = str(DEFAULT_GRAPHICS_SETTINGS["theme"]["theme_id"])
        self._runtime_scope_camera: dict[tuple[str, str, tuple[str, ...]], tuple[float, float, float]] = {}

        self.workspace_library_controller = WorkspaceLibraryController(self)
        self.project_session_controller = ProjectSessionController(self)
        self.run_controller = RunController(self)
        self.app_preferences_controller = AppPreferencesController()

        self.execution_client = ProcessExecutionClient()
        self.execution_client.subscribe(self.execution_event.emit)
        self.execution_event.connect(self._handle_execution_event, Qt.ConnectionType.QueuedConnection)

        self._create_actions()
        self._build_menu_bar()
        self.app_preferences_controller.load_into_host(self)
        self._wire_signals()
        self._build_qml_shell()
        self._restore_session()
        self._ensure_project_metadata_defaults()
        self._refresh_workspace_tabs()
        self._switch_workspace(self.workspace_manager.active_workspace_id())
        self._restore_script_editor_state()

        self.metrics_timer = QTimer(self)
        self.metrics_timer.setInterval(1000)
        self.metrics_timer.timeout.connect(self._update_metrics)
        self.metrics_timer.start()

        self.graph_hint_timer = QTimer(self)
        self.graph_hint_timer.setSingleShot(True)
        self.graph_hint_timer.timeout.connect(self.clear_graph_hint)

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(AUTOSAVE_INTERVAL_MS)
        self.autosave_timer.timeout.connect(self._autosave_tick)
        self.autosave_timer.start()

        self._set_run_ui_state("ready", "Idle", 0, 0, 0, 0, clear_run=True)
        self._update_metrics()

    @property
    def project_path(self) -> str:
        return self.state.project_path

    @project_path.setter
    def project_path(self, value: str) -> None:
        self.state.project_path = str(value)

    @property
    def recent_project_paths(self) -> list[str]:
        return list(self.state.recent_project_paths)

    @recent_project_paths.setter
    def recent_project_paths(self, value: list[str]) -> None:
        self.state.recent_project_paths = [str(path) for path in value]

    @property
    def _library_query(self) -> str:
        return self.state.library_query

    @_library_query.setter
    def _library_query(self, value: str) -> None:
        self.state.library_query = str(value)

    @property
    def _library_category(self) -> str:
        return self.state.library_category

    @_library_category.setter
    def _library_category(self, value: str) -> None:
        self.state.library_category = str(value)

    @property
    def _library_data_type(self) -> str:
        return self.state.library_data_type

    @_library_data_type.setter
    def _library_data_type(self, value: str) -> None:
        self.state.library_data_type = str(value)

    @property
    def _library_direction(self) -> str:
        return self.state.library_direction

    @_library_direction.setter
    def _library_direction(self, value: str) -> None:
        self.state.library_direction = str(value)

    @property
    def _active_run_id(self) -> str:
        return self.state.active_run_id

    @_active_run_id.setter
    def _active_run_id(self, value: str) -> None:
        self.state.active_run_id = str(value)

    @property
    def _active_run_workspace_id(self) -> str:
        return self.state.active_run_workspace_id

    @_active_run_workspace_id.setter
    def _active_run_workspace_id(self, value: str) -> None:
        self.state.active_run_workspace_id = str(value)

    @property
    def _engine_state_value(self) -> Literal["ready", "running", "paused", "error"]:
        return self.state.engine_state_value

    @_engine_state_value.setter
    def _engine_state_value(self, value: Literal["ready", "running", "paused", "error"] | str) -> None:
        normalized = str(value)
        if normalized not in {"ready", "running", "paused", "error"}:
            normalized = "ready"
        self.state.engine_state_value = normalized  # type: ignore[assignment]

    @property
    def _last_manual_save_ts(self) -> float:
        return self.state.last_manual_save_ts

    @_last_manual_save_ts.setter
    def _last_manual_save_ts(self, value: float) -> None:
        self.state.last_manual_save_ts = float(value)

    @property
    def _last_autosave_fingerprint(self) -> str:
        return self.state.last_autosave_fingerprint

    @_last_autosave_fingerprint.setter
    def _last_autosave_fingerprint(self, value: str) -> None:
        self.state.last_autosave_fingerprint = str(value)

    @property
    def _autosave_recovery_deferred(self) -> bool:
        return self.state.autosave_recovery_deferred

    @_autosave_recovery_deferred.setter
    def _autosave_recovery_deferred(self, value: bool) -> None:
        self.state.autosave_recovery_deferred = bool(value)

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

    def _build_qml_shell(self) -> None:
        self.quick_widget = QQuickWidget(self)
        self.quick_widget.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)

        self.quick_widget.engine().addImageProvider(UI_ICON_PROVIDER_ID, self._ui_icon_image_provider)
        context = self.quick_widget.rootContext()
        context.setContextProperty("mainWindow", self)
        context.setContextProperty("sceneBridge", self.scene)
        context.setContextProperty("viewBridge", self.view)
        context.setContextProperty("consoleBridge", self.console_panel)
        context.setContextProperty("scriptEditorBridge", self.script_editor)
        context.setContextProperty("scriptHighlighterBridge", self.script_highlighter)
        context.setContextProperty("workspaceTabsBridge", self.workspace_tabs)
        context.setContextProperty("uiIcons", self.ui_icons)
        context.setContextProperty("statusEngine", self.status_engine)
        context.setContextProperty("statusJobs", self.status_jobs)
        context.setContextProperty("statusMetrics", self.status_metrics)
        context.setContextProperty("statusNotifications", self.status_notifications)

        qml_path = Path(__file__).resolve().parents[2] / "ui_qml" / "MainShell.qml"
        self.quick_widget.setSource(QUrl.fromLocalFile(str(qml_path)))
        if self.quick_widget.status() == QQuickWidget.Status.Error:
            formatted_errors = "\n".join(error.toString() for error in self.quick_widget.errors()).strip()
            message = formatted_errors or "Unknown QML load error."
            self.console_panel.append_log("error", f"Failed to load MainShell.qml.\n{message}")
            QMessageBox.critical(self, "UI Load Error", f"Could not load the main UI.\n\n{message}")
        self.setCentralWidget(self.quick_widget)

    @pyqtProperty(str, notify=project_meta_changed)
    def project_display_name(self) -> str:
        filename = Path(self.project_path).name if self.project_path else "untitled.sfe"
        return f"EA Node Editor - {filename}"

    def _registry_library_items(self) -> list[dict[str, Any]]:
        return build_registry_library_items(registry_specs=self.registry.all_specs())

    def _combined_library_items(self) -> list[dict[str, Any]]:
        return build_combined_library_items(
            registry_items=self._registry_library_items(),
            custom_workflow_items=self.workspace_library_controller.custom_workflow_library_items(),
        )

    @staticmethod
    def _library_item_matches_filters(
        item: dict[str, Any],
        *,
        query: str,
        category: str,
        data_type: str,
        direction: str,
    ) -> bool:
        return library_item_matches_filters(
            item,
            query=query,
            category=category,
            data_type=data_type,
            direction=direction,
        )

    @pyqtProperty("QVariantList", notify=node_library_changed)
    def filtered_node_library_items(self) -> list[dict[str, Any]]:
        return build_filtered_library_items(
            combined_items=self._combined_library_items(),
            query=self._library_query,
            category=self._library_category,
            data_type=self._library_data_type,
            direction=self._library_direction,
        )

    @pyqtProperty("QVariantList", notify=node_library_changed)
    def grouped_node_library_items(self) -> list[dict[str, Any]]:
        return build_grouped_library_items(filtered_items=self.filtered_node_library_items)

    @pyqtProperty("QVariantList", notify=node_library_changed)
    def library_category_options(self) -> list[dict[str, str]]:
        return build_library_category_options(
            combined_items=self._combined_library_items(),
            registry_categories=self.registry.categories(),
        )

    @pyqtProperty("QVariantList", notify=node_library_changed)
    def library_direction_options(self) -> list[dict[str, str]]:
        return build_library_direction_options()

    @pyqtProperty("QVariantList", notify=node_library_changed)
    def library_data_type_options(self) -> list[dict[str, str]]:
        return build_library_data_type_options(
            registry_specs=self.registry.all_specs(),
            custom_workflow_items=self.workspace_library_controller.custom_workflow_library_items(),
        )

    @pyqtProperty("QVariantList", notify=workspace_state_changed)
    def pin_data_type_options(self) -> list[str]:
        return build_pin_data_type_options(
            registry_specs=self.registry.all_specs(),
            workspaces=self.model.project.workspaces.values(),
            subnode_pin_type_ids=self._SUBNODE_PIN_TYPE_IDS,
            subnode_pin_data_type_property=SUBNODE_PIN_DATA_TYPE_PROPERTY,
        )

    @pyqtProperty(bool, notify=graph_search_changed)
    def graph_search_open(self) -> bool:
        return bool(self._graph_search_open)

    @pyqtProperty(str, notify=graph_search_changed)
    def graph_search_query(self) -> str:
        return self._graph_search_query

    @pyqtProperty("QVariantList", notify=graph_search_changed)
    def graph_search_results(self) -> list[dict[str, Any]]:
        return list(self._graph_search_results)

    @pyqtProperty(int, notify=graph_search_changed)
    def graph_search_highlight_index(self) -> int:
        return int(self._graph_search_highlight_index)

    @pyqtProperty(bool, notify=connection_quick_insert_changed)
    def connection_quick_insert_open(self) -> bool:
        return bool(self._connection_quick_insert_open)

    @pyqtProperty(str, notify=connection_quick_insert_changed)
    def connection_quick_insert_query(self) -> str:
        return str(self._connection_quick_insert_query)

    @pyqtProperty("QVariantList", notify=connection_quick_insert_changed)
    def connection_quick_insert_results(self) -> list[dict[str, Any]]:
        return list(self._connection_quick_insert_results)

    @pyqtProperty(int, notify=connection_quick_insert_changed)
    def connection_quick_insert_highlight_index(self) -> int:
        return int(self._connection_quick_insert_highlight_index)

    @pyqtProperty(float, notify=connection_quick_insert_changed)
    def connection_quick_insert_overlay_x(self) -> float:
        context = self._connection_quick_insert_context or {}
        return float(context.get("overlay_x", 0.0))

    @pyqtProperty(float, notify=connection_quick_insert_changed)
    def connection_quick_insert_overlay_y(self) -> float:
        context = self._connection_quick_insert_context or {}
        return float(context.get("overlay_y", 0.0))

    @pyqtProperty(str, notify=connection_quick_insert_changed)
    def connection_quick_insert_source_summary(self) -> str:
        context = self._connection_quick_insert_context or {}
        node_title = str(context.get("node_title", "")).strip()
        port_label = str(context.get("port_label", "")).strip()
        data_type = str(context.get("data_type", "")).strip()
        if not node_title and not port_label:
            return ""
        summary = f"{node_title}.{port_label}" if node_title and port_label else (node_title or port_label)
        if data_type:
            summary += f" [{data_type}]"
        return summary

    @pyqtProperty(str, notify=graph_hint_changed)
    def graph_hint_message(self) -> str:
        return str(self._graph_hint_message)

    @pyqtProperty(bool, notify=graph_hint_changed)
    def graph_hint_visible(self) -> bool:
        return bool(self._graph_hint_message.strip())

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_show_grid(self) -> bool:
        return bool(self._graphics_show_grid)

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_show_minimap(self) -> bool:
        return bool(self._graphics_show_minimap)

    @pyqtProperty(bool, notify=graphics_preferences_changed)
    def graphics_minimap_expanded(self) -> bool:
        return bool(self._graphics_minimap_expanded)

    @pyqtProperty(str, notify=graphics_preferences_changed)
    def active_theme_id(self) -> str:
        return str(self._active_theme_id)

    @pyqtProperty(bool, notify=snap_to_grid_changed)
    def snap_to_grid_enabled(self) -> bool:
        return bool(self._snap_to_grid_enabled)

    @pyqtProperty(float, constant=True)
    def snap_grid_size(self) -> float:
        return float(self._SNAP_GRID_SIZE)

    @pyqtProperty(str, notify=workspace_state_changed)
    def active_workspace_id(self) -> str:
        try:
            return self.workspace_manager.active_workspace_id()
        except Exception:  # noqa: BLE001
            return ""

    @pyqtProperty(str, notify=workspace_state_changed)
    def active_workspace_name(self) -> str:
        workspace = self.model.project.workspaces.get(self.active_workspace_id)
        return workspace.name if workspace is not None else ""

    @pyqtProperty(str, notify=workspace_state_changed)
    def active_view_name(self) -> str:
        workspace = self.model.project.workspaces.get(self.active_workspace_id)
        if workspace is None:
            return ""
        workspace.ensure_default_view()
        active_view = workspace.views.get(workspace.active_view_id)
        if active_view is None:
            return ""
        return active_view.name

    @pyqtProperty("QVariantList", notify=workspace_state_changed)
    def active_view_items(self) -> list[dict[str, Any]]:
        workspace = self.model.project.workspaces.get(self.active_workspace_id)
        if workspace is None:
            return []
        workspace.ensure_default_view()
        items: list[dict[str, Any]] = []
        for view in workspace.views.values():
            items.append(
                {
                    "view_id": view.view_id,
                    "label": view.name,
                    "active": view.view_id == workspace.active_view_id,
                }
            )
        return items

    @pyqtProperty("QVariantList", notify=workspace_state_changed)
    def active_scope_breadcrumb_items(self) -> list[dict[str, str]]:
        return list(self.scene.scope_breadcrumb_model)

    def _selected_node_header_data(self) -> dict[str, Any]:
        selected = self._selected_node_context()
        if selected is None:
            return {}
        node, spec = selected
        workspace = self.model.project.workspaces.get(self.active_workspace_id)
        workflow_nodes = workspace.nodes if workspace is not None else {}
        return build_selected_node_header_data(
            node=node,
            spec=spec,
            workflow_nodes=workflow_nodes,
        )

    @pyqtProperty(str, notify=selected_node_changed)
    def selected_node_title(self) -> str:
        return str(self._selected_node_header_data().get("title", ""))

    @pyqtProperty(str, notify=selected_node_changed)
    def selected_node_subtitle(self) -> str:
        return str(self._selected_node_header_data().get("subtitle", ""))

    @pyqtProperty("QVariantList", notify=selected_node_changed)
    def selected_node_header_items(self) -> list[dict[str, str]]:
        header_data = self._selected_node_header_data()
        items = header_data.get("metadata_items", [])
        return list(items) if isinstance(items, list) else []

    @pyqtProperty(str, notify=selected_node_changed)
    def selected_node_summary(self) -> str:
        header_data = self._selected_node_header_data()
        if not header_data:
            return "No node selected"
        lines = [str(header_data.get("title", "")).strip()]
        for item in self.selected_node_header_items:
            label = str(item.get("label", "")).strip()
            value = str(item.get("value", "")).strip()
            if label and value:
                lines.append(f"{label}: {value}")
        return "\n".join(line for line in lines if line)

    @pyqtProperty(bool, notify=selected_node_changed)
    def has_selected_node(self) -> bool:
        return self._selected_node_context() is not None

    @pyqtProperty(bool, notify=selected_node_changed)
    def selected_node_collapsible(self) -> bool:
        selected = self._selected_node_context()
        if selected is None:
            return False
        _node, spec = selected
        return bool(spec.collapsible)

    @pyqtProperty(bool, notify=selected_node_changed)
    def selected_node_collapsed(self) -> bool:
        selected = self._selected_node_context()
        if selected is None:
            return False
        node, _spec = selected
        return bool(node.collapsed)

    @pyqtProperty(bool, notify=selected_node_changed)
    def selected_node_is_subnode_pin(self) -> bool:
        selected = self._selected_node_context()
        if selected is None:
            return False
        node, _spec = selected
        return node.type_id in self._SUBNODE_PIN_TYPE_IDS

    @pyqtProperty(bool, notify=selected_node_changed)
    def selected_node_is_subnode_shell(self) -> bool:
        selected = self._selected_node_context()
        if selected is None:
            return False
        node, _spec = selected
        return node.type_id == SUBNODE_TYPE_ID

    @pyqtProperty(bool, notify=workspace_state_changed)
    def can_publish_custom_workflow_from_scope(self) -> bool:
        return bool(self.scene.active_scope_path)

    @pyqtProperty("QVariantList", notify=selected_node_changed)
    def selected_node_property_items(self) -> list[dict[str, Any]]:
        selected = self._selected_node_context()
        if selected is None:
            return []
        node, spec = selected
        return build_selected_node_property_items(
            node=node,
            spec=spec,
            subnode_pin_type_ids=self._SUBNODE_PIN_TYPE_IDS,
        )

    @pyqtProperty("QVariantList", notify=selected_node_changed)
    def selected_node_port_items(self) -> list[dict[str, Any]]:
        selected = self._selected_node_context()
        if selected is None:
            return []
        if self.selected_node_is_subnode_pin:
            return []
        node, spec = selected
        workspace = self.model.project.workspaces.get(self.active_workspace_id)
        if workspace is None:
            return []
        return build_selected_node_port_items(
            node=node,
            spec=spec,
            workspace_nodes=workspace.nodes,
        )

    def _set_graph_search_state(
        self,
        *,
        open_: bool | None = None,
        query: str | None = None,
        results: list[dict[str, Any]] | None = None,
        highlight_index: int | None = None,
    ) -> None:
        window_search_scope_state.set_graph_search_state(
            self,
            open_=open_,
            query=query,
            results=results,
            highlight_index=highlight_index,
        )

    def _refresh_graph_search_results(self, query: str) -> None:
        window_search_scope_state.refresh_graph_search_results(self, query)

    def _set_connection_quick_insert_state(
        self,
        *,
        open_: bool | None = None,
        query: str | None = None,
        results: list[dict[str, Any]] | None = None,
        highlight_index: int | None = None,
        context: dict[str, Any] | None | object = _UNSET,
    ) -> None:
        changed = False
        if open_ is not None:
            normalized_open = bool(open_)
            if normalized_open != self._connection_quick_insert_open:
                self._connection_quick_insert_open = normalized_open
                changed = True
        if query is not None:
            normalized_query = str(query)
            if normalized_query != self._connection_quick_insert_query:
                self._connection_quick_insert_query = normalized_query
                changed = True
        if results is not None:
            if results != self._connection_quick_insert_results:
                self._connection_quick_insert_results = list(results)
                changed = True
        if highlight_index is not None:
            normalized_index = int(highlight_index)
            if normalized_index != self._connection_quick_insert_highlight_index:
                self._connection_quick_insert_highlight_index = normalized_index
                changed = True
        if context is not _UNSET:
            normalized_context = dict(context) if isinstance(context, dict) else None
            if normalized_context != self._connection_quick_insert_context:
                self._connection_quick_insert_context = normalized_context
                changed = True
        if changed:
            self.connection_quick_insert_changed.emit()

    def _connection_quick_insert_context_for_port(
        self,
        node_id: str,
        port_key: str,
    ) -> dict[str, Any] | None:
        workspace = self.model.project.workspaces.get(self.active_workspace_id)
        if workspace is None:
            return None
        normalized_node_id = str(node_id).strip()
        normalized_port_key = str(port_key).strip()
        if not normalized_node_id or not normalized_port_key:
            return None
        node = workspace.nodes.get(normalized_node_id)
        if node is None:
            return None
        spec = self.registry.get_spec(node.type_id)
        port = find_port(
            node=node,
            spec=spec,
            workspace_nodes=workspace.nodes,
            port_key=normalized_port_key,
        )
        if port is None or not bool(port.exposed):
            return None
        connection_count = 0
        for edge in workspace.edges.values():
            if edge.source_node_id == normalized_node_id and edge.source_port_key == normalized_port_key:
                connection_count += 1
            if edge.target_node_id == normalized_node_id and edge.target_port_key == normalized_port_key:
                connection_count += 1
        return {
            "node_id": normalized_node_id,
            "node_title": str(node.title),
            "type_id": str(node.type_id),
            "port_key": normalized_port_key,
            "port_label": str(port.label or port.key),
            "direction": str(port.direction),
            "kind": str(port.kind),
            "data_type": str(port.data_type),
            "connection_count": int(connection_count),
        }

    def _refresh_connection_quick_insert_results(self, query: str) -> None:
        context = self._connection_quick_insert_context
        if context is None:
            self._set_connection_quick_insert_state(query=str(query), results=[], highlight_index=-1)
            return
        normalized_query = str(query)
        results: list[dict[str, Any]] = []
        if not (
            str(context.get("direction", "")).strip().lower() == "in"
            and int(context.get("connection_count", 0)) > 0
        ):
            results = build_connection_quick_insert_items(
                combined_items=self._combined_library_items(),
                query=normalized_query,
                source_direction=str(context.get("direction", "")),
                source_kind=str(context.get("kind", "")),
                source_data_type=str(context.get("data_type", "")),
                limit=self._CONNECTION_QUICK_INSERT_LIMIT,
            )
        highlight_index = 0 if results else -1
        if 0 <= self._connection_quick_insert_highlight_index < len(results):
            highlight_index = self._connection_quick_insert_highlight_index
        self._set_connection_quick_insert_state(
            query=normalized_query,
            results=results,
            highlight_index=highlight_index,
        )

    def _active_scope_camera_key(self, scope_path: tuple[str, ...] | None = None) -> tuple[str, str, tuple[str, ...]] | None:
        return window_search_scope_state.active_scope_camera_key(self, scope_path)

    def _remember_scope_camera(self, scope_path: tuple[str, ...] | None = None) -> None:
        window_search_scope_state.remember_scope_camera(self, scope_path)

    def _restore_scope_camera(self, scope_path: tuple[str, ...] | None = None) -> bool:
        return bool(window_search_scope_state.restore_scope_camera(self, scope_path))

    def _navigate_scope(self, navigate_fn: Callable[[], bool]) -> bool:
        return bool(window_search_scope_state.navigate_scope(self, navigate_fn))

    def _on_scene_scope_changed(self) -> None:
        self.request_close_connection_quick_insert()
        self.workspace_state_changed.emit()
        self.selected_node_changed.emit()

    @pyqtSlot(str)
    def set_library_query(self, query: str) -> None:
        normalized = str(query).strip()
        if normalized == self._library_query:
            return
        self._library_query = normalized
        self.node_library_changed.emit()

    @pyqtSlot(str)
    def set_library_category(self, category: str) -> None:
        normalized = str(category).strip()
        if normalized == self._library_category:
            return
        self._library_category = normalized
        self.node_library_changed.emit()

    @pyqtSlot(str)
    def set_library_data_type(self, data_type: str) -> None:
        normalized = str(data_type).strip()
        if normalized == self._library_data_type:
            return
        self._library_data_type = normalized
        self.node_library_changed.emit()

    @pyqtSlot(str)
    def set_library_direction(self, direction: str) -> None:
        normalized = str(direction).strip().lower()
        if normalized not in {"", "in", "out"}:
            normalized = ""
        if normalized == self._library_direction:
            return
        self._library_direction = normalized
        self.node_library_changed.emit()

    @pyqtSlot(bool)
    def set_snap_to_grid_enabled(self, enabled: bool) -> None:
        window_search_scope_state.set_snap_to_grid_enabled(self, enabled)

    @pyqtSlot(bool)
    def set_graphics_minimap_expanded(self, expanded: bool) -> None:
        window_search_scope_state.set_graphics_minimap_expanded(self, expanded)

    @pyqtSlot(str)
    @pyqtSlot(str, int)
    def show_graph_hint(self, message: str, timeout_ms: int = 3600) -> None:
        window_search_scope_state.show_graph_hint(self, message, timeout_ms)

    @pyqtSlot()
    def clear_graph_hint(self) -> None:
        window_search_scope_state.clear_graph_hint(self)

    def apply_graphics_preferences(self, graphics: Any) -> dict[str, Any]:
        canvas = graphics.get("canvas", {}) if isinstance(graphics, dict) else {}
        interaction = graphics.get("interaction", {}) if isinstance(graphics, dict) else {}
        theme = graphics.get("theme", {}) if isinstance(graphics, dict) else {}

        changed = False
        show_grid = bool(canvas.get("show_grid", self._graphics_show_grid))
        show_minimap = bool(canvas.get("show_minimap", self._graphics_show_minimap))
        minimap_expanded = bool(canvas.get("minimap_expanded", self._graphics_minimap_expanded))
        active_theme_id = str(theme.get("theme_id", self._active_theme_id))

        if self._graphics_show_grid != show_grid:
            self._graphics_show_grid = show_grid
            changed = True
        if self._graphics_show_minimap != show_minimap:
            self._graphics_show_minimap = show_minimap
            changed = True
        if self._graphics_minimap_expanded != minimap_expanded:
            self._graphics_minimap_expanded = minimap_expanded
            changed = True
        if self._active_theme_id != active_theme_id:
            self._active_theme_id = active_theme_id
            changed = True

        window_search_scope_state.set_snap_to_grid_enabled(
            self,
            bool(interaction.get("snap_to_grid", self._snap_to_grid_enabled)),
            persist=False,
        )
        if changed:
            self.graphics_preferences_changed.emit()

        return {
            "canvas": {
                "show_grid": bool(self._graphics_show_grid),
                "show_minimap": bool(self._graphics_show_minimap),
                "minimap_expanded": bool(self._graphics_minimap_expanded),
            },
            "interaction": {
                "snap_to_grid": bool(self._snap_to_grid_enabled),
            },
            "theme": {
                "theme_id": str(self._active_theme_id),
            },
        }

    @pyqtSlot()
    def request_open_graph_search(self) -> None:
        self._set_connection_quick_insert_state(
            open_=False,
            query="",
            results=[],
            highlight_index=-1,
            context=None,
        )
        self._set_graph_search_state(open_=True, query="", results=[], highlight_index=-1)

    @pyqtSlot()
    def request_close_graph_search(self) -> None:
        self._set_graph_search_state(open_=False, query="", results=[], highlight_index=-1)

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
        context = self._connection_quick_insert_context_for_port(node_id, port_key)
        if context is None:
            return False
        context["scene_x"] = float(scene_x)
        context["scene_y"] = float(scene_y)
        context["overlay_x"] = float(overlay_x)
        context["overlay_y"] = float(overlay_y)
        self._set_graph_search_state(open_=False, query="", results=[], highlight_index=-1)
        self._set_connection_quick_insert_state(
            open_=True,
            query="",
            results=[],
            highlight_index=-1,
            context=context,
        )
        self._refresh_connection_quick_insert_results("")
        if not self._connection_quick_insert_results:
            message = (
                "This input is already connected."
                if str(context.get("direction", "")).strip().lower() == "in"
                and int(context.get("connection_count", 0)) > 0
                else "No compatible nodes found for quick insert."
            )
            self.show_graph_hint(message, 2200)
            self.request_close_connection_quick_insert()
            return False
        return True

    @pyqtSlot()
    def request_close_connection_quick_insert(self) -> None:
        self._set_connection_quick_insert_state(
            open_=False,
            query="",
            results=[],
            highlight_index=-1,
            context=None,
        )

    @pyqtSlot(str)
    def set_connection_quick_insert_query(self, query: str) -> None:
        if not self._connection_quick_insert_open:
            return
        self._refresh_connection_quick_insert_results(query)

    @pyqtSlot(int)
    def request_connection_quick_insert_move(self, delta: int) -> None:
        if not self._connection_quick_insert_open or not self._connection_quick_insert_results:
            return
        current = self._connection_quick_insert_highlight_index
        if current < 0:
            current = 0
        next_index = max(0, min(len(self._connection_quick_insert_results) - 1, current + int(delta)))
        self._set_connection_quick_insert_state(highlight_index=next_index)

    @pyqtSlot(int)
    def request_connection_quick_insert_highlight(self, index: int) -> None:
        if not self._connection_quick_insert_open:
            return
        if index < 0 or index >= len(self._connection_quick_insert_results):
            return
        self._set_connection_quick_insert_state(highlight_index=int(index))

    @pyqtSlot(result=bool)
    def request_connection_quick_insert_accept(self) -> bool:
        if not self._connection_quick_insert_open or not self._connection_quick_insert_results:
            return False
        index = self._connection_quick_insert_highlight_index
        if index < 0 or index >= len(self._connection_quick_insert_results):
            index = 0
        return self.request_connection_quick_insert_choose(index)

    @pyqtSlot(int, result=bool)
    def request_connection_quick_insert_choose(self, index: int) -> bool:
        if index < 0 or index >= len(self._connection_quick_insert_results):
            return False
        context = self._connection_quick_insert_context
        if context is None:
            return False
        selected_item = self._connection_quick_insert_results[index]
        offset = self._CONNECTION_QUICK_INSERT_OFFSET
        scene_x = float(context.get("scene_x", 0.0))
        if str(context.get("direction", "")).strip().lower() == "in":
            scene_x -= offset
        else:
            scene_x += offset
        created = self.request_drop_node_from_library(
            str(selected_item.get("type_id", "")),
            scene_x,
            float(context.get("scene_y", 0.0)),
            "port",
            str(context.get("node_id", "")),
            str(context.get("port_key", "")),
            "",
        )
        self.request_close_connection_quick_insert()
        return bool(created)

    @pyqtSlot(str)
    def set_graph_search_query(self, query: str) -> None:
        if not self._graph_search_open:
            return
        self._refresh_graph_search_results(query)

    @pyqtSlot(int)
    def request_graph_search_move(self, delta: int) -> None:
        window_search_scope_state.request_graph_search_move(self, delta)

    @pyqtSlot(int)
    def request_graph_search_highlight(self, index: int) -> None:
        window_search_scope_state.request_graph_search_highlight(self, index)

    @pyqtSlot(result=bool)
    def request_graph_search_accept(self) -> bool:
        return bool(window_search_scope_state.request_graph_search_accept(self))

    @pyqtSlot(int, result=bool)
    def request_graph_search_jump(self, index: int) -> bool:
        return bool(window_search_scope_state.request_graph_search_jump(self, index))

    @pyqtSlot(str)
    def request_add_node_from_library(self, type_id: str) -> None:
        self._add_node_from_library(type_id)

    @pyqtSlot(result=bool)
    def request_publish_custom_workflow_from_selected(self) -> bool:
        result = self.workspace_library_controller.publish_custom_workflow_from_selected_subnode()
        return bool(result.payload)

    @pyqtSlot(result=bool)
    def request_publish_custom_workflow_from_scope(self) -> bool:
        result = self.workspace_library_controller.publish_custom_workflow_from_current_scope()
        return bool(result.payload)

    @pyqtSlot(str, result=bool)
    def request_publish_custom_workflow_from_node(self, node_id: str) -> bool:
        result = self.workspace_library_controller.publish_custom_workflow_from_node(node_id)
        return bool(result.payload)

    @pyqtSlot(str, result=bool)
    @pyqtSlot(str, str, result=bool)
    def request_delete_custom_workflow_from_library(self, workflow_id: str, workflow_scope: str = "") -> bool:
        result = self.workspace_library_controller.delete_custom_workflow(workflow_id, workflow_scope)
        return bool(result.payload)

    @pyqtSlot(str, str, result=bool)
    def request_set_custom_workflow_scope(self, workflow_id: str, workflow_scope: str) -> bool:
        result = self.workspace_library_controller.set_custom_workflow_scope(workflow_id, workflow_scope)
        return bool(result.payload)

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
        result = self.workspace_library_controller.request_drop_node_from_library(
            type_id,
            scene_x,
            scene_y,
            target_mode,
            target_node_id,
            target_port_key,
            target_edge_id,
        )
        return bool(result.payload)

    @pyqtSlot()
    def request_run_workflow(self) -> None:
        self._run_workflow()

    @pyqtSlot()
    def request_toggle_run_pause(self) -> None:
        self._toggle_pause_resume()

    @pyqtSlot()
    def request_stop_workflow(self) -> None:
        self._stop_workflow()

    @pyqtSlot()
    def request_create_workspace(self) -> None:
        self._create_workspace()

    @pyqtSlot()
    def request_create_view(self) -> None:
        self._create_view()

    @pyqtSlot(str)
    def request_switch_view(self, view_id: str) -> None:
        workspace_id = self.workspace_manager.active_workspace_id()
        workspace = self.model.project.workspaces.get(workspace_id)
        if workspace is None:
            return
        workspace.ensure_default_view()
        target_id = str(view_id).strip()
        if not target_id or target_id not in workspace.views:
            return
        if workspace.active_view_id == target_id:
            return
        self._remember_scope_camera()
        self._switch_view(target_id)
        self.scene.sync_scope_with_active_view()
        self._restore_scope_camera()

    @pyqtSlot(str, result=bool)
    def request_open_subnode_scope(self, node_id: str) -> bool:
        normalized_node_id = str(node_id).strip()
        if not normalized_node_id:
            return False
        return bool(self._navigate_scope(lambda: self.scene.open_subnode_scope(normalized_node_id)))

    @pyqtSlot(str, result=bool)
    def request_open_scope_breadcrumb(self, node_id: str) -> bool:
        normalized_node_id = str(node_id).strip()
        return bool(self._navigate_scope(lambda: self.scene.navigate_scope_to(normalized_node_id)))

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
    def request_open_project(self) -> None:
        self._open_project()

    @pyqtSlot()
    def request_rename_workspace(self) -> None:
        self._rename_active_workspace()

    @pyqtSlot()
    def request_duplicate_workspace(self) -> None:
        self._duplicate_active_workspace()

    @pyqtSlot()
    def request_close_workspace(self) -> None:
        self._close_active_workspace()

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
        self.set_snap_to_grid_enabled(not self._snap_to_grid_enabled)
        return bool(self._snap_to_grid_enabled)

    @pyqtSlot()
    def request_connect_selected_nodes(self) -> None:
        self._connect_selected_nodes()

    @pyqtSlot(result=bool)
    def request_duplicate_selected_nodes(self) -> bool:
        return bool(self._duplicate_selected_nodes())

    @pyqtSlot(result=bool)
    def request_group_selected_nodes(self) -> bool:
        return bool(self._group_selected_nodes())

    @pyqtSlot(result=bool)
    def request_ungroup_selected_nodes(self) -> bool:
        return bool(self._ungroup_selected_nodes())

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
        return bool(self.workspace_library_controller.request_connect_ports(node_a_id, port_a, node_b_id, port_b).payload)

    @pyqtSlot(str, result=bool)
    def request_remove_edge(self, edge_id: str) -> bool:
        return bool(self.workspace_library_controller.request_remove_edge(edge_id).payload)

    @pyqtSlot(str, result=bool)
    def request_remove_node(self, node_id: str) -> bool:
        return bool(self.workspace_library_controller.request_remove_node(node_id).payload)

    @pyqtSlot(str, result=bool)
    def request_rename_node(self, node_id: str) -> bool:
        return bool(self.workspace_library_controller.request_rename_node(node_id).payload)

    @pyqtSlot("QVariantList", result=bool)
    def request_delete_selected_graph_items(self, edge_ids: list[Any]) -> bool:
        return bool(self.workspace_library_controller.request_delete_selected_graph_items(edge_ids).payload)

    @pyqtSlot(str, "QVariant")
    def set_selected_node_property(self, key: str, value: Any) -> None:
        self.workspace_library_controller.set_selected_node_property(key, value)

    @pyqtSlot(str, bool)
    def set_selected_port_exposed(self, key: str, exposed: bool) -> None:
        self.workspace_library_controller.set_selected_port_exposed(key, exposed)

    @pyqtSlot(bool)
    def set_selected_node_collapsed(self, collapsed: bool) -> None:
        self.workspace_library_controller.set_selected_node_collapsed(collapsed)

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

    def _search_graph_nodes(self, query, limit=_GRAPH_SEARCH_LIMIT):
        return self.workspace_library_controller.search_graph_nodes(query, limit)

    def _jump_to_graph_node(self, workspace_id, node_id):
        return self.workspace_library_controller.jump_to_graph_node(workspace_id, node_id)

    def _create_view(self):
        return self.workspace_library_controller.create_view()

    def _switch_view(self, view_id):
        return self.workspace_library_controller.switch_view(view_id)

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
        self.project_session_controller.show_workflow_settings_dialog()

    @pyqtSlot()
    @pyqtSlot(bool)
    def show_graphics_settings_dialog(self, _checked: bool = False) -> None:
        from ea_node_editor.ui.dialogs import GraphicsSettingsDialog

        dialog = GraphicsSettingsDialog(
            initial_settings=self.app_preferences_controller.graphics_settings(),
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        self.app_preferences_controller.set_graphics_settings(dialog.values(), host=self)

    @pyqtSlot()
    @pyqtSlot(bool)
    def set_script_editor_panel_visible(self, checked: bool | None = None) -> None:
        self.project_session_controller.set_script_editor_panel_visible(checked)

    def _prompt_recover_autosave(self):
        return self.project_session_controller.prompt_recover_autosave()

    def _update_metrics(self) -> None:
        metrics = read_system_metrics()
        self.update_system_metrics(metrics.cpu_percent, metrics.ram_used_gb, metrics.ram_total_gb)

    def _open_logs(self) -> None:
        return

    def showEvent(self, event) -> None:  # noqa: ANN001
        super().showEvent(event)
        if self._autosave_recovery_deferred:
            QTimer.singleShot(0, self._process_deferred_autosave_recovery)

    def closeEvent(self, event) -> None:  # noqa: ANN001
        self.autosave_timer.stop()
        self._autosave_tick()
        self._persist_session()
        self.execution_client.shutdown()
        super().closeEvent(event)

    def update_engine_status(
        self,
        state: Literal["ready", "running", "paused", "error"],
        details: str = "",
    ) -> None:
        text = state.capitalize()
        if details:
            text = f"{text} ({details})"
        icon_map = {
            "ready": "R",
            "running": "Run",
            "paused": "P",
            "error": "!",
        }
        self.status_engine.set_icon(icon_map.get(state, "E"))
        self.status_engine.set_text(text)

    def update_job_counters(self, running: int, queued: int, done: int, failed: int) -> None:
        self.status_jobs.set_text(f"R:{running} Q:{queued} D:{done} F:{failed}")

    def update_system_metrics(self, cpu_percent: float, ram_used_gb: float, ram_total_gb: float) -> None:
        self.status_metrics.set_text(
            f"CPU:{cpu_percent:.0f}% RAM:{ram_used_gb:.1f}/{ram_total_gb:.1f} GB"
        )

    def update_notification_counters(self, warnings: int, errors: int) -> None:
        self.status_notifications.set_text(f"W:{warnings} E:{errors}")
