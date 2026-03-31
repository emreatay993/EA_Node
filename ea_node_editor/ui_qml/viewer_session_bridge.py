from __future__ import annotations

import copy
import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

from ea_node_editor.execution.viewer_backend_dpf import DPF_EXECUTION_VIEWER_BACKEND_ID
from ea_node_editor.nodes.builtins.ansys_dpf_common import DPF_VIEWER_NODE_TYPE_ID

if TYPE_CHECKING:
    from ea_node_editor.graph.model import ProjectData
    from ea_node_editor.nodes.registry import NodeRegistry
    from ea_node_editor.ui.shell.window import ShellWindow
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge

_LIVE_MODE_FULL = "full"
_LIVE_MODE_PROXY = "proxy"
_LIVE_POLICY_FOCUS_ONLY = "focus_only"
_LIVE_POLICY_KEEP_LIVE = "keep_live"
_OPEN_SESSION_PHASES = frozenset({"open", "opening"})
_VIEWER_EVENT_TYPES = frozenset(
    {
        "viewer_session_opened",
        "viewer_session_updated",
        "viewer_data_materialized",
        "viewer_session_closed",
        "viewer_session_failed",
    }
)
_NODE_COMPLETED_EVENT_TYPE = "node_completed"
_RUNTIME_VIEWER_OUTPUT_KEY = "session"
_RUN_REQUIRED_BLOCKER = {
    "code": "rerun_required",
    "reason": "Live viewer transport is unavailable and requires rerun.",
    "rerun_required": True,
}


@dataclass(slots=True)
class _ViewerSessionProjection:
    workspace_id: str
    node_id: str
    session_id: str
    phase: str = "closed"
    request_id: str = ""
    last_command: str = ""
    last_error: str = ""
    playback_state: str = "paused"
    step_index: int = 0
    live_policy: str = _LIVE_POLICY_FOCUS_ONLY
    keep_live: bool = False
    cache_state: str = "empty"
    invalidated_reason: str = ""
    close_reason: str = ""
    backend_id: str = ""
    transport_revision: int = 0
    live_open_status: str = ""
    live_open_blocker: dict[str, Any] = field(default_factory=dict)
    data_refs: dict[str, Any] = field(default_factory=dict)
    transport: dict[str, Any] = field(default_factory=dict)
    camera_state: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)
    pending_summary: dict[str, Any] = field(default_factory=dict)
    pending_options: dict[str, Any] = field(default_factory=dict)
    pending_materialization: bool = False
    pending_proxy_snapshot_refresh: bool = False

    def payload(self) -> dict[str, Any]:
        summary = copy.deepcopy(self.summary)
        summary.update(copy.deepcopy(self.pending_summary))
        options = copy.deepcopy(self.options)
        options.update(copy.deepcopy(self.pending_options))
        live_policy = _normalize_live_policy(options.get("live_policy", self.live_policy))
        keep_live = bool(options.get("keep_live", self.keep_live))
        playback_state = _string(options.get("playback_state", self.playback_state)) or "paused"
        step_index = _coerce_step_index(options.get("step_index"), default=self.step_index)
        live_mode = _normalize_live_mode(options.get("live_mode", _LIVE_MODE_PROXY))

        summary["cache_state"] = self.cache_state
        if self.backend_id:
            summary["backend_id"] = self.backend_id
        if self.transport_revision > 0:
            summary["transport_revision"] = int(self.transport_revision)
        if self.live_open_status:
            summary["live_open_status"] = self.live_open_status
        if self.live_open_blocker:
            summary["live_open_blocker"] = copy.deepcopy(self.live_open_blocker)
        if self.invalidated_reason:
            summary["invalidated_reason"] = self.invalidated_reason
        if self.close_reason:
            summary["close_reason"] = self.close_reason
        if self.camera_state:
            summary.setdefault("camera_state", copy.deepcopy(self.camera_state))
            summary.setdefault("camera", copy.deepcopy(self.camera_state))

        options["live_policy"] = live_policy
        options["keep_live"] = keep_live
        options["playback_state"] = playback_state
        options["step_index"] = step_index
        options["live_mode"] = live_mode
        options["cache_state"] = self.cache_state
        if self.backend_id:
            options["backend_id"] = self.backend_id
        if self.transport_revision > 0:
            options["transport_revision"] = int(self.transport_revision)
        if self.live_open_status:
            options["live_open_status"] = self.live_open_status
        if self.live_open_blocker:
            options["live_open_blocker"] = copy.deepcopy(self.live_open_blocker)

        return {
            "workspace_id": self.workspace_id,
            "node_id": self.node_id,
            "session_id": self.session_id,
            "phase": self.phase,
            "request_id": self.request_id,
            "last_command": self.last_command,
            "last_error": self.last_error,
            "playback_state": playback_state,
            "step_index": step_index,
            "live_policy": live_policy,
            "keep_live": keep_live,
            "cache_state": self.cache_state,
            "invalidated_reason": self.invalidated_reason,
            "close_reason": self.close_reason,
            "backend_id": self.backend_id,
            "transport_revision": int(self.transport_revision),
            "live_open_status": self.live_open_status,
            "live_open_blocker": copy.deepcopy(self.live_open_blocker),
            "data_refs": copy.deepcopy(self.data_refs),
            "transport": copy.deepcopy(self.transport),
            "camera_state": copy.deepcopy(self.camera_state),
            "summary": summary,
            "options": options,
        }


def _copy_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): copy.deepcopy(item) for key, item in value.items()}


def _string(value: Any) -> str:
    return str(value or "").strip()


def _normalize_live_policy(value: Any) -> str:
    normalized = _string(value).lower() or _LIVE_POLICY_FOCUS_ONLY
    if normalized not in {_LIVE_POLICY_FOCUS_ONLY, _LIVE_POLICY_KEEP_LIVE}:
        return _LIVE_POLICY_FOCUS_ONLY
    return normalized


def _normalize_live_mode(value: Any) -> str:
    normalized = _string(value).lower() or _LIVE_MODE_PROXY
    if normalized not in {_LIVE_MODE_PROXY, _LIVE_MODE_FULL}:
        return _LIVE_MODE_PROXY
    return normalized


def _coerce_step_index(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_playback_payload(
    value: Any,
    *,
    fallback_state: str = "paused",
    fallback_step_index: int = 0,
) -> dict[str, Any]:
    payload = _copy_mapping(value)
    state = _string(payload.get("state") or payload.get("playback_state")) or fallback_state
    step_index = _coerce_step_index(
        payload.get("step_index", payload.get("frame_index")),
        default=fallback_step_index,
    )
    return {
        "state": state,
        "step_index": step_index,
    }


def _projection_safe_transport(value: Any) -> dict[str, Any]:
    transport = _copy_mapping(value)
    projection: dict[str, Any] = {}
    kind = _string(transport.get("kind"))
    if kind:
        projection["kind"] = kind
    backend_id = _string(transport.get("backend_id"))
    if backend_id:
        projection["backend_id"] = backend_id
    return projection


class ViewerSessionBridge(QObject):
    sessions_changed = pyqtSignal()
    active_workspace_changed = pyqtSignal()
    last_error_changed = pyqtSignal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        shell_window: "ShellWindow | None" = None,
        scene_bridge: "GraphSceneBridge | None" = None,
    ) -> None:
        super().__init__(parent)
        self._shell_window = shell_window
        self._scene_bridge = scene_bridge
        self._sessions: dict[tuple[str, str], _ViewerSessionProjection] = {}
        self._pending_reset_seed: dict[tuple[str, str], _ViewerSessionProjection] | None = None
        self._focused_viewer_node_by_workspace: dict[str, str] = {}
        self._last_error = ""
        self._policy_sync_in_progress = False

        if shell_window is not None:
            execution_event = getattr(shell_window, "execution_event", None)
            if execution_event is not None:
                execution_event.connect(self._handle_execution_event)
        if scene_bridge is not None:
            scene_bridge.workspace_changed.connect(self._on_workspace_changed)
            scene_bridge.selection_changed.connect(self._on_selection_changed)
            scene_bridge.nodes_changed.connect(self._on_nodes_changed)
            scene_bridge.edges_changed.connect(self._on_edges_changed)

    @pyqtProperty(str, notify=active_workspace_changed)
    def active_workspace_id(self) -> str:
        return self._current_workspace_id()

    @pyqtProperty("QVariantList", notify=sessions_changed)
    def sessions_model(self) -> list[dict[str, Any]]:
        workspace_id = self._current_workspace_id()
        sessions = [
            state.payload()
            for state in self._sessions.values()
            if state.workspace_id == workspace_id
        ]
        sessions.sort(key=lambda item: (str(item.get("phase", "")), str(item.get("node_id", ""))))
        return sessions

    @pyqtProperty(int, notify=sessions_changed)
    def session_count(self) -> int:
        workspace_id = self._current_workspace_id()
        return sum(1 for state in self._sessions.values() if state.workspace_id == workspace_id)

    @pyqtProperty(str, notify=last_error_changed)
    def last_error(self) -> str:
        return self._last_error

    @pyqtSlot(str, result="QVariantMap")
    @pyqtSlot(str, "QVariantMap", result="QVariantMap")
    def session_state(self, node_id: str, payload: Any = None) -> dict[str, Any]:
        workspace_id = self._workspace_id_from_payload(payload)
        normalized_node_id = _string(node_id)
        if not workspace_id or not normalized_node_id:
            return {}
        state = self._sessions.get((workspace_id, normalized_node_id))
        return state.payload() if state is not None else {}

    @pyqtSlot(str, result=str)
    @pyqtSlot(str, "QVariantMap", result=str)
    def open(self, node_id: str, payload: Any = None) -> str:
        workspace_id = self._workspace_id_from_payload(payload)
        normalized_node_id = _string(node_id)
        if not workspace_id or not normalized_node_id:
            return ""

        existing_state = self._sessions.get((workspace_id, normalized_node_id))
        payload_map = _copy_mapping(payload)
        data_refs = _copy_mapping(payload_map.get("data_refs"))
        transport = _copy_mapping(payload_map.get("transport"))
        if existing_state is not None:
            if not data_refs:
                data_refs = copy.deepcopy(existing_state.data_refs)
            if not transport:
                transport = copy.deepcopy(existing_state.transport)
        if existing_state is None and not data_refs and not transport:
            return ""

        state = existing_state or self._ensure_session_state(workspace_id, normalized_node_id)
        summary = _copy_mapping(payload_map.get("summary"))
        if not summary and existing_state is not None:
            summary = copy.deepcopy(existing_state.summary)
        summary.pop("close_reason", None)
        summary.pop("invalidated_reason", None)
        option_updates = _copy_mapping(payload_map.get("options"))
        if existing_state is not None:
            option_updates.pop("reason", None)
            option_updates.pop("release_handles", None)
        backend_id = self._resolve_backend_id(state, payload_map)
        camera_state = _copy_mapping(payload_map.get("camera_state"))
        if not camera_state and existing_state is not None:
            camera_state = copy.deepcopy(existing_state.camera_state)
        playback = _normalize_playback_payload(
            payload_map.get("playback_state") or option_updates,
            fallback_state=state.playback_state,
            fallback_step_index=state.step_index,
        )
        transport_revision = _coerce_step_index(
            payload_map.get("transport_revision"),
            default=state.transport_revision,
        )
        live_open_status = _string(payload_map.get("live_open_status")) or state.live_open_status
        live_open_blocker = _copy_mapping(payload_map.get("live_open_blocker"))
        if not live_open_blocker:
            live_open_blocker = copy.deepcopy(state.live_open_blocker)

        state.phase = "opening"
        state.invalidated_reason = ""
        state.close_reason = ""
        state.last_error = ""
        state.last_command = "open"
        self._clear_pending_projection(state)

        request_options = self._request_options(state, option_updates)
        request_options.pop("reason", None)
        request_options.pop("release_handles", None)
        request_options["playback_state"] = playback["state"]
        request_options["step_index"] = playback["step_index"]
        request_options["live_mode"] = self._desired_live_mode_map(workspace_id).get(
            (workspace_id, normalized_node_id),
            _LIVE_MODE_PROXY,
        )
        request_id = self._send_execution_command(
            "open_viewer_session",
            workspace_id=workspace_id,
            node_id=normalized_node_id,
            session_id=state.session_id,
            backend_id=backend_id,
            data_refs=data_refs,
            transport=transport,
            transport_revision=transport_revision,
            live_open_status=live_open_status,
            live_open_blocker=live_open_blocker,
            summary=summary,
            camera_state=camera_state,
            playback_state=playback,
            options=request_options,
        )
        if not request_id:
            state.phase = "error"
            self.sessions_changed.emit()
            return ""

        state.request_id = request_id
        state.backend_id = backend_id or state.backend_id
        self._merge_pending_projection(
            state,
            summary=summary,
            options=request_options,
        )
        state.camera_state = camera_state or state.camera_state
        state.playback_state = playback["state"]
        state.step_index = playback["step_index"]
        self.sessions_changed.emit()
        return state.session_id

    @pyqtSlot(str, result=bool)
    @pyqtSlot(str, "QVariantMap", result=bool)
    def close(self, node_id: str, payload: Any = None) -> bool:
        state = self._active_session(node_id, payload)
        if state is None:
            return False

        payload_map = _copy_mapping(payload)
        option_updates = _copy_mapping(payload_map.get("options"))
        if "reason" not in option_updates:
            option_updates["reason"] = "user_close"
        request_id = self._send_execution_command(
            "close_viewer_session",
            workspace_id=state.workspace_id,
            node_id=state.node_id,
            session_id=state.session_id,
            options=option_updates,
        )
        if not request_id:
            state.phase = "error"
            state.last_command = "close"
            self.sessions_changed.emit()
            return False

        state.request_id = request_id
        state.last_command = "close"
        state.phase = "closing"
        state.close_reason = _string(option_updates.get("reason"))
        self._clear_focused_viewer_node_if_matches(state.workspace_id, state.node_id)
        self.sessions_changed.emit()
        self._sync_live_policy(state.workspace_id)
        return True

    @pyqtSlot(str, result=bool)
    @pyqtSlot(str, "QVariantMap", result=bool)
    def play(self, node_id: str, payload: Any = None) -> bool:
        return self._update_session_command(
            node_id,
            payload,
            command_name="play",
            option_updates={"playback_state": "playing"},
        )

    @pyqtSlot(str, result=bool)
    @pyqtSlot(str, "QVariantMap", result=bool)
    def pause(self, node_id: str, payload: Any = None) -> bool:
        return self._update_session_command(
            node_id,
            payload,
            command_name="pause",
            option_updates={"playback_state": "paused"},
        )

    @pyqtSlot(str, result=bool)
    @pyqtSlot(str, "QVariantMap", result=bool)
    def step(self, node_id: str, payload: Any = None) -> bool:
        state = self._active_session(node_id, payload)
        if state is None:
            return False
        step_index = self._effective_step_index(state) + 1
        return self._update_session_command(
            node_id,
            payload,
            command_name="step",
            option_updates={
                "playback_state": "paused",
                "step_index": step_index,
            },
        )

    @pyqtSlot(str, str, result=bool)
    @pyqtSlot(str, str, "QVariantMap", result=bool)
    def set_live_policy(self, node_id: str, live_policy: str, payload: Any = None) -> bool:
        return self._update_session_command(
            node_id,
            payload,
            command_name="set_live_policy",
            option_updates={"live_policy": str(live_policy or "").strip() or _LIVE_POLICY_FOCUS_ONLY},
        )

    @pyqtSlot(str, bool, result=bool)
    @pyqtSlot(str, bool, "QVariantMap", result=bool)
    def set_keep_live(self, node_id: str, keep_live: bool, payload: Any = None) -> bool:
        return self._update_session_command(
            node_id,
            payload,
            command_name="set_keep_live",
            option_updates={"keep_live": bool(keep_live)},
        )

    @pyqtSlot(str, result=bool)
    @pyqtSlot(str, "QVariantMap", result=bool)
    def focus_session(self, node_id: str, payload: Any = None) -> bool:
        workspace_id = self._workspace_id_from_payload(payload)
        normalized_node_id = _string(node_id)
        if not workspace_id or not normalized_node_id:
            return False
        changed = self._set_focused_viewer_node(workspace_id, normalized_node_id)
        self._sync_live_policy(workspace_id)
        if changed:
            self.sessions_changed.emit()
        return True

    @pyqtSlot(result=bool)
    @pyqtSlot("QVariantMap", result=bool)
    def clear_viewer_focus(self, payload: Any = None) -> bool:
        workspace_id = self._workspace_id_from_payload(payload)
        if not workspace_id:
            return False
        changed = self._set_focused_viewer_node(workspace_id, "")
        self._sync_live_policy(workspace_id)
        if changed:
            self.sessions_changed.emit()
        return True

    def project_loaded(
        self,
        project: "ProjectData | None",
        registry: "NodeRegistry | None",
        *,
        reseed_on_next_reset: bool = False,
    ) -> None:
        next_sessions = self._build_project_projection(project, registry)
        self._sessions = next_sessions
        self._focused_viewer_node_by_workspace.clear()
        self._pending_reset_seed = copy.deepcopy(next_sessions) if reseed_on_next_reset else None
        self.sessions_changed.emit()

    def project_workspace_run_required(
        self,
        workspace_id: str,
        *,
        reason: str,
        run_id: str = "",
    ) -> None:
        normalized_workspace_id = _string(workspace_id)
        normalized_reason = _string(reason)
        if not normalized_workspace_id or not normalized_reason:
            return
        changed = False
        for state in self._sessions.values():
            if state.workspace_id != normalized_workspace_id:
                continue
            self._project_run_required_state(state, reason=normalized_reason, run_id=run_id)
            changed = True
        if changed:
            self.sessions_changed.emit()

    def project_all_run_required(self, *, reason: str) -> None:
        normalized_reason = _string(reason)
        if not normalized_reason or not self._sessions:
            return
        for state in self._sessions.values():
            self._project_run_required_state(state, reason=normalized_reason)
        self.sessions_changed.emit()

    def invalidate_workspace_sessions(
        self,
        workspace_id: str,
        *,
        reason: str,
        run_id: str = "",
    ) -> None:
        self.project_workspace_run_required(workspace_id, reason=reason, run_id=run_id)

    def invalidate_all_sessions(self, *, reason: str) -> None:
        self.project_all_run_required(reason=reason)

    def reset_all_sessions(self, *, reason: str = "") -> None:
        if reason:
            self._set_last_error("")
        pending_seed = copy.deepcopy(self._pending_reset_seed) if self._pending_reset_seed is not None else None
        self._pending_reset_seed = None
        self._sessions.clear()
        self._focused_viewer_node_by_workspace.clear()
        if pending_seed is not None and _string(reason) == "project_close":
            self._sessions = pending_seed
        self.sessions_changed.emit()

    def _build_project_projection(
        self,
        project: "ProjectData | None",
        registry: "NodeRegistry | None",
    ) -> dict[tuple[str, str], _ViewerSessionProjection]:
        if project is None:
            return {}
        next_sessions: dict[tuple[str, str], _ViewerSessionProjection] = {}
        previous_sessions = copy.deepcopy(self._sessions)
        workspaces = getattr(project, "workspaces", {})
        if not isinstance(workspaces, dict):
            return {}
        for workspace_id, workspace in workspaces.items():
            nodes = getattr(workspace, "nodes", {})
            if not isinstance(nodes, dict):
                continue
            for node_id, node in nodes.items():
                if not self._is_viewer_node(node, registry):
                    continue
                session_key = (str(workspace_id), str(node_id))
                baseline = previous_sessions.get(session_key)
                state = baseline or _ViewerSessionProjection(
                    workspace_id=str(workspace_id),
                    node_id=str(node_id),
                    session_id=self._build_session_id(str(workspace_id), str(node_id)),
                )
                state.workspace_id = str(workspace_id)
                state.node_id = str(node_id)
                state.session_id = self._build_session_id(state.workspace_id, state.node_id)
                state.request_id = ""
                state.last_error = ""
                state.invalidated_reason = ""
                state.close_reason = ""
                self._clear_pending_projection(state)
                if not state.backend_id:
                    state.backend_id = self._default_backend_id_for_node(node)
                self._project_run_required_state(
                    state,
                    reason="project_reload",
                    run_id="",
                )
                next_sessions[session_key] = state
        return next_sessions

    @staticmethod
    def _is_viewer_node(node: Any, registry: "NodeRegistry | None") -> bool:
        type_id = _string(getattr(node, "type_id", ""))
        if type_id == DPF_VIEWER_NODE_TYPE_ID:
            return True
        if registry is None:
            return False
        spec_or_none = getattr(registry, "spec_or_none", None)
        if not callable(spec_or_none):
            return False
        spec = spec_or_none(type_id)
        if spec is None:
            return False
        return _string(getattr(spec, "surface_family", "")) == "viewer"

    @staticmethod
    def _default_backend_id_for_node(node: Any) -> str:
        if _string(getattr(node, "type_id", "")) == DPF_VIEWER_NODE_TYPE_ID:
            return DPF_EXECUTION_VIEWER_BACKEND_ID
        return ""

    def _project_run_required_state(
        self,
        state: _ViewerSessionProjection,
        *,
        reason: str,
        run_id: str = "",
    ) -> None:
        blocker = copy.deepcopy(_RUN_REQUIRED_BLOCKER)
        state.phase = "blocked"
        state.request_id = ""
        state.last_command = "run_required"
        state.last_error = ""
        state.cache_state = "proxy_ready" if self._has_proxy_projection(state) else "empty"
        state.data_refs.clear()
        state.transport = _projection_safe_transport(state.transport)
        state.live_open_status = "blocked"
        state.live_open_blocker = blocker
        state.summary.pop("invalidated_reason", None)
        state.summary["cache_state"] = state.cache_state
        state.summary["live_open_status"] = "blocked"
        state.summary["live_open_blocker"] = copy.deepcopy(blocker)
        state.summary["rerun_required"] = True
        if state.backend_id:
            state.summary["backend_id"] = state.backend_id
        if state.transport_revision > 0:
            state.summary["transport_revision"] = int(state.transport_revision)
        if reason:
            state.summary["live_transport_release_reason"] = reason
        if run_id:
            state.summary["run_id"] = run_id
        state.options["cache_state"] = state.cache_state
        state.options["live_mode"] = _LIVE_MODE_PROXY
        state.options["live_open_status"] = "blocked"
        state.options["live_open_blocker"] = copy.deepcopy(blocker)
        state.options["rerun_required"] = True
        state.options["playback_state"] = state.playback_state
        state.options["step_index"] = int(state.step_index)
        state.options["live_policy"] = _normalize_live_policy(state.options.get("live_policy", state.live_policy))
        state.options["keep_live"] = bool(state.options.get("keep_live", state.keep_live))
        if state.backend_id:
            state.options["backend_id"] = state.backend_id
        if state.transport_revision > 0:
            state.options["transport_revision"] = int(state.transport_revision)

    @staticmethod
    def _has_proxy_projection(state: _ViewerSessionProjection) -> bool:
        return any(
            (
                bool(state.summary),
                bool(state.options),
                bool(state.camera_state),
                state.transport_revision > 0,
                bool(state.backend_id),
            )
        )

    def _active_session(self, node_id: str, payload: Any = None) -> _ViewerSessionProjection | None:
        workspace_id = self._workspace_id_from_payload(payload)
        normalized_node_id = _string(node_id)
        if not workspace_id or not normalized_node_id:
            return None
        state = self._sessions.get((workspace_id, normalized_node_id))
        if state is None or state.phase in {"closed", "blocked", "error"}:
            return None
        return state

    def _update_session_command(
        self,
        node_id: str,
        payload: Any,
        *,
        command_name: str,
        option_updates: dict[str, Any],
    ) -> bool:
        state = self._active_session(node_id, payload)
        if state is None:
            return False

        payload_map = _copy_mapping(payload)
        summary = _copy_mapping(payload_map.get("summary"))
        merged_option_updates = dict(option_updates)
        merged_option_updates.update(_copy_mapping(payload_map.get("options")))
        backend_id = self._resolve_backend_id(state, payload_map)
        camera_state = _copy_mapping(payload_map.get("camera_state")) or copy.deepcopy(state.camera_state)
        playback = _normalize_playback_payload(
            payload_map.get("playback_state") or merged_option_updates,
            fallback_state=state.playback_state,
            fallback_step_index=state.step_index,
        )
        request_options = self._request_options(state, merged_option_updates)
        request_id = self._send_execution_command(
            "update_viewer_session",
            workspace_id=state.workspace_id,
            node_id=state.node_id,
            session_id=state.session_id,
            backend_id=backend_id,
            camera_state=camera_state,
            playback_state=playback,
            summary=summary,
            options=request_options,
        )
        if not request_id:
            state.phase = "error"
            state.last_command = command_name
            self.sessions_changed.emit()
            return False

        state.phase = "open"
        state.request_id = request_id
        state.last_command = command_name
        state.backend_id = backend_id or state.backend_id
        state.camera_state = camera_state
        state.playback_state = playback["state"]
        state.step_index = playback["step_index"]
        self._merge_pending_projection(
            state,
            summary=summary,
            options=request_options,
        )
        self.sessions_changed.emit()
        self._sync_live_policy(state.workspace_id)
        return True

    def _resolve_backend_id(self, state: _ViewerSessionProjection, payload_map: Mapping[str, Any]) -> str:
        payload_backend_id = _string(payload_map.get("backend_id"))
        if payload_backend_id:
            return payload_backend_id
        options = _copy_mapping(payload_map.get("options"))
        summary = _copy_mapping(payload_map.get("summary"))
        return (
            _string(options.get("backend_id"))
            or _string(summary.get("backend_id"))
            or state.backend_id
        )

    @staticmethod
    def _clear_pending_projection(state: _ViewerSessionProjection) -> None:
        state.pending_summary.clear()
        state.pending_options.clear()
        state.pending_materialization = False

    @staticmethod
    def _merge_pending_projection(
        state: _ViewerSessionProjection,
        *,
        summary: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
        pending_materialization: bool | None = None,
    ) -> None:
        if summary:
            state.pending_summary.update(copy.deepcopy(summary))
        if options:
            state.pending_options.update(copy.deepcopy(options))
        if pending_materialization is not None:
            state.pending_materialization = pending_materialization

    @staticmethod
    def _effective_options(state: _ViewerSessionProjection) -> dict[str, Any]:
        options = copy.deepcopy(state.options)
        options.update(copy.deepcopy(state.pending_options))
        return options

    def _effective_step_index(self, state: _ViewerSessionProjection) -> int:
        return _coerce_step_index(
            self._effective_options(state).get("step_index"),
            default=state.step_index,
        )

    def _request_options(self, state: _ViewerSessionProjection, option_updates: dict[str, Any]) -> dict[str, Any]:
        options = self._effective_options(state)
        options.update(copy.deepcopy(option_updates))
        options["live_policy"] = _normalize_live_policy(options.get("live_policy", state.live_policy))
        options["keep_live"] = bool(options.get("keep_live", state.keep_live))
        options["playback_state"] = _string(options.get("playback_state", state.playback_state)) or "paused"
        options["step_index"] = _coerce_step_index(
            options.get("step_index"),
            default=self._effective_step_index(state),
        )
        options["live_mode"] = _normalize_live_mode(options.get("live_mode", _LIVE_MODE_PROXY))
        return options

    def _materialize_options(
        self,
        state: _ViewerSessionProjection,
        option_updates: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_updates = copy.deepcopy(option_updates or {})
        requested_live_mode = _normalize_live_mode(
            normalized_updates.get("live_mode", self._effective_options(state).get("live_mode", _LIVE_MODE_FULL))
        )
        options = self._request_options(state, normalized_updates)
        if requested_live_mode == _LIVE_MODE_FULL and "output_profile" not in normalized_updates:
            output_profile = "memory"
            options.pop("export_formats", None)
        else:
            output_profile = _string(options.get("output_profile")) or "memory"
        options["output_profile"] = output_profile
        options["live_mode"] = requested_live_mode
        return options

    def _send_execution_command(self, method_name: str, **kwargs: Any) -> str:
        execution_client = getattr(self._shell_window, "execution_client", None)
        method = getattr(execution_client, method_name, None)
        if not callable(method):
            self._set_last_error(f"Execution client does not support {method_name}.")
            return ""
        try:
            request_id = method(**kwargs)
        except TypeError as exc:
            self._set_last_error(str(exc))
            return ""
        except Exception as exc:  # noqa: BLE001
            self._set_last_error(str(exc))
            return ""
        self._set_last_error("")
        return _string(request_id)

    def _send_materialize_command(
        self,
        state: _ViewerSessionProjection,
        *,
        option_updates: dict[str, Any] | None = None,
    ) -> bool:
        request_options = self._materialize_options(state, option_updates)
        request_id = self._send_execution_command(
            "materialize_viewer_data",
            workspace_id=state.workspace_id,
            node_id=state.node_id,
            session_id=state.session_id,
            backend_id=state.backend_id,
            options=request_options,
        )
        if not request_id:
            state.phase = "error"
            state.last_command = "materialize"
            return False
        state.request_id = request_id
        state.last_command = "materialize"
        self._merge_pending_projection(
            state,
            options=request_options,
            pending_materialization=True,
        )
        return True

    def _ensure_session_state(self, workspace_id: str, node_id: str) -> _ViewerSessionProjection:
        session_key = (workspace_id, node_id)
        state = self._sessions.get(session_key)
        if state is not None:
            return state
        state = _ViewerSessionProjection(
            workspace_id=workspace_id,
            node_id=node_id,
            session_id=self._build_session_id(workspace_id, node_id),
        )
        self._sessions[session_key] = state
        return state

    @staticmethod
    def _build_session_id(workspace_id: str, node_id: str) -> str:
        digest = hashlib.sha1(f"{workspace_id}:{node_id}".encode("utf-8")).hexdigest()[:16]
        return f"viewer_session_{digest}"

    def _workspace_id_from_payload(self, payload: Any) -> str:
        payload_map = _copy_mapping(payload)
        workspace_id = _string(payload_map.get("workspace_id"))
        if workspace_id:
            return workspace_id
        return self._current_workspace_id()

    def _current_workspace_id(self) -> str:
        if self._scene_bridge is not None:
            workspace_id = _string(getattr(self._scene_bridge, "workspace_id", ""))
            if workspace_id:
                return workspace_id
        workspace_manager = getattr(self._shell_window, "workspace_manager", None)
        active_workspace_id = getattr(workspace_manager, "active_workspace_id", None)
        if not callable(active_workspace_id):
            return ""
        try:
            return _string(active_workspace_id())
        except Exception:  # noqa: BLE001
            return ""

    def _handle_execution_event(self, event: dict[str, Any]) -> None:
        event_type = _string(event.get("type"))
        if event_type == _NODE_COMPLETED_EVENT_TYPE:
            if self._seed_runtime_projection_from_node_completed(event):
                return
        if event_type not in _VIEWER_EVENT_TYPES:
            return

        workspace_id = _string(event.get("workspace_id"))
        node_id = _string(event.get("node_id"))
        if not workspace_id or not node_id:
            return

        state = self._ensure_session_state(workspace_id, node_id)
        state.session_id = _string(event.get("session_id")) or state.session_id
        state.request_id = _string(event.get("request_id")) or state.request_id

        if event_type == "viewer_session_failed":
            self._clear_pending_projection(state)
            state.phase = "error"
            state.last_command = _string(event.get("command"))
            state.last_error = _string(event.get("error"))
            self._set_last_error(state.last_error)
            self.sessions_changed.emit()
            return

        self._set_last_error("")
        self._clear_pending_projection(state)
        self._apply_authoritative_projection(state, event)
        state.last_error = ""
        if event_type == "viewer_session_closed":
            state.phase = "closed"
            state.data_refs.clear()
            state.transport = _projection_safe_transport(state.transport)
            self._clear_focused_viewer_node_if_matches(workspace_id, node_id)
        else:
            state.phase = "open"
        self.sessions_changed.emit()
        self._sync_live_policy(workspace_id)

    def _seed_runtime_projection_from_node_completed(
        self,
        event: Mapping[str, Any],
    ) -> bool:
        outputs = _copy_mapping(event.get("outputs"))
        runtime_payload = _copy_mapping(outputs.get(_RUNTIME_VIEWER_OUTPUT_KEY))
        if not runtime_payload:
            return False

        workspace_id = _string(runtime_payload.get("workspace_id")) or _string(event.get("workspace_id"))
        node_id = _string(runtime_payload.get("node_id")) or _string(event.get("node_id"))
        session_id = _string(runtime_payload.get("session_id"))
        if not workspace_id or not node_id or not session_id:
            return False

        state = self._ensure_session_state(workspace_id, node_id)
        state.session_id = session_id
        state.request_id = ""
        state.last_command = "run_projection"
        state.invalidated_reason = ""
        state.close_reason = ""
        state.last_error = ""

        self._set_last_error("")
        self._clear_pending_projection(state)
        self._apply_authoritative_projection(state, runtime_payload)
        state.phase = "closed"
        self.sessions_changed.emit()
        return True

    def _apply_authoritative_projection(
        self,
        state: _ViewerSessionProjection,
        event: Mapping[str, Any],
    ) -> None:
        summary = _copy_mapping(event.get("summary"))
        options = _copy_mapping(event.get("options"))
        playback = _normalize_playback_payload(
            event.get("playback_state") or options,
            fallback_state=state.playback_state,
            fallback_step_index=state.step_index,
        )
        camera_state = _copy_mapping(event.get("camera_state"))
        if not camera_state:
            camera_state = _copy_mapping(summary.get("camera_state") or summary.get("camera"))
        state.backend_id = (
            _string(event.get("backend_id"))
            or _string(options.get("backend_id"))
            or _string(summary.get("backend_id"))
            or state.backend_id
        )
        state.transport_revision = _coerce_step_index(
            event.get(
                "transport_revision",
                options.get("transport_revision", summary.get("transport_revision", state.transport_revision)),
            ),
            default=state.transport_revision,
        )
        state.live_open_status = (
            _string(event.get("live_open_status"))
            or _string(options.get("live_open_status"))
            or _string(summary.get("live_open_status"))
            or state.live_open_status
        )
        state.live_open_blocker = (
            _copy_mapping(event.get("live_open_blocker"))
            or _copy_mapping(options.get("live_open_blocker"))
            or _copy_mapping(summary.get("live_open_blocker"))
        )
        state.data_refs = _copy_mapping(event.get("data_refs"))
        state.transport = _copy_mapping(event.get("transport"))
        state.camera_state = camera_state
        state.summary = summary
        state.options = options
        state.playback_state = playback["state"]
        state.step_index = playback["step_index"]
        state.live_policy = _normalize_live_policy(options.get("live_policy", state.live_policy))
        state.keep_live = bool(options.get("keep_live", state.keep_live))
        state.cache_state = (
            _string(summary.get("cache_state"))
            or _string(options.get("cache_state"))
            or state.cache_state
            or "empty"
        )
        state.invalidated_reason = _string(summary.get("invalidated_reason"))
        state.close_reason = _string(summary.get("close_reason") or options.get("reason"))

    def _on_workspace_changed(self, _workspace_id: str) -> None:
        self.active_workspace_changed.emit()
        self.sessions_changed.emit()
        self._sync_live_policy(self._current_workspace_id())

    def _on_selection_changed(self) -> None:
        workspace_id = self._current_workspace_id()
        if workspace_id in self._focused_viewer_node_by_workspace:
            selected_lookup = _copy_mapping(getattr(self._scene_bridge, "selected_node_lookup", {}))
            focused_node_id = self._focused_viewer_node_id(workspace_id)
            if focused_node_id and not bool(selected_lookup.get(focused_node_id, False)):
                self._focused_viewer_node_by_workspace[workspace_id] = ""
        self._sync_live_policy(workspace_id)

    def _on_nodes_changed(self) -> None:
        workspace_id = self._current_workspace_id()
        if not workspace_id:
            return
        workspace_node_ids = self._workspace_node_ids(workspace_id)
        if workspace_node_ids is None:
            return
        removed_keys = [
            key
            for key, state in self._sessions.items()
            if state.workspace_id == workspace_id and state.node_id not in workspace_node_ids
        ]
        if removed_keys:
            for key in removed_keys:
                self._sessions.pop(key, None)
            self.sessions_changed.emit()
        self._prune_focused_viewer_node(workspace_id, workspace_node_ids)
        self._sync_live_policy(workspace_id)

    def _on_edges_changed(self) -> None:
        self._sync_live_policy(self._current_workspace_id())

    def _workspace_node_ids(self, workspace_id: str) -> set[str] | None:
        shell_window = self._shell_window
        if shell_window is None:
            return None
        model = getattr(shell_window, "model", None)
        project = getattr(model, "project", None)
        workspaces = getattr(project, "workspaces", None)
        if not isinstance(workspaces, dict):
            return None
        workspace = workspaces.get(workspace_id)
        if workspace is None:
            return None
        nodes = getattr(workspace, "nodes", None)
        if not isinstance(nodes, dict):
            return None
        return {str(node_id) for node_id in nodes}

    def _workspace_open_states(self, workspace_id: str) -> list[_ViewerSessionProjection]:
        states = [
            state
            for state in self._sessions.values()
            if state.workspace_id == workspace_id and state.phase in _OPEN_SESSION_PHASES
        ]
        states.sort(key=lambda state: state.node_id)
        return states

    def _focused_viewer_node_id(self, workspace_id: str) -> str:
        return _string(self._focused_viewer_node_by_workspace.get(_string(workspace_id), ""))

    def _set_focused_viewer_node(self, workspace_id: str, node_id: str) -> bool:
        normalized_workspace_id = _string(workspace_id)
        if not normalized_workspace_id:
            return False
        normalized_node_id = _string(node_id)
        current_node_id = self._focused_viewer_node_by_workspace.get(normalized_workspace_id)
        if current_node_id == normalized_node_id:
            return False
        self._focused_viewer_node_by_workspace[normalized_workspace_id] = normalized_node_id
        return True

    def _clear_focused_viewer_node_if_matches(self, workspace_id: str, node_id: str) -> bool:
        normalized_workspace_id = _string(workspace_id)
        normalized_node_id = _string(node_id)
        if not normalized_workspace_id or not normalized_node_id:
            return False
        if self._focused_viewer_node_by_workspace.get(normalized_workspace_id) != normalized_node_id:
            return False
        self._focused_viewer_node_by_workspace[normalized_workspace_id] = ""
        return True

    def _prune_focused_viewer_node(self, workspace_id: str, available_node_ids: set[str]) -> bool:
        normalized_workspace_id = _string(workspace_id)
        if not normalized_workspace_id or normalized_workspace_id not in self._focused_viewer_node_by_workspace:
            return False
        focused_node_id = self._focused_viewer_node_id(normalized_workspace_id)
        if not focused_node_id or focused_node_id in available_node_ids:
            return False
        self._focused_viewer_node_by_workspace[normalized_workspace_id] = ""
        return True

    @staticmethod
    def _has_proxy_preview(state: _ViewerSessionProjection) -> bool:
        return bool(state.data_refs.get("png") or state.data_refs.get("preview"))

    def _desired_live_mode_map(self, workspace_id: str) -> dict[tuple[str, str], str]:
        desired_modes: dict[tuple[str, str], str] = {}
        if not workspace_id:
            return desired_modes
        states = self._workspace_open_states(workspace_id)
        if not states:
            return desired_modes

        keep_live_keys: list[tuple[str, str]] = []
        focus_only_keys: list[tuple[str, str]] = []
        for state in states:
            key = (state.workspace_id, state.node_id)
            effective_options = self._effective_options(state)
            if bool(effective_options.get("keep_live", state.keep_live)) or _normalize_live_policy(
                effective_options.get("live_policy", state.live_policy)
            ) == _LIVE_POLICY_KEEP_LIVE:
                keep_live_keys.append(key)
            else:
                focus_only_keys.append(key)

        focus_entry_present = workspace_id in self._focused_viewer_node_by_workspace
        focused_node_id = self._focused_viewer_node_id(workspace_id)
        chosen_focus_key: tuple[str, str] | None = None
        if focused_node_id:
            for key in focus_only_keys:
                if key[1] == focused_node_id:
                    chosen_focus_key = key
                    break
        if chosen_focus_key is None and not focus_entry_present:
            selected_lookup = _copy_mapping(getattr(self._scene_bridge, "selected_node_lookup", {}))
            for key in focus_only_keys:
                if bool(selected_lookup.get(key[1], False)):
                    chosen_focus_key = key
                    break
        if chosen_focus_key is None and not focus_entry_present:
            for state in states:
                key = (state.workspace_id, state.node_id)
                if key not in focus_only_keys:
                    continue
                if _normalize_live_mode(self._effective_options(state).get("live_mode")) == _LIVE_MODE_FULL:
                    chosen_focus_key = key
                    break

        for key in keep_live_keys:
            desired_modes[key] = _LIVE_MODE_FULL
        if chosen_focus_key is not None:
            desired_modes[chosen_focus_key] = _LIVE_MODE_FULL
        for key in focus_only_keys:
            desired_modes.setdefault(key, _LIVE_MODE_PROXY)
        return desired_modes

    def _sync_live_policy(self, workspace_id: str) -> None:
        normalized_workspace_id = _string(workspace_id)
        if not normalized_workspace_id or self._policy_sync_in_progress:
            return
        desired_modes = self._desired_live_mode_map(normalized_workspace_id)
        if not desired_modes:
            return

        self._policy_sync_in_progress = True
        changed = False
        try:
            for state in self._workspace_open_states(normalized_workspace_id):
                if state.phase != "open":
                    continue
                desired_mode = desired_modes.get((state.workspace_id, state.node_id), _LIVE_MODE_PROXY)
                changed = self._apply_desired_live_mode(state, desired_mode) or changed
        finally:
            self._policy_sync_in_progress = False

        if changed:
            self.sessions_changed.emit()

    def _apply_desired_live_mode(self, state: _ViewerSessionProjection, desired_mode: str) -> bool:
        normalized_desired_mode = _normalize_live_mode(desired_mode)
        current_live_mode = _normalize_live_mode(self._effective_options(state).get("live_mode"))

        if normalized_desired_mode == _LIVE_MODE_PROXY:
            if current_live_mode != _LIVE_MODE_PROXY:
                request_options = self._request_options(state, {"live_mode": _LIVE_MODE_PROXY})
                request_id = self._send_execution_command(
                    "update_viewer_session",
                    workspace_id=state.workspace_id,
                    node_id=state.node_id,
                    session_id=state.session_id,
                    backend_id=state.backend_id,
                    camera_state=state.camera_state,
                    playback_state={
                        "state": state.playback_state,
                        "step_index": int(state.step_index),
                    },
                    options=request_options,
                )
                if not request_id:
                    state.phase = "error"
                    state.last_command = "set_live_mode"
                    return True
                state.request_id = request_id
                state.last_command = "set_live_mode"
                state.pending_proxy_snapshot_refresh = True
                self._merge_pending_projection(state, options={"live_mode": _LIVE_MODE_PROXY})
                return True
            if state.pending_materialization:
                return False
            if not (state.pending_proxy_snapshot_refresh or not self._has_proxy_preview(state)):
                return False
            materialize_requested = self._send_materialize_command(
                state,
                option_updates={
                    "live_mode": _LIVE_MODE_PROXY,
                    "output_profile": "stored",
                    "export_formats": ["png"],
                },
            )
            state.pending_proxy_snapshot_refresh = False
            return materialize_requested or state.phase == "error"

        state.pending_proxy_snapshot_refresh = False
        if _string(state.live_open_status).lower() != "ready":
            return False
        if state.cache_state == "live_ready":
            if current_live_mode == _LIVE_MODE_FULL:
                return False
            request_options = self._request_options(state, {"live_mode": _LIVE_MODE_FULL})
            request_id = self._send_execution_command(
                "update_viewer_session",
                workspace_id=state.workspace_id,
                node_id=state.node_id,
                session_id=state.session_id,
                backend_id=state.backend_id,
                camera_state=state.camera_state,
                playback_state={
                    "state": state.playback_state,
                    "step_index": int(state.step_index),
                },
                options=request_options,
            )
            if not request_id:
                state.phase = "error"
                state.last_command = "set_live_mode"
                return True
            state.request_id = request_id
            state.last_command = "set_live_mode"
            self._merge_pending_projection(state, options={"live_mode": _LIVE_MODE_FULL})
            return True

        if state.pending_materialization:
            return False
        materialize_requested = self._send_materialize_command(
            state,
            option_updates={"live_mode": _LIVE_MODE_FULL},
        )
        return materialize_requested or state.phase == "error"

    def _set_last_error(self, value: str) -> None:
        normalized = _string(value)
        if normalized == self._last_error:
            return
        self._last_error = normalized
        self.last_error_changed.emit()


__all__ = ["ViewerSessionBridge"]
