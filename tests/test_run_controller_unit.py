from __future__ import annotations

import unittest

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.ui.shell.controllers.run_controller import RunController
from ea_node_editor.ui.shell.state import ShellRunState


class _ConsoleStub:
    def __init__(self) -> None:
        self.logs: list[tuple[str, str]] = []
        self.warning_count = 0
        self.error_count = 0
        self.clear_count = 0

    def append_log(self, level: str, message: str) -> None:
        self.logs.append((str(level), str(message)))
        if level == "warning":
            self.warning_count += 1
        if level == "error":
            self.error_count += 1

    def clear_all(self) -> None:
        self.logs.clear()
        self.warning_count = 0
        self.error_count = 0
        self.clear_count += 1


class _ActionStub:
    def __init__(self) -> None:
        self.enabled = True
        self.text = ""
        self.icon = None

    def setEnabled(self, value: bool) -> None:  # noqa: N802
        self.enabled = bool(value)

    def setText(self, value: str) -> None:  # noqa: N802
        self.text = str(value)

    def setIcon(self, value) -> None:  # noqa: ANN001, N802
        self.icon = value


class _WorkspaceManagerStub:
    def active_workspace_id(self) -> str:
        return "ws_1"


class _SerializerStub:
    def to_document(self, project) -> dict:  # noqa: ANN001
        return {"project_id": project.project_id, "workspace_count": len(project.workspaces)}


class _ProjectSessionControllerStub:
    def workflow_settings_payload(self) -> dict:
        return {"general": {"project_name": "Demo"}}


class _ExecutionClientStub:
    def __init__(self) -> None:
        self.next_run_id = "run_live"
        self.start_calls: list[dict] = []
        self.pause_calls: list[str] = []
        self.resume_calls: list[str] = []
        self.stop_calls: list[str] = []

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
        self.pause_calls.append(run_id)

    def resume_run(self, run_id: str) -> None:
        self.resume_calls.append(run_id)

    def stop_run(self, run_id: str) -> None:
        self.stop_calls.append(run_id)


class _WorkspaceLibraryControllerStub:
    def __init__(self) -> None:
        self.focus_calls: list[tuple[str, str, str]] = []

    def focus_failed_node(self, workspace_id: str, node_id: str, error: str) -> None:
        self.focus_calls.append((workspace_id, node_id, error))


class _RunHostStub:
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
        self.run_state = ShellRunState()
        self.project_path = "demo.sfe"
        self.workspace_manager = _WorkspaceManagerStub()
        self.serializer = _SerializerStub()
        self.model = GraphModel()
        self.project_session_controller = _ProjectSessionControllerStub()
        self.console_panel = _ConsoleStub()
        self.execution_client = _ExecutionClientStub()
        self.workspace_library_controller = _WorkspaceLibraryControllerStub()
        self.action_stop = _ActionStub()
        self.action_pause = _ActionStub()
        self._notifications = (0, 0)
        self._engine_status = ("ready", "")
        self._job_counters = (0, 0, 0, 0)

    def update_notification_counters(self, warnings: int, errors: int) -> None:
        self._notifications = (warnings, errors)

    def update_engine_status(self, state: str, details: str = "") -> None:
        self._engine_status = (state, details)

    def update_job_counters(self, running: int, queued: int, done: int, failed: int) -> None:
        self._job_counters = (running, queued, done, failed)


class RunControllerUnitTests(unittest.TestCase):
    def test_run_workflow_starts_new_run_with_manual_trigger_and_updates_state(self) -> None:
        host = _RunHostStub()
        controller = RunController(host)  # type: ignore[arg-type]

        controller.run_workflow()

        self.assertEqual(host.console_panel.clear_count, 1)
        self.assertEqual(host.run_state.active_run_id, "run_live")
        self.assertEqual(host.run_state.active_run_workspace_id, "ws_1")
        self.assertEqual(host.run_state.engine_state_value, "running")
        self.assertEqual(host._engine_status, ("running", "Starting"))
        self.assertEqual(host._job_counters, (1, 0, 0, 0))
        self.assertTrue(host.action_pause.enabled)
        self.assertEqual(host.action_pause.text, "Pause")

        start_call = host.execution_client.start_calls[-1]
        self.assertEqual(start_call["project_path"], "demo.sfe")
        self.assertEqual(start_call["workspace_id"], "ws_1")
        self.assertEqual(start_call["trigger"]["kind"], "manual")
        self.assertEqual(start_call["trigger"]["workflow_settings"], {"general": {"project_name": "Demo"}})
        self.assertEqual(start_call["trigger"]["project_doc"]["workspace_count"], 1)

    def test_run_workflow_logs_error_when_start_fails(self) -> None:
        host = _RunHostStub()
        host.execution_client.next_run_id = ""
        controller = RunController(host)  # type: ignore[arg-type]

        controller.run_workflow()

        self.assertEqual(host.console_panel.logs[-1], ("error", "Failed to start workflow run."))
        self.assertEqual(host._notifications, (0, 1))
        self.assertEqual(host.run_state.active_run_id, "")
        self.assertEqual(host.run_state.engine_state_value, "error")
        self.assertEqual(host._engine_status, ("error", "Start Failed"))
        self.assertEqual(host._job_counters, (0, 0, 0, 1))

    def test_toggle_pause_resume_and_stop_route_to_execution_client(self) -> None:
        host = _RunHostStub()
        controller = RunController(host)  # type: ignore[arg-type]
        host.run_state.active_run_id = "run_live"
        host.run_state.engine_state_value = "running"

        controller.toggle_pause_resume()
        self.assertEqual(host.execution_client.pause_calls, ["run_live"])
        self.assertEqual(host._engine_status, ("running", "Pausing"))

        host.run_state.engine_state_value = "paused"
        controller.toggle_pause_resume()
        self.assertEqual(host.execution_client.resume_calls, ["run_live"])
        self.assertEqual(host._engine_status, ("running", "Resuming"))

        controller.stop_workflow()
        self.assertEqual(host.execution_client.stop_calls, ["run_live"])
        self.assertEqual(host._engine_status, ("paused", "Stopping"))

    def test_stale_run_event_is_ignored(self) -> None:
        host = _RunHostStub()
        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = "ws_1"
        controller = RunController(host)  # type: ignore[arg-type]

        controller.handle_execution_event(
            {
                "type": "log",
                "run_id": "run_stale",
                "workspace_id": "ws_1",
                "level": "error",
                "message": "should be ignored",
            }
        )

        self.assertEqual(host.console_panel.logs, [])
        self.assertEqual(host.run_state.active_run_id, "run_live")

    def test_run_failed_event_focuses_node_logs_traceback_and_clears_active_run(self) -> None:
        host = _RunHostStub()
        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = "ws_1"
        host.run_state.engine_state_value = "running"
        controller = RunController(host)  # type: ignore[arg-type]

        controller.handle_execution_event(
            {
                "type": "run_failed",
                "run_id": "run_live",
                "workspace_id": "ws_1",
                "node_id": "node_1",
                "error": "boom",
                "traceback": "traceback: line 1",
            }
        )

        self.assertEqual(host.console_panel.logs[-2:], [("error", "boom"), ("error", "traceback: line 1")])
        self.assertEqual(host._notifications, (0, 2))
        self.assertEqual(host.workspace_library_controller.focus_calls, [("ws_1", "node_1", "boom")])
        self.assertEqual(host.run_state.active_run_id, "")
        self.assertEqual(host.run_state.active_run_workspace_id, "")
        self.assertEqual(host.run_state.engine_state_value, "error")
        self.assertFalse(host.action_pause.enabled)
        self.assertEqual(host.action_pause.text, "Pause")

    def test_protocol_error_is_logged(self) -> None:
        host = _RunHostStub()
        controller = RunController(host)  # type: ignore[arg-type]

        controller.handle_execution_event({"type": "protocol_error", "error": "bad payload"})

        self.assertEqual(host.console_panel.logs, [("error", "bad payload")])
        self.assertEqual(host._notifications, (0, 1))


if __name__ == "__main__":
    unittest.main()
