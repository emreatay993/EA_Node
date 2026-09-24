# Purpose: Structure op specs: group backdrops, subnodes (create/ungroup/pins), scope navigation, selection, layout (arrange + straighten).
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
from ea_node_editor.automation.ops.common import EDGE_ID, NODE_ID, TITLE

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

NODE_SKIP_REASONS = ("locked_node", "hidden_in_collapsed_group", "not_selectable")
EDGE_SKIP_REASONS = ("mixed_port_sides", "unresolved_offset", *NODE_SKIP_REASONS, "not_drawn")
SKIPPED_NODE = object_schema({"node_id": NODE_ID, "reason": string_schema(enum=NODE_SKIP_REASONS)}, additional=True)

LAYOUT_ARRANGE = OpSpec(
    name="layout.arrange",
    domain=DOMAIN,
    summary=(
        "Align, distribute, or match the size of a set of nodes (align left/right/top/bottom/center_x/center_y, "
        "distribute horizontal/vertical, match_width/match_height)."
    ),
    description=(
        "align_left/right/top/bottom line nodes up with the outermost edge; align_center_y gives every node the "
        "vertical center of their combined bounds (a row whose side ports line up), align_center_x the horizontal "
        "center (a centered column). distribute_* needs 3+ nodes and keeps the outer two in place. "
        "match_width/match_height resize passive nodes of the same type_id to the first listed node of that type. "
        "snap_to_grid applies to align_left/right/top/bottom and distribute_* only. Locked nodes (unless the "
        "'interact with locked objects' preference is on), members of a collapsed Group, and nodes outside an open "
        "comment peek are left alone and listed in skipped_nodes. Results list moved/resized ids and "
        "overlapping_node_pairs so you can distribute or nudge afterwards."
    ),
    params=object_schema(
        {
            "node_ids": id_list_schema("Two or more nodes", min_items=2),
            "action": string_schema(
                enum=(
                    "align_left",
                    "align_right",
                    "align_top",
                    "align_bottom",
                    "align_center_x",
                    "align_center_y",
                    "distribute_horizontal",
                    "distribute_vertical",
                    "match_width",
                    "match_height",
                )
            ),
            "snap_to_grid": boolean_schema(default=False),
        },
        required=("node_ids", "action"),
    ),
    result=object_schema(
        {
            "moved_node_ids": array_schema(NODE_ID),
            "resized_node_ids": array_schema(NODE_ID),
            "skipped_nodes": array_schema(SKIPPED_NODE, "Nodes the action left alone, with the reason"),
            "overlapping_node_pairs": array_schema(array_schema(NODE_ID), "Pairs of the given nodes whose bounds overlap afterwards"),
        },
        additional=True,
    ),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("node_ids[]",),
    mcp_tool="layout_arrange",
)

LAYOUT_STRAIGHTEN = OpSpec(
    name="layout.straighten",
    domain=DOMAIN,
    summary="Move nodes so the wires between them run straight (the Straighten Connections action).",
    description=(
        "Omit node_ids and edge_ids to straighten every wire in the open scope; edge_ids add their endpoint nodes. "
        "A wire can be straightened when both ends sit on horizontal sides (right->left) or both on vertical sides "
        "(bottom->top). Only the given nodes move. Each connected set of wires is solved per axis and re-centred on "
        "its median offset so it does not drift; a set whose wires need contradictory offsets is not moved on that "
        "axis. Read straightened_edge_ids and skipped_edges: mixed_port_sides = an elbow such as right->top; "
        "unresolved_offset = the ends still differ by offset px (contradictory wires in the set, or a data-node "
        "port drawn away from its layout anchor); locked_node / hidden_in_collapsed_group / not_selectable = an "
        "end the scene would not move. Check overlapping_node_pairs in case straightening stacked nodes."
    ),
    params=object_schema(
        {
            "node_ids": id_list_schema("Nodes whose wires to straighten (default: every node in the open scope)"),
            "edge_ids": id_list_schema("Wires to straighten; their endpoint nodes join node_ids"),
        },
    ),
    result=object_schema(
        {
            "moved_node_ids": array_schema(NODE_ID),
            "straightened_edge_ids": array_schema(EDGE_ID),
            "skipped_edges": array_schema(
                object_schema(
                    {
                        "edge_id": EDGE_ID,
                        "reason": string_schema(enum=EDGE_SKIP_REASONS),
                        "source_side": string_schema(),
                        "target_side": string_schema(),
                        "node_id": NODE_ID,
                        "offset": {"type": "number"},
                    },
                    additional=True,
                )
            ),
            "overlapping_node_pairs": array_schema(array_schema(NODE_ID)),
        },
        additional=True,
    ),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("node_ids[]", "edge_ids[]"),
    mcp_tool="layout_straighten",
)

OPS: tuple[OpSpec, ...] = (
    GROUP_WRAP,
    SUBNODE_CREATE,
    SUBNODE_UNGROUP,
    SUBNODE_ADD_PIN,
    SCOPE_NAVIGATE,
    SELECTION_SET,
    LAYOUT_ARRANGE,
    LAYOUT_STRAIGHTEN,
)

__all__ = [
    "DOMAIN",
    "EDGE_SKIP_REASONS",
    "GROUP_WRAP",
    "LAYOUT_ARRANGE",
    "LAYOUT_STRAIGHTEN",
    "NODE_SKIP_REASONS",
    "OPS",
    "SCOPE_NAVIGATE",
    "SELECTION_SET",
    "SUBNODE_ADD_PIN",
    "SUBNODE_CREATE",
    "SUBNODE_UNGROUP",
]
