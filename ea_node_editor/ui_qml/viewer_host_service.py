from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QObject, QTimer, pyqtProperty, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QWidget

from ea_node_editor.execution.viewer_session_service import (
    VIEWER_SESSION_MODEL_KEY,
    coerce_viewer_session_model,
)
from ea_node_editor.ui_qml.embedded_viewer_overlay_manager import (
    EmbeddedViewerOverlayManager,
    EmbeddedViewerOverlaySpec,
)
from ea_node_editor.ui_qml.viewer_widget_binder import (
    ViewerWidgetBindRequest,
    ViewerWidgetBinder,
    ViewerWidgetBinderRegistry,
    ViewerWidgetNoBind,
    ViewerWidgetReleaseRequest,
)

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow
    from ea_node_editor.ui_qml.viewer_session_bridge import ViewerSessionBridge

_OverlayKey = tuple[str, str]


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


def _projected_session_model(projected_state: Mapping[str, Any]) -> dict[str, Any]:
    session_model = coerce_viewer_session_model(projected_state)
    if session_model:
        return session_model
    fallback = _mapping(projected_state.get(VIEWER_SESSION_MODEL_KEY))
    return fallback if fallback else _mapping(projected_state)


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
    session_model: dict[str, Any] = field(default_factory=dict)

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
            session_model=copy.deepcopy(self.session_model),
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
            session_model=copy.deepcopy(self.session_model),
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
        self._content_fullscreen_bridge: QObject | None = None
        self._binder_registry = ViewerWidgetBinderRegistry()
        self._bound_overlays: dict[_OverlayKey, _BoundOverlay] = {}
        self._last_error = ""
        self._sync_queued = False
        self._sync_suspended = False
        self._shutdown = False

        self._register_builtin_binders()
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

    def capture_overlay_camera_state(self, node_id: str, *, workspace_id: str = "") -> dict[str, Any]:
        if self._shutdown:
            return {}
        normalized_workspace_id = _string(workspace_id)
        if not normalized_workspace_id and self._viewer_session_bridge is not None:
            normalized_workspace_id = _string(
                getattr(self._viewer_session_bridge, "active_workspace_id", "")
            )
        normalized_node_id = _string(node_id)
        if not normalized_workspace_id or not normalized_node_id:
            return {}

        bound = self._bound_overlays.get((normalized_workspace_id, normalized_node_id))
        overlay_manager = self._overlay_manager
        if bound is None or overlay_manager is None:
            return {}
        widget = overlay_manager.overlay_widget(
            normalized_node_id,
            workspace_id=normalized_workspace_id,
        )
        if widget is None:
            return {}
        capture = getattr(bound.binder, "capture_camera_state", None)
        if not callable(capture):
            return {}
        try:
            return _mapping(capture(widget))
        except Exception as exc:  # noqa: BLE001
            self._set_last_error(str(exc))
            return {}

    def capture_overlay_preview_image(self, node_id: str, *, workspace_id: str = "") -> QImage:
        if self._shutdown:
            return QImage()
        normalized_workspace_id = _string(workspace_id)
        if not normalized_workspace_id and self._viewer_session_bridge is not None:
            normalized_workspace_id = _string(
                getattr(self._viewer_session_bridge, "active_workspace_id", "")
            )
        normalized_node_id = _string(node_id)
        if not normalized_workspace_id or not normalized_node_id:
            return QImage()

        bound = self._bound_overlays.get((normalized_workspace_id, normalized_node_id))
        overlay_manager = self._overlay_manager
        if bound is None or overlay_manager is None:
            return QImage()
        widget = overlay_manager.overlay_widget(
            normalized_node_id,
            workspace_id=normalized_workspace_id,
        )
        if not isinstance(widget, QWidget):
            return QImage()

        capture = getattr(bound.binder, "capture_preview_image", None)
        if callable(capture):
            try:
                captured = capture(widget)
            except Exception as exc:  # noqa: BLE001
                self._set_last_error(str(exc))
            else:
                if isinstance(captured, QImage) and not captured.isNull():
                    return captured.copy()

        grab_framebuffer = getattr(widget, "grabFramebuffer", None)
        if callable(grab_framebuffer):
            try:
                captured = grab_framebuffer()
            except Exception as exc:  # noqa: BLE001
                self._set_last_error(str(exc))
                return QImage()
            if isinstance(captured, QImage) and not captured.isNull():
                return captured.copy()

        try:
            pixmap = widget.grab()
        except Exception as exc:  # noqa: BLE001
            self._set_last_error(str(exc))
            return QImage()
        if pixmap.isNull():
            return QImage()
        image = pixmap.toImage()
        if image.isNull():
            return QImage()
        return image.copy()

    def register_binder(self, backend_id: str, binder: ViewerWidgetBinder) -> None:
        if self._shutdown:
            return
        self._binder_registry.register(backend_id, binder)
        self._schedule_sync()

    def _register_builtin_binders(self) -> None:
        try:
            from ea_node_editor.ui_qml.dpf_viewer_widget_binder import DpfViewerWidgetBinder
        except Exception:
            return
        if self._binder_registry.lookup(DpfViewerWidgetBinder.backend_id) is not None:
            return
        self._binder_registry.register(
            DpfViewerWidgetBinder.backend_id,
            DpfViewerWidgetBinder(),
        )

    def set_overlay_manager(self, overlay_manager: EmbeddedViewerOverlayManager | None) -> None:
        if self._shutdown:
            return
        if self._overlay_manager is overlay_manager:
            return
        self._release_all_bindings(reason="overlay_manager_replaced")
        previous_overlay_manager = self._overlay_manager
        self._overlay_manager = overlay_manager
        if previous_overlay_manager is not None:
            previous_overlay_manager.set_content_fullscreen_target(None)
            previous_overlay_manager.set_active_overlays(())
        self._connect_content_fullscreen_bridge()
        self._schedule_sync()

    def reset(self, *, reason: str = "") -> None:
        if self._shutdown:
            return
        self._release_all_bindings(reason=reason or "reset")
        overlay_manager = self._overlay_manager
        if overlay_manager is not None:
            overlay_manager.set_content_fullscreen_target(None)
            overlay_manager.set_active_overlays(())
        self._set_last_error("")
        self.state_changed.emit()

    def suspend_sync(self, *, reason: str = "") -> None:
        if self._shutdown:
            return
        self._sync_suspended = True
        if reason:
            self._set_last_error("")

    def resume_sync(self) -> None:
        if self._shutdown:
            return
        if not self._sync_suspended:
            return
        self._sync_suspended = False
        self._schedule_sync()

    def shutdown(self, *, reason: str = "") -> None:
        if self._shutdown:
            return
        self._shutdown = True
        self._sync_queued = False
        self._sync_suspended = False
        self._release_all_bindings(reason=reason or "shutdown")
        overlay_manager = self._overlay_manager
        if overlay_manager is not None:
            overlay_manager.set_content_fullscreen_target(None)
            overlay_manager.set_active_overlays(())
        self._overlay_manager = None
        self._content_fullscreen_bridge = None
        self._viewer_session_bridge = None
        self._shell_window = None
        self._set_last_error("")
        self.state_changed.emit()

    def _connect_signals(self) -> None:
        self._connect_signal(self._viewer_session_bridge, "sessions_changed", self._schedule_sync)
        self._connect_signal(self._viewer_session_bridge, "active_workspace_changed", self._schedule_sync)
        self._connect_content_fullscreen_bridge()

    def _connect_content_fullscreen_bridge(self) -> QObject | None:
        shell_window = self._shell_window
        bridge = getattr(shell_window, "content_fullscreen_bridge", None) if shell_window is not None else None
        if bridge is None:
            return self._content_fullscreen_bridge
        if bridge is self._content_fullscreen_bridge:
            return bridge
        self._content_fullscreen_bridge = bridge
        self._connect_signal(bridge, "content_fullscreen_changed", self._schedule_sync)
        return bridge if isinstance(bridge, QObject) else None

    @staticmethod
    def _connect_signal(source: object | None, name: str, slot) -> None:  # noqa: ANN001
        signal = getattr(source, name, None) if source is not None else None
        if signal is not None and hasattr(signal, "connect"):
            signal.connect(slot)

    def _schedule_sync(self) -> None:
        if self._shutdown:
            return
        if self._sync_queued:
            return
        self._sync_queued = True
        QTimer.singleShot(0, self._run_queued_sync)

    @pyqtSlot()
    def _run_queued_sync(self) -> None:
        if self._shutdown:
            self._sync_queued = False
            return
        if self._sync_suspended:
            self._sync_queued = False
            return
        self._sync_queued = False
        self.sync()

    @pyqtSlot()
    def sync(self) -> None:
        if self._shutdown or self._sync_suspended:
            return
        overlay_manager = self._overlay_manager
        bridge = self._viewer_session_bridge
        if overlay_manager is None or bridge is None:
            self._release_all_bindings(reason="overlay_manager_unavailable")
            if overlay_manager is not None:
                overlay_manager.set_content_fullscreen_target(None)
                overlay_manager.set_active_overlays(())
            self.state_changed.emit()
            return

        overlay_manager.set_content_fullscreen_target(self._content_fullscreen_overlay_spec())
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
            except ViewerWidgetNoBind:
                self._bound_overlays.pop(key, None)
                self._release_widget(
                    snapshot=snapshot,
                    binder=binder,
                    container=container,
                    widget=current_widget,
                    reason="no_bind",
                )
                continue
            except Exception as exc:  # noqa: BLE001
                self._bound_overlays.pop(key, None)
                self._release_widget(
                    snapshot=snapshot,
                    binder=binder,
                    container=container,
                    widget=current_widget,
                    reason="bind_error",
                )
                errors.append(str(exc))
                continue
            if widget is None:
                self._bound_overlays.pop(key, None)
                self._release_widget(
                    snapshot=snapshot,
                    binder=binder,
                    container=container,
                    widget=current_widget,
                    reason="no_bind",
                )
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

    def _content_fullscreen_overlay_spec(self) -> EmbeddedViewerOverlaySpec | None:
        bridge = self._connect_content_fullscreen_bridge()
        if bridge is None:
            return None
        if not bool(getattr(bridge, "open", False)):
            return None
        if _string(getattr(bridge, "content_kind", "")) != "viewer":
            return None
        workspace_id = _string(getattr(bridge, "workspace_id", ""))
        node_id = _string(getattr(bridge, "node_id", ""))
        if not workspace_id or not node_id:
            return None
        viewer_payload = _mapping(getattr(bridge, "viewer_payload", {}))
        return EmbeddedViewerOverlaySpec(
            workspace_id=workspace_id,
            node_id=node_id,
            session_id=_string(viewer_payload.get("session_id", "")),
        )

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
        self._release_widget(
            snapshot=bound.snapshot,
            binder=bound.binder,
            container=container,
            widget=widget,
            reason=reason,
        )

    def _release_widget(
        self,
        *,
        snapshot: _ViewerHostSessionSnapshot,
        binder: ViewerWidgetBinder,
        container,
        widget,
        reason: str,
    ) -> None:  # noqa: ANN001
        overlay_manager = self._overlay_manager
        if widget is None:
            return
        if overlay_manager is not None and overlay_manager.overlay_widget(snapshot.node_id, workspace_id=snapshot.workspace_id) is widget:
            if container is not None:
                try:
                    container.hide()
                except Exception:  # noqa: BLE001
                    pass
            try:
                widget.hide()
            except Exception:  # noqa: BLE001
                pass
        try:
            binder.release_widget(
                snapshot.release_request(
                    container=container,
                    widget=widget,
                    reason=reason,
                )
            )
        except Exception as exc:  # noqa: BLE001
            self._set_last_error(str(exc))
        finally:
            if overlay_manager is None:
                return
            if overlay_manager.overlay_widget(snapshot.node_id, workspace_id=snapshot.workspace_id) is widget:
                overlay_manager.detach_overlay_widget(
                    snapshot.node_id,
                    workspace_id=snapshot.workspace_id,
                )

    def _snapshot_from_projected_state(
        self,
        projected_state: Mapping[str, Any],
    ) -> _ViewerHostSessionSnapshot | None:
        session_model = _projected_session_model(projected_state)
        if not session_model:
            return None
        workspace_id = _string(session_model.get("workspace_id"))
        node_id = _string(session_model.get("node_id"))
        if not workspace_id or not node_id:
            return None
        summary = _mapping(session_model.get("summary"))
        options = _mapping(session_model.get("options"))
        data_refs = _mapping(session_model.get("data_refs"))
        transport = _mapping(session_model.get("transport"))
        live_open_blocker = (
            _mapping(session_model.get("live_open_blocker"))
            or _mapping(options.get("live_open_blocker"))
            or _mapping(summary.get("live_open_blocker"))
        )
        camera_state = _mapping(session_model.get("camera_state"))
        if not camera_state:
            camera_state = _mapping(summary.get("camera_state") or summary.get("camera"))
        playback_state = _mapping(session_model.get("playback"))
        if not playback_state:
            playback_state = _playback_state_from_projection(session_model, options, {})
        backend_id = _string(
            session_model.get("backend_id")
            or options.get("backend_id")
            or summary.get("backend_id")
            or transport.get("backend_id")
        )
        if not backend_id:
            return None
        session_id = _string(session_model.get("session_id"))
        transport_revision = _coerce_int(
            session_model.get(
                "transport_revision",
                options.get("transport_revision", summary.get("transport_revision", 0)),
            ),
            default=0,
        )
        live_open_status = _string(
            session_model.get("live_open_status")
            or options.get("live_open_status")
            or summary.get("live_open_status")
        )
        return _ViewerHostSessionSnapshot(
            workspace_id=workspace_id,
            node_id=node_id,
            session_id=session_id,
            backend_id=backend_id,
            phase=_string(session_model.get("phase")),
            cache_state=_string(session_model.get("cache_state") or summary.get("cache_state") or options.get("cache_state")),
            live_mode=_string(session_model.get("live_mode") or options.get("live_mode")),
            transport_revision=transport_revision,
            live_open_status=live_open_status,
            live_open_blocker=live_open_blocker,
            data_refs=data_refs,
            transport=transport,
            camera_state=camera_state,
            playback_state=playback_state,
            summary=summary,
            options=options,
            session_model=_mapping(session_model),
        )

    @staticmethod
    def _should_host_overlay(projected_state: Mapping[str, Any]) -> bool:
        session_model = _projected_session_model(projected_state)
        if _string(session_model.get("phase")) != "open":
            return False
        options = _mapping(session_model.get("options"))
        live_mode = _string(session_model.get("live_mode") or options.get("live_mode"))
        if live_mode != "full":
            return False
        live_open_status = _string(
            session_model.get("live_open_status")
            or options.get("live_open_status")
            or _mapping(session_model.get("summary")).get("live_open_status")
        )
        cache_state = _string(
            session_model.get("cache_state")
            or options.get("cache_state")
            or _mapping(session_model.get("summary")).get("cache_state")
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
