from __future__ import annotations

import copy
import math
from collections.abc import Mapping
from typing import Any

from PyQt6.QtCore import QPointF, QRectF

from ea_node_editor.graph.effective_ports import (
    are_data_types_compatible,
    port_data_type,
    port_direction,
    port_kind,
)
from ea_node_editor.graph.model import EdgeInstance, NodeInstance
from ea_node_editor.nodes.types import NodeTypeSpec, inline_property_specs
from ea_node_editor.ui.graph_theme import GraphThemeDefinition, resolve_edge_color
from ea_node_editor.ui_qml.graph_surface_metrics import (
    node_surface_metrics,
    standard_inline_body_height,
    surface_port_local_point,
)

EDGE_PAIR_LANE_SPACING = 24.0
EDGE_PORT_FAN_SPACING = 10.0
EDGE_FORWARD_LEAD_MIN = 56.0
EDGE_BACKWARD_VERTICAL_CLEARANCE = 56.0
EDGE_PIPE_STUB = 44.0
EDGE_PIPE_STUB_MIN = 32.0
EDGE_PIPE_STUB_MAX = 72.0
EDGE_PIPE_MIDDLE_MARGIN = 10.0
_FLOW_EDGE_STROKE_PATTERNS = {"solid", "dashed", "dotted"}
_FLOW_EDGE_ARROW_HEADS = {"filled", "open", "none"}


def inline_body_height(spec: NodeTypeSpec) -> float:
    return standard_inline_body_height(spec)


def node_size(
    node: NodeInstance,
    spec: NodeTypeSpec,
    workspace_nodes: Mapping[str, NodeInstance] | None = None,
) -> tuple[float, float]:
    scoped_nodes = workspace_nodes or {node.node_id: node}
    metrics = node_surface_metrics(node, spec, scoped_nodes)
    if node.collapsed:
        return metrics.collapsed_width, metrics.collapsed_height
    width = node.custom_width if node.custom_width is not None else metrics.default_width
    height = node.custom_height if node.custom_height is not None else metrics.default_height
    return width, height


def port_scene_pos(
    node: NodeInstance,
    spec: NodeTypeSpec,
    port_key: str,
    workspace_nodes: Mapping[str, NodeInstance] | None = None,
) -> QPointF:
    scoped_nodes = workspace_nodes or {node.node_id: node}
    metrics = node_surface_metrics(node, spec, scoped_nodes)
    width, _height = node_size(node, spec, scoped_nodes)

    if node.collapsed:
        direction = port_direction(node=node, spec=spec, workspace_nodes=scoped_nodes, port_key=port_key)
        if direction == "in":
            return QPointF(node.x, node.y + (metrics.collapsed_height * 0.5))
        return QPointF(node.x + width, node.y + (metrics.collapsed_height * 0.5))

    local_x, local_y = surface_port_local_point(
        node,
        spec,
        port_key,
        scoped_nodes,
        width=width,
        height=_height,
    )
    return QPointF(node.x + local_x, node.y + local_y)


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


def normalize_flow_edge_visual_style_payload(visual_style: Any) -> dict[str, Any]:
    if not isinstance(visual_style, Mapping):
        return {}
    normalized: dict[str, Any] = {}

    def normalized_string(value: Any) -> str:
        if not isinstance(value, str):
            return ""
        return value.strip()

    def normalized_positive_number(value: Any) -> float | None:
        if isinstance(value, bool):
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(numeric) or numeric <= 0.0:
            return None
        return numeric

    stroke_color = normalized_string(visual_style.get("stroke_color") or visual_style.get("color"))
    if stroke_color:
        normalized["stroke_color"] = stroke_color

    stroke_width = normalized_positive_number(visual_style.get("stroke_width"))
    if stroke_width is not None:
        normalized["stroke_width"] = stroke_width

    stroke_pattern = normalized_string(visual_style.get("stroke_pattern") or visual_style.get("stroke")).lower()
    if stroke_pattern in _FLOW_EDGE_STROKE_PATTERNS:
        normalized["stroke_pattern"] = stroke_pattern

    arrow_head = normalized_string(visual_style.get("arrow_head")).lower()
    if not arrow_head:
        arrow_payload = visual_style.get("arrow")
        if isinstance(arrow_payload, Mapping):
            arrow_head = normalized_string(arrow_payload.get("kind")).lower()
    if arrow_head in _FLOW_EDGE_ARROW_HEADS:
        normalized["arrow_head"] = arrow_head

    label_text_color = normalized_string(visual_style.get("label_text_color"))
    if label_text_color:
        normalized["label_text_color"] = label_text_color

    label_background_color = normalized_string(visual_style.get("label_background_color"))
    if label_background_color:
        normalized["label_background_color"] = label_background_color

    return normalized


def build_edge_payload(
    *,
    graph_theme: GraphThemeDefinition | object,
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
        source = port_scene_pos(
            source_node,
            source_spec,
            edge.source_port_key,
            workspace_nodes,
        )
        target = port_scene_pos(
            target_node,
            target_spec,
            edge.target_port_key,
            workspace_nodes,
        )
        source_width, source_height = node_size(source_node, source_spec, workspace_nodes)
        target_width, target_height = node_size(target_node, target_spec, workspace_nodes)
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
        src_dt = port_data_type(
            node=source_node,
            spec=source_spec,
            workspace_nodes=workspace_nodes,
            port_key=edge.source_port_key,
        )
        tgt_dt = port_data_type(
            node=target_node,
            spec=target_spec,
            workspace_nodes=workspace_nodes,
            port_key=edge.target_port_key,
        )
        dt_warning = not are_data_types_compatible(src_dt, tgt_dt)
        source_port_kind = port_kind(
            node=source_node,
            spec=source_spec,
            workspace_nodes=workspace_nodes,
            port_key=edge.source_port_key,
        )
        target_port_kind = port_kind(
            node=target_node,
            spec=target_spec,
            workspace_nodes=workspace_nodes,
            port_key=edge.target_port_key,
        )
        edge_family = "flow" if source_port_kind == "flow" and target_port_kind == "flow" else "standard"
        flow_style = normalize_flow_edge_visual_style_payload(edge.visual_style) if edge_family == "flow" else {}
        color = resolve_edge_color(
            graph_theme,
            port_kind=source_port_kind,
            data_type_warning=dt_warning,
        )
        edges_payload.append(
            {
                "edge_id": edge.edge_id,
                "source_node_id": edge.source_node_id,
                "source_port_key": edge.source_port_key,
                "target_node_id": edge.target_node_id,
                "target_port_key": edge.target_port_key,
                "source_port_kind": source_port_kind,
                "target_port_kind": target_port_kind,
                "edge_family": edge_family,
                "label": str(edge.label),
                "visual_style": copy.deepcopy(edge.visual_style),
                "flow_style": flow_style,
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
