from __future__ import annotations

import json
import math
import textwrap
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ea_node_editor.graph.effective_ports import find_port, port_direction, port_side, visible_ports
from ea_node_editor.graph.model import NodeInstance
from ea_node_editor.nodes.types import NodeTypeSpec, inline_property_specs
from ea_node_editor.ui.media_preview_provider import local_image_dimensions
from ea_node_editor.ui.pdf_preview_provider import local_pdf_page_dimensions


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


_SURFACE_METRIC_CONTRACT_PATH = (
    Path(__file__).resolve().parent / "components" / "graph" / "GraphNodeSurfaceMetricContract.json"
)
_CARDINAL_SIDES = frozenset({"top", "right", "bottom", "left"})
_FLOWCHART_OUTLINE_INSET = 0.5


@dataclass(frozen=True, slots=True)
class _FlowchartBounds:
    left: float
    top: float
    right: float
    bottom: float
    width: float
    height: float
    center_x: float
    center_y: float


def _load_surface_metric_contract() -> dict[str, Any]:
    with _SURFACE_METRIC_CONTRACT_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise TypeError("Graph node surface metric contract must decode to a mapping.")
    return data


def _contract_mapping(source: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = source.get(key, {})
    return dict(value) if isinstance(value, Mapping) else {}


def _contract_number(source: Mapping[str, Any], key: str) -> float:
    value = source.get(key)
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    raise KeyError(f"Missing numeric contract field {key!r}.")


def _contract_bool(source: Mapping[str, Any], key: str, default: bool = False) -> bool:
    value = source.get(key, default)
    return bool(value)


def _build_flowchart_variant_layouts(
    variants: Mapping[str, Any],
) -> dict[str, _FlowchartVariantLayout]:
    layouts: dict[str, _FlowchartVariantLayout] = {}
    for name, payload in variants.items():
        if not isinstance(payload, Mapping):
            continue
        layouts[str(name)] = _FlowchartVariantLayout(
            default_width=_contract_number(payload, "default_width"),
            min_width=_contract_number(payload, "min_width"),
            min_height=_contract_number(payload, "min_height"),
            title_top=_contract_number(payload, "title_top"),
            title_left_margin=_contract_number(payload, "title_left_margin"),
            title_right_margin=_contract_number(payload, "title_right_margin"),
            body_left_margin=_contract_number(payload, "body_left_margin"),
            body_right_margin=_contract_number(payload, "body_right_margin"),
            body_bottom_margin=_contract_number(payload, "body_bottom_margin"),
            square=_contract_bool(payload, "square"),
        )
    return layouts


def _build_passive_panel_layouts(
    variants: Mapping[str, Any],
) -> dict[str, _PassivePanelLayout]:
    layouts: dict[str, _PassivePanelLayout] = {}
    for name, payload in variants.items():
        if not isinstance(payload, Mapping):
            continue
        layouts[str(name)] = _PassivePanelLayout(
            default_width=_contract_number(payload, "default_width"),
            default_height=_contract_number(payload, "default_height"),
            min_width=_contract_number(payload, "min_width"),
            min_height=_contract_number(payload, "min_height"),
            title_top=_contract_number(payload, "title_top"),
            title_height=_contract_number(payload, "title_height"),
            title_left_margin=_contract_number(payload, "title_left_margin"),
            title_right_margin=_contract_number(payload, "title_right_margin"),
            body_top=_contract_number(payload, "body_top"),
            body_height=_contract_number(payload, "body_height"),
            body_left_margin=_contract_number(payload, "body_left_margin"),
            body_right_margin=_contract_number(payload, "body_right_margin"),
            body_bottom_margin=_contract_number(payload, "body_bottom_margin"),
            title_centered=_contract_bool(payload, "title_centered"),
        )
    return layouts


def _build_media_panel_layouts(
    variants: Mapping[str, Any],
) -> dict[str, _MediaPanelLayout]:
    layouts: dict[str, _MediaPanelLayout] = {}
    for name, payload in variants.items():
        if not isinstance(payload, Mapping):
            continue
        layouts[str(name)] = _MediaPanelLayout(
            default_width=_contract_number(payload, "default_width"),
            default_height=_contract_number(payload, "default_height"),
            min_width=_contract_number(payload, "min_width"),
            min_height=_contract_number(payload, "min_height"),
            title_top=_contract_number(payload, "title_top"),
            title_height=_contract_number(payload, "title_height"),
            title_left_margin=_contract_number(payload, "title_left_margin"),
            title_right_margin=_contract_number(payload, "title_right_margin"),
            body_top=_contract_number(payload, "body_top"),
            min_body_height=_contract_number(payload, "min_body_height"),
            body_left_margin=_contract_number(payload, "body_left_margin"),
            body_right_margin=_contract_number(payload, "body_right_margin"),
            body_bottom_margin=_contract_number(payload, "body_bottom_margin"),
            title_centered=_contract_bool(payload, "title_centered"),
        )
    return layouts


SURFACE_METRIC_CONTRACT = _load_surface_metric_contract()
_INLINE_CONTRACT = _contract_mapping(SURFACE_METRIC_CONTRACT, "inline")
_STANDARD_CONTRACT = _contract_mapping(SURFACE_METRIC_CONTRACT, "standard")
_PASSIVE_CONTRACT = _contract_mapping(SURFACE_METRIC_CONTRACT, "passive")
_FLOWCHART_CONTRACT = _contract_mapping(SURFACE_METRIC_CONTRACT, "flowchart")
_PLANNING_CONTRACT = _contract_mapping(SURFACE_METRIC_CONTRACT, "planning")
_ANNOTATION_CONTRACT = _contract_mapping(SURFACE_METRIC_CONTRACT, "annotation")
_MEDIA_CONTRACT = _contract_mapping(SURFACE_METRIC_CONTRACT, "media")

STANDARD_DEFAULT_WIDTH = _contract_number(_STANDARD_CONTRACT, "default_width")
STANDARD_MIN_WIDTH = _contract_number(_STANDARD_CONTRACT, "min_width")
STANDARD_MIN_HEIGHT = _contract_number(_STANDARD_CONTRACT, "min_height")
STANDARD_COLLAPSED_WIDTH = _contract_number(_STANDARD_CONTRACT, "collapsed_width")
STANDARD_COLLAPSED_HEIGHT = _contract_number(_STANDARD_CONTRACT, "collapsed_height")
STANDARD_HEADER_HEIGHT = _contract_number(_STANDARD_CONTRACT, "header_height")
STANDARD_HEADER_TOP_MARGIN = _contract_number(_STANDARD_CONTRACT, "header_top_margin")
STANDARD_BODY_TOP = _contract_number(_STANDARD_CONTRACT, "body_top")
STANDARD_PORT_HEIGHT = _contract_number(_STANDARD_CONTRACT, "port_height")
STANDARD_INLINE_ROW_HEIGHT = _contract_number(_INLINE_CONTRACT, "row_height")
STANDARD_INLINE_TEXTAREA_ROW_HEIGHT = _contract_number(_INLINE_CONTRACT, "textarea_row_height")
STANDARD_INLINE_ROW_SPACING = _contract_number(_INLINE_CONTRACT, "row_spacing")
STANDARD_INLINE_SECTION_PADDING = _contract_number(_INLINE_CONTRACT, "section_padding")
STANDARD_PORT_CENTER_OFFSET = _contract_number(_STANDARD_CONTRACT, "port_center_offset")
STANDARD_PORT_SIDE_MARGIN = _contract_number(_STANDARD_CONTRACT, "port_side_margin")
STANDARD_PORT_DOT_RADIUS = _contract_number(_STANDARD_CONTRACT, "port_dot_radius")
STANDARD_RESIZE_HANDLE_SIZE = _contract_number(_STANDARD_CONTRACT, "resize_handle_size")
STANDARD_BOTTOM_PADDING = _contract_number(_STANDARD_CONTRACT, "bottom_padding")
STANDARD_TITLE_LEFT_MARGIN = _contract_number(_STANDARD_CONTRACT, "title_left_margin")
STANDARD_TITLE_RIGHT_MARGIN = _contract_number(_STANDARD_CONTRACT, "title_right_margin")
STANDARD_BODY_LEFT_MARGIN = _contract_number(_STANDARD_CONTRACT, "body_left_margin")
STANDARD_BODY_RIGHT_MARGIN = _contract_number(_STANDARD_CONTRACT, "body_right_margin")
STANDARD_SHOW_HEADER_BACKGROUND = _contract_bool(_STANDARD_CONTRACT, "show_header_background", True)
STANDARD_SHOW_ACCENT_BAR = _contract_bool(_STANDARD_CONTRACT, "show_accent_bar", True)
STANDARD_USE_HOST_CHROME = _contract_bool(_STANDARD_CONTRACT, "use_host_chrome", True)

FLOWCHART_COLLAPSED_WIDTH = _contract_number(_FLOWCHART_CONTRACT, "collapsed_width")
FLOWCHART_COLLAPSED_HEIGHT = _contract_number(_FLOWCHART_CONTRACT, "collapsed_height")
FLOWCHART_TITLE_HEIGHT = _contract_number(_FLOWCHART_CONTRACT, "title_height")
FLOWCHART_PORT_HEIGHT = _contract_number(_FLOWCHART_CONTRACT, "port_height")
FLOWCHART_PORT_CENTER_OFFSET = _contract_number(_FLOWCHART_CONTRACT, "port_center_offset")
FLOWCHART_PORT_DOT_RADIUS = _contract_number(_FLOWCHART_CONTRACT, "port_dot_radius")
FLOWCHART_RESIZE_HANDLE_SIZE = _contract_number(_FLOWCHART_CONTRACT, "resize_handle_size")
FLOWCHART_INLINE_GAP = _contract_number(_FLOWCHART_CONTRACT, "inline_gap")
FLOWCHART_PORT_SECTION_TOP = _contract_number(_FLOWCHART_CONTRACT, "port_section_top")

PASSIVE_SURFACE_RESIZE_HANDLE_SIZE = _contract_number(_PASSIVE_CONTRACT, "resize_handle_size")
PASSIVE_PORT_SIDE_MARGIN = _contract_number(_PASSIVE_CONTRACT, "port_side_margin")
PASSIVE_PORT_DOT_RADIUS = _contract_number(_PASSIVE_CONTRACT, "port_dot_radius")
MEDIA_CAPTION_SPACING = _contract_number(_MEDIA_CONTRACT, "caption_spacing")
MEDIA_CAPTION_MAX_LINES = int(_contract_number(_MEDIA_CONTRACT, "caption_max_lines"))
MEDIA_CAPTION_LINE_HEIGHT_FACTOR = _contract_number(_MEDIA_CONTRACT, "caption_line_height_factor")
MEDIA_CAPTION_CHAR_WIDTH_FACTOR = _contract_number(_MEDIA_CONTRACT, "caption_char_width_factor")

_FLOWCHART_VARIANT_LAYOUTS = _build_flowchart_variant_layouts(
    _contract_mapping(_FLOWCHART_CONTRACT, "variants")
)
_PLANNING_VARIANT_LAYOUTS = _build_passive_panel_layouts(
    _contract_mapping(_PLANNING_CONTRACT, "variants")
)
_ANNOTATION_VARIANT_LAYOUTS = _build_passive_panel_layouts(
    _contract_mapping(_ANNOTATION_CONTRACT, "variants")
)
_MEDIA_VARIANT_LAYOUTS = _build_media_panel_layouts(
    _contract_mapping(_MEDIA_CONTRACT, "variants")
)


def standard_inline_body_height(spec: NodeTypeSpec) -> float:
    inline_specs = inline_property_specs(spec)
    if len(inline_specs) <= 0:
        return 0.0
    row_height = 0.0
    for property_spec in inline_specs:
        editor = str(property_spec.inline_editor or "").strip().lower()
        row_height += (
            STANDARD_INLINE_TEXTAREA_ROW_HEIGHT
            if editor == "textarea"
            else STANDARD_INLINE_ROW_HEIGHT
        )
    return (
        STANDARD_INLINE_SECTION_PADDING
        + row_height
        + max(0, len(inline_specs) - 1) * STANDARD_INLINE_ROW_SPACING
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


def _flowchart_bounds(width: float, height: float) -> _FlowchartBounds:
    if width <= 0.0 or height <= 0.0:
        return _FlowchartBounds(
            left=0.0,
            top=0.0,
            right=max(0.0, width),
            bottom=max(0.0, height),
            width=max(1.0, width),
            height=max(1.0, height),
            center_x=max(0.0, width) * 0.5,
            center_y=max(0.0, height) * 0.5,
        )

    inset = _FLOWCHART_OUTLINE_INSET
    left = inset
    top = inset
    right = max(left + 1.0, width - inset)
    bottom = max(top + 1.0, height - inset)
    width_value = max(1.0, right - left)
    height_value = max(1.0, bottom - top)
    return _FlowchartBounds(
        left=left,
        top=top,
        right=right,
        bottom=bottom,
        width=width_value,
        height=height_value,
        center_x=(left + right) * 0.5,
        center_y=(top + bottom) * 0.5,
    )


def _cubic_bezier_coordinate(p0: float, p1: float, p2: float, p3: float, t: float) -> float:
    omt = 1.0 - t
    return (
        (omt * omt * omt * p0)
        + (3.0 * omt * omt * t * p1)
        + (3.0 * omt * t * t * p2)
        + (t * t * t * p3)
    )


def _solve_monotonic_bezier_t_for_coordinate(
    target: float,
    p0: float,
    p1: float,
    p2: float,
    p3: float,
) -> float:
    increasing = p3 >= p0
    low = 0.0
    high = 1.0
    for _ in range(32):
        mid = (low + high) * 0.5
        value = _cubic_bezier_coordinate(p0, p1, p2, p3, mid)
        if (value < target) == increasing:
            low = mid
        else:
            high = mid
    return (low + high) * 0.5


def _document_bottom_anchor(bounds: _FlowchartBounds) -> tuple[float, float]:
    wave_depth = min(bounds.height * 0.11, 11.5)
    wave_base = bounds.bottom - wave_depth * 0.58
    wave_crest = bounds.bottom - wave_depth * 1.08
    wave_trough = bounds.bottom - wave_depth * 0.12
    middle_x = bounds.left + bounds.width * 0.52
    target_x = bounds.center_x

    if target_x >= middle_x:
        p0x = bounds.right
        p1x = bounds.right - bounds.width * 0.17
        p2x = bounds.left + bounds.width * 0.7
        p3x = middle_x
        p0y = wave_base
        p1y = wave_trough
        p2y = wave_trough
        p3y = wave_base - wave_depth * 0.34
    else:
        p0x = middle_x
        p1x = bounds.left + bounds.width * 0.33
        p2x = bounds.left + bounds.width * 0.14
        p3x = bounds.left
        p0y = wave_base - wave_depth * 0.34
        p1y = wave_crest
        p2y = wave_crest
        p3y = wave_base

    t = _solve_monotonic_bezier_t_for_coordinate(target_x, p0x, p1x, p2x, p3x)
    return target_x, _cubic_bezier_coordinate(p0y, p1y, p2y, p3y, t)


def flowchart_anchor_local_point(
    variant: str,
    width: float,
    height: float,
    side: str,
) -> tuple[float, float]:
    normalized_variant = normalize_flowchart_variant(variant)
    normalized_side = str(side or "").strip().lower()
    bounds = _flowchart_bounds(width, height)
    if normalized_side not in _CARDINAL_SIDES:
        return bounds.center_x, bounds.center_y

    if normalized_variant in {"start", "end", "process", "predefined_process"}:
        if normalized_side == "top":
            return bounds.center_x, bounds.top
        if normalized_side == "right":
            return bounds.right, bounds.center_y
        if normalized_side == "bottom":
            return bounds.center_x, bounds.bottom
        return bounds.left, bounds.center_y

    if normalized_variant == "decision":
        if normalized_side == "top":
            return bounds.center_x, bounds.top
        if normalized_side == "right":
            return bounds.right, bounds.center_y
        if normalized_side == "bottom":
            return bounds.center_x, bounds.bottom
        return bounds.left, bounds.center_y

    if normalized_variant == "connector":
        if normalized_side == "top":
            return bounds.center_x, bounds.top
        if normalized_side == "right":
            return bounds.right, bounds.center_y
        if normalized_side == "bottom":
            return bounds.center_x, bounds.bottom
        return bounds.left, bounds.center_y

    if normalized_variant == "input_output":
        slant = min(bounds.width * 0.13, bounds.height * 0.26)
        if normalized_side == "top":
            return bounds.center_x, bounds.top
        if normalized_side == "right":
            return bounds.right - (slant * 0.5), bounds.center_y
        if normalized_side == "bottom":
            return bounds.center_x, bounds.bottom
        return bounds.left + (slant * 0.5), bounds.center_y

    if normalized_variant == "database":
        cap = min(bounds.height * 0.13, 15.0)
        if normalized_side == "top":
            return bounds.center_x, bounds.top
        if normalized_side == "right":
            return bounds.right, bounds.center_y
        if normalized_side == "bottom":
            return bounds.center_x, bounds.bottom
        return bounds.left, bounds.center_y

    if normalized_variant == "document":
        if normalized_side == "top":
            return bounds.center_x, bounds.top
        if normalized_side == "right":
            return bounds.right, bounds.center_y
        if normalized_side == "bottom":
            return _document_bottom_anchor(bounds)
        return bounds.left, bounds.center_y

    if normalized_side == "top":
        return bounds.center_x, bounds.top
    if normalized_side == "right":
        return bounds.right, bounds.center_y
    if normalized_side == "bottom":
        return bounds.center_x, bounds.bottom
    return bounds.left, bounds.center_y


def flowchart_anchor_normal(side: str) -> tuple[float, float]:
    normalized_side = str(side or "").strip().lower()
    if normalized_side == "top":
        return 0.0, -1.0
    if normalized_side == "right":
        return 1.0, 0.0
    if normalized_side == "bottom":
        return 0.0, 1.0
    if normalized_side == "left":
        return -1.0, 0.0
    return 0.0, 0.0


def flowchart_anchor_tangent(side: str) -> tuple[float, float]:
    normalized_side = str(side or "").strip().lower()
    if normalized_side in {"top", "bottom"}:
        return 1.0, 0.0
    if normalized_side in {"left", "right"}:
        return 0.0, 1.0
    return 0.0, 0.0


def flowchart_port_side(
    node: NodeInstance,
    spec: NodeTypeSpec,
    port_key: str,
    workspace_nodes: Mapping[str, NodeInstance] | None = None,
) -> str:
    scoped_nodes = workspace_nodes or {node.node_id: node}
    port = find_port(
        node=node,
        spec=spec,
        workspace_nodes=scoped_nodes,
        port_key=port_key,
    )
    if port is not None:
        explicit_side = port_side(port)
        if explicit_side:
            return explicit_side
    normalized_key = str(port_key or "").strip().lower()
    return normalized_key if normalized_key in _CARDINAL_SIDES else ""


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
    *,
    variant: str,
) -> tuple[float, float]:
    default_width = float(layout.default_width)
    default_height = float(layout.default_height)
    source_path = str(node.properties.get("source_path", "") or "")
    if variant == "pdf_panel":
        media_dimensions = local_pdf_page_dimensions(source_path, node.properties.get("page_number"))
    else:
        media_dimensions = local_image_dimensions(source_path)
    if media_dimensions is None:
        return default_width, default_height
    media_width, media_height = media_dimensions
    if media_width <= 0 or media_height <= 0:
        return default_width, default_height

    preview_width = max(1.0, default_width - layout.body_left_margin - layout.body_right_margin)
    preview_height = preview_width * (float(media_height) / float(media_width))
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
        title_left_margin=STANDARD_TITLE_LEFT_MARGIN,
        title_right_margin=STANDARD_TITLE_RIGHT_MARGIN,
        title_centered=False,
        body_left_margin=STANDARD_BODY_LEFT_MARGIN,
        body_right_margin=STANDARD_BODY_RIGHT_MARGIN,
        body_bottom_margin=STANDARD_BOTTOM_PADDING,
        show_header_background=STANDARD_SHOW_HEADER_BACKGROUND,
        show_accent_bar=STANDARD_SHOW_ACCENT_BAR,
        use_host_chrome=STANDARD_USE_HOST_CHROME,
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
        port_side_margin=PASSIVE_PORT_SIDE_MARGIN,
        port_dot_radius=PASSIVE_PORT_DOT_RADIUS,
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
    variant = normalize_media_variant(spec.surface_variant)
    layout = _MEDIA_VARIANT_LAYOUTS[variant]
    default_width, default_height = _media_default_dimensions(node, layout, variant=variant)
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
        port_side_margin=PASSIVE_PORT_SIDE_MARGIN,
        port_dot_radius=PASSIVE_PORT_DOT_RADIUS,
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
        side = flowchart_port_side(node, spec, port_key, scoped_nodes)
        if side:
            return flowchart_anchor_local_point(
                spec.surface_variant,
                width_value,
                height_value,
                side,
            )
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
