from __future__ import annotations

import unittest

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
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


class _SignalCounter:
    def __init__(self) -> None:
        self.calls = 0

    def emit(self) -> None:
        self.calls += 1


class _WorkspaceManagerStub:
    def __init__(self, workspace_id: str) -> None:
        self._workspace_id = workspace_id

    def active_workspace_id(self) -> str:
        return self._workspace_id

    def set_active_workspace(self, workspace_id: str) -> None:
        self._workspace_id = workspace_id


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
        self.model = GraphModel()
        self.workspace_manager = _WorkspaceManagerStub(self.model.active_workspace.workspace_id)
        self.serializer = _SerializerStub()
        self.registry = build_default_registry()
        self.project_session_controller = _ProjectSessionControllerStub()
        self.console_panel = _ConsoleStub()
        self.execution_client = _ExecutionClientStub()
        self.workspace_library_controller = _WorkspaceLibraryControllerStub()
        self.action_run = _ActionStub()
        self.action_stop = _ActionStub()
        self.action_pause = _ActionStub()
        self.run_controls_changed = _SignalCounter()
        self._notifications = (0, 0)
        self._engine_status = ("ready", "")
        self._job_counters = (0, 0, 0, 0)
        self._failure_clear_count = 0

    def _normalize_node_execution_workspace_id(self, workspace_id: str) -> str:
        normalized_workspace_id = str(workspace_id or "").strip()
        if normalized_workspace_id:
            return normalized_workspace_id
        return str(self.run_state.active_run_workspace_id or self.run_state.node_execution_workspace_id or "").strip()

    def update_notification_counters(self, warnings: int, errors: int) -> None:
        self._notifications = (warnings, errors)

    def update_engine_status(self, state: str, details: str = "") -> None:
        self._engine_status = (state, details)

    def update_job_counters(self, running: int, queued: int, done: int, failed: int) -> None:
        self._job_counters = (running, queued, done, failed)

    def clear_run_failure_focus(self) -> None:
        self._failure_clear_count += 1

    def mark_node_execution_running(self, workspace_id: str, node_id: str) -> None:
        normalized_node_id = str(node_id or "").strip()
        if not normalized_node_id:
            return
        normalized_workspace_id = self._normalize_node_execution_workspace_id(workspace_id)
        if not normalized_workspace_id:
            return
        state = self.run_state
        changed = False
        if state.node_execution_workspace_id != normalized_workspace_id:
            state.node_execution_workspace_id = normalized_workspace_id
            state.running_node_ids.clear()
            state.completed_node_ids.clear()
            changed = True
        if normalized_node_id in state.completed_node_ids:
            state.completed_node_ids.discard(normalized_node_id)
            changed = True
        if normalized_node_id not in state.running_node_ids:
            state.running_node_ids.add(normalized_node_id)
            changed = True
        if changed:
            state.node_execution_revision += 1

    def mark_node_execution_completed(self, workspace_id: str, node_id: str) -> None:
        normalized_node_id = str(node_id or "").strip()
        if not normalized_node_id:
            return
        normalized_workspace_id = self._normalize_node_execution_workspace_id(workspace_id)
        if not normalized_workspace_id:
            return
        state = self.run_state
        changed = False
        if state.node_execution_workspace_id != normalized_workspace_id:
            state.node_execution_workspace_id = normalized_workspace_id
            state.running_node_ids.clear()
            state.completed_node_ids.clear()
            changed = True
        if normalized_node_id in state.running_node_ids:
            state.running_node_ids.discard(normalized_node_id)
            changed = True
        if normalized_node_id not in state.completed_node_ids:
            state.completed_node_ids.add(normalized_node_id)
            changed = True
        if changed:
            state.node_execution_revision += 1

    def clear_node_execution_visualization_state(self) -> None:
        state = self.run_state
        if not (state.node_execution_workspace_id or state.running_node_ids or state.completed_node_ids):
            return
        state.node_execution_workspace_id = ""
        state.running_node_ids.clear()
        state.completed_node_ids.clear()
        state.node_execution_revision += 1


class RunControllerUnitTests(unittest.TestCase):
    def assert_run_controls(
        self,
        host: _RunHostStub,
        *,
        run_enabled: bool,
        pause_enabled: bool,
        stop_enabled: bool,
        pause_label: str,
    ) -> None:
        self.assertEqual(host.action_run.enabled, run_enabled)
        self.assertEqual(host.action_pause.enabled, pause_enabled)
        self.assertEqual(host.action_stop.enabled, stop_enabled)
        self.assertEqual(host.action_pause.text, pause_label)

    def test_run_workflow_starts_new_run_with_manual_trigger_and_updates_state(self) -> None:
        host = _RunHostStub()
        controller = RunController(host)  # type: ignore[arg-type]

        controller.run_workflow()

        self.assertEqual(host.console_panel.clear_count, 1)
        self.assertEqual(host.run_state.active_run_id, "run_live")
        self.assertEqual(host.run_state.active_run_workspace_id, host.model.active_workspace.workspace_id)
        self.assertEqual(host.run_state.engine_state_value, "running")
        self.assertEqual(host._engine_status, ("running", "Starting"))
        self.assertEqual(host._job_counters, (1, 0, 0, 0))
        self.assert_run_controls(
            host,
            run_enabled=False,
            pause_enabled=True,
            stop_enabled=True,
            pause_label="Pause",
        )
        self.assertEqual(host.run_controls_changed.calls, 1)

        start_call = host.execution_client.start_calls[-1]
        self.assertEqual(start_call["project_path"], "demo.sfe")
        self.assertEqual(start_call["workspace_id"], host.model.active_workspace.workspace_id)
        self.assertEqual(start_call["trigger"]["kind"], "manual")
        self.assertEqual(start_call["trigger"]["workflow_settings"], {"general": {"project_name": "Demo"}})
        self.assertNotIn("project_doc", start_call["trigger"])
        runtime_snapshot = start_call["trigger"]["runtime_snapshot"]
        self.assertEqual(runtime_snapshot.active_workspace_id, host.model.active_workspace.workspace_id)
        self.assertEqual(len(runtime_snapshot.workspaces), 1)
        self.assertEqual(
            runtime_snapshot.to_document()["workspaces"][0]["workspace_id"],
            host.model.active_workspace.workspace_id,
        )

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
        self.assert_run_controls(
            host,
            run_enabled=True,
            pause_enabled=False,
            stop_enabled=False,
            pause_label="Pause",
        )
        self.assertEqual(host.run_controls_changed.calls, 1)

    def test_update_run_actions_idle_selected_workspace_enables_only_run(self) -> None:
        host = _RunHostStub()
        controller = RunController(host)  # type: ignore[arg-type]

        controller.update_run_actions()

        self.assert_run_controls(
            host,
            run_enabled=True,
            pause_enabled=False,
            stop_enabled=False,
            pause_label="Pause",
        )
        self.assertEqual(host.run_controls_changed.calls, 1)

    def test_update_run_actions_selected_workspace_owner_running_disables_run_and_enables_pause_stop(self) -> None:
        host = _RunHostStub()
        controller = RunController(host)  # type: ignore[arg-type]
        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = host.model.active_workspace.workspace_id
        host.run_state.engine_state_value = "running"

        controller.update_run_actions()

        self.assert_run_controls(
            host,
            run_enabled=False,
            pause_enabled=True,
            stop_enabled=True,
            pause_label="Pause",
        )
        self.assertEqual(host.run_controls_changed.calls, 1)

    def test_update_run_actions_selected_workspace_owner_paused_uses_resume_label(self) -> None:
        host = _RunHostStub()
        controller = RunController(host)  # type: ignore[arg-type]
        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = host.model.active_workspace.workspace_id
        host.run_state.engine_state_value = "paused"

        controller.update_run_actions()

        self.assert_run_controls(
            host,
            run_enabled=False,
            pause_enabled=True,
            stop_enabled=True,
            pause_label="Resume",
        )
        self.assertEqual(host.run_controls_changed.calls, 1)

    def test_update_run_actions_non_owning_selected_workspace_disables_pause_and_stop(self) -> None:
        host = _RunHostStub()
        controller = RunController(host)  # type: ignore[arg-type]
        owning_workspace_id = host.model.active_workspace.workspace_id
        other_workspace = host.model.create_workspace(name="Second Workspace")
        host.workspace_manager.set_active_workspace(other_workspace.workspace_id)
        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = owning_workspace_id
        host.run_state.engine_state_value = "running"

        controller.update_run_actions()

        self.assert_run_controls(
            host,
            run_enabled=True,
            pause_enabled=False,
            stop_enabled=False,
            pause_label="Pause",
        )
        self.assertEqual(host.run_controls_changed.calls, 1)

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
        host.run_state.active_run_workspace_id = host.model.active_workspace.workspace_id
        controller = RunController(host)  # type: ignore[arg-type]

        controller.handle_execution_event(
            {
                "type": "log",
                "run_id": "run_stale",
                "workspace_id": host.model.active_workspace.workspace_id,
                "level": "error",
                "message": "should be ignored",
            }
        )

        self.assertEqual(host.console_panel.logs, [])
        self.assertEqual(host.run_state.active_run_id, "run_live")

    def test_run_failed_event_focuses_node_logs_traceback_and_clears_active_run(self) -> None:
        host = _RunHostStub()
        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = host.model.active_workspace.workspace_id
        host.run_state.engine_state_value = "running"
        controller = RunController(host)  # type: ignore[arg-type]

        controller.handle_execution_event(
            {
                "type": "run_failed",
                "run_id": "run_live",
                "workspace_id": host.model.active_workspace.workspace_id,
                "node_id": "node_1",
                "error": "boom",
                "traceback": "traceback: line 1",
            }
        )

        self.assertEqual(host.console_panel.logs[-2:], [("error", "boom"), ("error", "traceback: line 1")])
        self.assertEqual(host._notifications, (0, 2))
        self.assertEqual(
            host.workspace_library_controller.focus_calls,
            [(host.model.active_workspace.workspace_id, "node_1", "boom")],
        )
        self.assertEqual(host.run_state.active_run_id, "")
        self.assertEqual(host.run_state.active_run_workspace_id, "")
        self.assertEqual(host.run_state.engine_state_value, "error")
        self.assert_run_controls(
            host,
            run_enabled=True,
            pause_enabled=False,
            stop_enabled=False,
            pause_label="Pause",
        )

    def test_protocol_error_is_logged(self) -> None:
        host = _RunHostStub()
        controller = RunController(host)  # type: ignore[arg-type]

        controller.handle_execution_event({"type": "protocol_error", "error": "bad payload"})

        self.assertEqual(host.console_panel.logs, [("error", "bad payload")])
        self.assertEqual(host._notifications, (0, 1))

    def test_node_execution_bridge_run_events_project_running_and_completed_nodes(self) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = workspace_id
        host.run_state.node_execution_workspace_id = workspace_id
        host.run_state.running_node_ids.add("node_stale")
        host.run_state.node_execution_revision = 4
        controller = RunController(host)  # type: ignore[arg-type]

        controller.handle_execution_event(
            {
                "type": "run_started",
                "run_id": "run_live",
                "workspace_id": workspace_id,
            }
        )

        self.assertEqual(host._failure_clear_count, 1)
        self.assertEqual(host.run_state.running_node_ids, set())
        self.assertEqual(host.run_state.completed_node_ids, set())
        self.assertEqual(host.run_state.node_execution_revision, 5)

        controller.handle_execution_event(
            {
                "type": "node_started",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": "node_1",
            }
        )

        self.assertEqual(host.run_state.node_execution_workspace_id, workspace_id)
        self.assertEqual(host.run_state.running_node_ids, {"node_1"})
        self.assertEqual(host.run_state.completed_node_ids, set())
        self.assertEqual(host.run_state.node_execution_revision, 6)

        controller.handle_execution_event(
            {
                "type": "node_completed",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": "node_1",
            }
        )

        self.assertEqual(host.run_state.running_node_ids, set())
        self.assertEqual(host.run_state.completed_node_ids, {"node_1"})
        self.assertEqual(host.run_state.node_execution_revision, 7)
        self.assertEqual(host._engine_status, ("running", "Running"))

    def test_node_execution_bridge_nonfatal_run_failed_preserves_last_execution_context(self) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = workspace_id
        host.run_state.node_execution_workspace_id = workspace_id
        host.run_state.completed_node_ids.add("node_1")
        host.run_state.node_execution_revision = 2
        controller = RunController(host)  # type: ignore[arg-type]

        controller.handle_execution_event(
            {
                "type": "run_failed",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": "node_1",
                "error": "boom",
                "traceback": "traceback: line 1",
                "fatal": False,
            }
        )

        self.assertEqual(host.run_state.node_execution_workspace_id, workspace_id)
        self.assertEqual(host.run_state.running_node_ids, set())
        self.assertEqual(host.run_state.completed_node_ids, {"node_1"})
        self.assertEqual(host.run_state.node_execution_revision, 2)
        self.assertEqual(host.run_state.active_run_id, "")

    def test_node_execution_bridge_terminal_events_clear_execution_state(self) -> None:
        host = _RunHostStub()
        workspace_id = host.model.active_workspace.workspace_id
        controller = RunController(host)  # type: ignore[arg-type]

        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = workspace_id
        host.run_state.node_execution_workspace_id = workspace_id
        host.run_state.running_node_ids.add("node_1")
        host.run_state.node_execution_revision = 1

        controller.handle_execution_event(
            {
                "type": "run_completed",
                "run_id": "run_live",
                "workspace_id": workspace_id,
            }
        )

        self.assertEqual(host.run_state.node_execution_workspace_id, "")
        self.assertEqual(host.run_state.running_node_ids, set())
        self.assertEqual(host.run_state.completed_node_ids, set())
        self.assertEqual(host.run_state.node_execution_revision, 2)

        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = workspace_id
        host.run_state.node_execution_workspace_id = workspace_id
        host.run_state.completed_node_ids.add("node_2")

        controller.handle_execution_event(
            {
                "type": "run_stopped",
                "run_id": "run_live",
                "workspace_id": workspace_id,
            }
        )

        self.assertEqual(host.run_state.node_execution_workspace_id, "")
        self.assertEqual(host.run_state.running_node_ids, set())
        self.assertEqual(host.run_state.completed_node_ids, set())
        self.assertEqual(host.run_state.node_execution_revision, 3)

        host.run_state.active_run_id = "run_live"
        host.run_state.active_run_workspace_id = workspace_id
        host.run_state.node_execution_workspace_id = workspace_id
        host.run_state.running_node_ids.add("node_3")

        controller.handle_execution_event(
            {
                "type": "run_failed",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": "node_3",
                "error": "fatal boom",
                "traceback": "traceback: line 9",
                "fatal": True,
            }
        )

        self.assertEqual(host.run_state.node_execution_workspace_id, "")
        self.assertEqual(host.run_state.running_node_ids, set())
        self.assertEqual(host.run_state.completed_node_ids, set())
        self.assertEqual(host.run_state.node_execution_revision, 4)


if __name__ == "__main__":
    unittest.main()
