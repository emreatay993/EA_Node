from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

from PyQt6.QtCore import QMetaObject

from tests.main_window_shell.base import MainWindowShellTestBase, SharedMainWindowShellTestBase
from tests.main_window_shell.bridge_contracts import (
    FrameRateSampler,
    GraphCanvasBridge,
    GraphCanvasCommandBridge,
    GraphCanvasStateBridge,
    QObject,
    ShellInspectorBridge,
    ShellLibraryBridge,
    ShellWorkspaceBridge,
    _GRAPH_CANVAS_HOST_DIRECT_ENV,
    _PASSIVE_IMAGE_DIRECT_ENV,
    _PASSIVE_PDF_DIRECT_ENV,
    _REPO_ROOT,
    _named_child_items,
    build_graph_fragment_payload,
    serialize_graph_fragment_payload,
)
from ea_node_editor.ui_qml.shell_context_bootstrap import ShellContextBundle
from ea_node_editor.ui_qml.viewer_host_service import ViewerHostService
from ea_node_editor.ui_qml.viewer_session_bridge import ViewerSessionBridge


_CONTENT_FULLSCREEN_PACKET_FILES = (
    _REPO_ROOT / "ea_node_editor" / "ui_qml" / "MainShell.qml",
    _REPO_ROOT / "ea_node_editor" / "ui_qml" / "ContentFullscreenOverlay.qml",
)


def _packet_file_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _status_strip_items(window) -> tuple[QObject, QObject, QObject, QObject]:
    root_object = window.quick_widget.rootObject()
    if root_object is None:
        raise AssertionError("Expected QML root object")

    status_strip = root_object.findChild(QObject, "shellStatusStrip")
    summary = root_object.findChild(QObject, "shellStatusStripGraphicsModeSummary")
    full_button = root_object.findChild(QObject, "shellStatusStripFullFidelityButton")
    max_button = root_object.findChild(QObject, "shellStatusStripMaxPerformanceButton")
    if status_strip is None or summary is None or full_button is None or max_button is None:
        raise AssertionError("Expected status-strip graphics mode controls")
    return status_strip, summary, full_button, max_button


class FrameRateSamplerTests(unittest.TestCase):
    def test_snapshot_is_zero_without_enough_frames(self) -> None:
        sampler = FrameRateSampler(window_seconds=1.0)

        self.assertEqual(sampler.snapshot(timestamp=1.0).fps, 0.0)

        sampler.record_frame(timestamp=1.25)
        sample = sampler.snapshot(timestamp=1.25)
        self.assertEqual(sample.fps, 0.0)
        self.assertEqual(sample.sample_count, 1)

    def test_snapshot_reports_average_fps_within_recent_window(self) -> None:
        sampler = FrameRateSampler(window_seconds=1.0)
        for timestamp in (10.0, 10.2, 10.4, 10.6):
            sampler.record_frame(timestamp=timestamp)

        sample = sampler.snapshot(timestamp=10.6)

        self.assertAlmostEqual(sample.fps, 5.0, places=4)
        self.assertEqual(sample.sample_count, 4)

    def test_snapshot_drops_stale_frames_and_returns_idle_zero(self) -> None:
        sampler = FrameRateSampler(window_seconds=0.5)
        for timestamp in (20.0, 20.1, 20.2):
            sampler.record_frame(timestamp=timestamp)

        self.assertGreater(sampler.snapshot(timestamp=20.2).fps, 0.0)
        self.assertEqual(sampler.snapshot(timestamp=20.8).fps, 0.0)


class MainWindowShellTelemetryTests(SharedMainWindowShellTestBase):
    def test_update_system_metrics_can_render_explicit_fps_value(self) -> None:
        self.window.update_system_metrics(37.0, 4.3, 16.0, fps=58.0)
        self.app.processEvents()

        self.assertEqual(self.window.status_metrics.text(), "FPS:58 CPU:37% RAM:4.3/16.0 GB")


class MainWindowShellBootstrapCompositionTests(SharedMainWindowShellTestBase):
    def test_bootstrap_starts_runtime_timers_with_expected_modes(self) -> None:
        self.assertTrue(self.window.metrics_timer.isActive())
        self.assertEqual(self.window.metrics_timer.interval(), 1000)
        self.assertFalse(self.window.graph_hint_timer.isActive())
        self.assertTrue(self.window.graph_hint_timer.isSingleShot())
        self.assertTrue(self.window.autosave_timer.isActive())


class MainWindowShellContextBootstrapTests(SharedMainWindowShellTestBase):
    def test_qml_context_removes_raw_canvas_globals_and_registers_bridge_first_facades(self) -> None:
        context = self.window.quick_widget.rootContext()

        expected_context_names = (
            "shellContext",
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
            "viewerSessionBridge",
            "viewerHostService",
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
        shell_context = context.contextProperty("shellContext")
        self.assertIsInstance(shell_context, ShellContextBundle)
        self.assertIs(shell_context, self.window.shell_context)
        self.assertIsInstance(shell_library_bridge, ShellLibraryBridge)
        self.assertIsNone(shell_library_bridge.shell_window)
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
        self.assertIsNone(shell_inspector_bridge.shell_window)
        self.assertIs(shell_inspector_bridge.inspector_source, self.window.shell_inspector_presenter)
        self.assertIs(shell_inspector_bridge.scene_bridge, self.window.scene)

        graph_canvas_state_bridge = context.contextProperty("graphCanvasStateBridge")
        self.assertIsInstance(graph_canvas_state_bridge, GraphCanvasStateBridge)
        self.assertIs(graph_canvas_state_bridge.parent(), self.window)
        self.assertIsNone(graph_canvas_state_bridge.shell_window)
        self.assertIs(graph_canvas_state_bridge.canvas_source, self.window.graph_canvas_presenter)
        self.assertIs(graph_canvas_state_bridge.graphics_source, self.window.shell_workspace_presenter)
        self.assertIs(graph_canvas_state_bridge.execution_source, self.window)
        self.assertIs(graph_canvas_state_bridge.scene_bridge, self.window.scene)
        self.assertIs(graph_canvas_state_bridge.view_bridge, self.window.view)

        graph_canvas_command_bridge = context.contextProperty("graphCanvasCommandBridge")
        self.assertIsInstance(graph_canvas_command_bridge, GraphCanvasCommandBridge)
        self.assertIs(graph_canvas_command_bridge.parent(), self.window)
        self.assertIsNone(graph_canvas_command_bridge.shell_window)
        self.assertIs(graph_canvas_command_bridge.canvas_source, self.window.graph_canvas_presenter)
        self.assertIs(graph_canvas_command_bridge.host_source, self.window.graph_canvas_host_presenter)
        self.assertIs(graph_canvas_command_bridge.scene_bridge, self.window.scene)
        self.assertIs(graph_canvas_command_bridge.view_bridge, self.window.view)

        viewer_session_bridge = context.contextProperty("viewerSessionBridge")
        self.assertIsInstance(viewer_session_bridge, ViewerSessionBridge)
        self.assertIs(viewer_session_bridge.parent(), self.window)
        self.assertEqual(
            viewer_session_bridge.active_workspace_id,
            self.window.workspace_manager.active_workspace_id(),
        )

        viewer_host_service = context.contextProperty("viewerHostService")
        self.assertIsInstance(viewer_host_service, ViewerHostService)
        self.assertIs(viewer_host_service.parent(), self.window)
        self.assertIs(viewer_host_service.overlay_manager, self.window.embedded_viewer_overlay_manager)

        context_bindings = dict(self.window._shell_qml_context_property_bindings)
        self.assertIs(context_bindings["shellContext"], shell_context)
        self.assertIs(context_bindings["shellLibraryBridge"], shell_library_bridge)
        self.assertIs(context_bindings["shellWorkspaceBridge"], shell_workspace_bridge)
        self.assertIs(context_bindings["shellInspectorBridge"], shell_inspector_bridge)
        self.assertIs(context_bindings["graphCanvasStateBridge"], graph_canvas_state_bridge)
        self.assertIs(context_bindings["graphCanvasCommandBridge"], graph_canvas_command_bridge)
        self.assertIs(context_bindings["viewerSessionBridge"], viewer_session_bridge)
        self.assertIs(context_bindings["viewerHostService"], viewer_host_service)

    def test_shell_window_keeps_bridge_aliases_in_sync_with_context_bundle(self) -> None:
        bridges = self.window._shell_context_bridges

        self.assertIs(self.window.shell_library_bridge, bridges.shell_library_bridge)
        self.assertIs(self.window.shell_workspace_bridge, bridges.shell_workspace_bridge)
        self.assertIs(self.window.shell_inspector_bridge, bridges.shell_inspector_bridge)
        self.assertIs(self.window.graph_canvas_state_bridge, bridges.graph_canvas_state_bridge)
        self.assertIs(self.window.graph_canvas_command_bridge, bridges.graph_canvas_command_bridge)
        self.assertIs(
            self.window.viewer_session_bridge,
            dict(self.window._shell_qml_context_property_bindings)["viewerSessionBridge"],
        )
        self.assertIs(
            self.window.viewer_host_service,
            dict(self.window._shell_qml_context_property_bindings)["viewerHostService"],
        )


class MainWindowShellStatusStripQuickToggleTests(SharedMainWindowShellTestBase):
    def test_status_strip_quick_toggle_reflects_current_mode_and_copy(self) -> None:
        _status_strip, summary, full_button, max_button = _status_strip_items(self.window)

        self.assertEqual(summary.property("text"), "Graphics: Full Fidelity")
        self.assertEqual(full_button.property("text"), "Full Fidelity")
        self.assertEqual(max_button.property("text"), "Max Performance")
        self.assertEqual(
            full_button.property("tooltipText"),
            "Keeps normal visual quality and applies only invisible structural optimizations.",
        )
        self.assertEqual(
            max_button.property("tooltipText"),
            "Temporarily simplifies whole-canvas rendering during pan, zoom, and burst edits; idle quality restores automatically.",
        )
        self.assertTrue(bool(full_button.property("selectedStyle")))
        self.assertFalse(bool(max_button.property("selectedStyle")))

        self.window.app_preferences_controller.set_graphics_settings(
            {
                "performance": {
                    "mode": "max_performance",
                }
            },
            host=self.window,
        )
        self.app.processEvents()

        self.assertEqual(self.window.graphics_performance_mode, "max_performance")
        self.assertEqual(summary.property("text"), "Graphics: Max Performance")
        self.assertFalse(bool(full_button.property("selectedStyle")))
        self.assertTrue(bool(max_button.property("selectedStyle")))

    def test_status_strip_quick_toggle_persists_mode_changes(self) -> None:
        _status_strip, summary, full_button, max_button = _status_strip_items(self.window)

        QMetaObject.invokeMethod(max_button, "click")
        self.app.processEvents()

        self.assertEqual(self.window.graphics_performance_mode, "max_performance")
        self.assertEqual(summary.property("text"), "Graphics: Max Performance")
        self.assertFalse(bool(full_button.property("selectedStyle")))
        self.assertTrue(bool(max_button.property("selectedStyle")))

        self._reopen_shared_window()
        _status_strip, reopened_summary, reopened_full_button, reopened_max_button = _status_strip_items(self.window)

        self.assertEqual(self.window.graphics_performance_mode, "max_performance")
        self.assertEqual(reopened_summary.property("text"), "Graphics: Max Performance")
        self.assertFalse(bool(reopened_full_button.property("selectedStyle")))
        self.assertTrue(bool(reopened_max_button.property("selectedStyle")))

        QMetaObject.invokeMethod(reopened_full_button, "click")
        self.app.processEvents()

        self.assertEqual(self.window.graphics_performance_mode, "full_fidelity")
        self.assertEqual(reopened_summary.property("text"), "Graphics: Full Fidelity")
        self.assertTrue(bool(reopened_full_button.property("selectedStyle")))
        self.assertFalse(bool(reopened_max_button.property("selectedStyle")))


class MainWindowShellContentFullscreenStaticContractsTests(unittest.TestCase):
    def test_content_fullscreen_overlay_is_shell_owned_and_bridge_gated(self) -> None:
        main_shell = _packet_file_text(_CONTENT_FULLSCREEN_PACKET_FILES[0])
        overlay = _packet_file_text(_CONTENT_FULLSCREEN_PACKET_FILES[1])

        self.assertIn("ContentFullscreenOverlay", main_shell)
        self.assertIn("bridgeRef: root.contentFullscreenBridgeRef", main_shell)
        self.assertIn('objectName: "contentFullscreenOverlay"', overlay)
        self.assertIn("readonly property bool bridgeOpen", overlay)
        self.assertIn("root.bridgeRef.open", overlay)
        self.assertIn("root.bridgeRef.request_close()", overlay)

    def test_content_fullscreen_overlay_declares_media_modes_and_viewer_viewport(self) -> None:
        overlay = _packet_file_text(_CONTENT_FULLSCREEN_PACKET_FILES[1])

        for snippet in (
            'objectName: "contentFullscreenMediaViewport"',
            'objectName: "contentFullscreenMediaImage"',
            'objectName: "contentFullscreenDisplayModeFitButton"',
            'objectName: "contentFullscreenDisplayModeFillButton"',
            'objectName: "contentFullscreenDisplayModeActualButton"',
            'objectName: "contentFullscreenViewerViewport"',
            "GraphMediaPanelGeometry.sourceClipRectFromNormalized",
            "sourceClipRect: root._sourceClipRect()",
            "root.mediaPayload.preview_url",
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, overlay)

    def test_content_fullscreen_overlay_blocks_background_and_handles_close_keys(self) -> None:
        overlay = _packet_file_text(_CONTENT_FULLSCREEN_PACKET_FILES[1])

        for snippet in (
            'objectName: "contentFullscreenInteractionBlocker"',
            "acceptedButtons: Qt.AllButtons",
            "event.key === Qt.Key_Escape",
            "event.key === Qt.Key_F11",
            'objectName: "contentFullscreenCloseButton"',
        ):
            with self.subTest(snippet=snippet):
                self.assertIn(snippet, overlay)


class MainWindowShellHostProtocolStateTests(SharedMainWindowShellTestBase):
    def test_search_scope_state_tracks_graph_search_quick_insert_and_hints(self) -> None:
        self.window.action_graph_search.trigger()
        self.window.set_graph_search_query("core.start")
        self.app.processEvents()

        graph_search_state = self.window.search_scope_state.graph_search
        self.assertTrue(graph_search_state.open)
        self.assertEqual(graph_search_state.query, "core.start")
        self.assertEqual(graph_search_state.enabled_scopes, ["title", "type", "content", "port"])
        self.assertEqual(graph_search_state.results, self.window.graph_search_results)

        self.window.request_open_canvas_quick_insert(40.0, 55.0, 120.0, 180.0)
        self.app.processEvents()

        quick_insert_state = self.window.search_scope_state.connection_quick_insert
        self.assertTrue(quick_insert_state.open)
        self.assertEqual(quick_insert_state.context["mode"], "canvas_insert")
        self.assertEqual(quick_insert_state.context["overlay_x"], 120.0)
        self.assertEqual(quick_insert_state.results, [])
        self.assertEqual(quick_insert_state.highlight_index, -1)
        self.assertEqual(quick_insert_state.results, self.window.connection_quick_insert_results)

        self.window.set_connection_quick_insert_query("start")
        self.app.processEvents()

        quick_insert_state = self.window.search_scope_state.connection_quick_insert
        self.assertEqual(quick_insert_state.query, "start")
        self.assertEqual(quick_insert_state.highlight_index, 0)
        self.assertGreaterEqual(len(quick_insert_state.results), 2)
        self.assertIn(
            "core.start",
            {str(item.get("type_id", "")) for item in quick_insert_state.results},
        )
        self.assertIn(
            "passive.flowchart.start",
            {str(item.get("type_id", "")) for item in quick_insert_state.results},
        )

        self.window.set_connection_quick_insert_query("   ")
        self.app.processEvents()

        quick_insert_state = self.window.search_scope_state.connection_quick_insert
        self.assertEqual(quick_insert_state.query, "   ")
        self.assertEqual(quick_insert_state.results, [])
        self.assertEqual(quick_insert_state.highlight_index, -1)

        self.window.show_graph_hint("Packet hint", 500)
        self.assertEqual(self.window.search_scope_state.graph_hint_message, "Packet hint")
        self.window.clear_graph_hint()
        self.assertEqual(self.window.search_scope_state.graph_hint_message, "")

    def test_scope_camera_cache_is_owned_by_search_scope_state(self) -> None:
        self.window.view.set_zoom(1.35)
        self.window.view.centerOn(140.0, -75.0)

        self.window._remember_scope_camera()

        key = self.window._active_scope_camera_key()
        self.assertIsNotNone(key)
        if key is None:
            self.fail("Expected active scope camera key")
        self.assertIn(key, self.window.search_scope_state.runtime_scope_camera)


class _MainWindowShellGraphCanvasHostDirectTests(MainWindowShellTestBase):
    __test__ = os.environ.get(_GRAPH_CANVAS_HOST_DIRECT_ENV) == "1"

    def test_graph_canvas_host_binds_canvas_bridge_ref_to_registered_graph_canvas_bridge(self) -> None:
        graph_canvas = self._graph_canvas_item()
        context = self.window.quick_widget.rootContext()
        graph_canvas_state_bridge = context.contextProperty("graphCanvasStateBridge")
        graph_canvas_command_bridge = context.contextProperty("graphCanvasCommandBridge")
        canvas_bridge = graph_canvas.property("canvasBridge")
        canvas_state_bridge = graph_canvas.property("canvasStateBridge")
        canvas_command_bridge = graph_canvas.property("canvasCommandBridge")
        canvas_bridge_ref = graph_canvas.property("canvasBridgeRef")

        self.assertIsInstance(graph_canvas_state_bridge, GraphCanvasStateBridge)
        self.assertIsInstance(graph_canvas_command_bridge, GraphCanvasCommandBridge)
        self.assertIsNone(context.contextProperty("graphCanvasBridge"))
        self.assertIsInstance(self.window.graph_canvas_bridge, GraphCanvasBridge)
        self.assertEqual(graph_canvas.objectName(), "graphCanvas")
        self.assertIsInstance(canvas_state_bridge, GraphCanvasStateBridge)
        self.assertIs(canvas_state_bridge, graph_canvas_state_bridge)
        self.assertIsInstance(canvas_command_bridge, GraphCanvasCommandBridge)
        self.assertIs(canvas_command_bridge, graph_canvas_command_bridge)
        self.assertIsNone(canvas_bridge)
        self.assertIsNone(canvas_bridge_ref)
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

        results_by_id = {
            item["node_id"]: item
            for item in self.window.graph_search_results
        }
        self.assertEqual(results_by_id[first_node_id]["instance_number"], 1)
        self.assertEqual(results_by_id[first_node_id]["instance_label"], "ID 1")
        self.assertEqual(results_by_id[second_node_id]["instance_number"], 2)
        self.assertEqual(results_by_id[second_node_id]["instance_label"], "ID 2")


class _PytestSubprocessShellClassTest(unittest.TestCase):
    __test__ = False

    _pytest_nodeid = ""
    _extra_env: dict[str, str] = {}

    def test_class_runs_in_subprocess(self) -> None:
        assert self._pytest_nodeid
        _run_pytest_shell_class_nodeid(self._pytest_nodeid, extra_env=self._extra_env)


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


class MainWindowShellPassiveImageNodesTests(_PytestSubprocessShellClassTest):
    __test__ = True
    _pytest_nodeid = "tests/main_window_shell/passive_image_nodes.py::MainWindowShellPassiveImageNodesTests"
    _extra_env = {_PASSIVE_IMAGE_DIRECT_ENV: "1"}


class MainWindowShellPassivePdfNodesTests(_PytestSubprocessShellClassTest):
    __test__ = True
    _pytest_nodeid = "tests/main_window_shell/passive_pdf_nodes.py::MainWindowShellPassivePdfNodesTests"
    _extra_env = {_PASSIVE_PDF_DIRECT_ENV: "1"}


class MainWindowShellGraphCanvasHostTests(_PytestSubprocessShellClassTest):
    __test__ = True
    _pytest_nodeid = "tests/test_main_window_shell.py::_MainWindowShellGraphCanvasHostDirectTests"
    _extra_env = {_GRAPH_CANVAS_HOST_DIRECT_ENV: "1"}


__all__ = [
    "FrameRateSamplerTests",
    "MainWindowShellTelemetryTests",
    "MainWindowShellBootstrapCompositionTests",
    "MainWindowShellContextBootstrapTests",
    "MainWindowShellStatusStripQuickToggleTests",
    "MainWindowShellContentFullscreenStaticContractsTests",
    "MainWindowShellHostProtocolStateTests",
    "_MainWindowShellGraphCanvasHostDirectTests",
    "MainWindowShellPassiveImageNodesTests",
    "MainWindowShellPassivePdfNodesTests",
    "MainWindowShellGraphCanvasHostTests",
]
