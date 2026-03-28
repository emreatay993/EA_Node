from __future__ import annotations

import multiprocessing as mp
import queue
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ea_node_editor.execution.protocol import (
    CloseViewerSessionCommand,
    MaterializeViewerDataCommand,
    OpenViewerSessionCommand,
    PauseRunCommand,
    ProtocolErrorEvent,
    ResumeRunCommand,
    RunFailedEvent,
    RunStateEvent,
    ShutdownCommand,
    StopRunCommand,
    UpdateViewerSessionCommand,
    VIEWER_COMMAND_TYPES,
    VIEWER_RESPONSE_EVENT_TYPES,
    ViewerSessionFailedEvent,
    WorkerCommand,
    WorkerEvent,
    command_to_dict,
    coerce_start_run_command,
    dict_to_event,
    event_to_dict,
)
from ea_node_editor.execution.worker import worker_main

_LISTENER_SHUTDOWN_SENTINEL = {"type": "__listener_shutdown__"}


@dataclass(frozen=True)
class _PendingViewerRequest:
    request_id: str
    command: str
    workspace_id: str
    node_id: str
    session_id: str


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
        self._viewer_request_lock = threading.Lock()
        self._pending_viewer_requests: dict[str, _PendingViewerRequest] = {}
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

    def _emit_protocol_error(
        self,
        message: str,
        *,
        run_id: str = "",
        request_id: str = "",
        command: str = "",
    ) -> None:
        with self._state_lock:
            workspace_id = self._active_workspace_id
        self._dispatch_event(
            ProtocolErrorEvent(
                run_id=run_id,
                workspace_id=workspace_id,
                request_id=request_id,
                command=command,
                error=message,
            )
        )

    def _try_post_command(self, command: WorkerCommand) -> tuple[bool, str]:
        try:
            payload = command_to_dict(command)
            self._command_queue.put(payload)
            return True, ""
        except Exception as exc:  # noqa: BLE001
            message = f"Failed to dispatch command: {exc}"
            self._emit_protocol_error(
                message,
                run_id=getattr(command, "run_id", ""),
                request_id=getattr(command, "request_id", ""),
                command=getattr(command, "type", ""),
            )
            return False, message

    def _post_command(self, command: WorkerCommand) -> bool:
        success, _message = self._try_post_command(command)
        return success

    @staticmethod
    def _next_viewer_request_id() -> str:
        return f"viewer_{uuid.uuid4().hex[:8]}"

    def _track_viewer_request(self, pending: _PendingViewerRequest) -> None:
        with self._viewer_request_lock:
            self._pending_viewer_requests[pending.request_id] = pending

    def _complete_viewer_request(self, request_id: str) -> _PendingViewerRequest | None:
        if not request_id:
            return None
        with self._viewer_request_lock:
            return self._pending_viewer_requests.pop(request_id, None)

    def _dispatch_viewer_request_failure(self, pending: _PendingViewerRequest, error: str) -> None:
        self._dispatch_event(
            ViewerSessionFailedEvent(
                request_id=pending.request_id,
                workspace_id=pending.workspace_id,
                node_id=pending.node_id,
                session_id=pending.session_id,
                command=pending.command,
                error=error,
            )
        )

    def _viewer_protocol_error_failure(
        self,
        payload: dict[str, Any],
    ) -> ViewerSessionFailedEvent | None:
        command = str(payload.get("command", ""))
        if command not in VIEWER_COMMAND_TYPES:
            return None
        request_id = str(payload.get("request_id", ""))
        pending = self._complete_viewer_request(request_id)
        if pending is None:
            return None
        return ViewerSessionFailedEvent(
            request_id=pending.request_id,
            workspace_id=pending.workspace_id or str(payload.get("workspace_id", "")),
            node_id=pending.node_id,
            session_id=pending.session_id,
            command=command,
            error=str(payload.get("error", "")),
        )

    def _send_viewer_command(
        self,
        command: WorkerCommand,
        *,
        require_session_id: bool = False,
    ) -> str:
        request_id = str(getattr(command, "request_id", ""))
        pending = _PendingViewerRequest(
            request_id=request_id,
            command=str(getattr(command, "type", "")),
            workspace_id=str(getattr(command, "workspace_id", "")),
            node_id=str(getattr(command, "node_id", "")),
            session_id=str(getattr(command, "session_id", "")),
        )
        self._track_viewer_request(pending)
        if require_session_id and not pending.session_id:
            self._complete_viewer_request(request_id)
            self._dispatch_viewer_request_failure(pending, "session_id is required.")
            return request_id
        try:
            self._ensure_process()
        except Exception as exc:  # noqa: BLE001
            self._complete_viewer_request(request_id)
            self._dispatch_viewer_request_failure(
                pending,
                f"Failed to start worker process: {exc}",
            )
            return request_id

        success, error_message = self._try_post_command(command)
        if not success:
            self._complete_viewer_request(request_id)
            self._dispatch_viewer_request_failure(pending, error_message)
        return request_id

    def start_run(
        self,
        project_path: str,
        workspace_id: str,
        trigger: dict[str, Any] | None = None,
    ) -> str:
        trigger_payload = dict(trigger or {})
        if "project_doc" in trigger_payload:
            self._emit_protocol_error(
                "start_run trigger does not accept project_doc; use runtime_snapshot.",
                command="start_run",
            )
            return ""

        run_id = f"run_{uuid.uuid4().hex[:8]}"
        runtime_snapshot = trigger_payload.pop("runtime_snapshot", None)
        try:
            command = coerce_start_run_command(
                {
                    "run_id": run_id,
                    "project_path": project_path,
                    "workspace_id": workspace_id,
                    "trigger": trigger_payload,
                    "runtime_snapshot": runtime_snapshot,
                }
            )
        except ValueError as exc:
            self._emit_protocol_error(str(exc), run_id=run_id, command="start_run")
            return ""

        try:
            self._ensure_process()
        except Exception as exc:  # noqa: BLE001
            self._emit_protocol_error(f"Failed to start worker process: {exc}", command="start_run")
            return ""
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

    def open_viewer_session(
        self,
        workspace_id: str,
        node_id: str,
        *,
        session_id: str = "",
        data_refs: dict[str, Any] | None = None,
        summary: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> str:
        return self._send_viewer_command(
            OpenViewerSessionCommand(
                request_id=self._next_viewer_request_id(),
                workspace_id=workspace_id,
                node_id=node_id,
                session_id=session_id,
                data_refs=dict(data_refs or {}),
                summary=dict(summary or {}),
                options=dict(options or {}),
            )
        )

    def update_viewer_session(
        self,
        workspace_id: str,
        node_id: str,
        session_id: str,
        *,
        data_refs: dict[str, Any] | None = None,
        summary: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> str:
        return self._send_viewer_command(
            UpdateViewerSessionCommand(
                request_id=self._next_viewer_request_id(),
                workspace_id=workspace_id,
                node_id=node_id,
                session_id=session_id,
                data_refs=dict(data_refs or {}),
                summary=dict(summary or {}),
                options=dict(options or {}),
            ),
            require_session_id=True,
        )

    def close_viewer_session(
        self,
        workspace_id: str,
        node_id: str,
        session_id: str,
        *,
        options: dict[str, Any] | None = None,
    ) -> str:
        return self._send_viewer_command(
            CloseViewerSessionCommand(
                request_id=self._next_viewer_request_id(),
                workspace_id=workspace_id,
                node_id=node_id,
                session_id=session_id,
                options=dict(options or {}),
            ),
            require_session_id=True,
        )

    def materialize_viewer_data(
        self,
        workspace_id: str,
        node_id: str,
        session_id: str,
        *,
        options: dict[str, Any] | None = None,
    ) -> str:
        return self._send_viewer_command(
            MaterializeViewerDataCommand(
                request_id=self._next_viewer_request_id(),
                workspace_id=workspace_id,
                node_id=node_id,
                session_id=session_id,
                options=dict(options or {}),
            ),
            require_session_id=True,
        )

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
        with self._viewer_request_lock:
            self._pending_viewer_requests.clear()
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
            viewer_failure_event = None
            if event_type == "protocol_error":
                viewer_failure_event = self._viewer_protocol_error_failure(payload)
            elif event_type in VIEWER_RESPONSE_EVENT_TYPES:
                self._complete_viewer_request(str(payload.get("request_id", "")))
            self._dispatch_event(typed_event)
            if viewer_failure_event is not None:
                self._dispatch_event(viewer_failure_event)

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
