# Purpose: Agent-facing guidance embedded in the MCP server: instructions text, corex:// resources, and prompt templates.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_mcp_server.py
"""Guidance served by ``corex-mcp`` (Qt-free, importable without ``mcp``).

Resources:

- ``corex://guide``      -- workflow recipe, error-code cheat sheet, retry rules.
- ``corex://ops``        -- op reference rendered from ``op_catalog`` (never from docgen).
- ``corex://styles``     -- node / edge / text style keys, enums, and aliases.
- ``corex://node-types`` -- passive families with type ids, port keys, and property hints.

``server_instructions()`` is the MCP ``instructions`` string (read once per
session, so it stays short and imperative). ``prompt_text()`` renders the two
prompt templates the server lists (``build_flowchart``, ``annotate_board``).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from ea_node_editor.automation import op_catalog
from ea_node_editor.automation.errors import ERROR_CODES, RETRYABLE_CODES, default_hint
from ea_node_editor.automation.op_model import OpSpec
from ea_node_editor.automation.ops.apply import MAX_APPLY_OPS, RECOMMENDED_APPLY_OPS
from ea_node_editor.passive_style_normalization import (
    FLOW_EDGE_ARROW_HEADS,
    FLOW_EDGE_PATH_MODES,
    FLOW_EDGE_STYLE_PATTERNS,
    PASSIVE_NODE_STYLE_FONT_WEIGHTS,
    PASSIVE_NODE_STYLE_GRADIENT_DIRECTIONS,
    RETIRED_PASSIVE_NODE_STYLE_KEYS,
    _PASSIVE_NODE_STYLE_KEYS,
)
from ea_node_editor.text_style import (
    DEFAULT_TEXT_STYLE_PROPERTIES,
    TEXT_ANNOTATION_STYLE_KEYS,
    TEXT_STYLE_FONT_WEIGHTS,
    TEXT_STYLE_FORMATS,
    TEXT_STYLE_HORIZONTAL_ALIGNMENTS,
    TEXT_STYLE_VERTICAL_ALIGNMENTS,
    TEXT_STYLE_WRAP_MODES,
)

GUIDE_URI = "corex://guide"
OPS_URI = "corex://ops"
STYLES_URI = "corex://styles"
NODE_TYPES_URI = "corex://node-types"
RESOURCE_URIS: tuple[str, ...] = (GUIDE_URI, OPS_URI, STYLES_URI, NODE_TYPES_URI)
RESOURCE_MIME_TYPE = "text/markdown"

_RESOURCE_META: dict[str, tuple[str, str, str]] = {
    GUIDE_URI: ("guide", "COREX automation guide", "Workflow recipe, error-code cheat sheet, and retry rules."),
    OPS_URI: ("ops", "COREX op reference", "Every MCP tool with its wire op, params, defaults, enums, flags, and result keys."),
    STYLES_URI: ("styles", "COREX style keys", "Node, edge, and text style keys, enums, ranges, and agent-friendly aliases."),
    NODE_TYPES_URI: ("node-types", "COREX passive node types", "Passive families with type ids, port keys, and key properties."),
}

# Layout grid agents are told to plan on: default passive shapes fit inside one cell with room for edge labels.
GRID_COLUMN_WIDTH = 320
GRID_ROW_HEIGHT = 160

# Aliases the handlers accept on top of the persisted keys (mirrors handlers/catalog.py; restated here so the
# Qt-free package never imports ea_node_editor.ui).
NODE_STYLE_ALIASES: dict[str, str] = {"fill_color_end": "gradient_color"}
EDGE_STYLE_ALIASES: dict[str, str] = {
    "color": "stroke_color",
    "width": "stroke_width",
    "pattern": "stroke_pattern",
    "label_color": "label_text_color",
    "label_background": "label_background_color",
}
TEXT_STYLE_ALIASES: dict[str, str] = {"color": "text_color"}
# Node style keys the owner (normalize_passive_node_style_payload) accepts; the retired header/accent keys are dropped.
NODE_STYLE_KEYS: tuple[str, ...] = tuple(sorted(_PASSIVE_NODE_STYLE_KEYS - RETIRED_PASSIVE_NODE_STYLE_KEYS))
EDGE_STYLE_KEYS: tuple[str, ...] = (
    "stroke_color",
    "stroke_width",
    "stroke_pattern",
    "arrow_head",
    "path_mode",
    "label_text_color",
    "label_background_color",
    "display_mode",
)
EDGE_DISPLAY_MODES: tuple[str, ...] = ("default", "faint", "hidden")
TEXT_STYLE_KEYS: tuple[str, ...] = ("format", *TEXT_ANNOTATION_STYLE_KEYS)

# Passive families (type ids and property keys restated from ea_node_editor/nodes/builtins/*).
FLOWCHART_TYPE_IDS: tuple[str, ...] = tuple(
    f"passive.flowchart.{variant}"
    for variant in (
        "start",
        "end",
        "process",
        "decision",
        "document",
        "connector",
        "input_output",
        "predefined_process",
        "database",
        "card",
        "callout",
        "multi_document",
        "tick",
        "timestamp",
        "message",
        "isometric_cube",
        "cube",
        "actor",
        "star",
        "x",
    )
)
ANNOTATION_TYPE_IDS: tuple[str, ...] = (
    "passive.annotation.sticky_note",
    "passive.annotation.callout",
    "passive.annotation.section_header",
    "passive.annotation.text",
    "passive.annotation.group_backdrop",
)
MEDIA_PANEL_TYPE_ID = "media.panel"
WEB_PAGE_VIEWER_TYPE_ID = "web.page_viewer"
PATH_POINTER_TYPE_ID = "io.path_pointer"
DATA_PANEL_TYPE_ID = "data.panel"
PASSIVE_FLOW_PORTS: tuple[str, ...] = ("top", "right", "bottom", "left")

PROMPTS: tuple[dict[str, Any], ...] = (
    {
        "name": "build_flowchart",
        "description": "Plan shapes and positions for a described process and build it with one graph_apply batch.",
        "arguments": ({"name": "description", "description": "The process or workflow to draw.", "required": True},),
    },
    {
        "name": "annotate_board",
        "description": "Add text blocks, media, links, and comments that explain a topic on the active canvas.",
        "arguments": ({"name": "topic", "description": "What the annotations should explain.", "required": True},),
    },
)


# ------------------------------------------------------------------ instructions


def server_instructions() -> str:
    return "\n".join(
        (
            "COREX is a node editor for engineering flowcharts and dataflow workflows; this server drives one live",
            "COREX instance through its local automation API (loopback only, per-instance token).",
            "",
            "1. Call corex_status first: it reports the active workspace, view, scope, selection, run state, and",
            "   whether the app is busy (modal dialog, project IO). Do not mutate while busy.",
            "2. Read corex://guide before the first edit; corex://ops, corex://styles, and corex://node-types are the",
            "   reference for tools, style keys, and passive node types.",
            "3. Ids are prefixed strings (node_..., edge_..., ws_..., view_...). Take them from results, graph_get, or",
            "   graph_find_nodes; never invent them.",
            "4. Prefer one graph_apply batch for more than ~3 mutations: everything is validated first, it is one undo",
            "   step, atomic=true rolls back on failure, and later ops reference earlier ones with $id or $id.field.",
            "5. $ref substitution happens only in declared id fields. Titles, markdown, bodies, and labels are never",
            "   substituted, so a literal $100 is safe there; inside an id field write $$ for a literal dollar.",
            "6. Passive flow nodes (flowchart shapes, annotations, web viewer) connect through ports",
            "   top|right|bottom|left. Data nodes use their spec port keys (catalog_describe_node_type).",
            "   Tidy with layout_arrange (align_center_y rows, align_center_x columns) and layout_straighten, which",
            "   moves nodes so wires run straight and reports skipped_edges.",
            "7. Style with node_set_style / edge_update using the keys in corex://styles; catalog_style_schema adds",
            "   the project's saved presets.",
            "8. Verify visually with capture_screenshot (mode=views returns content-cropped canvas PNGs inline).",
            "   Private headless instances render web panels and 3D viewers blank (fidelity=offscreen_layout); attach",
            "   to a visible instance or launch with --no-headless for native fidelity.",
            "9. Every mutating tool is exactly one undo step: corex_history(action=undo) reverts the last one.",
            "10. Retry errors whose `retryable` is true (APP_BUSY, APP_BUSY_MODAL, a TIMEOUT that expired in the",
            "    queue) after a short pause; every other error carries a hint",
            "    that says what to change. NO_EFFECT means the owner ignored the change; inspect state, do not retry.",
            "11. Never call corex_quit on an attached instance the user owns; quit only private instances you",
            "    launched, and project_save before closing anything that matters.",
        )
    )


# -------------------------------------------------------------------- resources


def resource_name(uri: str) -> str:
    return _resource_meta(uri)[0]


def resource_title(uri: str) -> str:
    return _resource_meta(uri)[1]


def resource_description(uri: str) -> str:
    return _resource_meta(uri)[2]


def resource_text(uri: str) -> str:
    """Markdown body for one ``corex://`` resource; unknown URIs raise ``ValueError``."""
    normalized = normalize_resource_uri(uri)
    if normalized == GUIDE_URI:
        return guide_text()
    if normalized == OPS_URI:
        return ops_text()
    if normalized == STYLES_URI:
        return styles_text()
    if normalized == NODE_TYPES_URI:
        return node_types_text()
    raise ValueError(f"Unknown COREX resource {uri!r}; valid resources: {', '.join(RESOURCE_URIS)}")


def normalize_resource_uri(uri: str) -> str:
    return str(uri or "").strip().rstrip("/").lower()


def _resource_meta(uri: str) -> tuple[str, str, str]:
    meta = _RESOURCE_META.get(normalize_resource_uri(uri))
    if meta is None:
        raise ValueError(f"Unknown COREX resource {uri!r}; valid resources: {', '.join(RESOURCE_URIS)}")
    return meta


# ------------------------------------------------------------------------ guide


def guide_text() -> str:
    apply_example = op_catalog.op_by_name("graph.apply").examples[0]
    lines: list[str] = [
        "# COREX automation guide",
        "",
        "Graph tools act on the active workspace and the open scope of one live COREX instance. Every mutating",
        "tool is one undo step; graph_apply batches are one undo step too.",
        "",
        "## Workflow recipe",
        "",
        "1. `corex_status` -- confirm the instance, the active workspace/view, the selection, and that `busy.*` is false.",
        "2. `catalog_list_node_types(runtime_behavior=\"passive\")` and `catalog_describe_node_type(type_id)` -- learn",
        "   property keys and ports. The passive families are summarised in corex://node-types; active (executing)",
        "   nodes come from the same catalog tools.",
        f"3. Plan coordinates on a {GRID_COLUMN_WIDTH} x {GRID_ROW_HEIGHT} grid: `x = column * {GRID_COLUMN_WIDTH}`,",
        f"   `y = row * {GRID_ROW_HEIGHT}`. Default passive shapes fit one cell, so neighbours never overlap and edge",
        "   labels have room. Left-to-right flows connect `right -> left`; top-to-bottom flows connect `bottom -> top`;",
        "   decision branches leave from `bottom` (yes) and `right` (no) or similar, with `label` on the edge.",
        "4. `graph_apply` -- one batch that creates the shapes and wires them, using `id` names and `$id` references:",
        "",
        "```json",
        json.dumps(apply_example, ensure_ascii=False, indent=2),
        "```",
        "",
        f"   Keep batches under {RECOMMENDED_APPLY_OPS} ops (hard cap {MAX_APPLY_OPS}). Every op is validated before",
        "   anything mutates (one INVALID_PARAMS listing `ops[i].<path>` problems). `atomic=true` (default): the first",
        "   failing op restores the pre-batch workspace, scope, and selection and the call fails with APPLY_FAILED",
        "   (`details.failed_index`, `details.failed_op`, `details.error`, `details.results`). `atomic=false` keeps the",
        "   earlier ops as one undo step and returns `failed_index >= 0` with the failing row's error in `results`.",
        "   `$id` is the earlier op's primary id; `$id.field` / `$id.list.0` read nested result fields.",
        "5. Style -- `node_set_style(node_id, style={...})` merges keys from corex://styles; `preset=` applies a saved",
        "   preset; `propagate=true` copies the style to the passive nodes connected by edges; `edge_update(edge_id,",
        "   style={...}, label=..., path_mode=...)` styles connectors.",
        "6. Structure -- `group_wrap` draws a Group backdrop around nodes (visual grouping); `subnode_create` folds",
        "   nodes into a nested scope (use `scope_navigate(target=\"node\", node_id=shell)` before editing inside,",
        "   `scope_navigate(target=\"root\")` to return); `selection_set` drives the canvas selection.",
        "7. Tidy -- `layout_arrange(node_ids, action=\"align_center_y\")` lines a row up on one center so side ports",
        "   meet (`align_center_x` for a column; also align_left|right|top|bottom, distribute_horizontal|vertical,",
        "   match_width|height). Then `layout_straighten()` (no ids = the whole open scope; or node_ids / edge_ids)",
        "   moves nodes so right->left and bottom->top wires run straight. Read `skipped_edges`: `mixed_port_sides`",
        "   is an elbow such as right->top (reconnect to opposite sides if it should be straight);",
        "   `unresolved_offset` means the ends still differ by `offset` px (move a node with node_update);",
        "   `locked_node` / `hidden_in_collapsed_group` ends are never moved. Check `overlapping_node_pairs`",
        "   and distribute or move nodes apart.",
        "8. Annotate -- `node_add_text` for markdown blocks, `node_add_media` for images/PDF/video (staged into the",
        "   project), `node_add_web_panel` for URLs or inline HTML, `comment_upsert` for threaded comments,",
        "   `link_upsert` for url|file|folder|workspace|node links.",
        "9. `project_save(path=\"C:/.../name.cxproj\")` -- a new project needs a path once (reason_code",
        "   `save_path_required`); afterwards `project_save()` saves in place and publishes staged files.",
        "10. `capture_screenshot` -- mode=views renders the active view cropped to content and returns the PNG inline;",
        "   pass `view_ids` for other views or `mode=\"window\"` for the whole window. Look at the image before",
        "   declaring the board done.",
        "",
        "## Reading the graph",
        "",
        "- `graph_get(include_properties=true, include_style=true)` -- full snapshot of the active workspace",
        "  (`scope=\"all\"` includes nodes inside subnodes with `parent_node_id`).",
        "- `graph_get_node(node_id)` -- geometry, properties, style, effective ports with connections, links, comments.",
        "- `graph_find_nodes(title_contains=..., type_id=...)` -- locate nodes without dumping the graph.",
        "- `workspace_list` / `workspace_create` / `workspace_update(activate=true)` -- tabs; `view_create` /",
        "  `view_set_camera(frame=\"all\")` -- cameras.",
        "",
        "## Runs",
        "",
        "- `run_start(wait=true, timeout_s=...)` runs the active workspace (or `scope=\"nodes\"`); passive-only graphs",
        "  complete immediately. `run_status(wait=true)` polls; `run_control(action=\"stop\")` stops.",
        "- Graph edits are allowed during a run. Only `run_start` returns RUN_ACTIVE, when a run or the auto-run your",
        "  edits queued is in flight: call `run_status(wait=true)` first.",
        "- One corex-mcp session sends one request at a time, so a long `run_status(wait=true)` delays later tool",
        "  calls (including `run_control(stop)`); use a short `timeout_s` and poll when you may need to stop.",
        "",
        "## Error codes",
        "",
        "Every error is `{code, message, hint, details, retryable}`. Default hints:",
        "",
        "| code | retryable | hint |",
        "|---|---|---|",
    ]
    for code in ERROR_CODES:
        lines.append(f"| `{code}` | {'yes' if code in RETRYABLE_CODES else 'no'} | {default_hint(code)} |")
    lines.extend(
        (
            "",
            "## Retry rules",
            "",
            "- `APP_BUSY` (project IO): wait 1-2 s and resend the same request.",
            "- `TIMEOUT`: resend only when `retryable` is true (the request expired in COREX's queue,",
            "  `details.executed=false`). `retryable=false` means the client stopped waiting but COREX may still",
            "  apply the op: check `corex_status`, `graph_get` or `corex_history` before resending.",
            "- `APP_BUSY_MODAL`: a dialog is open in the COREX window; ask the user to close it, then resend.",
            "- `APPLY_FAILED`: read `details.failed_index` / `details.results`, fix that op, resend the whole batch",
            "  (atomic batches were rolled back).",
            "- `NO_EFFECT`, `INVALID_PARAMS`, `NOT_FOUND`, `PORT_INCOMPATIBLE`, `PROPERTY_LOCKED_BY_PORT`: not retryable",
            "  as-is; change the request per the hint.",
            "- `APP_SHUTTING_DOWN`: the instance is gone; restart the MCP server (or COREX with --automation).",
            "",
            "## First-pass limits",
            "",
            "- Graph tools act on the active workspace and the open scope only.",
            "- Web panels and 3D viewers are blank in offscreen (private headless) screenshots",
            "  (`fidelity=offscreen_layout`); attach to a visible instance or launch with --no-headless.",
            "- graph_apply rollback cannot undo staged files or the title-driven artifact folder rename.",
            "- A failed run refocuses the canvas on the failed node (existing UI behaviour).",
        )
    )
    return "\n".join(lines) + "\n"


# -------------------------------------------------------------------------- ops


def ops_text() -> str:
    tools = op_catalog.mcp_tool_ops()
    lines: list[str] = [
        "# COREX op reference",
        "",
        f"{len(tools)} MCP tools, one per wire op (`tool -> op`). Params are the tool's input schema; unknown keys are",
        "rejected. Ops flagged `apply` may appear inside `graph_apply`; `$ref` tokens are resolved only in the listed",
        "`$ref fields`. `deferred` ops may block up to their `timeout_s` (the MCP call waits `timeout_s + 30 s`).",
        "",
    ]
    for domain, ops in op_catalog.ops_by_domain().items():
        lines.append(f"## {domain}")
        lines.append("")
        for op in ops:
            if op.mcp_tool is None:
                continue
            lines.extend(_op_section(op))
    return "\n".join(lines).rstrip() + "\n"


def _op_section(op: OpSpec) -> list[str]:
    lines = [f"### `{op.mcp_tool}` -> `{op.name}`", "", op.summary.strip()]
    if op.description.strip():
        lines.extend(("", op.description.strip()))
    lines.append("")
    lines.append(f"- flags: {_flag_text(op)}")
    properties = op.params.get("properties") or {}
    required = [str(key) for key in (op.params.get("required") or ())]
    required_lines = [_param_line(key, properties[key]) for key in required if key in properties]
    optional_lines = [_param_line(key, schema) for key, schema in properties.items() if key not in required]
    lines.append("- required: " + ("none" if not required_lines else ""))
    lines.extend(f"  - {line}" for line in required_lines)
    lines.append("- optional: " + ("none" if not optional_lines else ""))
    lines.extend(f"  - {line}" for line in optional_lines)
    if op.ref_fields:
        lines.append("- $ref fields: " + ", ".join(f"`{field}`" for field in op.ref_fields))
    result_keys = list((op.result.get("properties") or {}).keys())
    if result_keys:
        lines.append("- result keys: " + ", ".join(f"`{key}`" for key in result_keys))
    if op.primary_id_field:
        lines.append(f"- graph_apply `$id` resolves to: `{op.primary_id_field}`")
    if op.examples:
        lines.append("- example: `" + json.dumps(op.examples[0], ensure_ascii=False, separators=(",", ":")) + "`")
    lines.append("")
    return lines


def _flag_text(op: OpSpec) -> str:
    flags = ["mutates graph" if op.mutates_graph else "read-only"]
    if op.apply_allowed:
        flags.append("apply")
    if op.deferred:
        flags.append("deferred")
    return ", ".join(flags)


def _param_line(name: str, schema: Mapping[str, Any]) -> str:
    summary = schema_summary(schema)
    description = str(schema.get("description") or "").strip()
    return f"`{name}`: {summary}" + (f" -- {description}" if description else "")


def schema_summary(schema: Mapping[str, Any]) -> str:
    """Compact one-line rendering of a param schema (type, enum, default, bounds)."""
    parts = [_type_label(schema)]
    enum = schema.get("enum")
    if isinstance(enum, (list, tuple)) and enum:
        parts.append("one of " + "|".join(str(value) for value in enum))
    if "default" in schema:
        parts.append("default " + json.dumps(schema["default"], ensure_ascii=False))
    bounds = (("minimum", ">="), ("maximum", "<="), ("minLength", "min length"), ("minItems", "min items"), ("maxItems", "max items"))
    for keyword, label in bounds:
        if keyword in schema:
            parts.append(f"{label} {schema[keyword]}")
    return ", ".join(parts)


def _type_label(schema: Mapping[str, Any]) -> str:
    declared = schema.get("type")
    if isinstance(declared, (list, tuple)):
        label = "|".join(str(item) for item in declared)
    elif isinstance(declared, str):
        label = declared
    else:
        label = "any"
    if schema.get("nullable") and "null" not in label:
        label += "|null"
    if label == "array":
        items = schema.get("items")
        label = f"array of {_type_label(items)}" if isinstance(items, Mapping) else "array"
    elif label == "object":
        keys = list((schema.get("properties") or {}).keys())
        if keys:
            label += " (keys: " + ", ".join(keys) + ")"
    return label


# ----------------------------------------------------------------------- styles


def styles_text() -> str:
    text_defaults = {key: value for key, value in DEFAULT_TEXT_STYLE_PROPERTIES.items() if key != "text"}
    lines = [
        "# COREX style keys",
        "",
        "Colours are `#RRGGBB` or `#RRGGBBAA`. Values outside an enum or range are dropped by the owner and the",
        "op reports NO_EFFECT when nothing changed. `catalog_style_schema` returns the same keys plus the built-in and",
        "project-saved presets (`node_set_style(preset=<id or name>)`).",
        "",
        "## Node style (`node_set_style`, passive nodes only)",
        "",
        "- keys: " + ", ".join(f"`{key}`" for key in NODE_STYLE_KEYS),
        "- enums: `font_weight` "
        + "|".join(PASSIVE_NODE_STYLE_FONT_WEIGHTS)
        + "; `gradient_direction` "
        + "|".join(PASSIVE_NODE_STYLE_GRADIENT_DIRECTIONS),
        "- aliases: " + _alias_text(NODE_STYLE_ALIASES),
        "- rules: `border_width` > 0, `corner_radius` >= 0, `font_size` positive integer, `gradient_enabled=true`",
        "  requires `gradient_color`; `replace=true` swaps the whole override, `clear=true` removes it,",
        "  `propagate=true` copies the style to passive nodes connected by edges.",
        "",
        "## Edge style (`edge_connect(style=...)`, `edge_update(style=...)`)",
        "",
        "- keys: " + ", ".join(f"`{key}`" for key in EDGE_STYLE_KEYS),
        "- enums: `stroke_pattern` "
        + "|".join(FLOW_EDGE_STYLE_PATTERNS)
        + "; `arrow_head` "
        + "|".join(FLOW_EDGE_ARROW_HEADS)
        + "; `path_mode` "
        + "|".join(FLOW_EDGE_PATH_MODES)
        + "; `display_mode` "
        + "|".join(EDGE_DISPLAY_MODES),
        "- aliases: " + _alias_text(EDGE_STYLE_ALIASES),
        "- rules: `stroke_width` > 0; `path_mode=auto` clears the path override; `label` / `clear_label` and",
        "  `enabled` are top-level `edge_update` params, not style keys.",
        "",
        "## Text style (`node_add_text(style=...)`, rich-text slots via `node_update(properties=...)`)",
        "",
        "- keys: " + ", ".join(f"`{key}`" for key in TEXT_STYLE_KEYS),
        "- enums: `format` "
        + "|".join(TEXT_STYLE_FORMATS)
        + "; `font_weight` "
        + "|".join(TEXT_STYLE_FONT_WEIGHTS)
        + "; `horizontal_alignment` "
        + "|".join(TEXT_STYLE_HORIZONTAL_ALIGNMENTS)
        + "; `vertical_alignment` "
        + "|".join(TEXT_STYLE_VERTICAL_ALIGNMENTS)
        + "; `wrap_mode` "
        + "|".join(TEXT_STYLE_WRAP_MODES),
        "- aliases: " + _alias_text(TEXT_STYLE_ALIASES),
        "- ranges: `font_size` 6..144 (0 inherits), `opacity` 0..100, `padding` 0..64, `line_height` 0.5..4.0,",
        "  `letter_spacing` -10..20.",
        "- defaults for `passive.annotation.text`: `" + json.dumps(text_defaults, ensure_ascii=False) + "`",
        "- slot property keys: `passive.annotation.text` stores content in `text` and uses the bare style keys",
        "  (`font_size`, `text_color`, `format`, ...); other rich-text slots prefix the content key",
        "  (`body_font_size`, `body_format`, `subtitle_text_color`, ...). Set them with",
        "  `node_update(node_id, properties={...})`.",
    ]
    return "\n".join(lines) + "\n"


def _alias_text(aliases: Mapping[str, str]) -> str:
    return ", ".join(f"`{alias}` -> `{key}`" for alias, key in aliases.items()) or "none"


# ------------------------------------------------------------------- node types


def node_types_text() -> str:
    ports = "|".join(PASSIVE_FLOW_PORTS)
    lines = [
        "# COREX passive node types",
        "",
        "Passive nodes draw the board and never execute; `node_add(type_id, x, y, title=..., properties={...})`",
        "creates any of them. Titles of flowchart / annotation / group nodes live in `properties.title` (the",
        "`title` param sets it). Active (executing) nodes such as file readers, SSH steps, and solvers are not listed",
        "here: discover them with `catalog_list_node_types(runtime_behavior=\"active\", query=...)` and inspect ports",
        "and properties with `catalog_describe_node_type(type_id)`.",
        "",
        "## Flowchart shapes (`surface_family=flowchart`)",
        "",
        f"- ports: `{ports}` (neutral flow ports, multiple connections allowed)",
        "- properties: `title`, `body` (rich-text slot: `body_format`, `body_font_size`, `body_text_color`, ...).",
        "  The shape draws `body`. The classic shapes (start, end, process, decision, document, connector,",
        "  input_output, predefined_process, database) default `body` to their name, and node_add / node_update",
        "  copy `title` into an untouched body there, so `title` alone sets the label. Other shapes (card,",
        "  callout, message, timestamp, ...) treat `body` as separate content: set `properties.body` yourself.",
        "- type ids: " + ", ".join(f"`{type_id}`" for type_id in FLOWCHART_TYPE_IDS),
        "- specials: `passive.flowchart.timestamp` renders `%date{...}%` placeholders in `body` and has a `live`",
        "  boolean; `passive.flowchart.isometric_cube` adds `body_top` and `body_right` face texts.",
        "",
        "## Annotations (`surface_family=annotation` / `group_backdrop`)",
        "",
        f"- ports: `{ports}`",
        "- `passive.annotation.sticky_note`: `title`, `body` (+ `body_*` slot keys).",
        "- `passive.annotation.callout`: `title`, `body` (+ `body_*` slot keys).",
        "- `passive.annotation.section_header`: `title`, `subtitle` (+ `subtitle_*` slot keys).",
        "- `passive.annotation.text`: content key `text`, `format` (markdown|plain), bare style keys",
        "  (`font_family`, `font_size`, `text_color`, `background_color`, alignment, ...). Prefer `node_add_text`,",
        "  which takes `markdown`, `format`, and `style` directly.",
        "- `passive.annotation.group_backdrop`: `title` only; membership is geometric. Prefer `group_wrap(node_ids,",
        "  title)` so the backdrop is sized around the members.",
        "",
        f"## Media panel (`{MEDIA_PANEL_TYPE_ID}`)",
        "",
        "- create with `node_add_media(path, x, y, fit_mode=..., show_title=..., show_frame=...)`; the file is staged",
        "  into the project and `properties.source` holds the artifact ref.",
        "- properties: `source`, `fit_mode` (contain|cover|original), `show_title`, `show_frame`,",
        "  `lock_aspect_ratio`, `rotation_degrees`, `page_number` (PDF), `auto_play` / `loop` / `muted` (video).",
        "- ports: data input `source` (path, string, image, or plot values) instead of the cardinal flow ports;",
        "  check `catalog_describe_node_type` before wiring.",
        "",
        f"## Web page viewer (`{WEB_PAGE_VIEWER_TYPE_ID}`)",
        "",
        "- create with `node_add_web_panel(x, y, url=...)` or `html=...`. Inline HTML is a session scratch file that is",
        "  NOT packed into the .cxproj; for durable content use `project_stage_file` and pass its `artifact_ref` as `url`.",
        "- properties: `start_location`, `display_mode` (responsive|fit_width|fit_page; default fit_width),",
        "  `show_title`, `show_frame`, `persist_browser_state`.",
        f"- ports: `{ports}`. Not rendered in offscreen screenshots (fidelity=offscreen_layout).",
        "",
        f"## Path pointer (`{PATH_POINTER_TYPE_ID}`)",
        "",
        "- `node_add(\"io.path_pointer\", x, y, properties={\"path\": \"C:/data/run1\", \"mode\": \"folder\"})`;",
        "  `mode` is file|folder.",
        "- ports: data outputs `path` and `exists` (no cardinal flow ports); connect them to active nodes' inputs.",
        "",
        f"## Data panel (`{DATA_PANEL_TYPE_ID}`)",
        "",
        "- `node_add(\"data.panel\", x, y, properties={\"value\": \"text or data\"})`; it is a Data/Control node that",
        "  passes a connected `input` through to `output` and otherwise shows `value`.",
        "- properties: `value`, `mode` (0 text, 1 data), `interpretation` (text|auto|number), `font_size`,",
        "  `alignment`, `auto_resize`.",
        "- ports: data `input` / `output` (tree structured).",
        "",
        "## Geometry hints",
        "",
        f"- Plan on a {GRID_COLUMN_WIDTH} x {GRID_ROW_HEIGHT} grid; pass `width` / `height` to `node_add` for larger",
        "  text or media blocks; `catalog_describe_node_type` reports `default_size` and `min_size`.",
        "- `node_update(node_id, x=..., y=..., width=..., height=...)` moves and resizes; `layout_arrange` aligns,",
        "  distributes, and matches sizes; `layout_straighten` makes wires straight.",
        "- Default heights differ by shape (process 84, decision 128; read `default_size`). Nodes at the same `y`",
        "  align their top edges, so side ports sit at different heights and straight connectors jog. Fix a row with",
        "  `layout_arrange(action=\"align_center_y\")` (or place each node at `y = row_center - height / 2`), then",
        "  `layout_straighten`.",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------- prompts


def prompt_names() -> tuple[str, ...]:
    return tuple(str(prompt["name"]) for prompt in PROMPTS)


def prompt_description(name: str) -> str:
    return str(_prompt_spec(name)["description"])


def prompt_text(name: str, arguments: Mapping[str, Any] | None = None) -> str:
    """User message for one prompt template; unknown names raise ``ValueError``."""
    spec = _prompt_spec(name)
    values = {str(key): str(value) for key, value in (arguments or {}).items()}
    if spec["name"] == "build_flowchart":
        description = values.get("description", "").strip() or "the process the user describes"
        return "\n".join(
            (
                f"Build a COREX flowchart for: {description}",
                "",
                "1. Call corex_status; stop and report if busy.* is true.",
                "2. Plan the steps as flowchart shapes (passive.flowchart.start, process, decision, input_output,",
                f"   document, database, end). Place them on a {GRID_COLUMN_WIDTH} x {GRID_ROW_HEIGHT} grid, left to right",
                "   (or top to bottom for long flows), with decision branches labelled on their edges.",
                "3. Emit ONE graph_apply batch: node_add ops with id names, then edge_connect ops that reference them",
                "   with $id (right -> left for horizontal flow, bottom -> top for vertical). Set label=\"Build flowchart\".",
                "4. Tidy: layout_arrange(action=\"align_center_y\") on each row (align_center_x on each column),",
                "   then layout_straighten() and fix any skipped_edges it reports.",
                "5. Optionally style with node_set_style (see corex://styles) and wrap phases with group_wrap.",
                "6. Finish with capture_screenshot and describe what the board shows.",
            )
        )
    topic = values.get("topic", "").strip() or "the current board"
    return "\n".join(
        (
            f"Annotate the active COREX canvas to explain: {topic}",
            "",
            "1. Call corex_status, then graph_get to see what is already on the board and where free space is.",
            "2. Add explanations with node_add_text (markdown), images or PDFs with node_add_media, and references",
            "   with node_add_web_panel or link_upsert; keep new items on the grid next to the nodes they explain.",
            "3. Attach comment_upsert notes to specific nodes for review remarks; use group_wrap with a title to",
            "   frame related nodes.",
            "4. Prefer one graph_apply batch for the text and media nodes; then capture_screenshot and summarise.",
        )
    )


def _prompt_spec(name: str) -> dict[str, Any]:
    wanted = str(name or "").strip()
    for prompt in PROMPTS:
        if prompt["name"] == wanted:
            return prompt
    raise ValueError(f"Unknown prompt {name!r}; valid prompts: {', '.join(prompt_names())}")


__all__ = [
    "ANNOTATION_TYPE_IDS",
    "DATA_PANEL_TYPE_ID",
    "EDGE_STYLE_ALIASES",
    "EDGE_STYLE_KEYS",
    "FLOWCHART_TYPE_IDS",
    "GUIDE_URI",
    "MEDIA_PANEL_TYPE_ID",
    "NODE_STYLE_ALIASES",
    "NODE_STYLE_KEYS",
    "NODE_TYPES_URI",
    "OPS_URI",
    "PASSIVE_FLOW_PORTS",
    "PATH_POINTER_TYPE_ID",
    "PROMPTS",
    "RESOURCE_MIME_TYPE",
    "RESOURCE_URIS",
    "STYLES_URI",
    "TEXT_STYLE_ALIASES",
    "TEXT_STYLE_KEYS",
    "WEB_PAGE_VIEWER_TYPE_ID",
    "guide_text",
    "node_types_text",
    "normalize_resource_uri",
    "ops_text",
    "prompt_description",
    "prompt_names",
    "prompt_text",
    "resource_description",
    "resource_name",
    "resource_text",
    "resource_title",
    "schema_summary",
    "server_instructions",
    "styles_text",
]
