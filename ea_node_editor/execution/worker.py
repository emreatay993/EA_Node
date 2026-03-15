from __future__ import annotations

import asyncio
import queue
import time
import traceback
from collections import defaultdict, deque
from collections.abc import Callable
from multiprocessing import Queue
from typing import Any

from ea_node_editor.execution.protocol import (
    LogEvent,
    NodeCompletedEvent,
    NodeStartedEvent,
    PauseRunCommand,
    ProtocolErrorEvent,
    ResumeRunCommand,
    RunCompletedEvent,
    RunFailedEvent,
    RunStartedEvent,
    RunStateEvent,
    RunStoppedEvent,
    ShutdownCommand,
    StartRunCommand,
    StopRunCommand,
    WorkerCommand,
    WorkerEvent,
    dict_to_command,
    event_to_dict,
)
from ea_node_editor.execution.compiler import compile_workspace_document
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.types import ExecutionContext
from ea_node_editor.persistence.serializer import JsonProjectSerializer


def _find_port_kind(type_id: str, key: str, registry) -> str:
    spec = registry.get_spec(type_id)
    for port in spec.ports:
        if port.key == key:
            return port.kind
    return "data"


def _workspace_doc_from_project(project_doc: dict[str, Any], workspace_id: str) -> dict[str, Any]:
    for workspace_doc in project_doc.get("workspaces", []):
        if workspace_doc.get("workspace_id") == workspace_id:
            return workspace_doc
    raise KeyError(f"Workspace not found in project doc: {workspace_id}")


def _emit(event_queue: Queue, event: WorkerEvent) -> None:
    event_queue.put(event_to_dict(event))


def _emit_run_state(
    event_queue: Queue,
    *,
    run_id: str,
    workspace_id: str,
    state: str,
    transition: str,
    reason: str,
) -> None:
    _emit(
        event_queue,
        RunStateEvent(
            run_id=run_id,
            workspace_id=workspace_id,
            state=state,  # type: ignore[arg-type]
            transition=transition,
            reason=reason,
        ),
    )


def _emit_protocol_error(
    event_queue: Queue,
    message: str,
    *,
    run_id: str = "",
    workspace_id: str = "",
    command: str = "",
) -> None:
    _emit(
        event_queue,
        ProtocolErrorEvent(
            run_id=run_id,
            workspace_id=workspace_id,
            command=command,
            error=message,
        ),
    )


def _load_project_doc(command: StartRunCommand, serializer: JsonProjectSerializer) -> dict[str, Any]:
    if command.project_doc:
        return dict(command.project_doc)
    path = command.project_path
    if not path:
        raise ValueError("Missing project_path and project_doc")
    project = serializer.load(path)
    return serializer.to_document(project)


class _RunControl:
    def __init__(
        self,
        command_queue: Queue | None,
        event_queue: Queue,
        *,
        run_id: str,
        workspace_id: str,
    ) -> None:
        self._command_queue = command_queue
        self._event_queue = event_queue
        self.run_id = run_id
        self.workspace_id = workspace_id
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

        if isinstance(command, ShutdownCommand):
            self.shutdown_requested = True
            self.stop_requested = True
            self.stop_reason = "shutdown_requested"
            self._invoke_cancel_callbacks()
            return

        if command_run_id and command_run_id != self.run_id:
            _emit_protocol_error(
                self._event_queue,
                "Ignoring command for inactive run.",
                run_id=command_run_id,
                workspace_id=command_workspace_id,
                command=command_type,
            )
            return

        if isinstance(command, PauseRunCommand):
            if not self.paused:
                self.paused = True
                _emit_run_state(
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
                _emit_run_state(
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

        if isinstance(command, StartRunCommand):
            _emit_protocol_error(
                self._event_queue,
                "Worker already has an active run.",
                run_id=command_run_id,
                workspace_id=command_workspace_id,
                command=command_type,
            )
            return

        _emit_protocol_error(
            self._event_queue,
            "Unsupported command while run is active.",
            run_id=command_run_id or self.run_id,
            workspace_id=command_workspace_id or self.workspace_id,
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
            if not isinstance(raw_command, dict):
                _emit_protocol_error(self._event_queue, "Command payload must be a dictionary.")
                continue
            try:
                command = dict_to_command(dict(raw_command))
            except ValueError as exc:
                _emit_protocol_error(self._event_queue, f"Invalid command payload: {exc}")
                continue
            self._handle_command(command)

    def wait_until_runnable(self) -> None:
        while self.paused and not self.stop_requested and not self.shutdown_requested:
            time.sleep(0.05)
            self.poll_commands()

    def should_stop(self) -> bool:
        self.poll_commands()
        return self.stop_requested or self.shutdown_requested


def run_workflow(
    command: StartRunCommand | dict[str, Any],
    event_queue: Queue,
    command_queue: Queue | None = None,
) -> None:
    if isinstance(command, dict):
        if "type" in command:
            typed_command = dict_to_command(command)
            if not isinstance(typed_command, StartRunCommand):
                raise ValueError("run_workflow requires a start_run command payload.")
        else:
            project_doc = command.get("project_doc")
            typed_command = StartRunCommand(
                run_id=str(command.get("run_id", "")),
                project_path=str(command.get("project_path", "")),
                workspace_id=str(command.get("workspace_id", "")),
                trigger=dict(command.get("trigger", {})) if isinstance(command.get("trigger"), dict) else {},
                project_doc=dict(project_doc) if isinstance(project_doc, dict) else {},
            )
    else:
        typed_command = command

    run_id = typed_command.run_id
    workspace_id = typed_command.workspace_id
    trigger = dict(typed_command.trigger)
    control = _RunControl(command_queue, event_queue, run_id=run_id, workspace_id=workspace_id)
    registry = build_default_registry()
    serializer = JsonProjectSerializer(registry)
    project_doc = _load_project_doc(typed_command, serializer)
    workspace = compile_workspace_document(
        _workspace_doc_from_project(project_doc, workspace_id),
        registry=registry,
    )

    nodes = {node["node_id"]: node for node in workspace.get("nodes", [])}
    edges = list(workspace.get("edges", []))
    node_outputs: dict[str, dict[str, Any]] = {}
    executed: set[str] = set()

    exec_outgoing: dict[str, list[str]] = defaultdict(list)
    failed_outgoing: dict[str, list[str]] = defaultdict(list)
    data_incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    exec_incoming_count: dict[str, int] = {node_id: 0 for node_id in nodes}

    for edge in edges:
        source_node_id = edge["source_node_id"]
        target_node_id = edge["target_node_id"]
        source_type_id = nodes[source_node_id]["type_id"]
        source_kind = _find_port_kind(source_type_id, edge["source_port_key"], registry)
        if source_kind == "failed":
            failed_outgoing[source_node_id].append(target_node_id)
            exec_incoming_count[target_node_id] += 1
        elif source_kind in {"exec", "completed"}:
            exec_outgoing[source_node_id].append(target_node_id)
            exec_incoming_count[target_node_id] += 1
        elif source_kind == "flow":
            continue
        else:
            data_incoming[target_node_id].append(edge)

    start_nodes = [node_id for node_id, node in nodes.items() if node["type_id"] == "core.start"]
    if start_nodes:
        ready = deque(start_nodes)
    else:
        ready = deque(sorted(node_id for node_id, count in exec_incoming_count.items() if count == 0))

    _emit(event_queue, RunStartedEvent(run_id=run_id, workspace_id=workspace_id))
    _emit_run_state(
        event_queue,
        run_id=run_id,
        workspace_id=workspace_id,
        state="running",
        transition="start",
        reason="run_started",
    )

    def emit_stopped(reason: str) -> None:
        _emit(
            event_queue,
            RunStoppedEvent(
                run_id=run_id,
                workspace_id=workspace_id,
                reason=reason,
            ),
        )
        _emit_run_state(
            event_queue,
            run_id=run_id,
            workspace_id=workspace_id,
            state="ready",
            transition="stop",
            reason=reason,
        )

    _emit(
        event_queue,
        LogEvent(
            run_id=run_id,
            workspace_id=workspace_id,
            level="info",
            message="Workflow run started.",
        ),
    )

    def execute_node(node_id: str) -> str:
        node = nodes[node_id]
        plugin = registry.create(node["type_id"])

        inputs: dict[str, Any] = {}
        for edge in data_incoming.get(node_id, []):
            source_id = edge["source_node_id"]
            source_outputs = node_outputs.get(source_id, {})
            if edge["source_port_key"] in source_outputs:
                inputs[edge["target_port_key"]] = source_outputs[edge["source_port_key"]]

        _emit(
            event_queue,
            NodeStartedEvent(
                run_id=run_id,
                workspace_id=workspace_id,
                node_id=node_id,
            ),
        )

        def _log(level: str, message: str) -> None:
            _emit(
                event_queue,
                LogEvent(
                    run_id=run_id,
                    workspace_id=workspace_id,
                    node_id=node_id,
                    level=level,
                    message=message,
                ),
            )

        ctx = ExecutionContext(
            run_id=run_id,
            node_id=node_id,
            workspace_id=workspace_id,
            inputs=inputs,
            properties=registry.normalize_properties(node["type_id"], dict(node.get("properties", {}))),
            emit_log=_log,
            trigger=trigger,
            should_stop=control.should_stop,
            register_cancel=control.register_cancel_callback,
        )

        try:
            spec = plugin.spec()
            if spec.is_async and hasattr(plugin, "async_execute") and callable(plugin.async_execute):
                result = asyncio.run(plugin.async_execute(ctx))
            else:
                result = plugin.execute(ctx)
            if control.should_stop():
                return "stopped"
            node_outputs[node_id] = dict(result.outputs)
            _emit(
                event_queue,
                NodeCompletedEvent(
                    run_id=run_id,
                    workspace_id=workspace_id,
                    node_id=node_id,
                    outputs=dict(result.outputs),
                ),
            )
        except InterruptedError:
            if control.should_stop():
                return "stopped"
            raise
        except Exception as exc:  # noqa: BLE001
            error_str = str(exc)
            tb_str = traceback.format_exc()
            node_outputs[node_id] = {"error": error_str, "traceback": tb_str}

            has_failure_edges = bool(failed_outgoing.get(node_id))
            if has_failure_edges:
                _emit(
                    event_queue,
                    LogEvent(
                        run_id=run_id,
                        workspace_id=workspace_id,
                        node_id=node_id,
                        level="warning",
                        message=f"Node failed but has failure handlers: {error_str}",
                    ),
                )
                return "failed_handled"

            _emit(
                event_queue,
                RunFailedEvent(
                    run_id=run_id,
                    workspace_id=workspace_id,
                    node_id=node_id,
                    error=error_str,
                    traceback=tb_str,
                ),
            )
            _emit_run_state(
                event_queue,
                run_id=run_id,
                workspace_id=workspace_id,
                state="error",
                transition="fail",
                reason="node_exception",
            )
            return "failed"
        finally:
            control.clear_cancel_callbacks()
        return "ok"

    while ready:
        control.poll_commands()
        if control.shutdown_requested or control.stop_requested:
            emit_stopped(control.stop_reason or "stop_requested")
            return
        control.wait_until_runnable()
        if control.shutdown_requested or control.stop_requested:
            emit_stopped(control.stop_reason or "stop_requested")
            return

        node_id = ready.popleft()
        if node_id in executed:
            continue
        status = execute_node(node_id)
        if status == "failed":
            return
        if status == "stopped":
            emit_stopped(control.stop_reason or "stop_requested")
            return

        executed.add(node_id)
        if status == "failed_handled":
            for downstream in failed_outgoing.get(node_id, []):
                exec_incoming_count[downstream] -= 1
                if exec_incoming_count[downstream] <= 0:
                    ready.append(downstream)
        else:
            for downstream in exec_outgoing.get(node_id, []):
                exec_incoming_count[downstream] -= 1
                if exec_incoming_count[downstream] <= 0:
                    ready.append(downstream)

    if len(executed) < len(nodes):
        # Run unvisited nodes to support data-only graphs.
        for node_id in sorted(nodes):
            control.poll_commands()
            if control.shutdown_requested or control.stop_requested:
                emit_stopped(control.stop_reason or "stop_requested")
                return
            control.wait_until_runnable()
            if control.shutdown_requested or control.stop_requested:
                emit_stopped(control.stop_reason or "stop_requested")
                return

            if node_id in executed:
                continue
            status = execute_node(node_id)
            if status == "failed":
                return
            if status == "stopped":
                emit_stopped(control.stop_reason or "stop_requested")
                return
            executed.add(node_id)

    _emit(
        event_queue,
        RunCompletedEvent(
            run_id=run_id,
            workspace_id=workspace_id,
        ),
    )
    _emit_run_state(
        event_queue,
        run_id=run_id,
        workspace_id=workspace_id,
        state="ready",
        transition="complete",
        reason="run_completed",
    )


def worker_main(command_queue: Queue, event_queue: Queue) -> None:
    while True:
        raw_command = command_queue.get()
        if not isinstance(raw_command, dict):
            _emit_protocol_error(event_queue, "Command payload must be a dictionary.")
            continue

        try:
            command = dict_to_command(dict(raw_command))
        except ValueError as exc:
            _emit_protocol_error(event_queue, f"Invalid command payload: {exc}")
            continue

        if isinstance(command, ShutdownCommand):
            break
        if isinstance(command, StartRunCommand):
            try:
                run_workflow(command, event_queue, command_queue=command_queue)
            except Exception as exc:  # noqa: BLE001
                _emit(
                    event_queue,
                    RunFailedEvent(
                        run_id=command.run_id,
                        workspace_id=command.workspace_id,
                        error=str(exc),
                        traceback=traceback.format_exc(),
                    ),
                )
                _emit_run_state(
                    event_queue,
                    run_id=command.run_id,
                    workspace_id=command.workspace_id,
                    state="error",
                    transition="fail",
                    reason="worker_exception",
                )
        elif isinstance(command, StopRunCommand):
            _emit_protocol_error(
                event_queue,
                "No active run to stop.",
                run_id=command.run_id,
                workspace_id=command.workspace_id,
                command=command.type,
            )
        elif isinstance(command, (PauseRunCommand, ResumeRunCommand)):
            _emit_protocol_error(
                event_queue,
                "No active run for command.",
                run_id=command.run_id,
                workspace_id="",
                command=command.type,
            )
        else:
            _emit_protocol_error(
                event_queue,
                "Unknown command type.",
                run_id=getattr(command, "run_id", ""),
                workspace_id=getattr(command, "workspace_id", ""),
                command=getattr(command, "type", ""),
            )
