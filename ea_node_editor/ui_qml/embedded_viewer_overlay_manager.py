from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import QEvent, QObject, QPointF, QRect, QRectF, QTimer, pyqtSlot
from PyQt6.QtQuick import QQuickItem
from PyQt6.QtQuickWidgets import QQuickWidget
from PyQt6.QtWidgets import QWidget

if TYPE_CHECKING:
    from ea_node_editor.ui.shell.window import ShellWindow
    from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
    from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge

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


@dataclass(slots=True, frozen=True)
class EmbeddedViewerOverlaySpec:
    workspace_id: str
    node_id: str
    session_id: str = ""


@dataclass(slots=True)
class _OverlayRecord:
    workspace_id: str
    node_id: str
    session_id: str
    container: QWidget
    overlay_widget: QWidget | None = None


class EmbeddedViewerOverlayManager(QObject):
    def __init__(
        self,
        parent: QObject | None = None,
        *,
        quick_widget: QQuickWidget,
        shell_window: "ShellWindow | None" = None,
        scene_bridge: "GraphSceneBridge | None" = None,
        view_bridge: "ViewportBridge | None" = None,
    ) -> None:
        super().__init__(parent or quick_widget)
        self._quick_widget = quick_widget
        self._shell_window = shell_window
        self._scene_bridge = scene_bridge
        self._view_bridge = view_bridge
        self._desired_overlays: dict[_OverlayKey, EmbeddedViewerOverlaySpec] = {}
        self._overlay_records: dict[_OverlayKey, _OverlayRecord] = {}
        self._last_error = ""
        self._sync_queued = False

        self._quick_widget.installEventFilter(self)
        self._connect_signals()
        self._schedule_sync()

    @property
    def quick_widget(self) -> QQuickWidget:
        return self._quick_widget

    @property
    def last_error(self) -> str:
        return self._last_error

    def set_active_overlays(self, overlays: Iterable[EmbeddedViewerOverlaySpec]) -> None:
        desired_overlays: dict[_OverlayKey, EmbeddedViewerOverlaySpec] = {}
        for overlay in overlays:
            workspace_id = _string(getattr(overlay, "workspace_id", ""))
            node_id = _string(getattr(overlay, "node_id", ""))
            if not workspace_id or not node_id:
                continue
            desired_overlays[(workspace_id, node_id)] = EmbeddedViewerOverlaySpec(
                workspace_id=workspace_id,
                node_id=node_id,
                session_id=_string(getattr(overlay, "session_id", "")),
            )

        removed_keys = [key for key in self._overlay_records if key not in desired_overlays]
        self._desired_overlays = desired_overlays
        for key, overlay in desired_overlays.items():
            self._ensure_record(key=key, session_id=overlay.session_id)
        for key in removed_keys:
            self._teardown_record(key)
        self._schedule_sync()

    def overlay_widget(self, node_id: str, *, workspace_id: str = "") -> QWidget | None:
        resolved_workspace_id = _string(workspace_id) or self._active_workspace_id()
        record = self._overlay_records.get((resolved_workspace_id, _string(node_id)))
        if record is None:
            return None
        return record.overlay_widget

    def overlay_container(self, node_id: str, *, workspace_id: str = "") -> QWidget | None:
        resolved_workspace_id = _string(workspace_id) or self._active_workspace_id()
        record = self._overlay_records.get((resolved_workspace_id, _string(node_id)))
        if record is None:
            return None
        return record.container

    def attach_overlay_widget(self, node_id: str, widget: QWidget, *, workspace_id: str = "") -> bool:
        resolved_workspace_id = _string(workspace_id) or self._active_workspace_id()
        normalized_node_id = _string(node_id)
        if not resolved_workspace_id or not normalized_node_id:
            self._last_error = "workspace_id and node_id are required to attach an overlay widget."
            return False
        record = self._overlay_records.get((resolved_workspace_id, normalized_node_id))
        if record is None:
            record = self._ensure_record(
                key=(resolved_workspace_id, normalized_node_id),
                session_id="",
            )
        if record is None:
            self._last_error = "Unable to create overlay container."
            return False
        if record.overlay_widget is widget:
            self._last_error = ""
            self._schedule_sync()
            return True
        if record.overlay_widget is not None:
            self._teardown_widget(record.overlay_widget)
        if widget.parent() is not record.container:
            widget.setParent(record.container)
        if not widget.objectName():
            widget.setObjectName(f"embeddedViewerWidget::{resolved_workspace_id}::{normalized_node_id}")
        record.overlay_widget = widget
        widget.setGeometry(record.container.rect())
        if record.container.width() > 0 and record.container.height() > 0 and self._quick_widget.isVisible():
            record.container.show()
            widget.show()
            record.container.raise_()
            widget.raise_()
        self._last_error = ""
        self._schedule_sync()
        return True

    def detach_overlay_widget(self, node_id: str, *, workspace_id: str = "") -> None:
        resolved_workspace_id = _string(workspace_id) or self._active_workspace_id()
        record = self._overlay_records.get((resolved_workspace_id, _string(node_id)))
        if record is None or record.overlay_widget is None:
            return
        widget = record.overlay_widget
        record.overlay_widget = None
        self._teardown_widget(widget)
        self._schedule_sync()

    def eventFilter(self, watched: QObject | None, event: QEvent | None) -> bool:
        if watched is self._quick_widget and event is not None:
            event_type = event.type()
            if event_type in {
                QEvent.Type.Show,
                QEvent.Type.Resize,
                QEvent.Type.Move,
                QEvent.Type.LayoutRequest,
                QEvent.Type.UpdateRequest,
                QEvent.Type.Paint,
                QEvent.Type.WindowStateChange,
            }:
                self._schedule_sync()
            elif event_type == QEvent.Type.Hide:
                self._hide_all_records()
            elif event_type == QEvent.Type.Close:
                self._clear_records()
        return super().eventFilter(watched, event)

    def _connect_signals(self) -> None:
        self._connect_signal(self._quick_widget, "statusChanged", self._on_quick_widget_status_changed)
        self._connect_signal(self._scene_bridge, "nodes_changed", self._schedule_sync)
        self._connect_signal(self._scene_bridge, "workspace_changed", self._schedule_sync)
        self._connect_signal(self._view_bridge, "view_state_changed", self._schedule_sync)

    @staticmethod
    def _connect_signal(source: object | None, name: str, slot) -> None:  # noqa: ANN001
        signal = getattr(source, name, None) if source is not None else None
        if signal is not None and hasattr(signal, "connect"):
            signal.connect(slot)

    def _on_quick_widget_status_changed(self, _status) -> None:  # noqa: ANN001
        self._schedule_sync()

    def _schedule_sync(self) -> None:
        if self._sync_queued:
            return
        self._sync_queued = True
        QTimer.singleShot(0, self._run_queued_sync)

    @pyqtSlot()
    def _run_queued_sync(self) -> None:
        self._sync_queued = False
        self.sync()

    def _active_workspace_id(self) -> str:
        if self._scene_bridge is not None:
            return _string(getattr(self._scene_bridge, "workspace_id", ""))
        return ""

    @pyqtSlot()
    def sync(self) -> None:
        root_item = self._root_item()
        graph_canvas_item = self._graph_canvas_item(root_item)
        if root_item is None or graph_canvas_item is None:
            self._hide_all_records()
            return

        if not self._desired_overlays:
            self._clear_records()
            return

        node_payloads = self._node_payloads_by_id()
        managed_keys = set(self._desired_overlays)
        for key, overlay in self._desired_overlays.items():
            node_payload = node_payloads.get(key[1])
            if node_payload is None or _bool(node_payload.get("collapsed")):
                self._teardown_record(key)
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
                session_id=overlay.session_id,
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
        record = _OverlayRecord(
            workspace_id=key[0],
            node_id=key[1],
            session_id=session_id,
            container=container,
        )
        self._overlay_records[key] = record
        self._last_error = ""
        return record

    @staticmethod
    def _show_record(record: _OverlayRecord, geometry: QRect) -> None:
        record.container.setGeometry(geometry)
        widget = record.overlay_widget
        if widget is None:
            record.container.hide()
            return
        widget.setGeometry(record.container.rect())
        record.container.show()
        widget.show()
        record.container.raise_()
        widget.raise_()

    def _hide_record(self, key: _OverlayKey) -> None:
        record = self._overlay_records.get(key)
        if record is None:
            return
        if record.overlay_widget is not None:
            record.overlay_widget.hide()
        record.container.hide()

    def _hide_all_records(self) -> None:
        for key in list(self._overlay_records):
            self._hide_record(key)

    def _teardown_record(self, key: _OverlayKey) -> None:
        record = self._overlay_records.pop(key, None)
        if record is None:
            return
        if record.overlay_widget is not None:
            self._teardown_widget(record.overlay_widget)
        record.container.close()
        record.container.deleteLater()

    @staticmethod
    def _teardown_widget(widget: QWidget) -> None:
        widget.close()
        widget.deleteLater()

    def _clear_records(self) -> None:
        for key in list(self._overlay_records):
            self._teardown_record(key)


__all__ = ["EmbeddedViewerOverlayManager", "EmbeddedViewerOverlaySpec"]
