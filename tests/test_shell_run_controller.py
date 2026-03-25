from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtWidgets import QMessageBox

from ea_node_editor.ui_qml.viewer_session_bridge import ViewerSessionBridge
from tests.main_window_shell.base import MainWindowShellTestBase

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
        data_refs: dict | None = None,
        summary: dict | None = None,
        options: dict | None = None,
    ) -> str:
        request_id = self._next_request_id("open")
        self.open_calls.append(
            {
                "request_id": request_id,
                "workspace_id": workspace_id,
                "node_id": node_id,
                "session_id": session_id,
                "data_refs": dict(data_refs or {}),
                "summary": dict(summary or {}),
                "options": dict(options or {}),
            }
        )
        return request_id

    def update_viewer_session(
        self,
        *,
        workspace_id: str,
        node_id: str,
        session_id: str,
        data_refs: dict | None = None,
        summary: dict | None = None,
        options: dict | None = None,
    ) -> str:
        request_id = self._next_request_id("update")
        self.update_calls.append(
            {
                "request_id": request_id,
                "workspace_id": workspace_id,
                "node_id": node_id,
                "session_id": session_id,
                "data_refs": dict(data_refs or {}),
                "summary": dict(summary or {}),
                "options": dict(options or {}),
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
    ) -> str:
        request_id = self._next_request_id("close")
        self.close_calls.append(
            {
                "request_id": request_id,
                "workspace_id": workspace_id,
                "node_id": node_id,
                "session_id": session_id,
                "options": dict(options or {}),
            }
        )
        return request_id

    def shutdown(self) -> None:
        return None


def _viewer_opened_event(*, request_id: str, workspace_id: str, node_id: str, session_id: str) -> dict:
    return {
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


class ShellRunControllerTests(MainWindowShellTestBase):

    def test_viewer_session_bridge_context_property_exists_and_rerun_invalidates_current_workspace(self) -> None:
        execution_client = _ViewerExecutionClientStub()
        self.window.execution_client = execution_client

        bridge = self.window.quick_widget.rootContext().contextProperty("viewerSessionBridge")
        self.assertIsInstance(bridge, ViewerSessionBridge)
        self.assertIs(bridge, self.window.viewer_session_bridge)

        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("core.logger", x=120.0, y=40.0)
        session_id = bridge.open(node_id, {"summary": {"result_name": "displacement"}})
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
        self.assertEqual(state["phase"], "invalidated")
        self.assertEqual(state["invalidated_reason"], "workspace_rerun")
        self.assertEqual(state["summary"]["run_id"], "run_live")
        self.assertEqual(self.window.run_state.active_run_id, "run_live")
        self.assertEqual(self.window.run_state.active_run_workspace_id, workspace_id)

    def test_fatal_run_failed_event_invalidates_viewer_sessions_as_worker_reset(self) -> None:
        execution_client = _ViewerExecutionClientStub()
        self.window.execution_client = execution_client

        bridge = self.window.viewer_session_bridge
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("core.logger", x=160.0, y=80.0)
        session_id = bridge.open(node_id)
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
        self.assertEqual(state["phase"], "invalidated")
        self.assertEqual(state["invalidated_reason"], "worker_reset")
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
        critical.assert_called_once()

    def test_run_failed_event_centers_failed_node_and_reports_exception_details(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        failed_node_id = self.window.scene.add_node_from_type("core.python_script", x=860.0, y=640.0)
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

        errors_text = self.window.console_panel.errors_text
        self.assertIn("RuntimeError: boom", errors_text)
        self.assertIn("traceback: line 1", errors_text)
        self.assertEqual(self.window.run_state.active_run_id, "")
        self.assertEqual(self.window.run_state.active_run_workspace_id, "")
        self.assertEqual(self.window.run_state.engine_state_value, "error")
        critical.assert_called_once()
        critical_args = critical.call_args.args
        self.assertEqual(critical_args[1], "Workflow Error")
        self.assertEqual(critical_args[2], "RuntimeError: boom")


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
