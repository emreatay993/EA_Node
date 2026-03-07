"""Typed command/event protocol with queue-boundary dict adapters."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, TypeAlias

EngineState = Literal["ready", "running", "paused", "error"]
RunTransition = Literal["start", "pause", "resume", "stop", "complete", "fail"]
EventType = Literal[
    "run_started",
    "run_state",
    "run_completed",
    "run_failed",
    "run_stopped",
    "node_started",
    "node_completed",
    "log",
    "protocol_error",
]


@dataclass(frozen=True)
class StartRunCommand:
    type: Literal["start_run"] = "start_run"
    run_id: str = ""
    project_path: str = ""
    workspace_id: str = ""
    trigger: dict[str, Any] = field(default_factory=dict)
    project_doc: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StopRunCommand:
    type: Literal["stop_run"] = "stop_run"
    run_id: str = ""
    workspace_id: str = ""


@dataclass(frozen=True)
class PauseRunCommand:
    type: Literal["pause_run"] = "pause_run"
    run_id: str = ""


@dataclass(frozen=True)
class ResumeRunCommand:
    type: Literal["resume_run"] = "resume_run"
    run_id: str = ""


@dataclass(frozen=True)
class ShutdownCommand:
    type: Literal["shutdown"] = "shutdown"


WorkerCommand: TypeAlias = (
    StartRunCommand
    | StopRunCommand
    | PauseRunCommand
    | ResumeRunCommand
    | ShutdownCommand
)


@dataclass(frozen=True)
class RunStartedEvent:
    type: Literal["run_started"] = "run_started"
    run_id: str = ""
    workspace_id: str = ""


@dataclass(frozen=True)
class RunStateEvent:
    type: Literal["run_state"] = "run_state"
    run_id: str = ""
    workspace_id: str = ""
    state: EngineState = "ready"
    transition: RunTransition | str = ""
    reason: str = ""


@dataclass(frozen=True)
class RunCompletedEvent:
    type: Literal["run_completed"] = "run_completed"
    run_id: str = ""
    workspace_id: str = ""
    state: Literal["ready"] = "ready"


@dataclass(frozen=True)
class RunFailedEvent:
    type: Literal["run_failed"] = "run_failed"
    run_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    error: str = ""
    traceback: str = ""
    state: Literal["error"] = "error"
    fatal: bool = False


@dataclass(frozen=True)
class RunStoppedEvent:
    type: Literal["run_stopped"] = "run_stopped"
    run_id: str = ""
    workspace_id: str = ""
    reason: str = ""
    state: Literal["ready"] = "ready"


@dataclass(frozen=True)
class NodeStartedEvent:
    type: Literal["node_started"] = "node_started"
    run_id: str = ""
    workspace_id: str = ""
    node_id: str = ""


@dataclass(frozen=True)
class NodeCompletedEvent:
    type: Literal["node_completed"] = "node_completed"
    run_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    outputs: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LogEvent:
    type: Literal["log"] = "log"
    run_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    level: str = "info"
    message: str = ""


@dataclass(frozen=True)
class ProtocolErrorEvent:
    type: Literal["protocol_error"] = "protocol_error"
    run_id: str = ""
    workspace_id: str = ""
    command: str = ""
    error: str = ""


WorkerEvent: TypeAlias = (
    RunStartedEvent
    | RunStateEvent
    | RunCompletedEvent
    | RunFailedEvent
    | RunStoppedEvent
    | NodeStartedEvent
    | NodeCompletedEvent
    | LogEvent
    | ProtocolErrorEvent
)


def command_to_dict(command: WorkerCommand) -> dict[str, Any]:
    return asdict(command)


def event_to_dict(event: WorkerEvent) -> dict[str, Any]:
    return asdict(event)


def dict_to_event_type(payload: dict[str, Any]) -> str:
    return str(payload.get("type", ""))


def dict_to_command(payload: dict[str, Any]) -> WorkerCommand:
    command_type = str(payload.get("type", ""))
    if command_type == "start_run":
        project_doc = payload.get("project_doc")
        return StartRunCommand(
            run_id=str(payload.get("run_id", "")),
            project_path=str(payload.get("project_path", "")),
            workspace_id=str(payload.get("workspace_id", "")),
            trigger=dict(payload.get("trigger", {})) if isinstance(payload.get("trigger"), dict) else {},
            project_doc=dict(project_doc) if isinstance(project_doc, dict) else {},
        )
    if command_type == "stop_run":
        return StopRunCommand(
            run_id=str(payload.get("run_id", "")),
            workspace_id=str(payload.get("workspace_id", "")),
        )
    if command_type == "pause_run":
        return PauseRunCommand(run_id=str(payload.get("run_id", "")))
    if command_type == "resume_run":
        return ResumeRunCommand(run_id=str(payload.get("run_id", "")))
    if command_type == "shutdown":
        return ShutdownCommand()
    raise ValueError(f"Unknown command type: {command_type!r}")


def dict_to_event(payload: dict[str, Any]) -> WorkerEvent:
    event_type = str(payload.get("type", ""))
    if event_type == "run_started":
        return RunStartedEvent(
            run_id=str(payload.get("run_id", "")),
            workspace_id=str(payload.get("workspace_id", "")),
        )
    if event_type == "run_state":
        return RunStateEvent(
            run_id=str(payload.get("run_id", "")),
            workspace_id=str(payload.get("workspace_id", "")),
            state=str(payload.get("state", "ready")),  # type: ignore[arg-type]
            transition=str(payload.get("transition", "")),
            reason=str(payload.get("reason", "")),
        )
    if event_type == "run_completed":
        return RunCompletedEvent(
            run_id=str(payload.get("run_id", "")),
            workspace_id=str(payload.get("workspace_id", "")),
        )
    if event_type == "run_failed":
        return RunFailedEvent(
            run_id=str(payload.get("run_id", "")),
            workspace_id=str(payload.get("workspace_id", "")),
            node_id=str(payload.get("node_id", "")),
            error=str(payload.get("error", "")),
            traceback=str(payload.get("traceback", "")),
            fatal=bool(payload.get("fatal", False)),
        )
    if event_type == "run_stopped":
        return RunStoppedEvent(
            run_id=str(payload.get("run_id", "")),
            workspace_id=str(payload.get("workspace_id", "")),
            reason=str(payload.get("reason", "")),
        )
    if event_type == "node_started":
        return NodeStartedEvent(
            run_id=str(payload.get("run_id", "")),
            workspace_id=str(payload.get("workspace_id", "")),
            node_id=str(payload.get("node_id", "")),
        )
    if event_type == "node_completed":
        return NodeCompletedEvent(
            run_id=str(payload.get("run_id", "")),
            workspace_id=str(payload.get("workspace_id", "")),
            node_id=str(payload.get("node_id", "")),
            outputs=dict(payload.get("outputs", {})) if isinstance(payload.get("outputs"), dict) else {},
        )
    if event_type == "log":
        return LogEvent(
            run_id=str(payload.get("run_id", "")),
            workspace_id=str(payload.get("workspace_id", "")),
            node_id=str(payload.get("node_id", "")),
            level=str(payload.get("level", "info")),
            message=str(payload.get("message", "")),
        )
    if event_type == "protocol_error":
        return ProtocolErrorEvent(
            run_id=str(payload.get("run_id", "")),
            workspace_id=str(payload.get("workspace_id", "")),
            command=str(payload.get("command", "")),
            error=str(payload.get("error", "")),
        )
    raise ValueError(f"Unknown event type: {event_type!r}")
