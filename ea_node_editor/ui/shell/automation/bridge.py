# Purpose: GUI-thread AutomationBridge: FIFO request queue from the transport thread, busy/modal/shutdown guards, dialog watchdog, Deferred polling.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_bridge.py
"""AutomationBridge: serialises automation requests onto the GUI thread.

Contract
--------
- ``submit(request) -> concurrent.futures.Future[AutomationResponse]`` is
  thread-safe and is the ONLY entry point the transport thread uses. It emits
  a queued ``pyqtSignal`` so the request is appended to a FIFO on the GUI
  thread; the slot only enqueues and schedules a zero-delay single-shot drain
  when the bridge is not busy (capture and ``set_node_title`` run nested event
  loops, so draining must never re-enter).
- Pre-dispatch guards (checked on the GUI thread, in this order):
  ``host._shell_teardown_started`` -> ``APP_SHUTTING_DOWN``;
  ``QApplication.activeModalWidget()`` / ``activePopupWidget()`` ->
  ``APP_BUSY_MODAL`` (retryable); ``document_io_active()`` and
  ``op.mutates_graph`` -> ``APP_BUSY``.
- A watchdog ``QTimer`` runs during each op; if an unexpected ``QDialog``
  becomes the active modal widget it is rejected and the op fails with
  ``UNEXPECTED_DIALOG`` (even when the handler itself already finished).
- ``execute_op`` (dispatch.py) does validation + grouped history + error
  translation. A ``Deferred`` result is polled every ``poll_interval_s`` while
  the bridge is *not* busy, so ``run.control(stop)`` can interleave with a
  pending ``run.status(wait=true)``; ``timeout_s`` -> ``on_timeout()`` or
  ``TIMEOUT``. Every pending ``Deferred`` is polled in FIFO order on each
  tick, each against its own deadline
  ``min(deferred.timeout_s, request.timeout_s or inf)``.
- Requests carry ``timeout_s``; synchronous ops that exceed it still complete
  (we never kill GUI work). A request whose ``timeout_s`` already elapsed while
  it sat in the queue (the client has given up) is not executed and fails with
  ``TIMEOUT`` instead.
- ``shutdown()`` fails every queued request and pending ``Deferred`` with
  ``APP_SHUTTING_DOWN``, stops the timers, and makes later ``submit`` calls
  fail immediately. An op that is executing when ``shutdown()`` runs (from a
  nested event loop) still resolves with its real outcome.

Every Qt slot in this module is exception-safe: an unhandled exception in a
slot would abort the process under PyQt6.
"""

from __future__ import annotations

import logging
import math
import time
from collections import deque
from collections.abc import Mapping
from concurrent.futures import Future, InvalidStateError
from dataclasses import dataclass
from typing import Any

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication, QDialog, QWidget

from ea_node_editor.automation.errors import (
    APP_BUSY,
    APP_BUSY_MODAL,
    APP_SHUTTING_DOWN,
    INTERNAL,
    TIMEOUT,
    UNEXPECTED_DIALOG,
    AutomationOpError,
)
from ea_node_editor.automation.op_catalog import op_or_none
from ea_node_editor.automation.op_model import Deferred
from ea_node_editor.automation.protocol import AutomationRequest, AutomationResponse
from ea_node_editor.ui.shell.automation.context import AutomationContext
from ea_node_editor.ui.shell.automation.dispatch import HandlerTable, execute_op

logger = logging.getLogger(__name__)

WATCHDOG_INTERVAL_MS = 50
_MIN_POLL_INTERVAL_MS = 1


@dataclass(slots=True)
class _QueuedRequest:
    request: AutomationRequest
    future: "Future[AutomationResponse]"
    submitted_at: float


@dataclass(slots=True)
class _PendingDeferred:
    request: AutomationRequest
    future: "Future[AutomationResponse]"
    deferred: Deferred
    deadline: float
    limit_s: float


def _resolve(future: "Future[AutomationResponse]", response: AutomationResponse) -> None:
    """Set ``response`` on ``future`` unless the transport already gave up on it."""
    if future.done():
        return
    try:
        future.set_result(response)
    except InvalidStateError:
        pass


def _shutting_down(request_id: str, message: str = "COREX is shutting down.") -> AutomationResponse:
    return AutomationResponse.failure(request_id, AutomationOpError(APP_SHUTTING_DOWN, message))


def _widget_label(widget: QWidget) -> str:
    title = str(widget.windowTitle() or "").strip()
    if title:
        return title
    name = str(widget.objectName() or "").strip()
    return name or type(widget).__name__


class _DialogWatchdog:
    """Rejects any ``QDialog`` that becomes the active modal widget while an op runs."""

    def __init__(self, owner: QObject) -> None:
        self._timer = QTimer(owner)
        self._timer.setInterval(WATCHDOG_INTERVAL_MS)
        self._timer.timeout.connect(self._on_tick)
        self._baseline: QWidget | None = None
        self._rejected: list[str] = []
        self._seen: set[int] = set()
        self._active = False

    def start(self) -> None:
        self._baseline = QApplication.activeModalWidget()
        self._rejected = []
        self._seen = set()
        self._active = True
        self._timer.start()

    def stop(self) -> list[str]:
        """Stop the timer, do a final sweep, and return the titles of rejected dialogs."""
        self._timer.stop()
        if self._active:
            self.sweep()
        self._active = False
        self._baseline = None
        return list(self._rejected)

    def halt(self) -> None:
        """Stop without sweeping (bridge shutdown)."""
        self._active = False
        try:
            self._timer.stop()
        except RuntimeError:  # the owning QObject is already gone
            pass

    def sweep(self) -> None:
        if not self._active:
            return
        modal = QApplication.activeModalWidget()
        if modal is None or modal is self._baseline or not isinstance(modal, QDialog):
            return
        key = id(modal)
        if key in self._seen:
            return
        self._seen.add(key)
        label = _widget_label(modal)
        self._rejected.append(label)
        logger.warning("automation: rejecting unexpected dialog %r opened during an automation op", label)
        modal.reject()

    def _on_tick(self) -> None:
        try:
            self.sweep()
        except Exception:  # noqa: BLE001 - a slot must never raise under PyQt6
            logger.exception("automation dialog watchdog failed")


# Read-only ops that never open dialogs and that agents use to *see* a busy app
# (``app.status`` reports ``busy.modal_dialog``); everything else waits for the dialog.
MODAL_EXEMPT_OPS: frozenset[str] = frozenset({"app.status"})


class AutomationBridge(QObject):
    """Serialises automation requests onto the GUI thread (see module docstring)."""

    _request_queued = pyqtSignal(object)

    def __init__(self, context: AutomationContext, handlers: HandlerTable, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._context = context
        self._handlers = dict(handlers)
        self._queue: deque[_QueuedRequest] = deque()
        self._deferreds: deque[_PendingDeferred] = deque()
        self._busy = False
        self._closed = False
        self._drain_timer = QTimer(self)
        self._drain_timer.setSingleShot(True)
        self._drain_timer.setInterval(0)
        self._drain_timer.timeout.connect(self._drain)
        self._deferred_timer = QTimer(self)
        self._deferred_timer.timeout.connect(self._poll_deferreds)
        self._watchdog = _DialogWatchdog(self)
        self._request_queued.connect(self._enqueue, Qt.ConnectionType.QueuedConnection)

    # ------------------------------------------------------------- properties

    @property
    def context(self) -> AutomationContext:
        return self._context

    @property
    def busy(self) -> bool:
        return self._busy

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def queue_length(self) -> int:
        return len(self._queue)

    @property
    def pending_deferred(self) -> bool:
        return bool(self._deferreds)

    # ------------------------------------------------------- transport entry

    def submit(self, request: AutomationRequest) -> "Future[AutomationResponse]":
        """Thread-safe: hand ``request`` to the GUI thread and return its Future."""
        future: Future[AutomationResponse] = Future()
        if self._closed:
            _resolve(future, _shutting_down(request.id, "The automation bridge is closed."))
            return future
        self._request_queued.emit(_QueuedRequest(request, future, time.monotonic()))
        return future

    def shutdown(self) -> None:
        """Fail everything queued or pending with APP_SHUTTING_DOWN and stop the timers."""
        if self._closed:
            return
        self._closed = True
        queued = list(self._queue)
        self._queue.clear()
        pending = list(self._deferreds)
        self._deferreds.clear()
        for item in queued:
            _resolve(item.future, _shutting_down(item.request.id))
        for entry in pending:
            _resolve(entry.future, _shutting_down(entry.request.id))
        self._watchdog.halt()
        for timer in (self._drain_timer, self._deferred_timer):
            try:
                timer.stop()
            except RuntimeError:  # C++ side already deleted with the parent window
                pass

    # ------------------------------------------------------------ GUI thread

    def _enqueue(self, item: Any) -> None:
        try:
            if self._closed:
                _resolve(item.future, _shutting_down(item.request.id))
                return
            self._queue.append(item)
            self._schedule_drain()
        except Exception:  # noqa: BLE001 - a slot must never raise under PyQt6
            logger.exception("automation bridge failed to enqueue a request")

    def _schedule_drain(self) -> None:
        if self._closed or self._busy or not self._queue or self._drain_timer.isActive():
            return
        self._drain_timer.start()

    def _drain(self) -> None:
        """Run exactly one queued request, then yield to the event loop."""
        try:
            if self._closed or self._busy or not self._queue:
                return
            item = self._queue.popleft()
            if not item.future.set_running_or_notify_cancel():
                # The transport cancelled the Future while it waited in the queue.
                self._schedule_drain()
                return
            self._busy = True
            try:
                response = self._execute(item)
            except Exception as exc:  # noqa: BLE001 - never leave a transport thread parked on the Future
                logger.exception("automation bridge failed to execute %s", item.request.op)
                response = AutomationResponse.failure(item.request.id, self._internal(item.request.op, "dispatch", exc))
            finally:
                self._busy = False
            if response is not None:
                _resolve(item.future, response)
            if self._closed:
                # shutdown() ran inside the handler (nested loop): nothing may outlive it.
                self._fail_pending_deferreds()
                return
            self._schedule_drain()
            self._sync_deferred_timer()
        except Exception:  # noqa: BLE001 - a slot must never raise under PyQt6
            logger.exception("automation bridge drain failed")
            self._busy = False

    def _execute(self, item: _QueuedRequest) -> AutomationResponse | None:
        """Guards + dispatch for one request. ``None`` means a Deferred was registered."""
        request = item.request
        guard_error = self._guard(item)
        if guard_error is not None:
            return AutomationResponse.failure(request.id, guard_error)
        outcome: AutomationResponse | None = None
        deferred: Deferred | None = None
        handler_error: AutomationOpError | None = None
        self._watchdog.start()
        try:
            result = execute_op(self._context, self._handlers, request.op, request.params)
        except AutomationOpError as exc:
            handler_error = exc
        except Exception as exc:  # noqa: BLE001 - execute_op translates; this is the last line of defence
            logger.exception("automation op %s escaped dispatch translation", request.op)
            handler_error = AutomationOpError(
                INTERNAL,
                f"{request.op} raised {type(exc).__name__}: {exc}",
                details={"op": request.op, "exception": type(exc).__name__},
            )
        else:
            if isinstance(result, Deferred):
                deferred = result
            else:
                outcome = AutomationResponse.success(request.id, result)
        finally:
            rejected = self._watchdog.stop()
        if rejected:
            return AutomationResponse.failure(
                request.id,
                AutomationOpError(
                    UNEXPECTED_DIALOG,
                    f"{request.op} opened an unexpected dialog ({', '.join(rejected)}); it was dismissed.",
                    details={
                        "op": request.op,
                        "dialogs": list(rejected),
                        "handler_completed": handler_error is None,
                        "handler_error": handler_error.code if handler_error is not None else "",
                    },
                ),
            )
        if handler_error is not None:
            return AutomationResponse.failure(request.id, handler_error)
        if deferred is not None:
            self._register_deferred(item, deferred)
            return None
        return outcome

    def _guard(self, item: _QueuedRequest) -> AutomationOpError | None:
        request = item.request
        host = self._context.host
        if host is not None and host._shell_teardown_started:
            return AutomationOpError(APP_SHUTTING_DOWN, "COREX is shutting down.", details={"op": request.op})
        blocker = None
        modal = None
        if request.op not in MODAL_EXEMPT_OPS:
            modal = QApplication.activeModalWidget()
            popup = QApplication.activePopupWidget() if modal is None else None
            blocker = modal if modal is not None else popup
        if blocker is not None:
            kind = "modal dialog" if modal is not None else "popup"
            return AutomationOpError(
                APP_BUSY_MODAL,
                f"A {kind} is open in the COREX window: {_widget_label(blocker)}.",
                details={
                    "op": request.op,
                    "kind": "modal" if modal is not None else "popup",
                    "widget": type(blocker).__name__,
                    "title": str(blocker.windowTitle() or ""),
                },
                retryable=True,
            )
        spec = op_or_none(request.op)
        if spec is not None and spec.mutates_graph:
            session = self._context.project_session
            if session is not None and session.document_io_active():
                return AutomationOpError(
                    APP_BUSY,
                    "COREX is saving or loading a project document.",
                    details={"op": request.op, "reason": "document_io"},
                )
        timeout_s = float(request.timeout_s or 0.0)
        if timeout_s > 0:
            waited = time.monotonic() - item.submitted_at
            if waited > timeout_s:
                return AutomationOpError(
                    TIMEOUT,
                    f"{request.op} waited {waited:.1f}s in the queue, longer than its timeout_s={timeout_s:g}; "
                    "it was not executed.",
                    details={"op": request.op, "queued_s": round(waited, 3), "timeout_s": timeout_s, "executed": False},
                )
        return None

    # --------------------------------------------------------------- deferred

    def _register_deferred(self, item: _QueuedRequest, deferred: Deferred) -> None:
        limit = float(deferred.timeout_s)
        request_timeout = float(item.request.timeout_s or 0.0)
        if request_timeout > 0:
            limit = min(limit, request_timeout)
        if math.isnan(limit) or limit < 0:
            limit = 0.0
        deadline = time.monotonic() + limit if not math.isinf(limit) else math.inf
        self._deferreds.append(_PendingDeferred(item.request, item.future, deferred, deadline, limit))
        self._sync_deferred_timer()

    def _sync_deferred_timer(self) -> None:
        if self._closed or not self._deferreds:
            self._deferred_timer.stop()
            return
        shortest = min(float(entry.deferred.poll_interval_s or 0.0) for entry in self._deferreds)
        interval_ms = max(_MIN_POLL_INTERVAL_MS, int(round(shortest * 1000.0)))
        if not self._deferred_timer.isActive() or self._deferred_timer.interval() != interval_ms:
            self._deferred_timer.start(interval_ms)

    def _poll_deferreds(self) -> None:
        try:
            if self._closed or self._busy or not self._deferreds:
                return
            self._busy = True
            try:
                for entry in list(self._deferreds):
                    if entry not in self._deferreds:  # shutdown() ran inside a poll
                        break
                    response = self._poll_one(entry)
                    if response is None:
                        continue
                    self._deferreds.remove(entry)
                    _resolve(entry.future, response)
            finally:
                self._busy = False
            self._sync_deferred_timer()
            self._schedule_drain()
        except Exception:  # noqa: BLE001 - a slot must never raise under PyQt6
            logger.exception("automation bridge deferred poll failed")
            self._busy = False

    def _poll_one(self, entry: _PendingDeferred) -> AutomationResponse | None:
        request = entry.request
        deferred = entry.deferred
        try:
            outcome = deferred.poll()
        except AutomationOpError as exc:
            return AutomationResponse.failure(request.id, exc)
        except Exception as exc:  # noqa: BLE001 - translated into the frozen envelope
            logger.exception("automation deferred op %s poll failed", request.op)
            return AutomationResponse.failure(request.id, self._internal(request.op, "poll", exc))
        if outcome is not None:
            return self._result_response(request, outcome, "poll")
        if time.monotonic() < entry.deadline:
            return None
        if deferred.on_timeout is None:
            return AutomationResponse.failure(
                request.id,
                AutomationOpError(
                    TIMEOUT,
                    f"{request.op} did not complete within {entry.limit_s:g}s.",
                    details={"op": request.op, "timeout_s": entry.limit_s, "label": str(deferred.label or "")},
                ),
            )
        try:
            fallback = deferred.on_timeout()
        except AutomationOpError as exc:
            return AutomationResponse.failure(request.id, exc)
        except Exception as exc:  # noqa: BLE001 - translated into the frozen envelope
            logger.exception("automation deferred op %s on_timeout failed", request.op)
            return AutomationResponse.failure(request.id, self._internal(request.op, "on_timeout", exc))
        return self._result_response(request, fallback, "on_timeout")

    def _fail_pending_deferreds(self) -> None:
        pending = list(self._deferreds)
        self._deferreds.clear()
        for entry in pending:
            _resolve(entry.future, _shutting_down(entry.request.id))

    @staticmethod
    def _result_response(request: AutomationRequest, value: Any, stage: str) -> AutomationResponse:
        if not isinstance(value, Mapping):
            return AutomationResponse.failure(
                request.id,
                AutomationOpError(
                    INTERNAL,
                    f"{request.op} {stage} returned {type(value).__name__} instead of a result object.",
                    details={"op": request.op, "stage": stage},
                ),
            )
        return AutomationResponse.success(request.id, value)

    @staticmethod
    def _internal(op: str, stage: str, exc: BaseException) -> AutomationOpError:
        return AutomationOpError(
            INTERNAL,
            f"{op} {stage} raised {type(exc).__name__}: {exc}",
            details={"op": op, "stage": stage, "exception": type(exc).__name__},
        )


__all__ = ["AutomationBridge", "WATCHDOG_INTERVAL_MS"]
