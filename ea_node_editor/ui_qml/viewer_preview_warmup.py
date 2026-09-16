# Purpose: Pace the offscreen renders that give never-activated viewer nodes a first proxy frame.
# Map: subsystems/viewer_surfaces.md
# Tests: tests/test_viewer_preview_warmup.py

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from PyQt6.QtCore import QTimer

OverlayKey = tuple[str, str]


class ViewerPreviewWarmupQueue:
    """Render at most one warm-up preview per event-loop turn.

    A viewer node shows nothing until a live session has been entered and
    left at least once, which makes a freshly connected Model Viewer look
    broken. Warming one up means building the scene and rendering it
    offscreen, which is not free, so opening a project with several viewers
    must not do all of that work in a single blocking batch.

    The queue is deliberately dumb: callers decide which keys deserve a
    warm-up and how to render one. It only guarantees ordering, at most one
    render per turn, and that a key which stops deserving a warm-up before
    its turn arrives is dropped instead of rendered.
    """

    def __init__(
        self,
        *,
        render: Callable[[OverlayKey], None],
        still_wanted: Callable[[OverlayKey], bool],
        schedule: Callable[[Callable[[], None]], None] | None = None,
    ) -> None:
        self._render = render
        self._still_wanted = still_wanted
        self._schedule = schedule or (lambda callback: QTimer.singleShot(0, callback))
        self._queue: list[OverlayKey] = []
        self._queued: set[OverlayKey] = set()
        self._draining = False
        self._stopped = False

    @property
    def pending(self) -> tuple[OverlayKey, ...]:
        return tuple(self._queue)

    def contains(self, key: OverlayKey) -> bool:
        return key in self._queued

    def enqueue(self, keys: Iterable[OverlayKey]) -> None:
        if self._stopped:
            return
        added = False
        for key in keys:
            if key in self._queued:
                continue
            self._queue.append(key)
            self._queued.add(key)
            added = True
        if added:
            self._schedule_drain()

    def cancel(self, key: OverlayKey) -> None:
        if key not in self._queued:
            return
        self._queued.discard(key)
        self._queue = [pending for pending in self._queue if pending != key]

    def clear(self) -> None:
        self._queue.clear()
        self._queued.clear()

    def stop(self) -> None:
        self._stopped = True
        self.clear()

    def drain_one(self) -> bool:
        """Render the next deserving key. Returns whether anything rendered."""
        self._draining = False
        if self._stopped:
            return False
        rendered = False
        while self._queue:
            key = self._queue.pop(0)
            self._queued.discard(key)
            if not self._still_wanted(key):
                # It went live, changed identity, or already has a frame.
                continue
            self._render(key)
            rendered = True
            break
        if self._queue:
            self._schedule_drain()
        return rendered

    def _schedule_drain(self) -> None:
        if self._draining or self._stopped:
            return
        self._draining = True
        self._schedule(self.drain_one)


__all__ = ["OverlayKey", "ViewerPreviewWarmupQueue"]
