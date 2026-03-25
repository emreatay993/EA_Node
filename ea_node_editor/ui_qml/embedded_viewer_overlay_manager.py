from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QEvent, QObject, QPointF, QRect, QRectF, QTimer, pyqtSlot
from PyQt6.QtQuick import QQuickItem
from PyQt6.QtQuickWidgets import QQuickWidget
from PyQt6.QtWidgets import QWidget

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
    from ea_node_editor.ui_qml.viewer_session_bridge import ViewerSessionBridge
    from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge

InteractorFactory = Callable[[QWidget], QWidget]
_OverlayKey = tuple[str, str]


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _number(value: Any, fallback: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    if not math.isfinite(number):
        return fallback
    return number


def _string(value: Any) -> str:
    return str(value).strip()


def _bool(value: Any) -> bool:
    return bool(value)


def _rect_payload(value: Any) -> dict[str, float]:
    payload = _mapping(value)
    return {
        "x": max(0.0, _number(payload.get("x"), 0.0)),
        "y": max(0.0, _number(payload.get("y"), 0.0)),
        "width": max(0.0, _number(payload.get("width"), 0.0)),
        "height": max(0.0, _number(payload.get("height"), 0.0)),
    }


def _aligned_rect(rect: QRectF) -> QRect:
    normalized = QRectF(rect).normalized()
    left = math.floor(normalized.left())
    top = math.floor(normalized.top())
    right = math.ceil(normalized.right())
    bottom = math.ceil(normalized.bottom())
    return QRect(
        int(left),
        int(top),
        max(0, int(right - left)),
        max(0, int(bottom - top)),
    )


def _default_qt_interactor_factory(parent: QWidget) -> QWidget:
    from pyvistaqt import QtInteractor

    return QtInteractor(parent)


@dataclass(slots=True)
class _OverlayRecord:
    workspace_id: str
    node_id: str
    session_id: str
    container: QWidget
    interactor_widget: QWidget


class EmbeddedViewerOverlayManager(QObject):
    def __init__(
        self,
        parent: QObject | None = None,
        *,
        quick_widget: QQuickWidget,
        shell_window: "ShellWindow | None" = None,
        viewer_session_bridge: "ViewerSessionBridge | None" = None,
        scene_bridge: "GraphSceneBridge | None" = None,
        view_bridge: "ViewportBridge | None" = None,
        interactor_factory: InteractorFactory | None = None,
    ) -> None:
        super().__init__(parent or quick_widget)
        self._quick_widget = quick_widget
        self._shell_window = shell_window
        self._viewer_session_bridge = viewer_session_bridge
        self._scene_bridge = scene_bridge
        self._view_bridge = view_bridge
        self._interactor_factory: InteractorFactory = interactor_factory or _default_qt_interactor_factory
        self._overlay_records: dict[_OverlayKey, _OverlayRecord] = {}
        self._focus_only_active_key: _OverlayKey | None = None
        self._last_error = ""

        self._quick_widget.installEventFilter(self)
        self._connect_signals()
        QTimer.singleShot(0, self.sync)

    @property
    def quick_widget(self) -> QQuickWidget:
        return self._quick_widget

    @property
    def last_error(self) -> str:
        return self._last_error

    def set_interactor_factory(self, factory: InteractorFactory) -> None:
        self._interactor_factory = factory
        self._clear_records()
        QTimer.singleShot(0, self.sync)

    def overlay_widget(self, node_id: str, *, workspace_id: str = "") -> QWidget | None:
        resolved_workspace_id = _string(workspace_id) or self._active_workspace_id()
        record = self._overlay_records.get((resolved_workspace_id, _string(node_id)))
        if record is None:
            return None
        return record.interactor_widget

    def overlay_container(self, node_id: str, *, workspace_id: str = "") -> QWidget | None:
        resolved_workspace_id = _string(workspace_id) or self._active_workspace_id()
        record = self._overlay_records.get((resolved_workspace_id, _string(node_id)))
        if record is None:
            return None
        return record.container

    def eventFilter(self, watched: QObject | None, event: QEvent | None) -> bool:
        if watched is self._quick_widget and event is not None:
            event_type = event.type()
            if event_type in {
                QEvent.Type.Show,
                QEvent.Type.Resize,
                QEvent.Type.Move,
                QEvent.Type.LayoutRequest,
                QEvent.Type.WindowStateChange,
            }:
                QTimer.singleShot(0, self.sync)
            elif event_type == QEvent.Type.Hide:
                self._hide_all_records()
            elif event_type == QEvent.Type.Close:
                self._clear_records()
        return super().eventFilter(watched, event)

    def _connect_signals(self) -> None:
        self._connect_signal(self._quick_widget, "statusChanged", self._on_quick_widget_status_changed)
        self._connect_signal(self._viewer_session_bridge, "sessions_changed", self.sync)
        self._connect_signal(self._viewer_session_bridge, "active_workspace_changed", self.sync)
        self._connect_signal(self._scene_bridge, "nodes_changed", self.sync)
        self._connect_signal(self._scene_bridge, "selection_changed", self.sync)
        self._connect_signal(self._scene_bridge, "workspace_changed", self.sync)
        self._connect_signal(self._view_bridge, "view_state_changed", self.sync)

    @staticmethod
    def _connect_signal(source: object | None, name: str, slot) -> None:  # noqa: ANN001
        signal = getattr(source, name, None) if source is not None else None
        if signal is not None and hasattr(signal, "connect"):
            signal.connect(slot)

    def _on_quick_widget_status_changed(self, _status) -> None:  # noqa: ANN001
        QTimer.singleShot(0, self.sync)

    def _active_workspace_id(self) -> str:
        if self._viewer_session_bridge is not None:
            workspace_id = _string(getattr(self._viewer_session_bridge, "active_workspace_id", ""))
            if workspace_id:
                return workspace_id
        if self._scene_bridge is not None:
            return _string(getattr(self._scene_bridge, "workspace_id", ""))
        return ""

    @pyqtSlot()
    def sync(self) -> None:
        root_item = self._root_item()
        graph_canvas_item = self._graph_canvas_item(root_item)
        if root_item is None or graph_canvas_item is None:
            self._clear_records()
            return

        active_sessions = self._active_live_sessions()
        if not active_sessions:
            self._clear_records()
            return

        node_payloads = self._node_payloads_by_id()
        active_keys = self._active_overlay_keys(active_sessions)
        managed_keys = {key for key, _state in active_sessions}

        for key, state in active_sessions:
            node_payload = node_payloads.get(key[1])
            if node_payload is None or _bool(node_payload.get("collapsed")):
                self._teardown_record(key)
                continue

            if key not in active_keys:
                self._hide_record(key)
                continue

            geometry = self._overlay_geometry(
                root_item=root_item,
                graph_canvas_item=graph_canvas_item,
                node_payload=node_payload,
            )
            if geometry is None:
                self._hide_record(key)
                continue

            record = self._ensure_record(
                key=key,
                session_id=_string(state.get("session_id", "")),
            )
            if record is None:
                continue
            self._show_record(record, geometry)

        for key in list(self._overlay_records):
            if key not in managed_keys:
                self._teardown_record(key)

    def _root_item(self) -> QQuickItem | None:
        root_object = self._quick_widget.rootObject()
        return root_object if isinstance(root_object, QQuickItem) else None

    @staticmethod
    def _graph_canvas_item(root_item: QQuickItem | None) -> QQuickItem | None:
        if root_item is None:
            return None
        graph_canvas = root_item.findChild(QObject, "graphCanvas")
        return graph_canvas if isinstance(graph_canvas, QQuickItem) else None

    def _node_payloads_by_id(self) -> dict[str, dict[str, Any]]:
        payloads: dict[str, dict[str, Any]] = {}
        nodes_model = getattr(self._scene_bridge, "nodes_model", [])
        for payload in nodes_model if isinstance(nodes_model, list) else []:
            payload_map = _mapping(payload)
            node_id = _string(payload_map.get("node_id"))
            if node_id:
                payloads[node_id] = payload_map
        return payloads

    def _active_live_sessions(self) -> list[tuple[_OverlayKey, dict[str, Any]]]:
        sessions_model = getattr(self._viewer_session_bridge, "sessions_model", [])
        if not isinstance(sessions_model, list):
            return []
        sessions: list[tuple[_OverlayKey, dict[str, Any]]] = []
        for item in sessions_model:
            state = _mapping(item)
            if _string(state.get("phase")) != "open":
                continue
            if _string(state.get("cache_state")) != "live_ready":
                continue
            options = _mapping(state.get("options"))
            live_mode = _string(options.get("live_mode", state.get("live_mode", "")))
            if live_mode != "full":
                continue
            workspace_id = _string(state.get("workspace_id"))
            node_id = _string(state.get("node_id"))
            if not workspace_id or not node_id:
                continue
            sessions.append(((workspace_id, node_id), state))
        return sessions

    def _active_overlay_keys(
        self,
        sessions: list[tuple[_OverlayKey, dict[str, Any]]],
    ) -> set[_OverlayKey]:
        selected_lookup = _mapping(getattr(self._scene_bridge, "selected_node_lookup", {}))
        keep_live_keys: list[_OverlayKey] = []
        focus_only_candidates: list[_OverlayKey] = []
        for key, state in sessions:
            live_policy = _string(state.get("live_policy"))
            keep_live = _bool(state.get("keep_live"))
            if keep_live or live_policy == "keep_live":
                keep_live_keys.append(key)
            else:
                focus_only_candidates.append(key)

        chosen_focus_key: _OverlayKey | None = None
        for key in focus_only_candidates:
            if _bool(selected_lookup.get(key[1])):
                chosen_focus_key = key
                break
        if chosen_focus_key is None and self._focus_only_active_key in focus_only_candidates:
            chosen_focus_key = self._focus_only_active_key
        if chosen_focus_key is None and focus_only_candidates:
            chosen_focus_key = focus_only_candidates[0]
        self._focus_only_active_key = chosen_focus_key

        active_keys = set(keep_live_keys)
        if chosen_focus_key is not None:
            active_keys.add(chosen_focus_key)
        return active_keys

    def _overlay_geometry(
        self,
        *,
        root_item: QQuickItem,
        graph_canvas_item: QQuickItem,
        node_payload: Mapping[str, Any],
    ) -> QRect | None:
        canvas_origin = graph_canvas_item.mapToItem(root_item, QPointF(0.0, 0.0))
        canvas_width = max(0.0, _number(graph_canvas_item.width(), 0.0))
        canvas_height = max(0.0, _number(graph_canvas_item.height(), 0.0))
        if canvas_width <= 0.0 or canvas_height <= 0.0:
            return None

        zoom_value = max(1e-6, _number(getattr(self._view_bridge, "zoom_value", 1.0), 1.0))
        center_x = _number(getattr(self._view_bridge, "center_x", 0.0), 0.0)
        center_y = _number(getattr(self._view_bridge, "center_y", 0.0), 0.0)
        live_rect = self._viewer_live_rect(node_payload)
        if live_rect["width"] <= 0.0 or live_rect["height"] <= 0.0:
            return None

        rect = QRectF(
            canvas_origin.x() + (canvas_width * 0.5) + ((_number(node_payload.get("x")) + live_rect["x"] - center_x) * zoom_value),
            canvas_origin.y() + (canvas_height * 0.5) + ((_number(node_payload.get("y")) + live_rect["y"] - center_y) * zoom_value),
            live_rect["width"] * zoom_value,
            live_rect["height"] * zoom_value,
        )
        if rect.width() <= 0.0 or rect.height() <= 0.0:
            return None

        canvas_rect = QRectF(canvas_origin.x(), canvas_origin.y(), canvas_width, canvas_height)
        if not rect.intersects(canvas_rect):
            return None
        return _aligned_rect(rect)

    @staticmethod
    def _viewer_live_rect(node_payload: Mapping[str, Any]) -> dict[str, float]:
        viewer_surface = _mapping(node_payload.get("viewer_surface"))
        live_rect = _mapping(viewer_surface.get("live_rect"))
        if live_rect:
            return _rect_payload(live_rect)
        body_rect = _mapping(viewer_surface.get("body_rect"))
        if body_rect:
            return _rect_payload(body_rect)

        surface_metrics = _mapping(node_payload.get("surface_metrics"))
        body_x = max(0.0, _number(surface_metrics.get("body_left_margin"), 0.0))
        body_y = max(0.0, _number(surface_metrics.get("body_top"), 0.0))
        node_width = max(0.0, _number(node_payload.get("width"), 0.0))
        node_height = max(0.0, _number(node_payload.get("height"), 0.0))
        body_width = max(
            0.0,
            node_width - body_x - max(0.0, _number(surface_metrics.get("body_right_margin"), 0.0)),
        )
        body_height = max(
            0.0,
            min(
                max(0.0, _number(surface_metrics.get("body_height"), 0.0)),
                max(0.0, node_height - body_y),
            ),
        )
        return {
            "x": body_x,
            "y": body_y,
            "width": body_width,
            "height": body_height,
        }

    def _ensure_record(self, *, key: _OverlayKey, session_id: str) -> _OverlayRecord | None:
        record = self._overlay_records.get(key)
        if record is not None:
            record.session_id = session_id or record.session_id
            return record

        container = QWidget(self._quick_widget)
        container.setObjectName(f"embeddedViewerOverlay::{key[0]}::{key[1]}")
        container.hide()
        try:
            interactor_widget = self._interactor_factory(container)
        except Exception as exc:  # noqa: BLE001
            self._last_error = _string(exc)
            container.deleteLater()
            return None

        if interactor_widget.parent() is not container:
            interactor_widget.setParent(container)
        interactor_widget.setObjectName(
            interactor_widget.objectName() or f"embeddedViewerInteractor::{key[0]}::{key[1]}"
        )
        interactor_widget.hide()
        record = _OverlayRecord(
            workspace_id=key[0],
            node_id=key[1],
            session_id=session_id,
            container=container,
            interactor_widget=interactor_widget,
        )
        self._overlay_records[key] = record
        self._last_error = ""
        return record

    @staticmethod
    def _show_record(record: _OverlayRecord, geometry: QRect) -> None:
        record.container.setGeometry(geometry)
        record.interactor_widget.setGeometry(record.container.rect())
        record.container.show()
        record.interactor_widget.show()
        record.container.raise_()
        record.interactor_widget.raise_()

    def _hide_record(self, key: _OverlayKey) -> None:
        record = self._overlay_records.get(key)
        if record is None:
            return
        record.interactor_widget.hide()
        record.container.hide()

    def _hide_all_records(self) -> None:
        for key in list(self._overlay_records):
            self._hide_record(key)

    def _teardown_record(self, key: _OverlayKey) -> None:
        record = self._overlay_records.pop(key, None)
        if record is None:
            return
        record.interactor_widget.close()
        record.container.close()
        record.interactor_widget.deleteLater()
        record.container.deleteLater()

    def _clear_records(self) -> None:
        for key in list(self._overlay_records):
            self._teardown_record(key)


__all__ = ["EmbeddedViewerOverlayManager"]
