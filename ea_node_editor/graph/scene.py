from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QPointF, pyqtSignal
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import QGraphicsScene

from ea_node_editor.graph.items.edge_item import EdgeGraphicsItem
from ea_node_editor.graph.items.node_item import NodeGraphicsItem
from ea_node_editor.graph.model import GraphModel, WorkspaceData
from ea_node_editor.nodes.registry import NodeRegistry


class NodeGraphScene(QGraphicsScene):
    node_selected = pyqtSignal(str)
    workspace_changed = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._model: GraphModel | None = None
        self._registry: NodeRegistry | None = None
        self._workspace_id: str = ""
        self._node_items: dict[str, NodeGraphicsItem] = {}
        self._edge_items: dict[str, EdgeGraphicsItem] = {}
        self.setSceneRect(-5000, -5000, 10000, 10000)
        self.selectionChanged.connect(self._on_selection_changed)

    @property
    def workspace_id(self) -> str:
        return self._workspace_id

    def _require_bound(self) -> tuple[GraphModel, NodeRegistry]:
        if self._model is None or self._registry is None:
            raise RuntimeError("Scene is not bound")
        return self._model, self._registry

    def _node_item(self, node_id: str) -> NodeGraphicsItem:
        try:
            return self._node_items[node_id]
        except KeyError as exc:
            raise KeyError(f"Unknown scene node: {node_id}") from exc

    @staticmethod
    def _port_direction(item: NodeGraphicsItem, port_key: str) -> str:
        for port in item.spec.ports:
            if port.key == port_key:
                return port.direction
        raise KeyError(f"Port {port_key} not found on node {item.node.node_id}")

    @staticmethod
    def _port_kind(item: NodeGraphicsItem, port_key: str) -> str:
        for port in item.spec.ports:
            if port.key == port_key:
                return port.kind
        raise KeyError(f"Port {port_key} not found on node {item.node.node_id}")

    def _find_model_edge_id(
        self,
        source_node_id: str,
        source_port: str,
        target_node_id: str,
        target_port: str,
    ) -> str | None:
        if self._model is None:
            return None
        workspace = self._model.project.workspaces[self._workspace_id]
        for edge in workspace.edges.values():
            if (
                edge.source_node_id == source_node_id
                and edge.source_port_key == source_port
                and edge.target_node_id == target_node_id
                and edge.target_port_key == target_port
            ):
                return edge.edge_id
        return None

    def _add_edge_item(
        self,
        edge_id: str,
        source_item: NodeGraphicsItem,
        source_port: str,
        target_item: NodeGraphicsItem,
        target_port: str,
    ) -> None:
        source_data_type = self._get_port_data_type(source_item, source_port)
        target_data_type = self._get_port_data_type(target_item, target_port)
        data_type_mismatch = not self._are_data_types_compatible(source_data_type, target_data_type)

        edge_item = EdgeGraphicsItem(
            edge_id=edge_id,
            source_node=source_item,
            source_port=source_port,
            target_node=target_item,
            target_port=target_port,
            data_type_warning=data_type_mismatch,
        )
        source_item.add_edge(edge_item)
        target_item.add_edge(edge_item)
        self._edge_items[edge_id] = edge_item
        self.addItem(edge_item)

    @staticmethod
    def _is_port_exposed(item: NodeGraphicsItem, port_key: str) -> bool:
        for port in item.spec.ports:
            if port.key == port_key:
                return item.node.exposed_ports.get(port.key, port.exposed)
        raise KeyError(f"Port {port_key} not found on node {item.node.node_id}")

    @staticmethod
    def _default_port(item: NodeGraphicsItem, direction: str) -> str | None:
        for port in item.spec.ports:
            if port.direction != direction:
                continue
            if item.node.exposed_ports.get(port.key, port.exposed):
                return port.key
        return None

    _FLOW_KINDS = {"exec", "completed", "failed"}

    @staticmethod
    def _are_port_kinds_compatible(source_kind: str, target_kind: str) -> bool:
        if source_kind in NodeGraphScene._FLOW_KINDS or target_kind in NodeGraphScene._FLOW_KINDS:
            return source_kind == target_kind
        return True

    @staticmethod
    def _are_data_types_compatible(source_type: str, target_type: str) -> bool:
        """Check whether two data types are compatible.

        Returns True if the types match or either side accepts 'any'.
        Returns False if there is a mismatch (the connection is still
        allowed but the edge should show a warning color).
        """
        if source_type == "any" or target_type == "any":
            return True
        return source_type == target_type

    @staticmethod
    def _get_port_data_type(item: NodeGraphicsItem, port_key: str) -> str:
        for port in item.spec.ports:
            if port.key == port_key:
                return port.data_type
        return "any"

    def set_workspace(self, model: GraphModel, registry: NodeRegistry, workspace_id: str) -> None:
        self.clear()
        self._node_items.clear()
        self._edge_items.clear()
        self._model = model
        self._registry = registry
        self._workspace_id = workspace_id
        workspace = model.project.workspaces[workspace_id]

        for node in workspace.nodes.values():
            spec = registry.get_spec(node.type_id)
            node.properties = registry.normalize_properties(node.type_id, node.properties)
            node.exposed_ports = {
                port.key: bool(node.exposed_ports.get(port.key, port.exposed)) for port in spec.ports
            }
            item = NodeGraphicsItem(node=node, spec=spec, on_position_changed=self._on_node_moved)
            self._node_items[node.node_id] = item
            self.addItem(item)

        for edge in workspace.edges.values():
            source_item = self._node_items.get(edge.source_node_id)
            target_item = self._node_items.get(edge.target_node_id)
            if not source_item or not target_item:
                continue
            self._add_edge_item(
                edge_id=edge.edge_id,
                source_item=source_item,
                source_port=edge.source_port_key,
                target_item=target_item,
                target_port=edge.target_port_key,
            )

        self.workspace_changed.emit(workspace_id)

    def current_workspace(self) -> WorkspaceData:
        if self._model is None:
            raise RuntimeError("Scene has no graph model")
        return self._model.project.workspaces[self._workspace_id]

    def selected_node_id(self) -> str | None:
        for item in self.selectedItems():
            if isinstance(item, NodeGraphicsItem):
                return item.node.node_id
        return None

    def node_item(self, node_id: str) -> NodeGraphicsItem | None:
        return self._node_items.get(node_id)

    def edge_item(self, edge_id: str) -> EdgeGraphicsItem | None:
        return self._edge_items.get(edge_id)

    def add_node_from_type(self, type_id: str, x: float = 0.0, y: float = 0.0) -> str:
        model, registry = self._require_bound()
        spec = registry.get_spec(type_id)
        node = model.add_node(
            self._workspace_id,
            type_id=type_id,
            title=spec.display_name,
            x=x,
            y=y,
            properties=registry.default_properties(type_id),
            exposed_ports={port.key: port.exposed for port in spec.ports},
        )
        item = NodeGraphicsItem(node=node, spec=spec, on_position_changed=self._on_node_moved)
        self._node_items[node.node_id] = item
        self.addItem(item)
        item.setSelected(True)
        return node.node_id

    def add_edge(self, source_node_id: str, source_port: str, target_node_id: str, target_port: str) -> str:
        model, _ = self._require_bound()
        source_item = self._node_item(source_node_id)
        target_item = self._node_item(target_node_id)
        if self._port_direction(source_item, source_port) != "out":
            raise ValueError(f"Source port must be an output: {source_node_id}.{source_port}")
        if self._port_direction(target_item, target_port) != "in":
            raise ValueError(f"Target port must be an input: {target_node_id}.{target_port}")
        source_kind = self._port_kind(source_item, source_port)
        target_kind = self._port_kind(target_item, target_port)
        if not self._are_port_kinds_compatible(source_kind, target_kind):
            raise ValueError(f"Incompatible port kinds: {source_kind} -> {target_kind}.")
        if not self._is_port_exposed(source_item, source_port):
            raise ValueError(f"Source port is hidden: {source_node_id}.{source_port}")
        if not self._is_port_exposed(target_item, target_port):
            raise ValueError(f"Target port is hidden: {target_node_id}.{target_port}")

        existing_edge_id = self._find_model_edge_id(
            source_node_id=source_node_id,
            source_port=source_port,
            target_node_id=target_node_id,
            target_port=target_port,
        )
        if existing_edge_id and existing_edge_id in self._edge_items:
            return existing_edge_id

        edge = model.add_edge(
            self._workspace_id,
            source_node_id=source_node_id,
            source_port_key=source_port,
            target_node_id=target_node_id,
            target_port_key=target_port,
        )
        if edge.edge_id in self._edge_items:
            return edge.edge_id
        try:
            self._add_edge_item(
                edge_id=edge.edge_id,
                source_item=source_item,
                source_port=source_port,
                target_item=target_item,
                target_port=target_port,
            )
        except Exception:  # noqa: BLE001
            if existing_edge_id is None:
                model.remove_edge(self._workspace_id, edge.edge_id)
            raise
        return edge.edge_id

    def connect_nodes(self, node_a_id: str, node_b_id: str) -> str:
        source_item = self._node_item(node_a_id)
        target_item = self._node_item(node_b_id)
        a_to_b = (
            self._default_port(source_item, "out"),
            self._default_port(target_item, "in"),
        )
        b_to_a = (
            self._default_port(target_item, "out"),
            self._default_port(source_item, "in"),
        )
        can_a_to_b = all(a_to_b)
        can_b_to_a = all(b_to_a)
        if can_a_to_b and (not can_b_to_a or source_item.pos().x() <= target_item.pos().x()):
            return self.add_edge(node_a_id, a_to_b[0], node_b_id, a_to_b[1])
        if can_b_to_a:
            return self.add_edge(node_b_id, b_to_a[0], node_a_id, b_to_a[1])
        raise ValueError("Selected nodes do not have compatible out/in ports.")

    def remove_edge(self, edge_id: str) -> None:
        edge_item = self._edge_items.pop(edge_id, None)
        if edge_item is not None:
            edge_item.source_node.remove_edge(edge_item)
            edge_item.target_node.remove_edge(edge_item)
            self.removeItem(edge_item)
        if self._model is not None:
            self._model.remove_edge(self._workspace_id, edge_id)

    def remove_node(self, node_id: str) -> None:
        node_item = self._node_items.get(node_id)
        if node_item is not None:
            for edge_id, edge_item in list(self._edge_items.items()):
                if edge_item.source_node is node_item or edge_item.target_node is node_item:
                    self.remove_edge(edge_id)
            self._node_items.pop(node_id, None)
            self.removeItem(node_item)
        if self._model is not None:
            self._model.remove_node(self._workspace_id, node_id)

    def focus_node(self, node_id: str) -> QPointF | None:
        item = self._node_items.get(node_id)
        if not item:
            return None
        self.clearSelection()
        item.setSelected(True)
        return item.sceneBoundingRect().center()

    def set_node_collapsed(self, node_id: str, collapsed: bool) -> None:
        if self._model is None:
            return
        item = self._node_items.get(node_id)
        if item is not None:
            item.set_collapsed(collapsed)
        self._model.set_node_collapsed(self._workspace_id, node_id, collapsed)

    def set_node_property(self, node_id: str, key: str, value: Any) -> None:
        if self._model is None or self._registry is None:
            return
        node = self._model.project.workspaces[self._workspace_id].nodes[node_id]
        normalized = self._registry.normalize_property_value(node.type_id, key, value)
        self._model.set_node_property(self._workspace_id, node_id, key, normalized)

    def set_node_title(self, node_id: str, title: str) -> None:
        if self._model is None:
            return
        normalized = str(title).strip()
        if not normalized:
            return
        item = self._node_items.get(node_id)
        if item is not None:
            item.node.title = normalized
            item.update()
        self._model.set_node_title(self._workspace_id, node_id, normalized)

    def set_exposed_port(self, node_id: str, key: str, exposed: bool) -> None:
        if self._model is None:
            return
        self._model.set_exposed_port(self._workspace_id, node_id, key, exposed)
        if not exposed:
            workspace = self._model.project.workspaces[self._workspace_id]
            affected_edges = [
                edge_id
                for edge_id, edge in workspace.edges.items()
                if (edge.source_node_id == node_id and edge.source_port_key == key)
                or (edge.target_node_id == node_id and edge.target_port_key == key)
            ]
            for edge_id in affected_edges:
                self.remove_edge(edge_id)
        item = self._node_items.get(node_id)
        if item is not None:
            item.refresh_ports()

    def _on_node_moved(self, node_id: str, x: float, y: float) -> None:
        if self._model is None:
            return
        self._model.set_node_position(self._workspace_id, node_id, x, y)

    def _on_selection_changed(self) -> None:
        node_id = self.selected_node_id()
        self.node_selected.emit(node_id or "")

    def drawBackground(self, painter: QPainter, rect) -> None:  # noqa: ANN001
        painter.fillRect(rect, QColor("#1d1f24"))
        if rect.width() > 7000 or rect.height() > 7000:
            grid_size = 40
        else:
            grid_size = 20
        major_step = grid_size * 5
        left = int(rect.left()) - (int(rect.left()) % grid_size)
        top = int(rect.top()) - (int(rect.top()) % grid_size)

        painter.setPen(QColor("#2a2e37"))
        x = left
        while x < int(rect.right()):
            if x % major_step != 0:
                painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))
            x += grid_size
        y = top
        while y < int(rect.bottom()):
            if y % major_step != 0:
                painter.drawLine(int(rect.left()), y, int(rect.right()), y)
            y += grid_size

        painter.setPen(QColor("#323746"))
        x = left
        while x < int(rect.right()):
            if x % major_step == 0:
                painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))
            x += grid_size
        y = top
        while y < int(rect.bottom()):
            if y % major_step == 0:
                painter.drawLine(int(rect.left()), y, int(rect.right()), y)
            y += grid_size
