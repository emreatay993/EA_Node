from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ea_node_editor.graph.effective_ports import (
    are_data_types_compatible,
    port_data_type,
    port_kind,
)
from ea_node_editor.graph.model import EdgeInstance, NodeInstance
from ea_node_editor.nodes.types import NodeTypeSpec
from ea_node_editor.ui.graph_theme import GraphThemeDefinition, resolve_edge_color

from .anchors import flowchart_anchor_normal, flowchart_anchor_tangent, flowchart_port_side
from .route_endpoints import (
    _ResolvedEdgeEndpoint,
    _flow_pipe_route_sides,
    _flowchart_decision_source_fan_bias,
    _is_flowchart_surface,
    _rect_payload,
    _resolve_edge_endpoint,
    port_scene_pos,
)
from .route_pipe import (
    _orthogonal_flow_pipe_points,
    _pipe_control_handles,
    _should_use_flow_pipe_route,
    edge_control_points,
    edge_pipe_points,
)
from .route_styles import (
    EDGE_PAIR_LANE_SPACING,
    EDGE_PORT_FAN_SPACING,
    edge_lane_offsets,
    normalize_flow_edge_visual_style_payload,
)


@dataclass(frozen=True, slots=True)
class _EdgeLaneOffsets:
    pair_by_edge_id: Mapping[str, float]
    source_by_edge_id: Mapping[str, float]
    target_by_edge_id: Mapping[str, float]

    def values_for(self, edge_id: str) -> tuple[float, float, float]:
        return (
            float(self.pair_by_edge_id.get(edge_id, 0.0)),
            float(self.source_by_edge_id.get(edge_id, 0.0)),
            float(self.target_by_edge_id.get(edge_id, 0.0)),
        )


@dataclass(frozen=True, slots=True)
class _ResolvedEdgeRoute:
    route_mode: str
    pipe_points: list[dict[str, float]]
    c1x: float
    c1y: float
    c2x: float
    c2y: float


@dataclass(frozen=True, slots=True)
class _ResolvedEdgePayloadContext:
    source_node: NodeInstance
    target_node: NodeInstance
    source_spec: NodeTypeSpec
    target_spec: NodeTypeSpec
    source_endpoint: _ResolvedEdgeEndpoint
    target_endpoint: _ResolvedEdgeEndpoint
    source_port_kind: str
    target_port_kind: str
    source_port_side: str
    target_port_side: str
    edge_family: str
    pair_lane: float
    source_fan: float
    target_fan: float
    lane_bias: float
    route_source_side: str
    route_target_side: str
    data_type_warning: bool


def _edge_payload_lane_offsets(workspace_edges: list[EdgeInstance]) -> _EdgeLaneOffsets:
    return _EdgeLaneOffsets(
        pair_by_edge_id=edge_lane_offsets(
            workspace_edges,
            grouping_key=lambda edge: (edge.source_node_id, edge.target_node_id),
            spacing=EDGE_PAIR_LANE_SPACING,
        ),
        source_by_edge_id=edge_lane_offsets(
            workspace_edges,
            grouping_key=lambda edge: (edge.source_node_id, edge.source_port_key),
            spacing=EDGE_PORT_FAN_SPACING,
        ),
        target_by_edge_id=edge_lane_offsets(
            workspace_edges,
            grouping_key=lambda edge: (edge.target_node_id, edge.target_port_key),
            spacing=EDGE_PORT_FAN_SPACING,
        ),
    )


def _resolved_edge_endpoints(
    *,
    edge: EdgeInstance,
    source_node: NodeInstance,
    target_node: NodeInstance,
    source_spec: NodeTypeSpec,
    target_spec: NodeTypeSpec,
    workspace_nodes: Mapping[str, NodeInstance],
    node_specs: Mapping[str, NodeTypeSpec],
    source_proxy_backdrop_id: str,
    target_proxy_backdrop_id: str,
    show_port_labels: bool,
) -> tuple[_ResolvedEdgeEndpoint, _ResolvedEdgeEndpoint]:
    source_endpoint = _resolve_edge_endpoint(
        node_id=edge.source_node_id,
        port_key=edge.source_port_key,
        node=source_node,
        spec=source_spec,
        workspace_nodes=workspace_nodes,
        node_specs=node_specs,
        hidden_by_backdrop_id=source_proxy_backdrop_id,
        opposite_point=port_scene_pos(
            target_node,
            target_spec,
            edge.target_port_key,
            workspace_nodes,
            show_port_labels=show_port_labels,
        ),
        show_port_labels=show_port_labels,
    )
    target_endpoint = _resolve_edge_endpoint(
        node_id=edge.target_node_id,
        port_key=edge.target_port_key,
        node=target_node,
        spec=target_spec,
        workspace_nodes=workspace_nodes,
        node_specs=node_specs,
        hidden_by_backdrop_id=target_proxy_backdrop_id,
        opposite_point=source_endpoint.point,
        show_port_labels=show_port_labels,
    )
    if source_proxy_backdrop_id:
        source_endpoint = _resolve_edge_endpoint(
            node_id=edge.source_node_id,
            port_key=edge.source_port_key,
            node=source_node,
            spec=source_spec,
            workspace_nodes=workspace_nodes,
            node_specs=node_specs,
            hidden_by_backdrop_id=source_proxy_backdrop_id,
            opposite_point=target_endpoint.point,
            show_port_labels=show_port_labels,
        )
    if target_proxy_backdrop_id:
        target_endpoint = _resolve_edge_endpoint(
            node_id=edge.target_node_id,
            port_key=edge.target_port_key,
            node=target_node,
            spec=target_spec,
            workspace_nodes=workspace_nodes,
            node_specs=node_specs,
            hidden_by_backdrop_id=target_proxy_backdrop_id,
            opposite_point=source_endpoint.point,
            show_port_labels=show_port_labels,
        )
    if source_proxy_backdrop_id:
        source_endpoint = _resolve_edge_endpoint(
            node_id=edge.source_node_id,
            port_key=edge.source_port_key,
            node=source_node,
            spec=source_spec,
            workspace_nodes=workspace_nodes,
            node_specs=node_specs,
            hidden_by_backdrop_id=source_proxy_backdrop_id,
            opposite_point=target_endpoint.point,
            show_port_labels=show_port_labels,
        )
    return source_endpoint, target_endpoint


def _resolve_edge_payload_context(
    *,
    edge: EdgeInstance,
    workspace_nodes: Mapping[str, NodeInstance],
    node_specs: Mapping[str, NodeTypeSpec],
    collapsed_proxy_backdrop_by_node_id: Mapping[str, str],
    lane_offsets: _EdgeLaneOffsets,
    show_port_labels: bool,
) -> _ResolvedEdgePayloadContext | None:
    source_node = workspace_nodes.get(edge.source_node_id)
    target_node = workspace_nodes.get(edge.target_node_id)
    source_spec = node_specs.get(edge.source_node_id)
    target_spec = node_specs.get(edge.target_node_id)
    if source_node is None or target_node is None or source_spec is None or target_spec is None:
        return None

    source_proxy_backdrop_id = str(collapsed_proxy_backdrop_by_node_id.get(edge.source_node_id, '') or '')
    target_proxy_backdrop_id = str(collapsed_proxy_backdrop_by_node_id.get(edge.target_node_id, '') or '')
    if source_proxy_backdrop_id and source_proxy_backdrop_id == target_proxy_backdrop_id:
        return None

    source_port_side = flowchart_port_side(source_node, source_spec, edge.source_port_key, workspace_nodes)
    target_port_side = flowchart_port_side(target_node, target_spec, edge.target_port_key, workspace_nodes)
    source_endpoint, target_endpoint = _resolved_edge_endpoints(
        edge=edge,
        source_node=source_node,
        target_node=target_node,
        source_spec=source_spec,
        target_spec=target_spec,
        workspace_nodes=workspace_nodes,
        node_specs=node_specs,
        source_proxy_backdrop_id=source_proxy_backdrop_id,
        target_proxy_backdrop_id=target_proxy_backdrop_id,
        show_port_labels=show_port_labels,
    )

    pair_lane, source_fan, target_fan = lane_offsets.values_for(edge.edge_id)
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
    edge_family = 'flow' if source_port_kind == 'flow' and target_port_kind == 'flow' else 'standard'
    route_source_side, route_target_side = _flow_pipe_route_sides(source_endpoint.side, target_endpoint.side)
    if edge_family == 'flow' and _is_flowchart_surface(source_spec) and _is_flowchart_surface(target_spec):
        source_fan += _flowchart_decision_source_fan_bias(source_spec, edge.source_port_key)

    source_data_type = port_data_type(
        node=source_node,
        spec=source_spec,
        workspace_nodes=workspace_nodes,
        port_key=edge.source_port_key,
    )
    target_data_type = port_data_type(
        node=target_node,
        spec=target_spec,
        workspace_nodes=workspace_nodes,
        port_key=edge.target_port_key,
    )
    return _ResolvedEdgePayloadContext(
        source_node=source_node,
        target_node=target_node,
        source_spec=source_spec,
        target_spec=target_spec,
        source_endpoint=source_endpoint,
        target_endpoint=target_endpoint,
        source_port_kind=source_port_kind,
        target_port_kind=target_port_kind,
        source_port_side=source_port_side,
        target_port_side=target_port_side,
        edge_family=edge_family,
        pair_lane=pair_lane,
        source_fan=source_fan,
        target_fan=target_fan,
        lane_bias=pair_lane + source_fan - target_fan,
        route_source_side=route_source_side,
        route_target_side=route_target_side,
        data_type_warning=not are_data_types_compatible(source_data_type, target_data_type),
    )


def _resolve_edge_route(*, context: _ResolvedEdgePayloadContext) -> _ResolvedEdgeRoute:
    source = context.source_endpoint.point
    target = context.target_endpoint.point
    source_bounds = context.source_endpoint.bounds
    target_bounds = context.target_endpoint.bounds
    route_mode = 'bezier'
    pipe_points: list[dict[str, float]] = []
    if (
        context.edge_family == 'flow'
        and _should_use_flow_pipe_route(
            source,
            target,
            source_bounds,
            target_bounds,
            source_side=context.route_source_side,
            target_side=context.route_target_side,
        )
    ) or (context.edge_family != 'flow' and float(target.x()) < float(source.x()) - 8.0):
        route_mode = 'pipe'
        if context.edge_family == 'flow':
            pipe_points = _orthogonal_flow_pipe_points(
                source,
                target,
                source_bounds,
                target_bounds,
                pair_lane=context.pair_lane,
                source_fan=context.source_fan,
                target_fan=context.target_fan,
                source_side=context.route_source_side,
                target_side=context.route_target_side,
            )
        else:
            pipe_points = edge_pipe_points(
                source,
                target,
                source_bounds,
                target_bounds,
                pair_lane=context.pair_lane,
                source_fan=context.source_fan,
                target_fan=context.target_fan,
                source_side=context.source_endpoint.side,
                target_side=context.target_endpoint.side,
            )
        (c1x, c1y), (c2x, c2y) = _pipe_control_handles(pipe_points)
        return _ResolvedEdgeRoute(
            route_mode=route_mode,
            pipe_points=pipe_points,
            c1x=float(c1x),
            c1y=float(c1y),
            c2x=float(c2x),
            c2y=float(c2y),
        )

    c1x, c1y, c2x, c2y = edge_control_points(
        source,
        target,
        source_bounds,
        target_bounds,
        pair_lane=context.pair_lane,
        source_fan=context.source_fan,
        target_fan=context.target_fan,
        source_side=(
            context.route_source_side
            if context.edge_family == 'flow'
            or context.source_endpoint.hidden_by_backdrop_id
            or context.target_endpoint.hidden_by_backdrop_id
            else ''
        ),
        target_side=(
            context.route_target_side
            if context.edge_family == 'flow'
            or context.source_endpoint.hidden_by_backdrop_id
            or context.target_endpoint.hidden_by_backdrop_id
            else ''
        ),
    )
    return _ResolvedEdgeRoute(
        route_mode=route_mode,
        pipe_points=pipe_points,
        c1x=float(c1x),
        c1y=float(c1y),
        c2x=float(c2x),
        c2y=float(c2y),
    )


def _build_edge_payload_item(
    *,
    edge: EdgeInstance,
    graph_theme: GraphThemeDefinition | object,
    workspace_nodes: Mapping[str, NodeInstance],
    node_specs: Mapping[str, NodeTypeSpec],
    collapsed_proxy_backdrop_by_node_id: Mapping[str, str],
    lane_offsets: _EdgeLaneOffsets,
    show_port_labels: bool,
) -> dict[str, Any] | None:
    context = _resolve_edge_payload_context(
        edge=edge,
        workspace_nodes=workspace_nodes,
        node_specs=node_specs,
        collapsed_proxy_backdrop_by_node_id=collapsed_proxy_backdrop_by_node_id,
        lane_offsets=lane_offsets,
        show_port_labels=show_port_labels,
    )
    if context is None:
        return None

    source_endpoint = context.source_endpoint
    target_endpoint = context.target_endpoint
    source = source_endpoint.point
    target = target_endpoint.point
    source_side = source_endpoint.side
    target_side = target_endpoint.side
    source_normal_x, source_normal_y = flowchart_anchor_normal(source_side)
    target_normal_x, target_normal_y = flowchart_anchor_normal(target_side)
    source_tangent_x, source_tangent_y = flowchart_anchor_tangent(source_side)
    target_tangent_x, target_tangent_y = flowchart_anchor_tangent(target_side)
    route = _resolve_edge_route(context=context)
    flow_style = normalize_flow_edge_visual_style_payload(edge.visual_style) if context.edge_family == 'flow' else {}
    color = resolve_edge_color(
        graph_theme,
        port_kind=context.source_port_kind,
        data_type_warning=context.data_type_warning,
    )
    return {
        'edge_id': edge.edge_id,
        'source_node_id': edge.source_node_id,
        'source_port_key': edge.source_port_key,
        'target_node_id': edge.target_node_id,
        'target_port_key': edge.target_port_key,
        'source_port_kind': context.source_port_kind,
        'target_port_kind': context.target_port_kind,
        'edge_family': context.edge_family,
        'label': str(edge.label),
        'visual_style': copy.deepcopy(edge.visual_style),
        'flow_style': flow_style,
        'source_port_side': context.source_port_side,
        'target_port_side': context.target_port_side,
        'source_anchor_side': source_side,
        'target_anchor_side': target_side,
        'source_anchor_kind': source_endpoint.anchor_kind,
        'target_anchor_kind': target_endpoint.anchor_kind,
        'source_anchor_node_id': source_endpoint.anchor_node_id,
        'target_anchor_node_id': target_endpoint.anchor_node_id,
        'source_hidden_by_backdrop_id': source_endpoint.hidden_by_backdrop_id,
        'target_hidden_by_backdrop_id': target_endpoint.hidden_by_backdrop_id,
        'source_anchor_bounds': _rect_payload(source_endpoint.bounds),
        'target_anchor_bounds': _rect_payload(target_endpoint.bounds),
        'source_normal_x': float(source_normal_x),
        'source_normal_y': float(source_normal_y),
        'target_normal_x': float(target_normal_x),
        'target_normal_y': float(target_normal_y),
        'source_tangent_x': float(source_tangent_x),
        'source_tangent_y': float(source_tangent_y),
        'target_tangent_x': float(target_tangent_x),
        'target_tangent_y': float(target_tangent_y),
        'route': route.route_mode,
        'pipe_points': route.pipe_points,
        'lane_bias': float(context.lane_bias),
        'sx': float(source.x()),
        'sy': float(source.y()),
        'tx': float(target.x()),
        'ty': float(target.y()),
        'c1x': route.c1x,
        'c1y': route.c1y,
        'c2x': route.c2x,
        'c2y': route.c2y,
        'color': color,
        'data_type_warning': context.data_type_warning,
    }


def build_edge_payload(
    *,
    graph_theme: GraphThemeDefinition | object,
    workspace_edges: list[EdgeInstance],
    workspace_nodes: dict[str, NodeInstance],
    node_specs: dict[str, NodeTypeSpec],
    collapsed_proxy_backdrop_by_node_id: Mapping[str, str] | None = None,
    show_port_labels: bool = True,
) -> list[dict[str, Any]]:
    collapsed_proxy_backdrop_by_node_id = collapsed_proxy_backdrop_by_node_id or {}
    lane_offsets = _edge_payload_lane_offsets(workspace_edges)

    edges_payload: list[dict[str, Any]] = []
    for edge in workspace_edges:
        payload_item = _build_edge_payload_item(
            edge=edge,
            graph_theme=graph_theme,
            workspace_nodes=workspace_nodes,
            node_specs=node_specs,
            collapsed_proxy_backdrop_by_node_id=collapsed_proxy_backdrop_by_node_id,
            lane_offsets=lane_offsets,
            show_port_labels=show_port_labels,
        )
        if payload_item is not None:
            edges_payload.append(payload_item)
    return edges_payload
