from __future__ import annotations

from dataclasses import replace
from multiprocessing import Queue
from typing import Any

from ea_node_editor.execution.dpf_runtime.contracts import (
    DPF_FIELDS_CONTAINER_HANDLE_KIND,
)
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
from ea_node_editor.runtime_contracts import coerce_runtime_handle_ref

_DPF_VIEWER_SOURCE_KEY_ALIASES = {
    "fields": "fields_container",
    "field_data": "fields_container",
    "result": "fields_container",
}


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
    request_id: str = "",
    command: str = "",
) -> None:
    emit(
        event_queue,
        ProtocolErrorEvent(
            run_id=run_id,
            workspace_id=workspace_id,
            request_id=request_id,
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
    if isinstance(command, (OpenViewerSessionCommand, UpdateViewerSessionCommand)):
        command = replace(
            command,
            data_refs=_normalize_dpf_viewer_source_refs(command.data_refs),
        )
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


def _normalize_dpf_viewer_source_refs(source_refs: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for raw_key, value in source_refs.items():
        key = str(raw_key).strip()
        if not key:
            continue
        canonical_key = _DPF_VIEWER_SOURCE_KEY_ALIASES.get(key)
        if canonical_key is not None and _is_dpf_fields_container_ref(value):
            normalized.setdefault(canonical_key, value)
            continue
        normalized[key] = value
    return normalized


def _is_dpf_fields_container_ref(value: Any) -> bool:
    runtime_ref = coerce_runtime_handle_ref(value)
    return runtime_ref is not None and runtime_ref.kind == DPF_FIELDS_CONTAINER_HANDLE_KIND


def decode_command_payload(raw_command: Any, *, event_queue: Queue) -> WorkerCommand | None:
    if not isinstance(raw_command, dict):
        emit_protocol_error(event_queue, "Command payload must be a dictionary.")
        return None
    command_type = str(raw_command.get("type", "")).strip()
    request_id = str(raw_command.get("request_id", "")).strip()
    try:
        return dict_to_command(dict(raw_command))
    except ValueError as exc:
        emit_protocol_error(
            event_queue,
            f"Invalid command payload: {exc}",
            request_id=request_id,
            command=command_type,
        )
        return None


__all__ = [
    "decode_command_payload",
    "dispatch_viewer_command",
    "emit",
    "emit_protocol_error",
    "emit_run_state",
    "is_viewer_command",
]
