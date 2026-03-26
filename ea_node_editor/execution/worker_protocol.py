from __future__ import annotations

from multiprocessing import Queue
from typing import Any

from ea_node_editor.execution.protocol import (
    CloseViewerSessionCommand,
    MaterializeViewerDataCommand,
    OpenViewerSessionCommand,
    ProtocolErrorEvent,
    RunStateEvent,
    UpdateViewerSessionCommand,
    ViewerSessionFailedEvent,
    WorkerCommand,
    WorkerEvent,
    dict_to_command,
    event_to_dict,
)
from ea_node_editor.execution.worker_services import WorkerServices


def emit(event_queue: Queue, event: WorkerEvent) -> None:
    event_queue.put(event_to_dict(event))


def emit_run_state(
    event_queue: Queue,
    *,
    run_id: str,
    workspace_id: str,
    state: str,
    transition: str,
    reason: str,
) -> None:
    emit(
        event_queue,
        RunStateEvent(
            run_id=run_id,
            workspace_id=workspace_id,
            state=state,  # type: ignore[arg-type]
            transition=transition,
            reason=reason,
        ),
    )


def emit_protocol_error(
    event_queue: Queue,
    message: str,
    *,
    run_id: str = "",
    workspace_id: str = "",
    command: str = "",
) -> None:
    emit(
        event_queue,
        ProtocolErrorEvent(
            run_id=run_id,
            workspace_id=workspace_id,
            command=command,
            error=message,
        ),
    )


def is_viewer_command(command: WorkerCommand) -> bool:
    return isinstance(
        command,
        (
            OpenViewerSessionCommand,
            UpdateViewerSessionCommand,
            CloseViewerSessionCommand,
            MaterializeViewerDataCommand,
        ),
    )


def dispatch_viewer_command(
    command: WorkerCommand,
    *,
    event_queue: Queue,
    worker_services: WorkerServices,
) -> None:
    try:
        event = worker_services.viewer_session_service.handle_command(command)
    except Exception as exc:  # noqa: BLE001
        event = ViewerSessionFailedEvent(
            request_id=str(getattr(command, "request_id", "")).strip(),
            workspace_id=str(getattr(command, "workspace_id", "")).strip(),
            node_id=str(getattr(command, "node_id", "")).strip(),
            session_id=str(getattr(command, "session_id", "")).strip(),
            command=str(getattr(command, "type", "")).strip(),
            error=str(exc).strip() or "viewer session dispatch failed",
        )
    emit(event_queue, event)


def decode_command_payload(raw_command: Any, *, event_queue: Queue) -> WorkerCommand | None:
    if not isinstance(raw_command, dict):
        emit_protocol_error(event_queue, "Command payload must be a dictionary.")
        return None
    try:
        return dict_to_command(dict(raw_command))
    except ValueError as exc:
        emit_protocol_error(event_queue, f"Invalid command payload: {exc}")
        return None


__all__ = [
    "decode_command_payload",
    "dispatch_viewer_command",
    "emit",
    "emit_protocol_error",
    "emit_run_state",
    "is_viewer_command",
]
