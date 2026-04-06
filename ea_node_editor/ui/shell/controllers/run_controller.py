from __future__ import annotations

from typing import Any, Literal, Protocol

from ea_node_editor.execution.runtime_snapshot import build_runtime_snapshot
from ea_node_editor.ui.icon_registry import qicon
from ea_node_editor.ui.shell.run_flow import (
    event_targets_active_run,
    selected_workspace_run_control_state,
)
from ea_node_editor.ui.shell.state import ShellRunState


class _WorkflowSettingsSourceProtocol(Protocol):
    def workflow_settings_payload(self) -> dict[str, Any]: ...


class _RunFailureFocusProtocol(Protocol):
    def focus_failed_node(self, workspace_id: str, node_id: str, error: str) -> None: ...


class _RunControllerHostProtocol(Protocol):
    run_state: ShellRunState
    project_path: str
    workspace_manager: Any
    serializer: Any
    model: Any
    registry: Any
    project_session_controller: _WorkflowSettingsSourceProtocol
    console_panel: Any
    execution_client: Any
    workspace_library_controller: _RunFailureFocusProtocol
    action_run: Any
    action_stop: Any
    action_pause: Any
    run_controls_changed: Any
    _RUN_SCOPED_EVENT_TYPES: set[str]

    def update_notification_counters(self, warning_count: int, error_count: int) -> None: ...

    def update_engine_status(self, state: str, details: str) -> None: ...

    def update_job_counters(self, running: int, queued: int, done: int, failed: int) -> None: ...

    def clear_run_failure_focus(self) -> None: ...

    def mark_node_execution_running(self, workspace_id: str, node_id: str) -> None: ...

    def mark_node_execution_completed(self, workspace_id: str, node_id: str) -> None: ...

    def clear_node_execution_visualization_state(self) -> None: ...


class RunController:
    def __init__(self, host: _RunControllerHostProtocol) -> None:
        self._host = host

    @property
    def _state(self) -> ShellRunState:
        return self._host.run_state

    def run_workflow(self) -> None:
        if self._state.active_run_id:
            if self._state.engine_state_value == "paused":
                self.resume_workflow()
            else:
                self._host.console_panel.append_log("warning", "A workflow run is already active.")
                self._host.update_notification_counters(
                    self._host.console_panel.warning_count,
                    self._host.console_panel.error_count,
                )
            return

        self._host.clear_run_failure_focus()
        workspace_id = self._host.workspace_manager.active_workspace_id()
        runtime_snapshot = build_runtime_snapshot(
            self._host.model.project,
            workspace_id=workspace_id,
            registry=self._host.registry,
        )
        trigger = {
            "kind": "manual",
            "workflow_settings": self._host.project_session_controller.workflow_settings_payload(),
            "runtime_snapshot": runtime_snapshot,
        }
        self._host.console_panel.clear_all()
        run_id = self._host.execution_client.start_run(
            project_path=self._host.project_path,
            workspace_id=workspace_id,
            trigger=trigger,
        )
        if not run_id:
            self._host.console_panel.append_log("error", "Failed to start workflow run.")
            self._host.update_notification_counters(
                self._host.console_panel.warning_count,
                self._host.console_panel.error_count,
            )
            self.set_run_ui_state("error", "Start Failed", 0, 0, 0, 1, clear_run=True)
            return
        self._state.active_run_id = run_id
        self._state.active_run_workspace_id = workspace_id
        self._invalidate_viewer_sessions_for_rerun(workspace_id=workspace_id, run_id=run_id)
        self.set_run_ui_state("running", "Starting", 1, 0, 0, 0)

    def toggle_pause_resume(self) -> None:
        if not self._state.active_run_id:
            return
        if self._state.engine_state_value == "paused":
            self.resume_workflow()
        elif self._state.engine_state_value == "running":
            self.pause_workflow()

    def pause_workflow(self) -> None:
        if not self._state.active_run_id or self._state.engine_state_value != "running":
            return
        self._host.execution_client.pause_run(self._state.active_run_id)
        self._host.update_engine_status("running", "Pausing")

    def resume_workflow(self) -> None:
        if not self._state.active_run_id or self._state.engine_state_value != "paused":
            return
        self._host.execution_client.resume_run(self._state.active_run_id)
        self._host.update_engine_status("running", "Resuming")

    def stop_workflow(self) -> None:
        if not self._state.active_run_id:
            return
        self._host.execution_client.stop_run(self._state.active_run_id)
        if self._state.engine_state_value == "paused":
            self._host.update_engine_status("paused", "Stopping")
        else:
            self._host.update_engine_status("running", "Stopping")
        self.update_run_actions()

    def handle_execution_event(self, event: dict[str, Any]) -> None:
        event_type = str(event.get("type", ""))
        if not event_targets_active_run(
            event,
            active_run_id=self._state.active_run_id,
            run_scoped_event_types=self._host._RUN_SCOPED_EVENT_TYPES,
        ):
            return

        if event_type == "run_started":
            workspace_id = self._event_workspace_id(event)
            if workspace_id:
                self._state.active_run_workspace_id = workspace_id
            self._host.clear_node_execution_visualization_state()
            self._host.clear_run_failure_focus()
        elif event_type == "node_started":
            self._host.mark_node_execution_running(
                self._event_workspace_id(event),
                str(event.get("node_id", "")),
            )
        elif event_type == "node_completed":
            self._host.mark_node_execution_completed(
                self._event_workspace_id(event),
                str(event.get("node_id", "")),
            )

        if event_type == "run_started" or (
            event_type in {"node_started", "node_completed"} and self._state.engine_state_value != "paused"
        ):
            self.set_run_ui_state("running", "Running", 1, 0, 0, 0)

        if event_type == "log":
            self._host.console_panel.append_log(event.get("level", "info"), event.get("message", ""))
            self._host.update_notification_counters(
                self._host.console_panel.warning_count,
                self._host.console_panel.error_count,
            )
        elif event_type == "run_completed":
            self._host.clear_node_execution_visualization_state()
            self.set_run_ui_state("ready", "Completed", 0, 0, 1, 0, clear_run=True)
        elif event_type == "run_failed":
            self.set_run_ui_state("error", "Failed", 0, 0, 0, 1)
            self._host.console_panel.append_log("error", event.get("error", "Unknown failure"))
            self._host.console_panel.append_log("error", event.get("traceback", ""))
            self._host.update_notification_counters(
                self._host.console_panel.warning_count,
                self._host.console_panel.error_count,
            )
            self._host.workspace_library_controller.focus_failed_node(
                event.get("workspace_id", ""),
                event.get("node_id", ""),
                event.get("error", ""),
            )
            if bool(event.get("fatal", False)):
                self._host.clear_node_execution_visualization_state()
                self._invalidate_viewer_sessions_for_worker_reset()
            self.clear_active_run()
            self.update_run_actions()
        elif event_type == "run_stopped":
            self._host.clear_node_execution_visualization_state()
            self.set_run_ui_state("ready", "Stopped", 0, 0, 0, 0, clear_run=True)
        elif event_type == "run_state":
            state = event.get("state", "ready")
            transition = str(event.get("transition", ""))
            if state == "paused" or transition == "pause":
                self.set_run_ui_state("paused", "Paused", 1, 0, 0, 0)
            elif state == "running":
                self.set_run_ui_state("running", "Running", 1, 0, 0, 0)
            elif transition == "stop":
                self._host.clear_node_execution_visualization_state()
                self.set_run_ui_state("ready", "Stopped", 0, 0, 0, 0, clear_run=True)
            elif state == "error":
                self.set_run_ui_state("error", "Failed", 0, 0, 0, 1)
        elif event_type == "protocol_error":
            self._host.console_panel.append_log("error", event.get("error", "Execution protocol error."))
            self._host.update_notification_counters(
                self._host.console_panel.warning_count,
                self._host.console_panel.error_count,
            )

    def clear_active_run(self) -> None:
        self._state.active_run_id = ""
        self._state.active_run_workspace_id = ""

    def set_run_ui_state(
        self,
        state: Literal["ready", "running", "paused", "error"],
        details: str,
        running: int,
        queued: int,
        done: int,
        failed: int,
        *,
        clear_run: bool = False,
    ) -> None:
        self._state.engine_state_value = state
        self._host.update_engine_status(state, details)
        self._host.update_job_counters(running, queued, done, failed)
        if clear_run:
            self.clear_active_run()
        self.update_run_actions()

    def update_run_actions(self) -> None:
        projection = selected_workspace_run_control_state(
            selected_workspace_id=self._host.workspace_manager.active_workspace_id(),
            active_run_id=self._state.active_run_id,
            active_run_workspace_id=self._state.active_run_workspace_id,
            engine_state=self._state.engine_state_value,
        )
        self._host.action_run.setEnabled(projection.can_run_active_workspace)
        self._host.action_stop.setEnabled(projection.can_stop_active_workspace)
        self._host.action_pause.setEnabled(projection.can_pause_active_workspace)
        self._host.action_pause.setText(projection.pause_label)
        if hasattr(self._host.action_pause, "setIcon"):
            self._host.action_pause.setIcon(qicon("resume" if projection.pause_label == "Resume" else "pause"))
        self._host.run_controls_changed.emit()

    def _event_workspace_id(self, event: dict[str, Any]) -> str:
        workspace_id = str(event.get("workspace_id", "") or "").strip()
        if workspace_id:
            return workspace_id
        return str(self._state.active_run_workspace_id or "").strip()

    def _invalidate_viewer_sessions_for_rerun(self, *, workspace_id: str, run_id: str) -> None:
        viewer_session_bridge = getattr(self._host, "viewer_session_bridge", None)
        if viewer_session_bridge is None:
            return
        project_workspace_run_required = getattr(viewer_session_bridge, "project_workspace_run_required", None)
        if callable(project_workspace_run_required):
            project_workspace_run_required(
                workspace_id,
                reason="workspace_rerun",
                run_id=run_id,
            )
            return
        invalidate_workspace_sessions = getattr(viewer_session_bridge, "invalidate_workspace_sessions", None)
        if not callable(invalidate_workspace_sessions):
            return
        invalidate_workspace_sessions(
            workspace_id,
            reason="workspace_rerun",
            run_id=run_id,
        )

    def _invalidate_viewer_sessions_for_worker_reset(self) -> None:
        viewer_session_bridge = getattr(self._host, "viewer_session_bridge", None)
        if viewer_session_bridge is None:
            return
        project_all_run_required = getattr(viewer_session_bridge, "project_all_run_required", None)
        if callable(project_all_run_required):
            project_all_run_required(reason="worker_reset")
            return
        invalidate_all_sessions = getattr(viewer_session_bridge, "invalidate_all_sessions", None)
        if not callable(invalidate_all_sessions):
            return
        invalidate_all_sessions(reason="worker_reset")
