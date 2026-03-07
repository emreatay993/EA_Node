"""Handles workflow execution: run, pause, resume, stop, and event processing."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from PyQt6.QtCore import QObject, Qt, pyqtSignal

from ea_node_editor.execution.client import ProcessExecutionClient

if TYPE_CHECKING:
    from ea_node_editor.ui_qml.models import ConsoleModel, StatusItemModel


class ExecutionController(QObject):
    execution_event = pyqtSignal(dict)
    engine_state_changed = pyqtSignal(str, str)
    run_finished = pyqtSignal()
    node_failed = pyqtSignal(str, str, str)

    _RUN_SCOPED_EVENT_TYPES = {
        "run_started", "run_state", "run_completed", "run_failed",
        "run_stopped", "node_started", "node_completed", "log",
    }

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._active_run_id = ""
        self._active_run_workspace_id = ""
        self._engine_state: Literal["ready", "running", "paused", "error"] = "ready"

        self.client = ProcessExecutionClient()
        self.client.subscribe(self.execution_event.emit)
        self.execution_event.connect(self._handle_event, Qt.ConnectionType.QueuedConnection)

    @property
    def active_run_id(self) -> str:
        return self._active_run_id

    @property
    def engine_state(self) -> str:
        return self._engine_state

    def start_run(
        self,
        project_path: str,
        workspace_id: str,
        trigger: dict[str, Any],
    ) -> str:
        if self._active_run_id:
            return ""
        run_id = self.client.start_run(
            project_path=project_path,
            workspace_id=workspace_id,
            trigger=trigger,
        )
        if run_id:
            self._active_run_id = run_id
            self._active_run_workspace_id = workspace_id
            self._set_state("running", "Starting")
        return run_id

    def pause(self) -> None:
        if self._active_run_id and self._engine_state == "running":
            self.client.pause_run(self._active_run_id)
            self._set_state("running", "Pausing")

    def resume(self) -> None:
        if self._active_run_id and self._engine_state == "paused":
            self.client.resume_run(self._active_run_id)
            self._set_state("running", "Resuming")

    def stop(self) -> None:
        if not self._active_run_id:
            return
        self.client.stop_run(self._active_run_id)
        self._set_state(self._engine_state, "Stopping")

    def toggle_pause_resume(self) -> None:
        if self._engine_state == "paused":
            self.resume()
        elif self._engine_state == "running":
            self.pause()

    def shutdown(self) -> None:
        self._active_run_id = ""
        self._active_run_workspace_id = ""
        self.client.shutdown()

    def _set_state(self, state: str, details: str = "") -> None:
        self._engine_state = state  # type: ignore[assignment]
        self.engine_state_changed.emit(state, details)

    def _clear_run(self) -> None:
        self._active_run_id = ""
        self._active_run_workspace_id = ""
        self.run_finished.emit()

    def _event_targets_active_run(self, event: dict[str, Any]) -> bool:
        event_type = str(event.get("type", ""))
        if event_type not in self._RUN_SCOPED_EVENT_TYPES:
            return True
        event_run_id = str(event.get("run_id", ""))
        return bool(self._active_run_id and event_run_id and event_run_id == self._active_run_id)

    def _handle_event(self, event: dict) -> None:
        event_type = str(event.get("type", ""))
        if not self._event_targets_active_run(event):
            return

        if event_type in {"run_started", "node_started", "node_completed"}:
            self._set_state("running", "Running")
        elif event_type == "run_completed":
            self._set_state("ready", "Completed")
            self._clear_run()
        elif event_type == "run_failed":
            self._set_state("error", "Failed")
            self.node_failed.emit(
                event.get("workspace_id", ""),
                event.get("node_id", ""),
                event.get("error", ""),
            )
            self._clear_run()
        elif event_type == "run_stopped":
            self._set_state("ready", "Stopped")
            self._clear_run()
        elif event_type == "run_state":
            state = event.get("state", "ready")
            transition = str(event.get("transition", ""))
            if state == "paused" or transition == "pause":
                self._set_state("paused", "Paused")
            elif state == "running":
                self._set_state("running", "Running")
            elif transition == "stop":
                self._set_state("ready", "Stopped")
                self._clear_run()
            elif state == "error":
                self._set_state("error", "Failed")
