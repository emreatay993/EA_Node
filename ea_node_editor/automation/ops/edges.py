# Purpose: Edge op specs: connect, update (label/style/mode/enabled), delete.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_catalog.py
from __future__ import annotations

from ea_node_editor.automation.op_model import (
    OpSpec,
    array_schema,
    boolean_schema,
    id_list_schema,
    object_schema,
    string_schema,
)
from ea_node_editor.automation.ops.common import (
    CHANGED_FIELDS,
    EDGE_ID,
    EDGE_STYLE,
    EDGE_SUMMARY,
    NODE_ID,
    PORT_KEY,
)

DOMAIN = "edge"

CONNECT = OpSpec(
    name="edge.connect",
    domain=DOMAIN,
    summary="Connect two ports. Passive flow ports are top|right|bottom|left; data ports use their spec keys.",
    description=(
        "replace_existing=false (default) appends to inputs that allow multiple connections and returns "
        "PORT_INCOMPATIBLE when the target is already occupied and single-valued; replace_existing=true "
        "rewires and reports replaced_edge_ids."
    ),
    params=object_schema(
        {
            "source_node_id": NODE_ID,
            "source_port": PORT_KEY,
            "target_node_id": NODE_ID,
            "target_port": PORT_KEY,
            "replace_existing": boolean_schema(default=False),
            "label": string_schema("Optional flow edge label"),
            "style": EDGE_STYLE,
        },
        required=("source_node_id", "source_port", "target_node_id", "target_port"),
    ),
    result=object_schema(
        {"edge_id": EDGE_ID, "edge": EDGE_SUMMARY, "replaced_edge_ids": array_schema(EDGE_ID)},
        additional=True,
    ),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("source_node_id", "target_node_id"),
    primary_id_field="edge_id",
    mcp_tool="edge_connect",
    examples=({"source_node_id": "$start", "source_port": "right", "target_node_id": "$mesh", "target_port": "left"},),
)

UPDATE = OpSpec(
    name="edge.update",
    domain=DOMAIN,
    summary="Update an edge's label, style, path mode, enabled flag, or display mode; optionally clear label/style.",
    params=object_schema(
        {
            "edge_id": EDGE_ID,
            "label": string_schema(),
            "style": EDGE_STYLE,
            "path_mode": string_schema(enum=("auto", "pipe", "bezier")),
            "enabled": boolean_schema(),
            "display_mode": string_schema(enum=("default", "faint", "hidden")),
            "clear_style": boolean_schema(default=False),
            "clear_label": boolean_schema(default=False),
        },
        required=("edge_id",),
    ),
    result=object_schema({"edge_id": EDGE_ID, "changed": CHANGED_FIELDS, "edge": EDGE_SUMMARY}, additional=True),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("edge_id",),
    primary_id_field="edge_id",
    mcp_tool="edge_update",
)

DELETE = OpSpec(
    name="edge.delete",
    domain=DOMAIN,
    summary="Delete one or more edges.",
    params=object_schema({"edge_ids": id_list_schema("Edge ids to delete")}, required=("edge_ids",)),
    result=object_schema({"deleted_edge_ids": array_schema(EDGE_ID)}, additional=True),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("edge_ids[]",),
    mcp_tool="edge_delete",
)

OPS: tuple[OpSpec, ...] = (CONNECT, UPDATE, DELETE)

__all__ = ["CONNECT", "DELETE", "DOMAIN", "OPS", "UPDATE"]
