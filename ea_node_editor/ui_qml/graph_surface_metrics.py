from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ea_node_editor.graph.effective_ports import visible_ports
from ea_node_editor.graph.model import NodeInstance
from ea_node_editor.nodes.types import NodeTypeSpec, inline_property_specs

STANDARD_DEFAULT_WIDTH = 210.0
STANDARD_MIN_WIDTH = 120.0
STANDARD_MIN_HEIGHT = 50.0
STANDARD_COLLAPSED_WIDTH = 130.0
STANDARD_COLLAPSED_HEIGHT = 36.0
STANDARD_HEADER_HEIGHT = 24.0
STANDARD_HEADER_TOP_MARGIN = 4.0
STANDARD_BODY_TOP = 30.0
STANDARD_PORT_HEIGHT = 18.0
STANDARD_INLINE_ROW_HEIGHT = 26.0
STANDARD_INLINE_ROW_SPACING = 4.0
STANDARD_INLINE_SECTION_PADDING = 8.0
STANDARD_PORT_CENTER_OFFSET = 6.0
STANDARD_PORT_SIDE_MARGIN = 8.0
STANDARD_PORT_DOT_RADIUS = 3.5
STANDARD_RESIZE_HANDLE_SIZE = 16.0
STANDARD_BOTTOM_PADDING = 8.0


@dataclass(frozen=True, slots=True)
class GraphNodeSurfaceMetrics:
    default_width: float
    default_height: float
    min_width: float
    min_height: float
    collapsed_width: float
    collapsed_height: float
    header_height: float
    header_top_margin: float
    body_top: float
    body_height: float
    port_top: float
    port_height: float
    port_center_offset: float
    port_side_margin: float
    port_dot_radius: float
    resize_handle_size: float

    def to_payload(self) -> dict[str, float]:
        return {
            "default_width": float(self.default_width),
            "default_height": float(self.default_height),
            "min_width": float(self.min_width),
            "min_height": float(self.min_height),
            "collapsed_width": float(self.collapsed_width),
            "collapsed_height": float(self.collapsed_height),
            "header_height": float(self.header_height),
            "header_top_margin": float(self.header_top_margin),
            "body_top": float(self.body_top),
            "body_height": float(self.body_height),
            "port_top": float(self.port_top),
            "port_height": float(self.port_height),
            "port_center_offset": float(self.port_center_offset),
            "port_side_margin": float(self.port_side_margin),
            "port_dot_radius": float(self.port_dot_radius),
            "resize_handle_size": float(self.resize_handle_size),
        }


def standard_inline_body_height(spec: NodeTypeSpec) -> float:
    inline_count = len(inline_property_specs(spec))
    if inline_count <= 0:
        return 0.0
    return (
        STANDARD_INLINE_SECTION_PADDING
        + inline_count * STANDARD_INLINE_ROW_HEIGHT
        + max(0, inline_count - 1) * STANDARD_INLINE_ROW_SPACING
    )


def _standard_surface_metrics(
    node: NodeInstance,
    spec: NodeTypeSpec,
    workspace_nodes: Mapping[str, NodeInstance] | None = None,
) -> GraphNodeSurfaceMetrics:
    scoped_nodes = workspace_nodes or {node.node_id: node}
    in_ports, out_ports = visible_ports(node=node, spec=spec, workspace_nodes=scoped_nodes)
    port_count = max(len(in_ports), len(out_ports), 1)
    body_height = standard_inline_body_height(spec)
    default_height = STANDARD_HEADER_HEIGHT + body_height + port_count * STANDARD_PORT_HEIGHT + STANDARD_BOTTOM_PADDING
    return GraphNodeSurfaceMetrics(
        default_width=STANDARD_DEFAULT_WIDTH,
        default_height=default_height,
        min_width=STANDARD_MIN_WIDTH,
        min_height=STANDARD_MIN_HEIGHT,
        collapsed_width=STANDARD_COLLAPSED_WIDTH,
        collapsed_height=STANDARD_COLLAPSED_HEIGHT,
        header_height=STANDARD_HEADER_HEIGHT,
        header_top_margin=STANDARD_HEADER_TOP_MARGIN,
        body_top=STANDARD_BODY_TOP,
        body_height=body_height,
        port_top=STANDARD_BODY_TOP + body_height,
        port_height=STANDARD_PORT_HEIGHT,
        port_center_offset=STANDARD_PORT_CENTER_OFFSET,
        port_side_margin=STANDARD_PORT_SIDE_MARGIN,
        port_dot_radius=STANDARD_PORT_DOT_RADIUS,
        resize_handle_size=STANDARD_RESIZE_HANDLE_SIZE,
    )


def node_surface_metrics(
    node: NodeInstance,
    spec: NodeTypeSpec,
    workspace_nodes: Mapping[str, NodeInstance] | None = None,
) -> GraphNodeSurfaceMetrics:
    family = str(spec.surface_family or "standard").strip() or "standard"
    if family == "standard":
        return _standard_surface_metrics(node, spec, workspace_nodes)
    return _standard_surface_metrics(node, spec, workspace_nodes)

