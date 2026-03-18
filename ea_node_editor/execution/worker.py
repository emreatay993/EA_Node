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

_CONTROL_PORT_KINDS = frozenset({"exec", "completed", "failed"})


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


class _RunEventPublisher:
    def __init__(self, event_queue: Queue, *, run_id: str, workspace_id: str) -> None:
        self._event_queue = event_queue
        self.run_id = run_id
        self.workspace_id = workspace_id

    def emit(self, event: WorkerEvent) -> None:
        _emit(self._event_queue, event)

    def emit_run_started(self) -> None:
        self.emit(RunStartedEvent(run_id=self.run_id, workspace_id=self.workspace_id))
        self.emit_run_state(state="running", transition="start", reason="run_started")

    def emit_run_state(self, *, state: str, transition: str, reason: str) -> None:
        _emit_run_state(
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
        self.emit(
            NodeStartedEvent(
                run_id=self.run_id,
                workspace_id=self.workspace_id,
                node_id=node_id,
            )
        )

    def emit_node_completed(self, node_id: str, outputs: dict[str, Any]) -> None:
        self.emit(
            NodeCompletedEvent(
                run_id=self.run_id,
                workspace_id=self.workspace_id,
                node_id=node_id,
                outputs=dict(outputs),
            )
        )

    def emit_log(self, level: str, message: str, *, node_id: str = "") -> None:
        self.emit(
            LogEvent(
                run_id=self.run_id,
                workspace_id=self.workspace_id,
                node_id=node_id,
                level=level,
                message=message,
            )
        )


def _is_dependency_spec(spec: Any) -> bool:
    return all(getattr(port, "kind", "") == "data" for port in getattr(spec, "ports", ()))


def _is_exec_entry_spec(spec: Any) -> bool:
    has_control_output = any(
        getattr(port, "direction", "") == "out" and getattr(port, "kind", "") in _CONTROL_PORT_KINDS
        for port in getattr(spec, "ports", ())
    )
    has_control_input = any(
        getattr(port, "direction", "") == "in" and getattr(port, "kind", "") in _CONTROL_PORT_KINDS
        for port in getattr(spec, "ports", ())
    )
    return has_control_output and not has_control_input


class _RuntimeGraph:
    def __init__(self, workspace: dict[str, Any], registry: Any) -> None:
        self.nodes = {node["node_id"]: node for node in workspace.get("nodes", [])}
        self.node_specs = {
            node_id: registry.get_spec(str(node.get("type_id", "")))
            for node_id, node in self.nodes.items()
        }
        self._port_kinds = {
            node_id: {port.key: port.kind for port in spec.ports}
            for node_id, spec in self.node_specs.items()
        }
        self.exec_outgoing: dict[str, list[str]] = defaultdict(list)
        self.failed_outgoing: dict[str, list[str]] = defaultdict(list)
        self.data_incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._dependency_outgoing: dict[str, set[str]] = defaultdict(set)
        self.exec_incoming_remaining: dict[str, int] = {node_id: 0 for node_id in self.nodes}
        self.dependency_nodes: set[str] = {
            node_id for node_id, spec in self.node_specs.items() if _is_dependency_spec(spec)
        }
        self.start_nodes = [
            node_id for node_id, node in self.nodes.items() if str(node.get("type_id", "")) == "core.start"
        ]

        for edge in workspace.get("edges", []):
            source_node_id = str(edge["source_node_id"])
            target_node_id = str(edge["target_node_id"])
            source_kind = self._port_kinds.get(source_node_id, {}).get(str(edge["source_port_key"]), "data")
            if source_kind == "failed":
                self.failed_outgoing[source_node_id].append(target_node_id)
                self.exec_incoming_remaining[target_node_id] += 1
            elif source_kind in {"exec", "completed"}:
                self.exec_outgoing[source_node_id].append(target_node_id)
                self.exec_incoming_remaining[target_node_id] += 1
            elif source_kind == "flow":
                continue
            else:
                self.data_incoming[target_node_id].append(edge)
                if source_node_id in self.dependency_nodes and target_node_id in self.dependency_nodes:
                    self._dependency_outgoing[source_node_id].add(target_node_id)

    def initial_ready(self) -> deque[str]:
        if self.start_nodes:
            return deque(self.start_nodes)
        return deque(
            sorted(
                node_id
                for node_id, spec in self.node_specs.items()
                if self.exec_incoming_remaining.get(node_id, 0) == 0 and _is_exec_entry_spec(spec)
            )
        )

    def dependency_sources_for(self, node_id: str) -> list[str]:
        sources: list[str] = []
        seen: set[str] = set()
        for edge in self.data_incoming.get(node_id, []):
            source_node_id = str(edge["source_node_id"])
            if source_node_id not in self.dependency_nodes or source_node_id in seen:
                continue
            seen.add(source_node_id)
            sources.append(source_node_id)
        return sources

    def input_values_for(self, node_id: str, node_outputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
        inputs: dict[str, Any] = {}
        for edge in self.data_incoming.get(node_id, []):
            source_outputs = node_outputs.get(str(edge["source_node_id"]), {})
            source_port_key = str(edge["source_port_key"])
            if source_port_key in source_outputs:
                inputs[str(edge["target_port_key"])] = source_outputs[source_port_key]
        return inputs

    def has_failure_downstream(self, node_id: str) -> bool:
        return bool(self.failed_outgoing.get(node_id))

    def release_downstream(self, node_id: str, status: str) -> list[str]:
        downstream_nodes = (
            self.failed_outgoing.get(node_id, [])
            if status == "failed_handled"
            else self.exec_outgoing.get(node_id, [])
        )
        ready_nodes: list[str] = []
        for downstream in downstream_nodes:
            self.exec_incoming_remaining[downstream] -= 1
            if self.exec_incoming_remaining[downstream] <= 0:
                ready_nodes.append(downstream)
        return ready_nodes

    def has_only_dependency_nodes(self) -> bool:
        return all(node_id in self.dependency_nodes for node_id in self.nodes)

    def dependency_sinks(self) -> list[str]:
        sinks = sorted(
            node_id for node_id in self.dependency_nodes if not self._dependency_outgoing.get(node_id)
        )
        if sinks:
            return sinks
        return sorted(self.dependency_nodes)


class _NodeExecutor:
    def __init__(
        self,
        runtime_graph: _RuntimeGraph,
        registry: Any,
        control: _RunControl,
        publisher: _RunEventPublisher,
        *,
        trigger: dict[str, Any],
    ) -> None:
        self._graph = runtime_graph
        self._registry = registry
        self._control = control
        self._publisher = publisher
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
        for source_node_id in self._graph.dependency_sources_for(node_id):
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
        node = self._graph.nodes[node_id]
        node_type_id = str(node["type_id"])
        plugin = self._registry.create(node_type_id)
        inputs = self._graph.input_values_for(node_id, self.node_outputs)

        self._publisher.emit_node_started(node_id)

        def _log(level: str, message: str) -> None:
            self._publisher.emit_log(level, message, node_id=node_id)

        ctx = ExecutionContext(
            run_id=self._publisher.run_id,
            node_id=node_id,
            workspace_id=self._publisher.workspace_id,
            inputs=inputs,
            properties=self._registry.normalize_properties(node_type_id, dict(node.get("properties", {}))),
            emit_log=_log,
            trigger=self._trigger,
            should_stop=self._control.should_stop,
            register_cancel=self._control.register_cancel_callback,
        )

        try:
            spec = self._graph.node_specs[node_id]
            if spec.is_async and hasattr(plugin, "async_execute") and callable(plugin.async_execute):
                result = asyncio.run(plugin.async_execute(ctx))
            else:
                result = plugin.execute(ctx)
            if self._control.should_stop():
                return "stopped"

            outputs = dict(result.outputs)
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

            if self._graph.has_failure_downstream(node_id):
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


def _coerce_start_run_command(command: StartRunCommand | dict[str, Any]) -> StartRunCommand:
    if not isinstance(command, dict):
        return command
    if "type" in command:
        typed_command = dict_to_command(command)
        if not isinstance(typed_command, StartRunCommand):
            raise ValueError("run_workflow requires a start_run command payload.")
        return typed_command

    project_doc = command.get("project_doc")
    return StartRunCommand(
        run_id=str(command.get("run_id", "")),
        project_path=str(command.get("project_path", "")),
        workspace_id=str(command.get("workspace_id", "")),
        trigger=dict(command.get("trigger", {})) if isinstance(command.get("trigger"), dict) else {},
        project_doc=dict(project_doc) if isinstance(project_doc, dict) else {},
    )


class _WorkflowRunner:
    def __init__(
        self,
        command: StartRunCommand,
        event_queue: Queue,
        command_queue: Queue | None = None,
    ) -> None:
        self._control = _RunControl(
            command_queue,
            event_queue,
            run_id=command.run_id,
            workspace_id=command.workspace_id,
        )
        self._publisher = _RunEventPublisher(
            event_queue,
            run_id=command.run_id,
            workspace_id=command.workspace_id,
        )
        self._registry = build_default_registry()
        serializer = JsonProjectSerializer(self._registry)
        project_doc = _load_project_doc(command, serializer)
        workspace = compile_workspace_document(
            _workspace_doc_from_project(project_doc, command.workspace_id),
            registry=self._registry,
        )
        self._graph = _RuntimeGraph(workspace, self._registry)
        self._executor = _NodeExecutor(
            self._graph,
            self._registry,
            self._control,
            self._publisher,
            trigger=dict(command.trigger),
        )

    def run(self) -> None:
        self._publisher.emit_run_started()
        self._publisher.emit_log("info", "Workflow run started.")

        ready = self._graph.initial_ready()
        while ready:
            node_id = ready.popleft()
            if node_id in self._executor.executed:
                continue
            status = self._executor.run_node(node_id)
            if self._handle_terminal_status(status):
                return
            ready.extend(self._graph.release_downstream(node_id, status))

        if not self._executor.executed and self._graph.has_only_dependency_nodes():
            for node_id in self._graph.dependency_sinks():
                if node_id in self._executor.executed:
                    continue
                status = self._executor.run_node(node_id)
                if self._handle_terminal_status(status):
                    return

        self._publisher.emit_run_completed()

    def _handle_terminal_status(self, status: str) -> bool:
        if status == "failed":
            return True
        if status == "stopped":
            self._publisher.emit_run_stopped(self._control.stop_reason or "stop_requested")
            return True
        return False


def run_workflow(
    command: StartRunCommand | dict[str, Any],
    event_queue: Queue,
    command_queue: Queue | None = None,
) -> None:
    typed_command = _coerce_start_run_command(command)
    _WorkflowRunner(
        typed_command,
        event_queue,
        command_queue=command_queue,
    ).run()


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
