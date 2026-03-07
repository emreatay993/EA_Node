from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QPointF, QRectF

from ea_node_editor.graph.model import EdgeInstance, NodeInstance
from ea_node_editor.graph.rules import are_data_types_compatible, port_data_type, port_direction, visible_ports
from ea_node_editor.nodes.types import NodeTypeSpec

NODE_HEADER_HEIGHT = 24.0
NODE_PORT_HEIGHT = 18.0
NODE_WIDTH = 210.0
NODE_COLLAPSED_WIDTH = 130.0
NODE_COLLAPSED_HEIGHT = 36.0
NODE_PORTS_TOP = 30.0
NODE_PORT_CENTER_OFFSET = 6.0
NODE_PORT_SIDE_MARGIN = 8.0
NODE_PORT_DOT_RADIUS = 3.5
EDGE_PAIR_LANE_SPACING = 24.0
EDGE_PORT_FAN_SPACING = 10.0
EDGE_FORWARD_LEAD_MIN = 56.0
EDGE_BACKWARD_VERTICAL_CLEARANCE = 56.0
EDGE_PIPE_STUB = 44.0
EDGE_PIPE_STUB_MIN = 32.0
EDGE_PIPE_STUB_MAX = 72.0
EDGE_PIPE_MIDDLE_MARGIN = 10.0


def node_size(node: NodeInstance, spec: NodeTypeSpec) -> tuple[float, float]:
    in_ports, out_ports = visible_ports(node, spec)
    if node.collapsed:
        return NODE_COLLAPSED_WIDTH, NODE_COLLAPSED_HEIGHT
    port_count = max(len(in_ports), len(out_ports), 1)
    height = NODE_HEADER_HEIGHT + port_count * NODE_PORT_HEIGHT + 8.0
    return NODE_WIDTH, height


def port_scene_pos(node: NodeInstance, spec: NodeTypeSpec, port_key: str) -> QPointF:
    in_ports, out_ports = visible_ports(node, spec)
    direction = port_direction(spec, port_key)
    width, _height = node_size(node, spec)

    if node.collapsed:
        if direction == "in":
            return QPointF(node.x, node.y + (NODE_COLLAPSED_HEIGHT * 0.5))
        return QPointF(node.x + width, node.y + (NODE_COLLAPSED_HEIGHT * 0.5))

    visible = in_ports if direction == "in" else out_ports
    row_index = 0
    for index, port in enumerate(visible):
        if port.key == port_key:
            row_index = index
            break
    y = node.y + NODE_PORTS_TOP + NODE_PORT_CENTER_OFFSET + NODE_PORT_HEIGHT * row_index
    if direction == "in":
        return QPointF(node.x + NODE_PORT_SIDE_MARGIN + NODE_PORT_DOT_RADIUS, y)
    return QPointF(node.x + width - NODE_PORT_SIDE_MARGIN - NODE_PORT_DOT_RADIUS, y)


def edge_color(spec: NodeTypeSpec, source_port_key: str, data_type_warning: bool = False) -> str:
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


def edge_lane_offsets(
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


def edge_control_points(
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

    lead = max(EDGE_FORWARD_LEAD_MIN, abs(dx) * 0.5)
    lead += abs(pair_lane) * 0.2
    c1x = float(source.x() + lead)
    c2x = float(target.x() - lead)
    c1y = float(source.y() + source_fan + pair_lane * 0.35)
    c2y = float(target.y() + target_fan - pair_lane * 0.35)
    return c1x, c1y, c2x, c2y


def edge_pipe_points(
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
    stub = min(EDGE_PIPE_STUB_MAX, max(EDGE_PIPE_STUB_MIN, max(EDGE_PIPE_STUB, abs(dx) * 0.2)))
    source_stub_x = float(max(source_bounds.right(), source.x()) + stub)
    target_stub_x = float(min(target_bounds.left(), target.x()) - stub)

    if source_stub_x <= target_stub_x:
        mid_x = (source_stub_x + target_stub_x) * 0.5
        source_stub_x = mid_x + EDGE_PIPE_STUB * 0.5
        target_stub_x = mid_x - EDGE_PIPE_STUB * 0.5

    vertical_clearance = EDGE_BACKWARD_VERTICAL_CLEARANCE * 0.6 + abs(pair_lane) * 0.8
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
    if source_bottom + EDGE_PIPE_MIDDLE_MARGIN <= target_top - EDGE_PIPE_MIDDLE_MARGIN:
        middle_low = source_bottom + EDGE_PIPE_MIDDLE_MARGIN
        middle_high = target_top - EDGE_PIPE_MIDDLE_MARGIN
    elif target_bottom + EDGE_PIPE_MIDDLE_MARGIN <= source_top - EDGE_PIPE_MIDDLE_MARGIN:
        middle_low = target_bottom + EDGE_PIPE_MIDDLE_MARGIN
        middle_high = source_top - EDGE_PIPE_MIDDLE_MARGIN

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


def category_accent(category: str) -> str:
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


def build_edge_payload(
    *,
    workspace_edges: list[EdgeInstance],
    workspace_nodes: dict[str, NodeInstance],
    node_specs: dict[str, NodeTypeSpec],
) -> list[dict[str, Any]]:
    pair_lane_offsets = edge_lane_offsets(
        workspace_edges,
        grouping_key=lambda edge: (edge.source_node_id, edge.target_node_id),
        spacing=EDGE_PAIR_LANE_SPACING,
    )
    source_fan_offsets = edge_lane_offsets(
        workspace_edges,
        grouping_key=lambda edge: (edge.source_node_id, edge.source_port_key),
        spacing=EDGE_PORT_FAN_SPACING,
    )
    target_fan_offsets = edge_lane_offsets(
        workspace_edges,
        grouping_key=lambda edge: (edge.target_node_id, edge.target_port_key),
        spacing=EDGE_PORT_FAN_SPACING,
    )

    edges_payload: list[dict[str, Any]] = []
    for edge in workspace_edges:
        source_node = workspace_nodes.get(edge.source_node_id)
        target_node = workspace_nodes.get(edge.target_node_id)
        source_spec = node_specs.get(edge.source_node_id)
        target_spec = node_specs.get(edge.target_node_id)
        if source_node is None or target_node is None or source_spec is None or target_spec is None:
            continue
        source = port_scene_pos(source_node, source_spec, edge.source_port_key)
        target = port_scene_pos(target_node, target_spec, edge.target_port_key)
        source_width, source_height = node_size(source_node, source_spec)
        target_width, target_height = node_size(target_node, target_spec)
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
            pipe_points = edge_pipe_points(
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
            c1x, c1y, c2x, c2y = edge_control_points(
                source,
                target,
                source_bounds,
                target_bounds,
                pair_lane=pair_lane,
                source_fan=source_fan,
                target_fan=target_fan,
            )
        src_dt = port_data_type(source_spec, edge.source_port_key)
        tgt_dt = port_data_type(target_spec, edge.target_port_key)
        dt_warning = not are_data_types_compatible(src_dt, tgt_dt)
        color = edge_color(source_spec, edge.source_port_key, data_type_warning=dt_warning)
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
    return edges_payload
