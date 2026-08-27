from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ea_node_editor.ui_qml.content_fullscreen_bridge import ContentFullscreenBridge
from ea_node_editor.ui_qml.jupyter_server_bridge import JupyterServerBridge
from ea_node_editor.ui_qml.native_folder_explorer_host_service import NativeFolderExplorerHostService
from ea_node_editor.ui_qml.plot_auto_preview_service import PlotAutoPreviewService
from ea_node_editor.ui_qml.plot_host_service import PlotHostService
from ea_node_editor.ui_qml.viewer_host_service import ViewerHostService
from ea_node_editor.ui_qml.viewer_control_bridge import ViewerControlBridge
from ea_node_editor.ui_qml.viewer_session_bridge import ViewerSessionBridge

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.composition.primitives import ShellPrimitiveDependencies
    from ea_node_editor.ui.shell.window import ShellWindow


@dataclass(frozen=True, slots=True)
class ShellRuntimeDependencies:
    content_fullscreen_bridge: ContentFullscreenBridge
    viewer_session_bridge: ViewerSessionBridge
    viewer_control_bridge: ViewerControlBridge
    viewer_host_service: ViewerHostService
    plot_host_service: PlotHostService
    plot_auto_preview_service: PlotAutoPreviewService
    native_folder_explorer_host_service: NativeFolderExplorerHostService
    jupyter_server_bridge: JupyterServerBridge

    def attach(self, host: "ShellWindow") -> None:
        host.content_fullscreen_bridge = self.content_fullscreen_bridge
        host.viewer_session_bridge = self.viewer_session_bridge
        host.viewer_control_bridge = self.viewer_control_bridge
        host.viewer_host_service = self.viewer_host_service
        host.plot_host_service = self.plot_host_service
        host.plot_auto_preview_service = self.plot_auto_preview_service
        host.native_folder_explorer_host_service = self.native_folder_explorer_host_service
        host.jupyter_server_bridge = self.jupyter_server_bridge


def create_viewer_service_dependencies(
    host: "ShellWindow",
    primitives: "ShellPrimitiveDependencies",
) -> ShellRuntimeDependencies:
    viewer_host_service_ref: list[ViewerHostService | None] = [None]

    def capture_overlay_camera_state(node_id: str, *, workspace_id: str = ""):  # noqa: ANN202
        viewer_host_service = viewer_host_service_ref[0]
        if viewer_host_service is None:
            return {}
        return viewer_host_service.capture_overlay_camera_state(
            node_id,
            workspace_id=workspace_id,
        )

    viewer_session_bridge = ViewerSessionBridge(
        host,
        shell_window=host,
        scene_bridge=primitives.scene,
        data_types=primitives.registry.data_types,
        capture_overlay_camera_state=capture_overlay_camera_state,
    )
    content_fullscreen_bridge = ContentFullscreenBridge(
        host,
        shell_window=host,
        scene_bridge=primitives.scene,
        viewer_session_bridge=viewer_session_bridge,
    )
    viewer_host_service = ViewerHostService(
        host,
        shell_window=host,
        viewer_session_bridge=viewer_session_bridge,
        preview_cache_provider=primitives._viewer_preview_cache_provider,
    )
    viewer_host_service_ref[0] = viewer_host_service
    viewer_control_bridge = ViewerControlBridge(
        host,
        shell_window=host,
        scene_bridge=primitives.scene,
        viewer_session_bridge=viewer_session_bridge,
    )
    plot_host_service = PlotHostService(
        host,
        shell_window=host,
        scene_bridge=primitives.scene,
        preview_cache_provider=primitives._plot_preview_cache_provider,
    )
    plot_auto_preview_service = PlotAutoPreviewService(
        host,
        scene_bridge=primitives.scene,
    )
    # With async preview surfaces wired, large sources must never convert on
    # the UI thread: cold reads return a loading state and the worker pools
    # build the managed cache. Small files (<= the inline threshold) still
    # convert synchronously.
    try:
        from ea_node_editor.addons.tabular_data.loader_cache_service import (
            set_shared_tabular_ui_thread_conversion_allowed,
        )

        set_shared_tabular_ui_thread_conversion_allowed(False)
    except Exception:  # noqa: BLE001 - tabular addon is optional
        pass
    native_folder_explorer_host_service = NativeFolderExplorerHostService(
        host,
        shell_window=host,
        scene_bridge=primitives.scene,
        enabled=False,
    )
    jupyter_server_bridge = JupyterServerBridge(
        host,
        shell_window=host,
    )
    return ShellRuntimeDependencies(
        content_fullscreen_bridge=content_fullscreen_bridge,
        viewer_session_bridge=viewer_session_bridge,
        viewer_control_bridge=viewer_control_bridge,
        viewer_host_service=viewer_host_service,
        plot_host_service=plot_host_service,
        plot_auto_preview_service=plot_auto_preview_service,
        native_folder_explorer_host_service=native_folder_explorer_host_service,
        jupyter_server_bridge=jupyter_server_bridge,
    )


__all__ = [
    "ShellRuntimeDependencies",
    "create_viewer_service_dependencies",
]
