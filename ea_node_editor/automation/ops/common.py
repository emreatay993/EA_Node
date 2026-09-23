# Purpose: Shared schema fragments (node/edge summaries, style objects, positions) reused across automation op specs.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_catalog.py
from __future__ import annotations

from typing import Any

from ea_node_editor.automation.op_model import (
    any_schema,
    array_schema,
    boolean_schema,
    number_schema,
    object_schema,
    string_schema,
)

NODE_ID = string_schema("Node id (node_...)", min_length=1)
EDGE_ID = string_schema("Edge id (edge_...)", min_length=1)
WORKSPACE_ID = string_schema("Workspace id (ws_...)", min_length=1)
VIEW_ID = string_schema("View id (view_...)", min_length=1)
TYPE_ID = string_schema("Node type id, e.g. passive.flowchart.process", min_length=1)
PORT_KEY = string_schema("Port key; passive flow nodes use top|right|bottom|left", min_length=1)
COORD = number_schema("Scene coordinate in canvas units")
SIZE = number_schema("Size in canvas units", minimum=1)
TITLE = string_schema("Node title shown in the header")

# Keys mirror passive_style_normalization.normalize_passive_node_style_payload; the handler also
# accepts the alias fill_color_end (-> gradient_color). catalog.style_schema returns the same list.
NODE_STYLE = object_schema(
    {
        "fill_color": string_schema("#RRGGBB or #RRGGBBAA"),
        "gradient_enabled": boolean_schema("Requires gradient_color"),
        "gradient_color": string_schema("Gradient end colour (#RRGGBB[AA]); alias fill_color_end"),
        "gradient_direction": string_schema(enum=("north", "east", "south", "west", "radial")),
        "border_color": string_schema("#RRGGBB[AA]"),
        "border_width": number_schema(minimum=0),
        "corner_radius": number_schema(minimum=0),
        "text_color": string_schema("#RRGGBB[AA]"),
        "font_size": number_schema(minimum=1, integer=True),
        "font_weight": string_schema(enum=("normal", "bold")),
    },
    additional=True,
    description="Passive node style override (persisted keys; see catalog.style_schema for enums and aliases)",
)

# Keys mirror passive_style_normalization.normalize_flow_edge_style_payload plus display_mode; the
# handler also accepts the aliases color/width/pattern/label_color/label_background.
EDGE_STYLE = object_schema(
    {
        "stroke_color": string_schema("#RRGGBB[AA]; alias color"),
        "stroke_width": number_schema(minimum=0, description="alias width"),
        "stroke_pattern": string_schema("alias pattern", enum=("solid", "dashed", "dotted")),
        "arrow_head": string_schema(enum=("filled", "open", "none")),
        "path_mode": string_schema(enum=("auto", "pipe", "bezier")),
        "display_mode": string_schema(enum=("default", "faint", "hidden")),
        "label_text_color": string_schema("#RRGGBB[AA]; alias label_color"),
        "label_background_color": string_schema("#RRGGBB[AA]; alias label_background"),
    },
    additional=True,
    description="Flow edge style override (persisted keys; see catalog.style_schema for aliases)",
)

# Keys mirror text_style.TEXT_ANNOTATION_STYLE_KEYS plus format; the handler also accepts the
# alias color (-> text_color). Ranges are clamped by the owner (font_size 6..144, opacity 0..100,
# padding 0..64, line_height 0.5..4.0, letter_spacing -10..20); 0 / sentinel values inherit.
TEXT_STYLE = object_schema(
    {
        "format": string_schema(enum=("markdown", "plain")),
        "font_family": string_schema(),
        "font_size": number_schema(minimum=0, description="0 inherits the graph label size"),
        "font_weight": string_schema(enum=("normal", "medium", "demibold", "bold", "black")),
        "italic": boolean_schema(),
        "underline": boolean_schema(),
        "strikeout": boolean_schema(),
        "text_color": string_schema("#RRGGBB[AA]; alias color"),
        "background_color": string_schema("#RRGGBB[AA]"),
        "horizontal_alignment": string_schema(enum=("left", "center", "right", "justify")),
        "vertical_alignment": string_schema(enum=("top", "middle", "bottom")),
        "wrap_mode": string_schema(enum=("word", "anywhere", "none")),
        "line_height": number_schema(minimum=0),
        "letter_spacing": number_schema(),
        "padding": number_schema(minimum=-1),
        "opacity": number_schema(minimum=-1, maximum=100),
    },
    additional=True,
    description="Rich text slot style (persisted keys; see catalog.style_schema for aliases and ranges)",
)

PORT_SUMMARY = object_schema(
    {
        "key": string_schema(),
        "direction": string_schema(),
        "kind": string_schema(),
        "data_type": string_schema(),
        "label": string_schema(),
        "side": string_schema(),
        "required": boolean_schema(),
        "exposed": boolean_schema(),
        "allow_multiple_connections": boolean_schema(),
        "connected_edge_ids": array_schema(string_schema()),
    },
    additional=True,
)

NODE_SUMMARY = object_schema(
    {
        "node_id": NODE_ID,
        "type_id": TYPE_ID,
        "title": TITLE,
        "x": COORD,
        "y": COORD,
        "width": number_schema(),
        "height": number_schema(),
        "collapsed": boolean_schema(),
        "locked": boolean_schema(),
        "parent_node_id": string_schema(description="Owning subnode shell id or empty"),
        "runtime_behavior": string_schema(),
        "surface_family": string_schema(),
        "comment_count": number_schema(integer=True),
        "link_count": number_schema(integer=True),
    },
    additional=True,
    description="Compact node summary returned by every node op",
)

EDGE_SUMMARY = object_schema(
    {
        "edge_id": EDGE_ID,
        "source_node_id": NODE_ID,
        "source_port": PORT_KEY,
        "target_node_id": NODE_ID,
        "target_port": PORT_KEY,
        "enabled": boolean_schema(),
        "label": string_schema(),
        "kind": string_schema(description="flow or data"),
    },
    additional=True,
    description="Compact edge summary returned by every edge op",
)

CHANGED_FIELDS = array_schema(string_schema(), "Names of the fields that actually changed")


def ok_result(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    fields: dict[str, Any] = {"ok": boolean_schema()}
    fields.update(extra or {})
    return object_schema(fields, additional=True)


__all__ = [
    "CHANGED_FIELDS",
    "COORD",
    "EDGE_ID",
    "EDGE_STYLE",
    "EDGE_SUMMARY",
    "NODE_ID",
    "NODE_STYLE",
    "NODE_SUMMARY",
    "PORT_KEY",
    "PORT_SUMMARY",
    "SIZE",
    "TEXT_STYLE",
    "TITLE",
    "TYPE_ID",
    "VIEW_ID",
    "WORKSPACE_ID",
    "any_schema",
    "ok_result",
]
