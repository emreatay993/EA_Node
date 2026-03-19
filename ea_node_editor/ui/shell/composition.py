from __future__ import annotations

from dataclasses import dataclass, fields
from typing import TYPE_CHECKING

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtQuickWidgets import QQuickWidget
from PyQt6.QtWidgets import QMessageBox

from ea_node_editor.graph.model import GraphModel, ProjectData
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.settings import AUTOSAVE_INTERVAL_MS, DEFAULT_GRAPHICS_SETTINGS
from ea_node_editor.telemetry.frame_rate import FrameRateSampler
from ea_node_editor.ui.graph_interactions import GraphInteractions
from ea_node_editor.ui.graph_theme import default_graph_theme_id_for_shell_theme
from ea_node_editor.ui.icon_registry import UiIconImageProvider, UiIconRegistryBridge
from ea_node_editor.ui.media_preview_provider import LocalMediaPreviewImageProvider
from ea_node_editor.ui.pdf_preview_provider import LocalPdfPreviewImageProvider
from ea_node_editor.ui.shell.controllers import (
    AppPreferencesController,
    ProjectSessionController,
    RunController,
    WorkspaceLibraryController,
)
from ea_node_editor.ui.shell.presenters import (
    GraphCanvasPresenter,
    ShellInspectorPresenter,
    ShellLibraryPresenter,
    ShellWorkspacePresenter,
    build_default_shell_workspace_ui_state,
)
from ea_node_editor.ui.shell.runtime_history import RuntimeGraphHistory
from ea_node_editor.ui.shell.state import ShellState
from ea_node_editor.ui.shell.window_search_scope_state import WindowSearchScopeController
from ea_node_editor.ui_qml.console_model import ConsoleModel
from ea_node_editor.ui_qml.graph_canvas_bridge import GraphCanvasBridge
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

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow


@dataclass(frozen=True, slots=True)
class _ShellStateBundle:
    state: ShellState
    project_session_state: object
    library_filter_state: object
    run_state: object
    search_scope_state: object
    workspace_ui_state: object


@dataclass(frozen=True, slots=True)
class _ShellPrimitiveBundle:
    registry: object
    serializer: JsonProjectSerializer
    _session_store: object
    session_store: object
    model: GraphModel
    workspace_manager: WorkspaceManager
    runtime_history: RuntimeGraphHistory
    scene: GraphSceneBridge
    view: ViewportBridge
    _graph_interactions: GraphInteractions
    graph_interactions: GraphInteractions
    console_panel: ConsoleModel
    script_editor: ScriptEditorModel
    script_highlighter: QmlScriptSyntaxBridge
    workspace_tabs: WorkspaceTabsModel
    ui_icons: UiIconRegistryBridge
    _ui_icon_image_provider: UiIconImageProvider
    _local_media_preview_provider: LocalMediaPreviewImageProvider
    _local_pdf_preview_provider: LocalPdfPreviewImageProvider
    status_engine: StatusItemModel
    status_jobs: StatusItemModel
    status_metrics: StatusItemModel
    status_notifications: StatusItemModel
    _frame_rate_sampler: FrameRateSampler
    theme_bridge: ThemeBridge
    graph_theme_bridge: GraphThemeBridge


@dataclass(frozen=True, slots=True)
class _ShellControllerBundle:
    search_scope_controller: WindowSearchScopeController
    workspace_library_controller: WorkspaceLibraryController
    project_session_controller: ProjectSessionController
    run_controller: RunController
    app_preferences_controller: AppPreferencesController
    execution_client: object


@dataclass(frozen=True, slots=True)
class _ShellPresenterBundle:
    shell_library_presenter: ShellLibraryPresenter
    shell_workspace_presenter: ShellWorkspacePresenter
    shell_inspector_presenter: ShellInspectorPresenter
    graph_canvas_presenter: GraphCanvasPresenter


@dataclass(frozen=True, slots=True)
class _ShellContextBridgeBundle:
    _shell_context_bridges: ShellContextBridges
    shell_library_bridge: ShellLibraryBridge
    shell_workspace_bridge: ShellWorkspaceBridge
    shell_inspector_bridge: ShellInspectorBridge
    graph_canvas_bridge: GraphCanvasBridge


@dataclass(frozen=True, slots=True)
class _ShellTimerBundle:
    metrics_timer: QTimer
    graph_hint_timer: QTimer
    autosave_timer: QTimer


@dataclass(frozen=True, slots=True)
class _ShellWindowComposition:
    state: _ShellStateBundle
    primitives: _ShellPrimitiveBundle
    controllers: _ShellControllerBundle
    presenters: _ShellPresenterBundle
    context_bridges: _ShellContextBridgeBundle


def create_shell_window() -> "ShellWindow":
    from ea_node_editor.ui.shell.window import ShellWindow

    host = ShellWindow(_defer_bootstrap=True)
    composition = build_shell_window_composition(host)
    bootstrap_shell_window(host, composition)
    return host


def build_shell_window_composition(host: "ShellWindow") -> _ShellWindowComposition:
    state_bundle = _create_shell_state_bundle()
    _apply_bootstrap_bundle(host, state_bundle)

    primitive_bundle = _create_shell_primitive_bundle(host)
    _apply_bootstrap_bundle(host, primitive_bundle)

    controller_bundle = _create_shell_controller_bundle(host)
    _apply_bootstrap_bundle(host, controller_bundle)

    presenter_bundle = _create_shell_presenter_bundle(host)
    _apply_bootstrap_bundle(host, presenter_bundle)

    context_bridge_bundle = _create_shell_context_bridge_bundle(host)

    return _ShellWindowComposition(
        state=state_bundle,
        primitives=primitive_bundle,
        controllers=controller_bundle,
        presenters=presenter_bundle,
        context_bridges=context_bridge_bundle,
    )


def bootstrap_shell_window(host: "ShellWindow", composition: _ShellWindowComposition) -> None:
    _configure_shell_window_host(host)
    _apply_bootstrap_bundle(host, composition.state)
    _apply_bootstrap_bundle(host, composition.primitives)
    _apply_bootstrap_bundle(host, composition.controllers)
    _apply_bootstrap_bundle(host, composition.presenters)
    _apply_bootstrap_bundle(host, composition.context_bridges)
    _run_shell_startup_sequence(host)
    _apply_bootstrap_bundle(host, _create_shell_timer_bundle(host))
    _finalize_shell_window_bootstrap(host)


def _configure_shell_window_host(host: "ShellWindow") -> None:
    host.setWindowTitle("EA Node Editor")
    host.resize(1600, 900)


def _create_shell_state_bundle() -> _ShellStateBundle:
    state = ShellState()
    project_session_state = state.project_session
    library_filter_state = state.library_filters
    run_state = state.run
    search_scope_state = state.search_scope

    graphics_settings = DEFAULT_GRAPHICS_SETTINGS
    workspace_ui_state = build_default_shell_workspace_ui_state(graphics_settings)
    search_scope_state.graphics_minimap_expanded = bool(graphics_settings["canvas"]["minimap_expanded"])
    search_scope_state.snap_to_grid_enabled = bool(graphics_settings["interaction"]["snap_to_grid"])

    return _ShellStateBundle(
        state=state,
        project_session_state=project_session_state,
        library_filter_state=library_filter_state,
        run_state=run_state,
        search_scope_state=search_scope_state,
        workspace_ui_state=workspace_ui_state,
    )


def _create_shell_primitive_bundle(host: "ShellWindow") -> _ShellPrimitiveBundle:
    registry = build_default_registry()
    serializer = JsonProjectSerializer(registry)
    session_store = host._create_session_store(serializer)
    model = GraphModel(ProjectData(project_id="proj_local", name="untitled"))
    workspace_manager = WorkspaceManager(model)
    runtime_history = RuntimeGraphHistory()
    scene = GraphSceneBridge(host)
    scene.bind_runtime_history(runtime_history)
    view = ViewportBridge(host)
    graph_interactions = GraphInteractions(
        scene=scene,
        registry=registry,
        history=runtime_history,
    )
    console_panel = ConsoleModel(host)
    script_editor = ScriptEditorModel(host)
    script_highlighter = QmlScriptSyntaxBridge(host)
    workspace_tabs = WorkspaceTabsModel(host)
    ui_icons = UiIconRegistryBridge(host)
    ui_icon_image_provider = UiIconImageProvider()
    local_media_preview_provider = LocalMediaPreviewImageProvider()
    local_pdf_preview_provider = LocalPdfPreviewImageProvider()
    status_engine = StatusItemModel("E", "Ready", host)
    status_jobs = StatusItemModel("J", "R:0 Q:0 D:0 F:0", host)
    status_metrics = StatusItemModel("M", "FPS:0 CPU:0% RAM:0/0 GB", host)
    status_notifications = StatusItemModel("N", "W:0 E:0", host)
    frame_rate_sampler = FrameRateSampler()
    theme_bridge = ThemeBridge(host, theme_id=host.workspace_ui_state.active_theme_id)
    graph_theme_bridge = GraphThemeBridge(
        host,
        theme_id=default_graph_theme_id_for_shell_theme(host.workspace_ui_state.active_theme_id),
    )
    scene.bind_graph_theme_bridge(graph_theme_bridge)
    return _ShellPrimitiveBundle(
        registry=registry,
        serializer=serializer,
        _session_store=session_store,
        session_store=session_store,
        model=model,
        workspace_manager=workspace_manager,
        runtime_history=runtime_history,
        scene=scene,
        view=view,
        _graph_interactions=graph_interactions,
        graph_interactions=graph_interactions,
        console_panel=console_panel,
        script_editor=script_editor,
        script_highlighter=script_highlighter,
        workspace_tabs=workspace_tabs,
        ui_icons=ui_icons,
        _ui_icon_image_provider=ui_icon_image_provider,
        _local_media_preview_provider=local_media_preview_provider,
        _local_pdf_preview_provider=local_pdf_preview_provider,
        status_engine=status_engine,
        status_jobs=status_jobs,
        status_metrics=status_metrics,
        status_notifications=status_notifications,
        _frame_rate_sampler=frame_rate_sampler,
        theme_bridge=theme_bridge,
        graph_theme_bridge=graph_theme_bridge,
    )


def _create_shell_controller_bundle(host: "ShellWindow") -> _ShellControllerBundle:
    search_scope_controller = WindowSearchScopeController(host, host.search_scope_state)
    workspace_library_controller = WorkspaceLibraryController(host)
    project_session_controller = ProjectSessionController(host)
    run_controller = RunController(host)
    app_preferences_controller = AppPreferencesController()
    execution_client = host._create_execution_client()
    execution_client.subscribe(host.execution_event.emit)
    host.execution_event.connect(host._handle_execution_event, Qt.ConnectionType.QueuedConnection)
    return _ShellControllerBundle(
        search_scope_controller=search_scope_controller,
        workspace_library_controller=workspace_library_controller,
        project_session_controller=project_session_controller,
        run_controller=run_controller,
        app_preferences_controller=app_preferences_controller,
        execution_client=execution_client,
    )


def _create_shell_presenter_bundle(host: "ShellWindow") -> _ShellPresenterBundle:
    shell_library_presenter = ShellLibraryPresenter(host)
    shell_workspace_presenter = ShellWorkspacePresenter(host)
    shell_inspector_presenter = ShellInspectorPresenter(host)
    graph_canvas_presenter = GraphCanvasPresenter(
        host,
        workspace_presenter=shell_workspace_presenter,
        library_presenter=shell_library_presenter,
        inspector_presenter=shell_inspector_presenter,
    )
    return _ShellPresenterBundle(
        shell_library_presenter=shell_library_presenter,
        shell_workspace_presenter=shell_workspace_presenter,
        shell_inspector_presenter=shell_inspector_presenter,
        graph_canvas_presenter=graph_canvas_presenter,
    )


def _create_shell_context_bridge_bundle(host: "ShellWindow") -> _ShellContextBridgeBundle:
    shell_context_bridges = create_shell_context_bridges(host)
    return _ShellContextBridgeBundle(
        _shell_context_bridges=shell_context_bridges,
        shell_library_bridge=shell_context_bridges.shell_library_bridge,
        shell_workspace_bridge=shell_context_bridges.shell_workspace_bridge,
        shell_inspector_bridge=shell_context_bridges.shell_inspector_bridge,
        graph_canvas_bridge=shell_context_bridges.graph_canvas_bridge,
    )


def _run_shell_startup_sequence(host: "ShellWindow") -> None:
    host._create_actions()
    host._build_menu_bar()
    host.app_preferences_controller.load_into_host(host)
    host._wire_signals()
    host.quick_widget = _build_shell_qml_widget(host)
    host._restore_session()
    host._ensure_project_metadata_defaults()
    host._refresh_workspace_tabs()
    host._switch_workspace(host.workspace_manager.active_workspace_id())
    host._restore_script_editor_state()


def _build_shell_qml_widget(host: "ShellWindow") -> QQuickWidget:
    widget = QQuickWidget(host)
    bootstrap_shell_qml_context(host, widget, host._shell_context_bridges)
    if widget.status() == QQuickWidget.Status.Error:
        formatted_errors = "\n".join(error.toString() for error in widget.errors()).strip()
        message = formatted_errors or "Unknown QML load error."
        host.console_panel.append_log("error", f"Failed to load MainShell.qml.\n{message}")
        QMessageBox.critical(host, "UI Load Error", f"Could not load the main UI.\n\n{message}")
    host.setCentralWidget(widget)
    return widget


def _create_shell_timer_bundle(host: "ShellWindow") -> _ShellTimerBundle:
    metrics_timer = QTimer(host)
    metrics_timer.setInterval(1000)
    metrics_timer.timeout.connect(host._update_metrics)
    metrics_timer.start()

    graph_hint_timer = QTimer(host)
    graph_hint_timer.setSingleShot(True)
    graph_hint_timer.timeout.connect(host.clear_graph_hint)

    autosave_timer = QTimer(host)
    autosave_timer.setInterval(AUTOSAVE_INTERVAL_MS)
    autosave_timer.timeout.connect(host._autosave_tick)
    autosave_timer.start()

    return _ShellTimerBundle(
        metrics_timer=metrics_timer,
        graph_hint_timer=graph_hint_timer,
        autosave_timer=autosave_timer,
    )


def _finalize_shell_window_bootstrap(host: "ShellWindow") -> None:
    host._set_run_ui_state("ready", "Idle", 0, 0, 0, 0, clear_run=True)
    host._update_metrics()


def _apply_bootstrap_bundle(host: "ShellWindow", bundle: object) -> None:
    for field in fields(bundle):
        setattr(host, field.name, getattr(bundle, field.name))

