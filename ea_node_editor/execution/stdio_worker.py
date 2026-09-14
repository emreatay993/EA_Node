from __future__ import annotations

import json
import queue
import sys
import threading
import traceback
from contextlib import nullcontext
from typing import Any, TextIO

from ea_node_editor.execution.run_messages import (
    PauseRunCommand,
    ResumeRunCommand,
    RunFailedEvent,
    ShutdownCommand,
    StartRunCommand,
    StopRunCommand,
    RetireWorkspaceCommand,
    WorkspaceRetiredEvent,
)
from ea_node_editor.execution.protocol_codec import (
    command_to_dict,
)
from ea_node_editor.execution.worker import run_workflow
from ea_node_editor.execution.worker_protocol import (
    dispatch_generation_preparation,
    command_payload_type,
    dispatch_viewer_command,
    dispatch_viewer_invalidation,
    decode_command_payload,
    emit,
    emit_protocol_error,
    emit_run_state,
    is_viewer_command,
)
from ea_node_editor.execution.worker_services import WorkerServices
from ea_node_editor.execution.viewer_messages import InvalidateViewerSessionsCommand
from ea_node_editor.execution.generation_messages import PrepareGenerationCommand

_EVENT_WRITER_SENTINEL = object()


def _event_writer(event_queue: queue.Queue[Any], output: TextIO) -> None:
    while True:
        event = event_queue.get()
        if event is _EVENT_WRITER_SENTINEL:
            return
        try:
            output.write(
                json.dumps(event, ensure_ascii=True, separators=(",", ":")) + "\n"
            )
            output.flush()
        except OSError:
            return


def _run_workflow_thread(
    command: StartRunCommand,
    *,
    event_queue: queue.Queue[Any],
    command_queue: queue.Queue[dict[str, Any]],
    worker_services: WorkerServices,
    lifecycle_lock: Any = None,
    run_finished: threading.Event | None = None,
) -> None:
    try:
        run_workflow(
            command,
            event_queue,
            command_queue=command_queue,
            worker_services=worker_services,
        )
    except Exception as exc:  # noqa: BLE001
        worker_services.reset()
        emit(
            event_queue,
            RunFailedEvent(
                run_id=command.run_id,
                workspace_id=command.workspace_id,
                error=str(exc),
                traceback=traceback.format_exc(),
            ),
        )
        emit_run_state(
            event_queue,
            run_id=command.run_id,
            workspace_id=command.workspace_id,
            state="error",
            transition="fail",
            reason="worker_exception",
        )
    finally:
        with lifecycle_lock if lifecycle_lock is not None else nullcontext():
            deferred = []
            while True:
                try:
                    payload = command_queue.get_nowait()
                except queue.Empty:
                    break
                if command_payload_type(payload) in {
                    "invalidate_viewer_sessions",
                    "retire_workspace",
                }:
                    pending = decode_command_payload(
                        payload,
                        event_queue=event_queue,
                        worker_services=worker_services,
                    )
                    if pending is not None:
                        _dispatch_lifecycle_command(
                            pending, event_queue, worker_services
                        )
                else:
                    deferred.append(payload)
            for payload in deferred:
                command_queue.put(payload)
            if run_finished is not None:
                run_finished.set()


def _dispatch_lifecycle_command(
    command: Any, event_queue: queue.Queue[Any], services: WorkerServices
) -> bool:
    if isinstance(command, PrepareGenerationCommand):
        dispatch_generation_preparation(
            command, event_queue=event_queue, worker_services=services
        )
        return True
    if isinstance(command, InvalidateViewerSessionsCommand):
        dispatch_viewer_invalidation(
            command, event_queue=event_queue, worker_services=services
        )
        return True
    if isinstance(command, RetireWorkspaceCommand):
        try:
            retired = services.mechanical_session_service.retire_workspace(
                command.workspace_id
            )
            emit(
                event_queue,
                WorkspaceRetiredEvent(
                    request_id=command.request_id,
                    workspace_id=command.workspace_id,
                    retired_count=str(retired),
                ),
            )
        except Exception as exc:  # noqa: BLE001
            emit_protocol_error(
                event_queue,
                str(exc),
                request_id=command.request_id,
                workspace_id=command.workspace_id,
                command=command.type,
            )
        return True
    return False


def _load_json_line(
    line: str, *, event_queue: queue.Queue[Any]
) -> dict[str, Any] | None:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError as exc:
        emit_protocol_error(event_queue, f"Invalid JSON command payload: {exc}")
        return None
    if not isinstance(payload, dict):
        emit_protocol_error(event_queue, "Command payload must be a dictionary.")
        return None
    return dict(payload)


def main(stdin: TextIO | None = None, stdout: TextIO | None = None) -> int:
    input_stream = stdin or sys.stdin
    protocol_output = stdout or sys.stdout
    sys.stdout = sys.stderr

    event_queue: queue.Queue[Any] = queue.Queue()
    command_queue: queue.Queue[dict[str, Any]] = queue.Queue()
    worker_services = WorkerServices()
    writer = threading.Thread(
        target=_event_writer,
        args=(event_queue, protocol_output),
        daemon=True,
        name="external-python-event-writer",
    )
    writer.start()
    active_thread: threading.Thread | None = None
    lifecycle_lock = threading.Lock()
    run_finished = threading.Event()
    run_finished.set()

    try:
        for line in input_stream:
            payload = _load_json_line(line, event_queue=event_queue)
            if payload is None:
                continue

            if active_thread is not None and run_finished.is_set():
                active_thread.join(timeout=0.1)
                active_thread = None

            run_is_active = not run_finished.is_set()
            active_catalog = None
            if run_is_active:
                try:
                    active_catalog = worker_services.data_types
                except ValueError:
                    pass
            if run_is_active and command_payload_type(payload) == "start_run":
                emit_protocol_error(
                    event_queue,
                    "Worker already has an active run.",
                    command="start_run",
                    catalog=active_catalog,
                )
                continue

            command = decode_command_payload(
                payload,
                event_queue=event_queue,
                catalog=active_catalog,
                worker_services=None if run_is_active else worker_services,
            )
            if command is None:
                continue

            with lifecycle_lock:
                queued_for_run = not run_finished.is_set()
                if queued_for_run:
                    command_queue.put(payload)
            if queued_for_run:
                if isinstance(command, ShutdownCommand):
                    assert active_thread is not None
                    active_thread.join(timeout=2.0)
                    break
                continue

            if isinstance(command, ShutdownCommand):
                break
            if _dispatch_lifecycle_command(command, event_queue, worker_services):
                continue
            if isinstance(command, StartRunCommand):
                active_thread = threading.Thread(
                    target=_run_workflow_thread,
                    args=(command,),
                    kwargs={
                        "event_queue": event_queue,
                        "command_queue": command_queue,
                        "worker_services": worker_services,
                        "lifecycle_lock": lifecycle_lock,
                        "run_finished": run_finished,
                    },
                    daemon=False,
                    name=f"external-python-run-{command.run_id}",
                )
                run_finished.clear()
                active_thread.start()
            elif isinstance(command, StopRunCommand):
                emit_protocol_error(
                    event_queue,
                    "No active run to stop.",
                    run_id=command.run_id,
                    workspace_id=command.workspace_id,
                    command=command.type,
                )
            elif isinstance(command, (PauseRunCommand, ResumeRunCommand)):
                emit_protocol_error(
                    event_queue,
                    "No active run for command.",
                    run_id=command.run_id,
                    workspace_id="",
                    command=command.type,
                )
            elif is_viewer_command(command):
                dispatch_viewer_command(
                    command,
                    event_queue=event_queue,
                    worker_services=worker_services,
                )
            else:
                emit_protocol_error(
                    event_queue,
                    "Unknown command type.",
                    run_id=str(getattr(command, "run_id", "")),
                    workspace_id=str(getattr(command, "workspace_id", "")),
                    request_id=str(getattr(command, "request_id", "")),
                    command=str(getattr(command, "type", "")),
                )

        if active_thread is not None and active_thread.is_alive():
            command_queue.put(command_to_dict(ShutdownCommand()))
            active_thread.join(timeout=2.0)
    finally:
        event_queue.put(_EVENT_WRITER_SENTINEL)
        writer.join(timeout=1.0)
        worker_services.reset()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main"]
