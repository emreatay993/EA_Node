from __future__ import annotations

import importlib
import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from PyQt6.QtCore import QObject

from ea_node_editor.ui.shell.runtime_clipboard import (
    build_graph_fragment_payload,
    serialize_graph_fragment_payload,
)
from ea_node_editor.ui_qml.graph_canvas_command_bridge import GraphCanvasCommandBridge
from ea_node_editor.ui_qml.graph_canvas_state_bridge import GraphCanvasStateBridge
from ea_node_editor.ui_qml.shell_inspector_bridge import ShellInspectorBridge
from ea_node_editor.ui_qml.shell_library_bridge import ShellLibraryBridge
from ea_node_editor.ui_qml.shell_workspace_bridge import ShellWorkspaceBridge
from tests.main_window_shell.base import MainWindowShellTestBase, SharedMainWindowShellTestBase
from tests.main_window_shell.bridge_contracts import (
    _GRAPH_CANVAS_HOST_DIRECT_ENV,
    _REPO_ROOT,
    _named_child_items,
)

_SHELL_TEST_MODULES = (
    "tests.main_window_shell.shell_basics_and_search",
    "tests.main_window_shell.drop_connect_and_workflow_io",
    "tests.main_window_shell.edit_clipboard_history",
    "tests.main_window_shell.passive_style_context_menus",
    "tests.main_window_shell.passive_property_editors",
    "tests.main_window_shell.passive_image_nodes",
    "tests.main_window_shell.passive_pdf_nodes",
    "tests.main_window_shell.view_library_inspector",
    "tests.main_window_shell.bridge_contracts",
    "tests.main_window_shell.bridge_qml_boundaries",
    "tests.main_window_shell.shell_runtime_contracts",
)


def _load_shell_test_modules() -> None:
    for module_name in _SHELL_TEST_MODULES:
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            if exc.name != module_name:
                raise
            continue
        exported_names = getattr(module, "__all__", None)
        if exported_names is None:
            exported_names = [name for name in module.__dict__ if not name.startswith("_")]
        globals().update({name: getattr(module, name) for name in exported_names})


def _pop_isolated_imported_shell_cases() -> dict[str, type[MainWindowShellTestBase]]:
    isolated_cases: dict[str, type[MainWindowShellTestBase]] = {}
    for isolated_name in (
        "MainWindowShellPassiveImageNodesTests",
        "MainWindowShellPassivePdfNodesTests",
        "MainWindowShellPassiveImageNodesSubprocessTests",
        "MainWindowShellPassivePdfNodesSubprocessTests",
    ):
        candidate = globals().pop(isolated_name, None)
        if (
            isinstance(candidate, type)
            and candidate.__module__ == "tests.main_window_shell.shell_runtime_contracts"
        ):
            globals()[isolated_name] = candidate
            continue
        if isinstance(candidate, type) and issubclass(candidate, MainWindowShellTestBase):
            isolated_cases[isolated_name] = candidate
    return isolated_cases


_load_shell_test_modules()
_ISOLATED_IMPORTED_SHELL_CASES = _pop_isolated_imported_shell_cases()


def _assert_text_snippets(
    test_case: unittest.TestCase,
    *,
    label: str,
    text: str,
    absent_snippets: tuple[str, ...] = (),
    present_snippets: tuple[str, ...] = (),
) -> None:
    for snippet in absent_snippets:
        with test_case.subTest(path=label, snippet=snippet, expectation="absent"):
            test_case.assertNotIn(snippet, text)

    for snippet in present_snippets:
        with test_case.subTest(path=label, snippet=snippet, expectation="present"):
            test_case.assertIn(snippet, text)


def _run_pytest_shell_class_nodeid(nodeid: str, *, extra_env: dict[str, str] | None = None) -> None:
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--ignore=venv", nodeid, "-q"],
        cwd=_REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return
    output = "\n".join(
        part.strip()
        for part in (result.stdout, result.stderr)
        if part and part.strip()
    )
    raise AssertionError(
        f"Subprocess shell test failed for {nodeid} "
        f"(exit={result.returncode}).\n{output}"
    )


class MainWindowShellContextBootstrapTests(SharedMainWindowShellTestBase):
    def test_qml_context_removes_raw_canvas_globals_and_registers_split_canvas_bridges(self) -> None:
        context = self.window.quick_widget.rootContext()

        expected_context_names = (
            "scriptEditorBridge",
            "scriptHighlighterBridge",
            "themeBridge",
            "graphThemeBridge",
            "uiIcons",
            "statusEngine",
            "statusJobs",
            "statusMetrics",
            "statusNotifications",
            "shellLibraryBridge",
            "shellWorkspaceBridge",
            "shellInspectorBridge",
            "graphCanvasStateBridge",
            "graphCanvasCommandBridge",
        )
        for name in expected_context_names:
            with self.subTest(name=name):
                self.assertIsNotNone(context.contextProperty(name))

        for name in (
            "mainWindow",
            "sceneBridge",
            "viewBridge",
            "consoleBridge",
            "workspaceTabsBridge",
            "graphCanvasBridge",
        ):
            with self.subTest(name=name, expectation="removed"):
                self.assertIsNone(context.contextProperty(name))

        shell_library_bridge = context.contextProperty("shellLibraryBridge")
        self.assertIsInstance(shell_library_bridge, ShellLibraryBridge)
        self.assertIs(shell_library_bridge.shell_window, self.window)
        self.assertIs(shell_library_bridge.library_source, self.window.shell_library_presenter)

        shell_workspace_bridge = context.contextProperty("shellWorkspaceBridge")
        self.assertIsInstance(shell_workspace_bridge, ShellWorkspaceBridge)
        self.assertIs(shell_workspace_bridge.shell_window, self.window)
        self.assertIs(shell_workspace_bridge.workspace_source, self.window.shell_workspace_presenter)
        self.assertIs(shell_workspace_bridge.scene_bridge, self.window.scene)
        self.assertIs(shell_workspace_bridge.view_bridge, self.window.view)
        self.assertIs(shell_workspace_bridge.console_bridge, self.window.console_panel)
        self.assertIs(shell_workspace_bridge.workspace_tabs_bridge, self.window.workspace_tabs)

        shell_inspector_bridge = context.contextProperty("shellInspectorBridge")
        self.assertIsInstance(shell_inspector_bridge, ShellInspectorBridge)
        self.assertIs(shell_inspector_bridge.shell_window, self.window)
        self.assertIs(shell_inspector_bridge.inspector_source, self.window.shell_inspector_presenter)
        self.assertIs(shell_inspector_bridge.scene_bridge, self.window.scene)

        graph_canvas_state_bridge = context.contextProperty("graphCanvasStateBridge")
        self.assertIsInstance(graph_canvas_state_bridge, GraphCanvasStateBridge)
        self.assertIs(graph_canvas_state_bridge.parent(), self.window)
        self.assertIs(graph_canvas_state_bridge.shell_window, self.window)
        self.assertIs(graph_canvas_state_bridge.canvas_source, self.window.graph_canvas_presenter)
        self.assertIs(graph_canvas_state_bridge.scene_bridge, self.window.scene)
        self.assertIs(graph_canvas_state_bridge.view_bridge, self.window.view)

        graph_canvas_command_bridge = context.contextProperty("graphCanvasCommandBridge")
        self.assertIsInstance(graph_canvas_command_bridge, GraphCanvasCommandBridge)
        self.assertIs(graph_canvas_command_bridge.parent(), self.window)
        self.assertIs(graph_canvas_command_bridge.shell_window, self.window)
        self.assertIs(graph_canvas_command_bridge.canvas_source, self.window.graph_canvas_presenter)
        self.assertIs(graph_canvas_command_bridge.host_source, self.window)
        self.assertIs(graph_canvas_command_bridge.scene_bridge, self.window.scene)
        self.assertIs(graph_canvas_command_bridge.view_bridge, self.window.view)

        context_bindings = dict(self.window._shell_qml_context_property_bindings)
        self.assertIs(context_bindings["shellLibraryBridge"], shell_library_bridge)
        self.assertIs(context_bindings["shellWorkspaceBridge"], shell_workspace_bridge)
        self.assertIs(context_bindings["shellInspectorBridge"], shell_inspector_bridge)
        self.assertIs(context_bindings["graphCanvasStateBridge"], graph_canvas_state_bridge)
        self.assertIs(context_bindings["graphCanvasCommandBridge"], graph_canvas_command_bridge)

    def test_shell_window_keeps_split_bridge_aliases_in_sync_with_context_bundle(self) -> None:
        bridges = self.window._shell_context_bridges

        self.assertIs(self.window.shell_library_bridge, bridges.shell_library_bridge)
        self.assertIs(self.window.shell_workspace_bridge, bridges.shell_workspace_bridge)
        self.assertIs(self.window.shell_inspector_bridge, bridges.shell_inspector_bridge)
        self.assertIs(self.window.graph_canvas_state_bridge, bridges.graph_canvas_state_bridge)
        self.assertIs(self.window.graph_canvas_command_bridge, bridges.graph_canvas_command_bridge)


class MainWindowGraphCanvasBridgeTests(SharedMainWindowShellTestBase):
    def test_qml_context_registers_only_state_and_command_canvas_bridges(self) -> None:
        context = self.window.quick_widget.rootContext()
        graph_canvas_state_bridge = context.contextProperty("graphCanvasStateBridge")
        graph_canvas_command_bridge = context.contextProperty("graphCanvasCommandBridge")

        self.assertIsInstance(graph_canvas_state_bridge, GraphCanvasStateBridge)
        self.assertIs(graph_canvas_state_bridge.parent(), self.window)
        self.assertIs(graph_canvas_state_bridge.shell_window, self.window)
        self.assertIs(graph_canvas_state_bridge.canvas_source, self.window.graph_canvas_presenter)
        self.assertIs(graph_canvas_state_bridge.scene_bridge, self.window.scene)
        self.assertIs(graph_canvas_state_bridge.view_bridge, self.window.view)

        self.assertIsInstance(graph_canvas_command_bridge, GraphCanvasCommandBridge)
        self.assertIs(graph_canvas_command_bridge.parent(), self.window)
        self.assertIs(graph_canvas_command_bridge.shell_window, self.window)
        self.assertIs(graph_canvas_command_bridge.canvas_source, self.window.graph_canvas_presenter)
        self.assertIs(graph_canvas_command_bridge.host_source, self.window)
        self.assertIs(graph_canvas_command_bridge.scene_bridge, self.window.scene)
        self.assertIs(graph_canvas_command_bridge.view_bridge, self.window.view)

        self.assertIsNone(context.contextProperty("graphCanvasBridge"))

    def test_shell_window_keeps_graph_canvas_state_command_bridge_aliases_in_sync_with_context_bundle(self) -> None:
        bridges = self.window._shell_context_bridges

        self.assertIs(self.window.graph_canvas_state_bridge, bridges.graph_canvas_state_bridge)
        self.assertIs(self.window.graph_canvas_command_bridge, bridges.graph_canvas_command_bridge)


class ShellWorkspaceBridgeQmlBoundaryTests(unittest.TestCase):
    def test_workspace_run_title_and_console_qml_routes_owned_concerns_through_shell_workspace_bridge(self) -> None:
        expectations = {
            "ea_node_editor/ui_qml/components/shell/ShellTitleBar.qml": (
                (
                    "property var mainWindowRef",
                    "mainWindowRef.project_display_name",
                ),
                (
                    "readonly property var workspaceBridgeRef: shellWorkspaceBridge",
                    "root.workspaceBridgeRef.project_display_name",
                ),
            ),
            "ea_node_editor/ui_qml/components/shell/ShellRunToolbar.qml": (
                (
                    "property var mainWindowRef",
                    "mainWindowRef.request_run_workflow",
                    "mainWindowRef.request_toggle_run_pause",
                    "mainWindowRef.request_stop_workflow",
                    "mainWindowRef.show_workflow_settings_dialog",
                    "mainWindowRef.set_script_editor_panel_visible",
                ),
                (
                    "property var viewBridgeRef",
                    "property var scriptEditorBridgeRef",
                    "readonly property var workspaceBridgeRef: shellWorkspaceBridge",
                    "root.workspaceBridgeRef.request_run_workflow",
                    "root.workspaceBridgeRef.request_toggle_run_pause",
                    "root.workspaceBridgeRef.request_stop_workflow",
                    "root.workspaceBridgeRef.show_workflow_settings_dialog",
                    "root.workspaceBridgeRef.set_script_editor_panel_visible",
                ),
            ),
            "ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml": (
                (
                    "mainWindowRef.graphics_tab_strip_density",
                    "mainWindowRef.active_scope_breadcrumb_items",
                    "mainWindowRef.active_view_items",
                    "mainWindowRef.active_workspace_id",
                    "mainWindowRef.request_open_scope_breadcrumb",
                    "mainWindowRef.request_switch_view",
                    "mainWindowRef.request_move_view_tab",
                    "mainWindowRef.request_rename_view",
                    "mainWindowRef.request_close_view",
                    "mainWindowRef.request_create_view",
                    "mainWindowRef.request_move_workspace_tab",
                    "mainWindowRef.request_rename_workspace_by_id",
                    "mainWindowRef.request_close_workspace_by_id",
                    "mainWindowRef.request_create_workspace",
                    "property var workspaceTabsBridgeRef",
                    "property var consoleBridgeRef",
                    "workspaceTabsBridgeRef.tabs",
                    "workspaceTabsBridgeRef.activate_workspace",
                    "consoleBridgeRef.error_count_value",
                    "consoleBridgeRef.warning_count_value",
                    "consoleBridgeRef.clear_all",
                    "consoleBridgeRef.output_text",
                    "consoleBridgeRef.errors_text",
                    "consoleBridgeRef.warnings_text",
                    "property var mainWindowRef",
                    "property var sceneBridgeRef",
                    "property var viewBridgeRef",
                    "property var graphCanvasBridgeRef",
                    "canvasBridge: root.graphCanvasBridgeRef",
                ),
                (
                    "property var graphCanvasStateBridgeRef",
                    "property var graphCanvasCommandBridgeRef",
                    "property var overlayHostItem",
                    "readonly property var workspaceBridgeRef: shellWorkspaceBridge",
                    "root.workspaceBridgeRef.graphics_tab_strip_density",
                    "root.workspaceBridgeRef.active_scope_breadcrumb_items",
                    "root.workspaceBridgeRef.active_view_items",
                    "root.workspaceBridgeRef.active_workspace_id",
                    "root.workspaceBridgeRef.request_open_scope_breadcrumb",
                    "root.workspaceBridgeRef.request_switch_view",
                    "root.workspaceBridgeRef.request_move_view_tab",
                    "root.workspaceBridgeRef.request_rename_view",
                    "root.workspaceBridgeRef.request_close_view",
                    "root.workspaceBridgeRef.request_create_view",
                    "root.workspaceBridgeRef.request_move_workspace_tab",
                    "root.workspaceBridgeRef.request_rename_workspace_by_id",
                    "root.workspaceBridgeRef.request_close_workspace_by_id",
                    "root.workspaceBridgeRef.request_create_workspace",
                    "root.workspaceBridgeRef.workspace_tabs",
                    "root.workspaceBridgeRef.activate_workspace",
                    "root.workspaceBridgeRef.error_count_value",
                    "root.workspaceBridgeRef.warning_count_value",
                    "root.workspaceBridgeRef.clear_all",
                    "root.workspaceBridgeRef.output_text",
                    "root.workspaceBridgeRef.errors_text",
                    "root.workspaceBridgeRef.warnings_text",
                    "canvasStateBridge: root.graphCanvasStateBridgeRef",
                    "canvasCommandBridge: root.graphCanvasCommandBridgeRef",
                ),
            ),
            "ea_node_editor/ui_qml/components/shell/ScriptEditorOverlay.qml": (
                (
                    "property var mainWindowRef",
                    "mainWindowRef.set_script_editor_panel_visible(false)",
                ),
                (
                    "property var scriptEditorBridgeRef",
                    "property var scriptHighlighterBridgeRef",
                    "readonly property var workspaceBridgeRef: shellWorkspaceBridge",
                    "root.workspaceBridgeRef.set_script_editor_panel_visible(false)",
                ),
            ),
        }

        for relative_path, (absent_snippets, present_snippets) in expectations.items():
            qml_text = (_REPO_ROOT / relative_path).read_text(encoding="utf-8")
            _assert_text_snippets(
                self,
                label=relative_path,
                text=qml_text,
                absent_snippets=absent_snippets,
                present_snippets=present_snippets,
            )

    def test_main_shell_keeps_only_the_remaining_live_shell_plumbing_assignments(self) -> None:
        relative_path = "ea_node_editor/ui_qml/MainShell.qml"
        qml_text = (_REPO_ROOT / relative_path).read_text(encoding="utf-8")

        absent_snippets = (
            "typeof graphCanvasBridge",
            "typeof mainWindow",
            "typeof sceneBridge",
            "typeof viewBridge",
            "workspaceTabsBridgeRef: workspaceTabsBridge",
            "consoleBridgeRef: consoleBridge",
            "mainWindowRef: mainWindow",
            "sceneBridgeRef: root.sceneBridgeRef",
            "viewBridgeRef: root.viewBridgeRef",
            "viewBridgeRef: viewBridge",
            "readonly property var canvasShellBridgeRef",
            "readonly property var canvasSceneBridgeRef",
            "readonly property var canvasBridgeRef: graphCanvasBridge",
            "canvasBridgeRef: root.canvasBridgeRef",
        )
        present_snippets = (
            "readonly property var canvasStateBridgeRef: graphCanvasStateBridge",
            "readonly property var canvasCommandBridgeRef: graphCanvasCommandBridge",
            "readonly property var canvasViewBridgeRef: root.canvasStateBridgeRef",
            "WorkspaceCenterPane {",
            "graphCanvasStateBridgeRef: root.canvasStateBridgeRef",
            "graphCanvasCommandBridgeRef: root.canvasCommandBridgeRef",
            "overlayHostItem: root",
            "viewBridgeRef: root.canvasViewBridgeRef",
            "ShellStatusStrip {",
            "canvasStateBridgeRef: root.canvasStateBridgeRef",
            "canvasCommandBridgeRef: root.canvasCommandBridgeRef",
            "scriptEditorBridgeRef: scriptEditorBridge",
            "scriptHighlighterBridgeRef: scriptHighlighterBridge",
        )

        _assert_text_snippets(
            self,
            label=relative_path,
            text=qml_text,
            absent_snippets=absent_snippets,
            present_snippets=present_snippets,
        )


class GraphCanvasQmlBoundaryTests(unittest.TestCase):
    def test_graph_canvas_routes_owned_concerns_through_split_bridge_refs(self) -> None:
        relative_path = "ea_node_editor/ui_qml/components/GraphCanvas.qml"
        qml_text = (_REPO_ROOT / relative_path).read_text(encoding="utf-8")

        absent_snippets = (
            "property var canvasBridge: null",
            "readonly property var canvasBridgeRef",
            "property var mainWindowBridge",
            "property var sceneBridge: root.canvasStateBridgeRef",
            "property var viewBridge: root.canvasStateBridgeRef",
            "mainWindowBridge.graphics_minimap_expanded",
            "mainWindowBridge.graphics_show_grid",
            "mainWindowBridge.graphics_show_minimap",
            "mainWindowBridge.graphics_node_shadow",
            "mainWindowBridge.graphics_shadow_strength",
            "mainWindowBridge.graphics_shadow_softness",
            "mainWindowBridge.graphics_shadow_offset",
            "mainWindowBridge.snap_to_grid_enabled",
            "mainWindowBridge.snap_grid_size",
            "mainWindowBridge.request_open_subnode_scope",
            "mainWindowBridge.browse_node_property_path",
            "mainWindowBridge.request_drop_node_from_library",
            "mainWindowBridge.request_connect_ports",
            "mainWindowBridge.request_open_connection_quick_insert",
            "sceneBridge.nodes_model",
            "sceneBridge.selected_node_lookup",
            "sceneBridge.select_node",
            "sceneBridge.set_node_property",
            "sceneBridge.are_port_kinds_compatible",
            "sceneBridge.are_data_types_compatible",
            "sceneBridge.move_nodes_by_delta",
            "sceneBridge.move_node",
            "sceneBridge.resize_node",
            "viewBridge.adjust_zoom",
            "viewBridge.pan_by",
            "viewBridge.set_viewport_size",
            "viewBridge.zoom_value",
            "viewBridge.center_x",
            "viewBridge.center_y",
            "property var hoveredPort: null",
            "property var pendingConnectionPort: null",
            "property var wireDragState: null",
            "property bool edgeContextVisible: false",
            "property bool interactionActive: false",
            "readonly property var _canvasCommandBridgeRef",
            "readonly property var _canvasShellBridgeRef",
            "readonly property var _canvasSceneBridgeRef",
            "readonly property var _canvasViewBridgeRef",
            "readonly property var _canvasShellCompatRef",
            "readonly property var _canvasSceneCompatRef",
            "readonly property var _canvasViewCompatRef",
            "readonly property var _canvasCompatBridgeRef",
        )
        present_snippets = (
            "property var canvasStateBridge: null",
            "property var canvasCommandBridge: null",
            "readonly property var canvasStateBridgeRef",
            "readonly property var canvasCommandBridgeRef",
            "readonly property var _canvasStateBridgeRef",
            "readonly property var _canvasSceneStateBridgeRef",
            "readonly property var _canvasViewStateBridgeRef",
            "readonly property var _canvasShellCommandBridgeRef",
            "readonly property var _canvasSceneCommandBridgeRef",
            "readonly property var _canvasViewCommandBridgeRef",
            "readonly property var sceneBridge: root._canvasSceneStateBridgeRef",
            "readonly property var viewBridge: root._canvasViewStateBridgeRef",
            "root._canvasStateBridgeRef.graphics_show_grid",
            "root._canvasSceneStateBridgeRef.nodes_model",
            "GraphCanvasComponents.GraphCanvasInteractionState {",
            "GraphCanvasComponents.GraphCanvasSceneState {",
            "GraphCanvasComponents.GraphCanvasNodeSurfaceBridge {",
            "GraphCanvasComponents.GraphCanvasWorldLayer {",
            "property alias hoveredPort: interactionState.hoveredPort",
            "property alias pendingConnectionPort: interactionState.pendingConnectionPort",
            "property alias interactionActive: interactionState.interactionActive",
            "interactionState.updateLibraryDropPreview(screenX, screenY, payload);",
            "interactionState.beginPortWireDrag(nodeId, portKey, direction, sceneX, sceneY, screenX, screenY);",
            "var bridge = root._canvasShellCommandBridgeRef",
            "var view = root._canvasViewStateBridgeRef",
            "viewBridge: root._canvasViewStateBridgeRef",
            "sceneBridge: root._canvasSceneStateBridgeRef",
            "shellCommandBridge: root._canvasShellCommandBridgeRef",
            "sceneCommandBridge: root._canvasSceneCommandBridgeRef",
            "sceneStateBridge: root._canvasSceneStateBridgeRef",
            "viewStateBridge: root._canvasViewStateBridgeRef",
            "viewCommandBridge: root._canvasViewCommandBridgeRef",
            "target: root._canvasSceneStateBridgeRef",
            "target: root._canvasViewStateBridgeRef",
        )

        _assert_text_snippets(
            self,
            label=relative_path,
            text=qml_text,
            absent_snippets=absent_snippets,
            present_snippets=present_snippets,
        )

    def test_graph_canvas_interaction_state_helper_owns_extracted_canvas_state(self) -> None:
        relative_path = "ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml"
        helper_text = (_REPO_ROOT / relative_path).read_text(encoding="utf-8")

        present_snippets = (
            "property var pendingConnectionPort: null",
            "property var wireDragState: null",
            "property bool edgeContextVisible: false",
            "property bool interactionActive: false",
            "property var interactionIdleTimer: null",
            "function updateLibraryDropPreview(screenX, screenY, payload) {",
            "function finishPortWireDrag(nodeId, portKey, direction, _sceneX, _sceneY, screenX, screenY, dragActive) {",
            "function _openNodeContext(nodeId, x, y) {",
            "function resetSceneBridgeState() {",
        )

        _assert_text_snippets(
            self,
            label=relative_path,
            text=helper_text,
            present_snippets=present_snippets,
        )

    def test_graph_canvas_helper_components_hold_scene_surface_and_delegate_logic(self) -> None:
        expectations = {
            "ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasSceneState.qml": (
                "property var selectedEdgeIds: []",
                "function sceneNodePayload(nodeId) {",
                "function syncEdgePayload() {",
                'bridge && typeof bridge.selected_node_lookup !== "undefined"',
            ),
            "ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeSurfaceBridge.qml": (
                "function requestOpenSubnodeScope(nodeId) {",
                "function commitNodeSurfaceProperties(nodeId, properties) {",
                "function browseNodePropertyPath(nodeId, key, currentPath) {",
                "var bridge = root.canvasItem ? root.canvasItem._canvasSceneCommandBridgeRef : null;",
            ),
            "ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeDelegate.qml": (
                "GraphComponents.GraphNodeHost {",
                "property bool backdropInputOverlay: false",
                "canvasItem.requestEdgeRedraw",
            ),
            "ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasWorldLayer.qml": (
                "property bool backdropInputOverlay: false",
                "delegate: GraphCanvasNodeDelegate {",
                "scale: viewBridge ? viewBridge.zoom_value : 1.0",
            ),
        }

        for relative_path, present_snippets in expectations.items():
            qml_text = (_REPO_ROOT / relative_path).read_text(encoding="utf-8")
            _assert_text_snippets(
                self,
                label=relative_path,
                text=qml_text,
                present_snippets=present_snippets,
            )

    def test_overlay_host_item_plumbing_remains_live_for_canvas_overlay_paths(self) -> None:
        expectations = {
            "ea_node_editor/ui_qml/MainShell.qml": (
                "WorkspaceCenterPane {",
                "overlayHostItem: root",
            ),
            "ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml": (
                "property var overlayHostItem",
                "overlayHostItem: root.overlayHostItem",
            ),
            "ea_node_editor/ui_qml/components/GraphCanvas.qml": (
                "property var overlayHostItem: null",
            ),
            "ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml": (
                "var overlayHost = root.canvasItem.overlayHostItem || root.canvasItem;",
            ),
            "ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml": (
                "root.canvasItem.overlayHostItem ? root.canvasItem.overlayHostItem : root.canvasItem",
            ),
        }

        for relative_path, present_snippets in expectations.items():
            qml_text = (_REPO_ROOT / relative_path).read_text(encoding="utf-8")
            _assert_text_snippets(
                self,
                label=relative_path,
                text=qml_text,
                present_snippets=present_snippets,
            )


class _MainWindowShellGraphCanvasHostDirectTests(MainWindowShellTestBase):
    __test__ = os.environ.get(_GRAPH_CANVAS_HOST_DIRECT_ENV) == "1"

    def test_graph_canvas_host_binds_split_canvas_bridge_refs_to_registered_context_bridges(self) -> None:
        graph_canvas = self._graph_canvas_item()
        context = self.window.quick_widget.rootContext()
        graph_canvas_state_bridge = context.contextProperty("graphCanvasStateBridge")
        graph_canvas_command_bridge = context.contextProperty("graphCanvasCommandBridge")
        canvas_state_bridge = graph_canvas.property("canvasStateBridge")
        canvas_command_bridge = graph_canvas.property("canvasCommandBridge")
        canvas_state_bridge_ref = graph_canvas.property("canvasStateBridgeRef")
        canvas_command_bridge_ref = graph_canvas.property("canvasCommandBridgeRef")

        self.assertIsNone(context.contextProperty("graphCanvasBridge"))
        self.assertIsInstance(graph_canvas_state_bridge, GraphCanvasStateBridge)
        self.assertIsInstance(graph_canvas_command_bridge, GraphCanvasCommandBridge)
        self.assertIs(self.window.graph_canvas_state_bridge, graph_canvas_state_bridge)
        self.assertIs(self.window.graph_canvas_command_bridge, graph_canvas_command_bridge)
        self.assertEqual(graph_canvas.objectName(), "graphCanvas")
        self.assertIsInstance(canvas_state_bridge, GraphCanvasStateBridge)
        self.assertIs(canvas_state_bridge, graph_canvas_state_bridge)
        self.assertIsInstance(canvas_command_bridge, GraphCanvasCommandBridge)
        self.assertIs(canvas_command_bridge, graph_canvas_command_bridge)
        self.assertIsInstance(canvas_state_bridge_ref, GraphCanvasStateBridge)
        self.assertIs(canvas_state_bridge_ref, graph_canvas_state_bridge)
        self.assertIsInstance(canvas_command_bridge_ref, GraphCanvasCommandBridge)
        self.assertIs(canvas_command_bridge_ref, graph_canvas_command_bridge)
        self.assertIsNone(graph_canvas.property("canvasBridge"))
        self.assertIsNone(graph_canvas.property("canvasBridgeRef"))
        self.assertEqual(
            bool(graph_canvas.property("showGrid")),
            graph_canvas_state_bridge.graphics_show_grid,
        )
        self.assertEqual(
            bool(graph_canvas.property("minimapVisible")),
            graph_canvas_state_bridge.graphics_show_minimap,
        )
        self.assertEqual(
            bool(graph_canvas.property("minimapExpanded")),
            graph_canvas_state_bridge.graphics_minimap_expanded,
        )

    def test_graph_canvas_keeps_graph_node_card_discoverability_after_host_refactor(self) -> None:
        graph_canvas = self._graph_canvas_item()
        self.window.scene.add_node_from_type("core.logger", 180.0, 120.0)
        self.app.processEvents()

        node_cards = _named_child_items(graph_canvas, "graphNodeCard")
        self.assertGreaterEqual(len(node_cards), 1)
        self.assertIsNotNone(node_cards[0].findChild(QObject, "graphNodeStandardSurface"))

    def test_plain_text_graph_fragment_payload_is_ignored_by_paste(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        self.window.scene.add_node_from_type("core.start", x=25.0, y=35.0)
        before_state = self._workspace_state()
        before_depth = self.window.runtime_history.undo_depth(workspace_id)
        clipboard = self.app.clipboard()

        valid_text_payload = serialize_graph_fragment_payload(
            build_graph_fragment_payload(
                nodes=[
                    {
                        "ref_id": "ref-start",
                        "type_id": "core.start",
                        "title": "Start",
                        "x": 0.0,
                        "y": 0.0,
                        "collapsed": False,
                        "properties": {},
                        "exposed_ports": {},
                        "visual_style": {},
                        "parent_node_id": None,
                    }
                ],
                edges=[],
            )
        )
        self.assertIsNotNone(valid_text_payload)
        clipboard.setText(str(valid_text_payload))

        pasted = self.window.request_paste_selected_nodes()
        self.assertFalse(pasted)
        self.assertEqual(self._workspace_state(), before_state)
        self.assertEqual(self.window.runtime_history.undo_depth(workspace_id), before_depth)

    def test_graph_search_results_use_user_facing_instance_ids_for_duplicate_nodes(self) -> None:
        first_node_id = self.window.scene.add_node_from_type("core.start", x=40.0, y=40.0)
        second_node_id = self.window.scene.add_node_from_type("core.start", x=260.0, y=40.0)
        self.window.scene.set_node_title(first_node_id, "Duplicate Search Alpha")
        self.window.scene.set_node_title(second_node_id, "Duplicate Search Beta")
        self.app.processEvents()

        self.window.action_graph_search.trigger()
        self.window.set_graph_search_query("duplicate search")
        self.app.processEvents()

        results_by_id = {item["node_id"]: item for item in self.window.graph_search_results}
        self.assertEqual(results_by_id[first_node_id]["instance_number"], 1)
        self.assertEqual(results_by_id[first_node_id]["instance_label"], "ID 1")
        self.assertEqual(results_by_id[second_node_id]["instance_number"], 2)
        self.assertEqual(results_by_id[second_node_id]["instance_label"], "ID 2")


class MainWindowShellGraphCanvasHostTests(unittest.TestCase):
    __test__ = True

    def test_class_runs_in_subprocess(self) -> None:
        _run_pytest_shell_class_nodeid(
            "tests/test_main_window_shell.py::_MainWindowShellGraphCanvasHostDirectTests",
            extra_env={_GRAPH_CANVAS_HOST_DIRECT_ENV: "1"},
        )


class MainWindowShellHostFacadeDelegationTests(SharedMainWindowShellTestBase):
    def test_host_slots_delegate_nontrivial_host_logic_to_shell_host_presenter(self) -> None:
        self.assertIsNotNone(self.window.shell_host_presenter)

        with (
            patch.object(self.window.shell_host_presenter, "show_graphics_settings_dialog") as show_graphics_mock,
            patch.object(self.window.shell_host_presenter, "set_graph_cursor_shape") as set_cursor_mock,
            patch.object(
                self.window.shell_host_presenter,
                "request_edit_passive_node_style",
                return_value=True,
            ) as edit_passive_style_mock,
        ):
            self.window.show_graphics_settings_dialog()
            self.window.set_graph_cursor_shape(3)
            result = self.window.request_edit_passive_node_style("node-1")

        show_graphics_mock.assert_called_once_with(False)
        set_cursor_mock.assert_called_once_with(3)
        edit_passive_style_mock.assert_called_once_with("node-1")
        self.assertTrue(result)


def load_tests(loader: unittest.TestLoader, _tests, _pattern):  # noqa: ANN001
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(FrameRateSamplerTests))
    suite.addTests(loader.loadTestsFromTestCase(ShellLibraryBridgeTests))
    suite.addTests(loader.loadTestsFromTestCase(ShellInspectorBridgeTests))
    suite.addTests(loader.loadTestsFromTestCase(ShellWorkspaceBridgeTests))
    suite.addTests(loader.loadTestsFromTestCase(ShellLibraryBridgeQmlBoundaryTests))
    suite.addTests(loader.loadTestsFromTestCase(ShellInspectorBridgeQmlBoundaryTests))
    suite.addTests(loader.loadTestsFromTestCase(ShellWorkspaceBridgeQmlBoundaryTests))
    suite.addTests(loader.loadTestsFromTestCase(GraphCanvasQmlBoundaryTests))
    suite.addTests(loader.loadTestsFromTestCase(MainWindowShellPassiveImageNodesTests))
    suite.addTests(loader.loadTestsFromTestCase(MainWindowShellPassivePdfNodesTests))
    suite.addTests(loader.loadTestsFromTestCase(MainWindowShellGraphCanvasHostTests))

    shell_classes: list[type[SharedMainWindowShellTestBase]] = []
    for candidate in globals().values():
        if not isinstance(candidate, type):
            continue
        if not issubclass(candidate, SharedMainWindowShellTestBase):
            continue
        if candidate is SharedMainWindowShellTestBase:
            continue
        shell_classes.append(candidate)

    for case_type in sorted(shell_classes, key=lambda item: (item.__module__, item.__name__)):
        suite.addTests(loader.loadTestsFromTestCase(case_type))
    return suite


if __name__ == "__main__":
    unittest.main()
