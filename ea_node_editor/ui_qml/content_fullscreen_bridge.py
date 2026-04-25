from __future__ import annotations

import copy
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from ea_node_editor.nodes.builtins.ansys_dpf_common import DPF_VIEWER_NODE_TYPE_ID
from ea_node_editor.nodes.builtins.passive_media import (
    PASSIVE_MEDIA_IMAGE_PANEL_TYPE_ID,
    PASSIVE_MEDIA_PDF_PANEL_TYPE_ID,
)
from ea_node_editor.ui_qml.graph_scene_payload_builder import build_content_fullscreen_media_payload

if TYPE_CHECKING:
    from ea_node_editor.graph.model import GraphModel, NodeInstance, WorkspaceData
    from ea_node_editor.nodes.registry import NodeRegistry
    from ea_node_editor.nodes.types import NodeTypeSpec
    from ea_node_editor.ui.shell.window import ShellWindow
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
    from ea_node_editor.ui_qml.viewer_session_bridge import ViewerSessionBridge


@dataclass(frozen=True, slots=True)
class _FullscreenCandidate:
    workspace_id: str
    node: "NodeInstance"
    spec: "NodeTypeSpec"
    content_kind: str
    media_payload: dict[str, Any]
    viewer_payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class _FullscreenResolution:
    candidate: _FullscreenCandidate | None
    error: str


class _ContentFullscreenPolicyService:
    def __init__(
        self,
        *,
        shell_window_provider: Callable[[], "ShellWindow | None"],
        scene_bridge_provider: Callable[[], "GraphSceneBridge | None"],
        viewer_session_bridge_provider: Callable[[], "ViewerSessionBridge | None"],
    ) -> None:
        self._shell_window_provider = shell_window_provider
        self._scene_bridge_provider = scene_bridge_provider
        self._viewer_session_bridge_provider = viewer_session_bridge_provider

    def resolve_candidate(self, node_id: str) -> _FullscreenResolution:
        normalized_node_id = str(node_id or "").strip()
        if not normalized_node_id:
            return _FullscreenResolution(None, "A node must be selected for content fullscreen.")
        workspace_result = self.active_workspace()
        if isinstance(workspace_result, str):
            return _FullscreenResolution(None, workspace_result)
        workspace_id, workspace, registry = workspace_result
        node = workspace.nodes.get(normalized_node_id)
        if node is None:
            return _FullscreenResolution(None, "The selected node is no longer available.")
        spec = self.node_spec(registry, node.type_id)
        if spec is None:
            return _FullscreenResolution(None, "The selected node type is unavailable.")
        content_kind = self.content_kind_for_node(node, spec)
        if not content_kind:
            return _FullscreenResolution(None, "The selected node does not support content fullscreen.")
        if content_kind in {"image", "pdf"} and not str(node.properties.get("source_path", "") or "").strip():
            return _FullscreenResolution(None, "Media nodes need a source path before they can open fullscreen.")
        return _FullscreenResolution(
            _FullscreenCandidate(
                workspace_id=workspace_id,
                node=node,
                spec=spec,
                content_kind=content_kind,
                media_payload=(
                    build_content_fullscreen_media_payload(
                        workspace_id=workspace_id,
                        node=node,
                        spec=spec,
                    )
                    if content_kind in {"image", "pdf"}
                    else {}
                ),
                viewer_payload=(
                    self.build_viewer_payload(
                        workspace_id=workspace_id,
                        node=node,
                        spec=spec,
                    )
                    if content_kind == "viewer"
                    else {}
                ),
            ),
            "",
        )

    def active_workspace(self) -> tuple[str, "WorkspaceData", "NodeRegistry"] | str:
        shell_window = self._shell_window_provider()
        scene_bridge = self._scene_bridge_provider()
        scene_workspace_id = str(getattr(scene_bridge, "workspace_id", "") or "").strip()
        manager = getattr(shell_window, "workspace_manager", None) if shell_window is not None else None
        manager_workspace_id = ""
        if manager is not None:
            active_workspace_id = getattr(manager, "active_workspace_id", None)
            if callable(active_workspace_id):
                manager_workspace_id = str(active_workspace_id() or "").strip()
        if scene_workspace_id and manager_workspace_id and scene_workspace_id != manager_workspace_id:
            return "The active workspace state is ambiguous."
        workspace_id = scene_workspace_id or manager_workspace_id
        if not workspace_id:
            return "The active workspace state is ambiguous."
        model = getattr(shell_window, "model", None) if shell_window is not None else None
        registry = getattr(shell_window, "registry", None) if shell_window is not None else None
        if model is None or registry is None:
            return "The graph model is not ready."
        project = getattr(model, "project", None)
        workspaces = getattr(project, "workspaces", {}) if project is not None else {}
        workspace = workspaces.get(workspace_id)
        if workspace is None:
            return "The active workspace state is ambiguous."
        return workspace_id, workspace, registry

    @staticmethod
    def node_spec(registry: "NodeRegistry", type_id: str) -> "NodeTypeSpec | None":
        spec_or_none = getattr(registry, "spec_or_none", None)
        if callable(spec_or_none):
            return spec_or_none(type_id)
        try:
            return registry.get_spec(type_id)
        except KeyError:
            return None

    @staticmethod
    def content_kind_for_node(node: "NodeInstance", spec: "NodeTypeSpec") -> str:
        if node.type_id == PASSIVE_MEDIA_IMAGE_PANEL_TYPE_ID:
            return "image"
        if node.type_id == PASSIVE_MEDIA_PDF_PANEL_TYPE_ID:
            return "pdf"
        if node.type_id == DPF_VIEWER_NODE_TYPE_ID and str(spec.surface_family or "").strip() == "viewer":
            return "viewer"
        return ""

    def build_viewer_payload(
        self,
        *,
        workspace_id: str,
        node: "NodeInstance",
        spec: "NodeTypeSpec",
    ) -> dict[str, Any]:
        session_state = self.viewer_session_state(node.node_id)
        options = session_state.get("options", {})
        options_payload = options if isinstance(options, dict) else {}
        summary = session_state.get("summary", {})
        summary_payload = summary if isinstance(summary, dict) else {}
        payload = {
            "workspace_id": str(workspace_id),
            "node_id": str(node.node_id),
            "type_id": str(node.type_id),
            "title": str(node.title or spec.display_name),
            "display_name": str(spec.display_name),
            "surface_family": str(spec.surface_family or ""),
            "surface_variant": str(spec.surface_variant or ""),
            "properties": copy.deepcopy(node.properties),
            "session_state": session_state,
            "session_id": str(session_state.get("session_id", "") or ""),
            "phase": str(session_state.get("phase", "closed") or "closed"),
            "cache_state": str(session_state.get("cache_state", "") or ""),
            "live_mode": str(session_state.get("live_mode", "") or options_payload.get("live_mode", "") or ""),
            "summary": copy.deepcopy(summary_payload),
            "viewer_surface": self.scene_node_payload(node.node_id).get("viewer_surface", {}),
        }
        return payload

    def viewer_session_state(self, node_id: str) -> dict[str, Any]:
        bridge = self._viewer_session_bridge_provider()
        session_state = getattr(bridge, "session_state", None) if bridge is not None else None
        if not callable(session_state):
            return {}
        try:
            state = session_state(node_id)
        except Exception:  # noqa: BLE001
            return {}
        return copy.deepcopy(state) if isinstance(state, dict) else {}

    def scene_node_payload(self, node_id: str) -> dict[str, Any]:
        scene_bridge = self._scene_bridge_provider()
        if scene_bridge is None:
            return {}
        try:
            payloads = list(getattr(scene_bridge, "nodes_model", []) or [])
        except Exception:  # noqa: BLE001
            return {}
        normalized = str(node_id or "").strip()
        for payload in payloads:
            if isinstance(payload, dict) and str(payload.get("node_id", "")).strip() == normalized:
                return copy.deepcopy(payload)
        return {}


class ContentFullscreenBridge(QObject):
    content_fullscreen_changed = pyqtSignal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        shell_window: "ShellWindow | None" = None,
        scene_bridge: "GraphSceneBridge | None" = None,
        viewer_session_bridge: "ViewerSessionBridge | None" = None,
    ) -> None:
        super().__init__(parent)
        self._shell_window = shell_window
        self._scene_bridge = scene_bridge
        self._viewer_session_bridge = viewer_session_bridge
        self._open = False
        self._node_id = ""
        self._workspace_id = ""
        self._content_kind = ""
        self._title = ""
        self._media_payload: dict[str, Any] = {}
        self._viewer_payload: dict[str, Any] = {}
        self._last_error = ""
        self._policy_service = _ContentFullscreenPolicyService(
            shell_window_provider=lambda: self._shell_window,
            scene_bridge_provider=lambda: self._scene_bridge,
            viewer_session_bridge_provider=lambda: self._viewer_session_bridge,
        )
        self._connect_scene_lifecycle()

    @property
    def shell_window(self) -> "ShellWindow | None":
        return self._shell_window

    @property
    def scene_bridge(self) -> "GraphSceneBridge | None":
        return self._scene_bridge

    @property
    def viewer_session_bridge(self) -> "ViewerSessionBridge | None":
        return self._viewer_session_bridge

    def _connect_scene_lifecycle(self) -> None:
        if self._scene_bridge is None:
            return
        self._scene_bridge.workspace_changed.connect(self._on_workspace_changed)
        self._scene_bridge.nodes_changed.connect(self._on_nodes_changed)

    @pyqtProperty(bool, notify=content_fullscreen_changed)
    def open(self) -> bool:
        return self._open

    @pyqtProperty(str, notify=content_fullscreen_changed)
    def node_id(self) -> str:
        return self._node_id

    @pyqtProperty(str, notify=content_fullscreen_changed)
    def workspace_id(self) -> str:
        return self._workspace_id

    @pyqtProperty(str, notify=content_fullscreen_changed)
    def content_kind(self) -> str:
        return self._content_kind

    @pyqtProperty(str, notify=content_fullscreen_changed)
    def title(self) -> str:
        return self._title

    @pyqtProperty("QVariantMap", notify=content_fullscreen_changed)
    def media_payload(self) -> dict[str, Any]:
        return copy.deepcopy(self._media_payload)

    @pyqtProperty("QVariantMap", notify=content_fullscreen_changed)
    def viewer_payload(self) -> dict[str, Any]:
        return copy.deepcopy(self._viewer_payload)

    @pyqtProperty(str, notify=content_fullscreen_changed)
    def last_error(self) -> str:
        return self._last_error

    @pyqtSlot(str, result=bool)
    def request_open_node(self, node_id: str) -> bool:
        resolution = self._resolve_candidate(node_id)
        if resolution.candidate is None:
            self._close_with_error(resolution.error)
            return False
        self._open_candidate(resolution.candidate)
        return True

    @pyqtSlot(str, result=bool)
    def request_toggle_for_node(self, node_id: str) -> bool:
        normalized = str(node_id or "").strip()
        if self._open and normalized and normalized == self._node_id:
            self.request_close()
            return True
        return self.request_open_node(normalized)

    @pyqtSlot()
    def request_close(self) -> None:
        self._set_state(
            open_=False,
            node_id="",
            workspace_id="",
            content_kind="",
            title="",
            media_payload={},
            viewer_payload={},
            last_error="",
        )

    @pyqtSlot(str, result=bool)
    def can_open_node(self, node_id: str) -> bool:
        return self._resolve_candidate(node_id).candidate is not None

    def _on_workspace_changed(self, _workspace_id: str = "") -> None:
        if self._open:
            self.request_close()

    def _on_nodes_changed(self) -> None:
        if not self._open:
            return
        resolution = self._resolve_candidate(self._node_id)
        if resolution.candidate is None:
            self.request_close()
            return
        self._open_candidate(resolution.candidate)

    def _open_candidate(self, candidate: _FullscreenCandidate) -> None:
        self._set_state(
            open_=True,
            node_id=candidate.node.node_id,
            workspace_id=candidate.workspace_id,
            content_kind=candidate.content_kind,
            title=str(candidate.node.title or candidate.spec.display_name),
            media_payload=candidate.media_payload,
            viewer_payload=candidate.viewer_payload,
            last_error="",
        )

    def _close_with_error(self, error: str) -> None:
        self._set_state(
            open_=False,
            node_id="",
            workspace_id="",
            content_kind="",
            title="",
            media_payload={},
            viewer_payload={},
            last_error=str(error or "Content cannot be opened fullscreen."),
        )

    def _set_state(
        self,
        *,
        open_: bool,
        node_id: str,
        workspace_id: str,
        content_kind: str,
        title: str,
        media_payload: dict[str, Any],
        viewer_payload: dict[str, Any],
        last_error: str,
    ) -> None:
        next_media_payload = copy.deepcopy(media_payload)
        next_viewer_payload = copy.deepcopy(viewer_payload)
        changed = (
            self._open != bool(open_)
            or self._node_id != str(node_id or "")
            or self._workspace_id != str(workspace_id or "")
            or self._content_kind != str(content_kind or "")
            or self._title != str(title or "")
            or self._media_payload != next_media_payload
            or self._viewer_payload != next_viewer_payload
            or self._last_error != str(last_error or "")
        )
        if not changed:
            return
        self._open = bool(open_)
        self._node_id = str(node_id or "")
        self._workspace_id = str(workspace_id or "")
        self._content_kind = str(content_kind or "")
        self._title = str(title or "")
        self._media_payload = next_media_payload
        self._viewer_payload = next_viewer_payload
        self._last_error = str(last_error or "")
        self.content_fullscreen_changed.emit()

    def _resolve_candidate(self, node_id: str) -> _FullscreenResolution:
        return self._policy_service.resolve_candidate(node_id)

    def _active_workspace(self) -> tuple[str, "WorkspaceData", "NodeRegistry"] | str:
        return self._policy_service.active_workspace()

    @staticmethod
    def _node_spec(registry: "NodeRegistry", type_id: str) -> "NodeTypeSpec | None":
        return _ContentFullscreenPolicyService.node_spec(registry, type_id)

    @staticmethod
    def _content_kind_for_node(node: "NodeInstance", spec: "NodeTypeSpec") -> str:
        return _ContentFullscreenPolicyService.content_kind_for_node(node, spec)

    def _build_viewer_payload(
        self,
        *,
        workspace_id: str,
        node: "NodeInstance",
        spec: "NodeTypeSpec",
    ) -> dict[str, Any]:
        return self._policy_service.build_viewer_payload(
            workspace_id=workspace_id,
            node=node,
            spec=spec,
        )

    def _viewer_session_state(self, node_id: str) -> dict[str, Any]:
        return self._policy_service.viewer_session_state(node_id)

    def _scene_node_payload(self, node_id: str) -> dict[str, Any]:
        return self._policy_service.scene_node_payload(node_id)


__all__ = ["ContentFullscreenBridge"]
