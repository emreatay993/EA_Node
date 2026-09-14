# Purpose: Own ordered, cancellable Qt-free preparation and dispatch work.
# Map: subsystems/execution.md
# Tests: tests/test_execution_submission.py
from __future__ import annotations

from collections.abc import Callable, Mapping
from concurrent.futures import Future, ThreadPoolExecutor
import threading
from typing import Any
import uuid

from ea_node_editor.execution.prepared_execution import PreparedExecution
from ea_node_editor.execution.request_capture import PreparationCapture


class SubmissionCancelled(ValueError):
    """A request was cancelled or its captured inputs became obsolete."""


class SubmissionHandle:
    """An identity available before work starts, with nonblocking cancellation."""

    def __init__(self, workspace_id: str, schedule_stop: Callable[[str], None]) -> None:
        self.submission_id = f"submission_{uuid.uuid4().hex}"
        self.workspace_id = workspace_id
        self.cancellation = threading.Event()
        self._lock = threading.Lock()
        self._state = "queued"
        self._run_id = ""
        self._reason = ""
        self._schedule_stop = schedule_stop
        self._result: Future[str] = Future()

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    @property
    def run_id(self) -> str:
        with self._lock:
            return self._run_id

    def result(self, timeout: float | None = None) -> str:
        return self._result.result(timeout)

    def cancel(self, reason: str = "user") -> bool:
        with self._lock:
            if self.cancellation.is_set() or self._state in {"cancelled", "failed"}:
                return False
            self._reason = str(reason)
            self.cancellation.set()
            run_id = self._run_id if self._state == "dispatched" else ""
        if run_id:
            self._schedule_stop(run_id)
        return True

    def _begin(self) -> None:
        with self._lock:
            self._raise_if_cancelled()
            self._state = "preparing"

    def _raise_if_cancelled(self) -> None:
        if self.cancellation.is_set():
            raise SubmissionCancelled(self._reason or "cancelled")

    def _admit(self, run_id: str) -> Mapping[str, Any]:
        # Called in the runtime's final acceptance section. No callbacks, I/O
        # or executor waits are allowed inside this state transition.
        with self._lock:
            self._raise_if_cancelled()
            self._state = "admitted"
            self._run_id = run_id
        return {
            "type": "submission_admitted",
            "submission_id": self.submission_id,
            "run_id": run_id,
            "workspace_id": self.workspace_id,
        }

    def _dispatched(self) -> bool:
        with self._lock:
            self._state = "dispatched"
            return self.cancellation.is_set()

    def _failure(self, error: Exception) -> tuple[Exception, dict[str, Any]]:
        stale_reasons = {
            "prepared_workspace_revision_changed",
            "prepared_solution_observation_changed",
            "prepared_project_or_registry_changed",
            "prepared_dispatch_changed_before_start",
            "prepared_runtime_generation_changed",
            "preparation_evicted",
            "runtime_shutdown",
        }
        with self._lock:
            cancelled = (
                self.cancellation.is_set()
                or isinstance(error, SubmissionCancelled)
                or str(error) in stale_reasons
            )
            reason = (
                self._reason
                if self.cancellation.is_set()
                else ("inputs_changed" if cancelled else "preparation_failed")
            )
            self._state = "cancelled" if cancelled else "failed"
            result_error = SubmissionCancelled(reason) if cancelled else error
            event = {
                "type": f"submission_{self._state}",
                "submission_id": self.submission_id,
                "run_id": self._run_id,
                "workspace_id": self.workspace_id,
                "reason": reason,
                "error": str(error),
            }
        return result_error, event


class ExecutionSubmissionService:
    """One executor per runtime; state acceptance remains in CorexRuntime/store."""

    def __init__(
        self,
        *,
        prepare: Callable[..., PreparedExecution],
        dispatch: Callable[..., str],
        discard: Callable[[PreparedExecution], None],
        stop: Callable[[str], None],
        publish: Callable[[Mapping[str, Any]], None],
    ) -> None:
        self._prepare = prepare
        self._dispatch = dispatch
        self._discard = discard
        self._stop = stop
        self._publish = publish
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="corex-preparation"
        )
        self._lock = threading.Lock()
        self._pending: dict[str, SubmissionHandle] = {}
        self._closed = False

    def submit(self, capture: PreparationCapture) -> SubmissionHandle:
        if type(capture) is not PreparationCapture:
            raise TypeError("submission requires an owned PreparationCapture")
        handle = SubmissionHandle(capture.request.workspace_id, self._schedule_stop)
        with self._lock:
            if self._closed:
                raise RuntimeError("runtime submissions are closed")
            self._pending[handle.submission_id] = handle
            self._executor.submit(self._run, handle, capture)
        return handle

    def _run(self, handle: SubmissionHandle, capture: PreparationCapture) -> None:
        prepared = None
        failure = None
        run_id = ""
        try:
            handle._begin()
            prepared = self._prepare(capture, cancellation=handle.cancellation)
            handle._raise_if_cancelled()
            run_id = self._dispatch(
                prepared, cancellation=handle.cancellation, admission=handle._admit
            )
            if not run_id:
                raise RuntimeError("Execution client did not start a run.")
            if handle._dispatched():
                # StartRun has been written. Never send StopRun ahead of it.
                self._stop(run_id)
        except Exception as exc:
            failure = handle._failure(exc)
        finally:
            try:
                if prepared is not None:
                    self._discard(prepared)
            finally:
                with self._lock:
                    self._pending.pop(handle.submission_id, None)
        if failure is not None:
            error, event = failure
            self._publish(event)
            handle._result.set_exception(error)
        else:
            handle._result.set_result(run_id)

    def _schedule_stop(self, run_id: str) -> None:
        with self._lock:
            if not self._closed:
                self._executor.submit(self._stop, run_id)

    def submit_background(self, work: Callable[[], Any]) -> Future[Any]:
        """Share the preparation executor with generation initialization."""
        with self._lock:
            if self._closed:
                raise RuntimeError("runtime submissions are closed")
            return self._executor.submit(work)

    def cancel_pending(self, reason: str, *, workspace_id: str | None = None) -> None:
        with self._lock:
            handles = tuple(self._pending.values())
        for handle in handles:
            if workspace_id is None or handle.workspace_id == workspace_id:
                handle.cancel(reason)

    def shutdown(
        self, *, wait: bool = True, cleanup: Callable[[], None] | None = None
    ) -> None:
        with self._lock:
            first_close = not self._closed
            self._closed = True
            handles = tuple(self._pending.values())
            if first_close and cleanup is not None:
                self._executor.submit(cleanup)
        for handle in handles:
            handle.cancel("runtime_shutdown")
        # Cleanup follows any in-flight preparation. Subscribers may detach
        # immediately; this executor never waits for a GUI callback.
        self._executor.shutdown(wait=wait)
