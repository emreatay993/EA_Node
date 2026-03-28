from __future__ import annotations

import asyncio
import queue
import time
import traceback
from collections.abc import Callable
from multiprocessing import Queue
from typing import Any

from ea_node_editor.execution.protocol import (
    PauseRunCommand,
    ResumeRunCommand,
    RunCompletedEvent,
    RunFailedEvent,
    RunStartedEvent,
    RunStoppedEvent,
    ShutdownCommand,
    StartRunCommand,
    StopRunCommand,
    WorkerCommand,
    WorkerEvent,
)
from ea_node_editor.execution.runtime_snapshot import (
    RuntimeSnapshot,
    RuntimeSnapshotContext,
    sanitize_execution_trigger,
)
from ea_node_editor.execution.worker_protocol import (
    decode_command_payload,
    dispatch_viewer_command,
    emit,
    emit_protocol_error,
    emit_run_state,
    is_viewer_command,
)
from ea_node_editor.execution.worker_runtime import (
    ExecutionPlan,
    RuntimeArtifactService,
    prepare_runtime,
)
from ea_node_editor.execution.worker_services import WorkerServices
from ea_node_editor.nodes.types import ExecutionContext


class RunControl:
    def __init__(
        self,
        command_queue: Queue | None,
        event_queue: Queue,
        *,
        run_id: str,
        workspace_id: str,
        viewer_command_handler: Callable[[WorkerCommand], None] | None = None,
    ) -> None:
        self._command_queue = command_queue
        self._event_queue = event_queue
        self.run_id = run_id
        self.workspace_id = workspace_id
        self._viewer_command_handler = viewer_command_handler
        self.paused = False
        self.stop_requested = False
        self.shutdown_requested = False
        self.stop_reason = ""
        self._cancel_callbacks: list[Callable[[], None]] = []

    def register_cancel_callback(self, callback: Callable[[], None]) -> None:
        if not callable(callback):
            return
        self._cancel_callbacks.append(callback)

    def _invoke_cancel_callbacks(self) -> None:
        callbacks = list(self._cancel_callbacks)
        self._cancel_callbacks.clear()
        for callback in callbacks:
            try:
                callback()
            except Exception:  # noqa: BLE001
                continue

    def clear_cancel_callbacks(self) -> None:
        self._cancel_callbacks.clear()

    def _handle_command(self, command: WorkerCommand) -> None:
        command_type = command.type
        command_run_id = getattr(command, "run_id", "")
        command_workspace_id = getattr(command, "workspace_id", "")
        command_request_id = getattr(command, "request_id", "")

        if isinstance(command, ShutdownCommand):
            self.shutdown_requested = True
            self.stop_requested = True
            self.stop_reason = "shutdown_requested"
            self._invoke_cancel_callbacks()
            return

        if command_run_id and command_run_id != self.run_id:
            emit_protocol_error(
                self._event_queue,
                "Ignoring command for inactive run.",
                run_id=command_run_id,
                workspace_id=command_workspace_id,
                request_id=command_request_id,
                command=command_type,
            )
            return

        if isinstance(command, PauseRunCommand):
            if not self.paused:
                self.paused = True
                emit_run_state(
                    self._event_queue,
                    run_id=self.run_id,
                    workspace_id=self.workspace_id,
                    state="paused",
                    transition="pause",
                    reason="pause_requested",
                )
            return

        if isinstance(command, ResumeRunCommand):
            if self.paused:
                self.paused = False
                emit_run_state(
                    self._event_queue,
                    run_id=self.run_id,
                    workspace_id=self.workspace_id,
                    state="running",
                    transition="resume",
                    reason="resume_requested",
                )
            return

        if isinstance(command, StopRunCommand):
            self.stop_requested = True
            self.stop_reason = "stop_requested"
            self._invoke_cancel_callbacks()
            return

        if is_viewer_command(command):
            if self._viewer_command_handler is None:
                emit_protocol_error(
                    self._event_queue,
                    "Viewer command handler is unavailable.",
                    workspace_id=command_workspace_id,
                    request_id=command_request_id,
                    command=command_type,
                )
                return
            self._viewer_command_handler(command)
            return

        if isinstance(command, StartRunCommand):
            emit_protocol_error(
                self._event_queue,
                "Worker already has an active run.",
                run_id=command_run_id,
                workspace_id=command_workspace_id,
                request_id=command_request_id,
                command=command_type,
            )
            return

        emit_protocol_error(
            self._event_queue,
            "Unsupported command while run is active.",
            run_id=command_run_id or self.run_id,
            workspace_id=command_workspace_id or self.workspace_id,
            request_id=command_request_id,
            command=command_type,
        )

    def poll_commands(self) -> None:
        if self._command_queue is None:
            return
        while True:
            try:
                raw_command = self._command_queue.get_nowait()
            except queue.Empty:
                return
            command = decode_command_payload(raw_command, event_queue=self._event_queue)
            if command is None:
                continue
            self._handle_command(command)

    def wait_until_runnable(self) -> None:
        while self.paused and not self.stop_requested and not self.shutdown_requested:
            time.sleep(0.05)
            self.poll_commands()

    def should_stop(self) -> bool:
        self.poll_commands()
        return self.stop_requested or self.shutdown_requested


class RunEventPublisher:
    def __init__(self, event_queue: Queue, *, run_id: str, workspace_id: str) -> None:
        self._event_queue = event_queue
        self.run_id = run_id
        self.workspace_id = workspace_id

    def emit(self, event: WorkerEvent) -> None:
        emit(self._event_queue, event)

    def emit_run_started(self) -> None:
        self.emit(RunStartedEvent(run_id=self.run_id, workspace_id=self.workspace_id))
        self.emit_run_state(state="running", transition="start", reason="run_started")

    def emit_run_state(self, *, state: str, transition: str, reason: str) -> None:
        emit_run_state(
            self._event_queue,
            run_id=self.run_id,
            workspace_id=self.workspace_id,
            state=state,
            transition=transition,
            reason=reason,
        )

    def emit_run_completed(self) -> None:
        self.emit(RunCompletedEvent(run_id=self.run_id, workspace_id=self.workspace_id))
        self.emit_run_state(state="ready", transition="complete", reason="run_completed")

    def emit_run_stopped(self, reason: str) -> None:
        self.emit(
            RunStoppedEvent(
                run_id=self.run_id,
                workspace_id=self.workspace_id,
                reason=reason,
            )
        )
        self.emit_run_state(state="ready", transition="stop", reason=reason)

    def emit_run_failed(
        self,
        *,
        node_id: str,
        error: str,
        traceback_text: str,
        reason: str,
    ) -> None:
        self.emit(
            RunFailedEvent(
                run_id=self.run_id,
                workspace_id=self.workspace_id,
                node_id=node_id,
                error=error,
                traceback=traceback_text,
            )
        )
        self.emit_run_state(state="error", transition="fail", reason=reason)

    def emit_node_started(self, node_id: str) -> None:
        from ea_node_editor.execution.protocol import NodeStartedEvent

        self.emit(
            NodeStartedEvent(
                run_id=self.run_id,
                workspace_id=self.workspace_id,
                node_id=node_id,
            )
        )

    def emit_node_completed(self, node_id: str, outputs: dict[str, Any]) -> None:
        from ea_node_editor.execution.protocol import NodeCompletedEvent

        self.emit(
            NodeCompletedEvent(
                run_id=self.run_id,
                workspace_id=self.workspace_id,
                node_id=node_id,
                outputs=dict(outputs),
            )
        )

    def emit_log(self, level: str, message: str, *, node_id: str = "") -> None:
        from ea_node_editor.execution.protocol import LogEvent

        self.emit(
            LogEvent(
                run_id=self.run_id,
                workspace_id=self.workspace_id,
                node_id=node_id,
                level=level,
                message=message,
            )
        )


class NodeExecutor:
    def __init__(
        self,
        execution_plan: ExecutionPlan,
        registry: Any,
        control: RunControl,
        publisher: RunEventPublisher,
        *,
        artifact_service: RuntimeArtifactService,
        worker_services: WorkerServices,
        project_path: str,
        runtime_snapshot: RuntimeSnapshot,
        runtime_context: RuntimeSnapshotContext,
        trigger: dict[str, Any],
    ) -> None:
        self._plan = execution_plan
        self._registry = registry
        self._control = control
        self._publisher = publisher
        self._artifact_service = artifact_service
        self._worker_services = worker_services
        self._project_path = str(project_path).strip()
        self._runtime_snapshot = runtime_snapshot
        self._runtime_context = runtime_context
        self._trigger = trigger
        self.node_outputs: dict[str, dict[str, Any]] = {}
        self.executed: set[str] = set()
        self._dependency_stack: set[str] = set()

    def run_node(self, node_id: str) -> str:
        if node_id in self.executed:
            return "ok"
        status = self._await_runnable()
        if status is not None:
            return status
        dependency_status = self._resolve_dependencies(node_id)
        if dependency_status != "ok":
            return dependency_status
        status = self._await_runnable()
        if status is not None:
            return status
        return self._execute_node(node_id)

    def _await_runnable(self) -> str | None:
        self._control.poll_commands()
        if self._control.shutdown_requested or self._control.stop_requested:
            return "stopped"
        self._control.wait_until_runnable()
        if self._control.shutdown_requested or self._control.stop_requested:
            return "stopped"
        return None

    def _resolve_dependencies(self, node_id: str) -> str:
        for source_node_id in self._plan.dependency_sources_for(node_id):
            if source_node_id in self.executed or source_node_id in self._dependency_stack:
                continue
            self._dependency_stack.add(source_node_id)
            try:
                status = self.run_node(source_node_id)
            finally:
                self._dependency_stack.discard(source_node_id)
            if status != "ok":
                return status
        return "ok"

    def _execute_node(self, node_id: str) -> str:
        node = self._plan.nodes[node_id]
        node_type_id = node.type_id
        plugin = self._registry.create(node_type_id)
        inputs = self._plan.input_values_for(node_id, self.node_outputs)

        self._publisher.emit_node_started(node_id)

        def _log(level: str, message: str) -> None:
            self._publisher.emit_log(level, message, node_id=node_id)

        ctx = ExecutionContext(
            run_id=self._publisher.run_id,
            node_id=node_id,
            workspace_id=self._publisher.workspace_id,
            inputs=inputs,
            properties=self._registry.normalize_properties(node_type_id, dict(node.properties)),
            emit_log=_log,
            trigger=self._trigger,
            should_stop=self._control.should_stop,
            register_cancel=self._control.register_cancel_callback,
            project_path=self._project_path,
            runtime_snapshot=self._runtime_snapshot,
            runtime_snapshot_context=self._runtime_context,
            path_resolver=self._artifact_service.resolve_path,
            worker_services=self._worker_services,
        )

        try:
            spec = self._plan.node_specs[node_id]
            if spec.is_async and hasattr(plugin, "async_execute") and callable(plugin.async_execute):
                result = asyncio.run(plugin.async_execute(ctx))
            else:
                result = plugin.execute(ctx)
            if self._control.should_stop():
                return "stopped"

            outputs = self._artifact_service.normalize_outputs(dict(result.outputs))
            self.node_outputs[node_id] = outputs
            self._publisher.emit_node_completed(node_id, outputs)
            self.executed.add(node_id)
            return "ok"
        except InterruptedError:
            if self._control.should_stop():
                return "stopped"
            raise
        except Exception as exc:  # noqa: BLE001
            error_str = str(exc)
            traceback_text = traceback.format_exc()
            self.node_outputs[node_id] = {"error": error_str, "traceback": traceback_text}

            if self._plan.has_failure_downstream(node_id):
                self._publisher.emit_log(
                    "warning",
                    f"Node failed but has failure handlers: {error_str}",
                    node_id=node_id,
                )
                self.executed.add(node_id)
                return "failed_handled"

            self._publisher.emit_run_failed(
                node_id=node_id,
                error=error_str,
                traceback_text=traceback_text,
                reason="node_exception",
            )
            return "failed"
        finally:
            self._control.clear_cancel_callbacks()


class WorkflowRunner:
    def __init__(
        self,
        command: StartRunCommand,
        event_queue: Queue,
        command_queue: Queue | None = None,
        worker_services: WorkerServices | None = None,
    ) -> None:
        self._command = command
        self._worker_services = worker_services or WorkerServices()
        self._control = RunControl(
            command_queue,
            event_queue,
            run_id=command.run_id,
            workspace_id=command.workspace_id,
            viewer_command_handler=lambda viewer_command: dispatch_viewer_command(
                viewer_command,
                event_queue=event_queue,
                worker_services=self._worker_services,
            ),
        )
        self._publisher = RunEventPublisher(
            event_queue,
            run_id=command.run_id,
            workspace_id=command.workspace_id,
        )
        prepared = prepare_runtime(command)
        self._registry = prepared.registry
        self._runtime_snapshot = prepared.runtime_snapshot
        self._runtime_context = prepared.runtime_context
        self._plan = prepared.plan
        self._worker_services.viewer_session_service.prepare_workspace_context(
            workspace_id=command.workspace_id,
            project_path=command.project_path,
            runtime_snapshot=self._runtime_snapshot,
            runtime_snapshot_context=self._runtime_context,
            invalidate_existing=True,
        )
        self._artifact_service = RuntimeArtifactService(
            runtime_context=self._runtime_context,
        )
        self._executor = NodeExecutor(
            self._plan,
            self._registry,
            self._control,
            self._publisher,
            artifact_service=self._artifact_service,
            worker_services=self._worker_services,
            project_path=command.project_path,
            runtime_snapshot=self._runtime_snapshot,
            runtime_context=self._runtime_context,
            trigger=sanitize_execution_trigger(command.trigger),
        )

    def run(self) -> None:
        try:
            self._publisher.emit_run_started()
            self._publisher.emit_log("info", "Workflow run started.")

            ready = self._plan.initial_ready()
            while ready:
                node_id = ready.popleft()
                if node_id in self._executor.executed:
                    continue
                status = self._executor.run_node(node_id)
                if self._handle_terminal_status(status):
                    return
                ready.extend(self._plan.release_downstream(node_id, status))

            if not self._executor.executed and self._plan.has_only_dependency_nodes():
                for node_id in self._plan.dependency_sinks():
                    if node_id in self._executor.executed:
                        continue
                    status = self._executor.run_node(node_id)
                    if self._handle_terminal_status(status):
                        return

            self._publisher.emit_run_completed()
        finally:
            self._worker_services.cleanup_run(self._command.run_id)

    def _handle_terminal_status(self, status: str) -> bool:
        if status == "failed":
            return True
        if status == "stopped":
            self._publisher.emit_run_stopped(self._control.stop_reason or "stop_requested")
            return True
        return False


__all__ = [
    "NodeExecutor",
    "RunControl",
    "RunEventPublisher",
    "WorkflowRunner",
]
