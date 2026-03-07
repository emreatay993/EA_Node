"""Typed event and command definitions for the execution protocol.

All communication between the UI process and the worker process goes through
these structures. Using dataclasses instead of raw dicts means a misspelled
field name causes an immediate error rather than silent data loss.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

EngineState = Literal["ready", "running", "paused", "error"]
RunTransition = Literal["start", "pause", "resume", "stop", "complete", "fail"]
EventType = Literal[
    "run_started", "run_state", "run_completed", "run_failed", "run_stopped",
    "node_started", "node_completed", "log", "protocol_error",
]


# ---------------------------------------------------------------------------
# Commands (UI -> Worker)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StartRunCommand:
    type: str = "start_run"
    run_id: str = ""
    project_path: str = ""
    workspace_id: str = ""
    trigger: dict[str, Any] = field(default_factory=dict)
    project_doc: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class StopRunCommand:
    type: str = "stop_run"
    run_id: str = ""
    workspace_id: str = ""


@dataclass(frozen=True)
class PauseRunCommand:
    type: str = "pause_run"
    run_id: str = ""


@dataclass(frozen=True)
class ResumeRunCommand:
    type: str = "resume_run"
    run_id: str = ""


@dataclass(frozen=True)
class ShutdownCommand:
    type: str = "shutdown"


# ---------------------------------------------------------------------------
# Events (Worker -> UI)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RunStartedEvent:
    type: str = "run_started"
    run_id: str = ""
    workspace_id: str = ""


@dataclass(frozen=True)
class RunStateEvent:
    type: str = "run_state"
    run_id: str = ""
    workspace_id: str = ""
    state: str = "ready"
    transition: str = ""
    reason: str = ""


@dataclass(frozen=True)
class RunCompletedEvent:
    type: str = "run_completed"
    run_id: str = ""
    workspace_id: str = ""
    state: str = "ready"


@dataclass(frozen=True)
class RunFailedEvent:
    type: str = "run_failed"
    run_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    error: str = ""
    traceback: str = ""
    state: str = "error"
    fatal: bool = False


@dataclass(frozen=True)
class RunStoppedEvent:
    type: str = "run_stopped"
    run_id: str = ""
    workspace_id: str = ""
    reason: str = ""
    state: str = "ready"


@dataclass(frozen=True)
class NodeStartedEvent:
    type: str = "node_started"
    run_id: str = ""
    workspace_id: str = ""
    node_id: str = ""


@dataclass(frozen=True)
class NodeCompletedEvent:
    type: str = "node_completed"
    run_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    outputs: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LogEvent:
    type: str = "log"
    run_id: str = ""
    workspace_id: str = ""
    node_id: str = ""
    level: str = "info"
    message: str = ""


@dataclass(frozen=True)
class ProtocolErrorEvent:
    type: str = "protocol_error"
    run_id: str = ""
    workspace_id: str = ""
    command: str = ""
    error: str = ""


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def event_to_dict(event: Any) -> dict[str, Any]:
    """Convert a typed event dataclass to a plain dict for queue transport."""
    return asdict(event)


def dict_to_event_type(payload: dict[str, Any]) -> str:
    """Extract the event type string from a payload dict."""
    return str(payload.get("type", ""))


# Backward-compatible TypedDict aliases for code that still uses raw dicts
class WorkerCommand(dict):
    """Legacy dict wrapper -- prefer the typed command dataclasses above."""
    pass


class WorkerEvent(dict):
    """Legacy dict wrapper -- prefer the typed event dataclasses above."""
    pass
