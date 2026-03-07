from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Literal

from PyQt6.QtCore import QTimer, Qt, QUrl, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtQuick import QQuickWindow, QSGRendererInterface
from PyQt6.QtQuickWidgets import QQuickWidget
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMainWindow, QMessageBox

from ea_node_editor.execution.client import ProcessExecutionClient
from ea_node_editor.graph.model import GraphModel, NodeInstance, ProjectData
from ea_node_editor.graph.rules import (
    find_port,
    is_port_exposed,
    ports_compatible,
)
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import NodeTypeSpec
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.settings import (
    AUTOSAVE_INTERVAL_MS,
    DEFAULT_UI_STATE,
    DEFAULT_WORKFLOW_SETTINGS,
    autosave_project_path,
    recent_session_path,
)
from ea_node_editor.telemetry.system_metrics import read_system_metrics
from ea_node_editor.ui.dialogs.workflow_settings_dialog import WorkflowSettingsDialog
from ea_node_editor.ui.graph_interactions import GraphInteractions
from ea_node_editor.ui.shell.inspector_flow import coerce_editor_input_value
from ea_node_editor.ui.shell.library_flow import input_port_is_available, pick_connection_candidate
from ea_node_editor.ui.shell.project_flow import (
    coerce_timestamp,
    document_fingerprint,
    merge_defaults,
    write_json_atomic,
)
from ea_node_editor.ui.shell.run_flow import event_targets_active_run, run_action_state
from ea_node_editor.ui.shell.workspace_flow import build_workspace_tab_items, next_workspace_tab_index
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge
from ea_node_editor.ui_qml.console_model import ConsoleModel
from ea_node_editor.ui_qml.script_editor_model import ScriptEditorModel
from ea_node_editor.ui_qml.status_model import StatusItemModel
from ea_node_editor.ui_qml.workspace_tabs_model import WorkspaceTabsModel
from ea_node_editor.ui_qml.syntax_bridge import QmlScriptSyntaxBridge
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

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("EA Node Editor")
        self.resize(1600, 900)

        self.registry: NodeRegistry = build_default_registry()
        self.serializer = JsonProjectSerializer()
        self.model = GraphModel(ProjectData(project_id="proj_local", name="untitled"))
        self.workspace_manager = WorkspaceManager(self.model)
        self._ensure_project_metadata_defaults()

        self.project_path = ""
        self._library_query = ""
        self._library_category = ""
        self._library_data_type = ""
        self._library_direction = ""
        self._active_run_id = ""
        self._active_run_workspace_id = ""
        self._engine_state_value: Literal["ready", "running", "paused", "error"] = "ready"
        self._last_manual_save_ts = 0.0
        self._last_autosave_fingerprint = ""
        self._autosave_recovery_deferred = False

        self.scene = GraphSceneBridge(self)
        self.view = ViewportBridge(self)
        self._graph_interactions = GraphInteractions(scene=self.scene, registry=self.registry)
        self.console_panel = ConsoleModel(self)
        self.script_editor = ScriptEditorModel(self)
        self.script_highlighter = QmlScriptSyntaxBridge(self)
        self.workspace_tabs = WorkspaceTabsModel(self)
        self.status_engine = StatusItemModel("E", "Ready", self)
        self.status_jobs = StatusItemModel("J", "R:0 Q:0 D:0 F:0", self)
        self.status_metrics = StatusItemModel("M", "CPU:0% RAM:0/0 GB", self)
        self.status_notifications = StatusItemModel("N", "W:0 E:0", self)

        self.execution_client = ProcessExecutionClient()
        self.execution_client.subscribe(self.execution_event.emit)
        self.execution_event.connect(
            self._handle_execution_event,
            Qt.ConnectionType.QueuedConnection,
        )

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

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(AUTOSAVE_INTERVAL_MS)
        self.autosave_timer.timeout.connect(self._autosave_tick)
        self.autosave_timer.start()

        self._set_run_ui_state("ready", "Idle", 0, 0, 0, 0, clear_run=True)
        self._update_metrics()

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
            self.action_connect_selected,
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
        edit_menu.addAction(self.action_connect_selected)

        view_menu = menu_bar.addMenu("&View")
        view_menu.addAction(self.action_toggle_script_editor)

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

        qml_path = Path(__file__).resolve().parents[1] / "ui_qml" / "MainShell.qml"
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

    @pyqtProperty(str, notify=selected_node_changed)
    def selected_node_summary(self) -> str:
        selected = self._selected_node_context()
        if selected is None:
            return "No node selected"
        node, spec = selected
        return f"{spec.display_name}\nID: {node.node_id}\nType: {node.type_id}"

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
        created_node_id = self._insert_library_node(type_id, scene_x, scene_y)
        if not created_node_id:
            return False

        mode = str(target_mode).strip().lower()
        if mode == "port":
            self._auto_connect_dropped_node_to_port(
                created_node_id,
                str(target_node_id).strip(),
                str(target_port_key).strip(),
            )
        elif mode == "edge":
            self._auto_connect_dropped_node_to_edge(
                created_node_id,
                str(target_edge_id).strip(),
            )

        self._refresh_workspace_tabs()
        return True

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
        self._switch_view(target_id)

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

    @pyqtSlot()
    def request_connect_selected_nodes(self) -> None:
        self._connect_selected_nodes()

    @pyqtSlot(str, str, str, str, result=bool)
    def request_connect_ports(
        self,
        node_a_id: str,
        port_a: str,
        node_b_id: str,
        port_b: str,
    ) -> bool:
        result = self._graph_interactions.connect_ports(node_a_id, port_a, node_b_id, port_b)
        if result.ok:
            self._refresh_workspace_tabs()
        return result.ok

    @pyqtSlot(str, result=bool)
    def request_remove_edge(self, edge_id: str) -> bool:
        result = self._graph_interactions.remove_edge(edge_id)
        if result.ok:
            self._refresh_workspace_tabs()
        return result.ok

    @pyqtSlot(str, result=bool)
    def request_remove_node(self, node_id: str) -> bool:
        result = self._graph_interactions.remove_node(node_id)
        if result.ok:
            self.selected_node_changed.emit()
            self._refresh_workspace_tabs()
        return result.ok

    @pyqtSlot(str, result=bool)
    def request_rename_node(self, node_id: str) -> bool:
        workspace = self.model.project.workspaces.get(self.workspace_manager.active_workspace_id())
        if workspace is None:
            return False
        node = workspace.nodes.get(str(node_id).strip())
        if node is None:
            return False
        new_title, ok = QInputDialog.getText(self, "Rename Node", "New name:", text=node.title)
        if not ok:
            return False
        result = self._graph_interactions.rename_node(node.node_id, new_title)
        if result.ok:
            self.selected_node_changed.emit()
            self._refresh_workspace_tabs()
        return result.ok

    @pyqtSlot("QVariantList", result=bool)
    def request_delete_selected_graph_items(self, edge_ids: list[Any]) -> bool:
        result = self._graph_interactions.delete_selected_items(edge_ids)
        if result.ok:
            self.selected_node_changed.emit()
            self._refresh_workspace_tabs()
        return result.ok

    @pyqtSlot(str, "QVariant")
    def set_selected_node_property(self, key: str, value: Any) -> None:
        selected = self._selected_node_context()
        if selected is None:
            return
        node, spec = selected
        property_spec = next((prop for prop in spec.properties if prop.key == key), None)
        if property_spec is None:
            return
        coerced = coerce_editor_input_value(property_spec.type, value, property_spec.default)
        self._on_node_property_changed(node.node_id, property_spec.key, coerced)

    @pyqtSlot(str, bool)
    def set_selected_port_exposed(self, key: str, exposed: bool) -> None:
        selected = self._selected_node_context()
        if selected is None:
            return
        node, _spec = selected
        self._on_port_exposed_changed(node.node_id, str(key), bool(exposed))

    @pyqtSlot(bool)
    def set_selected_node_collapsed(self, collapsed: bool) -> None:
        selected = self._selected_node_context()
        if selected is None:
            return
        node, spec = selected
        if not spec.collapsible:
            return
        self._on_node_collapse_changed(node.node_id, bool(collapsed))

    def _ensure_project_metadata_defaults(self) -> None:
        metadata = self.model.project.metadata if isinstance(self.model.project.metadata, dict) else {}
        metadata["ui"] = merge_defaults(metadata.get("ui"), DEFAULT_UI_STATE)
        metadata["workflow_settings"] = merge_defaults(
            metadata.get("workflow_settings"),
            DEFAULT_WORKFLOW_SETTINGS,
        )
        self.model.project.metadata = metadata

    def _workflow_settings_payload(self) -> dict[str, Any]:
        self._ensure_project_metadata_defaults()
        return merge_defaults(
            self.model.project.metadata.get("workflow_settings", {}),
            DEFAULT_WORKFLOW_SETTINGS,
        )

    def _persist_script_editor_state(self) -> None:
        self._ensure_project_metadata_defaults()
        self.model.project.metadata["ui"]["script_editor"] = {
            "visible": self.script_editor.visible,
            "floating": self.script_editor.floating,
        }

    def _restore_script_editor_state(self) -> None:
        self._ensure_project_metadata_defaults()
        state = self.model.project.metadata["ui"].get("script_editor", {})
        selected_node_id = self.scene.selected_node_id() or ""
        can_show_editor = bool(selected_node_id)
        visible = bool(state.get("visible", False)) and can_show_editor
        floating = bool(state.get("floating", False))
        self.script_editor.set_floating(floating)
        self.script_editor.set_visible(visible)
        self.action_toggle_script_editor.setChecked(visible)

    def _switch_workspace_by_offset(self, offset: int) -> None:
        target = next_workspace_tab_index(
            self.workspace_tabs.count(),
            self.workspace_tabs.currentIndex(),
            offset,
        )
        if target is None:
            return
        self.workspace_tabs.setCurrentIndex(target)

    def _refresh_workspace_tabs(self) -> None:
        current_workspace = self.workspace_manager.active_workspace_id()
        tabs = build_workspace_tab_items(self.workspace_manager.list_workspaces())
        self.workspace_tabs.set_tabs(tabs, current_workspace)
        self.workspace_state_changed.emit()

    def _switch_workspace(self, workspace_id: str) -> None:
        self._save_active_view_state()
        if workspace_id not in self.model.project.workspaces:
            return
        self.workspace_manager.set_active_workspace(workspace_id)
        self.scene.set_workspace(self.model, self.registry, workspace_id)
        self._restore_active_view_state()
        self._refresh_workspace_tabs()
        self.script_editor.set_node(None)
        self.workspace_state_changed.emit()

    def _save_active_view_state(self) -> None:
        if not self.scene.workspace_id:
            return
        workspace = self.model.project.workspaces.get(self.scene.workspace_id)
        if workspace is None:
            return
        workspace.ensure_default_view()
        view_state = workspace.views.get(workspace.active_view_id)
        if view_state is None:
            workspace.active_view_id = next(iter(workspace.views))
            view_state = workspace.views[workspace.active_view_id]
        view_state.zoom = self.view.zoom
        center = self.view.mapToScene(self.view.viewport().rect().center())
        view_state.pan_x = center.x()
        view_state.pan_y = center.y()

    def _restore_active_view_state(self) -> None:
        workspace_id = self.workspace_manager.active_workspace_id()
        workspace = self.model.project.workspaces.get(workspace_id)
        if workspace is None:
            return
        workspace.ensure_default_view()
        view_state = workspace.views.get(workspace.active_view_id)
        if view_state is None:
            workspace.active_view_id = next(iter(workspace.views))
            view_state = workspace.views[workspace.active_view_id]
        self.view.set_zoom(max(0.1, min(3.0, view_state.zoom)))
        self.view.centerOn(view_state.pan_x, view_state.pan_y)

    def _create_view(self) -> None:
        workspace_id = self.workspace_manager.active_workspace_id()
        self._save_active_view_state()
        name, ok = QInputDialog.getText(self, "New View", "View name:")
        if not ok:
            return
        normalized_name = str(name).strip()
        view_id = self.workspace_manager.create_view(workspace_id, name=normalized_name or None)
        self.workspace_manager.set_active_view(workspace_id, view_id)
        self._restore_active_view_state()
        self.workspace_state_changed.emit()

    def _switch_view(self, view_id: str) -> None:
        workspace_id = self.workspace_manager.active_workspace_id()
        self._save_active_view_state()
        self.workspace_manager.set_active_view(workspace_id, view_id)
        self._restore_active_view_state()
        self.workspace_state_changed.emit()

    def _create_workspace(self) -> None:
        name, ok = QInputDialog.getText(self, "New Workspace", "Workspace name:")
        if not ok:
            return
        workspace_id = self.workspace_manager.create_workspace(name=name or None)
        self._refresh_workspace_tabs()
        self._switch_workspace(workspace_id)

    def _rename_active_workspace(self) -> None:
        index = self.workspace_tabs.currentIndex()
        if index < 0:
            return
        workspace_id = self.workspace_tabs.tabData(index)
        if not workspace_id:
            return
        workspace = self.model.project.workspaces[workspace_id]
        name, ok = QInputDialog.getText(self, "Rename Workspace", "New name:", text=workspace.name)
        if ok and name.strip():
            self.workspace_manager.rename_workspace(workspace_id, name.strip())
            self._refresh_workspace_tabs()

    def _duplicate_active_workspace(self) -> None:
        index = self.workspace_tabs.currentIndex()
        if index < 0:
            return
        workspace_id = self.workspace_tabs.tabData(index)
        if not workspace_id:
            return
        duplicated_id = self.workspace_manager.duplicate_workspace(workspace_id)
        self._refresh_workspace_tabs()
        self._switch_workspace(duplicated_id)

    def _close_active_workspace(self) -> None:
        index = self.workspace_tabs.currentIndex()
        if index >= 0:
            self._on_workspace_tab_close(index)

    def _on_workspace_tab_changed(self, index: int) -> None:
        if index < 0:
            return
        workspace_id = self.workspace_tabs.tabData(index)
        if workspace_id:
            self._switch_workspace(workspace_id)

    def _on_workspace_tab_close(self, index: int) -> None:
        workspace_id = self.workspace_tabs.tabData(index)
        if not workspace_id:
            return
        workspace = self.model.project.workspaces[workspace_id]
        if workspace.dirty:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                f"Workspace '{workspace.name}' has unsaved changes. Close anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        try:
            self.workspace_manager.close_workspace(workspace_id)
        except ValueError:
            QMessageBox.warning(self, "Workspace", "Cannot close the last workspace.")
            return
        self._refresh_workspace_tabs()
        self._switch_workspace(self.workspace_manager.active_workspace_id())

    def _add_node_from_library(self, type_id: str) -> None:
        center = self.view.mapToScene(self.view.viewport().rect().center())
        if self._insert_library_node(type_id, center.x(), center.y()):
            self._refresh_workspace_tabs()

    def _insert_library_node(self, type_id: str, x: float, y: float) -> str:
        normalized_type = str(type_id).strip()
        if not normalized_type:
            return ""
        try:
            return self.scene.add_node_from_type(normalized_type, x=float(x), y=float(y))
        except (KeyError, RuntimeError, ValueError):
            return ""

    def _active_workspace(self):
        workspace_id = self.workspace_manager.active_workspace_id()
        return self.model.project.workspaces.get(workspace_id)

    def _prompt_connection_candidate(
        self,
        *,
        title: str,
        label: str,
        candidates: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        return pick_connection_candidate(
            parent=self,
            title=title,
            label=label,
            candidates=candidates,
        )

    def _auto_connect_dropped_node_to_port(
        self,
        new_node_id: str,
        target_node_id: str,
        target_port_key: str,
    ) -> bool:
        workspace = self._active_workspace()
        if workspace is None:
            return False

        new_node = workspace.nodes.get(new_node_id)
        target_node = workspace.nodes.get(target_node_id)
        if new_node is None or target_node is None:
            return False

        new_spec = self.registry.get_spec(new_node.type_id)
        target_spec = self.registry.get_spec(target_node.type_id)
        target_port = find_port(target_spec, str(target_port_key).strip())
        if target_port is None:
            return False

        candidates: list[dict[str, Any]] = []
        if target_port.direction == "in":
            if not input_port_is_available(workspace, target_node.node_id, target_port.key):
                return False
            for port in new_spec.ports:
                if port.direction != "out" or not is_port_exposed(new_node, new_spec, port.key):
                    continue
                if not ports_compatible(port, target_port):
                    continue
                candidates.append(
                    {
                        "source_node_id": new_node.node_id,
                        "source_port_key": port.key,
                        "target_node_id": target_node.node_id,
                        "target_port_key": target_port.key,
                        "label": f"{new_spec.display_name}.{port.key} -> {target_spec.display_name}.{target_port.key}",
                    }
                )
        elif target_port.direction == "out":
            for port in new_spec.ports:
                if port.direction != "in" or not is_port_exposed(new_node, new_spec, port.key):
                    continue
                if not ports_compatible(target_port, port):
                    continue
                candidates.append(
                    {
                        "source_node_id": target_node.node_id,
                        "source_port_key": target_port.key,
                        "target_node_id": new_node.node_id,
                        "target_port_key": port.key,
                        "label": f"{target_spec.display_name}.{target_port.key} -> {new_spec.display_name}.{port.key}",
                    }
                )
        else:
            return False

        selected = self._prompt_connection_candidate(
            title="Auto-Connect Port",
            label="Choose connection:",
            candidates=candidates,
        )
        if selected is None:
            return False

        try:
            self.scene.add_edge(
                selected["source_node_id"],
                selected["source_port_key"],
                selected["target_node_id"],
                selected["target_port_key"],
            )
            return True
        except (KeyError, ValueError):
            return False

    def _auto_connect_dropped_node_to_edge(self, new_node_id: str, target_edge_id: str) -> bool:
        workspace = self._active_workspace()
        if workspace is None:
            return False
        edge = workspace.edges.get(target_edge_id)
        new_node = workspace.nodes.get(new_node_id)
        if edge is None or new_node is None:
            return False

        source_node = workspace.nodes.get(edge.source_node_id)
        target_node = workspace.nodes.get(edge.target_node_id)
        if source_node is None or target_node is None:
            return False

        source_spec = self.registry.get_spec(source_node.type_id)
        target_spec = self.registry.get_spec(target_node.type_id)
        new_spec = self.registry.get_spec(new_node.type_id)
        source_port = find_port(source_spec, str(edge.source_port_key).strip())
        target_port = find_port(target_spec, str(edge.target_port_key).strip())
        if source_port is None or target_port is None:
            return False

        candidate_inputs = [
            port
            for port in new_spec.ports
            if port.direction == "in"
            and is_port_exposed(new_node, new_spec, port.key)
            and ports_compatible(source_port, port)
        ]
        candidate_outputs = [
            port
            for port in new_spec.ports
            if port.direction == "out"
            and is_port_exposed(new_node, new_spec, port.key)
            and ports_compatible(port, target_port)
        ]

        candidates: list[dict[str, Any]] = []
        for input_port in candidate_inputs:
            for output_port in candidate_outputs:
                candidates.append(
                    {
                        "new_input_port": input_port.key,
                        "new_output_port": output_port.key,
                        "label": (
                            f"{source_spec.display_name}.{source_port.key} -> {new_spec.display_name}.{input_port.key}, "
                            f"{new_spec.display_name}.{output_port.key} -> {target_spec.display_name}.{target_port.key}"
                        ),
                    }
                )

        selected = self._prompt_connection_candidate(
            title="Auto-Insert On Edge",
            label="Choose inserted wiring:",
            candidates=candidates,
        )
        if selected is None:
            return False

        original = {
            "source_node_id": edge.source_node_id,
            "source_port_key": edge.source_port_key,
            "target_node_id": edge.target_node_id,
            "target_port_key": edge.target_port_key,
        }
        created_edge_ids: list[str] = []
        removed_original = False
        try:
            self.scene.remove_edge(target_edge_id)
            removed_original = True
            first_id = self.scene.add_edge(
                original["source_node_id"],
                original["source_port_key"],
                new_node_id,
                selected["new_input_port"],
            )
            created_edge_ids.append(first_id)
            second_id = self.scene.add_edge(
                new_node_id,
                selected["new_output_port"],
                original["target_node_id"],
                original["target_port_key"],
            )
            created_edge_ids.append(second_id)
            return True
        except (KeyError, ValueError):
            for edge_id in created_edge_ids:
                self.scene.remove_edge(edge_id)
            if removed_original:
                try:
                    self.scene.add_edge(
                        original["source_node_id"],
                        original["source_port_key"],
                        original["target_node_id"],
                        original["target_port_key"],
                    )
                except (KeyError, ValueError):
                    pass
            return False

    def _on_scene_node_selected(self, node_id: str) -> None:
        workspace = self.model.project.workspaces[self.workspace_manager.active_workspace_id()]
        node = workspace.nodes.get(node_id)
        self.script_editor.set_node(node)
        if self.script_editor.visible:
            self.script_editor.focus_editor()
        self.selected_node_changed.emit()

    def _on_node_property_changed(self, node_id: str, key: str, value: Any) -> None:
        self.scene.set_node_property(node_id, key, value)
        if key == "script" and self.script_editor.current_node_id == node_id:
            workspace = self.model.project.workspaces[self.workspace_manager.active_workspace_id()]
            self.script_editor.set_node(workspace.nodes.get(node_id))
        self.selected_node_changed.emit()
        self._refresh_workspace_tabs()

    def _on_port_exposed_changed(self, node_id: str, key: str, exposed: bool) -> None:
        self.scene.set_exposed_port(node_id, key, exposed)
        self.selected_node_changed.emit()
        self._refresh_workspace_tabs()

    def _on_node_collapse_changed(self, node_id: str, collapsed: bool) -> None:
        self.scene.set_node_collapsed(node_id, collapsed)
        self.selected_node_changed.emit()
        self._refresh_workspace_tabs()

    def _connect_selected_nodes(self) -> None:
        selected = [item for item in self.scene.selectedItems() if hasattr(item, "node")]
        if len(selected) != 2:
            QMessageBox.information(self, "Connect", "Select exactly two nodes to connect.")
            return
        first_item = selected[0]
        second_item = selected[1]
        try:
            self.scene.connect_nodes(first_item.node.node_id, second_item.node.node_id)
        except (KeyError, ValueError):
            QMessageBox.warning(self, "Connect", "No compatible ports found on selected nodes.")
            return
        self._refresh_workspace_tabs()

    @pyqtSlot()
    @pyqtSlot(bool)
    def show_workflow_settings_dialog(self, _checked: bool = False) -> None:
        self._ensure_project_metadata_defaults()
        dialog = WorkflowSettingsDialog(
            initial_settings=self.model.project.metadata.get("workflow_settings", {}),
            parent=self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        self.model.project.metadata["workflow_settings"] = dialog.values()
        self._persist_session()

    @pyqtSlot()
    @pyqtSlot(bool)
    def set_script_editor_panel_visible(self, checked: bool | None = None) -> None:
        target_visible = bool(checked) if checked is not None else not self.script_editor.visible
        self.script_editor.set_visible(target_visible)
        self.action_toggle_script_editor.setChecked(target_visible)
        self._persist_script_editor_state()
        if target_visible:
            node_id = self.scene.selected_node_id()
            if node_id:
                workspace = self.model.project.workspaces[self.workspace_manager.active_workspace_id()]
                self.script_editor.set_node(workspace.nodes.get(node_id))
            self.script_editor.focus_editor()

    def _selected_node_context(self) -> tuple[NodeInstance, NodeTypeSpec] | None:
        node_id = self.scene.selected_node_id()
        if not node_id:
            return None
        workspace = self.model.project.workspaces.get(self.active_workspace_id)
        if workspace is None:
            return None
        node = workspace.nodes.get(node_id)
        if node is None:
            return None
        spec = self.registry.get_spec(node.type_id)
        return node, spec

    def _run_workflow(self) -> None:
        if self._active_run_id:
            if self._engine_state_value == "paused":
                self._resume_workflow()
            else:
                self.console_panel.append_log("warning", "A workflow run is already active.")
                self.update_notification_counters(self.console_panel.warning_count, self.console_panel.error_count)
            return

        workspace_id = self.workspace_manager.active_workspace_id()
        document = self.serializer.to_document(self.model.project)
        trigger = {
            "kind": "manual",
            "workflow_settings": self._workflow_settings_payload(),
            "project_doc": document,
        }
        self.console_panel.clear_all()
        run_id = self.execution_client.start_run(
            project_path=self.project_path,
            workspace_id=workspace_id,
            trigger=trigger,
        )
        if not run_id:
            self.console_panel.append_log("error", "Failed to start workflow run.")
            self.update_notification_counters(self.console_panel.warning_count, self.console_panel.error_count)
            self._set_run_ui_state("error", "Start Failed", 0, 0, 0, 1, clear_run=True)
            return
        self._active_run_id = run_id
        self._active_run_workspace_id = workspace_id
        self._set_run_ui_state("running", "Starting", 1, 0, 0, 0)

    def _toggle_pause_resume(self) -> None:
        if not self._active_run_id:
            return
        if self._engine_state_value == "paused":
            self._resume_workflow()
        elif self._engine_state_value == "running":
            self._pause_workflow()

    def _pause_workflow(self) -> None:
        if not self._active_run_id or self._engine_state_value != "running":
            return
        self.execution_client.pause_run(self._active_run_id)
        self.update_engine_status("running", "Pausing")

    def _resume_workflow(self) -> None:
        if not self._active_run_id or self._engine_state_value != "paused":
            return
        self.execution_client.resume_run(self._active_run_id)
        self.update_engine_status("running", "Resuming")

    def _stop_workflow(self) -> None:
        if not self._active_run_id:
            return
        self.execution_client.stop_run(self._active_run_id)
        if self._engine_state_value == "paused":
            self.update_engine_status("paused", "Stopping")
        else:
            self.update_engine_status("running", "Stopping")
        self._update_run_actions()

    def _handle_execution_event(self, event: dict) -> None:
        event_type = str(event.get("type", ""))
        if not event_targets_active_run(
            event,
            active_run_id=self._active_run_id,
            run_scoped_event_types=self._RUN_SCOPED_EVENT_TYPES,
        ):
            return

        if event_type in {"run_started", "node_started", "node_completed"}:
            self._set_run_ui_state("running", "Running", 1, 0, 0, 0)

        if event_type == "log":
            self.console_panel.append_log(event.get("level", "info"), event.get("message", ""))
            self.update_notification_counters(self.console_panel.warning_count, self.console_panel.error_count)
        elif event_type == "run_completed":
            self._set_run_ui_state("ready", "Completed", 0, 0, 1, 0, clear_run=True)
        elif event_type == "run_failed":
            self._set_run_ui_state("error", "Failed", 0, 0, 0, 1)
            self.console_panel.append_log("error", event.get("error", "Unknown failure"))
            self.console_panel.append_log("error", event.get("traceback", ""))
            self.update_notification_counters(self.console_panel.warning_count, self.console_panel.error_count)
            self._focus_failed_node(event.get("workspace_id", ""), event.get("node_id", ""), event.get("error", ""))
            self._clear_active_run()
            self._update_run_actions()
        elif event_type == "run_stopped":
            self._set_run_ui_state("ready", "Stopped", 0, 0, 0, 0, clear_run=True)
        elif event_type == "run_state":
            state = event.get("state", "ready")
            transition = str(event.get("transition", ""))
            if state == "paused" or transition == "pause":
                self._set_run_ui_state("paused", "Paused", 1, 0, 0, 0)
            elif state == "running":
                self._set_run_ui_state("running", "Running", 1, 0, 0, 0)
            elif transition == "stop":
                self._set_run_ui_state("ready", "Stopped", 0, 0, 0, 0, clear_run=True)
            elif state == "error":
                self._set_run_ui_state("error", "Failed", 0, 0, 0, 1)
        elif event_type == "protocol_error":
            self.console_panel.append_log("error", event.get("error", "Execution protocol error."))
            self.update_notification_counters(self.console_panel.warning_count, self.console_panel.error_count)

    def _clear_active_run(self) -> None:
        self._active_run_id = ""
        self._active_run_workspace_id = ""

    def _set_run_ui_state(
        self,
        state: Literal["ready", "running", "paused", "error"],
        details: str,
        running: int,
        queued: int,
        done: int,
        failed: int,
        *,
        clear_run: bool = False,
    ) -> None:
        self._engine_state_value = state
        self.update_engine_status(state, details)
        self.update_job_counters(running, queued, done, failed)
        if clear_run:
            self._clear_active_run()
        self._update_run_actions()

    def _update_run_actions(self) -> None:
        can_pause, pause_label = run_action_state(self._active_run_id, self._engine_state_value)
        self.action_stop.setEnabled(True)
        self.action_pause.setEnabled(can_pause)
        self.action_pause.setText(pause_label)

    def _focus_failed_node(self, workspace_id: str, node_id: str, error: str) -> None:
        if workspace_id and workspace_id != self.workspace_manager.active_workspace_id():
            self._switch_workspace(workspace_id)

        focus_candidates: list[str] = []
        if node_id:
            focus_candidates.append(node_id)
        focus_candidates.extend(self._reveal_parent_chain(workspace_id, node_id))

        center = None
        for target_node_id in focus_candidates:
            center = self.scene.focus_node(target_node_id)
            if center is not None:
                break
        if center is not None:
            self.view.centerOn(center)
        if error:
            QMessageBox.critical(self, "Workflow Error", error)

    def _reveal_parent_chain(self, workspace_id: str, node_id: str) -> list[str]:
        if not workspace_id or not node_id:
            return []
        workspace = self.model.project.workspaces.get(workspace_id)
        if workspace is None:
            return []
        node = workspace.nodes.get(node_id)
        if node is None:
            return []

        chain: list[str] = []
        seen: set[str] = set()
        parent_id = node.parent_node_id
        while parent_id and parent_id not in seen:
            seen.add(parent_id)
            parent_node = workspace.nodes.get(parent_id)
            if parent_node is None:
                break
            chain.append(parent_id)
            parent_id = parent_node.parent_node_id

        for candidate_id in reversed(chain):
            parent_node = workspace.nodes.get(candidate_id)
            if parent_node is not None and parent_node.collapsed:
                self.scene.set_node_collapsed(candidate_id, False)
        return chain

    def _save_project(self) -> None:
        path = self.project_path
        if not path:
            path, _ = QFileDialog.getSaveFileName(self, "Save Project", "", "EA Project (*.sfe)")
        if not path:
            return
        self._save_active_view_state()
        self.serializer.save(path, self.model.project)
        saved_path = Path(path).with_suffix(".sfe")
        self.project_path = str(saved_path)
        try:
            self._last_manual_save_ts = saved_path.stat().st_mtime
        except OSError:
            self._last_manual_save_ts = time.time()
        for workspace in self.model.project.workspaces.values():
            workspace.dirty = False
        self._refresh_workspace_tabs()
        self._discard_autosave_snapshot()
        self._last_autosave_fingerprint = document_fingerprint(
            self.serializer.to_document(self.model.project)
        )
        self._persist_session()
        self.project_meta_changed.emit()

    def _new_project(self) -> None:
        self.model = GraphModel(ProjectData(project_id="proj_local", name="untitled"))
        self.workspace_manager = WorkspaceManager(self.model)
        self._ensure_project_metadata_defaults()
        self.project_path = ""
        self._last_manual_save_ts = 0.0
        self._discard_autosave_snapshot()
        self._last_autosave_fingerprint = document_fingerprint(
            self.serializer.to_document(self.model.project)
        )
        self._refresh_workspace_tabs()
        self._switch_workspace(self.workspace_manager.active_workspace_id())
        self._restore_script_editor_state()
        self._persist_session()
        self.project_meta_changed.emit()

    def _open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "EA Project (*.sfe)")
        if not path:
            return
        try:
            project = self.serializer.load(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Open Project", f"Could not open project file.\\n{exc}")
            return
        resolved_path = Path(path).with_suffix(".sfe")
        self.model = GraphModel(project)
        self.workspace_manager = WorkspaceManager(self.model)
        self._ensure_project_metadata_defaults()
        self.project_path = str(resolved_path)
        try:
            self._last_manual_save_ts = resolved_path.stat().st_mtime
        except OSError:
            self._last_manual_save_ts = time.time()
        self._discard_autosave_snapshot()
        self._last_autosave_fingerprint = document_fingerprint(
            self.serializer.to_document(self.model.project)
        )
        self._refresh_workspace_tabs()
        self._switch_workspace(self.workspace_manager.active_workspace_id())
        self._restore_script_editor_state()
        self._persist_session()
        self.project_meta_changed.emit()

    def _restore_session(self) -> None:
        session = self._load_session_payload()
        session_project_path = str(session.get("project_path", "")).strip()
        self._last_manual_save_ts = coerce_timestamp(session.get("last_manual_save_ts", 0.0))

        restored = False
        if session_project_path and Path(session_project_path).exists():
            try:
                project = self.serializer.load(session_project_path)
                self.model = GraphModel(project)
                self.workspace_manager = WorkspaceManager(self.model)
                self.project_path = session_project_path
                self._last_manual_save_ts = max(
                    self._last_manual_save_ts,
                    Path(session_project_path).stat().st_mtime,
                )
                restored = True
            except Exception:  # noqa: BLE001
                self.project_path = ""

        if not restored:
            doc = session.get("project_doc")
            if isinstance(doc, dict):
                try:
                    project = self.serializer.from_document(doc)
                    self.model = GraphModel(project)
                    self.workspace_manager = WorkspaceManager(self.model)
                    self.project_path = ""
                    restored = True
                except Exception:  # noqa: BLE001
                    self.project_path = ""

        recovered_project = self._recover_autosave_if_newer()
        if recovered_project is not None:
            self.model = GraphModel(recovered_project)
            self.workspace_manager = WorkspaceManager(self.model)
            self.project_path = session_project_path if Path(session_project_path).exists() else ""
            restored = True

        if not restored:
            self.project_path = ""

        self._ensure_project_metadata_defaults()
        self._last_autosave_fingerprint = document_fingerprint(
            self.serializer.to_document(self.model.project)
        )
        self.project_meta_changed.emit()

    def _load_session_payload(self) -> dict[str, Any]:
        session_path = recent_session_path()
        if not session_path.exists():
            return {}
        try:
            payload = json.loads(session_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}
        return payload if isinstance(payload, dict) else {}

    def _discard_autosave_snapshot(self) -> None:
        try:
            autosave_path = autosave_project_path()
            if autosave_path.exists():
                autosave_path.unlink()
        except OSError:
            pass
        self._last_autosave_fingerprint = ""

    def _recover_autosave_if_newer(self) -> ProjectData | None:
        autosave_path = autosave_project_path()
        if not autosave_path.exists():
            return None

        try:
            autosave_ts = autosave_path.stat().st_mtime
        except OSError:
            return None

        manual_save_ts = self._last_manual_save_ts
        if self.project_path and Path(self.project_path).exists():
            try:
                manual_save_ts = max(manual_save_ts, Path(self.project_path).stat().st_mtime)
            except OSError:
                pass
        if autosave_ts <= manual_save_ts:
            return None

        try:
            recovered_project = self.serializer.load(str(autosave_path))
        except Exception:  # noqa: BLE001
            self._discard_autosave_snapshot()
            return None

        # If session restore already yielded the same document, autosave recovery is redundant.
        current_doc = self.serializer.to_document(self.model.project)
        recovered_doc = self.serializer.to_document(recovered_project)
        if document_fingerprint(current_doc) == document_fingerprint(recovered_doc):
            self._discard_autosave_snapshot()
            return None

        if not self.isVisible():
            self._autosave_recovery_deferred = True
            return None

        choice = self._prompt_recover_autosave()
        if choice != QMessageBox.StandardButton.Yes:
            self._discard_autosave_snapshot()
            return None

        self._discard_autosave_snapshot()
        return recovered_project

    def _prompt_recover_autosave(self) -> QMessageBox.StandardButton:
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Question)
        dialog.setWindowTitle("Recover Autosave")
        dialog.setText("A newer autosave snapshot is available. Recover it?")
        dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        dialog.setDefaultButton(QMessageBox.StandardButton.Yes)
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        return QMessageBox.StandardButton(dialog.exec())

    def _process_deferred_autosave_recovery(self) -> None:
        if not self._autosave_recovery_deferred:
            return
        self._autosave_recovery_deferred = False
        recovered_project = self._recover_autosave_if_newer()
        if recovered_project is None:
            return
        self.model = GraphModel(recovered_project)
        self.workspace_manager = WorkspaceManager(self.model)
        self._ensure_project_metadata_defaults()
        self._refresh_workspace_tabs()
        self._switch_workspace(self.workspace_manager.active_workspace_id())
        self._restore_script_editor_state()
        self._last_autosave_fingerprint = document_fingerprint(
            self.serializer.to_document(self.model.project)
        )
        self._persist_session()

    def _autosave_tick(self) -> None:
        try:
            self._save_active_view_state()
            project_doc = self.serializer.to_document(self.model.project)
            fingerprint = document_fingerprint(project_doc)
            if fingerprint == self._last_autosave_fingerprint:
                return
            write_json_atomic(autosave_project_path(), project_doc)
            self._last_autosave_fingerprint = fingerprint
            self._persist_session(project_doc=project_doc)
        except Exception:  # noqa: BLE001
            return

    def _persist_session(self, project_doc: dict[str, Any] | None = None) -> None:
        self._save_active_view_state()
        self._persist_script_editor_state()
        document = project_doc if isinstance(project_doc, dict) else self.serializer.to_document(self.model.project)
        session = {
            "project_path": self.project_path,
            "last_manual_save_ts": self._last_manual_save_ts,
            "project_doc": document,
        }
        try:
            write_json_atomic(recent_session_path(), session)
        except Exception:  # noqa: BLE001
            return

    def _update_metrics(self) -> None:
        metrics = read_system_metrics()
        self.update_system_metrics(metrics.cpu_percent, metrics.ram_used_gb, metrics.ram_total_gb)

    def _open_logs(self) -> None:
        return

    def _import_node_package(self) -> None:
        from ea_node_editor.nodes.package_manager import import_package
        from ea_node_editor.nodes.plugin_loader import discover_and_load_plugins

        path, _ = QFileDialog.getOpenFileName(
            self, "Import Node Package", "", "Node Package (*.eanp)"
        )
        if not path:
            return
        try:
            manifest = import_package(Path(path))
            discover_and_load_plugins(self.registry)
            self.node_library_changed.emit()
            QMessageBox.information(
                self,
                "Import Successful",
                f"Installed '{manifest.name}' v{manifest.version} "
                f"with {len(manifest.nodes)} node(s).\n\n"
                "The nodes are now available in the Node Library.",
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Import Failed", f"Could not import package.\n{exc}")

    def _export_node_package(self) -> None:
        from ea_node_editor.nodes.package_manager import PackageManifest, export_package

        name, ok = QInputDialog.getText(self, "Export Node Package", "Package name:")
        if not ok or not name.strip():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Node Package", f"{name.strip()}.eanp", "Node Package (*.eanp)"
        )
        if not path:
            return
        manifest = PackageManifest(
            name=name.strip(),
            nodes=[spec.type_id for spec in self.registry.all_specs()],
        )
        try:
            export_package([], manifest, Path(path))
            QMessageBox.information(
                self, "Export Successful", f"Package saved to {path}"
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Export Failed", f"Could not export package.\n{exc}")

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

    # Main window API contract
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
