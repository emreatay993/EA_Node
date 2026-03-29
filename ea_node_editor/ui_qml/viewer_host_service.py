from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QObject, QTimer, pyqtProperty, pyqtSignal, pyqtSlot

from ea_node_editor.ui_qml.embedded_viewer_overlay_manager import (
    EmbeddedViewerOverlayManager,
    EmbeddedViewerOverlaySpec,
)
from ea_node_editor.ui_qml.viewer_widget_binder import (
    ViewerWidgetBindRequest,
    ViewerWidgetBinder,
    ViewerWidgetBinderRegistry,
    ViewerWidgetReleaseRequest,
)

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow
    from ea_node_editor.ui_qml.viewer_session_bridge import ViewerSessionBridge

_OverlayKey = tuple[str, str]
_VIEWER_EVENT_TYPES = frozenset(
    {
        "viewer_session_opened",
        "viewer_session_updated",
        "viewer_data_materialized",
        "viewer_session_closed",
        "viewer_session_failed",
    }
)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _string(value: Any) -> str:
    return str(value).strip()


def _coerce_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return tuple(sorted((_string(key), _freeze_value(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def _playback_state_from_projection(
    state: Mapping[str, Any],
    options: Mapping[str, Any],
    fallback: Mapping[str, Any],
) -> dict[str, Any]:
    playback = _mapping(options.get("playback"))
    if playback:
        return playback
    base = _mapping(fallback)
    playback_state = _string(options.get("playback_state", state.get("playback_state", base.get("state", "paused"))))
    step_index = _coerce_int(options.get("step_index", state.get("step_index", base.get("step_index", 0))), default=0)
    return {
        "state": playback_state or "paused",
        "step_index": step_index,
    }


@dataclass(slots=True, frozen=True)
class _ViewerHostSessionSnapshot:
    workspace_id: str
    node_id: str
    session_id: str
    backend_id: str
    phase: str
    cache_state: str
    live_mode: str
    transport_revision: int
    live_open_status: str
    live_open_blocker: dict[str, Any] = field(default_factory=dict)
    data_refs: dict[str, Any] = field(default_factory=dict)
    transport: dict[str, Any] = field(default_factory=dict)
    camera_state: dict[str, Any] = field(default_factory=dict)
    playback_state: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)

    @property
    def overlay_key(self) -> _OverlayKey:
        return (self.workspace_id, self.node_id)

    def overlay_spec(self) -> EmbeddedViewerOverlaySpec:
        return EmbeddedViewerOverlaySpec(
            workspace_id=self.workspace_id,
            node_id=self.node_id,
            session_id=self.session_id,
        )

    def bind_request(self, *, container, current_widget) -> ViewerWidgetBindRequest:  # noqa: ANN001
        return ViewerWidgetBindRequest(
            workspace_id=self.workspace_id,
            node_id=self.node_id,
            session_id=self.session_id,
            backend_id=self.backend_id,
            transport_revision=self.transport_revision,
            live_mode=self.live_mode,
            cache_state=self.cache_state,
            live_open_status=self.live_open_status,
            live_open_blocker=copy.deepcopy(self.live_open_blocker),
            data_refs=copy.deepcopy(self.data_refs),
            transport=copy.deepcopy(self.transport),
            camera_state=copy.deepcopy(self.camera_state),
            playback_state=copy.deepcopy(self.playback_state),
            summary=copy.deepcopy(self.summary),
            options=copy.deepcopy(self.options),
            container=container,
            current_widget=current_widget,
        )

    def release_request(self, *, container, widget, reason: str) -> ViewerWidgetReleaseRequest:  # noqa: ANN001
        return ViewerWidgetReleaseRequest(
            workspace_id=self.workspace_id,
            node_id=self.node_id,
            session_id=self.session_id,
            backend_id=self.backend_id,
            transport_revision=self.transport_revision,
            data_refs=copy.deepcopy(self.data_refs),
            transport=copy.deepcopy(self.transport),
            summary=copy.deepcopy(self.summary),
            options=copy.deepcopy(self.options),
            container=container,
            widget=widget,
            reason=reason,
        )


@dataclass(slots=True)
class _BoundOverlay:
    binder: ViewerWidgetBinder
    snapshot: _ViewerHostSessionSnapshot
    signature: tuple[Any, ...]


class ViewerHostService(QObject):
    state_changed = pyqtSignal()
    last_error_changed = pyqtSignal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        shell_window: "ShellWindow | None" = None,
        viewer_session_bridge: "ViewerSessionBridge | None" = None,
        overlay_manager: EmbeddedViewerOverlayManager | None = None,
    ) -> None:
        super().__init__(parent)
        self._shell_window = shell_window
        self._viewer_session_bridge = viewer_session_bridge
        self._overlay_manager = overlay_manager
        self._binder_registry = ViewerWidgetBinderRegistry()
        self._authoritative_sessions: dict[_OverlayKey, _ViewerHostSessionSnapshot] = {}
        self._bound_overlays: dict[_OverlayKey, _BoundOverlay] = {}
        self._last_error = ""
        self._sync_queued = False

        self._connect_signals()
        self._schedule_sync()

    @property
    def binder_registry(self) -> ViewerWidgetBinderRegistry:
        return self._binder_registry

    @property
    def overlay_manager(self) -> EmbeddedViewerOverlayManager | None:
        return self._overlay_manager

    @pyqtProperty(int, notify=state_changed)
    def active_overlay_count(self) -> int:
        return len(self._bound_overlays)

    @pyqtProperty(str, notify=last_error_changed)
    def last_error(self) -> str:
        return self._last_error

    def register_binder(self, backend_id: str, binder: ViewerWidgetBinder) -> None:
        self._binder_registry.register(backend_id, binder)
        self._schedule_sync()

    def set_overlay_manager(self, overlay_manager: EmbeddedViewerOverlayManager | None) -> None:
        if self._overlay_manager is overlay_manager:
            return
        self._release_all_bindings(reason="overlay_manager_replaced")
        previous_overlay_manager = self._overlay_manager
        self._overlay_manager = overlay_manager
        if previous_overlay_manager is not None:
            previous_overlay_manager.set_active_overlays(())
        self._schedule_sync()

    def reset(self, *, reason: str = "") -> None:
        self._authoritative_sessions.clear()
        self._release_all_bindings(reason=reason or "reset")
        overlay_manager = self._overlay_manager
        if overlay_manager is not None:
            overlay_manager.set_active_overlays(())
        self._set_last_error("")
        self.state_changed.emit()

    def _connect_signals(self) -> None:
        self._connect_signal(self._viewer_session_bridge, "sessions_changed", self._schedule_sync)
        self._connect_signal(self._viewer_session_bridge, "active_workspace_changed", self._schedule_sync)
        self._connect_signal(self._shell_window, "execution_event", self._handle_execution_event)

    @staticmethod
    def _connect_signal(source: object | None, name: str, slot) -> None:  # noqa: ANN001
        signal = getattr(source, name, None) if source is not None else None
        if signal is not None and hasattr(signal, "connect"):
            signal.connect(slot)

    def _schedule_sync(self) -> None:
        if self._sync_queued:
            return
        self._sync_queued = True
        QTimer.singleShot(0, self._run_queued_sync)

    @pyqtSlot()
    def _run_queued_sync(self) -> None:
        self._sync_queued = False
        self.sync()

    @pyqtSlot()
    def sync(self) -> None:
        overlay_manager = self._overlay_manager
        bridge = self._viewer_session_bridge
        if overlay_manager is None or bridge is None:
            self._release_all_bindings(reason="overlay_manager_unavailable")
            self.state_changed.emit()
            return

        projected_sessions = getattr(bridge, "sessions_model", [])
        desired_overlays: dict[_OverlayKey, tuple[_ViewerHostSessionSnapshot, ViewerWidgetBinder]] = {}
        errors: list[str] = []
        for item in projected_sessions if isinstance(projected_sessions, list) else []:
            projected_state = _mapping(item)
            if not self._should_host_overlay(projected_state):
                continue
            snapshot = self._snapshot_from_projected_state(projected_state)
            if snapshot is None:
                continue
            binder = self._binder_registry.lookup(snapshot.backend_id)
            if binder is None:
                errors.append(f"No viewer widget binder registered for backend '{snapshot.backend_id}'.")
                continue
            desired_overlays[snapshot.overlay_key] = (snapshot, binder)

        for key, bound in list(self._bound_overlays.items()):
            desired = desired_overlays.get(key)
            if desired is None or desired[0].backend_id != bound.snapshot.backend_id or desired[1] is not bound.binder:
                self._release_binding(key, reason="inactive")

        overlay_manager.set_active_overlays(
            snapshot.overlay_spec()
            for snapshot, _binder in desired_overlays.values()
        )

        for key, (snapshot, binder) in desired_overlays.items():
            container = overlay_manager.overlay_container(snapshot.node_id, workspace_id=snapshot.workspace_id)
            if container is None:
                continue
            current_widget = overlay_manager.overlay_widget(snapshot.node_id, workspace_id=snapshot.workspace_id)
            signature = self._binding_signature(snapshot)
            bound = self._bound_overlays.get(key)
            if bound is not None and bound.binder is binder and bound.signature == signature and current_widget is not None:
                continue
            try:
                widget = binder.bind_widget(
                    snapshot.bind_request(
                        container=container,
                        current_widget=current_widget,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc))
                continue
            if widget is None:
                errors.append(f"Binder '{snapshot.backend_id}' did not return a widget.")
                continue
            overlay_manager.attach_overlay_widget(
                snapshot.node_id,
                widget,
                workspace_id=snapshot.workspace_id,
            )
            self._bound_overlays[key] = _BoundOverlay(
                binder=binder,
                snapshot=snapshot,
                signature=signature,
            )

        self._set_last_error(errors[0] if errors else "")
        self.state_changed.emit()

    def _release_all_bindings(self, *, reason: str) -> None:
        for key in list(self._bound_overlays):
            self._release_binding(key, reason=reason)

    def _release_binding(self, key: _OverlayKey, *, reason: str) -> None:
        bound = self._bound_overlays.pop(key, None)
        if bound is None:
            return
        overlay_manager = self._overlay_manager
        container = None
        widget = None
        if overlay_manager is not None:
            container = overlay_manager.overlay_container(bound.snapshot.node_id, workspace_id=bound.snapshot.workspace_id)
            widget = overlay_manager.overlay_widget(bound.snapshot.node_id, workspace_id=bound.snapshot.workspace_id)
        try:
            bound.binder.release_widget(
                bound.snapshot.release_request(
                    container=container,
                    widget=widget,
                    reason=reason,
                )
            )
        except Exception as exc:  # noqa: BLE001
            self._set_last_error(str(exc))

    def _snapshot_from_projected_state(
        self,
        projected_state: Mapping[str, Any],
    ) -> _ViewerHostSessionSnapshot | None:
        workspace_id = _string(projected_state.get("workspace_id"))
        node_id = _string(projected_state.get("node_id"))
        if not workspace_id or not node_id:
            return None
        key = (workspace_id, node_id)
        authoritative = self._authoritative_sessions.get(key)
        summary = copy.deepcopy(authoritative.summary) if authoritative is not None else {}
        summary.update(_mapping(projected_state.get("summary")))
        options = copy.deepcopy(authoritative.options) if authoritative is not None else {}
        options.update(_mapping(projected_state.get("options")))
        data_refs = copy.deepcopy(authoritative.data_refs) if authoritative is not None else {}
        data_refs.update(_mapping(projected_state.get("data_refs")))
        transport = copy.deepcopy(authoritative.transport) if authoritative is not None else {}
        live_open_blocker = _mapping(options.get("live_open_blocker"))
        if not live_open_blocker:
            live_open_blocker = _mapping(summary.get("live_open_blocker"))
        if not live_open_blocker and authoritative is not None:
            live_open_blocker = copy.deepcopy(authoritative.live_open_blocker)
        camera_state = _mapping(summary.get("camera_state") or summary.get("camera"))
        if not camera_state and authoritative is not None:
            camera_state = copy.deepcopy(authoritative.camera_state)
        playback_state = _playback_state_from_projection(
            projected_state,
            options,
            authoritative.playback_state if authoritative is not None else {},
        )
        backend_id = _string(
            options.get("backend_id")
            or summary.get("backend_id")
            or transport.get("backend_id")
            or (authoritative.backend_id if authoritative is not None else "")
        )
        if not backend_id:
            return None
        session_id = _string(projected_state.get("session_id") or (authoritative.session_id if authoritative is not None else ""))
        transport_revision = _coerce_int(
            options.get("transport_revision", summary.get("transport_revision", authoritative.transport_revision if authoritative is not None else 0)),
            default=0,
        )
        live_open_status = _string(
            options.get("live_open_status")
            or summary.get("live_open_status")
            or (authoritative.live_open_status if authoritative is not None else "")
        )
        return _ViewerHostSessionSnapshot(
            workspace_id=workspace_id,
            node_id=node_id,
            session_id=session_id,
            backend_id=backend_id,
            phase=_string(projected_state.get("phase")),
            cache_state=_string(projected_state.get("cache_state") or summary.get("cache_state") or options.get("cache_state")),
            live_mode=_string(options.get("live_mode")),
            transport_revision=transport_revision,
            live_open_status=live_open_status,
            live_open_blocker=live_open_blocker,
            data_refs=data_refs,
            transport=transport,
            camera_state=camera_state,
            playback_state=playback_state,
            summary=summary,
            options=options,
        )

    def _handle_execution_event(self, event: dict[str, Any]) -> None:
        event_type = _string(event.get("type"))
        if event_type not in _VIEWER_EVENT_TYPES:
            return
        workspace_id = _string(event.get("workspace_id"))
        node_id = _string(event.get("node_id"))
        if not workspace_id or not node_id:
            return
        key = (workspace_id, node_id)
        if event_type in {"viewer_session_closed", "viewer_session_failed"}:
            self._authoritative_sessions.pop(key, None)
            if event_type == "viewer_session_failed":
                self._set_last_error(_string(event.get("error")))
            self._schedule_sync()
            return

        summary = _mapping(event.get("summary"))
        options = _mapping(event.get("options"))
        authoritative = _ViewerHostSessionSnapshot(
            workspace_id=workspace_id,
            node_id=node_id,
            session_id=_string(event.get("session_id")),
            backend_id=_string(event.get("backend_id") or options.get("backend_id") or summary.get("backend_id")),
            phase="open",
            cache_state=_string(summary.get("cache_state") or options.get("cache_state")),
            live_mode=_string(options.get("live_mode")),
            transport_revision=_coerce_int(event.get("transport_revision"), default=0),
            live_open_status=_string(event.get("live_open_status")),
            live_open_blocker=_mapping(event.get("live_open_blocker")),
            data_refs=_mapping(event.get("data_refs")),
            transport=_mapping(event.get("transport")),
            camera_state=_mapping(event.get("camera_state")),
            playback_state=_mapping(event.get("playback_state")),
            summary=summary,
            options=options,
        )
        self._authoritative_sessions[key] = authoritative
        self._schedule_sync()

    @staticmethod
    def _should_host_overlay(projected_state: Mapping[str, Any]) -> bool:
        if _string(projected_state.get("phase")) != "open":
            return False
        options = _mapping(projected_state.get("options"))
        live_mode = _string(options.get("live_mode", projected_state.get("live_mode")))
        if live_mode != "full":
            return False
        live_open_status = _string(
            options.get("live_open_status")
            or _mapping(projected_state.get("summary")).get("live_open_status")
        )
        cache_state = _string(
            projected_state.get("cache_state")
            or options.get("cache_state")
            or _mapping(projected_state.get("summary")).get("cache_state")
        )
        return live_open_status == "ready" or cache_state == "live_ready"

    @staticmethod
    def _binding_signature(snapshot: _ViewerHostSessionSnapshot) -> tuple[Any, ...]:
        return (
            snapshot.session_id,
            snapshot.backend_id,
            snapshot.transport_revision,
            snapshot.live_mode,
            snapshot.cache_state,
            snapshot.live_open_status,
            _freeze_value(snapshot.live_open_blocker),
            _freeze_value(snapshot.transport),
            _freeze_value(snapshot.data_refs),
            _freeze_value(snapshot.camera_state),
            _freeze_value(snapshot.playback_state),
            _freeze_value(snapshot.options),
        )

    def _set_last_error(self, value: str) -> None:
        normalized = _string(value)
        if normalized == self._last_error:
            return
        self._last_error = normalized
        self.last_error_changed.emit()


__all__ = ["ViewerHostService"]
