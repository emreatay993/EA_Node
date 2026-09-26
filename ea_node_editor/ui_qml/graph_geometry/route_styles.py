from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from ea_node_editor.graph.records import EdgeInstance
from ea_node_editor.passive_style_normalization import (
    FLOW_EDGE_STYLE_PATTERNS,
    normalize_flow_edge_arrow_kind,
    normalize_flow_edge_label_orientation,
    normalize_flow_edge_label_position,
)

EDGE_PAIR_LANE_SPACING = 24.0
EDGE_PORT_FAN_SPACING = 10.0
EDGE_PATH_MODES = {"auto", "pipe", "bezier"}


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


def _normalized_style_string(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def normalize_edge_path_mode(value: Any) -> str:
    normalized = _normalized_style_string(value).lower()
    return normalized if normalized in EDGE_PATH_MODES else "auto"


def _normalized_positive_style_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric) or numeric <= 0.0:
        return None
    return numeric


def normalize_flow_edge_visual_style_payload(visual_style: Any) -> dict[str, Any]:
    if not isinstance(visual_style, Mapping):
        return {}
    normalized: dict[str, Any] = {}

    stroke_color = _normalized_style_string(visual_style.get("stroke_color") or visual_style.get("color"))
    if stroke_color:
        normalized["stroke_color"] = stroke_color

    stroke_width = _normalized_positive_style_number(visual_style.get("stroke_width"))
    if stroke_width is not None:
        normalized["stroke_width"] = stroke_width

    stroke_pattern = _normalized_style_string(visual_style.get("stroke_pattern") or visual_style.get("stroke")).lower()
    if stroke_pattern in FLOW_EDGE_STYLE_PATTERNS:
        normalized["stroke_pattern"] = stroke_pattern

    arrow_head = normalize_flow_edge_arrow_kind(visual_style.get("arrow_head"))
    if not arrow_head:
        arrow_payload = visual_style.get("arrow")
        if isinstance(arrow_payload, Mapping):
            arrow_head = normalize_flow_edge_arrow_kind(arrow_payload.get("kind"))
    if arrow_head:
        normalized["arrow_head"] = arrow_head

    arrow_tail = normalize_flow_edge_arrow_kind(visual_style.get("arrow_tail"))
    if arrow_tail:
        normalized["arrow_tail"] = arrow_tail

    path_mode = normalize_edge_path_mode(visual_style.get("path_mode"))
    if path_mode != "auto":
        normalized["path_mode"] = path_mode

    label_position = normalize_flow_edge_label_position(visual_style.get("label_position"))
    if label_position is not None:
        normalized["label_position"] = label_position

    label_orientation = normalize_flow_edge_label_orientation(visual_style.get("label_orientation"))
    if label_orientation != "horizontal":
        normalized["label_orientation"] = label_orientation

    label_text_color = _normalized_style_string(visual_style.get("label_text_color"))
    if label_text_color:
        normalized["label_text_color"] = label_text_color

    label_background_color = _normalized_style_string(visual_style.get("label_background_color"))
    if label_background_color:
        normalized["label_background_color"] = label_background_color

    return normalized
