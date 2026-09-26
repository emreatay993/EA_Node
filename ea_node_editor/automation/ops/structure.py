# Purpose: Structure op specs: group backdrops, swimlane pools and lanes, subnodes (create/ungroup/pins), scope navigation, selection, layout (arrange + straighten + tidy).
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
from ea_node_editor.automation.ops.common import COORD, EDGE_ID, NODE_ID, TITLE

DOMAIN = "structure"

GROUP_WRAP = OpSpec(
    name="group.wrap",
    domain=DOMAIN,
    summary="Wrap nodes in a Group backdrop (passive.annotation.group_backdrop) with an optional title.",
    description=(
        "An expanded Group owns the nodes inside its area (moving a node in or out changes membership); a collapsed "
        "Group keeps exactly the members it had when it was collapsed, nodes placed over its hidden area stay outside "
        "it, and expanding it makes room around it. The backdrop is sized around the given nodes; moving it (node_update "
        "x/y, or a canvas drag) moves them, nested Groups included. Hidden nodes cannot be wrapped."
    ),
    params=object_schema({"node_ids": id_list_schema("Nodes to wrap"), "title": TITLE}, required=("node_ids",)),
    result=object_schema({"group_node_id": NODE_ID, "member_node_ids": array_schema(NODE_ID)}, additional=True),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("node_ids[]",),
    primary_id_field="group_node_id",
    mcp_tool="group_wrap",
)

# Restated from ea_node_editor/nodes/builtins/passive_annotation.py (SWIMLANE_ORIENTATIONS) and
# ea_node_editor/graph/swimlane_layout.py (lane and pool size limits) so the op catalog never imports the graph
# package; tests/automation/test_catalog.py keeps them in sync.
SWIMLANE_ORIENTATIONS = ("horizontal", "vertical")
SWIMLANE_MIN_LANE_SIZE = 120
SWIMLANE_MIN_POOL_LENGTH = 360

SWIMLANE_LANE = object_schema(
    {
        "lane_node_id": NODE_ID,
        "title": string_schema("The lane's role name"),
        "node_ids": array_schema(NODE_ID, "What the lane holds directly (a Group counts once)"),
        "contained_node_ids": array_schema(NODE_ID, "Everything inside the lane, Group members included"),
    },
    additional=True,
)
SWIMLANE_POOL = object_schema(
    {
        "pool_node_id": NODE_ID,
        "title": string_schema(),
        "orientation": string_schema(enum=SWIMLANE_ORIENTATIONS),
        "collapsed": boolean_schema("A collapsed pool is listed without lanes"),
        "lane_node_ids": array_schema(NODE_ID, "Lanes in stack order (top to bottom, or left to right)"),
        "lanes": array_schema(SWIMLANE_LANE),
    },
    additional=True,
)

SWIMLANE_CREATE_POOL = OpSpec(
    name="swimlane.create_pool",
    domain=DOMAIN,
    summary="Add a swimlane pool with its role lanes (passive.annotation.swimlane_pool / swimlane_lane).",
    description=(
        "Lanes are Group backdrops stacked in the pool: a node placed in a lane belongs to it, and moving a lane "
        "moves what it holds. horizontal (default): lanes are rows, the pool's title band is on the left and the flow "
        "runs left to right; vertical: lanes are columns and the flow runs top to bottom. Lanes resize together: "
        "they share the pool's length, a lane grows (pushing the lanes after it) to fit what it holds, and a lane "
        "never shrinks past its contents. Place nodes with swimlane_assign (or node_add inside a lane's rectangle), "
        "then layout_tidy the pool for layers along the flow with one row per lane. Rename a lane with "
        "node_update(title=...); change the orientation with node_update(properties={'orientation': ...})."
    ),
    params=object_schema(
        {
            "x": COORD,
            "y": COORD,
            "title": TITLE,
            "orientation": string_schema(
                "horizontal: lanes are rows, flow left to right; vertical: lanes are columns, flow top to bottom",
                enum=SWIMLANE_ORIENTATIONS,
                default=SWIMLANE_ORIENTATIONS[0],
            ),
            "lanes": array_schema(
                string_schema("Role name"),
                "One role name per lane, in stack order (default: three lanes named Lane 1..3)",
                min_items=1,
                max_items=24,
            ),
            "lane_size": number_schema(
                "Lane thickness across the flow in px (default 200)", minimum=SWIMLANE_MIN_LANE_SIZE, maximum=4000
            ),
            "length": number_schema(
                "Pool length along the flow in px, title band included (default 1200)",
                minimum=SWIMLANE_MIN_POOL_LENGTH,
                maximum=20000,
            ),
        },
        required=("x", "y"),
    ),
    result=object_schema(
        {"pool_node_id": NODE_ID, "lane_node_ids": array_schema(NODE_ID), "pool": SWIMLANE_POOL},
        additional=True,
    ),
    mutates_graph=True,
    apply_allowed=True,
    primary_id_field="pool_node_id",
    mcp_tool="swimlane_create_pool",
    examples=({"x": 0, "y": 0, "title": "Order to delivery", "lanes": ["Customer", "Sales", "Warehouse"]},),
)

SWIMLANE_ADD_LANE = OpSpec(
    name="swimlane.add_lane",
    domain=DOMAIN,
    summary="Add a lane to a swimlane pool at a stack position (default: after the last lane).",
    description="The lanes after the new one move on with what they hold, and the pool grows.",
    params=object_schema(
        {
            "pool_node_id": NODE_ID,
            "title": string_schema("The new lane's role name"),
            "index": number_schema("Stack position, 0 = first (default: last)", minimum=0, integer=True),
        },
        required=("pool_node_id",),
    ),
    result=object_schema({"lane_node_id": NODE_ID, "lane_node_ids": array_schema(NODE_ID)}, additional=True),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("pool_node_id",),
    primary_id_field="lane_node_id",
    mcp_tool="swimlane_add_lane",
)

SWIMLANE_REMOVE_LANE = OpSpec(
    name="swimlane.remove_lane",
    domain=DOMAIN,
    summary="Remove a lane from its pool; the lane before it (else after it) takes its band and what it held.",
    description="Nothing else moves and the pool keeps its size; the removed lane's nodes stay (in the neighbour).",
    params=object_schema({"lane_node_id": NODE_ID}, required=("lane_node_id",)),
    result=object_schema({"removed_lane_node_id": NODE_ID, "lane_node_ids": array_schema(NODE_ID)}, additional=True),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("lane_node_id",),
    mcp_tool="swimlane_remove_lane",
)

SWIMLANE_MOVE_LANE = OpSpec(
    name="swimlane.move_lane",
    domain=DOMAIN,
    summary="Move a lane to another stack position in its pool; every lane keeps what it holds.",
    params=object_schema(
        {"lane_node_id": NODE_ID, "index": number_schema("Target stack position, 0 = first", minimum=0, integer=True)},
        required=("lane_node_id", "index"),
    ),
    result=object_schema({"lane_node_ids": array_schema(NODE_ID, "Lanes in their new stack order")}, additional=True),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("lane_node_id",),
    mcp_tool="swimlane_move_lane",
)

SWIMLANE_ASSIGN = OpSpec(
    name="swimlane.assign",
    domain=DOMAIN,
    summary="Move nodes into a lane: placed after what the lane holds along the flow, centred across the lane.",
    description=(
        "The lane (and pool) grow to fit. A Group moves with its members. Run layout_tidy on the pool afterwards for "
        "layers along the flow. Hidden members of a collapsed Group, pools and lanes cannot be assigned."
    ),
    params=object_schema(
        {"node_ids": id_list_schema("Nodes to move into the lane"), "lane_node_id": NODE_ID},
        required=("node_ids", "lane_node_id"),
    ),
    result=object_schema(
        {"assigned_node_ids": array_schema(NODE_ID), "lane_node_id": NODE_ID, "pool": SWIMLANE_POOL},
        additional=True,
    ),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("node_ids[]", "lane_node_id"),
    mcp_tool="swimlane_assign",
)

SWIMLANE_DESCRIBE = OpSpec(
    name="swimlane.describe",
    domain=DOMAIN,
    summary="List the swimlane pools of the open scope: orientation, lanes in stack order and what each lane holds.",
    params=object_schema({"pool_node_id": string_schema("Only this pool (default: every pool)", min_length=1)}),
    result=object_schema({"pools": array_schema(SWIMLANE_POOL)}, additional=True),
    mutates_graph=False,
    apply_allowed=True,
    ref_fields=("pool_node_id",),
    mcp_tool="swimlane_describe",
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

# Restated from ea_node_editor/graph/transform_tidy_layout.py (TIDY_MODES, TIDY_DIRECTIONS, DEFAULT_TIDY_*_GAP) so the
# op catalog never imports the graph package; tests/automation/test_catalog.py keeps the two in sync.
TIDY_MODES = ("auto_layout", "in_place")
TIDY_DIRECTIONS = ("auto", "left_to_right", "top_to_bottom")
DEFAULT_TIDY_COLUMN_GAP = 96
DEFAULT_TIDY_ROW_GAP = 64
# locked_group: the node is, or sits in, a Group backdrop that Tidy may not move or grow because that Group (or a
# node inside it) is locked.
TIDY_NODE_SKIP_REASONS = (*NODE_SKIP_REASONS, "locked_group")

LAYOUT_TIDY = OpSpec(
    name="layout.tidy",
    domain=DOMAIN,
    summary=(
        "Tidy nodes: auto-layout from the wires (left to right / top to bottom) or clean up in place, "
        "keeping Group backdrops intact and laying swimlane pools out lane by lane."
    ),
    description=(
        "Omit node_ids to tidy every node in the open scope. auto_layout rebuilds the arrangement from the wires "
        "(direction auto-detected from the port sides they use, or forced with left_to_right / top_to_bottom): rows "
        "and columns are centered so right->left and bottom->top wires run straight, loop-back wires stay elbows "
        "(loop_edge_ids), and the block keeps its current top-left; in_place keeps the arrangement and snaps "
        "near-aligned rows and columns onto shared center lines with even gaps. Group backdrops stay intact: a "
        "listed backdrop's members are laid out inside it and the backdrop is refitted, a collapsed Group moves as "
        "one block with its hidden members and is laid out at its collapsed size at every level, and an unlisted "
        "backdrop grows to keep listed members; when the result would still move a node "
        "into or out of a Group nothing changes and the call fails with NO_EFFECT "
        "(details.membership_conflict_node_ids). A swimlane pool (listed, or pulled in by one of its lanes) is laid "
        "out as one unit along its own flow (rows of a horizontal pool, columns of a vertical one): steps share "
        "layer columns across every lane, each lane is one row (two steps of one lane in the same layer stack), and "
        "the lanes are resized to what they hold. Locked nodes (unless the 'interact with locked objects' preference "
        "is on), members of a collapsed Group, nodes outside an open comment peek, Groups that hold a locked node "
        "(with their contents), and nodes whose locked Group would have to grow are left alone and listed in "
        "skipped_nodes (the last two as locked_group); the new block steps around locked nodes and those Groups, "
        "and unwired annotations are never re-arranged. Other nodes the new block would overlap are pushed aside "
        "(pushed_node_ids) while the 'Avoid overlaps when expanding collapsed items' graphics setting is on (the "
        "default). Read straightened_edge_ids, skipped_edges, and overlapping_node_pairs afterwards; changed=false "
        "means the nodes were already tidy."
    ),
    params=object_schema(
        {
            "node_ids": id_list_schema(
                "Nodes to tidy (default: every node in the open scope); one Group or swimlane pool tidies what it holds"
            ),
            "mode": string_schema(
                "auto_layout rebuilds the arrangement from the wires; in_place keeps it and straightens rows and columns",
                enum=TIDY_MODES,
                default=TIDY_MODES[0],
            ),
            "direction": string_schema(
                "Flow direction for auto_layout; auto detects it from the port sides the wires use (in_place ignores it)",
                enum=TIDY_DIRECTIONS,
                default=TIDY_DIRECTIONS[0],
            ),
            "column_gap": number_schema(
                "Gap in px between steps along the flow (in_place: between columns, the median current gap clamped "
                "to 1x..3x this value)",
                minimum=24,
                maximum=400,
                default=DEFAULT_TIDY_COLUMN_GAP,
            ),
            "row_gap": number_schema(
                "Gap in px between rows across the flow (in_place: between rows, the median current gap clamped to "
                "1x..3x this value)",
                minimum=16,
                maximum=400,
                default=DEFAULT_TIDY_ROW_GAP,
            ),
        },
    ),
    result=object_schema(
        {
            "moved_node_ids": array_schema(NODE_ID, "Tidied nodes that moved, incl. the hidden members of a moved collapsed Group"),
            "resized_group_ids": array_schema(NODE_ID, "Group backdrops refitted or grown around their members"),
            "pushed_node_ids": array_schema(NODE_ID, "Other nodes moved out of the way of the new block"),
            "skipped_nodes": array_schema(
                object_schema({"node_id": NODE_ID, "reason": string_schema(enum=TIDY_NODE_SKIP_REASONS)}, additional=True),
                "Nodes Tidy left alone, with the reason",
            ),
            "loop_edge_ids": array_schema(EDGE_ID, "Loop-back wires kept as elbows"),
            "membership_conflict_node_ids": array_schema(NODE_ID, "Empty on success; a conflict fails with NO_EFFECT"),
            "straightened_edge_ids": array_schema(EDGE_ID, "Wires between laid-out nodes that now run straight"),
            "skipped_edges": array_schema(
                object_schema(
                    {
                        "edge_id": EDGE_ID,
                        "reason": string_schema(enum=("mixed_port_sides", "unresolved_offset", "not_drawn")),
                        "source_side": string_schema(),
                        "target_side": string_schema(),
                        "offset": {"type": "number"},
                    },
                    additional=True,
                ),
                "Wires between laid-out nodes that are not straight (elbows, loops, remaining offsets)",
            ),
            "overlapping_node_pairs": array_schema(
                array_schema(NODE_ID), "Overlapping pairs of drawn nodes in the scope that involve a tidied or pushed node"
            ),
            "direction": string_schema("left_to_right or top_to_bottom as applied; empty for in_place"),
            "mode": string_schema(enum=TIDY_MODES),
        },
        additional=True,
    ),
    mutates_graph=True,
    apply_allowed=True,
    ref_fields=("node_ids[]",),
    mcp_tool="layout_tidy",
)

OPS: tuple[OpSpec, ...] = (
    GROUP_WRAP,
    SWIMLANE_CREATE_POOL,
    SWIMLANE_ADD_LANE,
    SWIMLANE_REMOVE_LANE,
    SWIMLANE_MOVE_LANE,
    SWIMLANE_ASSIGN,
    SWIMLANE_DESCRIBE,
    SUBNODE_CREATE,
    SUBNODE_UNGROUP,
    SUBNODE_ADD_PIN,
    SCOPE_NAVIGATE,
    SELECTION_SET,
    LAYOUT_ARRANGE,
    LAYOUT_STRAIGHTEN,
    LAYOUT_TIDY,
)

__all__ = [
    "DEFAULT_TIDY_COLUMN_GAP",
    "DEFAULT_TIDY_ROW_GAP",
    "DOMAIN",
    "EDGE_SKIP_REASONS",
    "GROUP_WRAP",
    "LAYOUT_ARRANGE",
    "LAYOUT_STRAIGHTEN",
    "LAYOUT_TIDY",
    "NODE_SKIP_REASONS",
    "OPS",
    "SCOPE_NAVIGATE",
    "SELECTION_SET",
    "SUBNODE_ADD_PIN",
    "SUBNODE_CREATE",
    "SUBNODE_UNGROUP",
    "SWIMLANE_ADD_LANE",
    "SWIMLANE_ASSIGN",
    "SWIMLANE_CREATE_POOL",
    "SWIMLANE_DESCRIBE",
    "SWIMLANE_MIN_LANE_SIZE",
    "SWIMLANE_MIN_POOL_LENGTH",
    "SWIMLANE_MOVE_LANE",
    "SWIMLANE_ORIENTATIONS",
    "SWIMLANE_REMOVE_LANE",
    "TIDY_DIRECTIONS",
    "TIDY_MODES",
    "TIDY_NODE_SKIP_REASONS",
]
