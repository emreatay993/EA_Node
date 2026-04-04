from __future__ import annotations

import gc
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from unittest.mock import patch

from PyQt6.QtCore import QEvent, QUrl
from PyQt6.QtQuickWidgets import QQuickWidget
from PyQt6.QtWidgets import QApplication

from ea_node_editor.ui.shell.composition import create_shell_window
from ea_node_editor.ui.shell.window import ShellWindow
from tests.conftest import ShellTestEnvironment


class _ShellTestExecutionClient:
    def __init__(self) -> None:
        self._callbacks: list[object] = []

    def subscribe(self, callback) -> None:  # noqa: ANN001
        self._callbacks.append(callback)

    def shutdown(self) -> None:
        self._callbacks.clear()


def _flush_shell_qt_events(app: QApplication) -> None:
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


@contextmanager
def _shell_lifecycle_context() -> Iterator[QApplication]:
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    env = ShellTestEnvironment()
    env.start()
    execution_client_patch = patch(
        "ea_node_editor.ui.shell.window.ProcessExecutionClient",
        _ShellTestExecutionClient,
    )
    execution_client_patch.start()
    try:
        yield app
    finally:
        _flush_shell_qt_events(app)
        execution_client_patch.stop()
        env.stop()
        gc.collect()


def _build_window_via_constructor() -> ShellWindow:
    return ShellWindow()


def _build_window_via_factory() -> ShellWindow:
    return create_shell_window()


def _create_window(app: QApplication, factory: Callable[[], ShellWindow]) -> ShellWindow:
    window = factory()
    window.resize(1200, 800)
    window.show()
    _flush_shell_qt_events(app)
    return window


def _delete_window(window: ShellWindow, app: QApplication) -> None:
    window.deleteLater()
    _flush_shell_qt_events(app)
    gc.collect()


def test_shell_window_close_allows_repeated_in_process_cycles() -> None:
    with _shell_lifecycle_context() as app:
        for factory in (_build_window_via_constructor, _build_window_via_factory):
            for _cycle in range(3):
                window = _create_window(app, factory)
                quick_widget = getattr(window, "quick_widget", None)

                assert isinstance(quick_widget, QQuickWidget)
                assert quick_widget.rootObject() is not None
                assert not quick_widget.source().isEmpty()

                window.close()
                _flush_shell_qt_events(app)

                assert quick_widget.source() == QUrl()
                assert window.viewer_host_service.overlay_manager is None
                assert window.viewer_host_service.active_overlay_count == 0

                _delete_window(window, app)


def test_create_shell_window_factory_tracks_application_state_signal_for_teardown() -> None:
    with _shell_lifecycle_context() as app:
        window = _create_window(app, _build_window_via_factory)

        assert window._application_state_signal_connected is True

        window.close()
        _flush_shell_qt_events(app)

        assert window._application_state_signal_connected is False
        _delete_window(window, app)


def test_close_skips_deferred_autosave_recovery_after_teardown_starts() -> None:
    with _shell_lifecycle_context() as app:
        window = ShellWindow()
        window.resize(1200, 800)

        with patch.object(window, "_process_deferred_autosave_recovery") as recovery_mock:
            window._autosave_recovery_deferred = True
            window.show()
            window.close()
            _flush_shell_qt_events(app)

        recovery_mock.assert_not_called()
        _delete_window(window, app)


def test_close_releases_viewer_host_service_overlay_manager() -> None:
    with _shell_lifecycle_context() as app:
        window = _create_window(app, _build_window_via_constructor)
        host_service = window.viewer_host_service

        assert host_service.overlay_manager is window.embedded_viewer_overlay_manager

        window.close()
        _flush_shell_qt_events(app)

        assert host_service.overlay_manager is None
        assert host_service.active_overlay_count == 0
        _delete_window(window, app)
