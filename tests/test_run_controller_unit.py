from __future__ import annotations

import unittest

from ea_node_editor.ui.shell.controllers.run_controller import RunController


class _ConsoleStub:
    def __init__(self) -> None:
        self.logs: list[tuple[str, str]] = []
        self.warning_count = 0
        self.error_count = 0

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


class _ActionStub:
    def __init__(self) -> None:
        self.enabled = True
        self.text = ""

    def setEnabled(self, value: bool) -> None:  # noqa: N802
        self.enabled = bool(value)

    def setText(self, value: str) -> None:  # noqa: N802
        self.text = str(value)


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
        self._active_run_id = "run_live"
        self._active_run_workspace_id = "ws_1"
        self._engine_state_value = "running"
        self.console_panel = _ConsoleStub()
        self.action_stop = _ActionStub()
        self.action_pause = _ActionStub()
        self.workspace_library_controller = type("W", (), {"focus_failed_node": lambda *_args, **_kwargs: None})()

    def update_notification_counters(self, warnings: int, errors: int) -> None:
        self._notifications = (warnings, errors)

    def update_engine_status(self, state: str, details: str = "") -> None:
        self._engine_status = (state, details)

    def update_job_counters(self, running: int, queued: int, done: int, failed: int) -> None:
        self._job_counters = (running, queued, done, failed)


class RunControllerUnitTests(unittest.TestCase):
    def test_stale_run_event_is_ignored(self) -> None:
        host = _RunHostStub()
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
        self.assertEqual(host._active_run_id, "run_live")

    def test_set_run_ui_state_updates_host_state_and_actions(self) -> None:
        host = _RunHostStub()
        controller = RunController(host)  # type: ignore[arg-type]

        controller.set_run_ui_state("paused", "Paused", 1, 0, 0, 0)

        self.assertEqual(host._engine_state_value, "paused")
        self.assertEqual(host._engine_status, ("paused", "Paused"))
        self.assertEqual(host._job_counters, (1, 0, 0, 0))
        self.assertTrue(host.action_pause.enabled)
        self.assertEqual(host.action_pause.text, "Resume")


if __name__ == "__main__":
    unittest.main()
