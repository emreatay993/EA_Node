from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QGraphicsItem

from ea_node_editor.graph.model import NodeInstance
from ea_node_editor.nodes.types import NodeTypeSpec, PortSpec


if TYPE_CHECKING:
    from ea_node_editor.graph.items.edge_item import EdgeGraphicsItem


class NodeGraphicsItem(QGraphicsItem):
    HEADER_HEIGHT = 24.0
    PORT_HEIGHT = 18.0
    WIDTH = 210.0
    COLLAPSED_WIDTH = 130.0
    COLLAPSED_HEIGHT = 36.0

    def __init__(
        self,
        node: NodeInstance,
        spec: NodeTypeSpec,
        on_position_changed: Callable[[str, float, float], None] | None = None,
    ) -> None:
        super().__init__()
        self.node = node
        self.spec = spec
        self._on_position_changed = on_position_changed
        self._edges: set[EdgeGraphicsItem] = set()
        self._cached_rect = QRectF()
        self._title_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
        self._text_font = QFont("Segoe UI", 8)
        self._border_selected = QColor("#67b7ff")
        self._border_normal = QColor("#4a4f59")
        self._body_brush = QBrush(QColor("#262a31"))
        self._header_brush = QBrush(QColor("#2f333b"))
        self._label_pen = QPen(QColor("#e8edf8"))
        self._port_label_pen = QPen(QColor("#cad1df"))
        self._port_hollow_brush = QBrush(Qt.BrushStyle.NoBrush)
        self._port_connected_pen = QPen(QColor("#67d487"), 1.2)
        self._port_connected_brush = QBrush(QColor("#67d487"))
        self._port_data_pen = QPen(QColor("#7aa8ff"), 1)
        self._port_exec_pen = QPen(QColor("#67d487"), 1)
        self._port_completed_pen = QPen(QColor("#e4ce7d"), 1)
        self._accent_color = self._category_accent(spec.category)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)
        self.setPos(self.node.x, self.node.y)
        self._recompute_rect()

    def add_edge(self, edge: EdgeGraphicsItem) -> None:
        self._edges.add(edge)
        self.update()

    def remove_edge(self, edge: EdgeGraphicsItem) -> None:
        if edge in self._edges:
            self._edges.remove(edge)
            self.update()

    def _port_connection_count(self, port_key: str) -> int:
        return sum(
            1
            for edge in self._edges
            if (edge.source_node is self and edge.source_port == port_key)
            or (edge.target_node is self and edge.target_port == port_key)
        )

    def _has_connected_port(self, direction: str) -> bool:
        ports = self.visible_ports()[0] if direction == "in" else self.visible_ports()[1]
        return any(self._port_connection_count(port.key) > 0 for port in ports)

    def set_collapsed(self, collapsed: bool) -> None:
        if self.node.collapsed == collapsed:
            return
        self.prepareGeometryChange()
        self.node.collapsed = collapsed
        self._recompute_rect()
        for edge in self._edges:
            edge.update_path()
        self.update()

    def refresh_ports(self) -> None:
        self.prepareGeometryChange()
        self._recompute_rect()
        for edge in self._edges:
            edge.update_path()
        self.update()

    def visible_ports(self) -> tuple[list[PortSpec], list[PortSpec]]:
        in_ports: list[PortSpec] = []
        out_ports: list[PortSpec] = []
        for port in self.spec.ports:
            exposed = self.node.exposed_ports.get(port.key, port.exposed)
            if not exposed:
                continue
            if port.direction == "in":
                in_ports.append(port)
            else:
                out_ports.append(port)
        return in_ports, out_ports

    def _port_direction(self, port_key: str) -> str | None:
        for port in self.spec.ports:
            if port.key == port_key:
                return port.direction
        return None

    def _port_row_index(self, port_key: str, direction: str, visible_ports: list[PortSpec]) -> int:
        for index, port in enumerate(visible_ports):
            if port.key == port_key:
                return index
        ordered_keys = [port.key for port in self.spec.ports if port.direction == direction]
        if port_key in ordered_keys:
            max_visible_index = max(len(visible_ports) - 1, 0)
            return min(ordered_keys.index(port_key), max_visible_index)
        return 0

    def port_scene_pos(self, port_key: str) -> QPointF:
        in_ports, out_ports = self.visible_ports()
        direction = self._port_direction(port_key)
        if direction is None:
            direction = "in" if any(port.key == port_key for port in in_ports) else "out"
        if self.node.collapsed:
            if direction == "in":
                local = QPointF(self._cached_rect.left(), self._cached_rect.center().y())
            else:
                local = QPointF(self._cached_rect.right(), self._cached_rect.center().y())
            return self.mapToScene(local)

        visible_ports = in_ports if direction == "in" else out_ports
        row_index = self._port_row_index(port_key, direction, visible_ports)
        y = self.HEADER_HEIGHT + self.PORT_HEIGHT * (row_index + 0.6)
        if direction == "in":
            x = self._cached_rect.left()
        else:
            x = self._cached_rect.right()
        return self.mapToScene(QPointF(x, y))

    def _recompute_rect(self) -> None:
        in_ports, out_ports = self.visible_ports()
        if self.node.collapsed:
            self._cached_rect = QRectF(0.0, 0.0, self.COLLAPSED_WIDTH, self.COLLAPSED_HEIGHT)
            return
        port_count = max(len(in_ports), len(out_ports), 1)
        height = self.HEADER_HEIGHT + port_count * self.PORT_HEIGHT + 8.0
        self._cached_rect = QRectF(0.0, 0.0, self.WIDTH, height)

    @staticmethod
    def _category_accent(category: str) -> QColor:
        normalized = category.strip().lower()
        if normalized.startswith("core"):
            return QColor("#2f89ff")
        if "input" in normalized or "output" in normalized:
            return QColor("#22b455")
        if "physics" in normalized:
            return QColor("#d88c32")
        if "logic" in normalized:
            return QColor("#b35bd1")
        return QColor("#4aa9d6")

    def boundingRect(self) -> QRectF:
        return self._cached_rect.adjusted(-1.0, -1.0, 1.0, 1.0)

    def paint(self, painter: QPainter, option, widget=None) -> None:  # noqa: ANN001
        rect = self._cached_rect
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        border_color = self._border_selected if self.isSelected() else self._border_normal
        painter.setPen(QPen(border_color, 1.2))
        painter.setBrush(self._body_brush)
        painter.drawRoundedRect(rect, 4, 4)

        painter.fillRect(QRectF(rect.left(), rect.top(), rect.width(), 3), self._accent_color)
        painter.fillRect(QRectF(rect.left(), rect.top() + 3, rect.width(), self.HEADER_HEIGHT - 3), self._header_brush)

        try:
            lod = option.levelOfDetailFromTransform(painter.worldTransform())
        except Exception:  # noqa: BLE001
            lod = 1.0
        if lod < 0.38:
            self._draw_lod_compact(painter, rect)
            return

        painter.setFont(self._title_font)
        painter.setPen(self._label_pen)
        title = self.node.title if self.node.title else self.spec.display_name
        painter.drawText(
            QRectF(rect.left() + 8, rect.top() + 4, rect.width() - 16, self.HEADER_HEIGHT - 6),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            title,
        )

        if self.node.collapsed:
            self._draw_collapsed_ports(painter, rect)
            return

        in_ports, out_ports = self.visible_ports()
        painter.setFont(self._text_font)
        row_count = max(len(in_ports), len(out_ports), 1)
        draw_labels = lod >= 0.62
        for row in range(row_count):
            y = rect.top() + self.HEADER_HEIGHT + self.PORT_HEIGHT * (row + 0.6)
            if row < len(in_ports):
                port = in_ports[row]
                self._draw_port(painter, rect.left(), y, port, align_left=True, draw_label=draw_labels)
            if row < len(out_ports):
                port = out_ports[row]
                self._draw_port(painter, rect.right(), y, port, align_left=False, draw_label=draw_labels)

    def _draw_lod_compact(self, painter: QPainter, rect: QRectF) -> None:
        painter.setPen(QPen(self._border_selected if self.isSelected() else self._border_normal, 1))
        painter.setBrush(QBrush(QColor("#2c3038")))
        painter.drawRoundedRect(rect, 3, 3)
        painter.fillRect(QRectF(rect.left(), rect.top(), rect.width(), 3), self._accent_color)
        center_y = rect.center().y()
        painter.setPen(self._port_connected_pen if self._has_connected_port("in") else self._port_exec_pen)
        painter.setBrush(self._port_connected_brush if self._has_connected_port("in") else self._port_hollow_brush)
        painter.drawEllipse(QPointF(rect.left(), center_y), 3.6, 3.6)
        painter.setPen(self._port_connected_pen if self._has_connected_port("out") else self._port_exec_pen)
        painter.setBrush(self._port_connected_brush if self._has_connected_port("out") else self._port_hollow_brush)
        painter.drawEllipse(QPointF(rect.right(), center_y), 3.6, 3.6)

    def _draw_collapsed_ports(self, painter: QPainter, rect: QRectF) -> None:
        y = rect.center().y()
        left_connected = self._has_connected_port("in")
        right_connected = self._has_connected_port("out")
        painter.setPen(self._port_connected_pen if left_connected else QPen(QColor("#888"), 1))
        painter.setBrush(self._port_connected_brush if left_connected else self._port_hollow_brush)
        painter.drawEllipse(QPointF(rect.left(), y), 4, 4)
        painter.setPen(self._port_connected_pen if right_connected else QPen(QColor("#888"), 1))
        painter.setBrush(self._port_connected_brush if right_connected else self._port_hollow_brush)
        painter.drawEllipse(QPointF(rect.right(), y), 4, 4)

    def _draw_port(
        self,
        painter: QPainter,
        x: float,
        y: float,
        port: PortSpec,
        *,
        align_left: bool,
        draw_label: bool,
    ) -> None:
        if port.kind == "exec":
            pen = self._port_exec_pen
        elif port.kind == "completed":
            pen = self._port_completed_pen
        else:
            pen = self._port_data_pen
        connected = self._port_connection_count(port.key) > 0
        painter.setPen(self._port_connected_pen if connected else pen)
        painter.setBrush(self._port_connected_brush if connected else self._port_hollow_brush)
        painter.drawEllipse(QPointF(x, y), 4, 4)
        if not draw_label:
            return
        painter.setPen(self._port_label_pen)
        label_rect = QRectF(
            x + 7 if align_left else x - 100,
            y - 8,
            94,
            16,
        )
        alignment = Qt.AlignmentFlag.AlignLeft if align_left else Qt.AlignmentFlag.AlignRight
        painter.drawText(label_rect, alignment | Qt.AlignmentFlag.AlignVCenter, port.key)

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self._edges:
                edge.update_path()
            if self._on_position_changed:
                point = self.pos()
                self._on_position_changed(self.node.node_id, point.x(), point.y())
        return super().itemChange(change, value)
