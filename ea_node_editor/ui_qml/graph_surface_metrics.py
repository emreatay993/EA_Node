from __future__ import annotations

import math
import textwrap
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ea_node_editor.graph.effective_ports import port_direction, visible_ports
from ea_node_editor.graph.model import NodeInstance
from ea_node_editor.nodes.types import NodeTypeSpec, inline_property_specs
from ea_node_editor.ui.media_preview_provider import local_image_dimensions

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

FLOWCHART_COLLAPSED_WIDTH = 140.0
FLOWCHART_COLLAPSED_HEIGHT = 40.0
FLOWCHART_TITLE_HEIGHT = 24.0
FLOWCHART_PORT_HEIGHT = 18.0
FLOWCHART_PORT_CENTER_OFFSET = 6.0
FLOWCHART_PORT_DOT_RADIUS = 4.0
FLOWCHART_RESIZE_HANDLE_SIZE = 16.0
FLOWCHART_INLINE_GAP = 8.0
FLOWCHART_PORT_SECTION_TOP = 12.0

PASSIVE_SURFACE_RESIZE_HANDLE_SIZE = 16.0
MEDIA_CAPTION_SPACING = 10.0
MEDIA_CAPTION_MAX_LINES = 4
MEDIA_CAPTION_LINE_HEIGHT_FACTOR = 1.3
MEDIA_CAPTION_CHAR_WIDTH_FACTOR = 0.55


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
    title_top: float
    title_height: float
    title_left_margin: float
    title_right_margin: float
    title_centered: bool
    body_left_margin: float
    body_right_margin: float
    body_bottom_margin: float
    show_header_background: bool
    show_accent_bar: bool
    use_host_chrome: bool

    def to_payload(self) -> dict[str, Any]:
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
            "title_top": float(self.title_top),
            "title_height": float(self.title_height),
            "title_left_margin": float(self.title_left_margin),
            "title_right_margin": float(self.title_right_margin),
            "title_centered": bool(self.title_centered),
            "body_left_margin": float(self.body_left_margin),
            "body_right_margin": float(self.body_right_margin),
            "body_bottom_margin": float(self.body_bottom_margin),
            "show_header_background": bool(self.show_header_background),
            "show_accent_bar": bool(self.show_accent_bar),
            "use_host_chrome": bool(self.use_host_chrome),
        }


@dataclass(frozen=True, slots=True)
class _FlowchartVariantLayout:
    default_width: float
    min_width: float
    min_height: float
    title_top: float
    title_left_margin: float
    title_right_margin: float
    body_left_margin: float
    body_right_margin: float
    body_bottom_margin: float
    square: bool = False


@dataclass(frozen=True, slots=True)
class _PassivePanelLayout:
    default_width: float
    default_height: float
    min_width: float
    min_height: float
    title_top: float
    title_height: float
    title_left_margin: float
    title_right_margin: float
    body_top: float
    body_height: float
    body_left_margin: float
    body_right_margin: float
    body_bottom_margin: float
    title_centered: bool = False


@dataclass(frozen=True, slots=True)
class _MediaPanelLayout:
    default_width: float
    default_height: float
    min_width: float
    min_height: float
    title_top: float
    title_height: float
    title_left_margin: float
    title_right_margin: float
    body_top: float
    min_body_height: float
    body_left_margin: float
    body_right_margin: float
    body_bottom_margin: float
    title_centered: bool = False


_FLOWCHART_VARIANT_LAYOUTS: dict[str, _FlowchartVariantLayout] = {
    "start": _FlowchartVariantLayout(
        default_width=228.0,
        min_width=152.0,
        min_height=78.0,
        title_top=18.0,
        title_left_margin=34.0,
        title_right_margin=34.0,
        body_left_margin=30.0,
        body_right_margin=30.0,
        body_bottom_margin=16.0,
    ),
    "end": _FlowchartVariantLayout(
        default_width=228.0,
        min_width=152.0,
        min_height=78.0,
        title_top=18.0,
        title_left_margin=34.0,
        title_right_margin=34.0,
        body_left_margin=30.0,
        body_right_margin=30.0,
        body_bottom_margin=16.0,
    ),
    "process": _FlowchartVariantLayout(
        default_width=224.0,
        min_width=156.0,
        min_height=84.0,
        title_top=18.0,
        title_left_margin=20.0,
        title_right_margin=20.0,
        body_left_margin=18.0,
        body_right_margin=18.0,
        body_bottom_margin=16.0,
    ),
    "decision": _FlowchartVariantLayout(
        default_width=236.0,
        min_width=192.0,
        min_height=128.0,
        title_top=26.0,
        title_left_margin=66.0,
        title_right_margin=66.0,
        body_left_margin=46.0,
        body_right_margin=46.0,
        body_bottom_margin=22.0,
    ),
    "document": _FlowchartVariantLayout(
        default_width=228.0,
        min_width=176.0,
        min_height=104.0,
        title_top=18.0,
        title_left_margin=24.0,
        title_right_margin=24.0,
        body_left_margin=20.0,
        body_right_margin=20.0,
        body_bottom_margin=24.0,
    ),
    "connector": _FlowchartVariantLayout(
        default_width=108.0,
        min_width=92.0,
        min_height=92.0,
        title_top=18.0,
        title_left_margin=20.0,
        title_right_margin=20.0,
        body_left_margin=20.0,
        body_right_margin=20.0,
        body_bottom_margin=18.0,
        square=True,
    ),
    "input_output": _FlowchartVariantLayout(
        default_width=236.0,
        min_width=182.0,
        min_height=94.0,
        title_top=20.0,
        title_left_margin=34.0,
        title_right_margin=34.0,
        body_left_margin=28.0,
        body_right_margin=28.0,
        body_bottom_margin=18.0,
    ),
    "predefined_process": _FlowchartVariantLayout(
        default_width=236.0,
        min_width=182.0,
        min_height=94.0,
        title_top=20.0,
        title_left_margin=36.0,
        title_right_margin=36.0,
        body_left_margin=30.0,
        body_right_margin=30.0,
        body_bottom_margin=18.0,
    ),
    "database": _FlowchartVariantLayout(
        default_width=228.0,
        min_width=180.0,
        min_height=128.0,
        title_top=24.0,
        title_left_margin=30.0,
        title_right_margin=30.0,
        body_left_margin=24.0,
        body_right_margin=24.0,
        body_bottom_margin=22.0,
    ),
}

_PLANNING_VARIANT_LAYOUTS: dict[str, _PassivePanelLayout] = {
    "task_card": _PassivePanelLayout(
        default_width=248.0,
        default_height=168.0,
        min_width=190.0,
        min_height=148.0,
        title_top=12.0,
        title_height=24.0,
        title_left_margin=14.0,
        title_right_margin=14.0,
        body_top=44.0,
        body_height=112.0,
        body_left_margin=14.0,
        body_right_margin=14.0,
        body_bottom_margin=12.0,
    ),
    "milestone_card": _PassivePanelLayout(
        default_width=248.0,
        default_height=156.0,
        min_width=190.0,
        min_height=136.0,
        title_top=12.0,
        title_height=24.0,
        title_left_margin=14.0,
        title_right_margin=14.0,
        body_top=44.0,
        body_height=100.0,
        body_left_margin=14.0,
        body_right_margin=14.0,
        body_bottom_margin=12.0,
    ),
    "risk_card": _PassivePanelLayout(
        default_width=252.0,
        default_height=180.0,
        min_width=196.0,
        min_height=156.0,
        title_top=12.0,
        title_height=24.0,
        title_left_margin=14.0,
        title_right_margin=14.0,
        body_top=44.0,
        body_height=124.0,
        body_left_margin=14.0,
        body_right_margin=14.0,
        body_bottom_margin=12.0,
    ),
    "decision_card": _PassivePanelLayout(
        default_width=252.0,
        default_height=180.0,
        min_width=196.0,
        min_height=156.0,
        title_top=12.0,
        title_height=24.0,
        title_left_margin=14.0,
        title_right_margin=14.0,
        body_top=44.0,
        body_height=124.0,
        body_left_margin=14.0,
        body_right_margin=14.0,
        body_bottom_margin=12.0,
    ),
}

_ANNOTATION_VARIANT_LAYOUTS: dict[str, _PassivePanelLayout] = {
    "sticky_note": _PassivePanelLayout(
        default_width=228.0,
        default_height=152.0,
        min_width=176.0,
        min_height=128.0,
        title_top=14.0,
        title_height=22.0,
        title_left_margin=14.0,
        title_right_margin=14.0,
        body_top=42.0,
        body_height=98.0,
        body_left_margin=14.0,
        body_right_margin=14.0,
        body_bottom_margin=12.0,
    ),
    "callout": _PassivePanelLayout(
        default_width=236.0,
        default_height=156.0,
        min_width=184.0,
        min_height=132.0,
        title_top=14.0,
        title_height=22.0,
        title_left_margin=16.0,
        title_right_margin=16.0,
        body_top=42.0,
        body_height=102.0,
        body_left_margin=16.0,
        body_right_margin=16.0,
        body_bottom_margin=12.0,
    ),
    "section_header": _PassivePanelLayout(
        default_width=280.0,
        default_height=112.0,
        min_width=220.0,
        min_height=96.0,
        title_top=18.0,
        title_height=24.0,
        title_left_margin=18.0,
        title_right_margin=18.0,
        body_top=52.0,
        body_height=34.0,
        body_left_margin=18.0,
        body_right_margin=18.0,
        body_bottom_margin=12.0,
    ),
}

_MEDIA_VARIANT_LAYOUTS: dict[str, _MediaPanelLayout] = {
    "image_panel": _MediaPanelLayout(
        default_width=296.0,
        default_height=236.0,
        min_width=220.0,
        min_height=176.0,
        title_top=12.0,
        title_height=24.0,
        title_left_margin=14.0,
        title_right_margin=14.0,
        body_top=44.0,
        min_body_height=120.0,
        body_left_margin=14.0,
        body_right_margin=14.0,
        body_bottom_margin=12.0,
    ),
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


def normalize_flowchart_variant(variant: str) -> str:
    normalized = str(variant or "").strip().lower()
    return normalized if normalized in _FLOWCHART_VARIANT_LAYOUTS else "process"


def normalize_planning_variant(variant: str) -> str:
    normalized = str(variant or "").strip().lower()
    return normalized if normalized in _PLANNING_VARIANT_LAYOUTS else "task_card"


def normalize_annotation_variant(variant: str) -> str:
    normalized = str(variant or "").strip().lower()
    return normalized if normalized in _ANNOTATION_VARIANT_LAYOUTS else "sticky_note"


def normalize_media_variant(variant: str) -> str:
    normalized = str(variant or "").strip().lower()
    return normalized if normalized in _MEDIA_VARIANT_LAYOUTS else "image_panel"


def _safe_number(value: Any, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    if not math.isfinite(number):
        return fallback
    return number


def _wrapped_media_caption_lines(text: str, max_chars_per_line: int) -> int:
    line_count = 0
    paragraphs = text.splitlines() or [text]
    wrap_width = max(1, int(max_chars_per_line))
    for paragraph in paragraphs:
        normalized = paragraph.expandtabs(4)
        if not normalized:
            line_count += 1
        else:
            wrapped = textwrap.wrap(
                normalized,
                width=wrap_width,
                break_long_words=True,
                break_on_hyphens=False,
                drop_whitespace=False,
                replace_whitespace=False,
            )
            line_count += max(1, len(wrapped))
        if line_count >= MEDIA_CAPTION_MAX_LINES:
            return MEDIA_CAPTION_MAX_LINES
    return max(1, min(line_count, MEDIA_CAPTION_MAX_LINES))


def _media_caption_height(node: NodeInstance, content_width: float) -> float:
    caption = str(node.properties.get("caption", "") or "")
    if not caption:
        return 0.0
    font_size = max(1.0, _safe_number(node.visual_style.get("font_size"), 12.0))
    line_height = max(1.0, math.ceil(font_size * MEDIA_CAPTION_LINE_HEIGHT_FACTOR))
    average_char_width = max(1.0, font_size * MEDIA_CAPTION_CHAR_WIDTH_FACTOR)
    max_chars_per_line = max(1, int(max(1.0, content_width) / average_char_width))
    line_count = _wrapped_media_caption_lines(caption, max_chars_per_line)
    return line_height * line_count


def _media_default_dimensions(
    node: NodeInstance,
    layout: _MediaPanelLayout,
) -> tuple[float, float]:
    default_width = float(layout.default_width)
    default_height = float(layout.default_height)
    image_dimensions = local_image_dimensions(str(node.properties.get("source_path", "") or ""))
    if image_dimensions is None:
        return default_width, default_height
    image_width, image_height = image_dimensions
    if image_width <= 0 or image_height <= 0:
        return default_width, default_height

    preview_width = max(1.0, default_width - layout.body_left_margin - layout.body_right_margin)
    preview_height = preview_width * (float(image_height) / float(image_width))
    caption_height = _media_caption_height(node, preview_width)
    caption_extra = (MEDIA_CAPTION_SPACING + caption_height) if caption_height > 0.0 else 0.0
    body_height = max(layout.min_body_height, preview_height + caption_extra)
    return (
        default_width,
        max(layout.min_height, layout.body_top + layout.body_bottom_margin + body_height),
    )


def _resolved_dimensions(
    node: NodeInstance,
    *,
    default_width: float,
    default_height: float,
) -> tuple[float, float]:
    width = float(node.custom_width) if node.custom_width is not None else float(default_width)
    height = float(node.custom_height) if node.custom_height is not None else float(default_height)
    return width, height


def _visible_port_count(
    node: NodeInstance,
    spec: NodeTypeSpec,
    workspace_nodes: Mapping[str, NodeInstance] | None = None,
) -> int:
    scoped_nodes = workspace_nodes or {node.node_id: node}
    in_ports, out_ports = visible_ports(node=node, spec=spec, workspace_nodes=scoped_nodes)
    return max(len(in_ports), len(out_ports), 1)


def _standard_surface_metrics(
    node: NodeInstance,
    spec: NodeTypeSpec,
    workspace_nodes: Mapping[str, NodeInstance] | None = None,
) -> GraphNodeSurfaceMetrics:
    port_count = _visible_port_count(node, spec, workspace_nodes)
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
        title_top=STANDARD_HEADER_TOP_MARGIN,
        title_height=STANDARD_HEADER_HEIGHT,
        title_left_margin=10.0,
        title_right_margin=10.0,
        title_centered=False,
        body_left_margin=8.0,
        body_right_margin=8.0,
        body_bottom_margin=STANDARD_BOTTOM_PADDING,
        show_header_background=True,
        show_accent_bar=True,
        use_host_chrome=True,
    )


def _flowchart_surface_metrics(
    node: NodeInstance,
    spec: NodeTypeSpec,
    workspace_nodes: Mapping[str, NodeInstance] | None = None,
) -> GraphNodeSurfaceMetrics:
    layout = _FLOWCHART_VARIANT_LAYOUTS[normalize_flowchart_variant(spec.surface_variant)]
    body_height = standard_inline_body_height(spec)
    port_count = _visible_port_count(node, spec, workspace_nodes)
    base_port_section_top = (
        layout.title_top + FLOWCHART_TITLE_HEIGHT + FLOWCHART_INLINE_GAP + body_height + FLOWCHART_INLINE_GAP
        if body_height > 0.0
        else FLOWCHART_PORT_SECTION_TOP
    )
    default_height = max(
        layout.min_height,
        base_port_section_top + port_count * FLOWCHART_PORT_HEIGHT + layout.body_bottom_margin,
    )
    default_width = layout.default_width
    min_width = layout.min_width
    if layout.square:
        default_width = max(default_width, default_height)
        min_width = max(min_width, layout.min_height)

    active_width, active_height = _resolved_dimensions(
        node,
        default_width=default_width,
        default_height=default_height,
    )
    title_top = (
        layout.title_top
        if body_height > 0.0
        else max(12.0, (active_height - FLOWCHART_TITLE_HEIGHT) * 0.5)
    )
    body_top = title_top + FLOWCHART_TITLE_HEIGHT + FLOWCHART_INLINE_GAP
    port_section_top = (
        body_top + body_height + FLOWCHART_INLINE_GAP if body_height > 0.0 else FLOWCHART_PORT_SECTION_TOP
    )
    available_port_height = max(
        port_count * FLOWCHART_PORT_HEIGHT,
        active_height - port_section_top - layout.body_bottom_margin,
    )
    port_top = port_section_top + max(0.0, (available_port_height - port_count * FLOWCHART_PORT_HEIGHT) * 0.5)
    return GraphNodeSurfaceMetrics(
        default_width=default_width,
        default_height=default_height,
        min_width=min_width,
        min_height=layout.min_height,
        collapsed_width=FLOWCHART_COLLAPSED_WIDTH,
        collapsed_height=FLOWCHART_COLLAPSED_HEIGHT,
        header_height=0.0,
        header_top_margin=0.0,
        body_top=body_top,
        body_height=body_height,
        port_top=port_top,
        port_height=FLOWCHART_PORT_HEIGHT,
        port_center_offset=FLOWCHART_PORT_CENTER_OFFSET,
        port_side_margin=0.0,
        port_dot_radius=FLOWCHART_PORT_DOT_RADIUS,
        resize_handle_size=FLOWCHART_RESIZE_HANDLE_SIZE,
        title_top=title_top,
        title_height=FLOWCHART_TITLE_HEIGHT,
        title_left_margin=layout.title_left_margin,
        title_right_margin=layout.title_right_margin,
        title_centered=True,
        body_left_margin=layout.body_left_margin,
        body_right_margin=layout.body_right_margin,
        body_bottom_margin=layout.body_bottom_margin,
        show_header_background=False,
        show_accent_bar=False,
        use_host_chrome=False,
    )


def _passive_panel_surface_metrics(
    node: NodeInstance,
    layout: _PassivePanelLayout,
) -> GraphNodeSurfaceMetrics:
    _active_width, active_height = _resolved_dimensions(
        node,
        default_width=layout.default_width,
        default_height=layout.default_height,
    )
    body_height = max(layout.body_height, active_height - layout.body_top - layout.body_bottom_margin)
    return GraphNodeSurfaceMetrics(
        default_width=layout.default_width,
        default_height=layout.default_height,
        min_width=layout.min_width,
        min_height=layout.min_height,
        collapsed_width=STANDARD_COLLAPSED_WIDTH,
        collapsed_height=STANDARD_COLLAPSED_HEIGHT,
        header_height=0.0,
        header_top_margin=0.0,
        body_top=layout.body_top,
        body_height=body_height,
        port_top=active_height - layout.body_bottom_margin,
        port_height=0.0,
        port_center_offset=0.0,
        port_side_margin=STANDARD_PORT_SIDE_MARGIN,
        port_dot_radius=STANDARD_PORT_DOT_RADIUS,
        resize_handle_size=PASSIVE_SURFACE_RESIZE_HANDLE_SIZE,
        title_top=layout.title_top,
        title_height=layout.title_height,
        title_left_margin=layout.title_left_margin,
        title_right_margin=layout.title_right_margin,
        title_centered=layout.title_centered,
        body_left_margin=layout.body_left_margin,
        body_right_margin=layout.body_right_margin,
        body_bottom_margin=layout.body_bottom_margin,
        show_header_background=False,
        show_accent_bar=False,
        use_host_chrome=True,
    )


def _planning_surface_metrics(node: NodeInstance, spec: NodeTypeSpec) -> GraphNodeSurfaceMetrics:
    layout = _PLANNING_VARIANT_LAYOUTS[normalize_planning_variant(spec.surface_variant)]
    return _passive_panel_surface_metrics(node, layout)


def _annotation_surface_metrics(node: NodeInstance, spec: NodeTypeSpec) -> GraphNodeSurfaceMetrics:
    layout = _ANNOTATION_VARIANT_LAYOUTS[normalize_annotation_variant(spec.surface_variant)]
    return _passive_panel_surface_metrics(node, layout)


def _media_surface_metrics(node: NodeInstance, spec: NodeTypeSpec) -> GraphNodeSurfaceMetrics:
    layout = _MEDIA_VARIANT_LAYOUTS[normalize_media_variant(spec.surface_variant)]
    default_width, default_height = _media_default_dimensions(node, layout)
    _active_width, active_height = _resolved_dimensions(
        node,
        default_width=default_width,
        default_height=default_height,
    )
    body_height = max(layout.min_body_height, active_height - layout.body_top - layout.body_bottom_margin)
    return GraphNodeSurfaceMetrics(
        default_width=default_width,
        default_height=default_height,
        min_width=layout.min_width,
        min_height=layout.min_height,
        collapsed_width=STANDARD_COLLAPSED_WIDTH,
        collapsed_height=STANDARD_COLLAPSED_HEIGHT,
        header_height=0.0,
        header_top_margin=0.0,
        body_top=layout.body_top,
        body_height=body_height,
        port_top=active_height - layout.body_bottom_margin,
        port_height=0.0,
        port_center_offset=0.0,
        port_side_margin=STANDARD_PORT_SIDE_MARGIN,
        port_dot_radius=STANDARD_PORT_DOT_RADIUS,
        resize_handle_size=PASSIVE_SURFACE_RESIZE_HANDLE_SIZE,
        title_top=layout.title_top,
        title_height=layout.title_height,
        title_left_margin=layout.title_left_margin,
        title_right_margin=layout.title_right_margin,
        title_centered=layout.title_centered,
        body_left_margin=layout.body_left_margin,
        body_right_margin=layout.body_right_margin,
        body_bottom_margin=layout.body_bottom_margin,
        show_header_background=False,
        show_accent_bar=False,
        use_host_chrome=True,
    )


def node_surface_metrics(
    node: NodeInstance,
    spec: NodeTypeSpec,
    workspace_nodes: Mapping[str, NodeInstance] | None = None,
) -> GraphNodeSurfaceMetrics:
    family = str(spec.surface_family or "standard").strip() or "standard"
    if family == "flowchart":
        return _flowchart_surface_metrics(node, spec, workspace_nodes)
    if family == "planning":
        return _planning_surface_metrics(node, spec)
    if family == "annotation":
        return _annotation_surface_metrics(node, spec)
    if family == "media":
        return _media_surface_metrics(node, spec)
    return _standard_surface_metrics(node, spec, workspace_nodes)


def _flowchart_horizontal_bounds(
    variant: str,
    width: float,
    height: float,
    local_y: float,
) -> tuple[float, float]:
    if width <= 0.0 or height <= 0.0:
        return 0.0, max(0.0, width)
    y_value = max(0.0, min(height, local_y))
    if variant in {"start", "end"}:
        radius = min(width * 0.5, height * 0.5)
        cy = height * 0.5
        dy = max(-radius, min(radius, y_value - cy))
        dx = math.sqrt(max(0.0, radius * radius - dy * dy))
        left = radius - dx
        return left, width - left
    if variant == "decision":
        left = abs((height * 0.5) - y_value) * width / height
        return left, width - left
    if variant == "connector":
        rx = width * 0.5
        ry = height * 0.5
        cy = height * 0.5
        dy = max(-ry, min(ry, y_value - cy))
        if ry <= 0.0:
            return 0.0, width
        factor = math.sqrt(max(0.0, 1.0 - (dy * dy) / (ry * ry)))
        dx = rx * factor
        return rx - dx, rx + dx
    if variant == "input_output":
        slant = min(width * 0.13, height * 0.26)
        left = max(0.0, slant * (1.0 - (y_value / height)))
        return left, width - left
    return 0.0, width


def surface_port_local_point(
    node: NodeInstance,
    spec: NodeTypeSpec,
    port_key: str,
    workspace_nodes: Mapping[str, NodeInstance] | None = None,
    *,
    width: float | None = None,
    height: float | None = None,
) -> tuple[float, float]:
    scoped_nodes = workspace_nodes or {node.node_id: node}
    metrics = node_surface_metrics(node, spec, scoped_nodes)
    resolved_width, resolved_height = _resolved_dimensions(
        node,
        default_width=metrics.default_width,
        default_height=metrics.default_height,
    )
    width_value = float(width) if width is not None else resolved_width
    height_value = float(height) if height is not None else resolved_height

    direction = port_direction(node=node, spec=spec, workspace_nodes=scoped_nodes, port_key=port_key)
    if node.collapsed:
        return (
            0.0 if direction == "in" else width_value,
            metrics.collapsed_height * 0.5,
        )

    in_ports, out_ports = visible_ports(node=node, spec=spec, workspace_nodes=scoped_nodes)
    visible = in_ports if direction == "in" else out_ports
    row_index = 0
    for index, port in enumerate(visible):
        if port.key == port_key:
            row_index = index
            break
    local_y = metrics.port_top + metrics.port_center_offset + metrics.port_height * row_index
    family = str(spec.surface_family or "standard").strip() or "standard"
    if family == "flowchart":
        left, right = _flowchart_horizontal_bounds(
            normalize_flowchart_variant(spec.surface_variant),
            width_value,
            height_value,
            local_y,
        )
        return (left if direction == "in" else right), local_y
    if direction == "in":
        return metrics.port_side_margin + metrics.port_dot_radius, local_y
    return width_value - metrics.port_side_margin - metrics.port_dot_radius, local_y
