# Purpose: Direct owner tests for native cached-preview render-gated handoff state.
# Map: subsystems/viewer_surfaces.md
# Tests: tests/test_native_presentation_handoff.py
from __future__ import annotations

import time

from PyQt6.QtCore import QCoreApplication, QObject, pyqtSignal

from ea_node_editor.ui_qml.native_presentation_handoff import (
    NativePresentationHandoff,
)


class _RenderWindow(QObject):
    afterRendering = pyqtSignal()


class _RootItem:
    def __init__(self, window: _RenderWindow) -> None:
        self._window = window

    def window(self) -> _RenderWindow:
        return self._window


class _QuickWidget:
    def __init__(self, window: _RenderWindow) -> None:
        self._root = _RootItem(window)

    def rootObject(self) -> _RootItem:  # noqa: N802
        return self._root


class _OverlayManager:
    def __init__(self, window: _RenderWindow) -> None:
        self.quick_widget = _QuickWidget(window)


def _process_events_until(
    app: QCoreApplication,
    predicate,  # noqa: ANN001
    *,
    timeout_seconds: float = 0.5,
) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.002)
    app.processEvents()
    return bool(predicate())


def test_expected_preview_source_completes_after_one_rendered_frame() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    window = _RenderWindow()
    manager = _OverlayManager(window)
    completed: list[tuple[str, str]] = []
    handoff = NativePresentationHandoff(
        overlay_manager_provider=lambda: manager,
        completion_callback=completed.append,
        timeout_ms=10_000,
    )
    key = ("workspace", "node")

    assert handoff.begin(key, expected_source="image://preview/current")
    handoff.notify_preview_swapped(key, "image://preview/stale")
    assert handoff.is_armed(key) is False
    assert window.receivers(window.afterRendering) == 0

    handoff.notify_preview_swapped(key, " image://preview/current ")
    handoff.notify_preview_swapped(key, "image://preview/current")
    assert handoff.is_armed(key) is True
    assert handoff.render_gate_connected is True
    assert window.receivers(window.afterRendering) == 1

    window.afterRendering.emit()
    assert completed == []
    assert handoff.render_gate_connected is False
    assert window.receivers(window.afterRendering) == 0
    app.processEvents()

    assert completed == [key]
    assert handoff.pending_count == 0


def test_stale_timeout_serial_cannot_complete_newer_pending_handoff() -> None:
    completed: list[tuple[str, str]] = []
    handoff = NativePresentationHandoff(
        overlay_manager_provider=lambda: None,
        completion_callback=completed.append,
        timeout_ms=10_000,
    )
    key = ("workspace", "node")

    assert handoff.begin(key, expected_source="image://preview/first")
    stale_serial = handoff.pending_serial(key)
    assert handoff.begin(key, expected_source="image://preview/second")
    current_serial = handoff.pending_serial(key)
    assert current_serial > stale_serial

    handoff._expire(key, stale_serial)  # noqa: SLF001
    assert handoff.contains(key)
    assert completed == []

    handoff._expire(key, current_serial)  # noqa: SLF001
    assert handoff.contains(key) is False
    assert completed == [key]


def test_queued_render_completion_cannot_complete_a_newer_armed_swap() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    window = _RenderWindow()
    manager = _OverlayManager(window)
    completed = []
    handoff = NativePresentationHandoff(
        overlay_manager_provider=lambda: manager,
        completion_callback=completed.append,
        timeout_ms=10_000,
    )
    key = ("workspace", "node")
    handoff.begin(key, expected_source="first")
    handoff.notify_preview_swapped(key, "first")
    window.afterRendering.emit()
    handoff.cancel(key)
    handoff.begin(key, expected_source="second")
    handoff.notify_preview_swapped(key, "second")
    app.processEvents()
    assert completed == []
    assert handoff.expected_source(key) == "second"
    window.afterRendering.emit()
    app.processEvents()
    assert completed == [key]


def test_timeout_uses_recovery_instead_of_claiming_a_rendered_preview() -> None:
    completed, expired = [], []
    handoff = NativePresentationHandoff(
        overlay_manager_provider=lambda: None,
        completion_callback=completed.append,
        timeout_callback=expired.append,
        timeout_ms=10_000,
    )
    key = ("workspace", "node")
    handoff.begin(key, expected_source="current")
    handoff._expire(key, handoff.pending_serial(key))
    assert completed == []
    assert expired == [key]


def test_widget_preview_is_painted_before_native_overlay_completion() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    window = _RenderWindow()
    manager = _OverlayManager(window)
    events = []
    manager.quick_widget.repaint = lambda: events.append("paint")
    handoff = NativePresentationHandoff(
        overlay_manager_provider=lambda: manager,
        completion_callback=lambda key: events.append("hide"),
        timeout_ms=10_000,
    )
    key = ("workspace", "node")
    handoff.begin(key, expected_source="current")
    handoff.notify_preview_swapped(key, "current")
    window.afterRendering.emit()
    assert events == []
    app.processEvents()
    assert events == ["paint", "hide"]


def test_widget_paint_cannot_complete_a_replacement_handoff() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    window = _RenderWindow()
    manager = _OverlayManager(window)
    completed = []
    handoff = NativePresentationHandoff(
        overlay_manager_provider=lambda: manager,
        completion_callback=completed.append,
        timeout_ms=10_000,
    )
    key = ("workspace", "node")
    def repaint():
        handoff.begin(key, expected_source="replacement")
        handoff.notify_preview_swapped(key, "replacement")
    manager.quick_widget.repaint = repaint
    handoff.begin(key, expected_source="current")
    handoff.notify_preview_swapped(key, "current")
    window.afterRendering.emit()
    app.processEvents()
    assert completed == []
    assert handoff.expected_source(key) == "replacement"
    handoff.shutdown()


def test_real_qt_timeout_completes_separate_viewer_and_plot_host_outcomes() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    viewer_outcomes: list[tuple[str, tuple[str, str]]] = []
    plot_outcomes: list[tuple[str, tuple[str, str]]] = []
    viewer_handoff = NativePresentationHandoff(
        overlay_manager_provider=lambda: None,
        completion_callback=lambda key: viewer_outcomes.append(("viewer", key)),
        timeout_ms=20,
    )
    plot_handoff = NativePresentationHandoff(
        overlay_manager_provider=lambda: None,
        completion_callback=lambda key: plot_outcomes.append(("plot", key)),
        timeout_ms=20,
    )
    viewer_key = ("workspace", "viewer-node")
    plot_key = ("workspace", "plot-node")

    assert viewer_handoff.begin(
        viewer_key, expected_source="image://viewer-preview/current"
    )
    assert plot_handoff.begin(plot_key, expected_source="image://plot-preview/current")
    assert _process_events_until(
        app,
        lambda: viewer_handoff.pending_count == 0 and plot_handoff.pending_count == 0,
    )

    assert viewer_outcomes == [("viewer", viewer_key)]
    assert plot_outcomes == [("plot", plot_key)]


def test_cancel_flush_and_shutdown_disconnect_idle_render_gate() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    window = _RenderWindow()
    manager = _OverlayManager(window)
    completed: list[tuple[str, str]] = []
    handoff = NativePresentationHandoff(
        overlay_manager_provider=lambda: manager,
        completion_callback=completed.append,
        timeout_ms=20,
    )
    first = ("workspace", "first")
    second = ("workspace", "second")
    third = ("workspace", "third")

    assert handoff.begin(first, expected_source="image://preview/first")
    handoff.notify_preview_swapped(first, "image://preview/first")
    assert handoff.render_gate_connected
    handoff.cancel(first)
    assert handoff.render_gate_connected is False
    assert completed == []
    assert (
        _process_events_until(
            app,
            lambda: False,
            timeout_seconds=0.08,
        )
        is False
    )
    assert completed == []

    assert handoff.begin(second, expected_source="image://preview/second")
    handoff.flush()
    assert completed == [second]

    assert handoff.begin(third, expected_source="image://preview/third")
    handoff.notify_preview_swapped(third, "image://preview/third")
    assert handoff.render_gate_connected
    handoff.shutdown()
    assert handoff.pending_count == 0
    assert handoff.render_gate_connected is False
    assert window.receivers(window.afterRendering) == 0
    window.afterRendering.emit()
    assert (
        _process_events_until(
            app,
            lambda: False,
            timeout_seconds=0.08,
        )
        is False
    )
    assert completed == [second]
    assert handoff.begin(third, expected_source="image://preview/new") is False


def test_viewer_and_plot_handoffs_never_share_pending_state() -> None:
    viewer_completed: list[tuple[str, str]] = []
    plot_completed: list[tuple[str, str]] = []
    viewer_handoff = NativePresentationHandoff(
        overlay_manager_provider=lambda: None,
        completion_callback=viewer_completed.append,
        timeout_ms=10_000,
    )
    plot_handoff = NativePresentationHandoff(
        overlay_manager_provider=lambda: None,
        completion_callback=plot_completed.append,
        timeout_ms=10_000,
    )
    key = ("workspace", "node")

    assert viewer_handoff is not plot_handoff
    assert viewer_handoff.begin(key, expected_source="image://viewer/current")
    assert viewer_handoff.contains(key)
    assert plot_handoff.contains(key) is False
    plot_handoff.flush()
    assert viewer_handoff.contains(key)
    assert viewer_completed == []
    assert plot_completed == []
