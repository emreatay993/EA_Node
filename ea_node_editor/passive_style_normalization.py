from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from secrets import token_hex
from typing import Any, Literal

PresetKind = Literal["node", "edge"]

_FINAL_HEX_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?$")
_NODE_PRESET_ID_PATTERN = re.compile(r"^node_preset_[0-9a-f]{8}$")
_EDGE_PRESET_ID_PATTERN = re.compile(r"^edge_preset_[0-9a-f]{8}$")

PASSIVE_NODE_STYLE_FONT_WEIGHTS = ("normal", "bold")
FLOW_EDGE_STYLE_PATTERNS = ("solid", "dashed", "dotted")
FLOW_EDGE_ARROW_HEADS = ("filled", "open", "none")


def normalize_passive_style_presets(value: Any) -> dict[str, list[dict[str, Any]]]:
    source = value if isinstance(value, Mapping) else {}
    return {
        "node_presets": normalize_style_preset_entries(source.get("node_presets"), kind="node"),
        "edge_presets": normalize_style_preset_entries(source.get("edge_presets"), kind="edge"),
    }


def normalize_style_preset_entries(value: Any, *, kind: PresetKind) -> list[dict[str, Any]]:
    style_normalizer = _style_normalizer(kind)
    normalized_entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for index, entry in enumerate(_as_sequence(value), start=1):
        if not isinstance(entry, Mapping):
            continue
        preset_id = _normalized_user_preset_id(
            entry.get("preset_id"),
            kind=kind,
            used_ids=seen_ids,
        )
        seen_ids.add(preset_id)
        normalized_entries.append(
            {
                "preset_id": preset_id,
                "name": _normalized_preset_name(entry.get("name"), kind=kind, index=index),
                "style": style_normalizer(entry.get("style")),
            }
        )
    return normalized_entries


def normalize_passive_node_style_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, Any] = {}

    for key in ("fill_color", "border_color", "text_color", "accent_color", "header_color"):
        color_value = _normalized_hex_color(value.get(key))
        if color_value:
            normalized[key] = color_value

    border_width = _normalized_positive_number(value.get("border_width"))
    if border_width is not None:
        normalized["border_width"] = border_width

    corner_radius = _normalized_nonnegative_number(value.get("corner_radius"))
    if corner_radius is not None:
        normalized["corner_radius"] = corner_radius

    font_size = _normalized_positive_int(value.get("font_size"))
    if font_size is not None:
        normalized["font_size"] = font_size

    font_weight = str(value.get("font_weight", "")).strip().lower()
    if font_weight in PASSIVE_NODE_STYLE_FONT_WEIGHTS:
        normalized["font_weight"] = font_weight

    return normalized


def normalize_flow_edge_style_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, Any] = {}

    for key in ("stroke_color", "label_text_color", "label_background_color"):
        color_value = _normalized_hex_color(value.get(key))
        if color_value:
            normalized[key] = color_value

    stroke_width = _normalized_positive_number(value.get("stroke_width"))
    if stroke_width is not None:
        normalized["stroke_width"] = stroke_width

    stroke_pattern = str(value.get("stroke_pattern", "")).strip().lower()
    if stroke_pattern in FLOW_EDGE_STYLE_PATTERNS:
        normalized["stroke_pattern"] = stroke_pattern

    arrow_head = str(value.get("arrow_head", "")).strip().lower()
    if arrow_head in FLOW_EDGE_ARROW_HEADS:
        normalized["arrow_head"] = arrow_head

    return normalized


def _normalized_user_preset_id(value: Any, *, kind: PresetKind, used_ids: set[str]) -> str:
    normalized = str(value or "").strip().lower()
    pattern = _NODE_PRESET_ID_PATTERN if kind == "node" else _EDGE_PRESET_ID_PATTERN
    if normalized and pattern.match(normalized) and normalized not in used_ids:
        return normalized
    return _new_user_preset_id(kind, used_ids=used_ids)


def _new_user_preset_id(kind: PresetKind, *, used_ids: set[str]) -> str:
    prefix = "node_preset_" if kind == "node" else "edge_preset_"
    while True:
        candidate = f"{prefix}{token_hex(4)}"
        if candidate not in used_ids:
            return candidate


def _normalized_preset_name(value: Any, *, kind: PresetKind, index: int) -> str:
    normalized = str(value or "").strip()
    if normalized:
        return normalized
    return f"{kind.title()} Preset {index}"


def _style_normalizer(kind: PresetKind):
    return normalize_passive_node_style_payload if kind == "node" else normalize_flow_edge_style_payload


def _as_sequence(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)
    return []


def _normalized_hex_color(value: Any) -> str:
    normalized = str(value or "").strip()
    if not _FINAL_HEX_COLOR.match(normalized):
        return ""
    return normalized


def _normalized_positive_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric) or numeric <= 0.0:
        return None
    return numeric


def _normalized_nonnegative_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric) or numeric < 0.0:
        return None
    return numeric


def _normalized_positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return None
    if numeric <= 0:
        return None
    return numeric


__all__ = [
    "FLOW_EDGE_ARROW_HEADS",
    "FLOW_EDGE_STYLE_PATTERNS",
    "PASSIVE_NODE_STYLE_FONT_WEIGHTS",
    "PresetKind",
    "normalize_flow_edge_style_payload",
    "normalize_passive_node_style_payload",
    "normalize_passive_style_presets",
    "normalize_style_preset_entries",
]
