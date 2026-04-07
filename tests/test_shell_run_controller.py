from __future__ import annotations

import os
import re
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtCore import QObject
from PyQt6.QtQuick import QQuickItem
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QMessageBox

from ea_node_editor.ui_qml.shell_inspector_bridge import ShellInspectorBridge
from ea_node_editor.ui_qml.shell_library_bridge import ShellLibraryBridge
from ea_node_editor.ui_qml.shell_workspace_bridge import ShellWorkspaceBridge
from ea_node_editor.ui_qml.viewer_session_bridge import ViewerSessionBridge
from tests.main_window_shell.base import MainWindowShellTestBase
from tests.qt_wait import wait_for_condition_or_raise

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SHELL_TEST_RUNNER = (
    "import sys, unittest; "
    "target = sys.argv[1]; "
    "suite = unittest.defaultTestLoader.loadTestsFromName(target); "
    "result = unittest.TextTestRunner(verbosity=2).run(suite); "
    "sys.exit(0 if result.wasSuccessful() else 1)"
)


class _ViewerExecutionClientStub:
    def __init__(self) -> None:
        self.next_run_id = "run_live"
        self.start_calls: list[dict] = []
        self.pause_calls: list[str] = []
        self.resume_calls: list[str] = []
        self.stop_calls: list[str] = []
        self.open_calls: list[dict] = []
        self.update_calls: list[dict] = []
        self.close_calls: list[dict] = []
        self._request_counter = 0

    def _next_request_id(self, prefix: str) -> str:
        self._request_counter += 1
        return f"{prefix}_{self._request_counter}"

    def start_run(self, *, project_path: str, workspace_id: str, trigger: dict) -> str:
        self.start_calls.append(
            {
                "project_path": project_path,
                "workspace_id": workspace_id,
                "trigger": trigger,
            }
        )
        return self.next_run_id

    def pause_run(self, run_id: str) -> None:
        self.pause_calls.append(str(run_id))

    def resume_run(self, run_id: str) -> None:
        self.resume_calls.append(str(run_id))

    def stop_run(self, run_id: str) -> None:
        self.stop_calls.append(str(run_id))

    def open_viewer_session(
        self,
        *,
        workspace_id: str,
        node_id: str,
        session_id: str = "",
        backend_id: str = "",
        data_refs: dict | None = None,
        camera_state: dict | None = None,
        playback_state: dict | None = None,
        summary: dict | None = None,
        options: dict | None = None,
        **extra,
    ) -> str:
        request_id = self._next_request_id("open")
        self.open_calls.append(
            {
                "request_id": request_id,
                "workspace_id": workspace_id,
                "node_id": node_id,
                "session_id": session_id,
                "backend_id": backend_id,
                "data_refs": dict(data_refs or {}),
                "camera_state": dict(camera_state or {}),
                "playback_state": dict(playback_state or {}),
                "summary": dict(summary or {}),
                "options": dict(options or {}),
                "extra": dict(extra),
            }
        )
        return request_id

    def update_viewer_session(
        self,
        *,
        workspace_id: str,
        node_id: str,
        session_id: str,
        backend_id: str = "",
        camera_state: dict | None = None,
        playback_state: dict | None = None,
        summary: dict | None = None,
        options: dict | None = None,
        **extra,
    ) -> str:
        request_id = self._next_request_id("update")
        self.update_calls.append(
            {
                "request_id": request_id,
                "workspace_id": workspace_id,
                "node_id": node_id,
                "session_id": session_id,
                "backend_id": backend_id,
                "camera_state": dict(camera_state or {}),
                "playback_state": dict(playback_state or {}),
                "summary": dict(summary or {}),
                "options": dict(options or {}),
                "extra": dict(extra),
            }
        )
        return request_id

    def close_viewer_session(
        self,
        *,
        workspace_id: str,
        node_id: str,
        session_id: str,
        options: dict | None = None,
        **extra,
    ) -> str:
        request_id = self._next_request_id("close")
        self.close_calls.append(
            {
                "request_id": request_id,
                "workspace_id": workspace_id,
                "node_id": node_id,
                "session_id": session_id,
                "options": dict(options or {}),
                "extra": dict(extra),
            }
        )
        return request_id

    def shutdown(self) -> None:
        return None


def _viewer_opened_event(
    *,
    request_id: str,
    workspace_id: str,
    node_id: str,
    session_id: str,
    **overrides,
) -> dict:
    payload = {
        "type": "viewer_session_opened",
        "request_id": request_id,
        "workspace_id": workspace_id,
        "node_id": node_id,
        "session_id": session_id,
        "data_refs": {},
        "summary": {
            "cache_state": "proxy_ready",
            "result_name": "displacement",
        },
        "options": {
            "session_state": "open",
            "cache_state": "proxy_ready",
            "live_policy": "focus_only",
            "keep_live": False,
            "playback_state": "paused",
            "live_mode": "proxy",
        },
    }
    payload.update(overrides)
    return payload


def _graph_node_card(graph_canvas: QObject, node_id: str) -> QObject | None:
    match: QObject | None = None

    def _walk(item: QObject | None) -> None:
        nonlocal match
        if item is None or match is not None:
            return
        if item.objectName() == "graphNodeCard":
            node_data = item.property("nodeData")
            if isinstance(node_data, dict) and str(node_data.get("node_id", "")) == str(node_id):
                match = item
                return
        child_items = getattr(item, "childItems", None)
        if callable(child_items):
            for child in child_items():
                _walk(child)

    _walk(graph_canvas)
    return match


def _named_qquick_item(root: QObject, object_name: str) -> QQuickItem | None:
    match: QQuickItem | None = None

    def _walk(item: QObject | None) -> None:
        nonlocal match
        if item is None or match is not None or not isinstance(item, QQuickItem):
            return
        if item.objectName() == object_name:
            match = item
            return
        for child in item.childItems():
            _walk(child)

    _walk(root)
    return match


def _variant_payload(value):  # noqa: ANN001
    if value is None:
        return None
    converter = getattr(value, "toVariant", None)
    if callable(converter):
        return converter()
    return value


def _graph_edge_layer(graph_canvas: QObject) -> QObject | None:
    return graph_canvas.findChild(QObject, "graphCanvasEdgeLayer")


def _graph_edge_canvas_layer(graph_canvas: QObject) -> QObject | None:
    return graph_canvas.findChild(QObject, "graphCanvasEdgeCanvasLayer")


def _edge_snapshot_payload(edge_layer: QObject, edge_id: str) -> dict[str, object] | None:
    payload = _variant_payload(edge_layer._visibleEdgeSnapshot(edge_id))
    if payload is None:
        return None
    return payload if isinstance(payload, dict) else dict(payload)


def _edge_paint_diagnostics(edge_canvas_layer: QObject, edge_id: str) -> dict[str, object] | None:
    payload = _variant_payload(edge_canvas_layer.property("_paintDiagnosticsByEdgeId")) or {}
    if not isinstance(payload, dict):
        payload = dict(payload)
    edge_payload = _variant_payload(payload.get(edge_id))
    if edge_payload is None:
        return None
    return edge_payload if isinstance(edge_payload, dict) else dict(edge_payload)


def _build_execution_edge_progress_visualization_graph(window) -> dict[str, str]:  # noqa: ANN001
    start_id = window.scene.add_node_from_type("core.start", x=20.0, y=40.0)
    script_id = window.scene.add_node_from_type("core.python_script", x=150.0, y=40.0)
    on_failure_id = window.scene.add_node_from_type("core.on_failure", x=280.0, y=40.0)
    logger_id = window.scene.add_node_from_type("core.logger", x=410.0, y=40.0)
    end_id = window.scene.add_node_from_type("core.end", x=540.0, y=40.0)
    constant_id = window.scene.add_node_from_type("core.constant", x=410.0, y=200.0)

    exec_edge_id = window.scene.add_edge(start_id, "exec_out", script_id, "exec_in")
    failed_edge_id = window.scene.add_edge(script_id, "on_failed", on_failure_id, "failed_in")
    continuation_edge_id = window.scene.add_edge(on_failure_id, "exec_out", logger_id, "exec_in")
    terminal_edge_id = window.scene.add_edge(logger_id, "exec_out", end_id, "exec_in")
    data_edge_id = window.scene.add_edge(constant_id, "as_text", logger_id, "message")

    return {
        "start_node_id": start_id,
        "script_node_id": script_id,
        "on_failure_node_id": on_failure_id,
        "logger_node_id": logger_id,
        "end_node_id": end_id,
        "constant_node_id": constant_id,
        "exec_edge_id": exec_edge_id,
        "failed_edge_id": failed_edge_id,
        "continuation_edge_id": continuation_edge_id,
        "terminal_edge_id": terminal_edge_id,
        "data_edge_id": data_edge_id,
    }


class ShellRunControllerTests(MainWindowShellTestBase):
    def test_node_execution_visualization_shell_events_drive_graph_node_chrome_states(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("core.logger", x=120.0, y=40.0)
        self.window._active_run_id = "run_live"
        self.window._active_run_workspace_id = workspace_id
        self.window._set_run_ui_state("running", "Running", 1, 0, 0, 0)
        self.app.processEvents()

        graph_canvas = self._graph_canvas_item()
        wait_for_condition_or_raise(
            lambda: _graph_node_card(graph_canvas, node_id) is not None,
            timeout_ms=500,
            app=self.app,
            timeout_message="Timed out waiting for graph node card to appear.",
        )
        node_card = _graph_node_card(graph_canvas, node_id)
        self.assertIsNotNone(node_card)
        if node_card is None:
            self.fail("Expected graph node card to exist")

        background_layer = node_card.findChild(QObject, "graphNodeChromeBackgroundLayer")
        elapsed_timer = node_card.findChild(QObject, "graphNodeElapsedTimer")
        self.assertIsNotNone(background_layer)
        self.assertIsNotNone(elapsed_timer)
        self.assertFalse(bool(node_card.property("isRunningNode")))
        self.assertFalse(bool(node_card.property("isCompletedNode")))
        self.assertEqual(dict(graph_canvas.property("runningNodeLookup")), {})
        self.assertEqual(dict(graph_canvas.property("completedNodeLookup")), {})

        self.window.execution_event.emit(
            {
                "type": "run_started",
                "run_id": "run_live",
                "workspace_id": workspace_id,
            }
        )
        self.window.execution_event.emit(
            {
                "type": "node_started",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": node_id,
            }
        )
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: bool(node_card.property("isRunningNode"))
            and str(background_layer.property("effectiveBorderState")) == "running"
            and bool(elapsed_timer.property("visible")),
            timeout_ms=400,
            app=self.app,
            timeout_message="Timed out waiting for running-node execution chrome.",
        )
        self.assertTrue(bool(node_card.property("renderActive")))
        self.assertEqual(int(node_card.property("z")), 31)
        self.assertEqual(dict(graph_canvas.property("runningNodeLookup")), {node_id: True})

        QTest.qWait(160)
        self.app.processEvents()
        elapsed_text = str(elapsed_timer.property("text") or "")
        self.assertRegex(elapsed_text, re.compile(r"^\d+\.\ds$"))
        self.assertNotEqual(elapsed_text, "0.0s")

        self.window.execution_event.emit(
            {
                "type": "node_completed",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": node_id,
                "outputs": {"exit_code": 0},
            }
        )
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: bool(node_card.property("isCompletedNode"))
            and not bool(node_card.property("isRunningNode"))
            and str(background_layer.property("effectiveBorderState")) == "completed"
            and not bool(elapsed_timer.property("visible")),
            timeout_ms=400,
            app=self.app,
            timeout_message="Timed out waiting for completed-node execution chrome.",
        )
        self.assertIn(int(node_card.property("z")), {29, 30})
        self.assertEqual(dict(graph_canvas.property("runningNodeLookup")), {})
        self.assertEqual(dict(graph_canvas.property("completedNodeLookup")), {node_id: True})

        QTest.qWait(80)
        self.app.processEvents()
        self.assertGreater(float(background_layer.property("completedFlashProgress")), 0.0)

        self.window.execution_event.emit(
            {
                "type": "run_completed",
                "run_id": "run_live",
                "workspace_id": workspace_id,
            }
        )
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: not bool(node_card.property("isCompletedNode"))
            and not bool(node_card.property("isRunningNode")),
            timeout_ms=400,
            app=self.app,
            timeout_message="Timed out waiting for execution visualization cleanup after run completion.",
        )
        self.assertEqual(dict(graph_canvas.property("runningNodeLookup")), {})
        self.assertEqual(dict(graph_canvas.property("completedNodeLookup")), {})
        self.assertIn(str(background_layer.property("effectiveBorderState")), {"idle", "selected"})

    def test_node_execution_visualization_failure_priority_overrides_completed_chrome(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("core.logger", x=180.0, y=120.0)
        graph_canvas = self._graph_canvas_item()

        wait_for_condition_or_raise(
            lambda: _graph_node_card(graph_canvas, node_id) is not None,
            timeout_ms=500,
            app=self.app,
            timeout_message="Timed out waiting for graph node card to appear.",
        )
        node_card = _graph_node_card(graph_canvas, node_id)
        self.assertIsNotNone(node_card)
        if node_card is None:
            self.fail("Expected graph node card to exist")

        background_layer = node_card.findChild(QObject, "graphNodeChromeBackgroundLayer")
        running_halo = node_card.findChild(QObject, "graphNodeRunningHalo")
        completed_flash_halo = node_card.findChild(QObject, "graphNodeCompletedFlashHalo")
        self.assertIsNotNone(background_layer)
        self.assertIsNotNone(running_halo)
        self.assertIsNotNone(completed_flash_halo)

        self.window.mark_node_execution_completed(workspace_id, node_id)
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: bool(node_card.property("isCompletedNode"))
            and str(background_layer.property("effectiveBorderState")) == "completed",
            timeout_ms=400,
            app=self.app,
            timeout_message="Timed out waiting for completed execution chrome before failure priority check.",
        )

        with patch.object(QMessageBox, "critical"):
            self.window._focus_failed_node(workspace_id, node_id, "boom")
        self.app.processEvents()

        self.assertTrue(bool(node_card.property("isFailedNode")))
        self.assertEqual(dict(graph_canvas.property("failedNodeLookup")), {node_id: True})
        self.assertEqual(str(background_layer.property("effectiveBorderState")), "failed")
        self.assertFalse(bool(running_halo.property("visible")))
        self.assertFalse(bool(completed_flash_halo.property("visible")))

    def test_nonfatal_run_failed_hides_elapsed_timer_for_failed_running_node(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("core.logger", x=220.0, y=140.0)
        self.window._active_run_id = "run_live"
        self.window._active_run_workspace_id = workspace_id
        self.window._set_run_ui_state("running", "Running", 1, 0, 0, 0)
        self.app.processEvents()

        graph_canvas = self._graph_canvas_item()
        wait_for_condition_or_raise(
            lambda: _graph_node_card(graph_canvas, node_id) is not None,
            timeout_ms=500,
            app=self.app,
            timeout_message="Timed out waiting for graph node card to appear.",
        )
        node_card = _graph_node_card(graph_canvas, node_id)
        self.assertIsNotNone(node_card)
        if node_card is None:
            self.fail("Expected graph node card to exist")

        background_layer = node_card.findChild(QObject, "graphNodeChromeBackgroundLayer")
        elapsed_timer = node_card.findChild(QObject, "graphNodeElapsedTimer")
        self.assertIsNotNone(background_layer)
        self.assertIsNotNone(elapsed_timer)

        self.window.execution_event.emit(
            {
                "type": "run_started",
                "run_id": "run_live",
                "workspace_id": workspace_id,
            }
        )
        self.window.execution_event.emit(
            {
                "type": "node_started",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": node_id,
            }
        )
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: bool(node_card.property("isRunningNode")) and bool(elapsed_timer.property("visible")),
            timeout_ms=400,
            app=self.app,
            timeout_message="Timed out waiting for running-node elapsed timer to appear.",
        )

        QTest.qWait(160)
        self.app.processEvents()
        self.assertNotEqual(str(elapsed_timer.property("text") or ""), "0.0s")

        with patch.object(QMessageBox, "critical"):
            self.window.execution_event.emit(
                {
                    "type": "run_failed",
                    "run_id": "run_live",
                    "workspace_id": workspace_id,
                    "node_id": node_id,
                    "error": "boom",
                    "traceback": "traceback: line 1",
                    "fatal": False,
                }
            )
            self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: bool(node_card.property("isFailedNode"))
            and str(background_layer.property("effectiveBorderState")) == "failed"
            and not bool(elapsed_timer.property("visible")),
            timeout_ms=400,
            app=self.app,
            timeout_message="Timed out waiting for failed-node timer cleanup.",
        )
        self.assertEqual(dict(graph_canvas.property("failedNodeLookup")), {node_id: True})

    def test_execution_edge_progress_visualization_shell_canvas_tracks_dimming_flash_failure_branch_and_completion_cleanup(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        graph_ids = _build_execution_edge_progress_visualization_graph(self.window)
        self.app.processEvents()

        graph_canvas = self._graph_canvas_item()
        edge_layer = _graph_edge_layer(graph_canvas)
        edge_canvas_layer = _graph_edge_canvas_layer(graph_canvas)
        self.assertIsNotNone(edge_layer)
        self.assertIsNotNone(edge_canvas_layer)
        if edge_layer is None or edge_canvas_layer is None:
            self.fail("Expected graph canvas edge layers to expose stable object names")

        def _snapshot(edge_id: str) -> dict[str, object] | None:
            return _edge_snapshot_payload(edge_layer, edge_id)

        def _paint(edge_id: str) -> dict[str, object] | None:
            return _edge_paint_diagnostics(edge_canvas_layer, edge_id)

        wait_for_condition_or_raise(
            lambda: all(
                _snapshot(edge_id) is not None and _paint(edge_id) is not None
                for edge_id in (
                    graph_ids["exec_edge_id"],
                    graph_ids["failed_edge_id"],
                    graph_ids["continuation_edge_id"],
                    graph_ids["data_edge_id"],
                )
            ),
            timeout_ms=800,
            app=self.app,
            timeout_message="Timed out waiting for execution-edge progress visualization snapshots.",
        )

        idle_exec = _paint(graph_ids["exec_edge_id"])
        idle_failed = _paint(graph_ids["failed_edge_id"])
        idle_data = _paint(graph_ids["data_edge_id"])
        self.assertIsNotNone(idle_exec)
        self.assertIsNotNone(idle_failed)
        self.assertIsNotNone(idle_data)
        if idle_exec is None or idle_failed is None or idle_data is None:
            self.fail("Expected edge paint diagnostics before execution begins")

        self.assertFalse(bool(idle_exec["executionVisualizationActive"]))
        self.assertEqual(float(idle_exec["strokeAlpha"]), 1.0)
        self.assertAlmostEqual(float(idle_exec["strokeWidthScreenPx"]), 2.0, places=6)
        self.assertEqual(float(idle_exec["flashAlpha"]), 0.0)
        self.assertFalse(bool(idle_failed["executionVisualizationActive"]))
        self.assertEqual(float(idle_failed["strokeAlpha"]), 1.0)
        self.assertEqual(float(idle_data["strokeAlpha"]), 1.0)
        self.assertAlmostEqual(float(idle_data["strokeWidthScreenPx"]), 2.0, places=6)
        self.assertFalse(bool(idle_data["executionDimmedActive"]))

        with patch.object(self.window.execution_client, "start_run", return_value="run_live"):
            self.window._run_workflow()
        self.app.processEvents()
        self.window.execution_event.emit(
            {
                "type": "run_started",
                "run_id": "run_live",
                "workspace_id": workspace_id,
            }
        )
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: (
                bool((_paint(graph_ids["exec_edge_id"]) or {}).get("executionVisualizationActive"))
                and bool((_paint(graph_ids["exec_edge_id"]) or {}).get("executionDimmedActive"))
                and bool((_paint(graph_ids["failed_edge_id"]) or {}).get("executionDimmedActive"))
                and bool((_paint(graph_ids["continuation_edge_id"]) or {}).get("executionDimmedActive"))
            ),
            timeout_ms=800,
            app=self.app,
            timeout_message="Timed out waiting for dimmed execution-edge render state at run start.",
        )

        run_started_exec = _paint(graph_ids["exec_edge_id"])
        run_started_failed = _paint(graph_ids["failed_edge_id"])
        run_started_continuation = _paint(graph_ids["continuation_edge_id"])
        run_started_data = _paint(graph_ids["data_edge_id"])
        self.assertIsNotNone(run_started_exec)
        self.assertIsNotNone(run_started_failed)
        self.assertIsNotNone(run_started_continuation)
        self.assertIsNotNone(run_started_data)
        if (
            run_started_exec is None
            or run_started_failed is None
            or run_started_continuation is None
            or run_started_data is None
        ):
            self.fail("Expected execution-edge paint diagnostics after run start")

        for payload in (run_started_exec, run_started_failed, run_started_continuation):
            self.assertEqual(float(payload["strokeAlpha"]), 0.35)
            self.assertAlmostEqual(float(payload["strokeWidthScreenPx"]), 1.7, places=6)
            self.assertEqual(float(payload["flashAlpha"]), 0.0)
        self.assertEqual(dict(graph_canvas.property("progressedExecutionEdgeLookup")), {})
        self.assertEqual(float(run_started_data["strokeAlpha"]), 1.0)
        self.assertAlmostEqual(float(run_started_data["strokeWidthScreenPx"]), 2.0, places=6)
        self.assertFalse(bool(run_started_data["executionDimmedActive"]))

        self.window.execution_event.emit(
            {
                "type": "node_completed",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": graph_ids["start_node_id"],
                "outputs": {"exit_code": 0},
            }
        )
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: (
                graph_ids["exec_edge_id"] in dict(graph_canvas.property("progressedExecutionEdgeLookup"))
                and bool((_snapshot(graph_ids["exec_edge_id"]) or {}).get("executionProgressed"))
                and float(((_paint(graph_ids["exec_edge_id"]) or {}).get("flashAlpha", 0.0))) > 0.0
            ),
            timeout_ms=800,
            app=self.app,
            timeout_message="Timed out waiting for the first execution edge to progress and flash.",
        )

        progressed_exec = _paint(graph_ids["exec_edge_id"])
        self.assertIsNotNone(progressed_exec)
        if progressed_exec is None:
            self.fail("Expected progressed execution-edge diagnostics")
        self.assertFalse(bool(progressed_exec["executionDimmedActive"]))
        self.assertTrue(bool(progressed_exec["executionProgressed"]))
        self.assertEqual(float(progressed_exec["strokeAlpha"]), 1.0)
        self.assertAlmostEqual(float(progressed_exec["strokeWidthScreenPx"]), 2.0, places=6)
        self.assertLessEqual(float(progressed_exec["flashAlpha"]), 0.55)
        self.assertGreater(float(progressed_exec["flashAlpha"]), 0.0)
        self.assertAlmostEqual(float(progressed_exec["flashWidthScreenPx"]), 3.4, places=6)

        wait_for_condition_or_raise(
            lambda: float(((_paint(graph_ids["exec_edge_id"]) or {}).get("flashAlpha", -1.0))) == 0.0,
            timeout_ms=1000,
            app=self.app,
            timeout_message="Timed out waiting for the first execution edge flash to expire.",
        )

        self.window.execution_event.emit(
            {
                "type": "node_failed_handled",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": graph_ids["script_node_id"],
                "error": "boom handled",
            }
        )
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: (
                graph_ids["failed_edge_id"] in dict(graph_canvas.property("progressedExecutionEdgeLookup"))
                and bool((_snapshot(graph_ids["failed_edge_id"]) or {}).get("executionProgressed"))
                and float(((_paint(graph_ids["failed_edge_id"]) or {}).get("flashAlpha", 0.0))) > 0.0
            ),
            timeout_ms=800,
            app=self.app,
            timeout_message="Timed out waiting for handled-failure branch edge progression.",
        )

        failed_edge = _paint(graph_ids["failed_edge_id"])
        continuation_edge = _paint(graph_ids["continuation_edge_id"])
        self.assertIsNotNone(failed_edge)
        self.assertIsNotNone(continuation_edge)
        if failed_edge is None or continuation_edge is None:
            self.fail("Expected handled-failure branch diagnostics")
        self.assertTrue(bool(failed_edge["executionProgressed"]))
        self.assertEqual(float(failed_edge["strokeAlpha"]), 1.0)
        self.assertGreater(float(failed_edge["flashAlpha"]), 0.0)
        self.assertTrue(bool(continuation_edge["executionDimmedActive"]))
        self.assertEqual(float(continuation_edge["strokeAlpha"]), 0.35)

        self.window.execution_event.emit(
            {
                "type": "node_completed",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": graph_ids["on_failure_node_id"],
                "outputs": {"exit_code": 0},
            }
        )
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: (
                graph_ids["continuation_edge_id"] in dict(graph_canvas.property("progressedExecutionEdgeLookup"))
                and bool((_snapshot(graph_ids["continuation_edge_id"]) or {}).get("executionProgressed"))
                and float(((_paint(graph_ids["continuation_edge_id"]) or {}).get("flashAlpha", 0.0))) > 0.0
            ),
            timeout_ms=800,
            app=self.app,
            timeout_message="Timed out waiting for the failure-handler continuation edge to progress.",
        )

        self.window.execution_event.emit(
            {
                "type": "run_completed",
                "run_id": "run_live",
                "workspace_id": workspace_id,
            }
        )
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: (
                dict(graph_canvas.property("progressedExecutionEdgeLookup")) == {}
                and not bool((_paint(graph_ids["exec_edge_id"]) or {}).get("executionVisualizationActive"))
                and float(((_paint(graph_ids["exec_edge_id"]) or {}).get("strokeAlpha", 0.0))) == 1.0
                and float(((_paint(graph_ids["failed_edge_id"]) or {}).get("strokeAlpha", 0.0))) == 1.0
            ),
            timeout_ms=1000,
            app=self.app,
            timeout_message="Timed out waiting for execution-edge cleanup after run completion.",
        )

        completed_exec = _paint(graph_ids["exec_edge_id"])
        completed_failed = _paint(graph_ids["failed_edge_id"])
        completed_data = _paint(graph_ids["data_edge_id"])
        self.assertIsNotNone(completed_exec)
        self.assertIsNotNone(completed_failed)
        self.assertIsNotNone(completed_data)
        if completed_exec is None or completed_failed is None or completed_data is None:
            self.fail("Expected execution-edge paint diagnostics after completion cleanup")

        self.assertFalse(bool(completed_exec["executionVisualizationActive"]))
        self.assertFalse(bool(completed_exec["executionDimmedActive"]))
        self.assertEqual(float(completed_exec["strokeAlpha"]), 1.0)
        self.assertAlmostEqual(float(completed_exec["strokeWidthScreenPx"]), 2.0, places=6)
        self.assertEqual(float(completed_exec["flashAlpha"]), 0.0)
        self.assertFalse(bool(completed_failed["executionDimmedActive"]))
        self.assertEqual(float(completed_failed["strokeAlpha"]), 1.0)
        self.assertEqual(float(completed_data["strokeAlpha"]), 1.0)
        self.assertFalse(bool(completed_data["executionDimmedActive"]))

    def test_execution_edge_progress_visualization_terminal_events_clear_progressed_edge_render_state(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        graph_ids = _build_execution_edge_progress_visualization_graph(self.window)
        self.app.processEvents()

        graph_canvas = self._graph_canvas_item()
        edge_layer = _graph_edge_layer(graph_canvas)
        edge_canvas_layer = _graph_edge_canvas_layer(graph_canvas)
        self.assertIsNotNone(edge_layer)
        self.assertIsNotNone(edge_canvas_layer)
        if edge_layer is None or edge_canvas_layer is None:
            self.fail("Expected graph canvas edge layers to expose stable object names")

        def _paint(edge_id: str) -> dict[str, object] | None:
            return _edge_paint_diagnostics(edge_canvas_layer, edge_id)

        wait_for_condition_or_raise(
            lambda: _paint(graph_ids["exec_edge_id"]) is not None,
            timeout_ms=800,
            app=self.app,
            timeout_message="Timed out waiting for terminal-cleanup edge diagnostics.",
        )

        terminal_events = (
            {
                "label": "run_stopped",
                "payload": {
                    "type": "run_stopped",
                    "run_id": "run_live",
                    "workspace_id": workspace_id,
                },
                "patch_critical": False,
            },
            {
                "label": "run_failed_fatal",
                "payload": {
                    "type": "run_failed",
                    "run_id": "run_live",
                    "workspace_id": workspace_id,
                    "node_id": graph_ids["script_node_id"],
                    "error": "fatal boom",
                    "traceback": "traceback: line 1",
                    "fatal": True,
                },
                "patch_critical": True,
            },
        )

        for terminal_event in terminal_events:
            with self.subTest(terminal_event=terminal_event["label"]):
                self.window.clear_node_execution_visualization_state()
                self.app.processEvents()

                with patch.object(self.window.execution_client, "start_run", return_value="run_live"):
                    self.window._run_workflow()
                self.app.processEvents()
                self.window.execution_event.emit(
                    {
                        "type": "run_started",
                        "run_id": "run_live",
                        "workspace_id": workspace_id,
                    }
                )
                self.window.execution_event.emit(
                    {
                        "type": "node_completed",
                        "run_id": "run_live",
                        "workspace_id": workspace_id,
                        "node_id": graph_ids["start_node_id"],
                        "outputs": {"exit_code": 0},
                    }
                )
                self.app.processEvents()

                wait_for_condition_or_raise(
                    lambda: (
                        graph_ids["exec_edge_id"] in dict(graph_canvas.property("progressedExecutionEdgeLookup"))
                        and float(((_paint(graph_ids["exec_edge_id"]) or {}).get("flashAlpha", 0.0))) > 0.0
                    ),
                    timeout_ms=800,
                    app=self.app,
                    timeout_message=f"Timed out seeding progressed edge state for {terminal_event['label']}.",
                )

                if terminal_event["patch_critical"]:
                    with patch.object(QMessageBox, "critical"):
                        self.window.execution_event.emit(dict(terminal_event["payload"]))
                        self.app.processEvents()
                else:
                    self.window.execution_event.emit(dict(terminal_event["payload"]))
                    self.app.processEvents()

                wait_for_condition_or_raise(
                    lambda: (
                        dict(graph_canvas.property("progressedExecutionEdgeLookup")) == {}
                        and not bool((_paint(graph_ids["exec_edge_id"]) or {}).get("executionVisualizationActive"))
                        and float(((_paint(graph_ids["exec_edge_id"]) or {}).get("strokeAlpha", 0.0))) == 1.0
                        and float(((_paint(graph_ids["exec_edge_id"]) or {}).get("flashAlpha", -1.0))) == 0.0
                    ),
                    timeout_ms=1000,
                    app=self.app,
                    timeout_message=f"Timed out waiting for {terminal_event['label']} to clear edge render state.",
                )

    def test_viewer_session_bridge_context_property_exists_and_rerun_invalidates_current_workspace(self) -> None:
        execution_client = _ViewerExecutionClientStub()
        self.window.execution_client = execution_client

        bridge = self.window.quick_widget.rootContext().contextProperty("viewerSessionBridge")
        self.assertIsInstance(bridge, ViewerSessionBridge)
        self.assertIs(bridge, self.window.viewer_session_bridge)

        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("core.logger", x=120.0, y=40.0)
        session_id = bridge.open(
            node_id,
            {
                "data_refs": {"fields": "fields_ref"},
                "summary": {"result_name": "displacement"},
            },
        )
        open_call = execution_client.open_calls[-1]
        self.window.execution_event.emit(
            _viewer_opened_event(
                request_id=open_call["request_id"],
                workspace_id=workspace_id,
                node_id=node_id,
                session_id=session_id,
            )
        )
        self.app.processEvents()

        self.window._run_workflow()
        self.app.processEvents()

        state = bridge.session_state(node_id)
        self.assertEqual(state["phase"], "blocked")
        self.assertEqual(state["live_open_status"], "blocked")
        self.assertTrue(state["live_open_blocker"]["rerun_required"])
        self.assertEqual(state["summary"]["run_id"], "run_live")
        self.assertEqual(self.window.run_state.active_run_id, "run_live")
        self.assertEqual(self.window.run_state.active_run_workspace_id, workspace_id)

    def test_shell_context_bridge_fallbacks_wrap_shell_window_with_focused_sources(self) -> None:
        library_bridge = ShellLibraryBridge(self.window, shell_window=self.window)
        workspace_bridge = ShellWorkspaceBridge(
            self.window,
            shell_window=self.window,
            scene_bridge=self.window.scene,
            view_bridge=self.window.view,
            console_bridge=self.window.console_panel,
            workspace_tabs_bridge=self.window.workspace_tabs,
        )
        inspector_bridge = ShellInspectorBridge(
            self.window,
            shell_window=self.window,
            scene_bridge=self.window.scene,
        )

        self.assertIsNot(library_bridge.library_source, self.window)
        self.assertIsNot(workspace_bridge.workspace_source, self.window)
        self.assertIsNot(inspector_bridge.inspector_source, self.window)
        self.assertEqual(library_bridge.graph_search_query, self.window.shell_library_presenter.graph_search_query)
        self.assertEqual(workspace_bridge.project_display_name, self.window.shell_workspace_presenter.project_display_name)
        self.assertEqual(inspector_bridge.selected_node_title, self.window.shell_inspector_presenter.selected_node_title)

    def test_selected_workspace_toolbar_buttons_follow_run_owner_state_and_warning_path(self) -> None:
        root_object = self.window.quick_widget.rootObject()
        self.assertIsNotNone(root_object)
        if root_object is None:
            self.fail("Expected main shell root object to exist")

        run_button = _named_qquick_item(root_object, "shellRunToolbarRunButton")
        pause_button = _named_qquick_item(root_object, "shellRunToolbarPauseButton")
        stop_button = _named_qquick_item(root_object, "shellRunToolbarStopButton")
        self.assertIsNotNone(run_button)
        self.assertIsNotNone(pause_button)
        self.assertIsNotNone(stop_button)
        if run_button is None or pause_button is None or stop_button is None:
            self.fail("Expected shell toolbar run buttons to expose stable object names")

        workspace_a_id = self.window.workspace_manager.active_workspace_id()
        workspace_b_id = self.window.workspace_manager.create_workspace("Second Workspace")
        self.window._refresh_workspace_tabs()
        self.window._switch_workspace(workspace_a_id)
        self.app.processEvents()

        bridge = self.window.quick_widget.rootContext().contextProperty("shellWorkspaceBridge")
        self.assertIsInstance(bridge, ShellWorkspaceBridge)
        if not isinstance(bridge, ShellWorkspaceBridge):
            self.fail("Expected shellWorkspaceBridge context property to exist")

        wait_for_condition_or_raise(
            lambda: bool(run_button.property("enabled"))
            and not bool(pause_button.property("enabled"))
            and not bool(stop_button.property("enabled")),
            timeout_ms=400,
            app=self.app,
            timeout_message="Timed out waiting for idle toolbar run controls.",
        )

        with patch.object(self.window.execution_client, "start_run", return_value="run_owner") as start_run:
            bridge.request_run_workflow()
            self.app.processEvents()

            wait_for_condition_or_raise(
                lambda: not bool(run_button.property("enabled"))
                and bool(pause_button.property("enabled"))
                and bool(stop_button.property("enabled")),
                timeout_ms=400,
                app=self.app,
                timeout_message="Timed out waiting for owning-workspace toolbar run controls.",
            )
            self.assertEqual(self.window.run_state.active_run_id, "run_owner")
            self.assertEqual(self.window.run_state.active_run_workspace_id, workspace_a_id)

            self.window._switch_workspace(workspace_b_id)
            self.app.processEvents()

            wait_for_condition_or_raise(
                lambda: bool(run_button.property("enabled"))
                and not bool(pause_button.property("enabled"))
                and not bool(stop_button.property("enabled")),
                timeout_ms=400,
                app=self.app,
                timeout_message="Timed out waiting for non-owning workspace toolbar run controls.",
            )

            warnings_before = self.window.console_panel.warning_count
            bridge.request_run_workflow()
            self.app.processEvents()

            self.assertEqual(start_run.call_count, 1)
            self.assertEqual(self.window.run_state.active_run_id, "run_owner")
            self.assertEqual(self.window.run_state.active_run_workspace_id, workspace_a_id)
            self.assertEqual(self.window.console_panel.warning_count, warnings_before + 1)
            self.assertIn("A workflow run is already active.", self.window.console_panel.warnings_text)

            self.window._switch_workspace(workspace_a_id)
            self.app.processEvents()

            wait_for_condition_or_raise(
                lambda: not bool(run_button.property("enabled"))
                and bool(pause_button.property("enabled"))
                and bool(stop_button.property("enabled")),
                timeout_ms=400,
                app=self.app,
                timeout_message="Timed out waiting for owning-workspace toolbar run controls to restore.",
            )

    def test_fatal_run_failed_event_invalidates_viewer_sessions_as_worker_reset(self) -> None:
        execution_client = _ViewerExecutionClientStub()
        self.window.execution_client = execution_client

        bridge = self.window.viewer_session_bridge
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("core.logger", x=160.0, y=80.0)
        session_id = bridge.open(node_id, {"data_refs": {"fields": "fields_ref"}})
        open_call = execution_client.open_calls[-1]
        self.window.execution_event.emit(
            _viewer_opened_event(
                request_id=open_call["request_id"],
                workspace_id=workspace_id,
                node_id=node_id,
                session_id=session_id,
            )
        )
        self.app.processEvents()

        self.window._active_run_id = "run_live"
        self.window._active_run_workspace_id = workspace_id
        self.window._set_run_ui_state("running", "Running", 1, 0, 0, 0)
        with patch.object(QMessageBox, "critical") as critical:
            self.window.execution_event.emit(
                {
                    "type": "run_failed",
                    "run_id": "run_live",
                    "workspace_id": workspace_id,
                    "node_id": node_id,
                    "error": "Execution worker terminated unexpectedly.",
                    "traceback": "",
                    "fatal": True,
                }
            )
            self.app.processEvents()

        state = bridge.session_state(node_id)
        self.assertEqual(state["phase"], "blocked")
        self.assertEqual(state["live_open_status"], "blocked")
        self.assertTrue(state["live_open_blocker"]["rerun_required"])
        self.assertEqual(state["summary"]["live_transport_release_reason"], "worker_reset")
        self.assertEqual(self.window.run_state.active_run_id, "")
        critical.assert_called_once()

    def test_stream_log_events_are_scoped_to_active_run(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        self.window._active_run_id = "run_live"
        self.window._active_run_workspace_id = workspace_id
        self.window._set_run_ui_state("running", "Running", 1, 0, 0, 0)

        self.window.execution_event.emit(
            {
                "type": "log",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": "node_stream",
                "level": "info",
                "message": "[stdout] tick_ui_0",
            }
        )
        self.window.execution_event.emit(
            {
                "type": "log",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": "node_stream",
                "level": "info",
                "message": "[stderr] warn_ui_0",
            }
        )
        self.window.execution_event.emit(
            {
                "type": "log",
                "run_id": "run_stale",
                "workspace_id": workspace_id,
                "node_id": "node_stream",
                "level": "info",
                "message": "[stdout] should_not_appear",
            }
        )
        self.app.processEvents()

        output_text = self.window.console_panel.output_text
        self.assertIn("[stdout] tick_ui_0", output_text)
        self.assertIn("[stderr] warn_ui_0", output_text)
        self.assertNotIn("should_not_appear", output_text)
        self.assertEqual(self.window._engine_state_value, "running")
        self.assertEqual(self.window.run_state.active_run_id, "run_live")
        self.assertEqual(self.window.run_state.active_run_workspace_id, workspace_id)
        self.assertEqual(self.window.run_state.engine_state_value, "running")

    def test_stale_run_events_do_not_mutate_active_run_ui(self) -> None:
        self.window._active_run_id = "run_live"
        self.window._set_run_ui_state("running", "Running", 1, 0, 0, 0)
        initial_error_count = self.window.console_panel.error_count

        self.window.execution_event.emit(
            {
                "type": "run_failed",
                "run_id": "run_stale",
                "workspace_id": self.window.workspace_manager.active_workspace_id(),
                "node_id": "",
                "error": "stale failure",
                "traceback": "traceback",
            }
        )
        self.app.processEvents()

        self.assertEqual(self.window._active_run_id, "run_live")
        self.assertEqual(self.window._engine_state_value, "running")
        self.assertEqual(self.window.status_jobs.text(), "R:1 Q:0 D:0 F:0")
        self.assertEqual(self.window.console_panel.error_count, initial_error_count)
        self.assertEqual(self.window.run_state.active_run_id, "run_live")
        self.assertEqual(self.window.run_state.engine_state_value, "running")

    def test_node_completed_artifact_ref_payload_keeps_run_ui_running(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        self.window._active_run_id = "run_live"
        self.window._active_run_workspace_id = workspace_id
        self.window._set_run_ui_state("running", "Running", 1, 0, 0, 0)
        initial_output_text = self.window.console_panel.output_text
        initial_error_count = self.window.console_panel.error_count

        self.window.execution_event.emit(
            {
                "type": "node_completed",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": "node_process",
                "outputs": {
                    "stdout": {
                        "__ea_runtime_value__": "artifact_ref",
                        "ref": "artifact-stage://stored_stdout",
                        "artifact_id": "stored_stdout",
                        "scope": "staged",
                    },
                    "stderr": {
                        "__ea_runtime_value__": "artifact_ref",
                        "ref": "artifact-stage://stored_stderr",
                        "artifact_id": "stored_stderr",
                        "scope": "staged",
                    },
                    "exit_code": 0,
                },
            }
        )
        self.app.processEvents()

        self.assertEqual(self.window._active_run_id, "run_live")
        self.assertEqual(self.window._engine_state_value, "running")
        self.assertEqual(self.window.status_jobs.text(), "R:1 Q:0 D:0 F:0")
        self.assertEqual(self.window.console_panel.output_text, initial_output_text)
        self.assertEqual(self.window.console_panel.error_count, initial_error_count)
        self.assertEqual(self.window.run_state.active_run_id, "run_live")
        self.assertEqual(self.window.run_state.active_run_workspace_id, workspace_id)
        self.assertEqual(self.window.run_state.engine_state_value, "running")

    def test_failure_focus_reveals_parent_chain_when_present(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]

        parent_id = self.window.scene.add_node_from_type("core.start", x=0.0, y=0.0)
        child_id = self.window.scene.add_node_from_type("core.logger", x=140.0, y=0.0)
        workspace.nodes[child_id].parent_node_id = parent_id
        self.window.scene.set_node_collapsed(parent_id, True)
        self.assertTrue(workspace.nodes[parent_id].collapsed)

        with patch.object(QMessageBox, "critical") as critical:
            self.window._focus_failed_node(workspace_id, child_id, "boom")

        self.app.processEvents()
        self.assertFalse(workspace.nodes[parent_id].collapsed)
        self.assertEqual(self.window.scene.selected_node_id(), child_id)
        self.assertEqual(self.window.run_state.failed_node_id, child_id)
        self.assertEqual(self.window.run_state.failed_workspace_id, workspace_id)
        critical.assert_called_once()

    def test_run_failed_event_centers_failed_node_and_reports_exception_details(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        failed_node_id = self.window.scene.add_node_from_type("core.python_script", x=860.0, y=640.0)
        self.window.scene.set_node_title(failed_node_id, "Exploding Script")
        node_item = self.window.scene.node_item(failed_node_id)
        self.assertIsNotNone(node_item)
        if node_item is None:
            self.fail("Expected failed node item to exist")
        expected_center = node_item.sceneBoundingRect().center()

        self.window._active_run_id = "run_live"
        self.window._active_run_workspace_id = workspace_id
        self.window._set_run_ui_state("running", "Running", 1, 0, 0, 0)

        with patch.object(QMessageBox, "critical") as critical:
            self.window.execution_event.emit(
                {
                    "type": "run_failed",
                    "run_id": "run_live",
                    "workspace_id": workspace_id,
                    "node_id": failed_node_id,
                    "error": "RuntimeError: boom",
                    "traceback": "traceback: line 1",
                }
            )
            self.app.processEvents()

        self.assertAlmostEqual(self.window.view.center_x, expected_center.x(), delta=8.0)
        self.assertAlmostEqual(self.window.view.center_y, expected_center.y(), delta=8.0)
        self.assertEqual(self.window.scene.selected_node_id(), failed_node_id)
        self.assertEqual(self.window.run_state.failed_node_id, failed_node_id)
        self.assertEqual(self.window.run_state.failed_workspace_id, workspace_id)
        self.assertEqual(self.window.run_state.failed_node_title, "Exploding Script")
        self.assertGreaterEqual(self.window.run_state.failure_focus_revision, 1)

        errors_text = self.window.console_panel.errors_text
        self.assertIn("RuntimeError: boom", errors_text)
        self.assertIn("traceback: line 1", errors_text)
        self.assertEqual(self.window.run_state.active_run_id, "")
        self.assertEqual(self.window.run_state.active_run_workspace_id, "")
        self.assertEqual(self.window.run_state.engine_state_value, "error")
        self.assertIn('Execution halted at "Exploding Script".', self.window.graph_hint_message)
        graph_canvas = self._graph_canvas_item()
        failed_lookup = graph_canvas.property("failedNodeLookup")
        self.assertEqual(dict(failed_lookup), {failed_node_id: True})
        self.assertEqual(graph_canvas.property("failedNodeTitle"), "Exploding Script")
        self.assertGreaterEqual(int(graph_canvas.property("failedNodeRevision")), 1)
        critical.assert_called_once()
        critical_args = critical.call_args.args
        self.assertEqual(critical_args[1], "Workflow Error")
        self.assertEqual(critical_args[2], "RuntimeError: boom")

    def test_new_run_clears_failed_node_highlight_before_start(self) -> None:
        execution_client = _ViewerExecutionClientStub()
        self.window.execution_client = execution_client

        workspace_id = self.window.workspace_manager.active_workspace_id()
        failed_node_id = self.window.scene.add_node_from_type("core.logger", x=240.0, y=180.0)
        self.window.scene.set_node_title(failed_node_id, "Previous Failure")

        with patch.object(QMessageBox, "critical"):
            self.window._focus_failed_node(workspace_id, failed_node_id, "boom")
        self.app.processEvents()

        self.assertEqual(self.window.run_state.failed_node_id, failed_node_id)
        graph_canvas = self._graph_canvas_item()
        self.assertEqual(dict(graph_canvas.property("failedNodeLookup")), {failed_node_id: True})

        self.window._run_workflow()
        self.app.processEvents()

        self.assertEqual(self.window.run_state.failed_node_id, "")
        self.assertEqual(self.window.run_state.failed_workspace_id, "")
        self.assertEqual(dict(graph_canvas.property("failedNodeLookup")), {})


class _SubprocessShellWindowTest(unittest.TestCase):
    __test__ = False

    def __init__(self, target: str) -> None:
        super().__init__(methodName="runTest")
        self._target = target

    def id(self) -> str:
        return self._target

    def __str__(self) -> str:
        return self._target

    def shortDescription(self) -> str:
        return self._target

    def runTest(self) -> None:
        env = os.environ.copy()
        env.setdefault("QT_QPA_PLATFORM", "offscreen")
        result = subprocess.run(
            [sys.executable, "-c", _SHELL_TEST_RUNNER, self._target],
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
        self.fail(
            f"Subprocess shell test failed for {self._target} "
            f"(exit={result.returncode}).\n{output}"
        )


def load_tests(loader: unittest.TestLoader, _tests, _pattern):  # noqa: ANN001
    suite = unittest.TestSuite()
    for test_name in loader.getTestCaseNames(ShellRunControllerTests):
        target = f"{ShellRunControllerTests.__module__}.{ShellRunControllerTests.__qualname__}.{test_name}"
        suite.addTest(_SubprocessShellWindowTest(target))
    return suite


if __name__ == "__main__":
    unittest.main()
