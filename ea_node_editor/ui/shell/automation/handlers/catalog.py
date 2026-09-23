# Purpose: Catalog automation handlers: node type listing/description and style schema (T05); style key/preset owners for node handlers.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_nodes.py
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ea_node_editor.automation.errors import NOT_FOUND, AutomationOpError
from ea_node_editor.automation.op_model import Deferred
from ea_node_editor.graph.effective_ports import effective_ports, is_subnode_pin_type
from ea_node_editor.graph.records import NodeInstance
from ea_node_editor.nodes.node_specs import NodeTypeSpec, PropertySpec
from ea_node_editor.passive_style_normalization import (
    FLOW_EDGE_ARROW_HEADS,
    FLOW_EDGE_PATH_MODES,
    FLOW_EDGE_STYLE_PATTERNS,
    PASSIVE_NODE_STYLE_FONT_WEIGHTS,
    PASSIVE_NODE_STYLE_GRADIENT_DIRECTIONS,
    RETIRED_PASSIVE_NODE_STYLE_KEYS,
    _PASSIVE_NODE_STYLE_KEYS,
    normalize_passive_style_presets,
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
from ea_node_editor.ui.passive_style_presets import built_in_style_presets
from ea_node_editor.ui.shell.automation.context import AutomationContext
from ea_node_editor.ui.shell.automation.handlers.graph_read import instance_spec, json_safe, port_summary
from ea_node_editor.ui_qml.graph_surface_metrics import node_surface_metrics
from ea_node_editor.ui_qml.surface_contracts import surface_spec_for_node_type

# Node style keys the owner (normalize_passive_node_style_payload) actually accepts.
NODE_STYLE_KEYS: tuple[str, ...] = tuple(sorted(_PASSIVE_NODE_STYLE_KEYS - RETIRED_PASSIVE_NODE_STYLE_KEYS))
# Friendlier names accepted by node.set_style and mapped onto owner keys.
NODE_STYLE_ALIASES: dict[str, str] = {"fill_color_end": "gradient_color"}
NODE_STYLE_ENUMS: dict[str, tuple[str, ...]] = {
    "font_weight": tuple(PASSIVE_NODE_STYLE_FONT_WEIGHTS),
    "gradient_direction": tuple(PASSIVE_NODE_STYLE_GRADIENT_DIRECTIONS),
}
# Flow edge style keys: normalize_flow_edge_style_payload keys plus the display_mode
# the scene's edge style normaliser understands (default | faint | hidden).
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
# Agent-facing edge style aliases (ops/common.EDGE_STYLE spellings) -> persisted flow-edge keys.
# Single shell-side definition: handlers/edges.py validates style keys against EDGE_STYLE_KEYS after
# mapping these, and catalog.style_schema publishes them.
EDGE_STYLE_ALIASES: dict[str, str] = {
    "color": "stroke_color",
    "width": "stroke_width",
    "pattern": "stroke_pattern",
    "label_color": "label_text_color",
    "label_background": "label_background_color",
}
EDGE_STYLE_ENUMS: dict[str, tuple[str, ...]] = {
    "stroke_pattern": tuple(FLOW_EDGE_STYLE_PATTERNS),
    "arrow_head": tuple(FLOW_EDGE_ARROW_HEADS),
    "path_mode": tuple(FLOW_EDGE_PATH_MODES),
    "display_mode": ("default", "faint", "hidden"),
}
TEXT_STYLE_KEYS: tuple[str, ...] = ("format", *TEXT_ANNOTATION_STYLE_KEYS)
TEXT_STYLE_ALIASES: dict[str, str] = {"color": "text_color"}
TEXT_STYLE_ENUMS: dict[str, tuple[str, ...]] = {
    "format": tuple(TEXT_STYLE_FORMATS),
    "font_weight": tuple(TEXT_STYLE_FONT_WEIGHTS),
    "horizontal_alignment": tuple(TEXT_STYLE_HORIZONTAL_ALIGNMENTS),
    "vertical_alignment": tuple(TEXT_STYLE_VERTICAL_ALIGNMENTS),
    "wrap_mode": tuple(TEXT_STYLE_WRAP_MODES),
}
# Surface families whose rendered title is the ``title`` *property*; ``node.title``
# is only a synced mirror there (see _GraphSceneContext.sync_surface_title).
TITLE_PROPERTY_FAMILIES = frozenset({"flowchart", "annotation", "group_backdrop"})
_MODEL_VIEWER_TYPE_ID = "model.viewer"


def title_is_property_backed(spec: NodeTypeSpec) -> bool:
    return str(spec.surface_family or "") in TITLE_PROPERTY_FAMILIES and any(
        prop.key == "title" for prop in spec.properties
    )


def project_style_presets(context: AutomationContext) -> dict[str, list[dict[str, Any]]]:
    """Built-in presets followed by the project's saved presets (metadata.ui.passive_style_presets)."""
    metadata = context.model.project.metadata
    ui = metadata.get("ui") if isinstance(metadata, Mapping) else None
    saved = normalize_passive_style_presets(ui.get("passive_style_presets") if isinstance(ui, Mapping) else None)
    presets: dict[str, list[dict[str, Any]]] = {}
    for kind, saved_key in (("node", "node_presets"), ("edge", "edge_presets")):
        entries = [dict(entry) for entry in built_in_style_presets(kind)]
        for entry in saved[saved_key]:
            row = dict(entry)
            row["read_only"] = False
            entries.append(row)
        presets[kind] = entries
    return presets


def lookup_style_preset(context: AutomationContext, kind: str, preset: str) -> dict[str, Any]:
    """Find a preset by id or (case-insensitive) name, raising NOT_FOUND with the available names."""
    wanted = str(preset or "").strip()
    entries = project_style_presets(context).get(kind, [])
    for entry in entries:
        if str(entry.get("preset_id")) == wanted:
            return entry
    lowered = wanted.lower()
    for entry in entries:
        if str(entry.get("name") or "").strip().lower() == lowered:
            return entry
    raise AutomationOpError(
        NOT_FOUND,
        f"No {kind} style preset named '{wanted}'.",
        hint="Call catalog.style_schema and use one of presets.node[].preset_id or name.",
        details={
            "kind": kind,
            "preset": wanted,
            "available": [{"preset_id": entry.get("preset_id"), "name": entry.get("name")} for entry in entries],
        },
    )


def node_type_row(spec: NodeTypeSpec) -> dict[str, Any]:
    return {
        "type_id": spec.type_id,
        "display_name": str(spec.display_name),
        "category_path": [str(part) for part in spec.category_path],
        "category": "/".join(str(part) for part in spec.category_path),
        "runtime_behavior": str(spec.runtime_behavior),
        "surface_family": str(spec.surface_family),
        "surface_variant": str(spec.surface_variant or ""),
        "description": str(spec.description or ""),
        "keywords": [str(keyword) for keyword in spec.keywords],
        "collapsible": bool(spec.collapsible),
    }


def _property_row(prop: PropertySpec) -> dict[str, Any]:
    return {
        "key": prop.key,
        "type": str(prop.type),
        "label": str(prop.label),
        "default": json_safe(prop.make_default()),
        "enum_values": [str(value) for value in prop.enum_values],
        "minimum": prop.minimum,
        "maximum": prop.maximum,
        "step": float(prop.step or 0.0),
        "description": str(prop.description or ""),
        "expose_port_toggle": bool(prop.expose_port_toggle),
        "inspector_visible": bool(prop.inspector_visible),
        "group": str(prop.group or ""),
        "sensitive": bool(prop.sensitive),
        "nullable": bool(prop.nullable),
        "affects_execution": bool(prop.affects_execution),
    }


def _type_is_resizable(spec: NodeTypeSpec) -> bool:
    # Mirrors GraphNodeHost.qml manualResizeEligible: passive nodes, panel-like
    # surfaces (media panel), and the 3D model viewer accept manual resize.
    if str(spec.runtime_behavior) == "passive" or spec.type_id == _MODEL_VIEWER_TYPE_ID:
        return True
    surface = surface_spec_for_node_type(type_id=spec.type_id, spec=spec)
    return bool(surface.metadata.get("panel_like", False))


def _probe_node(context: AutomationContext, spec: NodeTypeSpec) -> NodeInstance:
    return NodeInstance(
        node_id="",
        type_id=spec.type_id,
        title=str(spec.display_name),
        x=0.0,
        y=0.0,
        properties=context.registry.default_properties(spec.type_id),
    )


def _size_payloads(probe: NodeInstance, spec: NodeTypeSpec) -> tuple[dict[str, float] | None, dict[str, float] | None]:
    try:
        metrics = node_surface_metrics(probe, spec, {})
    except Exception:  # noqa: BLE001 - sizing is advisory; unknown surfaces report null sizes
        return None, None
    return (
        {"width": float(metrics.default_width), "height": float(metrics.default_height)},
        {"width": float(metrics.min_width), "height": float(metrics.min_height)},
    )


# --------------------------------------------------------------------- handlers


def list_node_types(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    query = str(params.get("query") or "").strip().lower()
    category = str(params.get("category") or "").strip().lower().strip("/")
    behavior = str(params.get("runtime_behavior") or "any")
    limit = int(params.get("limit") or 200)
    rows: list[dict[str, Any]] = []
    for spec in context.registry.all_specs():
        if is_subnode_pin_type(spec.type_id):
            continue  # pins only exist inside a subnode shell; they are not addable
        if behavior != "any" and str(spec.runtime_behavior) != behavior:
            continue
        row = node_type_row(spec)
        if category and not row["category"].lower().startswith(category):
            continue
        if query:
            haystack = " ".join(
                (row["type_id"], row["display_name"], row["category"], row["description"], *row["keywords"])
            ).lower()
            if query not in haystack:
                continue
        rows.append(row)
    rows.sort(key=lambda row: (tuple(row["category_path"]), row["display_name"].lower(), row["type_id"]))
    return {"node_types": rows[:limit], "total": len(rows)}


def describe_node_type(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    spec = context.spec_for(str(params["type_id"]))
    probe = _probe_node(context, spec)
    resolved = instance_spec(context, probe) or spec
    default_size, min_size = _size_payloads(probe, resolved)
    return {
        **node_type_row(spec),
        "resizable": _type_is_resizable(spec),
        "title_is_property": title_is_property_backed(spec),
        "default_size": default_size,
        "min_size": min_size,
        "ports": [port_summary(port) for port in effective_ports(node=probe, spec=resolved, workspace_nodes={})],
        "properties": [_property_row(prop) for prop in resolved.properties],
    }


def style_schema(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    presets = project_style_presets(context)
    text_defaults = {key: value for key, value in DEFAULT_TEXT_STYLE_PROPERTIES.items() if key != "text"}
    return {
        "node_style": {
            "keys": list(NODE_STYLE_KEYS),
            "enums": {key: list(values) for key, values in NODE_STYLE_ENUMS.items()},
            "aliases": dict(NODE_STYLE_ALIASES),
            "notes": (
                "Colours are #RRGGBB or #RRGGBBAA; border_width > 0; corner_radius >= 0; font_size is a "
                "positive integer; gradient_enabled=true requires gradient_color."
            ),
        },
        "edge_style": {
            "keys": list(EDGE_STYLE_KEYS),
            "enums": {key: list(values) for key, values in EDGE_STYLE_ENUMS.items()},
            "aliases": dict(EDGE_STYLE_ALIASES),
            "notes": (
                "Colours are #RRGGBB or #RRGGBBAA; stroke_width > 0; path_mode=auto clears the override; "
                "keys outside keys/aliases are rejected with INVALID_PARAMS."
            ),
        },
        "text_style": {
            "keys": list(TEXT_STYLE_KEYS),
            "enums": {key: list(values) for key, values in TEXT_STYLE_ENUMS.items()},
            "aliases": dict(TEXT_STYLE_ALIASES),
            "defaults": json_safe(text_defaults),
            "slot_property_key": "<content_key>_<style_key>; passive.annotation.text uses bare keys (content key 'text')",
            "notes": "font_size 6..144, opacity 0..100, padding 0..64, line_height 0.5..4.0, letter_spacing -10..20.",
        },
        "presets": {
            "node": json_safe(presets["node"]),
            "edge": json_safe(presets["edge"]),
        },
    }


HANDLERS = {
    'catalog.list_node_types': list_node_types,
    'catalog.describe_node_type': describe_node_type,
    'catalog.style_schema': style_schema,
}

__all__ = [
    "EDGE_STYLE_ALIASES",
    "EDGE_STYLE_ENUMS",
    "EDGE_STYLE_KEYS",
    "HANDLERS",
    "NODE_STYLE_ALIASES",
    "NODE_STYLE_ENUMS",
    "NODE_STYLE_KEYS",
    "TEXT_STYLE_ALIASES",
    "TEXT_STYLE_ENUMS",
    "TEXT_STYLE_KEYS",
    "TITLE_PROPERTY_FAMILIES",
    "lookup_style_preset",
    "node_type_row",
    "project_style_presets",
    "title_is_property_backed",
]
