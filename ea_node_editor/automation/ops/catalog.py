# Purpose: Catalog op specs: list/describe node types and the style schema.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_catalog.py
from __future__ import annotations

from ea_node_editor.automation.op_model import (
    OpSpec,
    any_schema,
    array_schema,
    boolean_schema,
    number_schema,
    object_schema,
    string_schema,
)
from ea_node_editor.automation.ops.common import PORT_SUMMARY, TYPE_ID

DOMAIN = "catalog"

NODE_TYPE_ROW = object_schema(
    {
        "type_id": TYPE_ID,
        "display_name": string_schema(),
        "category_path": array_schema(string_schema()),
        "runtime_behavior": string_schema(description="active | passive | compile_only"),
        "surface_family": string_schema(),
        "description": string_schema(),
        "keywords": array_schema(string_schema()),
    },
    additional=True,
)

LIST_NODE_TYPES = OpSpec(
    name="catalog.list_node_types",
    domain=DOMAIN,
    summary="List available node types with optional text/category/behaviour filters.",
    description=(
        "Flowcharts and boards are built from the passive families (passive.flowchart.*, "
        "passive.annotation.*, web.page_viewer, io.path_pointer) plus two active display nodes "
        "(media.panel, data.panel); node_set_style only accepts passive nodes."
    ),
    params=object_schema(
        {
            "query": string_schema("Case-insensitive match against id, name, keywords, category"),
            "category": string_schema("Category path prefix, e.g. 'Utilities/Flowchart'"),
            "runtime_behavior": string_schema(enum=("any", "active", "passive"), default="any"),
            "limit": number_schema(minimum=1, maximum=500, default=200, integer=True),
        },
    ),
    result=object_schema(
        {"node_types": array_schema(NODE_TYPE_ROW), "total": number_schema(integer=True)},
        additional=True,
    ),
    mcp_tool="catalog_list_node_types",
)

DESCRIBE_NODE_TYPE = OpSpec(
    name="catalog.describe_node_type",
    domain=DOMAIN,
    summary="Describe one node type: ports, properties (types, enums, defaults), sizing, collapsible/resizable flags.",
    description="Unknown ids return UNKNOWN_NODE_TYPE with close suggestions in details.suggestions.",
    params=object_schema({"type_id": TYPE_ID}, required=("type_id",)),
    result=object_schema(
        {
            "type_id": TYPE_ID,
            "display_name": string_schema(),
            "category_path": array_schema(string_schema()),
            "description": string_schema(),
            "runtime_behavior": string_schema(),
            "surface_family": string_schema(),
            "surface_variant": string_schema(),
            "collapsible": boolean_schema(),
            "resizable": boolean_schema(),
            "default_size": object_schema({"width": number_schema(), "height": number_schema()}, additional=True),
            "min_size": object_schema({"width": number_schema(), "height": number_schema()}, additional=True),
            "ports": array_schema(PORT_SUMMARY),
            "properties": array_schema(
                object_schema(
                    {
                        "key": string_schema(),
                        "type": string_schema(),
                        "label": string_schema(),
                        "default": any_schema(),
                        "enum_values": array_schema(string_schema()),
                        "minimum": any_schema(),
                        "maximum": any_schema(),
                        "description": string_schema(),
                        "expose_port_toggle": boolean_schema(),
                        "inspector_visible": boolean_schema(),
                    },
                    additional=True,
                )
            ),
            "keywords": array_schema(string_schema()),
        },
        additional=True,
    ),
    mcp_tool="catalog_describe_node_type",
)

STYLE_SCHEMA = OpSpec(
    name="catalog.style_schema",
    domain=DOMAIN,
    summary="Return the authoritative node-style, edge-style, and text-style key sets, enums, and saved presets.",
    description="Use the returned keys with node.set_style, edge.update, and node.add_text style params.",
    params=object_schema({}),
    result=object_schema(
        {
            "node_style": object_schema({}, additional=True),
            "edge_style": object_schema({}, additional=True),
            "text_style": object_schema({}, additional=True),
            "presets": object_schema(
                {
                    "node": array_schema(object_schema({}, additional=True)),
                    "edge": array_schema(object_schema({}, additional=True)),
                },
                additional=True,
            ),
        },
        additional=True,
    ),
    mcp_tool="catalog_style_schema",
)

OPS: tuple[OpSpec, ...] = (LIST_NODE_TYPES, DESCRIBE_NODE_TYPE, STYLE_SCHEMA)

__all__ = ["DESCRIBE_NODE_TYPE", "DOMAIN", "LIST_NODE_TYPES", "OPS", "STYLE_SCHEMA"]
