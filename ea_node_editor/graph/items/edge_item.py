from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QPainterPath, QPen
from PyQt6.QtWidgets import QGraphicsPathItem

if TYPE_CHECKING:
    from ea_node_editor.graph.items.node_item import NodeGraphicsItem


class EdgeGraphicsItem(QGraphicsPathItem):
    def __init__(
        self,
        edge_id: str,
        source_node: NodeGraphicsItem,
        source_port: str,
        target_node: NodeGraphicsItem,
        target_port: str,
        data_type_warning: bool = False,
    ) -> None:
        super().__init__()
        self.edge_id = edge_id
        self.source_node = source_node
        self.source_port = source_port
        self.target_node = target_node
        self.target_port = target_port
        self.data_type_warning = data_type_warning
        self._data_pen = QPen(QColor("#6f89af"), 2.0)
        self._exec_pen = QPen(QColor("#63b378"), 2.0)
        self._completed_pen = QPen(QColor("#ccb464"), 2.0)
        self._failed_pen = QPen(QColor("#d94f4f"), 2.0)
        self._warning_pen = QPen(QColor("#e8a838"), 2.0)
        self._selected_pen = QPen(QColor("#7ac3ff"), 2.2)
        self.setPen(self._pen_for_kind())
        self.setZValue(-1.0)
        self.update_path()

    def _pen_for_kind(self) -> QPen:
        for port in self.source_node.spec.ports:
            if port.key == self.source_port:
                if port.kind == "exec":
                    return QPen(self._exec_pen)
                if port.kind == "completed":
                    return QPen(self._completed_pen)
                if port.kind == "failed":
                    return QPen(self._failed_pen)
                break
        if self.data_type_warning:
            return QPen(self._warning_pen)
        return QPen(self._data_pen)

    def update_path(self) -> None:
        self.setPen(self._selected_pen if self.isSelected() else self._pen_for_kind())
        source = self.source_node.port_scene_pos(self.source_port)
        target = self.target_node.port_scene_pos(self.target_port)
        path = QPainterPath(source)
        delta_x = max(50.0, abs(target.x() - source.x()) * 0.5)
        control_1 = QPointF(source.x() + delta_x, source.y())
        control_2 = QPointF(target.x() - delta_x, target.y())
        path.cubicTo(control_1, control_2, target)
        self.setPath(path)
