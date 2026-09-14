# Purpose: Deliver deterministic submission events on the caller's queued UI turns.
# Map: feature_routes/run_controller_selected_workspace_state
# Tests: tests/test_run_controller_unit.py, tests/test_shell_run_controller.py
from __future__ import annotations

from ea_node_editor.execution.submission_service import SubmissionHandle


class QueuedSubmissionDriver:
    """Test transport for clients whose dispatch method only records a request."""

    def __init__(self, *, schedule, prepare, dispatch, publish, stop):
        self._schedule = schedule
        self._prepare = prepare
        self._dispatch = dispatch
        self._publish = publish
        self._stop = stop
        self._pending = {}
        self._closed = False

    def submit(self, request):
        handle = SubmissionHandle(
            request.workspace_id,
            lambda run_id: self._schedule(lambda: self._stop(run_id)),
        )
        self._pending[handle.submission_id] = handle

        def deliver():
            try:
                handle._begin()
                prepared = self._prepare(request)
                handle._raise_if_cancelled()
                run_id = self._dispatch(prepared)
                if not run_id:
                    raise RuntimeError("start failed")
                self._publish(
                    {
                        **handle._admit(run_id),
                        "recompute_node_ids": list(prepared.recompute_node_ids),
                    }
                )
                if handle._dispatched():
                    self._stop(run_id)
                handle._result.set_result(run_id)
            except Exception as exc:
                error, event = handle._failure(exc)
                if not self._closed:
                    self._publish(event)
                handle._result.set_exception(error)
            finally:
                self._pending.pop(handle.submission_id, None)

        self._schedule(deliver)
        return handle

    def cancel_pending(self, reason="user", *, workspace_id=None):
        for handle in tuple(self._pending.values()):
            if workspace_id is None or handle.workspace_id == workspace_id:
                handle.cancel(reason)

    def close(self):
        self._closed = True
        self.cancel_pending("runtime_shutdown")
