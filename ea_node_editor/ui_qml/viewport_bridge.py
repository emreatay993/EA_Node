from __future__ import annotations

from PyQt6.QtCore import QObject, QPointF, QRect, QRectF, pyqtProperty, pyqtSignal, pyqtSlot

MIN_ZOOM = 0.1
MAX_ZOOM = 3.0
FRAME_PADDING_PX = 80.0


class ViewportBridge(QObject):
    zoom_changed = pyqtSignal(float)
    center_changed = pyqtSignal(float, float)
    view_state_changed = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._zoom = 1.0
        self._center_x = 0.0
        self._center_y = 0.0
        self._viewport_rect = QRect(0, 0, 1600, 900)

    @property
    def zoom(self) -> float:
        return self._zoom

    @pyqtProperty(float, notify=zoom_changed)
    def zoom_value(self) -> float:
        return self._zoom

    @pyqtProperty(float, notify=center_changed)
    def center_x(self) -> float:
        return self._center_x

    @pyqtProperty(float, notify=center_changed)
    def center_y(self) -> float:
        return self._center_y

    @pyqtProperty("QVariantMap", notify=view_state_changed)
    def visible_scene_rect_payload(self) -> dict[str, float]:
        return self._rect_payload(self.visible_scene_rect())

    def _clamp_zoom(self, zoom: float) -> float:
        return max(MIN_ZOOM, min(float(zoom), MAX_ZOOM))

    def set_zoom(self, zoom: float) -> None:
        clamped = self._clamp_zoom(float(zoom))
        if abs(self._zoom - clamped) < 1e-6:
            return
        self._zoom = clamped
        self.zoom_changed.emit(self._zoom)
        self.view_state_changed.emit()

    @pyqtSlot(float)
    def adjust_zoom(self, factor: float) -> None:
        self.set_zoom(self._zoom * float(factor))

    def centerOn(self, x: float | QPointF, y: float | None = None) -> None:  # noqa: N802
        if isinstance(x, QPointF):
            cx = float(x.x())
            cy = float(x.y())
        elif y is None:
            cx = float(x)
            cy = self._center_y
        else:
            cx = float(x)
            cy = float(y)

        if abs(self._center_x - cx) < 1e-6 and abs(self._center_y - cy) < 1e-6:
            return
        self._center_x = cx
        self._center_y = cy
        self.center_changed.emit(self._center_x, self._center_y)
        self.view_state_changed.emit()

    @pyqtSlot(float, float)
    def pan_by(self, delta_x: float, delta_y: float) -> None:
        self.centerOn(self._center_x + float(delta_x), self._center_y + float(delta_y))

    def mapToScene(self, _point) -> QPointF:  # noqa: ANN001, N802
        return QPointF(self._center_x, self._center_y)

    def viewport(self) -> "ViewportBridge":
        return self

    def rect(self) -> QRect:
        return QRect(self._viewport_rect)

    def visible_scene_rect(self) -> QRectF:
        zoom = max(MIN_ZOOM, self._zoom)
        scene_width = float(self._viewport_rect.width()) / zoom
        scene_height = float(self._viewport_rect.height()) / zoom
        return QRectF(
            self._center_x - (scene_width * 0.5),
            self._center_y - (scene_height * 0.5),
            scene_width,
            scene_height,
        )

    def _rect_payload(self, rect: QRectF) -> dict[str, float]:
        normalized = QRectF(rect).normalized()
        return {
            "x": float(normalized.x()),
            "y": float(normalized.y()),
            "width": float(max(0.0, normalized.width())),
            "height": float(max(0.0, normalized.height())),
        }

    @pyqtSlot(result="QVariantMap")
    def visible_scene_rect_map(self) -> dict[str, float]:
        return self._rect_payload(self.visible_scene_rect())

    @pyqtSlot(float, float)
    def center_on_scene_point(self, x: float, y: float) -> None:
        self.centerOn(float(x), float(y))

    def fit_zoom_for_scene_rect(self, scene_rect: QRectF, padding_px: float = FRAME_PADDING_PX) -> float:
        normalized = QRectF(scene_rect).normalized()
        width = max(1e-6, float(normalized.width()))
        height = max(1e-6, float(normalized.height()))
        padding = max(0.0, float(padding_px))
        viewport_width = max(1.0, float(self._viewport_rect.width()) - (padding * 2.0))
        viewport_height = max(1.0, float(self._viewport_rect.height()) - (padding * 2.0))
        fitted = min(viewport_width / width, viewport_height / height)
        return self._clamp_zoom(fitted)

    def center_on_scene_rect(self, scene_rect: QRectF) -> bool:
        normalized = QRectF(scene_rect).normalized()
        if not normalized.isValid():
            return False
        self.centerOn(normalized.center())
        return True

    def frame_scene_rect(self, scene_rect: QRectF, padding_px: float = FRAME_PADDING_PX) -> bool:
        normalized = QRectF(scene_rect).normalized()
        if not normalized.isValid():
            return False
        if normalized.width() <= 0.0 or normalized.height() <= 0.0:
            return False
        self.set_zoom(self.fit_zoom_for_scene_rect(normalized, padding_px=padding_px))
        self.centerOn(normalized.center())
        return True

    @pyqtSlot(float, float)
    def set_viewport_size(self, width: float, height: float) -> None:
        w = max(1, int(round(width)))
        h = max(1, int(round(height)))
        if self._viewport_rect.width() == w and self._viewport_rect.height() == h:
            return
        self._viewport_rect = QRect(0, 0, w, h)
        self.view_state_changed.emit()


__all__ = ["ViewportBridge"]
