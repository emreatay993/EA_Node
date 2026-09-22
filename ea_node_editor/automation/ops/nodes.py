# Purpose: Node op specs: add (generic/text/media/web), update, style, delete, duplicate.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_catalog.py
from __future__ import annotations

from ea_node_editor.automation.op_model import (
    OpSpec,
    array_schema,
    boolean_schema,
    id_list_schema,
    number_schema,
    object_schema,
    string_schema,
)
from ea_node_editor.automation.ops.common import (
    CHANGED_FIELDS,
    COORD,
    NODE_ID,
    NODE_STYLE,
    NODE_SUMMARY,
    SIZE,
    TEXT_STYLE,
    TITLE,
    TYPE_ID,
)

DOMAIN = "node"

_PLACEMENT = {
    "x": COORD,
    "y": COORD,
    "title": TITLE,
    "width": SIZE,
    "height": SIZE,
    "parent_node_id": string_schema("Create inside this subnode shell (must be the open scope)"),
    "select": boolean_schema("Select the new node after creation", default=False),
}

ADD = OpSpec(
    name="node.add",
    domain=DOMAIN,
    summary="Create a node of any registered type at (x, y) with optional title, size, and property overrides.",
    description=(
        "Use catalog.describe_node_type first for property keys. Flowchart shapes: passive.flowchart.start|"
        "process|decision|end|document|database|input_output|connector|... Path pointer: io.path_pointer "
        "(properties.path, properties.mode=file|folder). Panel: data.panel."
    ),
    params=object_schema(
        {
            "type_id": TYPE_ID,
            **_PLACEMENT,
            "properties": object_schema({}, additional=True, description="Property overrides validated by the registry"),
        },
        required=("type_id", "x", "y"),
    ),
    result=object_schema({"node_id": NODE_ID, "node": NODE_SUMMARY}, additional=True),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("parent_node_id",),
    primary_id_field="node_id",
    mcp_tool="node_add",
    examples=({"type_id": "passive.flowchart.process", "x": 320, "y": 120, "title": "Mesh the part"},),
)

ADD_TEXT = OpSpec(
    name="node.add_text",
    domain=DOMAIN,
    summary="Create a markdown text annotation (passive.annotation.text) with optional text style.",
    params=object_schema(
        {
            "markdown": string_schema("Body text; markdown by default", min_length=0),
            **_PLACEMENT,
            "format": string_schema(enum=("markdown", "plain"), default="markdown"),
            "style": TEXT_STYLE,
        },
        required=("markdown", "x", "y"),
    ),
    result=object_schema({"node_id": NODE_ID, "node": NODE_SUMMARY}, additional=True),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("parent_node_id",),
    primary_id_field="node_id",
    mcp_tool="node_add_text",
)

ADD_MEDIA = OpSpec(
    name="node.add_media",
    domain=DOMAIN,
    summary="Create a media panel (media.panel) showing an image, video, or PDF file; the file is staged into the project.",
    params=object_schema(
        {
            "path": string_schema("Absolute path to an image/video/PDF", min_length=1),
            **_PLACEMENT,
            "fit_mode": string_schema("Media fit mode (see catalog.describe_node_type media.panel)"),
            "show_title": boolean_schema(),
            "show_frame": boolean_schema(),
        },
        required=("path", "x", "y"),
    ),
    result=object_schema({"node_id": NODE_ID, "node": NODE_SUMMARY, "artifact_ref": string_schema()}, additional=True),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("parent_node_id",),
    primary_id_field="node_id",
    mcp_tool="node_add_media",
)

ADD_WEB_PANEL = OpSpec(
    name="node.add_web_panel",
    domain=DOMAIN,
    summary="Create a web viewer (web.page_viewer) for a URL, or for inline HTML that is staged as a project file.",
    description="Web content is not rendered in offscreen (private headless) screenshots.",
    params=object_schema(
        {
            "url": string_schema("http(s):// or file:// location"),
            "html": string_schema("Inline HTML document; staged under the project and opened as file://"),
            **_PLACEMENT,
            "display_mode": string_schema("web.page_viewer display mode enum"),
        },
        required=("x", "y"),
    ),
    result=object_schema({"node_id": NODE_ID, "node": NODE_SUMMARY, "url": string_schema()}, additional=True),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("parent_node_id",),
    primary_id_field="node_id",
    mcp_tool="node_add_web_panel",
)

UPDATE = OpSpec(
    name="node.update",
    domain=DOMAIN,
    summary="Update title, position, size, properties, port labels, exposed ports, collapsed, or locked on one node.",
    description=(
        "Only supplied fields change; the result lists what actually changed (NO_EFFECT when nothing did). "
        "Properties driven by a connected/exposed port return PROPERTY_LOCKED_BY_PORT."
    ),
    params=object_schema(
        {
            "node_id": NODE_ID,
            "title": TITLE,
            "x": COORD,
            "y": COORD,
            "width": SIZE,
            "height": SIZE,
            "properties": object_schema({}, additional=True),
            "port_labels": object_schema({}, additional=True, description="port_key -> label ('' clears)"),
            "exposed_ports": object_schema({}, additional=True, description="port_key -> bool"),
            "collapsed": boolean_schema(),
            "locked": boolean_schema(),
        },
        required=("node_id",),
    ),
    result=object_schema({"node_id": NODE_ID, "changed": CHANGED_FIELDS, "node": NODE_SUMMARY}, additional=True),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("node_id",),
    primary_id_field="node_id",
    mcp_tool="node_update",
)

SET_STYLE = OpSpec(
    name="node.set_style",
    domain=DOMAIN,
    summary="Set, merge, clear, or propagate a passive node's visual style (or apply a saved preset).",
    description=(
        "style merges into the current style unless replace=true; clear=true removes the override; "
        "propagate=true copies the node's style to same-type passive nodes. Non-passive nodes return NOT_PASSIVE."
    ),
    params=object_schema(
        {
            "node_id": NODE_ID,
            "style": NODE_STYLE,
            "preset": string_schema("Saved node preset id or name (see catalog.style_schema)"),
            "replace": boolean_schema(default=False),
            "clear": boolean_schema(default=False),
            "propagate": boolean_schema(default=False),
        },
        required=("node_id",),
    ),
    result=object_schema(
        {
            "node_id": NODE_ID,
            "visual_style": object_schema({}, additional=True),
            "propagated_to": array_schema(NODE_ID),
        },
        additional=True,
    ),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("node_id",),
    primary_id_field="node_id",
    mcp_tool="node_set_style",
)

DELETE = OpSpec(
    name="node.delete",
    domain=DOMAIN,
    summary="Delete one or more nodes (and their edges) from the active workspace.",
    params=object_schema({"node_ids": id_list_schema("Node ids to delete")}, required=("node_ids",)),
    result=object_schema(
        {"deleted_node_ids": array_schema(NODE_ID), "removed_edge_ids": array_schema(string_schema())},
        additional=True,
    ),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("node_ids[]",),
    mcp_tool="node_delete",
)

DUPLICATE = OpSpec(
    name="node.duplicate",
    domain=DOMAIN,
    summary="Duplicate a set of nodes (with internal edges) offset from the originals.",
    params=object_schema(
        {
            "node_ids": id_list_schema("Node ids to duplicate together"),
            "offset_x": number_schema(default=40),
            "offset_y": number_schema(default=40),
        },
        required=("node_ids",),
    ),
    result=object_schema(
        {
            "node_ids": array_schema(NODE_ID, "New node ids in the same order as the input"),
            "id_map": object_schema({}, additional=True, description="original id -> new id"),
        },
        additional=True,
    ),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("node_ids[]",),
    mcp_tool="node_duplicate",
)

OPS: tuple[OpSpec, ...] = (ADD, ADD_TEXT, ADD_MEDIA, ADD_WEB_PANEL, UPDATE, SET_STYLE, DELETE, DUPLICATE)

__all__ = [
    "ADD",
    "ADD_MEDIA",
    "ADD_TEXT",
    "ADD_WEB_PANEL",
    "DELETE",
    "DOMAIN",
    "DUPLICATE",
    "OPS",
    "SET_STYLE",
    "UPDATE",
]
