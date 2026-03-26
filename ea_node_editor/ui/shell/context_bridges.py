from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

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


def create_shell_context_bridges(
    host: "ShellWindow",
    *,
    scene: object | None = None,
    view: object | None = None,
    console_panel: object | None = None,
    workspace_tabs: object | None = None,
) -> ShellContextBridges:
    resolved_scene = host.scene if scene is None else scene
    resolved_view = host.view if view is None else view
    resolved_console_panel = host.console_panel if console_panel is None else console_panel
    resolved_workspace_tabs = host.workspace_tabs if workspace_tabs is None else workspace_tabs
    graph_canvas_state_bridge = GraphCanvasStateBridge(
        host,
        shell_window=host,
        scene_bridge=resolved_scene,
        view_bridge=resolved_view,
    )
    graph_canvas_command_bridge = GraphCanvasCommandBridge(
        host,
        shell_window=host,
        scene_bridge=resolved_scene,
        view_bridge=resolved_view,
    )
    return ShellContextBridges(
        shell_library_bridge=ShellLibraryBridge(
            host,
            shell_window=host,
        ),
        shell_workspace_bridge=ShellWorkspaceBridge(
            host,
            shell_window=host,
            scene_bridge=resolved_scene,
            view_bridge=resolved_view,
            console_bridge=resolved_console_panel,
            workspace_tabs_bridge=resolved_workspace_tabs,
        ),
        shell_inspector_bridge=ShellInspectorBridge(
            host,
            shell_window=host,
            scene_bridge=resolved_scene,
        ),
        graph_canvas_state_bridge=graph_canvas_state_bridge,
        graph_canvas_command_bridge=graph_canvas_command_bridge,
        graph_canvas_bridge=GraphCanvasBridge(
            host,
            shell_window=host,
            scene_bridge=resolved_scene,
            view_bridge=resolved_view,
            state_bridge=graph_canvas_state_bridge,
            command_bridge=graph_canvas_command_bridge,
        ),
    )
