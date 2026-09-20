# Purpose: Gate native presentation changes on painted QML previews and canvas geometry.
# Map: subsystems/viewer_surfaces.md
# Tests: tests/test_native_presentation_handoff.py
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PyQt6.QtCore import QObject, QTimer


NativePresentationKey = tuple[str, str]


@dataclass(slots=True)
class _PendingPreviewSwap:
    expected_source: str
    serial: int
    armed: bool = False


class NativePresentationHandoff:
    """Gate native presentation changes until the supporting QML frame is painted."""

    def __init__(
        self,
        *,
        overlay_manager_provider: Callable[[], Any],
        completion_callback: Callable[[NativePresentationKey], None],
        timeout_ms: int | None,
        timeout_callback: Callable[[NativePresentationKey], None] | None = None,
    ) -> None:
        self._overlay_manager_provider: Callable[[], Any] | None = (
            overlay_manager_provider
        )
        self._completion_callback: Callable[[NativePresentationKey], None] | None = (
            completion_callback
        )
        self._timeout_ms = None if timeout_ms is None else max(0, int(timeout_ms))
        self._timeout_callback = timeout_callback
        self._pending: dict[NativePresentationKey, _PendingPreviewSwap] = {}
        self._serial = 0
        self._render_gate_window: QObject | None = None
        self._shutdown = False

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    @property
    def serial(self) -> int:
        return self._serial

    @property
    def render_gate_connected(self) -> bool:
        return self._render_gate_window is not None

    def contains(self, key: NativePresentationKey) -> bool:
        return key in self._pending

    def pending_serial(self, key: NativePresentationKey) -> int:
        pending = self._pending.get(key)
        return pending.serial if pending is not None else 0

    def expected_source(self, key: NativePresentationKey) -> str:
        pending = self._pending.get(key)
        return pending.expected_source if pending is not None else ""

    def is_armed(self, key: NativePresentationKey) -> bool:
        pending = self._pending.get(key)
        return bool(pending is not None and pending.armed)

    def begin(self, key: NativePresentationKey, *, expected_source: str) -> bool:
        if self._shutdown:
            return False
        normalized_source = str(expected_source or "").strip()
        if not normalized_source:
            return False
        self._serial += 1
        serial = self._serial
        self._pending[key] = _PendingPreviewSwap(
            expected_source=normalized_source,
            serial=serial,
        )
        if self._timeout_ms is not None:
            QTimer.singleShot(
                self._timeout_ms,
                lambda key=key, serial=serial: self._expire(key, serial),
            )
        return True

    def wait_for_render(self, key: NativePresentationKey) -> None:
        """Wait for canvas geometry to paint when its preview source is unchanged."""
        if self.begin(key, expected_source="canvas-geometry"):
            self.notify_preview_swapped(key, "canvas-geometry")

    def notify_preview_swapped(
        self,
        key: NativePresentationKey,
        source: str,
    ) -> None:
        if self._shutdown:
            return
        pending = self._pending.get(key)
        if pending is None or pending.armed:
            return
        if str(source or "").strip() != pending.expected_source:
            return
        pending.armed = True
        if not self._connect_render_gate():
            self._queue_armed_completion()

    def cancel(self, key: NativePresentationKey) -> None:
        self._pending.pop(key, None)
        self._disconnect_render_gate_if_idle()

    def flush(self) -> None:
        for key in list(self._pending):
            self._complete(key)

    def shutdown(self) -> None:
        if self._shutdown:
            return
        self._shutdown = True
        self._pending.clear()
        self._disconnect_render_gate()
        self._overlay_manager_provider = None
        self._completion_callback = None
        self._timeout_callback = None

    def _expire(self, key: NativePresentationKey, serial: int) -> None:
        pending = self._pending.get(key)
        if pending is None or pending.serial != serial:
            return
        self._complete(key, timed_out=True)

    def _complete(self, key: NativePresentationKey, *, timed_out: bool = False) -> None:
        if self._pending.pop(key, None) is None:
            return
        self._disconnect_render_gate_if_idle()
        if self._shutdown:
            return
        callback = self._timeout_callback if timed_out and self._timeout_callback else self._completion_callback
        if callback is not None:
            callback(key)

    def _queue_armed_completion(self) -> None:
        rendered = tuple(
            (key, pending.serial) for key, pending in self._pending.items() if pending.armed
        )
        QTimer.singleShot(0, lambda: self._complete_rendered(rendered))

    def _complete_rendered(self, rendered: tuple[tuple[NativePresentationKey, int], ...]) -> None:
        if not any(
            (pending := self._pending.get(key)) is not None
            and pending.serial == serial and pending.armed
            for key, serial in rendered
        ):
            return
        # QQuickWidget renders into a texture before its QWidget backing store
        # is painted. Present that texture while the native overlay still
        # covers it; otherwise hiding the overlay can expose an older/empty
        # backing-store frame. This runs on the queued GUI callback, never
        # within the scene graph's render callback.
        provider = self._overlay_manager_provider
        manager = provider() if provider is not None else None
        quick_widget = getattr(manager, "quick_widget", None)
        repaint = getattr(quick_widget, "repaint", None)
        if callable(repaint):
            repaint()
        for key, serial in rendered:
            pending = self._pending.get(key)
            if pending is not None and pending.serial == serial and pending.armed:
                self._complete(key)

    def _render_gate_source_window(self) -> QObject | None:
        provider = self._overlay_manager_provider
        overlay_manager = provider() if provider is not None else None
        quick_widget = (
            getattr(overlay_manager, "quick_widget", None)
            if overlay_manager is not None
            else None
        )
        root_object = getattr(quick_widget, "rootObject", None)
        root_item = root_object() if callable(root_object) else None
        window_getter = getattr(root_item, "window", None)
        window = window_getter() if callable(window_getter) else None
        return window if isinstance(window, QObject) else None

    def _connect_render_gate(self) -> bool:
        if self._render_gate_window is not None:
            return True
        window = self._render_gate_source_window()
        signal = getattr(window, "afterRendering", None) if window is not None else None
        if signal is None or not hasattr(signal, "connect"):
            return False
        try:
            signal.connect(self._on_render_gate_frame)
        except (TypeError, RuntimeError):
            return False
        self._render_gate_window = window
        return True

    def _on_render_gate_frame(self) -> None:
        # Never mutate host or overlay state inside the render callback.
        self._disconnect_render_gate()
        self._queue_armed_completion()

    def _disconnect_render_gate(self) -> None:
        window = self._render_gate_window
        self._render_gate_window = None
        if window is None:
            return
        signal = getattr(window, "afterRendering", None)
        if signal is None:
            return
        try:
            signal.disconnect(self._on_render_gate_frame)
        except (TypeError, RuntimeError):
            pass

    def _disconnect_render_gate_if_idle(self) -> None:
        if any(pending.armed for pending in self._pending.values()):
            return
        self._disconnect_render_gate()


__all__ = ["NativePresentationHandoff", "NativePresentationKey"]
