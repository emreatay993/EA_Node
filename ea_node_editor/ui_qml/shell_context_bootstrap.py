from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtQml import QQmlContext
from PyQt6.QtQuickWidgets import QQuickWidget

from ea_node_editor.ui.shell.context_bridges import (
    ShellContextBridges,
    create_shell_context_bridges,
)
from ea_node_editor.ui.icon_registry import UI_ICON_PROVIDER_ID
from ea_node_editor.ui.media_preview_provider import (
    LOCAL_MEDIA_PREVIEW_PROVIDER_ID,
)
from ea_node_editor.ui.pdf_preview_provider import (
    LOCAL_PDF_PREVIEW_PROVIDER_ID,
)
if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow

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
    host: "ShellWindow",
    bridges: ShellContextBridges,
) -> None:
    for name, value in shell_context_property_bindings(host, bridges):
        context.setContextProperty(name, value)


def shell_context_property_bindings(
    host: "ShellWindow",
    bridges: ShellContextBridges,
) -> tuple[tuple[str, object], ...]:
    bridge_first_bindings = (
        ("shellLibraryBridge", bridges.shell_library_bridge),
        ("shellWorkspaceBridge", bridges.shell_workspace_bridge),
        ("shellInspectorBridge", bridges.shell_inspector_bridge),
        ("graphCanvasStateBridge", bridges.graph_canvas_state_bridge),
        ("graphCanvasCommandBridge", bridges.graph_canvas_command_bridge),
        ("graphCanvasBridge", bridges.graph_canvas_bridge),
        ("viewerSessionBridge", host.viewer_session_bridge),
    )
    shared_service_bindings = (
        ("scriptEditorBridge", host.script_editor),
        ("scriptHighlighterBridge", host.script_highlighter),
        ("themeBridge", host.theme_bridge),
        ("graphThemeBridge", host.graph_theme_bridge),
        ("uiIcons", host.ui_icons),
        ("statusEngine", host.status_engine),
        ("statusJobs", host.status_jobs),
        ("statusMetrics", host.status_metrics),
        ("statusNotifications", host.status_notifications),
    )
    deferred_compatibility_bindings = (
        ("consoleBridge", host.console_panel),
        ("workspaceTabsBridge", host.workspace_tabs),
    )
    return bridge_first_bindings + shared_service_bindings + deferred_compatibility_bindings


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
    bridges: ShellContextBridges,
) -> None:
    quick_widget.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
    _register_image_providers(host, quick_widget)
    _register_context_properties(quick_widget.rootContext(), host, bridges)
    quick_widget.setSource(main_shell_qml_url())
    _connect_after_render_callback(host, quick_widget)


__all__ = [
    "ShellContextBridges",
    "bootstrap_shell_qml_context",
    "create_shell_context_bridges",
    "main_shell_qml_url",
    "shell_context_property_bindings",
]
