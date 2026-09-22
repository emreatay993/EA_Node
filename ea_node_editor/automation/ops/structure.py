# Purpose: Structure op specs: group backdrops, subnodes (create/ungroup/pins), scope navigation, selection, layout.
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
from ea_node_editor.automation.ops.common import NODE_ID, TITLE

DOMAIN = "structure"

GROUP_WRAP = OpSpec(
    name="group.wrap",
    domain=DOMAIN,
    summary="Wrap nodes in a Group backdrop (passive.annotation.group_backdrop) with an optional title.",
    description="Membership is geometric: the backdrop is sized around the given nodes; moving it moves them.",
    params=object_schema({"node_ids": id_list_schema("Nodes to wrap"), "title": TITLE}, required=("node_ids",)),
    result=object_schema({"group_node_id": NODE_ID, "member_node_ids": array_schema(NODE_ID)}, additional=True),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("node_ids[]",),
    primary_id_field="group_node_id",
    mcp_tool="group_wrap",
)

SUBNODE_CREATE = OpSpec(
    name="subnode.create",
    domain=DOMAIN,
    summary="Collapse nodes into a subnode shell (nested scope); boundary edges become input/output pins.",
    params=object_schema({"node_ids": id_list_schema("Nodes to move into the new subnode"), "title": TITLE}, required=("node_ids",)),
    result=object_schema(
        {
            "shell_node_id": NODE_ID,
            "input_pin_ids": array_schema(NODE_ID),
            "output_pin_ids": array_schema(NODE_ID),
            "member_node_ids": array_schema(NODE_ID),
        },
        additional=True,
    ),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("node_ids[]",),
    primary_id_field="shell_node_id",
    mcp_tool="subnode_create",
)

SUBNODE_UNGROUP = OpSpec(
    name="subnode.ungroup",
    domain=DOMAIN,
    summary="Dissolve a subnode shell, restoring its members to the current scope.",
    params=object_schema({"shell_node_id": NODE_ID}, required=("shell_node_id",)),
    result=object_schema({"restored_node_ids": array_schema(NODE_ID)}, additional=True),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("shell_node_id",),
    mcp_tool="subnode_ungroup",
)

SUBNODE_ADD_PIN = OpSpec(
    name="subnode.add_pin",
    domain=DOMAIN,
    summary="Add an input or output pin to a subnode shell.",
    params=object_schema(
        {"shell_node_id": NODE_ID, "direction": string_schema(enum=("in", "out"))},
        required=("shell_node_id", "direction"),
    ),
    result=object_schema({"pin_node_id": NODE_ID}, additional=True),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("shell_node_id",),
    primary_id_field="pin_node_id",
    mcp_tool="subnode_add_pin",
)

SCOPE_NAVIGATE = OpSpec(
    name="scope.navigate",
    domain=DOMAIN,
    summary="Open a subnode scope (target=node), go up one level (parent), or return to the root scope.",
    description="Graph ops act on the open scope; navigate before adding nodes inside a subnode.",
    params=object_schema(
        {
            "target": string_schema(enum=("root", "parent", "node")),
            "node_id": string_schema("Subnode shell id when target=node"),
        },
        required=("target",),
    ),
    result=object_schema({"scope_path": array_schema(NODE_ID)}, additional=True),
    mutates_graph=False,
    apply_allowed=True,
    ref_fields=("node_id",),
    mcp_tool="scope_navigate",
)

SELECTION_SET = OpSpec(
    name="selection.set",
    domain=DOMAIN,
    summary="Replace, extend, or clear the canvas selection.",
    params=object_schema(
        {
            "node_ids": array_schema(NODE_ID, "Nodes to select (ignored for mode=clear)"),
            "mode": string_schema(enum=("replace", "add", "clear"), default="replace"),
        },
    ),
    result=object_schema({"selected_node_ids": array_schema(NODE_ID)}, additional=True),
    mutates_graph=False,
    apply_allowed=True,
    ref_fields=("node_ids[]",),
    mcp_tool="selection_set",
)

LAYOUT_ARRANGE = OpSpec(
    name="layout.arrange",
    domain=DOMAIN,
    summary="Align or distribute a set of nodes (align left/right/top/bottom, distribute horizontal/vertical).",
    params=object_schema(
        {
            "node_ids": id_list_schema("Two or more nodes", min_items=2),
            "action": string_schema(
                enum=(
                    "align_left",
                    "align_right",
                    "align_top",
                    "align_bottom",
                    "distribute_horizontal",
                    "distribute_vertical",
                )
            ),
            "snap_to_grid": boolean_schema(default=False),
        },
        required=("node_ids", "action"),
    ),
    result=object_schema({"moved_node_ids": array_schema(NODE_ID)}, additional=True),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("node_ids[]",),
    mcp_tool="layout_arrange",
)

OPS: tuple[OpSpec, ...] = (
    GROUP_WRAP,
    SUBNODE_CREATE,
    SUBNODE_UNGROUP,
    SUBNODE_ADD_PIN,
    SCOPE_NAVIGATE,
    SELECTION_SET,
    LAYOUT_ARRANGE,
)

__all__ = [
    "DOMAIN",
    "GROUP_WRAP",
    "LAYOUT_ARRANGE",
    "OPS",
    "SCOPE_NAVIGATE",
    "SELECTION_SET",
    "SUBNODE_ADD_PIN",
    "SUBNODE_CREATE",
    "SUBNODE_UNGROUP",
]
