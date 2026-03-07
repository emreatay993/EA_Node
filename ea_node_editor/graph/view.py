from __future__ import annotations

from PyQt6.QtCore import QPoint, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QPainter, QWheelEvent
from PyQt6.QtWidgets import QGraphicsView


class NodeGraphView(QGraphicsView):
    zoom_changed = pyqtSignal(float)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._zoom = 1.0
        self._panning = False
        self._last_pan_point = QPoint()
        self.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing, False)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontSavePainterState, True)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, True)
        self.setCacheMode(QGraphicsView.CacheModeFlag.CacheBackground)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self._antialias_restore_timer = QTimer(self)
        self._antialias_restore_timer.setSingleShot(True)
        self._antialias_restore_timer.setInterval(120)
        self._antialias_restore_timer.timeout.connect(self._restore_render_hints)

    @property
    def zoom(self) -> float:
        return self._zoom

    def set_zoom(self, zoom: float) -> None:
        zoom = max(0.1, min(zoom, 3.0))
        if abs(self._zoom - zoom) < 1e-6:
            return
        factor = zoom / self._zoom
        self.scale(factor, factor)
        self._zoom = zoom
        self.zoom_changed.emit(self._zoom)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers():
            super().wheelEvent(event)
            return
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing, False)
        step = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.set_zoom(self._zoom * step)
        self._antialias_restore_timer.start()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._last_pan_point = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._panning:
            self.setRenderHint(QPainter.RenderHint.TextAntialiasing, False)
            delta = event.pos() - self._last_pan_point
            self._last_pan_point = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self._antialias_restore_timer.start()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _restore_render_hints(self) -> None:
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing, False)
