# Purpose: Read-only graph op specs: whole-graph snapshot, single node detail, node search.
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
from ea_node_editor.automation.ops.common import (
    EDGE_SUMMARY,
    NODE_ID,
    NODE_SUMMARY,
    PORT_SUMMARY,
    TYPE_ID,
    WORKSPACE_ID,
)

DOMAIN = "graph"

GET = OpSpec(
    name="graph.get",
    domain=DOMAIN,
    summary="Snapshot the active workspace: nodes, edges, views, scope, selection (optionally styles/properties).",
    description=(
        "scope=active (default) returns only nodes visible in the open scope; scope=all returns every node "
        "with parent_node_id so you can reason about subnodes."
    ),
    params=object_schema(
        {
            "workspace_id": string_schema("Defaults to the active workspace; other ids raise WRONG_WORKSPACE"),
            "scope": string_schema(enum=("active", "all"), default="active"),
            "include_style": boolean_schema(default=False),
            "include_properties": boolean_schema(default=False),
        },
    ),
    result=object_schema(
        {
            "workspace_id": WORKSPACE_ID,
            "workspace_name": string_schema(),
            "dirty": boolean_schema(),
            "scope_path": array_schema(string_schema()),
            "active_view_id": string_schema(),
            "views": array_schema(object_schema({"view_id": string_schema(), "name": string_schema(), "active": boolean_schema()}, additional=True)),
            "nodes": array_schema(NODE_SUMMARY),
            "edges": array_schema(EDGE_SUMMARY),
            "selected_node_ids": array_schema(string_schema()),
        },
        additional=True,
    ),
    mcp_tool="graph_get",
)

GET_NODE = OpSpec(
    name="graph.get_node",
    domain=DOMAIN,
    summary="Full detail for one node: geometry, properties, style, effective ports with connections, links, comments.",
    params=object_schema({"node_id": NODE_ID}, required=("node_id",)),
    result=object_schema(
        {
            "node": NODE_SUMMARY,
            "properties": object_schema({}, additional=True),
            "visual_style": object_schema({}, additional=True),
            "port_labels": object_schema({}, additional=True),
            "exposed_ports": object_schema({}, additional=True),
            "ports": array_schema(PORT_SUMMARY),
            "incident_edges": array_schema(EDGE_SUMMARY),
            "links": array_schema(object_schema({}, additional=True)),
            "comments": array_schema(object_schema({}, additional=True)),
            "in_active_scope": boolean_schema(),
        },
        additional=True,
    ),
    mcp_tool="graph_get_node",
)

FIND_NODES = OpSpec(
    name="graph.find_nodes",
    domain=DOMAIN,
    summary="Find nodes in the active workspace by title text, exact type id, or free-text query.",
    params=object_schema(
        {
            "query": string_schema("Case-insensitive match on title, type id, display name"),
            "type_id": TYPE_ID,
            "title": string_schema("Exact title match"),
            "title_contains": string_schema("Case-insensitive substring of the title"),
            "scope": string_schema(enum=("active", "all"), default="all"),
            "limit": number_schema(minimum=1, maximum=1000, default=100, integer=True),
        },
    ),
    result=object_schema(
        {"nodes": array_schema(NODE_SUMMARY), "total": number_schema(integer=True)},
        additional=True,
    ),
    mcp_tool="graph_find_nodes",
)

OPS: tuple[OpSpec, ...] = (GET, GET_NODE, FIND_NODES)

__all__ = ["DOMAIN", "FIND_NODES", "GET", "GET_NODE", "OPS", "any_schema"]
