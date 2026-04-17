from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ea_node_editor.graph.effective_ports import visible_ports
from ea_node_editor.graph.model import NodeInstance
from ea_node_editor.nodes.types import NodeTypeSpec


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
    standard_title_full_width: float = 0.0
    standard_left_label_width: float = 0.0
    standard_right_label_width: float = 0.0
    standard_port_gutter: float = 0.0
    standard_center_gap: float = 0.0
    standard_port_label_min_width: float = 0.0

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
            "standard_title_full_width": float(self.standard_title_full_width),
            "standard_left_label_width": float(self.standard_left_label_width),
            "standard_right_label_width": float(self.standard_right_label_width),
            "standard_port_gutter": float(self.standard_port_gutter),
            "standard_center_gap": float(self.standard_center_gap),
            "standard_port_label_min_width": float(self.standard_port_label_min_width),
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
    show_header_background: bool = False
    show_accent_bar: bool = False
    use_host_chrome: bool = True


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


@dataclass(frozen=True, slots=True)
class _StandardWidthContract:
    title_full_width: float
    left_label_width: float
    right_label_width: float
    port_gutter: float
    center_gap: float
    port_label_min_width: float

    @property
    def min_width_with_labels(self) -> float:
        return max(self.title_full_width, self.port_label_min_width)

    @property
    def min_width_without_labels(self) -> float:
        return self.title_full_width


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


SURFACE_METRIC_CONTRACT_PATH = (
    Path(__file__).resolve().parents[1] / "components" / "graph" / "GraphNodeSurfaceMetricContract.json"
)
CARDINAL_SIDES = frozenset({"top", "right", "bottom", "left"})
FLOWCHART_OUTLINE_INSET = 0.5


def _load_surface_metric_contract() -> dict[str, Any]:
    with SURFACE_METRIC_CONTRACT_PATH.open("r", encoding="utf-8") as handle:
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
            show_header_background=_contract_bool(payload, "show_header_background"),
            show_accent_bar=_contract_bool(payload, "show_accent_bar"),
            use_host_chrome=_contract_bool(payload, "use_host_chrome", True),
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
INLINE_CONTRACT = _contract_mapping(SURFACE_METRIC_CONTRACT, "inline")
STANDARD_CONTRACT = _contract_mapping(SURFACE_METRIC_CONTRACT, "standard")
PASSIVE_CONTRACT = _contract_mapping(SURFACE_METRIC_CONTRACT, "passive")
FLOWCHART_CONTRACT = _contract_mapping(SURFACE_METRIC_CONTRACT, "flowchart")
PLANNING_CONTRACT = _contract_mapping(SURFACE_METRIC_CONTRACT, "planning")
ANNOTATION_CONTRACT = _contract_mapping(SURFACE_METRIC_CONTRACT, "annotation")
COMMENT_BACKDROP_CONTRACT = _contract_mapping(SURFACE_METRIC_CONTRACT, "comment_backdrop")
MEDIA_CONTRACT = _contract_mapping(SURFACE_METRIC_CONTRACT, "media")

STANDARD_DEFAULT_WIDTH = _contract_number(STANDARD_CONTRACT, "default_width")
STANDARD_MIN_WIDTH = _contract_number(STANDARD_CONTRACT, "min_width")
STANDARD_MIN_HEIGHT = _contract_number(STANDARD_CONTRACT, "min_height")
STANDARD_COLLAPSED_WIDTH = _contract_number(STANDARD_CONTRACT, "collapsed_width")
STANDARD_COLLAPSED_HEIGHT = _contract_number(STANDARD_CONTRACT, "collapsed_height")
STANDARD_HEADER_HEIGHT = _contract_number(STANDARD_CONTRACT, "header_height")
STANDARD_HEADER_TOP_MARGIN = _contract_number(STANDARD_CONTRACT, "header_top_margin")
STANDARD_BODY_TOP = _contract_number(STANDARD_CONTRACT, "body_top")
STANDARD_PORT_HEIGHT = _contract_number(STANDARD_CONTRACT, "port_height")
STANDARD_INLINE_ROW_HEIGHT = _contract_number(INLINE_CONTRACT, "row_height")
STANDARD_INLINE_TEXTAREA_ROW_HEIGHT = _contract_number(INLINE_CONTRACT, "textarea_row_height")
STANDARD_INLINE_ROW_SPACING = _contract_number(INLINE_CONTRACT, "row_spacing")
STANDARD_INLINE_SECTION_PADDING = _contract_number(INLINE_CONTRACT, "section_padding")
STANDARD_PORT_CENTER_OFFSET = _contract_number(STANDARD_CONTRACT, "port_center_offset")
STANDARD_PORT_SIDE_MARGIN = _contract_number(STANDARD_CONTRACT, "port_side_margin")
STANDARD_PORT_DOT_RADIUS = _contract_number(STANDARD_CONTRACT, "port_dot_radius")
STANDARD_RESIZE_HANDLE_SIZE = _contract_number(STANDARD_CONTRACT, "resize_handle_size")
STANDARD_BOTTOM_PADDING = _contract_number(STANDARD_CONTRACT, "bottom_padding")
STANDARD_TITLE_LEFT_MARGIN = _contract_number(STANDARD_CONTRACT, "title_left_margin")
STANDARD_TITLE_RIGHT_MARGIN = _contract_number(STANDARD_CONTRACT, "title_right_margin")
STANDARD_BODY_LEFT_MARGIN = _contract_number(STANDARD_CONTRACT, "body_left_margin")
STANDARD_BODY_RIGHT_MARGIN = _contract_number(STANDARD_CONTRACT, "body_right_margin")
STANDARD_SHOW_HEADER_BACKGROUND = _contract_bool(STANDARD_CONTRACT, "show_header_background", True)
STANDARD_SHOW_ACCENT_BAR = _contract_bool(STANDARD_CONTRACT, "show_accent_bar", True)
STANDARD_USE_HOST_CHROME = _contract_bool(STANDARD_CONTRACT, "use_host_chrome", True)
STANDARD_PORT_GUTTER = _contract_number(STANDARD_CONTRACT, "standard_port_gutter")
STANDARD_CENTER_GAP = _contract_number(STANDARD_CONTRACT, "standard_center_gap")

FLOWCHART_COLLAPSED_WIDTH = _contract_number(FLOWCHART_CONTRACT, "collapsed_width")
FLOWCHART_COLLAPSED_HEIGHT = _contract_number(FLOWCHART_CONTRACT, "collapsed_height")
FLOWCHART_TITLE_HEIGHT = _contract_number(FLOWCHART_CONTRACT, "title_height")
FLOWCHART_PORT_HEIGHT = _contract_number(FLOWCHART_CONTRACT, "port_height")
FLOWCHART_PORT_CENTER_OFFSET = _contract_number(FLOWCHART_CONTRACT, "port_center_offset")
FLOWCHART_PORT_DOT_RADIUS = _contract_number(FLOWCHART_CONTRACT, "port_dot_radius")
FLOWCHART_RESIZE_HANDLE_SIZE = _contract_number(FLOWCHART_CONTRACT, "resize_handle_size")
FLOWCHART_INLINE_GAP = _contract_number(FLOWCHART_CONTRACT, "inline_gap")
FLOWCHART_PORT_SECTION_TOP = _contract_number(FLOWCHART_CONTRACT, "port_section_top")

PASSIVE_SURFACE_RESIZE_HANDLE_SIZE = _contract_number(PASSIVE_CONTRACT, "resize_handle_size")
PASSIVE_PORT_SIDE_MARGIN = _contract_number(PASSIVE_CONTRACT, "port_side_margin")
PASSIVE_PORT_DOT_RADIUS = _contract_number(PASSIVE_CONTRACT, "port_dot_radius")
MEDIA_CAPTION_SPACING = _contract_number(MEDIA_CONTRACT, "caption_spacing")
MEDIA_CAPTION_MAX_LINES = int(_contract_number(MEDIA_CONTRACT, "caption_max_lines"))
MEDIA_CAPTION_LINE_HEIGHT_FACTOR = _contract_number(MEDIA_CONTRACT, "caption_line_height_factor")
MEDIA_CAPTION_CHAR_WIDTH_FACTOR = _contract_number(MEDIA_CONTRACT, "caption_char_width_factor")

FLOWCHART_VARIANT_LAYOUTS = _build_flowchart_variant_layouts(
    _contract_mapping(FLOWCHART_CONTRACT, "variants")
)
PLANNING_VARIANT_LAYOUTS = _build_passive_panel_layouts(
    _contract_mapping(PLANNING_CONTRACT, "variants")
)
ANNOTATION_VARIANT_LAYOUTS = _build_passive_panel_layouts(
    _contract_mapping(ANNOTATION_CONTRACT, "variants")
)
COMMENT_BACKDROP_VARIANT_LAYOUTS = _build_passive_panel_layouts(
    _contract_mapping(COMMENT_BACKDROP_CONTRACT, "variants")
)
MEDIA_VARIANT_LAYOUTS = _build_media_panel_layouts(
    _contract_mapping(MEDIA_CONTRACT, "variants")
)

VIEWER_DEFAULT_WIDTH = 340.0
VIEWER_MIN_WIDTH = 320.0
VIEWER_BODY_TOP = STANDARD_BODY_TOP
VIEWER_LEGACY_DEFAULT_BODY_HEIGHTS = (186.0,)
VIEWER_DEFAULT_BODY_HEIGHT = 176.0
VIEWER_MIN_BODY_HEIGHT = 148.0
VIEWER_BODY_LEFT_MARGIN = 14.0
VIEWER_BODY_RIGHT_MARGIN = 14.0
VIEWER_BODY_BOTTOM_PADDING = 12.0
VIEWER_TITLE_RIGHT_MARGIN = 42.0


def _safe_number(value: Any, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    if not math.isfinite(number):
        return fallback
    return number


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
