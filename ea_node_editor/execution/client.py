from __future__ import annotations

import multiprocessing as mp
import queue
import threading
import uuid
from collections.abc import Callable
from typing import Any

from ea_node_editor.execution.protocol import (
    PauseRunCommand,
    ProtocolErrorEvent,
    ResumeRunCommand,
    RunFailedEvent,
    RunStateEvent,
    ShutdownCommand,
    StartRunCommand,
    StopRunCommand,
    WorkerCommand,
    WorkerEvent,
    command_to_dict,
    dict_to_event,
    event_to_dict,
)
from ea_node_editor.execution.worker import worker_main

_LISTENER_SHUTDOWN_SENTINEL = {"type": "__listener_shutdown__"}


class ProcessExecutionClient:
    _TERMINAL_EVENT_TYPES = {"run_completed", "run_failed", "run_stopped"}

    def __init__(self) -> None:
        self._ctx = mp.get_context("spawn")
        self._command_queue: mp.Queue = self._ctx.Queue()
        self._event_queue: mp.Queue = self._ctx.Queue()
        self._process: mp.Process | None = None
        self._state_lock = threading.Lock()
        self._callbacks: list[Callable[[dict[str, Any]], None]] = []
        self._active_run_id = ""
        self._active_workspace_id = ""
        self._listener_thread = threading.Thread(
            target=self._event_listener,
            daemon=True,
            name="execution-event-listener",
        )
        self._running = True
        self._listener_thread.start()

    def _ensure_process(self) -> None:
        with self._state_lock:
            process = self._process
        if process is not None and process.is_alive():
            return
        if process is not None and not process.is_alive():
            process.join(timeout=0.1)

        new_process = self._ctx.Process(
            target=worker_main,
            args=(self._command_queue, self._event_queue),
            daemon=True,
            name="ea-node-exec-worker",
        )
        new_process.start()
        with self._state_lock:
            self._process = new_process

    def subscribe(self, callback: Callable[[dict[str, Any]], None]) -> None:
        self._callbacks.append(callback)

    def _dispatch_event(self, event: WorkerEvent) -> None:
        payload = event_to_dict(event)
        for callback in list(self._callbacks):
            try:
                callback(dict(payload))
            except Exception:
                continue

    def _emit_protocol_error(self, message: str, *, run_id: str = "", command: str = "") -> None:
        with self._state_lock:
            workspace_id = self._active_workspace_id
        self._dispatch_event(
            ProtocolErrorEvent(
                run_id=run_id,
                workspace_id=workspace_id,
                command=command,
                error=message,
            )
        )

    def _post_command(self, command: WorkerCommand) -> bool:
        payload = command_to_dict(command)
        try:
            self._command_queue.put(payload)
            return True
        except Exception as exc:  # noqa: BLE001
            self._emit_protocol_error(
                f"Failed to dispatch command: {exc}",
                run_id=getattr(command, "run_id", ""),
                command=getattr(command, "type", ""),
            )
            return False

    def start_run(
        self,
        project_path: str,
        workspace_id: str,
        trigger: dict[str, Any] | None = None,
    ) -> str:
        try:
            self._ensure_process()
        except Exception as exc:  # noqa: BLE001
            self._emit_protocol_error(f"Failed to start worker process: {exc}", command="start_run")
            return ""

        run_id = f"run_{uuid.uuid4().hex[:8]}"
        project_doc = trigger.get("project_doc") if isinstance(trigger, dict) else None
        command = StartRunCommand(
            run_id=run_id,
            project_path=project_path,
            workspace_id=workspace_id,
            trigger=dict(trigger or {}),
            project_doc=dict(project_doc) if isinstance(project_doc, dict) else {},
        )
        with self._state_lock:
            self._active_run_id = run_id
            self._active_workspace_id = workspace_id
        if not self._post_command(command):
            with self._state_lock:
                self._active_run_id = ""
                self._active_workspace_id = ""
            return ""
        return run_id

    def pause_run(self, run_id: str) -> None:
        if run_id:
            self._post_command(PauseRunCommand(run_id=run_id))

    def resume_run(self, run_id: str) -> None:
        if run_id:
            self._post_command(ResumeRunCommand(run_id=run_id))

    def stop_run(self, run_id: str) -> None:
        if run_id:
            self._post_command(StopRunCommand(run_id=run_id))

    def shutdown(self) -> None:
        self._running = False
        try:
            self._event_queue.put_nowait(dict(_LISTENER_SHUTDOWN_SENTINEL))
        except Exception:
            pass
        with self._state_lock:
            process = self._process
            self._active_run_id = ""
            self._active_workspace_id = ""
        if process and process.is_alive():
            self._post_command(ShutdownCommand())
            process.join(timeout=1.5)
        if process and process.is_alive():
            process.terminate()
            process.join(timeout=0.5)
        with self._state_lock:
            self._process = None
        if self._listener_thread.is_alive():
            self._listener_thread.join(timeout=1.0)
        self._close_queue(self._command_queue)
        self._close_queue(self._event_queue)
        if self._listener_thread.is_alive():
            self._listener_thread.join(timeout=0.5)

    def _check_worker_health(self) -> None:
        with self._state_lock:
            process = self._process
            active_run_id = self._active_run_id
            workspace_id = self._active_workspace_id
        if process is None:
            return
        if process.is_alive():
            return

        process.join(timeout=0.1)
        with self._state_lock:
            self._process = None
            run_id = self._active_run_id
            run_workspace = self._active_workspace_id
            self._active_run_id = ""
            self._active_workspace_id = ""

        if active_run_id and run_id == active_run_id:
            self._dispatch_event(
                RunFailedEvent(
                    run_id=active_run_id,
                    workspace_id=workspace_id or run_workspace,
                    error="Execution worker terminated unexpectedly.",
                    traceback="",
                    fatal=True,
                )
            )
            self._dispatch_event(
                RunStateEvent(
                    run_id=active_run_id,
                    workspace_id=workspace_id or run_workspace,
                    state="error",
                    transition="fail",
                    reason="worker_terminated",
                )
            )

    def _event_listener(self) -> None:
        while self._running:
            try:
                event = self._event_queue.get(timeout=0.2)
            except queue.Empty:
                self._check_worker_health()
                continue
            except (EOFError, OSError):
                self._check_worker_health()
                continue

            if event == _LISTENER_SHUTDOWN_SENTINEL:
                break
            if not isinstance(event, dict):
                self._emit_protocol_error("Received non-dictionary event from worker.")
                continue

            try:
                typed_event = dict_to_event(dict(event))
            except ValueError as exc:
                self._emit_protocol_error(f"Received invalid worker event: {exc}")
                continue

            payload = event_to_dict(typed_event)
            event_type = payload.get("type", "")
            event_run_id = payload.get("run_id", "")
            self._dispatch_event(typed_event)

            if event_type in self._TERMINAL_EVENT_TYPES:
                with self._state_lock:
                    if not self._active_run_id or self._active_run_id == event_run_id:
                        self._active_run_id = ""
                        self._active_workspace_id = ""

    @staticmethod
    def _close_queue(queue_obj: mp.Queue) -> None:
        try:
            queue_obj.close()
        except Exception:
            pass
        try:
            queue_obj.join_thread()
        except Exception:
            pass
