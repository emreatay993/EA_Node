from __future__ import annotations

import gc
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtCore import QEvent, QMetaObject, QObject, Qt, QUrl
from PyQt6.QtGui import QImage
from PyQt6.QtTest import QTest
from PyQt6.QtQuickWidgets import QQuickWidget
from PyQt6.QtWidgets import QApplication

from ea_node_editor.nodes.builtins.passive_media import (
    PASSIVE_MEDIA_IMAGE_PANEL_TYPE_ID,
    PASSIVE_MEDIA_PDF_PANEL_TYPE_ID,
)
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
        "ea_node_editor.ui.shell.composition.ProcessExecutionClient",
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


def _find_child(root: QObject, object_name: str) -> QObject:
    child = root.findChild(QObject, object_name)
    if child is None:
        raise AssertionError(f"Expected QML object {object_name!r}")
    return child


def _qurl_text(value: object) -> str:
    to_string = getattr(value, "toString", None)
    if callable(to_string):
        return str(to_string())
    return str(value)


def _write_test_image(path: Path, color: int = 0xFF4C7BC0) -> None:
    image = QImage(48, 30, QImage.Format.Format_ARGB32)
    image.fill(color)
    assert image.save(str(path))


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


def test_content_fullscreen_bridge_closes_during_project_reset_lifecycle() -> None:
    with _shell_lifecycle_context() as app:
        window = _create_window(app, _build_window_via_constructor)
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "content-fullscreen-lifecycle.png"
            image = QImage(24, 18, QImage.Format.Format_ARGB32)
            image.fill(0xFF4C7BC0)
            assert image.save(str(image_path))

            node_id = window.scene.add_node_from_type(PASSIVE_MEDIA_IMAGE_PANEL_TYPE_ID, x=120.0, y=80.0)
            window.scene.set_node_property(node_id, "source_path", str(image_path))
            _flush_shell_qt_events(app)

            bridge = window.content_fullscreen_bridge
            assert bridge.request_open_node(node_id)
            assert bridge.open

            window._new_project()
            _flush_shell_qt_events(app)

            assert not bridge.open
            assert bridge.node_id == ""
            assert bridge.media_payload == {}

        window.close()
        _flush_shell_qt_events(app)
        _delete_window(window, app)


def test_content_fullscreen_overlay_renders_image_media_and_keeps_node_state_read_only() -> None:
    with _shell_lifecycle_context() as app:
        window = _create_window(app, _build_window_via_constructor)
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "content-fullscreen-overlay.png"
            _write_test_image(image_path)

            node_id = window.scene.add_node_from_type(PASSIVE_MEDIA_IMAGE_PANEL_TYPE_ID, x=120.0, y=80.0)
            window.scene.set_node_properties(
                node_id,
                {
                    "source_path": str(image_path),
                    "fit_mode": "cover",
                    "caption": "Fullscreen overlay caption",
                    "crop_x": 0.2,
                    "crop_y": 0.1,
                    "crop_w": 0.5,
                    "crop_h": 0.6,
                },
            )
            _flush_shell_qt_events(app)

            workspace = window.model.project.workspaces[window.workspace_manager.active_workspace_id()]
            before_state = workspace.nodes[node_id].properties.copy()
            bridge = window.content_fullscreen_bridge
            assert bridge.request_open_node(node_id)
            _flush_shell_qt_events(app)

            root = window.quick_widget.rootObject()
            assert root is not None
            overlay = _find_child(root, "contentFullscreenOverlay")
            media_image = _find_child(root, "contentFullscreenMediaImage")
            caption = _find_child(root, "contentFullscreenCaptionText")
            fit_button = _find_child(root, "contentFullscreenDisplayModeFitButton")
            fill_button = _find_child(root, "contentFullscreenDisplayModeFillButton")
            actual_button = _find_child(root, "contentFullscreenDisplayModeActualButton")

            assert bool(overlay.property("visible"))
            assert str(overlay.property("contentKind")) == "image"
            assert str(overlay.property("effectiveDisplayMode")) == "fill"
            assert "local-media-preview" in _qurl_text(media_image.property("source"))
            assert str(caption.property("text")) == "Fullscreen overlay caption"
            assert bool(fill_button.property("selectedStyle"))
            assert not bool(fit_button.property("selectedStyle"))

            QMetaObject.invokeMethod(actual_button, "click")
            _flush_shell_qt_events(app)

            assert str(overlay.property("effectiveDisplayMode")) == "actual"
            assert bool(actual_button.property("selectedStyle"))
            after_state = workspace.nodes[node_id].properties.copy()
            assert after_state == before_state

        window.close()
        _flush_shell_qt_events(app)
        _delete_window(window, app)


def test_content_fullscreen_overlay_renders_pdf_media_blocks_background_and_close_button() -> None:
    with _shell_lifecycle_context() as app:
        window = _create_window(app, _build_window_via_constructor)
        pdf_path = Path(__file__).resolve().parent / "fixtures" / "passive_nodes" / "reference_preview.pdf"

        node_id = window.scene.add_node_from_type(PASSIVE_MEDIA_PDF_PANEL_TYPE_ID, x=120.0, y=80.0)
        window.scene.set_node_properties(
            node_id,
            {
                "source_path": str(pdf_path),
                "page_number": 1,
                "caption": "Fullscreen PDF caption",
            },
        )
        _flush_shell_qt_events(app)

        bridge = window.content_fullscreen_bridge
        assert bridge.request_open_node(node_id)
        _flush_shell_qt_events(app)

        root = window.quick_widget.rootObject()
        assert root is not None
        overlay = _find_child(root, "contentFullscreenOverlay")
        blocker = _find_child(root, "contentFullscreenInteractionBlocker")
        media_summary = _find_child(root, "contentFullscreenMediaSummary")
        media_image = _find_child(root, "contentFullscreenMediaImage")
        caption = _find_child(root, "contentFullscreenCaptionText")
        close_button = _find_child(root, "contentFullscreenCloseButton")

        assert bool(overlay.property("visible"))
        assert str(overlay.property("contentKind")) == "pdf"
        assert bool(blocker.property("visible"))
        assert bool(blocker.property("preventStealing"))
        assert str(media_summary.property("text")) == "PDF page 1"
        assert "local-pdf-preview" in _qurl_text(media_image.property("source"))
        assert str(caption.property("text")) == "Fullscreen PDF caption"

        QTest.mouseClick(window.quick_widget, Qt.MouseButton.LeftButton, pos=window.quick_widget.rect().topLeft())
        _flush_shell_qt_events(app)
        assert bridge.open

        QMetaObject.invokeMethod(close_button, "click")
        _flush_shell_qt_events(app)
        assert not bridge.open

        window.close()
        _flush_shell_qt_events(app)
        _delete_window(window, app)


def test_content_fullscreen_overlay_closes_open_state_with_escape_and_f11() -> None:
    with _shell_lifecycle_context() as app:
        window = _create_window(app, _build_window_via_constructor)
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "content-fullscreen-shortcuts.png"
            _write_test_image(image_path, color=0xFF669933)

            node_id = window.scene.add_node_from_type(PASSIVE_MEDIA_IMAGE_PANEL_TYPE_ID, x=120.0, y=80.0)
            window.scene.set_node_property(node_id, "source_path", str(image_path))
            _flush_shell_qt_events(app)

            bridge = window.content_fullscreen_bridge
            root = window.quick_widget.rootObject()
            assert root is not None
            overlay = _find_child(root, "contentFullscreenOverlay")

            assert bridge.request_open_node(node_id)
            _flush_shell_qt_events(app)
            window.quick_widget.setFocus()
            QMetaObject.invokeMethod(overlay, "forceActiveFocus")
            QTest.keyClick(window.quick_widget, Qt.Key.Key_Escape)
            _flush_shell_qt_events(app)
            assert not bridge.open

            assert bridge.request_open_node(node_id)
            _flush_shell_qt_events(app)
            window.quick_widget.setFocus()
            QMetaObject.invokeMethod(overlay, "forceActiveFocus")
            QTest.keyClick(window.quick_widget, Qt.Key.Key_F11)
            _flush_shell_qt_events(app)
            assert not bridge.open

        window.close()
        _flush_shell_qt_events(app)
        _delete_window(window, app)


def test_content_fullscreen_overlay_exposes_viewer_viewport_placeholder_contract() -> None:
    with _shell_lifecycle_context() as app:
        window = _create_window(app, _build_window_via_constructor)

        node_id = window.scene.add_node_from_type("dpf.viewer", x=120.0, y=80.0)
        _flush_shell_qt_events(app)

        bridge = window.content_fullscreen_bridge
        assert bridge.request_open_node(node_id)
        _flush_shell_qt_events(app)

        root = window.quick_widget.rootObject()
        assert root is not None
        overlay = _find_child(root, "contentFullscreenOverlay")
        viewer_viewport = _find_child(root, "contentFullscreenViewerViewport")
        viewer_status = _find_child(root, "contentFullscreenViewerStatusText")

        assert bool(overlay.property("visible"))
        assert str(overlay.property("contentKind")) == "viewer"
        assert bool(viewer_viewport.property("visible"))
        assert "Session" in str(viewer_status.property("text"))

        window.close()
        _flush_shell_qt_events(app)
        _delete_window(window, app)
