from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Literal

from PyQt6.QtCore import QTimer, Qt, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtQuick import QQuickWindow, QSGRendererInterface
from PyQt6.QtQuickWidgets import QQuickWidget
from PyQt6.QtWidgets import QMainWindow

from ea_node_editor.execution.client import ProcessExecutionClient
from ea_node_editor.graph.model import GraphModel, ProjectData
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.persistence.session_store import SessionAutosaveStore
from ea_node_editor.settings import (
    AUTOSAVE_INTERVAL_MS,
    autosave_project_path,
    recent_session_path,
)
from ea_node_editor.telemetry.system_metrics import read_system_metrics
from ea_node_editor.ui.graph_interactions import GraphInteractions
from ea_node_editor.ui.shell.controllers import (
    ProjectSessionController,
    RunController,
    WorkspaceLibraryController,
)
from ea_node_editor.ui.shell.runtime_history import RuntimeGraphHistory
from ea_node_editor.ui.shell.state import ShellState
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


class ShellWindow(QMainWindow):
    execution_event = pyqtSignal(dict)
    node_library_changed = pyqtSignal()
    workspace_state_changed = pyqtSignal()
    selected_node_changed = pyqtSignal()
    project_meta_changed = pyqtSignal()
    graph_search_changed = pyqtSignal()
    graph_hint_changed = pyqtSignal()
    snap_to_grid_changed = pyqtSignal()

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
    _SNAP_GRID_SIZE = 20.0

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
        self.status_engine = StatusItemModel("E", "Ready", self)
        self.status_jobs = StatusItemModel("J", "R:0 Q:0 D:0 F:0", self)
        self.status_metrics = StatusItemModel("M", "CPU:0% RAM:0/0 GB", self)
        self.status_notifications = StatusItemModel("N", "W:0 E:0", self)
        self._graph_search_open = False
        self._graph_search_query = ""
        self._graph_search_results: list[dict[str, Any]] = []
        self._graph_search_highlight_index = -1
        self._graph_hint_message = ""
        self._snap_to_grid_enabled = False
        self._runtime_scope_camera: dict[tuple[str, str, tuple[str, ...]], tuple[float, float, float]] = {}

        self.workspace_library_controller = WorkspaceLibraryController(self)
        self.project_session_controller = ProjectSessionController(self)
        self.run_controller = RunController(self)

        self.execution_client = ProcessExecutionClient()
        self.execution_client.subscribe(self.execution_event.emit)
        self.execution_event.connect(self._handle_execution_event, Qt.ConnectionType.QueuedConnection)

        self._create_actions()
        self._build_menu_bar()
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
        self.action_new_project = QAction("New Project", self)
        self.action_new_project.setShortcut(QKeySequence.StandardKey.New)
        self.action_new_project.triggered.connect(self._new_project)

        self.action_new_workspace = QAction("New Workspace", self)
        self.action_new_workspace.setShortcut(QKeySequence("Ctrl+Shift+N"))
        self.action_new_workspace.triggered.connect(self._create_workspace)

        self.action_save_project = QAction("Save Project", self)
        self.action_save_project.setShortcut(QKeySequence.StandardKey.Save)
        self.action_save_project.triggered.connect(self._save_project)

        self.action_open_project = QAction("Open Project", self)
        self.action_open_project.setShortcut(QKeySequence.StandardKey.Open)
        self.action_open_project.triggered.connect(self._open_project)

        self.action_workflow_settings = QAction("Workflow Settings", self)
        self.action_workflow_settings.setShortcut(QKeySequence("Ctrl+,"))
        self.action_workflow_settings.triggered.connect(self.show_workflow_settings_dialog)

        self.action_toggle_script_editor = QAction("Script Editor", self)
        self.action_toggle_script_editor.setCheckable(True)
        self.action_toggle_script_editor.setShortcut(QKeySequence("Ctrl+Shift+E"))
        self.action_toggle_script_editor.triggered.connect(self.set_script_editor_panel_visible)

        self.action_run = QAction("Run", self)
        self.action_run.setShortcut(QKeySequence("F5"))
        self.action_run.triggered.connect(self._run_workflow)

        self.action_stop = QAction("Stop", self)
        self.action_stop.setShortcut(QKeySequence("Shift+F5"))
        self.action_stop.triggered.connect(self._stop_workflow)

        self.action_pause = QAction("Pause", self)
        self.action_pause.setShortcut(QKeySequence("F6"))
        self.action_pause.triggered.connect(self._toggle_pause_resume)

        self.action_connect_selected = QAction("Connect Selected", self)
        self.action_connect_selected.setShortcut(QKeySequence("Ctrl+L"))
        self.action_connect_selected.triggered.connect(self._connect_selected_nodes)

        self.action_duplicate_selection = QAction("Duplicate Selection", self)
        self.action_duplicate_selection.setShortcut(QKeySequence("Ctrl+D"))
        self.action_duplicate_selection.triggered.connect(self._duplicate_selected_nodes)

        self.action_align_left = QAction("Align Left", self)
        self.action_align_left.triggered.connect(self._align_selection_left)

        self.action_align_right = QAction("Align Right", self)
        self.action_align_right.triggered.connect(self._align_selection_right)

        self.action_align_top = QAction("Align Top", self)
        self.action_align_top.triggered.connect(self._align_selection_top)

        self.action_align_bottom = QAction("Align Bottom", self)
        self.action_align_bottom.triggered.connect(self._align_selection_bottom)

        self.action_distribute_horizontally = QAction("Distribute Horizontally", self)
        self.action_distribute_horizontally.triggered.connect(self._distribute_selection_horizontally)

        self.action_distribute_vertically = QAction("Distribute Vertically", self)
        self.action_distribute_vertically.triggered.connect(self._distribute_selection_vertically)

        self.action_snap_to_grid = QAction("Snap to Grid", self)
        self.action_snap_to_grid.setCheckable(True)
        self.action_snap_to_grid.setChecked(False)
        self.action_snap_to_grid.toggled.connect(self.set_snap_to_grid_enabled)

        self.action_undo = QAction("Undo", self)
        self.action_undo.setShortcut(QKeySequence("Ctrl+Z"))
        self.action_undo.triggered.connect(self._undo)

        self.action_redo = QAction("Redo", self)
        self.action_redo.setShortcuts([QKeySequence("Ctrl+Shift+Z"), QKeySequence("Ctrl+Y")])
        self.action_redo.triggered.connect(self._redo)

        self.action_copy_selection = QAction("Copy Selection", self)
        self.action_copy_selection.setShortcut(QKeySequence.StandardKey.Copy)
        self.action_copy_selection.triggered.connect(self._copy_selected_nodes_to_clipboard)

        self.action_cut_selection = QAction("Cut Selection", self)
        self.action_cut_selection.setShortcut(QKeySequence.StandardKey.Cut)
        self.action_cut_selection.triggered.connect(self._cut_selected_nodes_to_clipboard)

        self.action_paste_selection = QAction("Paste Selection", self)
        self.action_paste_selection.setShortcut(QKeySequence.StandardKey.Paste)
        self.action_paste_selection.triggered.connect(self._paste_nodes_from_clipboard)

        self.action_frame_all = QAction("Frame All", self)
        self.action_frame_all.setShortcut(QKeySequence("A"))
        self.action_frame_all.triggered.connect(self._frame_all)

        self.action_frame_selection = QAction("Frame Selection", self)
        self.action_frame_selection.setShortcut(QKeySequence("F"))
        self.action_frame_selection.triggered.connect(self._frame_selection)

        self.action_center_selection = QAction("Center Selection", self)
        self.action_center_selection.setShortcut(QKeySequence("Shift+F"))
        self.action_center_selection.triggered.connect(self._center_on_selection)

        self.action_scope_parent = QAction("Scope Parent", self)
        self.action_scope_parent.setShortcut(QKeySequence("Alt+Left"))
        self.action_scope_parent.triggered.connect(self.request_navigate_scope_parent)

        self.action_scope_root = QAction("Scope Root", self)
        self.action_scope_root.setShortcut(QKeySequence("Alt+Home"))
        self.action_scope_root.triggered.connect(self.request_navigate_scope_root)

        self.action_graph_search = QAction("Graph Search", self)
        self.action_graph_search.setShortcut(QKeySequence("Ctrl+K"))
        self.action_graph_search.triggered.connect(self.request_open_graph_search)

        self.action_new_view = QAction("New View", self)
        self.action_new_view.setShortcut(QKeySequence("Ctrl+Shift+V"))
        self.action_new_view.triggered.connect(self._create_view)

        self.action_duplicate_workspace = QAction("Duplicate Workspace", self)
        self.action_duplicate_workspace.setShortcut(QKeySequence("Ctrl+Shift+D"))
        self.action_duplicate_workspace.triggered.connect(self._duplicate_active_workspace)

        self.action_rename_workspace = QAction("Rename Workspace", self)
        self.action_rename_workspace.setShortcut(QKeySequence("F2"))
        self.action_rename_workspace.triggered.connect(self._rename_active_workspace)

        self.action_close_workspace = QAction("Close Workspace", self)
        self.action_close_workspace.setShortcut(QKeySequence.StandardKey.Close)
        self.action_close_workspace.triggered.connect(self._close_active_workspace)

        self.action_next_workspace = QAction("Next Workspace", self)
        self.action_next_workspace.setShortcuts([QKeySequence("Ctrl+Tab"), QKeySequence("Ctrl+PgDown")])
        self.action_next_workspace.triggered.connect(lambda: self._switch_workspace_by_offset(1))

        self.action_prev_workspace = QAction("Previous Workspace", self)
        self.action_prev_workspace.setShortcuts([QKeySequence("Ctrl+Shift+Tab"), QKeySequence("Ctrl+PgUp")])
        self.action_prev_workspace.triggered.connect(lambda: self._switch_workspace_by_offset(-1))

        self.action_import_node_package = QAction("Import Node Package...", self)
        self.action_import_node_package.triggered.connect(self._import_node_package)

        self.action_export_node_package = QAction("Export Node Package...", self)
        self.action_export_node_package.triggered.connect(self._export_node_package)

        for action in (
            self.action_new_project,
            self.action_new_workspace,
            self.action_save_project,
            self.action_open_project,
            self.action_workflow_settings,
            self.action_toggle_script_editor,
            self.action_run,
            self.action_stop,
            self.action_pause,
            self.action_undo,
            self.action_redo,
            self.action_copy_selection,
            self.action_cut_selection,
            self.action_paste_selection,
            self.action_connect_selected,
            self.action_duplicate_selection,
            self.action_align_left,
            self.action_align_right,
            self.action_align_top,
            self.action_align_bottom,
            self.action_distribute_horizontally,
            self.action_distribute_vertically,
            self.action_snap_to_grid,
            self.action_frame_all,
            self.action_frame_selection,
            self.action_center_selection,
            self.action_scope_parent,
            self.action_scope_root,
            self.action_graph_search,
            self.action_new_view,
            self.action_duplicate_workspace,
            self.action_rename_workspace,
            self.action_close_workspace,
            self.action_next_workspace,
            self.action_prev_workspace,
            self.action_import_node_package,
            self.action_export_node_package,
        ):
            action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
            self.addAction(action)

    def _build_menu_bar(self) -> None:
        menu_bar = self.menuBar()
        menu_bar.clear()

        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(self.action_new_project)
        file_menu.addAction(self.action_open_project)
        file_menu.addAction(self.action_save_project)
        file_menu.addSeparator()
        file_menu.addAction(self.action_import_node_package)
        file_menu.addAction(self.action_export_node_package)

        edit_menu = menu_bar.addMenu("&Edit")
        edit_menu.addAction(self.action_undo)
        edit_menu.addAction(self.action_redo)
        edit_menu.addSeparator()
        edit_menu.addAction(self.action_copy_selection)
        edit_menu.addAction(self.action_cut_selection)
        edit_menu.addAction(self.action_paste_selection)
        edit_menu.addSeparator()
        edit_menu.addAction(self.action_connect_selected)
        edit_menu.addAction(self.action_duplicate_selection)
        layout_menu = edit_menu.addMenu("Layout")
        layout_menu.addAction(self.action_align_left)
        layout_menu.addAction(self.action_align_right)
        layout_menu.addAction(self.action_align_top)
        layout_menu.addAction(self.action_align_bottom)
        layout_menu.addSeparator()
        layout_menu.addAction(self.action_distribute_horizontally)
        layout_menu.addAction(self.action_distribute_vertically)
        edit_menu.addAction(self.action_snap_to_grid)
        edit_menu.addSeparator()
        edit_menu.addAction(self.action_graph_search)

        view_menu = menu_bar.addMenu("&View")
        view_menu.addAction(self.action_toggle_script_editor)
        view_menu.addSeparator()
        view_menu.addAction(self.action_frame_all)
        view_menu.addAction(self.action_frame_selection)
        view_menu.addAction(self.action_center_selection)
        view_menu.addSeparator()
        view_menu.addAction(self.action_scope_parent)
        view_menu.addAction(self.action_scope_root)

        run_menu = menu_bar.addMenu("&Run")
        run_menu.addAction(self.action_run)
        run_menu.addAction(self.action_pause)
        run_menu.addAction(self.action_stop)

        workspace_menu = menu_bar.addMenu("&Workspace")
        workspace_menu.addAction(self.action_new_workspace)
        workspace_menu.addAction(self.action_new_view)
        workspace_menu.addAction(self.action_duplicate_workspace)
        workspace_menu.addAction(self.action_rename_workspace)
        workspace_menu.addAction(self.action_close_workspace)
        workspace_menu.addSeparator()
        workspace_menu.addAction(self.action_next_workspace)
        workspace_menu.addAction(self.action_prev_workspace)

        tools_menu = menu_bar.addMenu("&Tools")
        tools_menu.addAction(self.action_workflow_settings)

    def _wire_signals(self) -> None:
        self.scene.node_selected.connect(self._on_scene_node_selected)
        self.scene.scope_changed.connect(self._on_scene_scope_changed)
        self.script_editor.script_apply_requested.connect(self._on_node_property_changed)
        self.workspace_tabs.current_index_changed.connect(self._on_workspace_tab_changed)

    def _build_qml_shell(self) -> None:
        self.quick_widget = QQuickWidget(self)
        self.quick_widget.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)

        context = self.quick_widget.rootContext()
        context.setContextProperty("mainWindow", self)
        context.setContextProperty("sceneBridge", self.scene)
        context.setContextProperty("viewBridge", self.view)
        context.setContextProperty("consoleBridge", self.console_panel)
        context.setContextProperty("scriptEditorBridge", self.script_editor)
        context.setContextProperty("scriptHighlighterBridge", self.script_highlighter)
        context.setContextProperty("workspaceTabsBridge", self.workspace_tabs)
        context.setContextProperty("statusEngine", self.status_engine)
        context.setContextProperty("statusJobs", self.status_jobs)
        context.setContextProperty("statusMetrics", self.status_metrics)
        context.setContextProperty("statusNotifications", self.status_notifications)

        qml_path = Path(__file__).resolve().parents[2] / "ui_qml" / "MainShell.qml"
        self.quick_widget.setSource(QUrl.fromLocalFile(str(qml_path)))
        self.setCentralWidget(self.quick_widget)

    @pyqtProperty(str, notify=project_meta_changed)
    def project_display_name(self) -> str:
        filename = Path(self.project_path).name if self.project_path else "untitled.sfe"
        return f"EA Node Editor - {filename}"

    @pyqtProperty("QVariantList", notify=node_library_changed)
    def filtered_node_library_items(self) -> list[dict[str, Any]]:
        specs = self.registry.filter_nodes(
            query=self._library_query,
            category=self._library_category,
            data_type=self._library_data_type,
            direction=self._library_direction,
        )
        return [
            {
                "type_id": spec.type_id,
                "display_name": spec.display_name,
                "category": spec.category,
                "icon": spec.icon,
                "description": spec.description,
                "ports": [
                    {
                        "key": port.key,
                        "direction": port.direction,
                        "kind": port.kind,
                        "data_type": port.data_type,
                        "exposed": bool(port.exposed),
                    }
                    for port in spec.ports
                ],
            }
            for spec in specs
        ]

    @pyqtProperty("QVariantList", notify=node_library_changed)
    def grouped_node_library_items(self) -> list[dict[str, Any]]:
        groups: dict[str, list[dict[str, Any]]] = {}
        for item in self.filtered_node_library_items:
            category = str(item.get("category", "Other"))
            groups.setdefault(category, []).append(item)
        payload: list[dict[str, Any]] = []
        for category in sorted(groups):
            payload.append({"kind": "category", "category": category, "label": category})
            for node_item in groups[category]:
                payload.append(
                    {
                        "kind": "node",
                        "category": category,
                        "type_id": node_item["type_id"],
                        "display_name": node_item["display_name"],
                        "icon": node_item.get("icon", ""),
                        "description": node_item["description"],
                        "ports": list(node_item.get("ports", [])),
                    }
                )
        return payload

    @pyqtProperty("QVariantList", notify=node_library_changed)
    def library_category_options(self) -> list[dict[str, str]]:
        return [{"label": "All Categories", "value": ""}] + [
            {"label": category, "value": category} for category in self.registry.categories()
        ]

    @pyqtProperty("QVariantList", notify=node_library_changed)
    def library_direction_options(self) -> list[dict[str, str]]:
        return [
            {"label": "Any Port Direction", "value": ""},
            {"label": "Input", "value": "in"},
            {"label": "Output", "value": "out"},
        ]

    @pyqtProperty("QVariantList", notify=node_library_changed)
    def library_data_type_options(self) -> list[dict[str, str]]:
        data_types = sorted({port.data_type for spec in self.registry.all_specs() for port in spec.ports})
        return [{"label": "Any Data Type", "value": ""}] + [
            {"label": data_type, "value": data_type} for data_type in data_types
        ]

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

    @pyqtProperty(str, notify=graph_hint_changed)
    def graph_hint_message(self) -> str:
        return str(self._graph_hint_message)

    @pyqtProperty(bool, notify=graph_hint_changed)
    def graph_hint_visible(self) -> bool:
        return bool(self._graph_hint_message.strip())

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

    @pyqtProperty(str, notify=selected_node_changed)
    def selected_node_summary(self) -> str:
        selected = self._selected_node_context()
        if selected is None:
            return "No node selected"
        node, spec = selected
        return f"{spec.display_name}\\nID: {node.node_id}\\nType: {node.type_id}"

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

    @pyqtProperty("QVariantList", notify=selected_node_changed)
    def selected_node_property_items(self) -> list[dict[str, Any]]:
        selected = self._selected_node_context()
        if selected is None:
            return []
        node, spec = selected
        return [
            {
                "key": prop.key,
                "label": prop.label,
                "type": prop.type,
                "value": node.properties.get(prop.key, prop.default),
                "enum_values": list(prop.enum_values),
            }
            for prop in spec.properties
        ]

    @pyqtProperty("QVariantList", notify=selected_node_changed)
    def selected_node_port_items(self) -> list[dict[str, Any]]:
        selected = self._selected_node_context()
        if selected is None:
            return []
        node, spec = selected
        return [
            {
                "key": port.key,
                "direction": port.direction,
                "kind": port.kind,
                "data_type": port.data_type,
                "required": bool(port.required),
                "exposed": bool(node.exposed_ports.get(port.key, port.exposed)),
            }
            for port in spec.ports
        ]

    def _set_graph_search_state(
        self,
        *,
        open_: bool | None = None,
        query: str | None = None,
        results: list[dict[str, Any]] | None = None,
        highlight_index: int | None = None,
    ) -> None:
        changed = False
        if open_ is not None:
            normalized_open = bool(open_)
            if normalized_open != self._graph_search_open:
                self._graph_search_open = normalized_open
                changed = True
        if query is not None:
            normalized_query = str(query)
            if normalized_query != self._graph_search_query:
                self._graph_search_query = normalized_query
                changed = True
        if results is not None:
            normalized_results = list(results)
            if normalized_results != self._graph_search_results:
                self._graph_search_results = normalized_results
                changed = True
        if highlight_index is not None:
            normalized_index = int(highlight_index)
            if normalized_index != self._graph_search_highlight_index:
                self._graph_search_highlight_index = normalized_index
                changed = True
        if changed:
            self.graph_search_changed.emit()

    def _refresh_graph_search_results(self, query: str) -> None:
        normalized_query = str(query).strip()
        if not normalized_query:
            self._set_graph_search_state(query="", results=[], highlight_index=-1)
            return
        ranked = self._search_graph_nodes(normalized_query, limit=self._GRAPH_SEARCH_LIMIT)
        highlight = 0 if ranked else -1
        self._set_graph_search_state(query=normalized_query, results=ranked, highlight_index=highlight)

    def _active_scope_camera_key(self, scope_path: tuple[str, ...] | None = None) -> tuple[str, str, tuple[str, ...]] | None:
        workspace_id = self.workspace_manager.active_workspace_id()
        workspace = self.model.project.workspaces.get(workspace_id)
        if workspace is None:
            return None
        workspace.ensure_default_view()
        view_id = workspace.active_view_id
        if not view_id:
            return None
        if scope_path is None:
            scope_path = tuple(str(value) for value in self.scene.active_scope_path)
        return workspace_id, view_id, tuple(scope_path)

    def _remember_scope_camera(self, scope_path: tuple[str, ...] | None = None) -> None:
        key = self._active_scope_camera_key(scope_path)
        if key is None:
            return
        center = self.view.mapToScene(self.view.viewport().rect().center())
        self._runtime_scope_camera[key] = (float(self.view.zoom), float(center.x()), float(center.y()))

    def _restore_scope_camera(self, scope_path: tuple[str, ...] | None = None) -> bool:
        key = self._active_scope_camera_key(scope_path)
        if key is None:
            return False
        state = self._runtime_scope_camera.get(key)
        if state is None:
            return False
        zoom, pan_x, pan_y = state
        self.view.set_zoom(max(0.1, min(3.0, float(zoom))))
        self.view.centerOn(float(pan_x), float(pan_y))
        return True

    def _navigate_scope(self, navigate_fn: Callable[[], bool]) -> bool:
        self._remember_scope_camera()
        changed = bool(navigate_fn())
        if not changed:
            return False
        if not self._restore_scope_camera():
            self._frame_all()
        self.workspace_state_changed.emit()
        return True

    def _on_scene_scope_changed(self) -> None:
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
        normalized = bool(enabled)
        if self._snap_to_grid_enabled == normalized:
            if self.action_snap_to_grid.isChecked() != normalized:
                blocked = self.action_snap_to_grid.blockSignals(True)
                self.action_snap_to_grid.setChecked(normalized)
                self.action_snap_to_grid.blockSignals(blocked)
            return
        self._snap_to_grid_enabled = normalized
        if self.action_snap_to_grid.isChecked() != normalized:
            blocked = self.action_snap_to_grid.blockSignals(True)
            self.action_snap_to_grid.setChecked(normalized)
            self.action_snap_to_grid.blockSignals(blocked)
        self.snap_to_grid_changed.emit()

    @pyqtSlot(str)
    @pyqtSlot(str, int)
    def show_graph_hint(self, message: str, timeout_ms: int = 3600) -> None:
        normalized = str(message).strip()
        if not normalized:
            self.clear_graph_hint()
            return
        self._graph_hint_message = normalized
        self.graph_hint_changed.emit()
        timeout_value = max(250, int(timeout_ms))
        self.graph_hint_timer.start(timeout_value)

    @pyqtSlot()
    def clear_graph_hint(self) -> None:
        if self.graph_hint_timer.isActive():
            self.graph_hint_timer.stop()
        if not self._graph_hint_message:
            return
        self._graph_hint_message = ""
        self.graph_hint_changed.emit()

    @pyqtSlot()
    def request_open_graph_search(self) -> None:
        self._set_graph_search_state(open_=True, query="", results=[], highlight_index=-1)

    @pyqtSlot()
    def request_close_graph_search(self) -> None:
        self._set_graph_search_state(open_=False, query="", results=[], highlight_index=-1)

    @pyqtSlot(str)
    def set_graph_search_query(self, query: str) -> None:
        if not self._graph_search_open:
            return
        self._refresh_graph_search_results(query)

    @pyqtSlot(int)
    def request_graph_search_move(self, delta: int) -> None:
        if not self._graph_search_open or not self._graph_search_results:
            return
        step = 1 if int(delta) > 0 else -1 if int(delta) < 0 else 0
        if step == 0:
            return
        count = len(self._graph_search_results)
        current = self._graph_search_highlight_index
        if current < 0 or current >= count:
            next_index = 0 if step > 0 else count - 1
        else:
            next_index = max(0, min(count - 1, current + step))
        self._set_graph_search_state(highlight_index=next_index)

    @pyqtSlot(int)
    def request_graph_search_highlight(self, index: int) -> None:
        if not self._graph_search_open:
            return
        normalized = int(index)
        if normalized < 0 or normalized >= len(self._graph_search_results):
            return
        self._set_graph_search_state(highlight_index=normalized)

    @pyqtSlot(result=bool)
    def request_graph_search_accept(self) -> bool:
        if not self._graph_search_open:
            return False
        if not self._graph_search_query.strip():
            return False
        if not self._graph_search_results:
            return False
        index = self._graph_search_highlight_index
        if index < 0 or index >= len(self._graph_search_results):
            index = 0
        result = self._graph_search_results[index]
        jumped = self._jump_to_graph_node(result["workspace_id"], result["node_id"])
        if jumped:
            self.request_close_graph_search()
        return bool(jumped)

    @pyqtSlot(int, result=bool)
    def request_graph_search_jump(self, index: int) -> bool:
        normalized = int(index)
        if normalized < 0 or normalized >= len(self._graph_search_results):
            return False
        self._set_graph_search_state(highlight_index=normalized)
        return bool(self.request_graph_search_accept())

    @pyqtSlot(str)
    def request_add_node_from_library(self, type_id: str) -> None:
        self._add_node_from_library(type_id)

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

    _DELEGATED_METHODS: dict[str, tuple[str, str]] = {
        "_ensure_project_metadata_defaults": ("project_session_controller", "ensure_project_metadata_defaults"),
        "_workflow_settings_payload": ("project_session_controller", "workflow_settings_payload"),
        "_persist_script_editor_state": ("project_session_controller", "persist_script_editor_state"),
        "_restore_script_editor_state": ("project_session_controller", "restore_script_editor_state"),
        "_switch_workspace_by_offset": ("workspace_library_controller", "switch_workspace_by_offset"),
        "_refresh_workspace_tabs": ("workspace_library_controller", "refresh_workspace_tabs"),
        "_switch_workspace": ("workspace_library_controller", "switch_workspace"),
        "_save_active_view_state": ("workspace_library_controller", "save_active_view_state"),
        "_restore_active_view_state": ("workspace_library_controller", "restore_active_view_state"),
        "_visible_scene_rect": ("workspace_library_controller", "visible_scene_rect"),
        "_current_workspace_scene_bounds": ("workspace_library_controller", "current_workspace_scene_bounds"),
        "_selection_bounds": ("workspace_library_controller", "selection_bounds"),
        "_frame_all": ("workspace_library_controller", "frame_all"),
        "_frame_selection": ("workspace_library_controller", "frame_selection"),
        "_frame_node": ("workspace_library_controller", "frame_node"),
        "_center_on_node": ("workspace_library_controller", "center_on_node"),
        "_center_on_selection": ("workspace_library_controller", "center_on_selection"),
        "_search_graph_nodes": ("workspace_library_controller", "search_graph_nodes"),
        "_jump_to_graph_node": ("workspace_library_controller", "jump_to_graph_node"),
        "_create_view": ("workspace_library_controller", "create_view"),
        "_switch_view": ("workspace_library_controller", "switch_view"),
        "_create_workspace": ("workspace_library_controller", "create_workspace"),
        "_rename_active_workspace": ("workspace_library_controller", "rename_active_workspace"),
        "_duplicate_active_workspace": ("workspace_library_controller", "duplicate_active_workspace"),
        "_close_active_workspace": ("workspace_library_controller", "close_active_workspace"),
        "_on_workspace_tab_changed": ("workspace_library_controller", "on_workspace_tab_changed"),
        "_on_workspace_tab_close": ("workspace_library_controller", "on_workspace_tab_close"),
        "_add_node_from_library": ("workspace_library_controller", "add_node_from_library"),
        "_insert_library_node": ("workspace_library_controller", "insert_library_node"),
        "_active_workspace": ("workspace_library_controller", "active_workspace"),
        "_prompt_connection_candidate": ("workspace_library_controller", "prompt_connection_candidate"),
        "_auto_connect_dropped_node_to_port": ("workspace_library_controller", "auto_connect_dropped_node_to_port"),
        "_auto_connect_dropped_node_to_edge": ("workspace_library_controller", "auto_connect_dropped_node_to_edge"),
        "_on_scene_node_selected": ("workspace_library_controller", "on_scene_node_selected"),
        "_on_node_property_changed": ("workspace_library_controller", "on_node_property_changed"),
        "_on_port_exposed_changed": ("workspace_library_controller", "on_port_exposed_changed"),
        "_on_node_collapse_changed": ("workspace_library_controller", "on_node_collapse_changed"),
        "_connect_selected_nodes": ("workspace_library_controller", "connect_selected_nodes"),
        "_duplicate_selected_nodes": ("workspace_library_controller", "duplicate_selected_nodes"),
        "_align_selection_left": ("workspace_library_controller", "align_selection_left"),
        "_align_selection_right": ("workspace_library_controller", "align_selection_right"),
        "_align_selection_top": ("workspace_library_controller", "align_selection_top"),
        "_align_selection_bottom": ("workspace_library_controller", "align_selection_bottom"),
        "_distribute_selection_horizontally": ("workspace_library_controller", "distribute_selection_horizontally"),
        "_distribute_selection_vertically": ("workspace_library_controller", "distribute_selection_vertically"),
        "_copy_selected_nodes_to_clipboard": ("workspace_library_controller", "copy_selected_nodes_to_clipboard"),
        "_cut_selected_nodes_to_clipboard": ("workspace_library_controller", "cut_selected_nodes_to_clipboard"),
        "_paste_nodes_from_clipboard": ("workspace_library_controller", "paste_nodes_from_clipboard"),
        "_undo": ("workspace_library_controller", "undo"),
        "_redo": ("workspace_library_controller", "redo"),
        "_selected_node_context": ("workspace_library_controller", "selected_node_context"),
        "_focus_failed_node": ("workspace_library_controller", "focus_failed_node"),
        "_reveal_parent_chain": ("workspace_library_controller", "reveal_parent_chain"),
        "_import_node_package": ("workspace_library_controller", "import_node_package"),
        "_export_node_package": ("workspace_library_controller", "export_node_package"),
        "_run_workflow": ("run_controller", "run_workflow"),
        "_toggle_pause_resume": ("run_controller", "toggle_pause_resume"),
        "_pause_workflow": ("run_controller", "pause_workflow"),
        "_resume_workflow": ("run_controller", "resume_workflow"),
        "_stop_workflow": ("run_controller", "stop_workflow"),
        "_handle_execution_event": ("run_controller", "handle_execution_event"),
        "_clear_active_run": ("run_controller", "clear_active_run"),
        "_set_run_ui_state": ("run_controller", "set_run_ui_state"),
        "_update_run_actions": ("run_controller", "update_run_actions"),
        "_save_project": ("project_session_controller", "save_project"),
        "_new_project": ("project_session_controller", "new_project"),
        "_open_project": ("project_session_controller", "open_project"),
        "_restore_session": ("project_session_controller", "restore_session"),
        "_discard_autosave_snapshot": ("project_session_controller", "discard_autosave_snapshot"),
        "_recover_autosave_if_newer": ("project_session_controller", "recover_autosave_if_newer"),
        "_process_deferred_autosave_recovery": ("project_session_controller", "process_deferred_autosave_recovery"),
        "_autosave_tick": ("project_session_controller", "autosave_tick"),
        "_persist_session": ("project_session_controller", "persist_session"),
    }

    def __getattr__(self, name: str):
        delegate = self._DELEGATED_METHODS.get(name)
        if delegate is None:
            raise AttributeError(name)
        controller_name, method_name = delegate
        return getattr(getattr(self, controller_name), method_name)

    @pyqtSlot()
    @pyqtSlot(bool)
    def show_workflow_settings_dialog(self, _checked: bool = False) -> None:
        self.project_session_controller.show_workflow_settings_dialog()

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
