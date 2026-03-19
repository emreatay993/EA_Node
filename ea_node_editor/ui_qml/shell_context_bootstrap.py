from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtQml import QQmlContext
from PyQt6.QtQuickWidgets import QQuickWidget

from ea_node_editor.ui.icon_registry import UI_ICON_PROVIDER_ID
from ea_node_editor.ui.media_preview_provider import (
    LOCAL_MEDIA_PREVIEW_PROVIDER_ID,
)
from ea_node_editor.ui.pdf_preview_provider import (
    LOCAL_PDF_PREVIEW_PROVIDER_ID,
)
from ea_node_editor.ui_qml.graph_canvas_bridge import GraphCanvasBridge
from ea_node_editor.ui_qml.graph_canvas_command_bridge import GraphCanvasCommandBridge
from ea_node_editor.ui_qml.graph_canvas_state_bridge import GraphCanvasStateBridge
from ea_node_editor.ui_qml.shell_inspector_bridge import ShellInspectorBridge
from ea_node_editor.ui_qml.shell_library_bridge import ShellLibraryBridge
from ea_node_editor.ui_qml.shell_workspace_bridge import ShellWorkspaceBridge

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow


@dataclass(frozen=True, slots=True)
class ShellContextBridges:
    shell_library_bridge: ShellLibraryBridge
    shell_workspace_bridge: ShellWorkspaceBridge
    shell_inspector_bridge: ShellInspectorBridge
    graph_canvas_state_bridge: GraphCanvasStateBridge
    graph_canvas_command_bridge: GraphCanvasCommandBridge
    graph_canvas_bridge: GraphCanvasBridge


def create_shell_context_bridges(host: "ShellWindow") -> ShellContextBridges:
    graph_canvas_state_bridge = GraphCanvasStateBridge(
        host,
        shell_window=host,
        scene_bridge=host.scene,
        view_bridge=host.view,
    )
    graph_canvas_command_bridge = GraphCanvasCommandBridge(
        host,
        shell_window=host,
        scene_bridge=host.scene,
        view_bridge=host.view,
    )
    return ShellContextBridges(
        shell_library_bridge=ShellLibraryBridge(
            host,
            shell_window=host,
        ),
        shell_workspace_bridge=ShellWorkspaceBridge(
            host,
            shell_window=host,
            scene_bridge=host.scene,
            view_bridge=host.view,
            console_bridge=host.console_panel,
            workspace_tabs_bridge=host.workspace_tabs,
        ),
        shell_inspector_bridge=ShellInspectorBridge(
            host,
            shell_window=host,
            scene_bridge=host.scene,
        ),
        graph_canvas_state_bridge=graph_canvas_state_bridge,
        graph_canvas_command_bridge=graph_canvas_command_bridge,
        graph_canvas_bridge=GraphCanvasBridge(
            host,
            shell_window=host,
            scene_bridge=host.scene,
            view_bridge=host.view,
            state_bridge=graph_canvas_state_bridge,
            command_bridge=graph_canvas_command_bridge,
        ),
    )


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
        ("mainWindow", host),
        ("sceneBridge", host.scene),
        ("viewBridge", host.view),
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
