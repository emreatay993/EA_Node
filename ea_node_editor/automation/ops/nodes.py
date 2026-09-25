# Purpose: Node op specs: add (generic/text/media/web), update, style, text fit, delete, duplicate.
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
    summary="Create a web viewer (web.page_viewer) for a URL, or for inline HTML written to a session scratch file.",
    description=(
        "Inline html is written to the project's session staging folder (<staging>/automation/<uuid>.html) "
        "and opened as a file:// URL. It is NOT packed into the .cxproj on save and is lost with the session "
        "(a private instance deletes it on close). For durable content pass url pointing at a file you own, "
        "or copy the file in with project.stage_file and pass its artifact_ref (temp://...) as url; the save "
        "then packs it into the project (a file:// URL of staged_path is not packed). "
        "Web content is not rendered in offscreen (private headless) screenshots."
    ),
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
        "Properties driven by a connected/exposed port return PROPERTY_LOCKED_BY_PORT. Expanding makes room: "
        "neighbours move aside and parent Groups grow; it fails with NO_EFFECT when a locked Group would have to grow "
        "or no room exists. Moving a Group backdrop (x/y) moves everything inside it by the same amount, nested Groups "
        "and locked nodes included, like dragging it on the canvas; carried_node_ids lists those nodes, so do not move "
        "them yourself. move_contents=false moves or reshapes only an expanded Group's frame (like its corner handles): "
        "the nodes stay, so it can grow up or left around nodes. A collapsed Group always carries what it holds."
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
            "move_contents": boolean_schema(
                "Group backdrops only: false moves/reshapes the expanded frame without the nodes inside",
                default=True,
            ),
        },
        required=("node_id",),
    ),
    result=object_schema(
        {
            "node_id": NODE_ID,
            "changed": CHANGED_FIELDS,
            "node": NODE_SUMMARY,
            "carried_node_ids": array_schema(NODE_ID, "Nodes a Group move carried along (empty otherwise)"),
        },
        additional=True,
    ),
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
        "propagate=true copies the node's style to the passive nodes connected to it by edges (result "
        "propagated_to lists them). Non-passive nodes return NOT_PASSIVE; keys come from catalog.style_schema."
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

TEXT_FIT_MODES = ("clip", "grow", "shrink")
TEXT_FIT_REPORT = object_schema(
    {
        "mode": string_schema("Stored properties.body_fit", enum=TEXT_FIT_MODES),
        "overflowing": boolean_schema("True while the body text is still clipped"),
        "overflow_mark": string_schema(
            "How clipped text is marked: elide (last line ends in an ellipsis), pill (markdown), or empty",
            enum=("", "elide", "pill"),
        ),
        "font_size": number_schema("Style font size in px", integer=True),
        "rendered_font_size": number_schema("Drawn font size in px (smaller under shrink)", integer=True),
        "aspect_locked": boolean_schema("Square shapes grow in both directions, keeping their aspect ratio"),
    },
    additional=True,
)

FIT_TEXT = OpSpec(
    name="node.fit_text",
    domain=DOMAIN,
    summary="Set a flowchart shape's text fit (clip, grow, shrink) and report how its body text fits once drawn.",
    description=(
        "Every flowchart shape except timestamp stores the mode in properties.body_fit. clip keeps the size and "
        "ends clipped text in an ellipsis; grow enlarges the shape until the body fits (square shapes such as "
        "connector keep their aspect ratio); shrink lowers the font, to 6 px at the smallest, until it fits. "
        "The canvas measures the text, so the shape must be drawn: the op waits up to timeout_s for that (frame an "
        "off-screen shape with view.set_camera first) and applies the mode and any growth as one undo step. "
        "Omit mode to only report the current fit. A still-true overflowing means the text cannot fit this way: "
        "shorten it, widen the shape, or pick another mode."
    ),
    params=object_schema(
        {
            "node_id": NODE_ID,
            "mode": string_schema("Text fit mode; omit to only report", enum=TEXT_FIT_MODES),
            "timeout_s": number_schema("Seconds to wait for the canvas to draw the shape", minimum=0, maximum=120, default=5),
        },
        required=("node_id",),
    ),
    result=object_schema(
        {
            "node_id": NODE_ID,
            "changed": CHANGED_FIELDS,
            "node": NODE_SUMMARY,
            "text_fit": TEXT_FIT_REPORT,
        },
        additional=True,
    ),
    mutates_graph=True,
    deferred=True,
    ref_fields=("node_id",),
    primary_id_field="node_id",
    mcp_tool="node_fit_text",
    examples=({"node_id": "node_12", "mode": "grow"},),
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

OPS: tuple[OpSpec, ...] = (ADD, ADD_TEXT, ADD_MEDIA, ADD_WEB_PANEL, UPDATE, SET_STYLE, FIT_TEXT, DELETE, DUPLICATE)

__all__ = [
    "ADD",
    "ADD_MEDIA",
    "ADD_TEXT",
    "ADD_WEB_PANEL",
    "DELETE",
    "DOMAIN",
    "DUPLICATE",
    "FIT_TEXT",
    "OPS",
    "SET_STYLE",
    "TEXT_FIT_MODES",
    "TEXT_FIT_REPORT",
    "UPDATE",
]
