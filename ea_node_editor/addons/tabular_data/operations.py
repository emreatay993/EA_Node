# Purpose: Propagate cooperative cancellation through tabular backend operations.
# Map: feature_routes/tabular_data_addon_preview.md
# Tests: tests/test_tabular_composer_session.py
from contextlib import contextmanager
from contextvars import ContextVar
from threading import Event

_cancel_event: ContextVar[Event | None] = ContextVar("tabular_cancel_event", default=None)


def current_cancel_event() -> Event | None:
    return _cancel_event.get()


def check_cancelled() -> None:
    event = current_cancel_event()
    if event is not None and event.is_set():
        raise InterruptedError("Tabular operation cancelled")


@contextmanager
def tabular_operation(event: Event):
    token = _cancel_event.set(event)
    try:
        check_cancelled()
        yield
    finally:
        _cancel_event.reset(token)
