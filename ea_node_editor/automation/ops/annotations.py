# Purpose: Annotation op specs: node comments and node links.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_catalog.py
from __future__ import annotations

from ea_node_editor.automation.op_model import (
    OpSpec,
    boolean_schema,
    number_schema,
    object_schema,
    string_schema,
)
from ea_node_editor.automation.ops.common import NODE_ID

DOMAIN = "annotations"

COMMENT_UPSERT = OpSpec(
    name="comment.upsert",
    domain=DOMAIN,
    summary="Add or edit a comment on a node (threaded via parent_id; resolved/pinned flags).",
    params=object_schema(
        {
            "node_id": NODE_ID,
            "body": string_schema("Comment text (markdown)", min_length=1),
            "comment_id": string_schema("Existing comment id to edit; omit to create"),
            "author": string_schema("Author label; new comments default to 'automation', edits keep the stored author"),
            "parent_id": string_schema("Parent comment id for replies (must exist on the same node; fixed once set)"),
            "resolved": boolean_schema("New comments default to false; omit on edit to keep the current value"),
            "pinned": boolean_schema("New comments default to false; omit on edit to keep the current value"),
        },
        required=("node_id", "body"),
    ),
    result=object_schema({"comment_id": string_schema(), "comment": object_schema({}, additional=True)}, additional=True),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("node_id",),
    primary_id_field="comment_id",
    mcp_tool="comment_upsert",
)

COMMENT_REMOVE = OpSpec(
    name="comment.remove",
    domain=DOMAIN,
    summary="Remove a comment from a node.",
    params=object_schema({"node_id": NODE_ID, "comment_id": string_schema(min_length=1)}, required=("node_id", "comment_id")),
    result=object_schema({"removed": boolean_schema()}, additional=True),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("node_id",),
    mcp_tool="comment_remove",
)

LINK_UPSERT = OpSpec(
    name="link.upsert",
    domain=DOMAIN,
    summary="Add or edit a link on a node: url, file, folder, workspace, or node targets; optional ordering position.",
    params=object_schema(
        {
            "node_id": NODE_ID,
            "kind": string_schema(enum=("url", "file", "folder", "workspace", "node")),
            "title": string_schema(min_length=1),
            "target": string_schema("URL / path / workspace id / node id depending on kind"),
            "link_id": string_schema("Existing link id to edit; omit to create"),
            "subtitle": string_schema(),
            "target_workspace_id": string_schema("For kind=node: the workspace that owns target_node_id"),
            "target_node_id": string_schema("For kind=node"),
            "position": number_schema("Zero-based index in the node's link list", minimum=0, integer=True),
        },
        required=("node_id", "kind", "title"),
    ),
    result=object_schema({"link_id": string_schema(), "link": object_schema({}, additional=True)}, additional=True),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("node_id", "target_node_id"),
    primary_id_field="link_id",
    mcp_tool="link_upsert",
)

LINK_REMOVE = OpSpec(
    name="link.remove",
    domain=DOMAIN,
    summary="Remove a link from a node.",
    params=object_schema({"node_id": NODE_ID, "link_id": string_schema(min_length=1)}, required=("node_id", "link_id")),
    result=object_schema({"removed": boolean_schema()}, additional=True),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("node_id",),
    mcp_tool="link_remove",
)

OPS: tuple[OpSpec, ...] = (COMMENT_UPSERT, COMMENT_REMOVE, LINK_UPSERT, LINK_REMOVE)

__all__ = ["COMMENT_REMOVE", "COMMENT_UPSERT", "DOMAIN", "LINK_REMOVE", "LINK_UPSERT", "OPS"]
