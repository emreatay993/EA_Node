from __future__ import annotations

from PyQt6.QtCore import QObject, QPointF, QRect, pyqtProperty, pyqtSignal, pyqtSlot


class ViewportBridge(QObject):
    zoom_changed = pyqtSignal(float)
    center_changed = pyqtSignal(float, float)

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

    def set_zoom(self, zoom: float) -> None:
        clamped = max(0.1, min(float(zoom), 3.0))
        if abs(self._zoom - clamped) < 1e-6:
            return
        self._zoom = clamped
        self.zoom_changed.emit(self._zoom)

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

    @pyqtSlot(float, float)
    def pan_by(self, delta_x: float, delta_y: float) -> None:
        self.centerOn(self._center_x + float(delta_x), self._center_y + float(delta_y))

    def mapToScene(self, _point) -> QPointF:  # noqa: ANN001, N802
        return QPointF(self._center_x, self._center_y)

    def viewport(self) -> "ViewportBridge":
        return self

    def rect(self) -> QRect:
        return QRect(self._viewport_rect)

    @pyqtSlot(float, float)
    def set_viewport_size(self, width: float, height: float) -> None:
        w = max(1, int(round(width)))
        h = max(1, int(round(height)))
        if self._viewport_rect.width() == w and self._viewport_rect.height() == h:
            return
        self._viewport_rect = QRect(0, 0, w, h)


__all__ = ["ViewportBridge"]
