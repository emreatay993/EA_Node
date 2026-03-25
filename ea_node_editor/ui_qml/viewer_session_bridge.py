from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge


@dataclass(slots=True)
class _ViewerSessionState:
    workspace_id: str
    node_id: str
    session_id: str
    phase: str = "closed"
    request_id: str = ""
    last_command: str = ""
    last_error: str = ""
    playback_state: str = "paused"
    step_index: int = 0
    live_policy: str = "focus_only"
    keep_live: bool = False
    cache_state: str = "empty"
    invalidated_reason: str = ""
    close_reason: str = ""
    data_refs: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)

    def payload(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "node_id": self.node_id,
            "session_id": self.session_id,
            "phase": self.phase,
            "request_id": self.request_id,
            "last_command": self.last_command,
            "last_error": self.last_error,
            "playback_state": self.playback_state,
            "step_index": self.step_index,
            "live_policy": self.live_policy,
            "keep_live": self.keep_live,
            "cache_state": self.cache_state,
            "invalidated_reason": self.invalidated_reason,
            "close_reason": self.close_reason,
            "data_refs": copy.deepcopy(self.data_refs),
            "summary": copy.deepcopy(self.summary),
            "options": copy.deepcopy(self.options),
        }


def _copy_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {str(key): copy.deepcopy(item) for key, item in value.items()}


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
        self._sessions: dict[tuple[str, str], _ViewerSessionState] = {}
        self._last_error = ""

        if shell_window is not None:
            execution_event = getattr(shell_window, "execution_event", None)
            if execution_event is not None:
                execution_event.connect(self._handle_execution_event)
        if scene_bridge is not None:
            scene_bridge.workspace_changed.connect(self._on_workspace_changed)
            scene_bridge.nodes_changed.connect(self._on_nodes_changed)
            scene_bridge.edges_changed.connect(self._on_edges_changed)

    @property
    def shell_window(self) -> "ShellWindow | None":
        return self._shell_window

    @property
    def scene_bridge(self) -> "GraphSceneBridge | None":
        return self._scene_bridge

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
        normalized_node_id = str(node_id).strip()
        if not workspace_id or not normalized_node_id:
            return {}
        state = self._sessions.get((workspace_id, normalized_node_id))
        return state.payload() if state is not None else {}

    @pyqtSlot(str, result=str)
    @pyqtSlot(str, "QVariantMap", result=str)
    def open(self, node_id: str, payload: Any = None) -> str:
        workspace_id = self._workspace_id_from_payload(payload)
        normalized_node_id = str(node_id).strip()
        if not workspace_id or not normalized_node_id:
            return ""

        state = self._ensure_session_state(workspace_id, normalized_node_id)
        payload_map = _copy_mapping(payload)
        data_refs = _copy_mapping(payload_map.get("data_refs"))
        summary = _copy_mapping(payload_map.get("summary"))
        option_updates = _copy_mapping(payload_map.get("options"))

        state.phase = "opening"
        state.invalidated_reason = ""
        state.close_reason = ""
        state.last_error = ""
        state.last_command = "open"
        state.summary.pop("invalidated_reason", None)
        state.summary.pop("demoted_reason", None)
        state.summary.pop("close_reason", None)
        if data_refs:
            state.data_refs = copy.deepcopy(data_refs)
        state.summary.update(summary)
        self._merge_session_options(state, option_updates)

        request_options = self._request_options(state, option_updates)
        request_id = self._send_execution_command(
            "open_viewer_session",
            workspace_id=workspace_id,
            node_id=normalized_node_id,
            session_id=state.session_id,
            data_refs=data_refs,
            summary=summary,
            options=request_options,
        )
        if not request_id:
            state.phase = "error"
            state.last_command = "open"
            self.sessions_changed.emit()
            return ""

        state.request_id = request_id
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
        request_options = self._request_options(state, option_updates)
        request_id = self._send_execution_command(
            "close_viewer_session",
            workspace_id=state.workspace_id,
            node_id=state.node_id,
            session_id=state.session_id,
            options=request_options,
        )
        if not request_id:
            state.phase = "error"
            state.last_command = "close"
            self.sessions_changed.emit()
            return False

        state.request_id = request_id
        state.last_command = "close"
        state.phase = "closing"
        state.close_reason = str(option_updates.get("reason", "")).strip()
        self.sessions_changed.emit()
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
        step_index = state.step_index + 1
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
        normalized_policy = str(live_policy).strip() or "focus_only"
        return self._update_session_command(
            node_id,
            payload,
            command_name="set_live_policy",
            option_updates={"live_policy": normalized_policy},
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

    def invalidate_workspace_sessions(
        self,
        workspace_id: str,
        *,
        reason: str,
        run_id: str = "",
    ) -> None:
        normalized_workspace_id = str(workspace_id).strip()
        normalized_reason = str(reason).strip()
        if not normalized_workspace_id or not normalized_reason:
            return
        changed = False
        for state in self._sessions.values():
            if state.workspace_id != normalized_workspace_id:
                continue
            self._invalidate_state(state, normalized_reason)
            if run_id:
                state.summary["run_id"] = run_id
            changed = True
        if changed:
            self.sessions_changed.emit()

    def invalidate_all_sessions(self, *, reason: str) -> None:
        normalized_reason = str(reason).strip()
        if not normalized_reason or not self._sessions:
            return
        for state in self._sessions.values():
            self._invalidate_state(state, normalized_reason)
        self.sessions_changed.emit()

    def reset_all_sessions(self, *, reason: str = "") -> None:
        if reason:
            self._set_last_error("")
        if not self._sessions:
            return
        self._sessions.clear()
        self.sessions_changed.emit()

    def _active_session(self, node_id: str, payload: Any = None) -> _ViewerSessionState | None:
        workspace_id = self._workspace_id_from_payload(payload)
        normalized_node_id = str(node_id).strip()
        if not workspace_id or not normalized_node_id:
            return None
        state = self._sessions.get((workspace_id, normalized_node_id))
        if state is None or state.phase in {"closed", "invalidated"}:
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
        self._merge_session_options(state, merged_option_updates)

        request_options = self._request_options(state, merged_option_updates)
        request_id = self._send_execution_command(
            "update_viewer_session",
            workspace_id=state.workspace_id,
            node_id=state.node_id,
            session_id=state.session_id,
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
        state.summary.update(summary)
        self.sessions_changed.emit()
        return True

    def _merge_session_options(self, state: _ViewerSessionState, options: dict[str, Any]) -> None:
        state.options.update(copy.deepcopy(options))
        state.live_policy = str(state.options.get("live_policy", state.live_policy)).strip() or "focus_only"
        state.keep_live = bool(state.options.get("keep_live", state.keep_live))
        playback_state = str(state.options.get("playback_state", state.playback_state)).strip()
        state.playback_state = playback_state or "paused"
        if "step_index" in state.options:
            try:
                state.step_index = int(state.options.get("step_index", state.step_index))
            except (TypeError, ValueError):
                pass

    def _request_options(self, state: _ViewerSessionState, option_updates: dict[str, Any]) -> dict[str, Any]:
        options = copy.deepcopy(state.options)
        options.update(copy.deepcopy(option_updates))
        options["live_policy"] = str(options.get("live_policy", state.live_policy)).strip() or "focus_only"
        options["keep_live"] = bool(options.get("keep_live", state.keep_live))
        playback_state = str(options.get("playback_state", state.playback_state)).strip()
        options["playback_state"] = playback_state or "paused"
        options["live_mode"] = str(options.get("live_mode", "proxy")).strip() or "proxy"
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
        return str(request_id or "")

    def _ensure_session_state(self, workspace_id: str, node_id: str) -> _ViewerSessionState:
        session_key = (workspace_id, node_id)
        state = self._sessions.get(session_key)
        if state is not None:
            return state
        state = _ViewerSessionState(
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
        workspace_id = str(payload_map.get("workspace_id", "")).strip()
        if workspace_id:
            return workspace_id
        return self._current_workspace_id()

    def _current_workspace_id(self) -> str:
        if self._scene_bridge is not None:
            workspace_id = str(getattr(self._scene_bridge, "workspace_id", "")).strip()
            if workspace_id:
                return workspace_id
        workspace_manager = getattr(self._shell_window, "workspace_manager", None)
        if workspace_manager is None:
            return ""
        active_workspace_id = getattr(workspace_manager, "active_workspace_id", None)
        if not callable(active_workspace_id):
            return ""
        try:
            return str(active_workspace_id()).strip()
        except Exception:  # noqa: BLE001
            return ""

    def _handle_execution_event(self, event: dict[str, Any]) -> None:
        event_type = str(event.get("type", "")).strip()
        if event_type not in {
            "viewer_session_opened",
            "viewer_session_updated",
            "viewer_session_closed",
            "viewer_data_materialized",
            "viewer_session_failed",
        }:
            return

        workspace_id = str(event.get("workspace_id", "")).strip()
        node_id = str(event.get("node_id", "")).strip()
        if not workspace_id or not node_id:
            return

        state = self._ensure_session_state(workspace_id, node_id)
        state.session_id = str(event.get("session_id", state.session_id)).strip() or state.session_id
        state.request_id = str(event.get("request_id", state.request_id)).strip()

        if event_type == "viewer_session_failed":
            state.phase = "error"
            state.last_command = str(event.get("command", "")).strip()
            state.last_error = str(event.get("error", "")).strip()
            self._set_last_error(state.last_error)
            self.sessions_changed.emit()
            return

        self._set_last_error("")
        state.last_error = ""
        state.data_refs = _copy_mapping(event.get("data_refs", state.data_refs))
        state.summary = _copy_mapping(event.get("summary", state.summary))
        state.options = _copy_mapping(event.get("options", state.options))
        self._merge_session_options(state, {})
        state.cache_state = str(
            state.summary.get(
                "cache_state",
                state.options.get("cache_state", state.cache_state or "empty"),
            )
        ).strip() or "empty"
        state.invalidated_reason = str(state.summary.get("invalidated_reason", "")).strip()
        state.close_reason = str(
            state.summary.get("close_reason", state.options.get("reason", state.close_reason))
        ).strip()

        if event_type == "viewer_session_closed":
            state.phase = "closed"
            state.data_refs.clear()
        elif state.invalidated_reason:
            state.phase = "invalidated"
        else:
            state.phase = "open"
        self.sessions_changed.emit()

    def _on_workspace_changed(self, _workspace_id: str) -> None:
        self.active_workspace_changed.emit()
        self.sessions_changed.emit()

    def _on_nodes_changed(self) -> None:
        self._handle_graph_mutation()

    def _on_edges_changed(self) -> None:
        self._handle_graph_mutation()

    def _handle_graph_mutation(self) -> None:
        workspace_id = self._current_workspace_id()
        if not workspace_id:
            return
        workspace_node_ids = self._workspace_node_ids(workspace_id)
        changed = False
        for state in self._sessions.values():
            if state.workspace_id != workspace_id:
                continue
            if state.phase in {"closed", "invalidated"}:
                continue
            if workspace_node_ids is not None and state.node_id not in workspace_node_ids:
                self._invalidate_state(state, "graph_mutation")
                changed = True
                continue
            if self._demote_state_to_proxy(state, reason="graph_mutation"):
                changed = True
        if changed:
            self.sessions_changed.emit()

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

    @staticmethod
    def _demote_state_to_proxy(state: _ViewerSessionState, *, reason: str) -> bool:
        options_before = copy.deepcopy(state.options)
        summary_before = copy.deepcopy(state.summary)
        cache_before = state.cache_state
        if state.options.get("live_mode") != "proxy":
            state.options["live_mode"] = "proxy"
        if state.cache_state == "live_ready":
            state.cache_state = "proxy_ready"
        state.summary["demoted_reason"] = reason
        return (
            state.options != options_before
            or state.summary != summary_before
            or state.cache_state != cache_before
        )

    @staticmethod
    def _invalidate_state(state: _ViewerSessionState, reason: str) -> None:
        state.phase = "invalidated"
        state.invalidated_reason = reason
        state.cache_state = "invalidated"
        state.data_refs.clear()
        state.close_reason = ""
        state.options["live_mode"] = "proxy"
        state.summary["invalidated_reason"] = reason

    def _set_last_error(self, value: str) -> None:
        normalized = str(value).strip()
        if normalized == self._last_error:
            return
        self._last_error = normalized
        self.last_error_changed.emit()


__all__ = ["ViewerSessionBridge"]
