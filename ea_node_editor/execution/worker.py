from __future__ import annotations

import traceback
from multiprocessing import Queue
from typing import Any

from ea_node_editor.execution.protocol import (
    PauseRunCommand,
    ResumeRunCommand,
    RunFailedEvent,
    ShutdownCommand,
    StartRunCommand,
    StopRunCommand,
    coerce_start_run_command,
)
from ea_node_editor.execution.worker_protocol import (
    decode_command_payload,
    dispatch_viewer_command,
    emit,
    emit_protocol_error,
    emit_run_state,
    is_viewer_command,
)
from ea_node_editor.execution.worker_runner import WorkflowRunner
from ea_node_editor.execution.worker_services import WorkerServices


def run_workflow(
    command: StartRunCommand | dict[str, Any],
    event_queue: Queue,
    command_queue: Queue | None = None,
    worker_services: WorkerServices | None = None,
) -> None:
    typed_command = coerce_start_run_command(command)
    WorkflowRunner(
        typed_command,
        event_queue,
        command_queue=command_queue,
        worker_services=worker_services,
    ).run()


def worker_main(
    command_queue: Queue,
    event_queue: Queue,
    worker_services: WorkerServices | None = None,
) -> None:
    services = worker_services or WorkerServices()
    while True:
        raw_command = command_queue.get()
        command = decode_command_payload(raw_command, event_queue=event_queue)
        if command is None:
            continue

        if isinstance(command, ShutdownCommand):
            break
        if isinstance(command, StartRunCommand):
            try:
                run_workflow(
                    command,
                    event_queue,
                    command_queue=command_queue,
                    worker_services=services,
                )
            except Exception as exc:  # noqa: BLE001
                services.reset()
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
                worker_services=services,
            )
        else:
            emit_protocol_error(
                event_queue,
                "Unknown command type.",
                run_id=getattr(command, "run_id", ""),
                workspace_id=getattr(command, "workspace_id", ""),
                command=getattr(command, "type", ""),
            )
