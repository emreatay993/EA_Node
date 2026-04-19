from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtQuickWidgets import QQuickWidget
from PyQt6.QtWidgets import QMessageBox

from ea_node_editor.graph.model import GraphModel, ProjectData
from ea_node_editor.graph.mutation_service import create_workspace_mutation_service
from ea_node_editor.help.help_bridge import HelpBridge
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.settings import AUTOSAVE_INTERVAL_MS, DEFAULT_GRAPHICS_SETTINGS
from ea_node_editor.telemetry.frame_rate import FrameRateSampler
from ea_node_editor.telemetry.startup_profile import phase
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
from ea_node_editor.ui.shell.context_bridges import ShellContextBridges
from ea_node_editor.ui.shell.host_presenter import ShellHostPresenter
from ea_node_editor.ui.shell.presenters import (
    GraphCanvasPresenter,
    GraphCanvasHostPresenter,
    ShellInspectorPresenter,
    ShellLibraryPresenter,
    ShellWorkspacePresenter,
    build_default_shell_workspace_ui_state,
)
from ea_node_editor.ui.shell.runtime_history import RuntimeGraphHistory
from ea_node_editor.ui.shell.state import ShellState
from ea_node_editor.ui.shell.window_search_scope_state import WindowSearchScopeController
from ea_node_editor.ui_qml.console_model import ConsoleModel
from ea_node_editor.ui_qml.content_fullscreen_bridge import ContentFullscreenBridge
from ea_node_editor.ui_qml.graph_canvas_bridge import GraphCanvasBridge
from ea_node_editor.ui_qml.graph_canvas_command_bridge import GraphCanvasCommandBridge
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from ea_node_editor.ui_qml.graph_canvas_state_bridge import GraphCanvasStateBridge
from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge
from ea_node_editor.ui_qml.script_editor_model import ScriptEditorModel
from ea_node_editor.ui_qml.shell_inspector_bridge import ShellInspectorBridge
from ea_node_editor.ui_qml.shell_library_bridge import ShellLibraryBridge
from ea_node_editor.ui_qml.shell_context_bootstrap import (
    ShellContextPropertyBindings,
    bootstrap_shell_qml_context,
)
from ea_node_editor.ui_qml.shell_workspace_bridge import ShellWorkspaceBridge
from ea_node_editor.ui_qml.status_model import StatusItemModel
from ea_node_editor.ui_qml.syntax_bridge import QmlScriptSyntaxBridge
from ea_node_editor.ui_qml.theme_bridge import ThemeBridge
from ea_node_editor.ui_qml.viewer_host_service import ViewerHostService
from ea_node_editor.ui_qml.viewer_session_bridge import ViewerSessionBridge
from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge
from ea_node_editor.ui_qml.workspace_tabs_model import WorkspaceTabsModel
from ea_node_editor.workspace.manager import WorkspaceManager

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow


class _ShellWindowAdapterBase:
    def __init__(self, host: "ShellWindow") -> None:
        self._window = host

    @property
    def window(self) -> "ShellWindow":
        return self._window

    def __getattr__(self, name: str) -> object:
        return getattr(self._window, name)


class _WorkspaceLibraryControllerHostAdapter(_ShellWindowAdapterBase):
    pass


class _RunControllerHostAdapter(_ShellWindowAdapterBase):
    pass


class _ProjectSessionControllerHostAdapter(_ShellWindowAdapterBase):
    @property
    def dialog_parent_host(self) -> "ShellWindow":
        return self._window

    @property
    def model(self) -> GraphModel:
        return self._window.model

    @model.setter
    def model(self, value: GraphModel) -> None:
        self._window.model = value

    @property
    def workspace_manager(self) -> WorkspaceManager:
        return self._window.workspace_manager

    @workspace_manager.setter
    def workspace_manager(self, value: WorkspaceManager) -> None:
        self._window.workspace_manager = value

    @property
    def project_path(self) -> str:
        return self._window.project_path

    @project_path.setter
    def project_path(self, value: str) -> None:
        self._window.project_path = value

    def browse_node_property_path(self, node_id: str, key: str, current_path: str) -> str:
        presenter = getattr(self._window, "graph_canvas_presenter", None)
        browse = getattr(presenter, "browse_node_property_path", None)
        if not callable(browse):
            return ""
        return str(browse(node_id, key, current_path) or "")


class _ShellLibraryPresenterHostAdapter(_ShellWindowAdapterBase):
    pass


class _ShellWorkspacePresenterHostAdapter(_ShellWindowAdapterBase):
    pass


class _ShellInspectorPresenterHostAdapter(_ShellWindowAdapterBase):
    pass


class _GraphCanvasPresenterHostAdapter(_ShellWindowAdapterBase):
    pass


class _GraphCanvasHostPresenterHostAdapter(_ShellWindowAdapterBase):
    pass


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
        host.workflow_library_controller = self.workspace_library_controller.workflow_library_controller
        host.workspace_navigation_controller = self.workspace_library_controller.workspace_navigation_controller
        host.workspace_graph_edit_controller = self.workspace_library_controller.workspace_graph_edit_controller
        host.workspace_package_io_controller = self.workspace_library_controller.workspace_package_io_controller
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
    graph_canvas_host_presenter: GraphCanvasHostPresenter

    def attach(self, host: "ShellWindow") -> None:
        host.shell_host_presenter = self.shell_host_presenter
        host.shell_library_presenter = self.shell_library_presenter
        host.shell_workspace_presenter = self.shell_workspace_presenter
        host.shell_inspector_presenter = self.shell_inspector_presenter
        host.graph_canvas_presenter = self.graph_canvas_presenter
        host.graph_canvas_host_presenter = self.graph_canvas_host_presenter


@dataclass(frozen=True, slots=True)
class ShellRuntimeDependencies:
    content_fullscreen_bridge: ContentFullscreenBridge
    viewer_session_bridge: ViewerSessionBridge
    viewer_host_service: ViewerHostService

    def attach(self, host: "ShellWindow") -> None:
        host.content_fullscreen_bridge = self.content_fullscreen_bridge
        host.viewer_session_bridge = self.viewer_session_bridge
        host.viewer_host_service = self.viewer_host_service


@dataclass(frozen=True, slots=True)
class ShellContextBridgeDependencies:
    shell_context_bridges: ShellContextBridges
    shell_library_bridge: ShellLibraryBridge
    shell_workspace_bridge: ShellWorkspaceBridge
    shell_inspector_bridge: ShellInspectorBridge
    graph_canvas_state_bridge: GraphCanvasStateBridge
    graph_canvas_command_bridge: GraphCanvasCommandBridge
    graph_canvas_bridge: GraphCanvasBridge
    help_bridge: HelpBridge
    qml_context_property_bindings: ShellContextPropertyBindings

    def attach(self, host: "ShellWindow") -> None:
        host._shell_context_bridges = self.shell_context_bridges
        host._shell_qml_context_property_bindings = self.qml_context_property_bindings
        host.shell_library_bridge = self.shell_library_bridge
        host.shell_workspace_bridge = self.shell_workspace_bridge
        host.shell_inspector_bridge = self.shell_inspector_bridge
        host.graph_canvas_state_bridge = self.graph_canvas_state_bridge
        host.graph_canvas_command_bridge = self.graph_canvas_command_bridge
        host.graph_canvas_bridge = self.graph_canvas_bridge
        host.help_bridge = self.help_bridge


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
    runtime: ShellRuntimeDependencies
    context_bridges: ShellContextBridgeDependencies

    def attach(self, host: "ShellWindow") -> None:
        self.state.attach(host)
        self.primitives.attach(host)
        self.controllers.attach(host)
        self.presenters.attach(host)
        self.runtime.attach(host)
        self.context_bridges.attach(host)


class ShellWindowDependencyFactory:
    def __init__(self, host: "ShellWindow", registry: NodeRegistry | None = None) -> None:
        self._host = host
        self._registry = registry

    def build_composition(self) -> ShellWindowComposition:
        with phase("factory.state"):
            state = self.create_state_dependencies()
        with phase("factory.primitives"):
            primitives = self.create_primitive_dependencies(state)
        with phase("factory.controllers"):
            controllers = self.create_controller_dependencies(state)
        with phase("factory.presenters"):
            presenters = self.create_presenter_dependencies(state)
        with phase("factory.runtime"):
            runtime = self.create_runtime_dependencies(primitives)
        with phase("factory.context_bridges"):
            context_bridges = self.create_context_bridge_dependencies(primitives, presenters, runtime)
        return ShellWindowComposition(
            state=state,
            primitives=primitives,
            controllers=controllers,
            presenters=presenters,
            runtime=runtime,
            context_bridges=context_bridges,
        )

    def create_state_dependencies(self) -> ShellStateDependencies:
        return _create_shell_state_dependencies()

    def create_primitive_dependencies(self, state: ShellStateDependencies) -> ShellPrimitiveDependencies:
        return _create_shell_primitive_dependencies(self._host, state, registry=self._registry)

    def create_controller_dependencies(self, state: ShellStateDependencies) -> ShellControllerDependencies:
        return _create_shell_controller_dependencies(self._host, state)

    def create_presenter_dependencies(self, state: ShellStateDependencies) -> ShellPresenterDependencies:
        return _create_shell_presenter_dependencies(self._host, state)

    def create_runtime_dependencies(self, primitives: ShellPrimitiveDependencies) -> ShellRuntimeDependencies:
        return _create_shell_runtime_dependencies(self._host, primitives)

    def create_context_bridge_dependencies(
        self,
        primitives: ShellPrimitiveDependencies,
        presenters: ShellPresenterDependencies,
        runtime: ShellRuntimeDependencies,
    ) -> ShellContextBridgeDependencies:
        return _create_shell_context_bridge_dependencies(self._host, primitives, presenters, runtime)


class ShellWindowBootstrapCoordinator:
    def bootstrap(self, host: "ShellWindow", composition: ShellWindowComposition) -> None:
        with phase("coord.configure_host"):
            _configure_shell_window_host(host)
        with phase("coord.composition.attach"):
            composition.attach(host)
        with phase("coord.startup_sequence"):
            _run_shell_startup_sequence(host)
        with phase("coord.timer_deps"):
            self.create_timer_dependencies(host).attach(host)
        with phase("coord.finalize"):
            _finalize_shell_window_bootstrap(host)

    def create_timer_dependencies(self, host: "ShellWindow") -> ShellTimerDependencies:
        return _create_shell_timer_dependencies(host)


def create_shell_window(registry: NodeRegistry | None = None) -> "ShellWindow":
    """Build the shell window, optionally reusing a pre-built node registry.

    Pass ``registry`` to skip the blocking ``build_default_registry()`` call —
    the splash builds the registry on a worker thread and hands it in here.
    See ``PLANS_TO_IMPLEMENT/in_progress/splash_threaded_plugin_registry.md``.
    """
    from ea_node_editor.ui.shell.window import ShellWindow

    with phase("shell.ShellWindow()"):
        host = ShellWindow(_defer_bootstrap=True)
    with phase("shell.build_composition"):
        composition = build_shell_window_composition(host, registry=registry)
    with phase("shell.bootstrap"):
        bootstrap_shell_window(host, composition)
    with phase("shell.connect_state_signal"):
        host._connect_application_state_signal()
    return host


def build_shell_window_composition(
    host: "ShellWindow", registry: NodeRegistry | None = None
) -> ShellWindowComposition:
    return ShellWindowDependencyFactory(host, registry=registry).build_composition()


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
    *,
    registry: NodeRegistry | None = None,
) -> ShellPrimitiveDependencies:
    with phase("prim.build_default_registry"):
        if registry is None:
            registry = build_default_registry()
    with phase("prim.JsonProjectSerializer"):
        serializer = JsonProjectSerializer(registry)
    with phase("prim.session_store"):
        session_store = host._create_session_store(serializer)
    with phase("prim.GraphModel"):
        model = GraphModel(
            ProjectData(project_id="proj_local", name="untitled"),
            mutation_service_factory=create_workspace_mutation_service,
        )
    with phase("prim.WorkspaceManager"):
        workspace_manager = WorkspaceManager(model)
    with phase("prim.RuntimeGraphHistory"):
        runtime_history = RuntimeGraphHistory()
    with phase("prim.GraphSceneBridge"):
        scene = GraphSceneBridge(host)
        scene.bind_runtime_history(runtime_history)
    with phase("prim.ViewportBridge"):
        view = ViewportBridge(host)
    with phase("prim.GraphInteractions"):
        graph_interactions = GraphInteractions(
            scene=scene,
            registry=registry,
            history=runtime_history,
        )
    with phase("prim.ConsoleModel"):
        console_panel = ConsoleModel(host)
    with phase("prim.ScriptEditorModel"):
        script_editor = ScriptEditorModel(host)
    with phase("prim.QmlScriptSyntaxBridge"):
        script_highlighter = QmlScriptSyntaxBridge(host)
    with phase("prim.WorkspaceTabsModel"):
        workspace_tabs = WorkspaceTabsModel(host)
    with phase("prim.UiIconRegistryBridge"):
        ui_icons = UiIconRegistryBridge(host)
    with phase("prim.UiIconImageProvider"):
        ui_icon_image_provider = UiIconImageProvider()
    with phase("prim.LocalMediaPreviewImageProvider"):
        local_media_preview_provider = LocalMediaPreviewImageProvider()
    with phase("prim.LocalPdfPreviewImageProvider"):
        local_pdf_preview_provider = LocalPdfPreviewImageProvider()
    with phase("prim.StatusItemModels"):
        status_engine = StatusItemModel("E", "Ready", host)
        status_jobs = StatusItemModel("J", "R:0 Q:0 D:0 F:0", host)
        status_metrics = StatusItemModel("M", "FPS:0 CPU:0% RAM:0/0 GB", host)
        status_notifications = StatusItemModel("N", "W:0 E:0", host)
    with phase("prim.FrameRateSampler"):
        frame_rate_sampler = FrameRateSampler()
    with phase("prim.ThemeBridge"):
        theme_bridge = ThemeBridge(host, theme_id=state.workspace_ui_state.active_theme_id)
    with phase("prim.GraphThemeBridge"):
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
    workspace_library_controller = WorkspaceLibraryController(_WorkspaceLibraryControllerHostAdapter(host))
    project_session_controller = ProjectSessionController(_ProjectSessionControllerHostAdapter(host))
    run_controller = RunController(_RunControllerHostAdapter(host))
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
    shell_library_presenter = ShellLibraryPresenter(_ShellLibraryPresenterHostAdapter(host), parent=host)
    shell_workspace_presenter = ShellWorkspacePresenter(
        _ShellWorkspacePresenterHostAdapter(host),
        parent=host,
        ui_state=state.workspace_ui_state,
    )
    shell_inspector_presenter = ShellInspectorPresenter(_ShellInspectorPresenterHostAdapter(host), parent=host)
    graph_canvas_presenter = GraphCanvasPresenter(
        _GraphCanvasPresenterHostAdapter(host),
        parent=host,
        workspace_presenter=shell_workspace_presenter,
        library_presenter=shell_library_presenter,
        inspector_presenter=shell_inspector_presenter,
    )
    graph_canvas_host_presenter = GraphCanvasHostPresenter(_GraphCanvasHostPresenterHostAdapter(host), parent=host)
    return ShellPresenterDependencies(
        shell_host_presenter=shell_host_presenter,
        shell_library_presenter=shell_library_presenter,
        shell_workspace_presenter=shell_workspace_presenter,
        shell_inspector_presenter=shell_inspector_presenter,
        graph_canvas_presenter=graph_canvas_presenter,
        graph_canvas_host_presenter=graph_canvas_host_presenter,
    )


def _create_shell_runtime_dependencies(
    host: "ShellWindow",
    primitives: ShellPrimitiveDependencies,
) -> ShellRuntimeDependencies:
    viewer_session_bridge = ViewerSessionBridge(
        host,
        shell_window=host,
        scene_bridge=primitives.scene,
    )
    content_fullscreen_bridge = ContentFullscreenBridge(
        host,
        shell_window=host,
        scene_bridge=primitives.scene,
        viewer_session_bridge=viewer_session_bridge,
    )
    viewer_host_service = ViewerHostService(
        host,
        shell_window=host,
        viewer_session_bridge=viewer_session_bridge,
    )
    return ShellRuntimeDependencies(
        content_fullscreen_bridge=content_fullscreen_bridge,
        viewer_session_bridge=viewer_session_bridge,
        viewer_host_service=viewer_host_service,
    )


def _create_shell_context_bridge_dependencies(
    host: "ShellWindow",
    primitives: ShellPrimitiveDependencies,
    presenters: ShellPresenterDependencies,
    runtime: ShellRuntimeDependencies,
) -> ShellContextBridgeDependencies:
    graph_canvas_state_bridge = GraphCanvasStateBridge(
        host,
        shell_window=host,
        canvas_source=presenters.graph_canvas_presenter,
        scene_bridge=primitives.scene,
        view_bridge=primitives.view,
    )
    graph_canvas_command_bridge = GraphCanvasCommandBridge(
        host,
        shell_window=host,
        canvas_source=presenters.graph_canvas_presenter,
        host_source=presenters.graph_canvas_host_presenter,
        scene_bridge=primitives.scene,
        view_bridge=primitives.view,
    )
    shell_context_bridges = ShellContextBridges(
        shell_library_bridge=ShellLibraryBridge(
            host,
            shell_window=host,
            library_source=presenters.shell_library_presenter,
        ),
        shell_workspace_bridge=ShellWorkspaceBridge(
            host,
            shell_window=host,
            workspace_source=presenters.shell_workspace_presenter,
            scene_bridge=primitives.scene,
            view_bridge=primitives.view,
            console_bridge=primitives.console_panel,
            workspace_tabs_bridge=primitives.workspace_tabs,
        ),
        shell_inspector_bridge=ShellInspectorBridge(
            host,
            shell_window=host,
            inspector_source=presenters.shell_inspector_presenter,
            scene_bridge=primitives.scene,
        ),
        graph_canvas_state_bridge=graph_canvas_state_bridge,
        graph_canvas_command_bridge=graph_canvas_command_bridge,
        graph_canvas_bridge=GraphCanvasBridge(
            host,
            shell_window=host,
            scene_bridge=primitives.scene,
            view_bridge=primitives.view,
            state_bridge=graph_canvas_state_bridge,
            command_bridge=graph_canvas_command_bridge,
        ),
    )
    help_bridge = HelpBridge(host, shell_window=host)
    return ShellContextBridgeDependencies(
        shell_context_bridges=shell_context_bridges,
        shell_library_bridge=shell_context_bridges.shell_library_bridge,
        shell_workspace_bridge=shell_context_bridges.shell_workspace_bridge,
        shell_inspector_bridge=shell_context_bridges.shell_inspector_bridge,
        graph_canvas_state_bridge=graph_canvas_state_bridge,
        graph_canvas_command_bridge=graph_canvas_command_bridge,
        graph_canvas_bridge=shell_context_bridges.graph_canvas_bridge,
        help_bridge=help_bridge,
        qml_context_property_bindings=_build_shell_context_property_bindings(
            shell_context_bridges,
            primitives,
            runtime,
            help_bridge,
        ),
    )


def _build_shell_context_property_bindings(
    bridges: ShellContextBridges,
    primitives: ShellPrimitiveDependencies,
    runtime: ShellRuntimeDependencies,
    help_bridge: HelpBridge,
) -> ShellContextPropertyBindings:
    return (
        ("shellLibraryBridge", bridges.shell_library_bridge),
        ("shellWorkspaceBridge", bridges.shell_workspace_bridge),
        ("shellInspectorBridge", bridges.shell_inspector_bridge),
        ("graphCanvasStateBridge", bridges.graph_canvas_state_bridge),
        ("graphCanvasCommandBridge", bridges.graph_canvas_command_bridge),
        ("graphCanvasViewBridge", primitives.view),
        ("contentFullscreenBridge", runtime.content_fullscreen_bridge),
        ("viewerSessionBridge", runtime.viewer_session_bridge),
        ("viewerHostService", runtime.viewer_host_service),
        ("scriptEditorBridge", primitives.script_editor),
        ("scriptHighlighterBridge", primitives.script_highlighter),
        ("themeBridge", primitives.theme_bridge),
        ("graphThemeBridge", primitives.graph_theme_bridge),
        ("uiIcons", primitives.ui_icons),
        ("statusEngine", primitives.status_engine),
        ("statusJobs", primitives.status_jobs),
        ("statusMetrics", primitives.status_metrics),
        ("statusNotifications", primitives.status_notifications),
        ("helpBridge", help_bridge),
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
    context_property_bindings = host._shell_qml_context_property_bindings
    bootstrap_shell_qml_context(host, widget, context_property_bindings)
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
