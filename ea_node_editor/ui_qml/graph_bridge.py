from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PyQt6.QtCore import QObject, QPointF, QRect, QRectF, pyqtProperty, pyqtSignal, pyqtSlot

from ea_node_editor.graph.model import EdgeInstance, GraphModel, NodeInstance, WorkspaceData
from ea_node_editor.nodes.registry import NodeRegistry
from ea_node_editor.nodes.types import NodeTypeSpec


_NODE_HEADER_HEIGHT = 24.0
_NODE_PORT_HEIGHT = 18.0
_NODE_WIDTH = 210.0
_NODE_COLLAPSED_WIDTH = 130.0
_NODE_COLLAPSED_HEIGHT = 36.0
_NODE_PORTS_TOP = 30.0
_NODE_PORT_CENTER_OFFSET = 6.0
_NODE_PORT_SIDE_MARGIN = 8.0
_NODE_PORT_DOT_RADIUS = 3.5
_EDGE_PAIR_LANE_SPACING = 24.0
_EDGE_PORT_FAN_SPACING = 10.0
_EDGE_FORWARD_LEAD_MIN = 56.0
_EDGE_BACKWARD_VERTICAL_CLEARANCE = 56.0
_EDGE_PIPE_STUB = 44.0
_EDGE_PIPE_STUB_MIN = 32.0
_EDGE_PIPE_STUB_MAX = 72.0
_EDGE_PIPE_MIDDLE_MARGIN = 10.0


@dataclass(slots=True)
class _SelectedNodeProxy:
    node: NodeInstance


class _NodeItemProxy:
    def __init__(self, node: NodeInstance, spec: NodeTypeSpec) -> None:
        self.node = node
        self.spec = spec

    def sceneBoundingRect(self) -> QRectF:
        width, height = _node_size(self.node, self.spec)
        return QRectF(self.node.x, self.node.y, width, height)

    def port_scene_pos(self, port_key: str) -> QPointF:
        return _port_scene_pos(self.node, self.spec, port_key)


class QmlGraphScene(QObject):
    node_selected = pyqtSignal(str)
    workspace_changed = pyqtSignal(str)
    nodes_changed = pyqtSignal()
    edges_changed = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._model: GraphModel | None = None
        self._registry: NodeRegistry | None = None
        self._workspace_id = ""
        self._selected_node_ids: list[str] = []
        self._nodes_payload: list[dict[str, Any]] = []
        self._edges_payload: list[dict[str, Any]] = []

    @property
    def workspace_id(self) -> str:
        return self._workspace_id

    @pyqtProperty("QVariantList", notify=nodes_changed)
    def nodes_model(self) -> list[dict[str, Any]]:
        return self._nodes_payload

    @pyqtProperty("QVariantList", notify=edges_changed)
    def edges_model(self) -> list[dict[str, Any]]:
        return self._edges_payload

    @pyqtProperty(str, notify=node_selected)
    def selected_node_id_value(self) -> str:
        selected = self.selected_node_id()
        return selected or ""

    def _require_bound(self) -> tuple[GraphModel, NodeRegistry]:
        if self._model is None or self._registry is None:
            raise RuntimeError("Scene is not bound")
        return self._model, self._registry

    def set_workspace(self, model: GraphModel, registry: NodeRegistry, workspace_id: str) -> None:
        self._model = model
        self._registry = registry
        self._workspace_id = workspace_id
        self._selected_node_ids = []

        workspace = model.project.workspaces[workspace_id]
        for node in workspace.nodes.values():
            spec = registry.get_spec(node.type_id)
            node.properties = registry.normalize_properties(node.type_id, node.properties)
            node.exposed_ports = {
                port.key: bool(node.exposed_ports.get(port.key, port.exposed))
                for port in spec.ports
            }

        self._rebuild_models()
        self.workspace_changed.emit(workspace_id)
        self.node_selected.emit("")

    def current_workspace(self) -> WorkspaceData:
        if self._model is None:
            raise RuntimeError("Scene has no graph model")
        return self._model.project.workspaces[self._workspace_id]

    def selected_node_id(self) -> str | None:
        for node_id in reversed(self._selected_node_ids):
            if self._node(node_id) is not None:
                return node_id
        return None

    def selectedItems(self) -> list[_SelectedNodeProxy]:
        workspace = self.current_workspace()
        selected: list[_SelectedNodeProxy] = []
        for node_id in self._selected_node_ids:
            node = workspace.nodes.get(node_id)
            if node is not None:
                selected.append(_SelectedNodeProxy(node=node))
        return selected

    def clearSelection(self) -> None:
        if not self._selected_node_ids:
            return
        self._selected_node_ids = []
        self._rebuild_models()
        self.node_selected.emit("")

    @pyqtSlot()
    def clear_selection(self) -> None:
        self.clearSelection()

    @pyqtSlot(str)
    @pyqtSlot(str, bool)
    def select_node(self, node_id: str, additive: bool = False) -> None:
        if not node_id:
            self.clearSelection()
            return
        if self._node(node_id) is None:
            return
        if additive:
            if node_id in self._selected_node_ids:
                self._selected_node_ids = [value for value in self._selected_node_ids if value != node_id]
            else:
                self._selected_node_ids.append(node_id)
        else:
            self._selected_node_ids = [node_id]
        self._rebuild_models()
        self.node_selected.emit(self.selected_node_id() or "")

    @pyqtSlot(float, float, float, float)
    @pyqtSlot(float, float, float, float, bool)
    def select_nodes_in_rect(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        additive: bool = False,
    ) -> None:
        if self._model is None or self._registry is None or not self._workspace_id:
            return

        workspace = self.current_workspace()
        min_x = min(float(x1), float(x2))
        max_x = max(float(x1), float(x2))
        min_y = min(float(y1), float(y2))
        max_y = max(float(y1), float(y2))

        hit_ids: list[str] = []
        for node_id, node in workspace.nodes.items():
            spec = self._registry.get_spec(node.type_id)
            width, height = _node_size(node, spec)
            node_min_x = float(node.x)
            node_max_x = node_min_x + width
            node_min_y = float(node.y)
            node_max_y = node_min_y + height
            if node_max_x < min_x or node_min_x > max_x or node_max_y < min_y or node_min_y > max_y:
                continue
            hit_ids.append(node_id)

        if additive:
            next_selected = [node_id for node_id in self._selected_node_ids if node_id in workspace.nodes]
            for node_id in hit_ids:
                if node_id not in next_selected:
                    next_selected.append(node_id)
        else:
            next_selected = hit_ids

        if next_selected == self._selected_node_ids:
            return

        self._selected_node_ids = next_selected
        self._rebuild_models()
        self.node_selected.emit(self.selected_node_id() or "")

    def node_item(self, node_id: str) -> _NodeItemProxy | None:
        node = self._node(node_id)
        if node is None or self._registry is None:
            return None
        spec = self._registry.get_spec(node.type_id)
        return _NodeItemProxy(node=node, spec=spec)

    def edge_item(self, edge_id: str) -> dict[str, Any] | None:
        workspace = self.current_workspace()
        edge = workspace.edges.get(edge_id)
        if edge is None:
            return None
        return {
            "edge_id": edge.edge_id,
            "source_node_id": edge.source_node_id,
            "source_port_key": edge.source_port_key,
            "target_node_id": edge.target_node_id,
            "target_port_key": edge.target_port_key,
        }

    @pyqtSlot(str, float, float, result=str)
    def add_node_from_type(self, type_id: str, x: float = 0.0, y: float = 0.0) -> str:
        model, registry = self._require_bound()
        spec = registry.get_spec(type_id)
        node = model.add_node(
            self._workspace_id,
            type_id=type_id,
            title=spec.display_name,
            x=float(x),
            y=float(y),
            properties=registry.default_properties(type_id),
            exposed_ports={port.key: port.exposed for port in spec.ports},
        )
        self._selected_node_ids = [node.node_id]
        self._rebuild_models()
        self.node_selected.emit(node.node_id)
        return node.node_id

    def add_edge(self, source_node_id: str, source_port: str, target_node_id: str, target_port: str) -> str:
        model, registry = self._require_bound()
        source_node = self._node_or_raise(source_node_id)
        target_node = self._node_or_raise(target_node_id)
        source_spec = registry.get_spec(source_node.type_id)
        target_spec = registry.get_spec(target_node.type_id)

        if _port_direction(source_spec, source_port) != "out":
            raise ValueError(f"Source port must be an output: {source_node_id}.{source_port}")
        if _port_direction(target_spec, target_port) != "in":
            raise ValueError(f"Target port must be an input: {target_node_id}.{target_port}")
        source_kind = _port_kind(source_spec, source_port)
        target_kind = _port_kind(target_spec, target_port)
        if not _are_port_kinds_compatible(source_kind, target_kind):
            raise ValueError(f"Incompatible port kinds: {source_kind} -> {target_kind}.")
        if not _is_port_exposed(source_node, source_spec, source_port):
            raise ValueError(f"Source port is hidden: {source_node_id}.{source_port}")
        if not _is_port_exposed(target_node, target_spec, target_port):
            raise ValueError(f"Target port is hidden: {target_node_id}.{target_port}")

        existing = self._find_model_edge_id(source_node_id, source_port, target_node_id, target_port)
        if existing:
            return existing

        edge = model.add_edge(
            self._workspace_id,
            source_node_id=source_node_id,
            source_port_key=source_port,
            target_node_id=target_node_id,
            target_port_key=target_port,
        )
        self._rebuild_models()
        return edge.edge_id

    @pyqtSlot(str, str, result=str)
    def connect_nodes(self, node_a_id: str, node_b_id: str) -> str:
        model, registry = self._require_bound()
        workspace = model.project.workspaces[self._workspace_id]
        node_a = workspace.nodes[node_a_id]
        node_b = workspace.nodes[node_b_id]
        spec_a = registry.get_spec(node_a.type_id)
        spec_b = registry.get_spec(node_b.type_id)

        a_to_b = (_default_port(node_a, spec_a, "out"), _default_port(node_b, spec_b, "in"))
        b_to_a = (_default_port(node_b, spec_b, "out"), _default_port(node_a, spec_a, "in"))

        can_a_to_b = all(a_to_b)
        can_b_to_a = all(b_to_a)
        if can_a_to_b and (not can_b_to_a or node_a.x <= node_b.x):
            return self.add_edge(node_a_id, a_to_b[0], node_b_id, a_to_b[1])
        if can_b_to_a:
            return self.add_edge(node_b_id, b_to_a[0], node_a_id, b_to_a[1])
        raise ValueError("Selected nodes do not have compatible out/in ports.")

    def remove_edge(self, edge_id: str) -> None:
        if self._model is None:
            return
        self._model.remove_edge(self._workspace_id, edge_id)
        self._rebuild_models()

    def remove_node(self, node_id: str) -> None:
        if self._model is None:
            return
        self._model.remove_node(self._workspace_id, node_id)
        self._selected_node_ids = [value for value in self._selected_node_ids if value != node_id]
        self._rebuild_models()
        if not self._selected_node_ids:
            self.node_selected.emit("")

    @pyqtSlot(str)
    def focus_node_slot(self, node_id: str) -> None:
        self.focus_node(node_id)

    def focus_node(self, node_id: str) -> QPointF | None:
        item = self.node_item(node_id)
        if item is None:
            return None
        self._selected_node_ids = [node_id]
        self._rebuild_models()
        self.node_selected.emit(node_id)
        return item.sceneBoundingRect().center()

    def set_node_collapsed(self, node_id: str, collapsed: bool) -> None:
        if self._model is None:
            return
        self._model.set_node_collapsed(self._workspace_id, node_id, bool(collapsed))
        self._rebuild_models()

    def set_node_property(self, node_id: str, key: str, value: Any) -> None:
        if self._model is None or self._registry is None:
            return
        workspace = self._model.project.workspaces[self._workspace_id]
        node = workspace.nodes[node_id]
        normalized = self._registry.normalize_property_value(node.type_id, key, value)
        self._model.set_node_property(self._workspace_id, node_id, key, normalized)
        self._rebuild_models()

    def set_node_title(self, node_id: str, title: str) -> None:
        if self._model is None:
            return
        if self._node(node_id) is None:
            return
        normalized = str(title).strip()
        if not normalized:
            return
        self._model.set_node_title(self._workspace_id, node_id, normalized)
        self._rebuild_models()

    def set_exposed_port(self, node_id: str, key: str, exposed: bool) -> None:
        if self._model is None or self._registry is None:
            return
        self._model.set_exposed_port(self._workspace_id, node_id, key, bool(exposed))
        if not exposed:
            workspace = self._model.project.workspaces[self._workspace_id]
            affected_edges = [
                edge_id
                for edge_id, edge in workspace.edges.items()
                if (edge.source_node_id == node_id and edge.source_port_key == key)
                or (edge.target_node_id == node_id and edge.target_port_key == key)
            ]
            for edge_id in affected_edges:
                self._model.remove_edge(self._workspace_id, edge_id)
        self._rebuild_models()

    @pyqtSlot(str, float, float)
    def move_node(self, node_id: str, x: float, y: float) -> None:
        if self._model is None:
            return
        if self._node(node_id) is None:
            return
        self._model.set_node_position(self._workspace_id, node_id, float(x), float(y))
        self._rebuild_models()

    def _node(self, node_id: str) -> NodeInstance | None:
        if self._model is None:
            return None
        workspace = self._model.project.workspaces.get(self._workspace_id)
        if workspace is None:
            return None
        return workspace.nodes.get(node_id)

    def _node_or_raise(self, node_id: str) -> NodeInstance:
        node = self._node(node_id)
        if node is None:
            raise KeyError(f"Unknown scene node: {node_id}")
        return node

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

    def _rebuild_models(self) -> None:
        if self._model is None or self._registry is None or not self._workspace_id:
            self._nodes_payload = []
            self._edges_payload = []
            self.nodes_changed.emit()
            self.edges_changed.emit()
            return

        workspace = self._model.project.workspaces[self._workspace_id]
        workspace_edges = list(workspace.edges.values())
        port_connection_counts: dict[tuple[str, str], int] = {}
        for edge in workspace_edges:
            source_key = (edge.source_node_id, edge.source_port_key)
            target_key = (edge.target_node_id, edge.target_port_key)
            port_connection_counts[source_key] = port_connection_counts.get(source_key, 0) + 1
            port_connection_counts[target_key] = port_connection_counts.get(target_key, 0) + 1

        nodes_payload: list[dict[str, Any]] = []
        node_specs: dict[str, NodeTypeSpec] = {}

        for node_id, node in workspace.nodes.items():
            spec = self._registry.get_spec(node.type_id)
            node_specs[node_id] = spec
            width, height = _node_size(node, spec)
            ports_payload: list[dict[str, Any]] = []
            for port in spec.ports:
                exposed = bool(node.exposed_ports.get(port.key, port.exposed))
                if not exposed:
                    continue
                connection_count = port_connection_counts.get((node.node_id, port.key), 0)
                ports_payload.append(
                    {
                        "key": port.key,
                        "direction": port.direction,
                        "kind": port.kind,
                        "data_type": port.data_type,
                        "exposed": exposed,
                        "connection_count": int(connection_count),
                        "connected": bool(connection_count),
                    }
                )
            nodes_payload.append(
                {
                    "node_id": node.node_id,
                    "type_id": node.type_id,
                    "title": node.title,
                    "x": float(node.x),
                    "y": float(node.y),
                    "width": float(width),
                    "height": float(height),
                    "accent": _category_accent(spec.category),
                    "collapsed": bool(node.collapsed),
                    "selected": node.node_id in self._selected_node_ids,
                    "ports": ports_payload,
                }
            )

        pair_lane_offsets = _edge_lane_offsets(
            workspace_edges,
            grouping_key=lambda edge: (edge.source_node_id, edge.target_node_id),
            spacing=_EDGE_PAIR_LANE_SPACING,
        )
        source_fan_offsets = _edge_lane_offsets(
            workspace_edges,
            grouping_key=lambda edge: (edge.source_node_id, edge.source_port_key),
            spacing=_EDGE_PORT_FAN_SPACING,
        )
        target_fan_offsets = _edge_lane_offsets(
            workspace_edges,
            grouping_key=lambda edge: (edge.target_node_id, edge.target_port_key),
            spacing=_EDGE_PORT_FAN_SPACING,
        )

        edges_payload: list[dict[str, Any]] = []
        for edge in workspace_edges:
            source_node = workspace.nodes.get(edge.source_node_id)
            target_node = workspace.nodes.get(edge.target_node_id)
            source_spec = node_specs.get(edge.source_node_id)
            target_spec = node_specs.get(edge.target_node_id)
            if source_node is None or target_node is None or source_spec is None or target_spec is None:
                continue
            source = _port_scene_pos(source_node, source_spec, edge.source_port_key)
            target = _port_scene_pos(target_node, target_spec, edge.target_port_key)
            source_width, source_height = _node_size(source_node, source_spec)
            target_width, target_height = _node_size(target_node, target_spec)
            source_bounds = QRectF(source_node.x, source_node.y, source_width, source_height)
            target_bounds = QRectF(target_node.x, target_node.y, target_width, target_height)
            pair_lane = pair_lane_offsets.get(edge.edge_id, 0.0)
            source_fan = source_fan_offsets.get(edge.edge_id, 0.0)
            target_fan = target_fan_offsets.get(edge.edge_id, 0.0)
            lane_bias = pair_lane + source_fan - target_fan
            route_mode = "bezier"
            pipe_points: list[dict[str, float]] = []

            if float(target.x()) < float(source.x()) - 8.0:
                route_mode = "pipe"
                pipe_points = _edge_pipe_points(
                    source,
                    target,
                    source_bounds,
                    target_bounds,
                    pair_lane=pair_lane,
                    source_fan=source_fan,
                    target_fan=target_fan,
                )
                c1x = float(pipe_points[1]["x"])
                c1y = float(pipe_points[1]["y"])
                c2x = float(pipe_points[-2]["x"])
                c2y = float(pipe_points[-2]["y"])
            else:
                c1x, c1y, c2x, c2y = _edge_control_points(
                    source,
                    target,
                    source_bounds,
                    target_bounds,
                    pair_lane=pair_lane,
                    source_fan=source_fan,
                    target_fan=target_fan,
                )
            src_dt = _port_data_type(source_spec, edge.source_port_key)
            tgt_dt = _port_data_type(target_spec, edge.target_port_key)
            dt_warning = not _are_data_types_compatible(src_dt, tgt_dt)
            color = _edge_color(source_spec, edge.source_port_key, data_type_warning=dt_warning)
            edges_payload.append(
                {
                    "edge_id": edge.edge_id,
                    "source_node_id": edge.source_node_id,
                    "source_port_key": edge.source_port_key,
                    "target_node_id": edge.target_node_id,
                    "target_port_key": edge.target_port_key,
                    "route": route_mode,
                    "pipe_points": pipe_points,
                    "lane_bias": float(lane_bias),
                    "sx": float(source.x()),
                    "sy": float(source.y()),
                    "tx": float(target.x()),
                    "ty": float(target.y()),
                    "c1x": float(c1x),
                    "c1y": c1y,
                    "c2x": float(c2x),
                    "c2y": c2y,
                    "color": color,
                    "data_type_warning": dt_warning,
                }
            )

        self._nodes_payload = nodes_payload
        self._edges_payload = edges_payload
        self.nodes_changed.emit()
        self.edges_changed.emit()


class QmlGraphView(QObject):
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

    def viewport(self) -> "QmlGraphView":
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


def _node_size(node: NodeInstance, spec: NodeTypeSpec) -> tuple[float, float]:
    in_ports, out_ports = _visible_ports(node, spec)
    if node.collapsed:
        return _NODE_COLLAPSED_WIDTH, _NODE_COLLAPSED_HEIGHT
    port_count = max(len(in_ports), len(out_ports), 1)
    height = _NODE_HEADER_HEIGHT + port_count * _NODE_PORT_HEIGHT + 8.0
    return _NODE_WIDTH, height


def _visible_ports(node: NodeInstance, spec: NodeTypeSpec):
    in_ports = []
    out_ports = []
    for port in spec.ports:
        exposed = bool(node.exposed_ports.get(port.key, port.exposed))
        if not exposed:
            continue
        if port.direction == "in":
            in_ports.append(port)
        else:
            out_ports.append(port)
    return in_ports, out_ports


def _port_direction(spec: NodeTypeSpec, port_key: str) -> str:
    for port in spec.ports:
        if port.key == port_key:
            return port.direction
    raise KeyError(f"Port {port_key} not found on node type {spec.type_id}")


def _port_kind(spec: NodeTypeSpec, port_key: str) -> str:
    for port in spec.ports:
        if port.key == port_key:
            return port.kind
    raise KeyError(f"Port {port_key} not found on node type {spec.type_id}")


_FLOW_KINDS = {"exec", "completed", "failed"}


def _are_port_kinds_compatible(source_kind: str, target_kind: str) -> bool:
    if source_kind in _FLOW_KINDS or target_kind in _FLOW_KINDS:
        return source_kind == target_kind
    return True


def _is_port_exposed(node: NodeInstance, spec: NodeTypeSpec, port_key: str) -> bool:
    for port in spec.ports:
        if port.key == port_key:
            return bool(node.exposed_ports.get(port.key, port.exposed))
    raise KeyError(f"Port {port_key} not found on node type {spec.type_id}")


def _default_port(node: NodeInstance, spec: NodeTypeSpec, direction: str) -> str | None:
    for port in spec.ports:
        if port.direction != direction:
            continue
        if bool(node.exposed_ports.get(port.key, port.exposed)):
            return port.key
    return None


def _port_scene_pos(node: NodeInstance, spec: NodeTypeSpec, port_key: str) -> QPointF:
    in_ports, out_ports = _visible_ports(node, spec)
    direction = _port_direction(spec, port_key)
    width, _height = _node_size(node, spec)

    if node.collapsed:
        if direction == "in":
            return QPointF(node.x, node.y + (_NODE_COLLAPSED_HEIGHT * 0.5))
        return QPointF(node.x + width, node.y + (_NODE_COLLAPSED_HEIGHT * 0.5))

    visible_ports = in_ports if direction == "in" else out_ports
    row_index = 0
    for index, port in enumerate(visible_ports):
        if port.key == port_key:
            row_index = index
            break
    y = node.y + _NODE_PORTS_TOP + _NODE_PORT_CENTER_OFFSET + _NODE_PORT_HEIGHT * row_index
    if direction == "in":
        return QPointF(node.x + _NODE_PORT_SIDE_MARGIN + _NODE_PORT_DOT_RADIUS, y)
    return QPointF(node.x + width - _NODE_PORT_SIDE_MARGIN - _NODE_PORT_DOT_RADIUS, y)


def _edge_color(spec: NodeTypeSpec, source_port_key: str, data_type_warning: bool = False) -> str:
    for port in spec.ports:
        if port.key != source_port_key:
            continue
        if port.kind == "exec":
            return "#67D487"
        if port.kind == "completed":
            return "#E4CE7D"
        if port.kind == "failed":
            return "#D94F4F"
    if data_type_warning:
        return "#E8A838"
    return "#7AA8FF"


def _port_data_type(spec: NodeTypeSpec, port_key: str) -> str:
    for port in spec.ports:
        if port.key == port_key:
            return port.data_type
    return "any"


def _are_data_types_compatible(source_type: str, target_type: str) -> bool:
    if source_type == "any" or target_type == "any":
        return True
    return source_type == target_type


def _edge_lane_offsets(
    edges: list[EdgeInstance],
    grouping_key,
    spacing: float,
) -> dict[str, float]:
    grouped: dict[tuple[str, str], list[EdgeInstance]] = {}
    for edge in edges:
        key = grouping_key(edge)
        grouped.setdefault(key, []).append(edge)

    offsets: dict[str, float] = {}
    for grouped_edges in grouped.values():
        grouped_edges.sort(key=lambda edge: (edge.source_port_key, edge.target_port_key, edge.edge_id))
        if len(grouped_edges) <= 1:
            offsets[grouped_edges[0].edge_id] = 0.0
            continue
        center = (len(grouped_edges) - 1) / 2.0
        for index, edge in enumerate(grouped_edges):
            offsets[edge.edge_id] = (index - center) * float(spacing)
    return offsets


def _edge_control_points(
    source: QPointF,
    target: QPointF,
    source_bounds: QRectF,
    target_bounds: QRectF,
    *,
    pair_lane: float,
    source_fan: float,
    target_fan: float,
) -> tuple[float, float, float, float]:
    dx = float(target.x() - source.x())

    lead = max(_EDGE_FORWARD_LEAD_MIN, abs(dx) * 0.5)
    lead += abs(pair_lane) * 0.2
    c1x = float(source.x() + lead)
    c2x = float(target.x() - lead)
    c1y = float(source.y() + source_fan + pair_lane * 0.35)
    c2y = float(target.y() + target_fan - pair_lane * 0.35)
    return c1x, c1y, c2x, c2y


def _edge_pipe_points(
    source: QPointF,
    target: QPointF,
    source_bounds: QRectF,
    target_bounds: QRectF,
    *,
    pair_lane: float,
    source_fan: float,
    target_fan: float,
) -> list[dict[str, float]]:
    dx = float(target.x() - source.x())
    stub = min(_EDGE_PIPE_STUB_MAX, max(_EDGE_PIPE_STUB_MIN, max(_EDGE_PIPE_STUB, abs(dx) * 0.2)))
    source_stub_x = float(max(source_bounds.right(), source.x()) + stub)
    target_stub_x = float(min(target_bounds.left(), target.x()) - stub)

    if source_stub_x <= target_stub_x:
        mid_x = (source_stub_x + target_stub_x) * 0.5
        source_stub_x = mid_x + _EDGE_PIPE_STUB * 0.5
        target_stub_x = mid_x - _EDGE_PIPE_STUB * 0.5

    vertical_clearance = _EDGE_BACKWARD_VERTICAL_CLEARANCE * 0.6 + abs(pair_lane) * 0.8
    lane_bias = pair_lane + source_fan - target_fan
    top_bound = float(min(source_bounds.top(), target_bounds.top()))
    bottom_bound = float(max(source_bounds.bottom(), target_bounds.bottom()))
    top_route_y = float(top_bound - vertical_clearance - max(0.0, lane_bias))
    bottom_route_y = float(bottom_bound + vertical_clearance + max(0.0, -lane_bias))
    source_y = float(source.y())
    target_y = float(target.y())

    def route_len(route_y: float) -> float:
        return (
            abs(source_stub_x - float(source.x()))
            + abs(route_y - source_y)
            + abs(source_stub_x - target_stub_x)
            + abs(target_y - route_y)
            + abs(float(target.x()) - target_stub_x)
        )

    route_candidates: list[tuple[float, int]] = [
        (top_route_y, 1),
        (bottom_route_y, 1),
    ]

    middle_low: float | None = None
    middle_high: float | None = None
    source_bottom = float(source_bounds.bottom())
    source_top = float(source_bounds.top())
    target_bottom = float(target_bounds.bottom())
    target_top = float(target_bounds.top())
    if source_bottom + _EDGE_PIPE_MIDDLE_MARGIN <= target_top - _EDGE_PIPE_MIDDLE_MARGIN:
        middle_low = source_bottom + _EDGE_PIPE_MIDDLE_MARGIN
        middle_high = target_top - _EDGE_PIPE_MIDDLE_MARGIN
    elif target_bottom + _EDGE_PIPE_MIDDLE_MARGIN <= source_top - _EDGE_PIPE_MIDDLE_MARGIN:
        middle_low = target_bottom + _EDGE_PIPE_MIDDLE_MARGIN
        middle_high = source_top - _EDGE_PIPE_MIDDLE_MARGIN

    if middle_low is not None and middle_high is not None and middle_low <= middle_high:
        preferred_middle = (source_y + target_y) * 0.5 + lane_bias * 0.35
        middle_route_y = min(middle_high, max(middle_low, preferred_middle))
        route_candidates.append((middle_route_y, 0))

    route_y = min(route_candidates, key=lambda item: (route_len(item[0]), item[1]))[0]

    return [
        {"x": float(source.x()), "y": source_y},
        {"x": source_stub_x, "y": source_y},
        {"x": source_stub_x, "y": route_y},
        {"x": target_stub_x, "y": route_y},
        {"x": target_stub_x, "y": target_y},
        {"x": float(target.x()), "y": target_y},
    ]


def _category_accent(category: str) -> str:
    normalized = category.strip().lower()
    if normalized.startswith("core"):
        return "#2F89FF"
    if "input" in normalized or "output" in normalized:
        return "#22B455"
    if "physics" in normalized:
        return "#D88C32"
    if "logic" in normalized:
        return "#B35BD1"
    if "hpc" in normalized:
        return "#C75050"
    return "#4AA9D6"
