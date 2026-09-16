from __future__ import annotations

from collections.abc import Callable

from ea_node_editor.ui_qml.viewer_preview_warmup import ViewerPreviewWarmupQueue

A = ("ws", "node_a")
B = ("ws", "node_b")
C = ("ws", "node_c")


class _Scheduler:
    """Stand in for the event loop so drains can be stepped one at a time."""

    def __init__(self) -> None:
        self.callbacks: list[Callable[[], None]] = []

    def __call__(self, callback: Callable[[], None]) -> None:
        self.callbacks.append(callback)

    def run_next(self) -> bool:
        if not self.callbacks:
            return False
        self.callbacks.pop(0)()
        return True

    def run_all(self, limit: int = 50) -> int:
        turns = 0
        while self.callbacks and turns < limit:
            self.run_next()
            turns += 1
        return turns


def _queue(wanted: set[tuple[str, str]] | None = None):
    scheduler = _Scheduler()
    rendered: list[tuple[str, str]] = []
    allow = wanted if wanted is not None else {A, B, C}
    queue = ViewerPreviewWarmupQueue(
        render=rendered.append,
        still_wanted=lambda key: key in allow,
        schedule=scheduler,
    )
    return queue, scheduler, rendered, allow


def test_each_turn_renders_at_most_one_preview() -> None:
    """Opening several viewers must not block on one batch of renders."""
    queue, scheduler, rendered, _allow = _queue()

    queue.enqueue([A, B, C])
    assert rendered == []

    scheduler.run_next()
    assert rendered == [A]
    scheduler.run_next()
    assert rendered == [A, B]
    scheduler.run_next()
    assert rendered == [A, B, C]

    scheduler.run_all()
    assert rendered == [A, B, C]


def test_enqueue_ignores_keys_already_waiting() -> None:
    queue, scheduler, rendered, _allow = _queue()

    queue.enqueue([A, B])
    queue.enqueue([A, B, C])

    assert queue.pending == (A, B, C)
    scheduler.run_all()
    assert rendered == [A, B, C]


def test_a_key_that_stops_deserving_a_warmup_is_dropped_not_rendered() -> None:
    queue, scheduler, rendered, allow = _queue()
    queue.enqueue([A, B])

    allow.discard(A)
    scheduler.run_all()

    assert rendered == [B]


def test_cancel_removes_a_queued_key() -> None:
    queue, scheduler, rendered, _allow = _queue()
    queue.enqueue([A, B])

    queue.cancel(A)

    assert not queue.contains(A)
    scheduler.run_all()
    assert rendered == [B]


def test_stop_drops_everything_and_refuses_new_work() -> None:
    queue, scheduler, rendered, _allow = _queue()
    queue.enqueue([A, B])

    queue.stop()
    queue.enqueue([C])
    scheduler.run_all()

    assert rendered == []
    assert queue.pending == ()


def test_a_key_can_be_requeued_after_it_renders() -> None:
    queue, scheduler, rendered, _allow = _queue()
    queue.enqueue([A])
    scheduler.run_all()
    assert rendered == [A]

    queue.enqueue([A])
    scheduler.run_all()

    assert rendered == [A, A]
