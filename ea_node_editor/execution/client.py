from __future__ import annotations

import multiprocessing as mp
import queue
import threading
import uuid
from collections.abc import Callable
from typing import Any

from ea_node_editor.execution.worker import worker_main


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

    def _dispatch_event(self, payload: dict[str, Any]) -> None:
        for callback in list(self._callbacks):
            try:
                callback(dict(payload))
            except Exception:
                continue

    def _emit_protocol_error(self, message: str, *, run_id: str = "", command: str = "") -> None:
        with self._state_lock:
            workspace_id = self._active_workspace_id
        self._dispatch_event(
            {
                "type": "protocol_error",
                "run_id": run_id,
                "workspace_id": workspace_id,
                "command": command,
                "error": message,
            }
        )

    def _post_command(self, payload: dict[str, Any]) -> bool:
        try:
            self._command_queue.put(payload)
            return True
        except Exception as exc:  # noqa: BLE001
            self._emit_protocol_error(
                f"Failed to dispatch command: {exc}",
                run_id=str(payload.get("run_id", "")),
                command=str(payload.get("type", "")),
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
        message = {
            "type": "start_run",
            "run_id": run_id,
            "project_path": project_path,
            "workspace_id": workspace_id,
            "trigger": trigger or {},
        }
        if trigger and "project_doc" in trigger:
            message["project_doc"] = trigger["project_doc"]
        with self._state_lock:
            self._active_run_id = run_id
            self._active_workspace_id = workspace_id
        if not self._post_command(message):
            with self._state_lock:
                self._active_run_id = ""
                self._active_workspace_id = ""
            return ""
        return run_id

    def pause_run(self, run_id: str) -> None:
        if run_id:
            self._post_command({"type": "pause_run", "run_id": run_id})

    def resume_run(self, run_id: str) -> None:
        if run_id:
            self._post_command({"type": "resume_run", "run_id": run_id})

    def stop_run(self, run_id: str) -> None:
        if run_id:
            self._post_command({"type": "stop_run", "run_id": run_id})

    def shutdown(self) -> None:
        self._running = False
        with self._state_lock:
            process = self._process
            self._active_run_id = ""
            self._active_workspace_id = ""
        if process and process.is_alive():
            self._post_command({"type": "shutdown"})
            process.join(timeout=1.5)
        if process and process.is_alive():
            process.terminate()
            process.join(timeout=0.5)
        with self._state_lock:
            self._process = None
        if self._listener_thread.is_alive():
            self._listener_thread.join(timeout=1.0)

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
                {
                    "type": "run_failed",
                    "state": "error",
                    "run_id": active_run_id,
                    "workspace_id": workspace_id or run_workspace,
                    "error": "Execution worker terminated unexpectedly.",
                    "traceback": "",
                    "fatal": True,
                }
            )
            self._dispatch_event(
                {
                    "type": "run_state",
                    "state": "error",
                    "run_id": active_run_id,
                    "workspace_id": workspace_id or run_workspace,
                    "transition": "fail",
                    "reason": "worker_terminated",
                }
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

            if not isinstance(event, dict):
                self._emit_protocol_error("Received non-dictionary event from worker.")
                continue

            payload = dict(event)
            event_type = str(payload.get("type", ""))
            event_run_id = str(payload.get("run_id", ""))
            self._dispatch_event(payload)

            if event_type in self._TERMINAL_EVENT_TYPES:
                with self._state_lock:
                    if not self._active_run_id or self._active_run_id == event_run_id:
                        self._active_run_id = ""
                        self._active_workspace_id = ""
