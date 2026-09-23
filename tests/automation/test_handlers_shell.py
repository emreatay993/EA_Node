# Purpose: Offscreen ShellWindow tests for the app / workspace / view / project / run / capture automation handlers and their client facades (T09).
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_shell.py
from __future__ import annotations

import base64
import gc
import time
import unittest
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtWidgets import QApplication

from ea_node_editor import __version__
from ea_node_editor.automation.client_api.app import AppApi
from ea_node_editor.automation.client_api.capture import CaptureApi
from ea_node_editor.automation.client_api.project import ProjectApi
from ea_node_editor.automation.client_api.run import RunApi
from ea_node_editor.automation.client_api.workspaces import WorkspacesApi
from ea_node_editor.automation.errors import (
    INTERNAL,
    INVALID_PARAMS,
    LAST_VIEW,
    LAST_WORKSPACE,
    NO_EFFECT,
    NOT_FOUND,
    PROJECT_DIRTY,
    RUN_ACTIVE,
)
from ea_node_editor.ui.shell.automation.context import AutomationContext
from ea_node_editor.ui.shell.automation.handlers import app as app_handlers
from ea_node_editor.ui.shell.automation.handlers.capture import png_size
from tests.automation.harness import build_context, call, expect_error
from tests.conftest import ShellTestEnvironment
from tests.main_window_shell.base import _ShellTestExecutionClient

START = "passive.flowchart.start"
PROCESS = "passive.flowchart.process"
CONSTANT = "core.constant"  # cheap active node: the fake execution client fails its dispatch on the next event-loop turn
_EXECUTION_CLIENT_TARGET = "ea_node_editor.ui.shell.composition.controllers._create_shell_execution_client"


def _flush(app: QApplication) -> None:
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def _pump_until(app: QApplication, condition: Callable[[], bool], *, timeout_s: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while not condition():
        if time.monotonic() >= deadline:
            return False
        app.processEvents()
        time.sleep(0.005)
    return True


class _RecordingClient:
    """Stand-in for CorexClient.call: records (op, params, timeout_s) and answers with a stub."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
        self.response: dict[str, Any] = {"ok": True}

    def call(self, op: str, params: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        self.calls.append((op, dict(params or {}), dict(kwargs)))
        return dict(self.response)


class _ShellHandlerCase(unittest.TestCase):
    """One offscreen ShellWindow per class, built like tests/main_window_shell/base.py."""

    app: QApplication
    window: Any
    context: AutomationContext
    _env: ShellTestEnvironment
    _client_patch: Any
    _tmp: TemporaryDirectory

    @classmethod
    def setUpClass(cls) -> None:
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)
        _flush(cls.app)
        gc.collect()
        cls._env = ShellTestEnvironment()
        cls._env.start()
        cls._client_patch = patch(_EXECUTION_CLIENT_TARGET, _ShellTestExecutionClient)
        cls._client_patch.start()
        cls._tmp = TemporaryDirectory(prefix="corex-automation-shell-")
        from ea_node_editor.ui.shell.composition import create_shell_window

        cls.window = create_shell_window()
        cls.window.resize(1200, 800)
        cls.window.show()
        _flush(cls.app)

    @classmethod
    def tearDownClass(cls) -> None:
        window = cls.window
        cls.window = None
        try:
            window.close()
            window.deleteLater()
            _flush(cls.app)
        finally:
            cls._client_patch.stop()
            cls._env.stop()
            cls._tmp.cleanup()
            gc.collect()

    def setUp(self) -> None:
        self.tmp_path = Path(self._tmp.name)
        self._reset_shell()

    def _reset_shell(self) -> None:
        window = self.window
        for workspace in window.model.project.workspaces.values():
            workspace.dirty = False
        result = window.project_session_controller.new_project_noninteractive(discard_unsaved=True)
        self.assertTrue(result.ok, result.reason_code)
        window.console_panel.clear_all()
        window.run_projection_controller.set_run_ui_state(
            "ready", "Idle", 0, 0, 0, 0, clear_active_run=window.run_controller.clear_active_run
        )
        window.run_controller.clear_pending_auto_run()
        _flush(self.app)
        self.assertIsNone(QApplication.activeModalWidget(), "a modal dialog leaked into the automation shell")
        self.refresh_context()

    # ------------------------------------------------------------------ helpers

    def refresh_context(self) -> None:
        """Rebuild the context from the live host (fresh helpers between phases).

        ``AutomationContext`` reads ``model`` / ``workspace_manager`` / ``registry`` live
        from the host, so this is hygiene, not a correctness requirement
        (``test_context_follows_project_replacement`` proves the live lookup).
        """
        self.context = AutomationContext.from_host(self.window)

    def workspace(self):  # noqa: ANN201 - WorkspaceData
        return self.context.active_workspace()

    def add_node(self, type_id: str, x: float = 0.0, y: float = 0.0) -> str:
        return call(self.context, "node.add", {"type_id": type_id, "x": x, "y": y})["node_id"]

    def expect(self, op: str, params: dict[str, Any], code: str):  # noqa: ANN201 - AutomationOpError
        return expect_error(self.context, op, params, code)


class ShellFreeTests(unittest.TestCase):
    def test_app_status_and_workspace_list_work_without_a_shell(self) -> None:
        context = build_context()
        status = call(context, "app.status", {})
        self.assertEqual(status["app_version"], __version__)
        self.assertEqual(status["protocol"], 1)
        self.assertEqual(status["mode"], "visible")
        self.assertEqual(status["instance_id"], "")
        self.assertEqual(status["project_path"], "")
        self.assertFalse(status["project_dirty"])
        self.assertEqual(status["busy"], {"modal_dialog": False, "document_io": False, "shutting_down": False})
        self.assertEqual(status["run"], {"idle": True, "engine_state": "ready", "active_run_id": ""})
        self.assertEqual(status["active_workspace_id"], context.workspace_id())
        self.assertEqual((status["node_count"], status["edge_count"]), (0, 0))
        self.assertFalse(status["has_shell"])
        listing = call(context, "workspace.list", {})
        self.assertEqual(listing["active_workspace_id"], context.workspace_id())
        self.assertEqual([row["workspace_id"] for row in listing["workspaces"]], [context.workspace_id()])
        self.assertTrue(listing["workspaces"][0]["views"])

    def test_history_status_works_but_undo_needs_the_shell(self) -> None:
        context = build_context()
        status = call(context, "app.history", {})
        self.assertEqual((status["applied"], status["undo_depth"], status["redo_depth"]), (False, 0, 0))
        self.assertEqual(expect_error(context, "app.history", {"action": "undo"}, INTERNAL).code, INTERNAL)

    def test_shell_only_ops_fail_with_internal_in_the_harness(self) -> None:
        context = build_context()
        for op, params in (
            ("workspace.create", {}),
            ("view.create", {}),
            ("project.save", {}),
            ("run.status", {}),
            ("run.control", {"action": "stop"}),
            ("capture.screenshot", {}),
            ("app.quit", {}),
        ):
            with self.subTest(op=op):
                expect_error(context, op, params, INTERNAL)


class AppHandlerTests(_ShellHandlerCase):
    def test_status_reports_shell_state(self) -> None:
        node_id = self.add_node(PROCESS, 10, 20)
        status = call(self.context, "app.status", {})
        self.assertEqual(status["app_version"], __version__)
        self.assertEqual(status["qt_platform"], "offscreen")
        self.assertTrue(status["has_shell"])
        self.assertTrue(status["project_dirty"])
        self.assertEqual(status["project_path"], "")
        self.assertEqual(status["active_workspace_id"], self.workspace().workspace_id)
        self.assertEqual(status["active_view_id"], self.workspace().active_view_id)
        self.assertEqual(status["node_count"], 1)
        self.assertEqual(status["busy"], {"modal_dialog": False, "document_io": False, "shutting_down": False})
        self.assertTrue(status["run"]["idle"])
        self.assertEqual(status["scope_path"], [])
        self.assertIn(node_id, self.workspace().nodes)

    def test_history_undo_and_redo_round_trip_after_node_add(self) -> None:
        node_id = self.add_node(PROCESS)
        depths = call(self.context, "app.history", {"action": "status"})
        self.assertTrue(depths["can_undo"])
        self.assertGreaterEqual(depths["undo_depth"], 1)
        undone = call(self.context, "app.history", {"action": "undo"})
        self.assertTrue(undone["applied"])
        self.assertNotIn(node_id, self.workspace().nodes)
        self.assertTrue(undone["can_redo"])
        self.assertIsInstance(undone["action_type"], str)
        redone = call(self.context, "app.history", {"action": "redo"})
        self.assertTrue(redone["applied"])
        self.assertIn(node_id, self.workspace().nodes)
        # Nothing left to redo: applied=False, not an error.
        nothing = call(self.context, "app.history", {"action": "redo"})
        self.assertFalse(nothing["applied"])
        self.assertFalse(nothing["can_redo"])

    def test_quit_refuses_a_dirty_project_and_schedules_a_delayed_close(self) -> None:
        self.add_node(PROCESS)
        error = self.expect("app.quit", {}, PROJECT_DIRTY)
        self.assertIn("unsaved", error.message)
        scheduled: list[tuple[int, Any]] = []
        with patch.object(app_handlers.QTimer, "singleShot", lambda delay, callback: scheduled.append((delay, callback))):
            result = call(self.context, "app.quit", {"discard_unsaved": True})
        self.assertEqual(result, {"quitting": True, "project_dirty": True, "delay_ms": app_handlers.QUIT_DELAY_MS})
        self.assertEqual([delay for delay, _ in scheduled], [app_handlers.QUIT_DELAY_MS])
        self.assertTrue(callable(scheduled[0][1]))
        self.assertTrue(self.window.isVisible(), "the close must not run synchronously")

    def test_app_facade_builds_catalog_params(self) -> None:
        client = _RecordingClient()
        api = AppApi(client)
        api.status()
        api.undo()
        api.redo()
        api.quit(discard_unsaved=True)
        self.assertEqual(
            [(op, params) for op, params, _ in client.calls],
            [
                ("app.status", {}),
                ("app.history", {"action": "undo"}),
                ("app.history", {"action": "redo"}),
                ("app.quit", {"discard_unsaved": True}),
            ],
        )


class WorkspaceViewHandlerTests(_ShellHandlerCase):
    def test_list_create_duplicate_update_and_close(self) -> None:
        original_id = self.workspace().workspace_id
        node_id = self.add_node(PROCESS)
        listing = call(self.context, "workspace.list", {})
        self.assertEqual(listing["active_workspace_id"], original_id)
        row = listing["workspaces"][0]
        self.assertEqual((row["workspace_id"], row["active"], row["dirty"], row["node_count"]), (original_id, True, True, 1))
        self.assertEqual(row["views"][0]["view_id"], self.workspace().active_view_id)

        created = call(self.context, "workspace.create", {"name": "Second"})
        second_id = created["workspace_id"]
        self.assertEqual(created["name"], "Second")
        self.assertTrue(created["active"])
        self.assertEqual(self.context.workspace_id(), second_id)

        # activate=False restores the previously active tab.
        background = call(self.context, "workspace.create", {"name": "Background", "activate": False})
        self.assertFalse(background["active"])
        self.assertEqual(self.context.workspace_id(), second_id)

        duplicated = call(self.context, "workspace.create", {"duplicate_of": original_id, "name": "Copy"})
        copy_id = duplicated["workspace_id"]
        self.assertEqual(duplicated["duplicated_from"], original_id)
        self.assertEqual(duplicated["name"], "Copy")
        self.assertEqual(self.context.workspace_id(), copy_id)
        self.assertEqual(len(self.workspace().nodes), 1, "the duplicate carries the source node")
        # Node ids are workspace-scoped: the duplicate keeps them but owns independent records.
        self.assertIn(node_id, self.workspace().nodes)
        self.assertIsNot(self.workspace().nodes[node_id], self.context.model.project.workspaces[original_id].nodes[node_id])
        self.expect("workspace.create", {"duplicate_of": "ws_missing"}, NOT_FOUND)

        renamed = call(self.context, "workspace.update", {"workspace_id": second_id, "name": "Renamed", "activate": True})
        self.assertEqual(sorted(renamed["changed"]), ["active", "name"])
        self.assertEqual(self.context.workspace_id(), second_id)
        self.assertEqual(self.context.model.project.workspaces[second_id].name, "Renamed")
        self.expect("workspace.update", {"workspace_id": second_id, "name": "Renamed", "activate": True}, NO_EFFECT)
        self.expect("workspace.update", {"workspace_id": second_id}, INVALID_PARAMS)
        self.expect("workspace.update", {"workspace_id": "ws_missing", "name": "x"}, NOT_FOUND)

        # Dirty workspaces refuse to close unless discard_unsaved; clean ones close directly.
        dirty = self.expect("workspace.close", {"workspace_id": original_id}, PROJECT_DIRTY)
        self.assertEqual(dirty.details["reason"], "dirty")
        closed = call(self.context, "workspace.close", {"workspace_id": original_id, "discard_unsaved": True})
        self.assertTrue(closed["closed"])
        self.assertNotIn(original_id, self.context.model.project.workspaces)
        self.assertEqual(closed["retirement_error"], "")
        for workspace_id in (copy_id, background["workspace_id"]):
            self.assertTrue(call(self.context, "workspace.close", {"workspace_id": workspace_id, "discard_unsaved": True})["closed"])
        self.assertEqual(list(self.context.model.project.workspaces), [second_id])
        self.expect("workspace.close", {"workspace_id": second_id, "discard_unsaved": True}, LAST_WORKSPACE)
        self.expect("workspace.close", {"workspace_id": "ws_missing"}, NOT_FOUND)

    def test_view_create_update_close_and_last_view(self) -> None:
        workspace = self.workspace()
        first_view_id = workspace.active_view_id
        created = call(self.context, "view.create", {"name": "Detail"})
        detail_id = created["view_id"]
        self.assertEqual(created["name"], "Detail")
        self.assertTrue(created["active"])
        self.assertEqual(workspace.active_view_id, detail_id)

        background = call(self.context, "view.create", {"name": "Overview", "activate": False})
        self.assertFalse(background["active"])
        self.assertEqual(workspace.active_view_id, detail_id)

        updated = call(self.context, "view.update", {"view_id": first_view_id, "name": "Main", "activate": True})
        self.assertEqual(sorted(updated["changed"]), ["active", "name"])
        self.assertEqual(workspace.active_view_id, first_view_id)
        self.assertEqual(workspace.views[first_view_id].name, "Main")
        self.expect("view.update", {"view_id": first_view_id, "name": "Main", "activate": True}, NO_EFFECT)
        self.expect("view.update", {"view_id": "view_missing", "name": "x"}, NOT_FOUND)

        closed = call(self.context, "view.close", {"view_id": detail_id})
        self.assertTrue(closed["closed"])
        self.assertNotIn(detail_id, workspace.views)
        self.assertTrue(call(self.context, "view.close", {"view_id": background["view_id"]})["closed"])
        self.assertEqual(list(workspace.views), [first_view_id])
        self.expect("view.close", {"view_id": first_view_id}, LAST_VIEW)
        self.expect("view.close", {"view_id": "view_missing"}, NOT_FOUND)

    def test_set_camera_explicit_and_frame(self) -> None:
        view = self.context.view
        self.expect("view.set_camera", {}, INVALID_PARAMS)
        self.expect("view.set_camera", {"frame": "all"}, NO_EFFECT)  # empty workspace has nothing to frame
        explicit = call(self.context, "view.set_camera", {"zoom": 2.0, "center_x": 120.0, "center_y": -40.0})
        self.assertAlmostEqual(explicit["zoom"], 2.0)
        self.assertAlmostEqual(explicit["center_x"], 120.0)
        self.assertAlmostEqual(explicit["center_y"], -40.0)
        self.assertAlmostEqual(float(view.zoom_value), 2.0)
        clamped = call(self.context, "view.set_camera", {"zoom": 0.1})
        self.assertAlmostEqual(clamped["zoom"], 0.1)

        a = self.add_node(START, 0, 0)
        b = self.add_node(PROCESS, 900, 600)
        framed = call(self.context, "view.set_camera", {"frame": "all"})
        self.assertEqual(framed["framed"], "all")
        self.assertTrue(framed["changed"])
        self.assertLess(framed["zoom"], 2.0)
        self.assertGreater(framed["center_x"], 0.0)
        nodes_framed = call(self.context, "view.set_camera", {"frame": "nodes", "node_ids": [a]})
        self.assertEqual(nodes_framed["framed"], "nodes")
        self.assertGreater(nodes_framed["zoom"], framed["zoom"], "framing one node zooms in further than framing both")
        self.expect("view.set_camera", {"frame": "nodes"}, INVALID_PARAMS)
        self.expect("view.set_camera", {"frame": "nodes", "node_ids": ["node_missing"]}, NOT_FOUND)
        self.context.scene.clear_selection()
        self.expect("view.set_camera", {"frame": "selection"}, NO_EFFECT)
        self.context.scene.select_node(b, True)
        selection = call(self.context, "view.set_camera", {"frame": "selection", "zoom": 1.5})
        self.assertAlmostEqual(selection["zoom"], 1.5, msg="explicit zoom overrides the framed zoom")

    def test_workspaces_facade_builds_catalog_params(self) -> None:
        client = _RecordingClient()
        api = WorkspacesApi(client)
        api.list()
        api.create("A", activate=False)
        api.duplicate("ws_1", name="B")
        api.activate("ws_2")
        api.rename("ws_2", "C")
        api.close("ws_2", discard_unsaved=True)
        api.create_view("V")
        api.activate_view("view_1")
        api.close_view("view_1")
        api.frame_nodes("node_1")
        api.set_camera(zoom=1.25, center_x=1, center_y=2)
        self.assertEqual(
            [(op, params) for op, params, _ in client.calls],
            [
                ("workspace.list", {}),
                ("workspace.create", {"name": "A", "activate": False}),
                ("workspace.create", {"name": "B", "duplicate_of": "ws_1"}),
                ("workspace.update", {"workspace_id": "ws_2", "activate": True}),
                ("workspace.update", {"workspace_id": "ws_2", "name": "C"}),
                ("workspace.close", {"workspace_id": "ws_2", "discard_unsaved": True}),
                ("view.create", {"name": "V"}),
                ("view.update", {"view_id": "view_1", "activate": True}),
                ("view.close", {"view_id": "view_1"}),
                ("view.set_camera", {"frame": "nodes", "node_ids": ["node_1"]}),
                ("view.set_camera", {"zoom": 1.25, "center_x": 1.0, "center_y": 2.0}),
            ],
        )


class ProjectHandlerTests(_ShellHandlerCase):
    def test_save_as_open_round_trip_and_new_project_dirty_gate(self) -> None:
        node_id = self.add_node(PROCESS, 30, 40)
        self.expect("project.save", {}, INVALID_PARAMS)  # never saved: path required
        target = self.tmp_path / "round_trip" / "flow.cxproj"
        target.parent.mkdir(parents=True, exist_ok=True)
        saved = call(self.context, "project.save", {"path": str(target)})
        self.assertEqual(saved["status"], "saved")
        self.assertEqual(saved["reason_code"], "save_succeeded")
        self.assertEqual(Path(saved["project_path"]).resolve(), target.resolve())
        self.assertTrue(target.is_file())
        self.assertFalse(saved["project_dirty"])
        self.assertEqual(Path(self.window.project_path).resolve(), target.resolve())

        in_place = call(self.context, "project.save", {})
        self.assertEqual(in_place["status"], "saved")

        self.add_node(START, 200, 40)  # dirty again
        self.expect("project.open", {"new": True}, PROJECT_DIRTY)
        self.expect("project.open", {}, INVALID_PARAMS)
        self.expect("project.open", {"path": str(target), "new": True}, INVALID_PARAMS)
        fresh = call(self.context, "project.open", {"new": True, "discard_unsaved": True})
        self.refresh_context()
        self.assertTrue(fresh["new"])
        self.assertEqual(fresh["project_path"], "")
        self.assertEqual(len(self.workspace().nodes), 0)

        opened = call(self.context, "project.open", {"path": str(target)})
        self.refresh_context()
        self.assertEqual(Path(opened["project_path"]).resolve(), target.resolve())
        self.assertEqual(opened["active_workspace_id"], self.context.workspace_id())
        self.assertIn(opened["active_workspace_id"], opened["workspace_ids"])
        self.assertIn(node_id, self.workspace().nodes, "the saved node survives the round trip")
        missing = self.expect("project.open", {"path": str(self.tmp_path / "nope.cxproj")}, "OPEN_FAILED")
        self.assertEqual(missing.details["reason_code"], "not_found")

    def test_stage_file_from_path_and_from_base64(self) -> None:
        source = self.tmp_path / "asset.txt"
        source.write_bytes(b"hello staging")
        node_id = self.add_node(PROCESS)
        staged = call(self.context, "project.stage_file", {"path": str(source), "node_id": node_id})
        self.assertTrue(staged["artifact_ref"].startswith("temp://"), staged["artifact_ref"])
        self.assertEqual(staged["filename"], "asset.txt")
        self.assertEqual(staged["size_bytes"], 13)
        self.assertEqual(staged["node_id"], node_id)
        staged_path = Path(staged["staged_path"])
        self.assertTrue(staged_path.is_file(), staged["staged_path"])
        self.assertEqual(staged_path.read_bytes(), b"hello staging")
        self.assertIn("automation", staged_path.parts)

        payload = base64.b64encode(b"\x89PNG-ish bytes").decode("ascii")
        inline = call(self.context, "project.stage_file", {"content_base64": payload, "filename": "blob.bin", "subdirectory": "uploads"})
        self.assertTrue(inline["artifact_ref"].startswith("temp://"))
        inline_path = Path(inline["staged_path"])
        self.assertEqual(inline_path.read_bytes(), b"\x89PNG-ish bytes")
        self.assertEqual(inline_path.name, "blob.bin")
        self.assertIn("uploads", inline_path.parts)
        self.assertNotEqual(inline["artifact_ref"], staged["artifact_ref"])

        self.expect("project.stage_file", {}, INVALID_PARAMS)
        self.expect("project.stage_file", {"path": str(source), "content_base64": payload, "filename": "x"}, INVALID_PARAMS)
        self.expect("project.stage_file", {"content_base64": payload}, INVALID_PARAMS)
        self.expect("project.stage_file", {"content_base64": "%%%", "filename": "x.bin"}, INVALID_PARAMS)
        self.expect("project.stage_file", {"path": str(self.tmp_path / "missing.txt")}, INVALID_PARAMS)
        self.expect("project.stage_file", {"path": str(source), "node_id": "node_missing"}, NOT_FOUND)

    def test_context_follows_project_replacement(self) -> None:
        # The automation service builds ONE context at startup, so it must keep
        # targeting the live model after project.open / new replace host.model and
        # host.workspace_manager.
        service_context = self.context
        call(service_context, "project.open", {"new": True, "discard_unsaved": True})
        self.assertIs(service_context.model, self.window.model)
        node_id = call(service_context, "node.add", {"type_id": PROCESS, "x": 0, "y": 0})["node_id"]
        live_workspace_id = self.window.workspace_manager.active_workspace_id()
        self.assertIn(node_id, self.window.model.project.workspaces[live_workspace_id].nodes)
        self.assertEqual(call(service_context, "app.status", {})["node_count"], 1)

    def test_project_facade_builds_catalog_params(self) -> None:
        client = _RecordingClient()
        api = ProjectApi(client)
        api.open("C:/x/a.cxproj", discard_unsaved=True)
        api.new()
        api.save()
        api.save_as("C:/x/b.cxproj")
        api.stage_file("C:/x/c.png", node_id="node_1")
        api.stage_bytes("d.bin", b"\x00\x01", subdirectory="up")
        self.assertEqual(
            [(op, params) for op, params, _ in client.calls],
            [
                ("project.open", {"path": "C:/x/a.cxproj", "discard_unsaved": True}),
                ("project.open", {"new": True, "discard_unsaved": False}),
                ("project.save", {}),
                ("project.save", {"path": "C:/x/b.cxproj"}),
                ("project.stage_file", {"path": "C:/x/c.png", "node_id": "node_1"}),
                ("project.stage_file", {"content_base64": "AAE=", "filename": "d.bin", "subdirectory": "up"}),
            ],
        )


class RunHandlerTests(_ShellHandlerCase):
    def test_status_is_idle_and_stop_without_a_run_is_not_applied(self) -> None:
        status = call(self.context, "run.status", {})
        self.assertTrue(status["idle"])
        self.assertEqual(status["outcome"], "idle")
        self.assertEqual(status["engine_state"], "ready")
        self.assertEqual(status["log_tail"], [])
        self.assertFalse(status["timed_out"])
        waited = call(self.context, "run.status", {"wait": True, "timeout_s": 5})
        self.assertTrue(waited["idle"], "an already idle wait resolves immediately")
        stopped = call(self.context, "run.control", {"action": "stop"})
        self.assertFalse(stopped["applied"])
        self.assertTrue(stopped["idle"])
        self.assertFalse(call(self.context, "run.control", {"action": "pause"})["applied"])
        self.assertFalse(call(self.context, "run.control", {"action": "resume"})["applied"])

    def test_start_with_wait_returns_once_the_fake_client_settles(self) -> None:
        node_id = self.add_node(CONSTANT, 0, 0)
        started_at = time.monotonic()
        # The shell test execution client fails every dispatch on the next event-loop
        # turn, so the run settles as an error almost immediately; wait=true must
        # observe that transition instead of hanging.
        result = call(self.context, "run.start", {"wait": True, "timeout_s": 10, "log_tail": 5})
        self.assertLess(time.monotonic() - started_at, 8.0)
        self.assertTrue(result["started"], "run_workflow must have created a submission")
        self.assertTrue(result["idle"])
        self.assertFalse(result["timed_out"])
        self.assertEqual(result["scope"], "workspace")
        self.assertIn(result["engine_state"], {"error", "ready"})
        self.assertIn(result["outcome"], {"failed", "completed", "idle"})
        self.assertIsInstance(result["log_tail"], list)
        self.assertLessEqual(len(result["log_tail"]), 5)
        self.assertIn(node_id, self.workspace().nodes)

    def test_start_without_wait_then_second_start_is_run_active(self) -> None:
        node_id = self.add_node(CONSTANT, 0, 0)
        first = call(self.context, "run.start", {"scope": "nodes", "node_ids": [node_id]})
        self.assertTrue(first["started"])
        self.assertFalse(first["idle"], "the submission is pending until the event loop runs")
        self.assertEqual(first["outcome"], "running")
        self.assertEqual(first["target_node_ids"], [node_id])
        active = self.expect("run.start", {}, RUN_ACTIVE)
        self.assertTrue(active.details["active_submission_id"] or active.details["active_run_id"])
        stopped = call(self.context, "run.control", {"action": "stop"})
        self.assertTrue(stopped["applied"], "stop issues a request while a submission is pending")
        self.assertTrue(_pump_until(self.app, lambda: call(self.context, "run.status", {})["idle"]))
        self.expect("run.start", {"scope": "nodes"}, INVALID_PARAMS)
        self.expect("run.start", {"scope": "nodes", "node_ids": ["node_missing"]}, NOT_FOUND)

    def test_run_facade_builds_catalog_params_and_wait_timeouts(self) -> None:
        client = _RecordingClient()
        api = RunApi(client)
        api.start()
        api.start(node_ids=["node_1"])
        api.run_and_wait(7.0, log_tail=3)
        api.wait(2.5)
        api.stop()
        self.assertEqual(
            [(op, params) for op, params, _ in client.calls],
            [
                ("run.start", {"wait": False}),
                ("run.start", {"scope": "nodes", "node_ids": ["node_1"], "wait": False}),
                ("run.start", {"wait": True, "timeout_s": 7.0, "log_tail": 3}),
                ("run.status", {"wait": True, "timeout_s": 2.5}),
                ("run.control", {"action": "stop"}),
            ],
        )
        self.assertGreater(client.calls[2][2]["timeout_s"], 7.0, "the request timeout must outlive the wait")
        self.assertGreater(client.calls[3][2]["timeout_s"], 2.5)


class CaptureHandlerTests(_ShellHandlerCase):
    def _flowchart(self) -> tuple[str, str]:
        a = self.add_node(START, 0, 0)
        b = self.add_node(PROCESS, 320, 0)
        call(self.context, "edge.connect", {"source_node_id": a, "source_port": "right", "target_node_id": b, "target_port": "left"})
        _flush(self.app)
        return a, b

    def test_views_capture_writes_png_and_restores_the_shadow_flag(self) -> None:
        self._flowchart()
        presenter = self.window.shell_workspace_presenter
        presenter.set_graphics_node_shadow(True)
        self.assertTrue(presenter.graphics_node_shadow)
        output_dir = self.tmp_path / "captures"
        # The offscreen shadow toggle applies to this window only: app_preferences.json
        # is shared with the user's own settings and other COREX instances.
        with patch.object(self.window.app_preferences_controller, "persist") as persist:
            result = call(self.context, "capture.screenshot", {"output_dir": str(output_dir)})
        persist.assert_not_called()
        self.assertEqual(result["mode"], "views")
        self.assertEqual(result["fidelity"], "offscreen_layout")
        self.assertEqual(result["failures"], [])
        self.assertEqual(len(result["images"]), 1)
        image = result["images"][0]
        path = Path(image["path"])
        self.assertTrue(path.is_file(), image["path"])
        self.assertEqual(path.parent.resolve(), output_dir.resolve())
        self.assertGreater(path.stat().st_size, 1000, "a cropped flowchart PNG is not trivial")
        decoded = base64.b64decode(image["png_base64"])
        self.assertEqual(decoded, path.read_bytes())
        self.assertEqual((image["width"], image["height"]), png_size(path))
        self.assertGreater(image["width"], 100)
        self.assertGreater(image["height"], 50)
        self.assertEqual(image["view_id"], self.workspace().active_view_id)
        self.assertTrue(presenter.graphics_node_shadow, "the shadow preference is restored after the grab")

        without_inline = call(self.context, "capture.screenshot", {"output_dir": str(output_dir), "inline": False})
        self.assertNotIn("png_base64", without_inline["images"][0])
        self.expect("capture.screenshot", {"view_ids": ["view_missing"]}, NOT_FOUND)

    def test_window_capture_grabs_the_qml_host(self) -> None:
        self._flowchart()
        output_dir = self.tmp_path / "window_captures"
        result = call(self.context, "capture.screenshot", {"mode": "window", "output_dir": str(output_dir), "filename_stem": "shell view"})
        self.assertEqual(result["mode"], "window")
        image = result["images"][0]
        path = Path(image["path"])
        self.assertEqual(path.name, "shell_view.png")
        self.assertTrue(path.is_file())
        self.assertEqual((image["width"], image["height"]), png_size(path))
        self.assertGreater(image["width"], 200)
        self.assertGreater(image["height"], 200)
        self.assertEqual(base64.b64decode(image["png_base64"]), path.read_bytes())

        default_dir = call(self.context, "capture.screenshot", {"mode": "window", "inline": False})
        default_path = Path(default_dir["images"][0]["path"])
        self.assertTrue(default_path.is_file())
        self.assertIn("corex-capture-", default_path.parent.name)

    def test_capture_facade_decodes_inline_png_when_the_file_is_elsewhere(self) -> None:
        client = _RecordingClient()
        api = CaptureApi(client)
        png_bytes = b"\x89PNG\r\n\x1a\nfake"
        client.response = {
            "images": [{"path": "Z:/remote/shot.png", "png_base64": base64.b64encode(png_bytes).decode("ascii"), "width": 1, "height": 1}],
            "mode": "window",
            "fidelity": "native",
        }
        target = self.tmp_path / "facade" / "shot.png"
        result = api.screenshot_to(target)
        self.assertEqual(client.calls[0][0], "capture.screenshot")
        self.assertEqual(client.calls[0][1], {"mode": "window", "filename_stem": "shot", "output_dir": str(target.parent), "inline": True})
        self.assertEqual(result["saved_paths"], [str(target)])
        self.assertEqual(target.read_bytes(), png_bytes)
        api.screenshot(view_ids="view_1", scale=2, crop_to_content=False)
        self.assertEqual(client.calls[1][1], {"view_ids": ["view_1"], "scale": 2, "crop_to_content": False})


if __name__ == "__main__":
    unittest.main()
