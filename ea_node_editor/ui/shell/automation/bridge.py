# Purpose: GUI-thread AutomationBridge: FIFO request queue from the transport thread, busy/modal/shutdown guards, dialog watchdog, Deferred polling.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
"""AutomationBridge (T02 owner: implement; T00 fixes the public shape).

Contract
--------
- ``submit(request) -> concurrent.futures.Future[AutomationResponse]`` is
  thread-safe and is the ONLY entry point the transport thread uses. It emits
  a queued ``pyqtSignal`` so the request is appended to a FIFO on the GUI
  thread; the slot only enqueues and schedules ``QTimer.singleShot(0, drain)``
  when the bridge is not busy (capture and ``set_node_title`` run nested event
  loops, so draining must never re-enter).
- Pre-dispatch guards (checked on the GUI thread, in this order):
  ``host._shell_teardown_started`` -> ``APP_SHUTTING_DOWN``;
  ``QApplication.activeModalWidget()`` / ``activePopupWidget()`` ->
  ``APP_BUSY_MODAL`` (retryable); ``document_io_active()`` and
  ``op.mutates_graph`` -> ``APP_BUSY``.
- A watchdog ``QTimer`` runs during each op; if an unexpected ``QDialog``
  becomes the active modal widget it is rejected and the op fails with
  ``UNEXPECTED_DIALOG``.
- ``execute_op`` (dispatch.py) does validation + grouped history + error
  translation. A ``Deferred`` result is polled every ``poll_interval_s`` while
  the bridge is *not* busy, so ``run.control(stop)`` can interleave with a
  pending ``run.status(wait=true)``; ``timeout_s`` -> ``on_timeout()`` or
  ``TIMEOUT``.
- Requests carry ``timeout_s``; synchronous ops that exceed it still complete
  (we never kill GUI work) but the response is marked ``TIMEOUT`` if the
  client already gave up.
"""

from __future__ import annotations

from concurrent.futures import Future
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

from ea_node_editor.automation.errors import NOT_IMPLEMENTED, AutomationOpError
from ea_node_editor.automation.protocol import AutomationRequest, AutomationResponse
from ea_node_editor.ui.shell.automation.context import AutomationContext
from ea_node_editor.ui.shell.automation.dispatch import HandlerTable


class AutomationBridge(QObject):
    """Serialises automation requests onto the GUI thread (see module docstring)."""

    _request_queued = pyqtSignal(object)

    def __init__(self, context: AutomationContext, handlers: HandlerTable, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._context = context
        self._handlers = dict(handlers)
        self._queue: list[tuple[AutomationRequest, Future[AutomationResponse]]] = []
        self._busy = False
        self._closed = False
        self._request_queued.connect(self._enqueue)

    @property
    def context(self) -> AutomationContext:
        return self._context

    @property
    def busy(self) -> bool:
        return self._busy

    def submit(self, request: AutomationRequest) -> "Future[AutomationResponse]":
        future: Future[AutomationResponse] = Future()
        if self._closed:
            future.set_result(
                AutomationResponse.failure(
                    request.id,
                    AutomationOpError("APP_SHUTTING_DOWN", "The automation bridge is closed."),
                )
            )
            return future
        self._request_queued.emit((request, future))
        return future

    def _enqueue(self, item: Any) -> None:
        # T02: append to FIFO, schedule drain via QTimer.singleShot(0, self._drain) when not busy.
        request, future = item
        future.set_result(
            AutomationResponse.failure(
                request.id,
                AutomationOpError(NOT_IMPLEMENTED, "AutomationBridge dispatch is not implemented yet (T02)."),
            )
        )

    def shutdown(self) -> None:
        self._closed = True
        pending = list(self._queue)
        self._queue.clear()
        for request, future in pending:
            if not future.done():
                future.set_result(
                    AutomationResponse.failure(
                        request.id,
                        AutomationOpError("APP_SHUTTING_DOWN", "COREX is shutting down."),
                    )
                )


__all__ = ["AutomationBridge"]
