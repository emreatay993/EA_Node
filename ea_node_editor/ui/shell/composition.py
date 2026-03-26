from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtQuickWidgets import QQuickWidget
from PyQt6.QtWidgets import QMessageBox

from ea_node_editor.graph.model import GraphModel, ProjectData
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.settings import AUTOSAVE_INTERVAL_MS, DEFAULT_GRAPHICS_SETTINGS
from ea_node_editor.telemetry.frame_rate import FrameRateSampler
from ea_node_editor.ui.app_icon import apply_window_icon
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
from ea_node_editor.ui.shell.host_presenter import ShellHostPresenter
from ea_node_editor.ui.shell.context_bridges import (
    ShellContextBridges,
    create_shell_context_bridges,
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
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge
from ea_node_editor.ui_qml.script_editor_model import ScriptEditorModel
from ea_node_editor.ui_qml.shell_context_bootstrap import bootstrap_shell_qml_context
from ea_node_editor.ui_qml.status_model import StatusItemModel
from ea_node_editor.ui_qml.syntax_bridge import QmlScriptSyntaxBridge
from ea_node_editor.ui_qml.theme_bridge import ThemeBridge
from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge
from ea_node_editor.ui_qml.workspace_tabs_model import WorkspaceTabsModel
from ea_node_editor.workspace.manager import WorkspaceManager

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow


@dataclass(frozen=True, slots=True)
class ShellStateDependencies:
    state: ShellState
    project_session_state: object
    library_filter_state: object
    run_state: object
    search_scope_state: object
    workspace_ui_state: object

    def attach(self, host: "ShellWindow") -> None:
        host.state = self.state
        host.project_session_state = self.project_session_state
        host.library_filter_state = self.library_filter_state
        host.run_state = self.run_state
        host.search_scope_state = self.search_scope_state
        host.workspace_ui_state = self.workspace_ui_state


@dataclass(frozen=True, slots=True)
class ShellPrimitiveDependencies:
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

    def attach(self, host: "ShellWindow") -> None:
        host.registry = self.registry
        host.serializer = self.serializer
        host._session_store = self._session_store
        host.session_store = self.session_store
        host.model = self.model
        host.workspace_manager = self.workspace_manager
        host.runtime_history = self.runtime_history
        host.scene = self.scene
        host.view = self.view
        host._graph_interactions = self._graph_interactions
        host.graph_interactions = self.graph_interactions
        host.console_panel = self.console_panel
        host.script_editor = self.script_editor
        host.script_highlighter = self.script_highlighter
        host.workspace_tabs = self.workspace_tabs
        host.ui_icons = self.ui_icons
        host._ui_icon_image_provider = self._ui_icon_image_provider
        host._local_media_preview_provider = self._local_media_preview_provider
        host._local_pdf_preview_provider = self._local_pdf_preview_provider
        host.status_engine = self.status_engine
        host.status_jobs = self.status_jobs
        host.status_metrics = self.status_metrics
        host.status_notifications = self.status_notifications
        host._frame_rate_sampler = self._frame_rate_sampler
        host.theme_bridge = self.theme_bridge
        host.graph_theme_bridge = self.graph_theme_bridge


@dataclass(frozen=True, slots=True)
class ShellControllerDependencies:
    search_scope_controller: WindowSearchScopeController
    workspace_library_controller: WorkspaceLibraryController
    project_session_controller: ProjectSessionController
    run_controller: RunController
    app_preferences_controller: AppPreferencesController
    execution_client: object

    def attach(self, host: "ShellWindow") -> None:
        host.search_scope_controller = self.search_scope_controller
        host.workspace_library_controller = self.workspace_library_controller
        host.project_session_controller = self.project_session_controller
        host.run_controller = self.run_controller
        host.app_preferences_controller = self.app_preferences_controller
        host.execution_client = self.execution_client


@dataclass(frozen=True, slots=True)
class ShellPresenterDependencies:
    shell_host_presenter: ShellHostPresenter
    shell_library_presenter: ShellLibraryPresenter
    shell_workspace_presenter: ShellWorkspacePresenter
    shell_inspector_presenter: ShellInspectorPresenter
    graph_canvas_presenter: GraphCanvasPresenter

    def attach(self, host: "ShellWindow") -> None:
        host.shell_host_presenter = self.shell_host_presenter
        host.shell_library_presenter = self.shell_library_presenter
        host.shell_workspace_presenter = self.shell_workspace_presenter
        host.shell_inspector_presenter = self.shell_inspector_presenter
        host.graph_canvas_presenter = self.graph_canvas_presenter


@dataclass(frozen=True, slots=True)
class ShellContextBridgeDependencies:
    _shell_context_bridges: ShellContextBridges
    shell_library_bridge: ShellLibraryBridge
    shell_workspace_bridge: ShellWorkspaceBridge
    shell_inspector_bridge: ShellInspectorBridge
    graph_canvas_bridge: GraphCanvasBridge

    def attach(self, host: "ShellWindow") -> None:
        host._shell_context_bridges = self._shell_context_bridges
        host.shell_library_bridge = self.shell_library_bridge
        host.shell_workspace_bridge = self.shell_workspace_bridge
        host.shell_inspector_bridge = self.shell_inspector_bridge
        host.graph_canvas_bridge = self.graph_canvas_bridge


@dataclass(frozen=True, slots=True)
class ShellTimerDependencies:
    metrics_timer: QTimer
    graph_hint_timer: QTimer
    autosave_timer: QTimer

    def attach(self, host: "ShellWindow") -> None:
        host.metrics_timer = self.metrics_timer
        host.graph_hint_timer = self.graph_hint_timer
        host.autosave_timer = self.autosave_timer


@dataclass(frozen=True, slots=True)
class ShellWindowComposition:
    state: ShellStateDependencies
    primitives: ShellPrimitiveDependencies
    controllers: ShellControllerDependencies
    presenters: ShellPresenterDependencies
    context_bridges: ShellContextBridgeDependencies

    def attach(self, host: "ShellWindow") -> None:
        self.state.attach(host)
        self.primitives.attach(host)
        self.controllers.attach(host)
        self.presenters.attach(host)
        self.context_bridges.attach(host)


class ShellWindowDependencyFactory:
    def __init__(self, host: "ShellWindow") -> None:
        self._host = host

    def build_composition(self) -> ShellWindowComposition:
        state = self.create_state_dependencies()
        primitives = self.create_primitive_dependencies(state)
        controllers = self.create_controller_dependencies(state)
        presenters = self.create_presenter_dependencies(state)
        context_bridges = self.create_context_bridge_dependencies(primitives)
        return ShellWindowComposition(
            state=state,
            primitives=primitives,
            controllers=controllers,
            presenters=presenters,
            context_bridges=context_bridges,
        )

    def create_state_dependencies(self) -> ShellStateDependencies:
        return _create_shell_state_dependencies()

    def create_primitive_dependencies(self, state: ShellStateDependencies) -> ShellPrimitiveDependencies:
        return _create_shell_primitive_dependencies(self._host, state)

    def create_controller_dependencies(self, state: ShellStateDependencies) -> ShellControllerDependencies:
        return _create_shell_controller_dependencies(self._host, state)

    def create_presenter_dependencies(self, state: ShellStateDependencies) -> ShellPresenterDependencies:
        return _create_shell_presenter_dependencies(self._host, state)

    def create_context_bridge_dependencies(
        self,
        primitives: ShellPrimitiveDependencies,
    ) -> ShellContextBridgeDependencies:
        return _create_shell_context_bridge_dependencies(self._host, primitives)


class ShellWindowBootstrapCoordinator:
    def bootstrap(self, host: "ShellWindow", composition: ShellWindowComposition) -> None:
        _configure_shell_window_host(host)
        composition.attach(host)
        _run_shell_startup_sequence(host)
        self.create_timer_dependencies(host).attach(host)
        _finalize_shell_window_bootstrap(host)

    def create_timer_dependencies(self, host: "ShellWindow") -> ShellTimerDependencies:
        return _create_shell_timer_dependencies(host)


def create_shell_window() -> "ShellWindow":
    from ea_node_editor.ui.shell.window import ShellWindow

    host = ShellWindow(_defer_bootstrap=True)
    composition = build_shell_window_composition(host)
    bootstrap_shell_window(host, composition)
    return host


def build_shell_window_composition(host: "ShellWindow") -> ShellWindowComposition:
    return ShellWindowDependencyFactory(host).build_composition()


def bootstrap_shell_window(host: "ShellWindow", composition: ShellWindowComposition) -> None:
    ShellWindowBootstrapCoordinator().bootstrap(host, composition)


def _configure_shell_window_host(host: "ShellWindow") -> None:
    host.setWindowTitle("COREX Node Editor")
    apply_window_icon(host)
    host.resize(1600, 900)


def _create_shell_state_dependencies() -> ShellStateDependencies:
    state = ShellState()
    project_session_state = state.project_session
    library_filter_state = state.library_filters
    run_state = state.run
    search_scope_state = state.search_scope

    graphics_settings = DEFAULT_GRAPHICS_SETTINGS
    workspace_ui_state = build_default_shell_workspace_ui_state(graphics_settings)
    search_scope_state.graphics_minimap_expanded = bool(graphics_settings["canvas"]["minimap_expanded"])
    search_scope_state.snap_to_grid_enabled = bool(graphics_settings["interaction"]["snap_to_grid"])

    return ShellStateDependencies(
        state=state,
        project_session_state=project_session_state,
        library_filter_state=library_filter_state,
        run_state=run_state,
        search_scope_state=search_scope_state,
        workspace_ui_state=workspace_ui_state,
    )


def _create_shell_primitive_dependencies(
    host: "ShellWindow",
    state: ShellStateDependencies,
) -> ShellPrimitiveDependencies:
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
    theme_bridge = ThemeBridge(host, theme_id=state.workspace_ui_state.active_theme_id)
    graph_theme_bridge = GraphThemeBridge(
        host,
        theme_id=default_graph_theme_id_for_shell_theme(state.workspace_ui_state.active_theme_id),
    )
    scene.bind_graph_theme_bridge(graph_theme_bridge)
    return ShellPrimitiveDependencies(
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


def _create_shell_controller_dependencies(
    host: "ShellWindow",
    state: ShellStateDependencies,
) -> ShellControllerDependencies:
    search_scope_controller = WindowSearchScopeController(host, state.search_scope_state)
    workspace_library_controller = WorkspaceLibraryController(host)
    project_session_controller = ProjectSessionController(host)
    run_controller = RunController(host)
    app_preferences_controller = AppPreferencesController()
    execution_client = host._create_execution_client()
    execution_client.subscribe(host.execution_event.emit)
    host.execution_event.connect(host._handle_execution_event, Qt.ConnectionType.QueuedConnection)
    return ShellControllerDependencies(
        search_scope_controller=search_scope_controller,
        workspace_library_controller=workspace_library_controller,
        project_session_controller=project_session_controller,
        run_controller=run_controller,
        app_preferences_controller=app_preferences_controller,
        execution_client=execution_client,
    )


def _create_shell_presenter_dependencies(
    host: "ShellWindow",
    state: ShellStateDependencies,
) -> ShellPresenterDependencies:
    shell_host_presenter = ShellHostPresenter(host)
    shell_library_presenter = ShellLibraryPresenter(host)
    shell_workspace_presenter = ShellWorkspacePresenter(host, ui_state=state.workspace_ui_state)
    shell_inspector_presenter = ShellInspectorPresenter(host)
    graph_canvas_presenter = GraphCanvasPresenter(
        host,
        workspace_presenter=shell_workspace_presenter,
        library_presenter=shell_library_presenter,
        inspector_presenter=shell_inspector_presenter,
    )
    return ShellPresenterDependencies(
        shell_host_presenter=shell_host_presenter,
        shell_library_presenter=shell_library_presenter,
        shell_workspace_presenter=shell_workspace_presenter,
        shell_inspector_presenter=shell_inspector_presenter,
        graph_canvas_presenter=graph_canvas_presenter,
    )


def _create_shell_context_bridge_dependencies(
    host: "ShellWindow",
    primitives: ShellPrimitiveDependencies,
) -> ShellContextBridgeDependencies:
    shell_context_bridges = create_shell_context_bridges(
        host,
        scene=primitives.scene,
        view=primitives.view,
        console_panel=primitives.console_panel,
        workspace_tabs=primitives.workspace_tabs,
    )
    return ShellContextBridgeDependencies(
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


def _create_shell_timer_dependencies(host: "ShellWindow") -> ShellTimerDependencies:
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

    return ShellTimerDependencies(
        metrics_timer=metrics_timer,
        graph_hint_timer=graph_hint_timer,
        autosave_timer=autosave_timer,
    )


def _finalize_shell_window_bootstrap(host: "ShellWindow") -> None:
    host._set_run_ui_state("ready", "Idle", 0, 0, 0, 0, clear_run=True)
    host._update_metrics()
