"""Qt-free Corex runtime API and CLI entry point."""

from __future__ import annotations

import argparse
import copy
import json
import queue
import sys
import threading
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from ea_node_editor.execution.backends import (
    PROCESS_ISOLATED_BACKEND,
    TRUSTED_IN_PROCESS_BACKEND,
    ExecutionBackendPolicy,
)
from ea_node_editor.execution.client import ExecutionBackendClient
from ea_node_editor.execution.protocol import SettledPortResult
from ea_node_editor.execution.runtime_snapshot import (
    RuntimeSnapshot,
    build_runtime_snapshot,
    coerce_runtime_snapshot,
)
from ea_node_editor.graph.project_state import ProjectData
from ea_node_editor.graph.workspace_state import WorkspaceData
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.persistence.serializer import JsonProjectSerializer

ExecutionStatus = Literal["completed", "failed", "stopped", "timeout"]
ExecutionEvent = dict[str, Any]
ExecutionEventCallback = Callable[[ExecutionEvent], None]

TERMINAL_EVENT_TYPES = frozenset({"run_completed", "run_failed", "run_stopped"})
RUN_SCOPED_EVENT_TYPES = frozenset(
    {
        "run_started",
        "run_state",
        "run_completed",
        "run_failed",
        "run_stopped",
        "node_started",
        "node_settled",
        "trigger_capture_settled",
        "trigger_published",
        "log",
        "protocol_error",
    }
)


@dataclass(frozen=True, slots=True)
class ProjectLoadRequest:
    project_path: str | Path
    extra_plugin_dirs: tuple[Path, ...] = field(default_factory=tuple)

    def normalized_path(self) -> Path:
        return Path(self.project_path).expanduser()


@dataclass(frozen=True, slots=True)
class LoadedProject:
    project_path: Path
    project: ProjectData
    registry: NodeRegistry

    def select_workspace(
        self, selection: "WorkspaceSelection | str | None" = None
    ) -> WorkspaceData:
        return select_workspace(self, selection)


@dataclass(frozen=True, slots=True)
class WorkspaceSelection:
    workspace_id: str = ""


@dataclass(frozen=True, slots=True)
class CancellationRequest:
    run_id: str
    reason: str = "user"


@dataclass(frozen=True, slots=True)
class ExecutionRequest:
    project_path: str | Path = ""
    workspace_id: str = ""
    trigger: Mapping[str, Any] = field(default_factory=dict)
    runtime_snapshot: RuntimeSnapshot | Mapping[str, Any] | None = None
    execution_backend: ExecutionBackendPolicy | Mapping[str, Any] | str | None = None
    target_node_ids: tuple[str, ...] = field(default_factory=tuple)
    trigger_publications: Mapping[str, SettledPortResult] = field(default_factory=dict)
    trigger_captures: Mapping[str, SettledPortResult] = field(default_factory=dict)
    clicked_trigger_node_id: str = ""

    def trigger_without_runtime_snapshot(
        self,
    ) -> tuple[
        dict[str, Any],
        RuntimeSnapshot | Mapping[str, Any] | None,
        ExecutionBackendPolicy | Mapping[str, Any] | str | None,
    ]:
        trigger_source = dict(self.trigger)
        snapshot = self.runtime_snapshot
        if snapshot is None:
            snapshot = trigger_source.pop("runtime_snapshot", None)
        else:
            trigger_source.pop("runtime_snapshot", None)
        execution_backend = self.execution_backend
        if execution_backend is None:
            execution_backend = trigger_source.pop("execution_backend", None)
        else:
            trigger_source.pop("execution_backend", None)
        trigger = copy.deepcopy(trigger_source)
        return trigger, snapshot, execution_backend


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    run_id: str
    workspace_id: str
    status: ExecutionStatus
    events: tuple[ExecutionEvent, ...] = field(default_factory=tuple)
    terminal_event: ExecutionEvent = field(default_factory=dict)
    error: str = ""
    traceback: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "workspace_id": self.workspace_id,
            "status": self.status,
            "error": self.error,
            "traceback": self.traceback,
            "terminal_event": copy.deepcopy(self.terminal_event),
            "events": [copy.deepcopy(event) for event in self.events],
        }


class ExecutionEventStream:
    def __init__(self) -> None:
        self._events: queue.Queue[ExecutionEvent] = queue.Queue()
        self._callbacks: list[ExecutionEventCallback] = []
        self._lock = threading.RLock()

    def subscribe(self, callback: ExecutionEventCallback) -> Callable[[], None]:
        with self._lock:
            self._callbacks.append(callback)

        def _unsubscribe() -> None:
            with self._lock:
                try:
                    self._callbacks.remove(callback)
                except ValueError:
                    return

        return _unsubscribe

    def publish(self, event: Mapping[str, Any]) -> None:
        payload = copy.deepcopy(dict(event))
        self._events.put(payload)
        with self._lock:
            callbacks = tuple(self._callbacks)
        for callback in callbacks:
            try:
                callback(copy.deepcopy(payload))
            except Exception:
                continue

    def next_event(self, timeout: float | None = None) -> ExecutionEvent:
        return self._events.get(timeout=timeout)

    def iter_events(
        self,
        *,
        timeout: float | None = None,
        stop_after_terminal: bool = False,
    ) -> Iterator[ExecutionEvent]:
        while True:
            event = self.next_event(timeout=timeout)
            yield event
            if (
                stop_after_terminal
                and str(event.get("type", "")) in TERMINAL_EVENT_TYPES
            ):
                return


def load_project(
    request: ProjectLoadRequest | str | Path,
    *,
    registry: NodeRegistry | None = None,
    extra_plugin_dirs: Sequence[Path] | None = None,
) -> LoadedProject:
    if isinstance(request, ProjectLoadRequest):
        load_request = request
    else:
        load_request = ProjectLoadRequest(
            project_path=request,
            extra_plugin_dirs=tuple(extra_plugin_dirs or ()),
        )
    runtime_registry = registry or build_default_registry(
        extra_plugin_dirs=list(load_request.extra_plugin_dirs)
    )
    project_path = load_request.normalized_path()
    project = JsonProjectSerializer(runtime_registry).load(str(project_path))
    return LoadedProject(
        project_path=project_path,
        project=project,
        registry=runtime_registry,
    )


def select_workspace(
    project: LoadedProject | ProjectData,
    selection: WorkspaceSelection | str | None = None,
) -> WorkspaceData:
    project_data = project.project if isinstance(project, LoadedProject) else project
    if isinstance(selection, WorkspaceSelection):
        requested_workspace_id = str(selection.workspace_id or "").strip()
    else:
        requested_workspace_id = str(selection or "").strip()

    if not requested_workspace_id:
        return project_data.ensure_default_workspace()

    try:
        workspace = project_data.workspaces[requested_workspace_id]
    except KeyError as exc:
        raise KeyError(f"Workspace not found: {requested_workspace_id}") from exc
    project_data.active_workspace_id = requested_workspace_id
    return workspace


class CorexRuntime:
    def __init__(
        self,
        *,
        client: Any | None = None,
        registry: NodeRegistry | None = None,
    ) -> None:
        self._client = client or ExecutionBackendClient()
        self._owns_client = client is None
        self._registry = registry
        self._event_stream = ExecutionEventStream()
        self._client.subscribe(self._event_stream.publish)

    @property
    def events(self) -> ExecutionEventStream:
        return self._event_stream

    def subscribe(self, callback: ExecutionEventCallback) -> Callable[[], None]:
        return self._event_stream.subscribe(callback)

    def load_project(
        self,
        project_path: str | Path,
        *,
        extra_plugin_dirs: Sequence[Path] | None = None,
    ) -> LoadedProject:
        return load_project(
            project_path,
            registry=self._registry,
            extra_plugin_dirs=extra_plugin_dirs,
        )

    def prepare_request(self, request: ExecutionRequest) -> ExecutionRequest:
        trigger, raw_snapshot, execution_backend = (
            request.trigger_without_runtime_snapshot()
        )
        if raw_snapshot is not None and self._registry is None:
            raise ValueError(
                "raw runtime snapshots require an authoritative node registry"
            )
        catalog = self._registry.data_types if self._registry is not None else None
        runtime_snapshot = coerce_runtime_snapshot(raw_snapshot, catalog=catalog)
        workspace_id = str(request.workspace_id or "").strip()
        project_path = str(request.project_path or "").strip()

        if runtime_snapshot is None:
            loaded_project = self.load_project(project_path)
            self._registry = loaded_project.registry
            workspace = loaded_project.select_workspace(
                WorkspaceSelection(workspace_id)
            )
            runtime_snapshot = build_runtime_snapshot(
                loaded_project.project,
                workspace_id=workspace.workspace_id,
                registry=loaded_project.registry,
            )
            workspace_id = workspace.workspace_id
            project_path = str(loaded_project.project_path)
        else:
            if not workspace_id:
                workspace_id = str(runtime_snapshot.active_workspace_id or "").strip()
            runtime_snapshot.workspace(workspace_id)

        return ExecutionRequest(
            project_path=project_path,
            workspace_id=workspace_id,
            trigger=trigger,
            runtime_snapshot=runtime_snapshot,
            execution_backend=execution_backend,
            target_node_ids=tuple(request.target_node_ids),
            trigger_publications=dict(request.trigger_publications),
            trigger_captures=dict(request.trigger_captures),
            clicked_trigger_node_id=str(request.clicked_trigger_node_id),
        )

    def start(self, request: ExecutionRequest) -> str:
        return self._start_prepared(self.prepare_request(request))

    def start_run(
        self,
        project_path: str,
        workspace_id: str,
        trigger: dict[str, Any] | None = None,
        *,
        execution_backend: ExecutionBackendPolicy
        | Mapping[str, Any]
        | str
        | None = None,
        target_node_ids: tuple[str, ...] = (),
        trigger_publications: Mapping[str, SettledPortResult] | None = None,
        trigger_captures: Mapping[str, SettledPortResult] | None = None,
        clicked_trigger_node_id: str = "",
    ) -> str:
        return self.start(
            ExecutionRequest(
                project_path=project_path,
                workspace_id=workspace_id,
                trigger=dict(trigger or {}),
                execution_backend=execution_backend,
                target_node_ids=tuple(target_node_ids),
                trigger_publications=dict(trigger_publications or {}),
                trigger_captures=dict(trigger_captures or {}),
                clicked_trigger_node_id=clicked_trigger_node_id,
            )
        )

    def run(
        self,
        request: ExecutionRequest,
        *,
        timeout: float | None = None,
        on_event: ExecutionEventCallback | None = None,
    ) -> ExecutionResult:
        prepared = self.prepare_request(request)
        condition = threading.Condition()
        events: list[ExecutionEvent] = []
        terminal_event: ExecutionEvent | None = None
        run_id_holder = {"run_id": ""}

        def _capture(event: ExecutionEvent) -> None:
            nonlocal terminal_event
            event_type = str(event.get("type", ""))
            event_run_id = str(event.get("run_id", ""))
            active_run_id = run_id_holder["run_id"]
            if (
                active_run_id
                and event_type in RUN_SCOPED_EVENT_TYPES
                and event_run_id
                and event_run_id != active_run_id
            ):
                return
            payload = copy.deepcopy(dict(event))
            with condition:
                events.append(payload)
                if (
                    active_run_id
                    and event_type in TERMINAL_EVENT_TYPES
                    and event_run_id == active_run_id
                ):
                    terminal_event = payload
                condition.notify_all()
            if on_event is not None:
                on_event(copy.deepcopy(payload))

        unsubscribe = self.subscribe(_capture)
        try:
            run_id = self._start_prepared(prepared)
            run_id_holder["run_id"] = run_id
            if not run_id:
                terminal_event = self._start_failure_event(
                    events, prepared.workspace_id
                )
                return self._result_from_terminal(
                    run_id="",
                    workspace_id=prepared.workspace_id,
                    terminal_event=terminal_event,
                    events=events,
                )

            with condition:
                terminal_event = self._terminal_event_for_run(events, run_id)
            deadline = time.monotonic() + timeout if timeout is not None else None
            with condition:
                while terminal_event is None:
                    if deadline is None:
                        condition.wait(timeout=0.2)
                        continue
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    condition.wait(timeout=min(remaining, 0.2))

            if terminal_event is None:
                self.cancel(CancellationRequest(run_id=run_id, reason="timeout"))
                terminal_event = {
                    "type": "run_timeout",
                    "run_id": run_id,
                    "workspace_id": prepared.workspace_id,
                    "reason": "timeout",
                }
                with condition:
                    events.append(copy.deepcopy(terminal_event))

            return self._result_from_terminal(
                run_id=run_id,
                workspace_id=prepared.workspace_id,
                terminal_event=terminal_event,
                events=events,
            )
        finally:
            unsubscribe()

    def cancel(self, request: CancellationRequest) -> None:
        if request.run_id:
            self.stop_run(request.run_id)

    def pause_run(self, run_id: str) -> None:
        self._client.pause_run(run_id)

    def resume_run(self, run_id: str) -> None:
        self._client.resume_run(run_id)

    def stop_run(self, run_id: str) -> None:
        self._client.stop_run(run_id)

    def open_viewer_session(self, *args: Any, **kwargs: Any) -> str:
        return self._client.open_viewer_session(*args, **kwargs)

    def update_viewer_session(self, *args: Any, **kwargs: Any) -> str:
        return self._client.update_viewer_session(*args, **kwargs)

    def close_viewer_session(self, *args: Any, **kwargs: Any) -> str:
        return self._client.close_viewer_session(*args, **kwargs)

    def materialize_viewer_data(self, *args: Any, **kwargs: Any) -> str:
        return self._client.materialize_viewer_data(*args, **kwargs)

    def shutdown(self) -> None:
        if self._owns_client:
            self._client.shutdown()

    def _start_prepared(self, request: ExecutionRequest) -> str:
        if self._registry is None:
            raise ValueError("execution requires an authoritative node registry")
        trigger = copy.deepcopy(dict(request.trigger))
        trigger["runtime_snapshot"] = request.runtime_snapshot
        return self._client.start_run(
            project_path=str(request.project_path or ""),
            workspace_id=request.workspace_id,
            trigger=trigger,
            execution_backend=request.execution_backend,
            target_node_ids=request.target_node_ids,
            trigger_publications=request.trigger_publications,
            trigger_captures=request.trigger_captures,
            clicked_trigger_node_id=request.clicked_trigger_node_id,
            data_types=self._registry.data_types,
        )

    @staticmethod
    def _start_failure_event(
        events: list[ExecutionEvent], workspace_id: str
    ) -> ExecutionEvent:
        for event in reversed(events):
            if str(event.get("type", "")) == "protocol_error":
                return copy.deepcopy(event)
        return {
            "type": "run_failed",
            "run_id": "",
            "workspace_id": workspace_id,
            "error": "Execution client did not start a run.",
            "traceback": "",
        }

    @staticmethod
    def _terminal_event_for_run(
        events: list[ExecutionEvent], run_id: str
    ) -> ExecutionEvent | None:
        for event in events:
            if (
                str(event.get("type", "")) in TERMINAL_EVENT_TYPES
                and str(event.get("run_id", "")) == run_id
            ):
                return copy.deepcopy(event)
        return None

    @staticmethod
    def _result_from_terminal(
        *,
        run_id: str,
        workspace_id: str,
        terminal_event: ExecutionEvent,
        events: list[ExecutionEvent],
    ) -> ExecutionResult:
        event_type = str(terminal_event.get("type", ""))
        if event_type == "run_completed":
            status: ExecutionStatus = "completed"
        elif event_type == "run_stopped":
            status = "stopped"
        elif event_type == "run_timeout":
            status = "timeout"
        else:
            status = "failed"
        return ExecutionResult(
            run_id=str(terminal_event.get("run_id") or run_id),
            workspace_id=str(terminal_event.get("workspace_id") or workspace_id),
            status=status,
            events=tuple(copy.deepcopy(event) for event in events),
            terminal_event=copy.deepcopy(terminal_event),
            error=str(terminal_event.get("error", "")),
            traceback=str(terminal_event.get("traceback", "")),
        )


def _format_text_event(event: Mapping[str, Any]) -> str:
    parts = [
        f"type={event.get('type', '')}",
        f"run_id={event.get('run_id', '')}",
        f"workspace_id={event.get('workspace_id', '')}",
    ]
    node_id = str(event.get("node_id", ""))
    if node_id:
        parts.append(f"node_id={node_id}")
    message = str(event.get("message", "") or event.get("error", ""))
    if message:
        parts.append(f"message={message}")
    return "event " + " ".join(parts)


def _emit_cli_record(record: Mapping[str, Any], *, output_format: str) -> None:
    if output_format == "json":
        print(
            json.dumps(copy.deepcopy(dict(record)), sort_keys=True, ensure_ascii=True)
        )
        return
    record_type = str(record.get("record", ""))
    if record_type == "event":
        print(_format_text_event(dict(record.get("event", {}))))
    elif record_type == "result":
        result = dict(record.get("result", {}))
        print(
            "result "
            f"status={result.get('status', '')} "
            f"run_id={result.get('run_id', '')} "
            f"workspace_id={result.get('workspace_id', '')}"
        )
    else:
        print("error " + str(record.get("error", "")))


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="corex-runtime")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="Run a Corex workspace without Qt.")
    run_parser.add_argument("project", help="Path to the .cxproj project.")
    run_parser.add_argument(
        "--workspace",
        "-w",
        default="",
        help="Workspace id to run. Defaults to the project's active workspace.",
    )
    run_parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="Output format for streamed events and the final result.",
    )
    run_parser.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Maximum seconds to wait before requesting cancellation.",
    )
    run_parser.add_argument(
        "--execution-backend",
        choices=(PROCESS_ISOLATED_BACKEND, TRUSTED_IN_PROCESS_BACKEND),
        default=PROCESS_ISOLATED_BACKEND,
        help="Execution backend. Process isolation remains the default.",
    )
    run_parser.add_argument(
        "--trust-in-process",
        action="store_true",
        help="Required opt-in when --execution-backend=trusted_in_process.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    if args.command != "run":
        return 2

    runtime = CorexRuntime()
    try:
        result = runtime.run(
            ExecutionRequest(
                project_path=args.project,
                workspace_id=args.workspace,
                trigger={"kind": "headless_cli"},
                execution_backend=ExecutionBackendPolicy(
                    requested_backend=args.execution_backend,
                    allow_trusted_in_process=bool(args.trust_in_process),
                    reason="headless_cli",
                ),
            ),
            timeout=args.timeout,
            on_event=lambda event: _emit_cli_record(
                {"record": "event", "event": event},
                output_format=args.format,
            ),
        )
        _emit_cli_record(
            {"record": "result", "result": result.to_dict()},
            output_format=args.format,
        )
        return 0 if result.status == "completed" else 1
    except Exception as exc:  # noqa: BLE001
        _emit_cli_record(
            {"record": "error", "error": str(exc)},
            output_format=getattr(args, "format", "json"),
        )
        return 2
    finally:
        runtime.shutdown()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


__all__ = [
    "CancellationRequest",
    "CorexRuntime",
    "ExecutionEvent",
    "ExecutionEventCallback",
    "ExecutionEventStream",
    "ExecutionBackendPolicy",
    "ExecutionRequest",
    "ExecutionResult",
    "ExecutionStatus",
    "LoadedProject",
    "ProjectLoadRequest",
    "WorkspaceSelection",
    "load_project",
    "main",
    "select_workspace",
]
