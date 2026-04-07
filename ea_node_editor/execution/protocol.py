"""Typed command/event protocol with queue-boundary dict adapters."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from typing import Any, Literal, TypeAlias

from ea_node_editor.execution.runtime_value_codec import (
    deserialize_runtime_value,
    serialize_runtime_value,
)
from ea_node_editor.execution.runtime_snapshot import (
    RuntimeSnapshot,
    coerce_runtime_snapshot,
)

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
    "node_failed_handled",
    "log",
    "protocol_error",
    "viewer_session_opened",
    "viewer_session_updated",
    "viewer_session_closed",
    "viewer_data_materialized",
    "viewer_session_failed",
]

VIEWER_COMMAND_TYPES = frozenset(
    {
        "open_viewer_session",
        "update_viewer_session",
        "close_viewer_session",
        "materialize_viewer_data",
    }
)
VIEWER_RESPONSE_EVENT_TYPES = frozenset(
    {
        "viewer_session_opened",
        "viewer_session_updated",
        "viewer_session_closed",
        "viewer_data_materialized",
        "viewer_session_failed",
    }
)
_RUNTIME_VALUE_MARKER_KEY = "__ea_runtime_value__"
_VIEWER_RUNTIME_MARKERS = frozenset({"artifact_ref", "handle_ref"})


@dataclass(frozen=True)
class StartRunCommand:
    type: Literal["start_run"] = "start_run"
    run_id: str = ""
    project_path: str = ""
    workspace_id: str = ""
    trigger: dict[str, Any] = field(default_factory=dict)
    runtime_snapshot: RuntimeSnapshot | None = None


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


@dataclass(frozen=True)
class OpenViewerSessionCommand:
    type: Literal["open_viewer_session"] = "open_viewer_session"
    request_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    session_id: str = ""
    backend_id: str = ""
    data_refs: dict[str, Any] = field(default_factory=dict)
    transport: dict[str, Any] = field(default_factory=dict)
    transport_revision: int = 0
    live_open_status: str = ""
    live_open_blocker: dict[str, Any] = field(default_factory=dict)
    camera_state: dict[str, Any] = field(default_factory=dict)
    playback_state: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class UpdateViewerSessionCommand:
    type: Literal["update_viewer_session"] = "update_viewer_session"
    request_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    session_id: str = ""
    backend_id: str = ""
    data_refs: dict[str, Any] = field(default_factory=dict)
    transport: dict[str, Any] = field(default_factory=dict)
    transport_revision: int = 0
    live_open_status: str = ""
    live_open_blocker: dict[str, Any] = field(default_factory=dict)
    camera_state: dict[str, Any] = field(default_factory=dict)
    playback_state: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CloseViewerSessionCommand:
    type: Literal["close_viewer_session"] = "close_viewer_session"
    request_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    session_id: str = ""
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MaterializeViewerDataCommand:
    type: Literal["materialize_viewer_data"] = "materialize_viewer_data"
    request_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    session_id: str = ""
    backend_id: str = ""
    options: dict[str, Any] = field(default_factory=dict)


WorkerCommand: TypeAlias = (
    StartRunCommand
    | StopRunCommand
    | PauseRunCommand
    | ResumeRunCommand
    | ShutdownCommand
    | OpenViewerSessionCommand
    | UpdateViewerSessionCommand
    | CloseViewerSessionCommand
    | MaterializeViewerDataCommand
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
class NodeFailedHandledEvent:
    type: Literal["node_failed_handled"] = "node_failed_handled"
    run_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    error: str = ""


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
    request_id: str = ""
    command: str = ""
    error: str = ""


@dataclass(frozen=True)
class ViewerSessionOpenedEvent:
    type: Literal["viewer_session_opened"] = "viewer_session_opened"
    request_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    session_id: str = ""
    backend_id: str = ""
    data_refs: dict[str, Any] = field(default_factory=dict)
    transport: dict[str, Any] = field(default_factory=dict)
    transport_revision: int = 0
    live_open_status: str = ""
    live_open_blocker: dict[str, Any] = field(default_factory=dict)
    camera_state: dict[str, Any] = field(default_factory=dict)
    playback_state: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ViewerSessionUpdatedEvent:
    type: Literal["viewer_session_updated"] = "viewer_session_updated"
    request_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    session_id: str = ""
    backend_id: str = ""
    data_refs: dict[str, Any] = field(default_factory=dict)
    transport: dict[str, Any] = field(default_factory=dict)
    transport_revision: int = 0
    live_open_status: str = ""
    live_open_blocker: dict[str, Any] = field(default_factory=dict)
    camera_state: dict[str, Any] = field(default_factory=dict)
    playback_state: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ViewerSessionClosedEvent:
    type: Literal["viewer_session_closed"] = "viewer_session_closed"
    request_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    session_id: str = ""
    backend_id: str = ""
    transport: dict[str, Any] = field(default_factory=dict)
    transport_revision: int = 0
    live_open_status: str = ""
    live_open_blocker: dict[str, Any] = field(default_factory=dict)
    camera_state: dict[str, Any] = field(default_factory=dict)
    playback_state: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ViewerDataMaterializedEvent:
    type: Literal["viewer_data_materialized"] = "viewer_data_materialized"
    request_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    session_id: str = ""
    backend_id: str = ""
    data_refs: dict[str, Any] = field(default_factory=dict)
    transport: dict[str, Any] = field(default_factory=dict)
    transport_revision: int = 0
    live_open_status: str = ""
    live_open_blocker: dict[str, Any] = field(default_factory=dict)
    camera_state: dict[str, Any] = field(default_factory=dict)
    playback_state: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ViewerSessionFailedEvent:
    type: Literal["viewer_session_failed"] = "viewer_session_failed"
    request_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    session_id: str = ""
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
    | NodeFailedHandledEvent
    | LogEvent
    | ProtocolErrorEvent
    | ViewerSessionOpenedEvent
    | ViewerSessionUpdatedEvent
    | ViewerSessionClosedEvent
    | ViewerDataMaterializedEvent
    | ViewerSessionFailedEvent
)


def _serialize_dataclass_payload(value: Any) -> dict[str, Any]:
    return {
        field_info.name: serialize_runtime_value(getattr(value, field_info.name))
        for field_info in fields(value)
    }


def _serialize_viewer_value(value: Any, *, field_name: str) -> Any:
    serialized = serialize_runtime_value(value)
    if serialized is None or isinstance(serialized, (str, int, float, bool)):
        return serialized
    if isinstance(serialized, list):
        return [_serialize_viewer_value(item, field_name=field_name) for item in serialized]
    if isinstance(serialized, tuple):
        return [_serialize_viewer_value(item, field_name=field_name) for item in serialized]
    if isinstance(serialized, Mapping):
        marker = serialized.get(_RUNTIME_VALUE_MARKER_KEY)
        if marker in _VIEWER_RUNTIME_MARKERS:
            return dict(serialized)
        return {
            str(key): _serialize_viewer_value(item, field_name=field_name)
            for key, item in serialized.items()
        }
    raise TypeError(
        f"{field_name} must be JSON-safe and may only contain scalar values, lists, "
        "dictionaries, runtime handle refs, or runtime artifact refs."
    )


def _serialize_viewer_mapping(value: Any, *, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a dictionary payload.")
    return {
        str(key): _serialize_viewer_value(item, field_name=field_name)
        for key, item in value.items()
    }


def _deserialize_viewer_mapping(value: Any) -> dict[str, Any]:
    payload = deserialize_runtime_value(value)
    return dict(payload) if isinstance(payload, Mapping) else {}


def _deserialize_viewer_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def command_to_dict(command: WorkerCommand) -> dict[str, Any]:
    if isinstance(command, (OpenViewerSessionCommand, UpdateViewerSessionCommand)):
        return {
            "type": command.type,
            "request_id": command.request_id,
            "workspace_id": command.workspace_id,
            "node_id": command.node_id,
            "session_id": command.session_id,
            "backend_id": command.backend_id,
            "data_refs": _serialize_viewer_mapping(command.data_refs, field_name="data_refs"),
            "transport": _serialize_viewer_mapping(command.transport, field_name="transport"),
            "transport_revision": int(command.transport_revision),
            "live_open_status": str(command.live_open_status),
            "live_open_blocker": _serialize_viewer_mapping(command.live_open_blocker, field_name="live_open_blocker"),
            "camera_state": _serialize_viewer_mapping(command.camera_state, field_name="camera_state"),
            "playback_state": _serialize_viewer_mapping(command.playback_state, field_name="playback_state"),
            "summary": _serialize_viewer_mapping(command.summary, field_name="summary"),
            "options": _serialize_viewer_mapping(command.options, field_name="options"),
        }
    if isinstance(command, CloseViewerSessionCommand):
        return {
            "type": command.type,
            "request_id": command.request_id,
            "workspace_id": command.workspace_id,
            "node_id": command.node_id,
            "session_id": command.session_id,
            "options": _serialize_viewer_mapping(command.options, field_name="options"),
        }
    if isinstance(command, MaterializeViewerDataCommand):
        return {
            "type": command.type,
            "request_id": command.request_id,
            "workspace_id": command.workspace_id,
            "node_id": command.node_id,
            "session_id": command.session_id,
            "backend_id": command.backend_id,
            "options": _serialize_viewer_mapping(command.options, field_name="options"),
        }
    return _serialize_dataclass_payload(command)


def event_to_dict(event: WorkerEvent) -> dict[str, Any]:
    if isinstance(event, (ViewerSessionOpenedEvent, ViewerSessionUpdatedEvent, ViewerDataMaterializedEvent)):
        return {
            "type": event.type,
            "request_id": event.request_id,
            "workspace_id": event.workspace_id,
            "node_id": event.node_id,
            "session_id": event.session_id,
            "backend_id": event.backend_id,
            "data_refs": _serialize_viewer_mapping(event.data_refs, field_name="data_refs"),
            "transport": _serialize_viewer_mapping(event.transport, field_name="transport"),
            "transport_revision": int(event.transport_revision),
            "live_open_status": str(event.live_open_status),
            "live_open_blocker": _serialize_viewer_mapping(event.live_open_blocker, field_name="live_open_blocker"),
            "camera_state": _serialize_viewer_mapping(event.camera_state, field_name="camera_state"),
            "playback_state": _serialize_viewer_mapping(event.playback_state, field_name="playback_state"),
            "summary": _serialize_viewer_mapping(event.summary, field_name="summary"),
            "options": _serialize_viewer_mapping(event.options, field_name="options"),
        }
    if isinstance(event, ViewerSessionClosedEvent):
        return {
            "type": event.type,
            "request_id": event.request_id,
            "workspace_id": event.workspace_id,
            "node_id": event.node_id,
            "session_id": event.session_id,
            "backend_id": event.backend_id,
            "transport": _serialize_viewer_mapping(event.transport, field_name="transport"),
            "transport_revision": int(event.transport_revision),
            "live_open_status": str(event.live_open_status),
            "live_open_blocker": _serialize_viewer_mapping(event.live_open_blocker, field_name="live_open_blocker"),
            "camera_state": _serialize_viewer_mapping(event.camera_state, field_name="camera_state"),
            "playback_state": _serialize_viewer_mapping(event.playback_state, field_name="playback_state"),
            "summary": _serialize_viewer_mapping(event.summary, field_name="summary"),
            "options": _serialize_viewer_mapping(event.options, field_name="options"),
        }
    if isinstance(event, ViewerSessionFailedEvent):
        return {
            "type": event.type,
            "request_id": event.request_id,
            "workspace_id": event.workspace_id,
            "node_id": event.node_id,
            "session_id": event.session_id,
            "command": event.command,
            "error": event.error,
        }
    return _serialize_dataclass_payload(event)


def _start_run_command_from_payload(payload: Mapping[str, Any]) -> StartRunCommand:
    if "project_doc" in payload:
        raise ValueError("start_run payload does not accept project_doc; use runtime_snapshot.")
    trigger_payload = deserialize_runtime_value(payload.get("trigger"))
    runtime_snapshot_payload = deserialize_runtime_value(payload.get("runtime_snapshot"))
    return StartRunCommand(
        run_id=str(payload.get("run_id", "")),
        project_path=str(payload.get("project_path", "")),
        workspace_id=str(payload.get("workspace_id", "")),
        trigger=dict(trigger_payload) if isinstance(trigger_payload, Mapping) else {},
        runtime_snapshot=coerce_runtime_snapshot(runtime_snapshot_payload),
    )


def coerce_start_run_command(command: StartRunCommand | Mapping[str, Any]) -> StartRunCommand:
    if isinstance(command, StartRunCommand):
        return command

    payload = dict(command)
    payload.setdefault("type", "start_run")
    typed_command = dict_to_command(payload)
    if not isinstance(typed_command, StartRunCommand):
        raise ValueError("run_workflow requires a start_run command payload.")
    return typed_command


def dict_to_command(payload: dict[str, Any]) -> WorkerCommand:
    command_type = str(payload.get("type", ""))
    if command_type == "start_run":
        return _start_run_command_from_payload(payload)
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
    if command_type == "open_viewer_session":
        return OpenViewerSessionCommand(
            request_id=str(payload.get("request_id", "")),
            workspace_id=str(payload.get("workspace_id", "")),
            node_id=str(payload.get("node_id", "")),
            session_id=str(payload.get("session_id", "")),
            backend_id=str(payload.get("backend_id", "")),
            data_refs=_deserialize_viewer_mapping(payload.get("data_refs")),
            transport=_deserialize_viewer_mapping(payload.get("transport")),
            transport_revision=_deserialize_viewer_int(payload.get("transport_revision")),
            live_open_status=str(payload.get("live_open_status", "")),
            live_open_blocker=_deserialize_viewer_mapping(payload.get("live_open_blocker")),
            camera_state=_deserialize_viewer_mapping(payload.get("camera_state")),
            playback_state=_deserialize_viewer_mapping(payload.get("playback_state")),
            summary=_deserialize_viewer_mapping(payload.get("summary")),
            options=_deserialize_viewer_mapping(payload.get("options")),
        )
    if command_type == "update_viewer_session":
        return UpdateViewerSessionCommand(
            request_id=str(payload.get("request_id", "")),
            workspace_id=str(payload.get("workspace_id", "")),
            node_id=str(payload.get("node_id", "")),
            session_id=str(payload.get("session_id", "")),
            backend_id=str(payload.get("backend_id", "")),
            data_refs=_deserialize_viewer_mapping(payload.get("data_refs")),
            transport=_deserialize_viewer_mapping(payload.get("transport")),
            transport_revision=_deserialize_viewer_int(payload.get("transport_revision")),
            live_open_status=str(payload.get("live_open_status", "")),
            live_open_blocker=_deserialize_viewer_mapping(payload.get("live_open_blocker")),
            camera_state=_deserialize_viewer_mapping(payload.get("camera_state")),
            playback_state=_deserialize_viewer_mapping(payload.get("playback_state")),
            summary=_deserialize_viewer_mapping(payload.get("summary")),
            options=_deserialize_viewer_mapping(payload.get("options")),
        )
    if command_type == "close_viewer_session":
        return CloseViewerSessionCommand(
            request_id=str(payload.get("request_id", "")),
            workspace_id=str(payload.get("workspace_id", "")),
            node_id=str(payload.get("node_id", "")),
            session_id=str(payload.get("session_id", "")),
            options=_deserialize_viewer_mapping(payload.get("options")),
        )
    if command_type == "materialize_viewer_data":
        return MaterializeViewerDataCommand(
            request_id=str(payload.get("request_id", "")),
            workspace_id=str(payload.get("workspace_id", "")),
            node_id=str(payload.get("node_id", "")),
            session_id=str(payload.get("session_id", "")),
            backend_id=str(payload.get("backend_id", "")),
            options=_deserialize_viewer_mapping(payload.get("options")),
        )
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
        outputs_payload = deserialize_runtime_value(payload.get("outputs"))
        return NodeCompletedEvent(
            run_id=str(payload.get("run_id", "")),
            workspace_id=str(payload.get("workspace_id", "")),
            node_id=str(payload.get("node_id", "")),
            outputs=dict(outputs_payload) if isinstance(outputs_payload, dict) else {},
        )
    if event_type == "node_failed_handled":
        return NodeFailedHandledEvent(
            run_id=str(payload.get("run_id", "")),
            workspace_id=str(payload.get("workspace_id", "")),
            node_id=str(payload.get("node_id", "")),
            error=str(payload.get("error", "")),
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
            request_id=str(payload.get("request_id", "")),
            command=str(payload.get("command", "")),
            error=str(payload.get("error", "")),
        )
    if event_type == "viewer_session_opened":
        return ViewerSessionOpenedEvent(
            request_id=str(payload.get("request_id", "")),
            workspace_id=str(payload.get("workspace_id", "")),
            node_id=str(payload.get("node_id", "")),
            session_id=str(payload.get("session_id", "")),
            backend_id=str(payload.get("backend_id", "")),
            data_refs=_deserialize_viewer_mapping(payload.get("data_refs")),
            transport=_deserialize_viewer_mapping(payload.get("transport")),
            transport_revision=_deserialize_viewer_int(payload.get("transport_revision")),
            live_open_status=str(payload.get("live_open_status", "")),
            live_open_blocker=_deserialize_viewer_mapping(payload.get("live_open_blocker")),
            camera_state=_deserialize_viewer_mapping(payload.get("camera_state")),
            playback_state=_deserialize_viewer_mapping(payload.get("playback_state")),
            summary=_deserialize_viewer_mapping(payload.get("summary")),
            options=_deserialize_viewer_mapping(payload.get("options")),
        )
    if event_type == "viewer_session_updated":
        return ViewerSessionUpdatedEvent(
            request_id=str(payload.get("request_id", "")),
            workspace_id=str(payload.get("workspace_id", "")),
            node_id=str(payload.get("node_id", "")),
            session_id=str(payload.get("session_id", "")),
            backend_id=str(payload.get("backend_id", "")),
            data_refs=_deserialize_viewer_mapping(payload.get("data_refs")),
            transport=_deserialize_viewer_mapping(payload.get("transport")),
            transport_revision=_deserialize_viewer_int(payload.get("transport_revision")),
            live_open_status=str(payload.get("live_open_status", "")),
            live_open_blocker=_deserialize_viewer_mapping(payload.get("live_open_blocker")),
            camera_state=_deserialize_viewer_mapping(payload.get("camera_state")),
            playback_state=_deserialize_viewer_mapping(payload.get("playback_state")),
            summary=_deserialize_viewer_mapping(payload.get("summary")),
            options=_deserialize_viewer_mapping(payload.get("options")),
        )
    if event_type == "viewer_session_closed":
        return ViewerSessionClosedEvent(
            request_id=str(payload.get("request_id", "")),
            workspace_id=str(payload.get("workspace_id", "")),
            node_id=str(payload.get("node_id", "")),
            session_id=str(payload.get("session_id", "")),
            backend_id=str(payload.get("backend_id", "")),
            transport=_deserialize_viewer_mapping(payload.get("transport")),
            transport_revision=_deserialize_viewer_int(payload.get("transport_revision")),
            live_open_status=str(payload.get("live_open_status", "")),
            live_open_blocker=_deserialize_viewer_mapping(payload.get("live_open_blocker")),
            camera_state=_deserialize_viewer_mapping(payload.get("camera_state")),
            playback_state=_deserialize_viewer_mapping(payload.get("playback_state")),
            summary=_deserialize_viewer_mapping(payload.get("summary")),
            options=_deserialize_viewer_mapping(payload.get("options")),
        )
    if event_type == "viewer_data_materialized":
        return ViewerDataMaterializedEvent(
            request_id=str(payload.get("request_id", "")),
            workspace_id=str(payload.get("workspace_id", "")),
            node_id=str(payload.get("node_id", "")),
            session_id=str(payload.get("session_id", "")),
            backend_id=str(payload.get("backend_id", "")),
            data_refs=_deserialize_viewer_mapping(payload.get("data_refs")),
            transport=_deserialize_viewer_mapping(payload.get("transport")),
            transport_revision=_deserialize_viewer_int(payload.get("transport_revision")),
            live_open_status=str(payload.get("live_open_status", "")),
            live_open_blocker=_deserialize_viewer_mapping(payload.get("live_open_blocker")),
            camera_state=_deserialize_viewer_mapping(payload.get("camera_state")),
            playback_state=_deserialize_viewer_mapping(payload.get("playback_state")),
            summary=_deserialize_viewer_mapping(payload.get("summary")),
            options=_deserialize_viewer_mapping(payload.get("options")),
        )
    if event_type == "viewer_session_failed":
        return ViewerSessionFailedEvent(
            request_id=str(payload.get("request_id", "")),
            workspace_id=str(payload.get("workspace_id", "")),
            node_id=str(payload.get("node_id", "")),
            session_id=str(payload.get("session_id", "")),
            command=str(payload.get("command", "")),
            error=str(payload.get("error", "")),
        )
    raise ValueError(f"Unknown event type: {event_type!r}")
