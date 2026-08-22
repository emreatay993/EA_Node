from __future__ import annotations

"""Graph-canvas command bridge package.

The QML-facing ``GraphCanvasCommandBridge`` is composed from per-domain
plain-Python mixin modules; this composition root owns ONLY construction and
source resolution. New canvas commands are added as one ``@pyqtSlot`` in the
matching ``*_ops`` module (plus its protocol entry in the same file or
``protocols.py``) — not here.
"""

from typing import TYPE_CHECKING, cast

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal

from ea_node_editor.ui.folder_explorer import FolderExplorerFilesystemService
from ea_node_editor.ui_qml.graph_canvas_command.annotation_style_ops import AnnotationStyleOps
from ea_node_editor.ui_qml.graph_canvas_command.canvas_host_ops import CanvasHostOps
from ea_node_editor.ui_qml.graph_canvas_command.folder_explorer_ops import (
    FolderExplorerOps,
    _FolderExplorerClipboardSource,
    _FolderExplorerConfirmationSource,
    _FolderExplorerOpenSource,
)
from ea_node_editor.ui_qml.graph_canvas_command.graphics_settings_ops import GraphicsSettingsOps
from ea_node_editor.ui_qml.graph_canvas_command.media_image_ops import MediaImageOps
from ea_node_editor.ui_qml.graph_canvas_command.media_video_ops import MediaVideoOps
from ea_node_editor.ui_qml.graph_canvas_command.node_creation_ops import NodeCreationOps
from ea_node_editor.ui_qml.graph_canvas_command.protocols import (
    _GraphCanvasCommandSource,
    _GraphCanvasHostSource,
    _GraphCanvasSceneCommandSource,
    _GraphCanvasScenePolicySource,
)
from ea_node_editor.ui_qml.graph_canvas_command.scene_mutation_ops import SceneMutationOps
from ea_node_editor.ui_qml.graph_canvas_command.viewport_ops import ViewportOps

if TYPE_CHECKING:
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
    from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge


def _resolve_scene_command_source(scene_bridge: object | None) -> _GraphCanvasSceneCommandSource | None:
    if scene_bridge is None:
        return None
    return cast(
        _GraphCanvasSceneCommandSource,
        getattr(scene_bridge, "command_bridge", scene_bridge),
    )


def _resolve_scene_policy_source(scene_bridge: object | None) -> _GraphCanvasScenePolicySource | None:
    if scene_bridge is None:
        return None
    return cast(
        _GraphCanvasScenePolicySource,
        getattr(scene_bridge, "policy_bridge", scene_bridge),
    )


class GraphCanvasCommandBridge(
    GraphicsSettingsOps,
    ViewportOps,
    SceneMutationOps,
    MediaImageOps,
    MediaVideoOps,
    NodeCreationOps,
    AnnotationStyleOps,
    CanvasHostOps,
    FolderExplorerOps,
    QObject,
):
    managedArtifactRenameReleaseRequested = pyqtSignal(str)
    managedArtifactRenameReleaseFinished = pyqtSignal(str)

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        shell_window: object | None = None,
        canvas_source: _GraphCanvasCommandSource | None = None,
        host_source: _GraphCanvasHostSource | None = None,
        scene_bridge: "GraphSceneBridge | None" = None,
        view_bridge: "ViewportBridge | None" = None,
        folder_explorer_service: FolderExplorerFilesystemService | None = None,
        folder_explorer_confirmation_source: _FolderExplorerConfirmationSource | None = None,
        folder_explorer_clipboard_source: _FolderExplorerClipboardSource | None = None,
        folder_explorer_open_source: _FolderExplorerOpenSource | None = None,
    ) -> None:
        super().__init__(parent)
        self._shell_window = shell_window
        self._scene_bridge = scene_bridge
        self._view_bridge = view_bridge
        self._canvas_source = canvas_source
        self._host_source = host_source
        self._scene_command_source = _resolve_scene_command_source(scene_bridge)
        self._scene_policy_source = _resolve_scene_policy_source(scene_bridge)
        self._folder_explorer_service = folder_explorer_service or FolderExplorerFilesystemService()
        self._folder_explorer_confirmation_source = folder_explorer_confirmation_source
        self._folder_explorer_clipboard_source = folder_explorer_clipboard_source
        self._folder_explorer_open_source = folder_explorer_open_source
        self._text_annotation_style_clipboard = ""

    @property
    def shell_window(self) -> object | None:
        return None

    @property
    def canvas_source(self) -> _GraphCanvasCommandSource | None:
        return self._canvas_source

    @property
    def host_source(self) -> _GraphCanvasHostSource | None:
        return self._host_source

    @property
    def scene_bridge(self) -> "GraphSceneBridge | None":
        return self._scene_bridge

    @property
    def scene_command_source(self) -> _GraphCanvasSceneCommandSource | None:
        return self._scene_command_source

    @property
    def scene_policy_source(self) -> _GraphCanvasScenePolicySource | None:
        return self._scene_policy_source

    @property
    def view_bridge(self) -> "ViewportBridge | None":
        return self._view_bridge

    @pyqtProperty(QObject, constant=True)
    def viewport_bridge(self) -> "ViewportBridge | None":
        return self._view_bridge


__all__ = [
    "GraphCanvasCommandBridge",
]
