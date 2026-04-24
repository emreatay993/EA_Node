from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, Qt, QUrl, pyqtProperty
from PyQt6.QtQml import QQmlContext
from PyQt6.QtQuickWidgets import QQuickWidget

from ea_node_editor.ui.icon_registry import UI_ICON_PROVIDER_ID
from ea_node_editor.ui.media_preview_provider import (
    LOCAL_MEDIA_PREVIEW_PROVIDER_ID,
)
from ea_node_editor.ui.pdf_preview_provider import (
    LOCAL_PDF_PREVIEW_PROVIDER_ID,
)
if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow


ShellContextPropertyBindings = tuple[tuple[str, object], ...]


class ShellContextBundle(QObject):
    def __init__(
        self,
        *,
        shell_library_bridge: QObject,
        shell_workspace_bridge: QObject,
        shell_inspector_bridge: QObject,
        addon_manager_bridge: QObject,
        graph_action_bridge: QObject,
        graph_canvas_state_bridge: QObject,
        graph_canvas_command_bridge: QObject,
        graph_canvas_view_bridge: QObject,
        content_fullscreen_bridge: QObject,
        viewer_session_bridge: QObject,
        viewer_host_service: QObject,
        script_editor_bridge: QObject,
        script_highlighter_bridge: QObject,
        theme_bridge: QObject,
        graph_theme_bridge: QObject,
        ui_icons: QObject,
        status_engine: QObject,
        status_jobs: QObject,
        status_metrics: QObject,
        status_notifications: QObject,
        help_bridge: QObject,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._shell_library_bridge = shell_library_bridge
        self._shell_workspace_bridge = shell_workspace_bridge
        self._shell_inspector_bridge = shell_inspector_bridge
        self._addon_manager_bridge = addon_manager_bridge
        self._graph_action_bridge = graph_action_bridge
        self._graph_canvas_state_bridge = graph_canvas_state_bridge
        self._graph_canvas_command_bridge = graph_canvas_command_bridge
        self._graph_canvas_view_bridge = graph_canvas_view_bridge
        self._content_fullscreen_bridge = content_fullscreen_bridge
        self._viewer_session_bridge = viewer_session_bridge
        self._viewer_host_service = viewer_host_service
        self._script_editor_bridge = script_editor_bridge
        self._script_highlighter_bridge = script_highlighter_bridge
        self._theme_bridge = theme_bridge
        self._graph_theme_bridge = graph_theme_bridge
        self._ui_icons = ui_icons
        self._status_engine = status_engine
        self._status_jobs = status_jobs
        self._status_metrics = status_metrics
        self._status_notifications = status_notifications
        self._help_bridge = help_bridge

    @pyqtProperty(QObject, constant=True)
    def shellLibraryBridge(self) -> QObject:
        return self._shell_library_bridge

    @pyqtProperty(QObject, constant=True)
    def shellWorkspaceBridge(self) -> QObject:
        return self._shell_workspace_bridge

    @pyqtProperty(QObject, constant=True)
    def shellInspectorBridge(self) -> QObject:
        return self._shell_inspector_bridge

    @pyqtProperty(QObject, constant=True)
    def addonManagerBridge(self) -> QObject:
        return self._addon_manager_bridge

    @pyqtProperty(QObject, constant=True)
    def graphActionBridge(self) -> QObject:
        return self._graph_action_bridge

    @pyqtProperty(QObject, constant=True)
    def graphCanvasStateBridge(self) -> QObject:
        return self._graph_canvas_state_bridge

    @pyqtProperty(QObject, constant=True)
    def graphCanvasCommandBridge(self) -> QObject:
        return self._graph_canvas_command_bridge

    @pyqtProperty(QObject, constant=True)
    def graphCanvasViewBridge(self) -> QObject:
        return self._graph_canvas_view_bridge

    @pyqtProperty(QObject, constant=True)
    def contentFullscreenBridge(self) -> QObject:
        return self._content_fullscreen_bridge

    @pyqtProperty(QObject, constant=True)
    def viewerSessionBridge(self) -> QObject:
        return self._viewer_session_bridge

    @pyqtProperty(QObject, constant=True)
    def viewerHostService(self) -> QObject:
        return self._viewer_host_service

    @pyqtProperty(QObject, constant=True)
    def scriptEditorBridge(self) -> QObject:
        return self._script_editor_bridge

    @pyqtProperty(QObject, constant=True)
    def scriptHighlighterBridge(self) -> QObject:
        return self._script_highlighter_bridge

    @pyqtProperty(QObject, constant=True)
    def themeBridge(self) -> QObject:
        return self._theme_bridge

    @pyqtProperty(QObject, constant=True)
    def graphThemeBridge(self) -> QObject:
        return self._graph_theme_bridge

    @pyqtProperty(QObject, constant=True)
    def uiIcons(self) -> QObject:
        return self._ui_icons

    @pyqtProperty(QObject, constant=True)
    def statusEngine(self) -> QObject:
        return self._status_engine

    @pyqtProperty(QObject, constant=True)
    def statusJobs(self) -> QObject:
        return self._status_jobs

    @pyqtProperty(QObject, constant=True)
    def statusMetrics(self) -> QObject:
        return self._status_metrics

    @pyqtProperty(QObject, constant=True)
    def statusNotifications(self) -> QObject:
        return self._status_notifications

    @pyqtProperty(QObject, constant=True)
    def helpBridge(self) -> QObject:
        return self._help_bridge


def _register_image_providers(host: "ShellWindow", quick_widget: QQuickWidget) -> None:
    engine = quick_widget.engine()
    engine.addImageProvider(UI_ICON_PROVIDER_ID, host._ui_icon_image_provider)
    engine.addImageProvider(
        LOCAL_MEDIA_PREVIEW_PROVIDER_ID,
        host._local_media_preview_provider,
    )
    engine.addImageProvider(
        LOCAL_PDF_PREVIEW_PROVIDER_ID,
        host._local_pdf_preview_provider,
    )


def _register_context_properties(
    context: QQmlContext,
    context_property_bindings: ShellContextPropertyBindings,
) -> None:
    for name, value in context_property_bindings:
        context.setContextProperty(name, value)


def _main_shell_qml_path() -> Path:
    return Path(__file__).resolve().parent / "MainShell.qml"


def main_shell_qml_url() -> QUrl:
    return QUrl.fromLocalFile(str(_main_shell_qml_path()))


def _connect_after_render_callback(host: "ShellWindow", quick_widget: QQuickWidget) -> None:
    quick_window = quick_widget.quickWindow()
    if quick_window is not None:
        quick_window.afterRendering.connect(
            host._record_render_frame,
            Qt.ConnectionType.QueuedConnection,
        )


def bootstrap_shell_qml_context(
    host: "ShellWindow",
    quick_widget: QQuickWidget,
    context_property_bindings: ShellContextPropertyBindings,
) -> None:
    quick_widget.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
    _register_image_providers(host, quick_widget)
    _register_context_properties(quick_widget.rootContext(), context_property_bindings)
    quick_widget.setSource(main_shell_qml_url())
    _connect_after_render_callback(host, quick_widget)


__all__ = [
    "ShellContextBundle",
    "ShellContextPropertyBindings",
    "bootstrap_shell_qml_context",
    "main_shell_qml_url",
]
