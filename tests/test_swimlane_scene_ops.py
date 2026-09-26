# Purpose: Offscreen scene tests for swimlane pools: lane membership (Group area rule), lane drags and reorder, lanes resizing together, lane commands, deletion and copy, collapse, orientation, one undo step per command, standalone lanes (pools forming and dissolving), and the live resize, reorder and drop previews.
# Map: feature_routes/swimlane_pools_lanes
# Tests: tests/test_swimlane_scene_ops.py
from __future__ import annotations

import unittest
from typing import Any

from ea_node_editor.graph.hierarchy import scope_node_ids
from ea_node_editor.graph.swimlane_layout import (
    SWIMLANE_CONTENT_PADDING,
    SWIMLANE_DEFAULT_LANE_THICKNESS,
    SWIMLANE_DEFAULT_POOL_LENGTH,
    SWIMLANE_LANE_HEADER,
    SWIMLANE_MIN_LANE_THICKNESS,
    SWIMLANE_POOL_HEADER,
)
from ea_node_editor.ui.shell.library_projection import build_registry_library_items
from ea_node_editor.ui.shell.runtime_history import (
    ACTION_ADD_SWIMLANE_LANE,
    ACTION_MOVE_SWIMLANE_LANE,
    ACTION_REMOVE_SWIMLANE_LANE,
)
from ea_node_editor.ui_qml.graph_scene_mutation.group_scope import collect_group_scope
from tests.automation.harness import build_context, shared_registry

POOL = "passive.annotation.swimlane_pool"
LANE = "passive.annotation.swimlane_lane"
GROUP = "passive.annotation.group_backdrop"
PROCESS = "passive.flowchart.process"
LOGGER = "core.logger"
PAD = SWIMLANE_CONTENT_PADDING


class _SwimlaneCase(unittest.TestCase):
    def setUp(self) -> None:
        self.context = build_context()
        self.scene = self.context.scene

    # -- helpers -------------------------------------------------------------------------------------------------

    @property
    def workspace(self):  # noqa: ANN201
        return self.context.active_workspace()

    def node(self, node_id: str):  # noqa: ANN201
        return self.workspace.nodes[node_id]

    def frame(self, node_id: str) -> tuple[float, float, float, float]:
        node = self.node(node_id)
        return (float(node.x), float(node.y), float(node.custom_width), float(node.custom_height))

    def position(self, node_id: str) -> tuple[float, float]:
        node = self.node(node_id)
        return (float(node.x), float(node.y))

    def add(self, type_id: str, x: float, y: float) -> str:
        return self.scene.add_node_from_type(type_id, float(x), float(y))

    def pool(self, x: float = 0.0, y: float = 0.0, *, lanes=("A", "B", "C"), orientation: str = "horizontal"):  # noqa: ANN001, ANN201
        pool_id, lane_ids = self.scene.create_swimlane_pool(
            float(x), float(y), orientation=orientation, lane_titles=list(lanes)
        )
        self.assertTrue(pool_id)
        return pool_id, lane_ids

    def describe(self, pool_id: str) -> dict[str, Any]:
        return next(pool for pool in self.scene.describe_swimlane_pools() if pool["pool_node_id"] == pool_id)

    def lane_order(self, pool_id: str) -> list[str]:
        return list(self.describe(pool_id)["lane_node_ids"])

    def lane_items(self, pool_id: str) -> dict[str, list[str]]:
        return {lane["lane_node_id"]: list(lane["node_ids"]) for lane in self.describe(pool_id)["lanes"]}

    def owner(self, node_id: str) -> str | None:
        workspace = self.workspace
        scope = collect_group_scope(
            self.scene._authoring_boundary,  # noqa: SLF001
            workspace,
            scope_node_ids(workspace, self.scene._scene_context.scope_path),  # noqa: SLF001
            dict(workspace.nodes),
        )
        return scope.owner(node_id)

    def undo_depth(self) -> int:
        return self.context.runtime_history.undo_depth(self.context.workspace_id())

    def last_action(self) -> str:
        return self.context.runtime_history._undo_stacks[self.context.workspace_id()][-1].action_type  # noqa: SLF001

    def assert_stacked(self, pool_id: str) -> None:
        """Lanes follow each other with no gap from the pool's top, share its width, and fill it."""
        orientation = self.describe(pool_id)["orientation"]
        px, py, pw, ph = self.frame(pool_id)
        cursor = py if orientation == "horizontal" else px
        for lane_id in self.lane_order(pool_id):
            x, y, w, h = self.frame(lane_id)
            if orientation == "horizontal":
                self.assertAlmostEqual(x, px + SWIMLANE_POOL_HEADER)
                self.assertAlmostEqual(x + w, px + pw)
                self.assertAlmostEqual(y, cursor)
                cursor += h
            else:
                self.assertAlmostEqual(y, py + SWIMLANE_POOL_HEADER)
                self.assertAlmostEqual(y + h, py + ph)
                self.assertAlmostEqual(x, cursor)
                cursor += w
        self.assertAlmostEqual(cursor, (py + ph) if orientation == "horizontal" else (px + pw))

    def assert_inside(self, lane_id: str, node_id: str) -> None:
        lx, ly, lw, lh = self.frame(lane_id)
        rect = self.scene.node_bounds(node_id)
        self.assertGreaterEqual(rect.x(), lx + SWIMLANE_LANE_HEADER - 0.01)
        self.assertGreaterEqual(rect.y(), ly - 0.01)
        self.assertLessEqual(rect.x() + rect.width(), lx + lw + 0.01)
        self.assertLessEqual(rect.y() + rect.height(), ly + lh + 0.01)


class SwimlaneMembershipTests(_SwimlaneCase):
    def test_a_new_pool_stacks_its_lanes_and_the_group_rule_puts_them_in_it(self) -> None:
        pool_id = self.add(POOL, 100.0, 50.0)

        lanes = self.lane_order(pool_id)
        self.assertEqual(len(lanes), 3)
        self.assertEqual([self.node(lane_id).title for lane_id in lanes], ["Lane 1", "Lane 2", "Lane 3"])
        self.assert_stacked(pool_id)
        self.assertEqual(self.frame(lanes[0])[3], SWIMLANE_DEFAULT_LANE_THICKNESS)
        self.assertEqual({self.owner(lane_id) for lane_id in lanes}, {pool_id})
        self.assertEqual({self.node(lane_id).type_id for lane_id in lanes}, {LANE})

    def test_a_node_dropped_in_a_lane_belongs_to_that_lane(self) -> None:
        pool_id, (a, b, c) = self.pool()
        node_id = self.add(PROCESS, 300.0, 260.0)

        self.assertEqual(self.owner(node_id), b)
        self.assertEqual(self.lane_items(pool_id)[b], [node_id])
        self.assertEqual(self.position(node_id), (300.0, 260.0))

    def test_a_node_dropped_across_a_lane_line_snaps_into_the_lane_of_its_centre(self) -> None:
        pool_id, (a, b, c) = self.pool()
        lanes_before = {lane_id: self.frame(lane_id) for lane_id in (a, b, c)}
        # Lane a spans y 0..200 and lane b 200..400: an 84 px node at y 170 has its centre at 212, in lane b, and
        # crosses into lane a above it.
        node_id = self.add(PROCESS, 300.0, 170.0)

        self.assertEqual(self.owner(node_id), b)
        self.assertEqual(self.position(node_id)[1], 200.0 + PAD)
        self.assertEqual({lane_id: self.frame(lane_id) for lane_id in (a, b, c)}, lanes_before)

    def test_a_node_too_tall_for_its_lane_grows_it_and_pushes_the_lanes_after(self) -> None:
        pool_id, (a, b, c) = self.pool()
        tall = self.add(PROCESS, 300.0, 230.0)
        c_node = self.add(PROCESS, 300.0, 460.0)
        self.scene.set_node_geometry(tall, 300.0, 230.0, 224.0, 300.0)

        self.assertEqual(self.owner(tall), b)
        self.assertEqual(self.frame(b)[1] + self.frame(b)[3], 230.0 + 300.0 + PAD)
        self.assert_stacked(pool_id)
        # Lane c moved down with its node.
        self.assertEqual(self.frame(c)[1], 230.0 + 300.0 + PAD)
        self.assertEqual(self.position(c_node)[1], 460.0 + (230.0 + 300.0 + PAD - 400.0))
        self.assertEqual(self.owner(c_node), c)

    def test_moving_a_node_to_another_lane_changes_its_lane(self) -> None:
        pool_id, (a, b, c) = self.pool()
        node_id = self.add(PROCESS, 300.0, 60.0)
        self.assertEqual(self.owner(node_id), a)

        self.assertTrue(self.scene.move_nodes_by_delta([node_id], 0.0, 400.0))

        self.assertEqual(self.owner(node_id), c)
        self.assertEqual(self.lane_items(pool_id)[a], [])

    def test_moving_a_node_out_of_the_pool_leaves_every_lane(self) -> None:
        pool_id, (a, b, c) = self.pool()
        node_id = self.add(PROCESS, 300.0, 60.0)

        self.scene.move_node(node_id, 2000.0, 60.0)

        self.assertIsNone(self.owner(node_id))
        self.assertEqual(self.frame(pool_id)[2], 1200.0)

    def test_dragging_a_lane_carries_its_nodes_and_drops_it_into_the_slot_it_lands_in(self) -> None:
        pool_id, (a, b, c) = self.pool()
        a_node = self.add(PROCESS, 300.0, 60.0)
        c_node = self.add(PROCESS, 500.0, 460.0)

        # A canvas drag moves the lane with its members; lane a's centre lands below lane c's.
        self.assertTrue(self.scene.move_nodes_by_delta([a, a_node], 30.0, 480.0))

        self.assertEqual(self.lane_order(pool_id), [b, c, a])
        self.assert_stacked(pool_id)
        self.assertEqual(self.owner(a_node), a)
        self.assertEqual(self.position(a_node), (300.0, 60.0 + 400.0))
        self.assertEqual(self.owner(c_node), c)
        self.assertEqual(self.position(c_node), (500.0, 460.0 - 200.0))

    def test_a_lane_dragged_out_of_its_pool_goes_back(self) -> None:
        pool_id, (a, b, c) = self.pool()
        b_node = self.add(PROCESS, 300.0, 260.0)
        before = {node_id: self.position(node_id) for node_id in (a, b, c, b_node)}

        self.scene.move_nodes_by_delta([b, b_node], 3000.0, 900.0)

        self.assertEqual(self.lane_order(pool_id), [a, b, c])
        self.assertEqual({node_id: self.position(node_id) for node_id in (a, b, c, b_node)}, before)

    def test_a_lane_dragged_onto_another_pool_joins_it(self) -> None:
        first, (a, b, c) = self.pool()
        second, (d, e) = self.pool(0.0, 1000.0, lanes=("D", "E"))
        a_node = self.add(PROCESS, 300.0, 60.0)

        # Lane a's centre (100) lands between lanes d and e of the second pool (1000..1400).
        self.scene.move_nodes_by_delta([a, a_node], 0.0, 1110.0)

        self.assertEqual(self.lane_order(first), [b, c])
        self.assertEqual(self.lane_order(second), [d, a, e])
        self.assert_stacked(first)
        self.assert_stacked(second)
        self.assertEqual(self.owner(a_node), a)
        self.assert_inside(a, a_node)

    def test_moving_the_pool_moves_its_lanes_and_what_they_hold(self) -> None:
        pool_id, (a, b, c) = self.pool()
        node_id = self.add(PROCESS, 300.0, 260.0)

        self.scene.move_node(pool_id, 500.0, 700.0)

        self.assertEqual(self.frame(pool_id)[:2], (500.0, 700.0))
        self.assertEqual(self.position(node_id), (800.0, 960.0))
        self.assertEqual(self.owner(node_id), b)
        self.assert_stacked(pool_id)

    def test_a_group_inside_a_lane_moves_as_one_block(self) -> None:
        pool_id, (a, b, c) = self.pool()
        left = self.add(PROCESS, 300.0, 250.0)
        right = self.add(PROCESS, 600.0, 250.0)
        group_id = self.scene.wrap_node_ids_in_group_backdrop([left, right])

        self.assertEqual(self.owner(group_id), b)
        self.assertEqual(self.owner(left), group_id)
        self.assert_stacked(pool_id)
        self.assert_inside(b, group_id)


class SwimlaneResizeTests(_SwimlaneCase):
    def test_growing_a_lane_pushes_the_lanes_after_it_with_their_nodes(self) -> None:
        pool_id, (a, b, c) = self.pool()
        c_node = self.add(PROCESS, 300.0, 460.0)
        x, y, w, _h = self.frame(b)

        self.scene.set_node_geometry(b, x, y, w, 320.0)

        self.assertEqual(self.frame(b)[3], 320.0)
        self.assertEqual(self.frame(c)[1], 520.0)
        self.assertEqual(self.position(c_node)[1], 580.0)
        self.assertEqual(self.frame(pool_id)[3], 720.0)
        self.assert_stacked(pool_id)

    def test_a_lanes_top_edge_moves_the_lanes_above_and_the_pool_top(self) -> None:
        pool_id, (a, b, c) = self.pool()
        a_node = self.add(PROCESS, 300.0, 60.0)
        x, y, w, h = self.frame(b)

        self.scene.set_node_geometry(b, x, y - 50.0, w, h + 50.0)

        self.assertEqual(self.frame(pool_id)[1], -50.0)
        self.assertEqual(self.frame(a)[1], -50.0)
        self.assertEqual(self.position(a_node)[1], 10.0)
        self.assertEqual(self.frame(c)[1], 400.0)
        self.assert_stacked(pool_id)

    def test_a_lane_never_shrinks_past_what_it_holds_or_below_the_minimum(self) -> None:
        pool_id, (a, b, c) = self.pool()
        node_id = self.add(PROCESS, 300.0, 220.0)
        # Dropped 20 px below the lane line, the node was nudged to the lane's padding.
        self.assertEqual(self.position(node_id)[1], 200.0 + PAD)
        x, y, w, _h = self.frame(b)

        self.scene.set_node_geometry(b, x, y, w, 40.0)

        self.assertEqual(self.frame(b)[3], PAD + 84.0 + PAD)
        self.assertEqual(self.owner(node_id), b)
        x, y, w, _h = self.frame(a)
        self.scene.set_node_geometry(a, x, y, w, 10.0)
        self.assertEqual(self.frame(a)[3], SWIMLANE_MIN_LANE_THICKNESS)
        self.assert_stacked(pool_id)

    def test_resizing_a_lane_or_the_pool_along_the_flow_resizes_every_lane(self) -> None:
        pool_id, (a, b, c) = self.pool()
        x, y, _w, h = self.frame(c)

        self.scene.set_node_geometry(c, x, y, 1600.0, h)
        self.assertEqual({self.frame(lane_id)[2] for lane_id in (a, b, c)}, {1600.0})
        self.assertEqual(self.frame(pool_id)[2], 1600.0 + SWIMLANE_POOL_HEADER)

        px, py, _pw, ph = self.frame(pool_id)
        self.scene.set_node_geometry(pool_id, px, py, 900.0, ph)
        self.assertEqual({self.frame(lane_id)[2] for lane_id in (a, b, c)}, {900.0 - SWIMLANE_POOL_HEADER})
        self.assert_stacked(pool_id)

    def test_the_pools_stack_edges_resize_its_first_and_last_lanes(self) -> None:
        pool_id, (a, b, c) = self.pool()
        px, py, pw, ph = self.frame(pool_id)

        self.scene.set_node_geometry(pool_id, px, py - 100.0, pw, ph + 200.0)

        self.assertEqual([self.frame(lane_id)[3] for lane_id in (a, b, c)], [300.0, 200.0, 300.0])
        self.assertEqual(self.frame(pool_id)[1], py - 100.0)
        self.assert_stacked(pool_id)

    def test_a_vertical_pool_resizes_along_x(self) -> None:
        pool_id, (a, b) = self.pool(lanes=("A", "B"), orientation="vertical")
        x, y, w, h = self.frame(a)

        self.scene.set_node_geometry(a, x, y, w + 60.0, h)

        self.assertEqual(self.frame(a)[2], w + 60.0)
        self.assertEqual(self.frame(b)[0], x + w + 60.0)
        self.assert_stacked(pool_id)

    def test_expanding_a_node_in_a_lane_restacks_the_pool(self) -> None:
        pool_id, (a, b, c) = self.pool(lanes=("A", "B", "C"))
        logger = self.add(LOGGER, 300.0, 230.0)
        c_node = self.add(PROCESS, 300.0, 460.0)
        self.assertTrue(self.scene.set_node_collapsed(logger, True))
        self.assertTrue(self.scene.set_node_collapsed(logger, False))

        self.assertEqual(self.owner(logger), b)
        self.assert_inside(b, logger)
        self.assert_stacked(pool_id)
        self.assertEqual(self.owner(c_node), c)


class SwimlaneLaneCommandTests(_SwimlaneCase):
    def test_add_insert_move_and_remove_are_one_undo_step_each(self) -> None:
        pool_id, (a, b, c) = self.pool()
        b_node = self.add(PROCESS, 300.0, 260.0)

        depth = self.undo_depth()
        new_lane = self.scene.add_swimlane_lane(pool_id, 1, "New")
        self.assertEqual(self.undo_depth(), depth + 1)
        self.assertEqual(self.last_action(), ACTION_ADD_SWIMLANE_LANE)
        self.assertEqual(self.lane_order(pool_id), [a, new_lane, b, c])
        self.assertEqual(self.node(new_lane).title, "New")
        self.assertEqual(self.position(b_node)[1], 260.0 + SWIMLANE_DEFAULT_LANE_THICKNESS)
        self.assert_stacked(pool_id)

        inserted = self.scene.insert_swimlane_lane(c, True)
        self.assertEqual(self.lane_order(pool_id), [a, new_lane, b, c, inserted])

        depth = self.undo_depth()
        self.assertTrue(self.scene.move_swimlane_lane(b, -2))
        self.assertEqual(self.undo_depth(), depth + 1)
        self.assertEqual(self.last_action(), ACTION_MOVE_SWIMLANE_LANE)
        self.assertEqual(self.lane_order(pool_id), [b, a, new_lane, c, inserted])
        self.assertEqual(self.owner(b_node), b)
        self.assert_inside(b, b_node)
        self.assertFalse(self.scene.move_swimlane_lane(b, -1))

        depth = self.undo_depth()
        self.assertTrue(self.scene.remove_swimlane_lane(new_lane))
        self.assertEqual(self.undo_depth(), depth + 1)
        self.assertEqual(self.last_action(), ACTION_REMOVE_SWIMLANE_LANE)
        self.assertNotIn(new_lane, self.workspace.nodes)
        self.assert_stacked(pool_id)

    def test_removing_a_lane_hands_its_band_and_nodes_to_its_neighbour(self) -> None:
        pool_id, (a, b, c) = self.pool()
        b_node = self.add(PROCESS, 300.0, 260.0)
        pool_before = self.frame(pool_id)

        self.assertTrue(self.scene.remove_swimlane_lane(b))

        self.assertEqual(self.frame(pool_id), pool_before)
        self.assertEqual(self.frame(a)[3], 400.0)
        self.assertEqual(self.position(b_node), (300.0, 260.0))
        self.assertEqual(self.owner(b_node), a)
        # The first lane goes to the lane after it.
        self.assertTrue(self.scene.remove_swimlane_lane(a))
        self.assertEqual(self.frame(c)[1:4:2], (0.0, 600.0))
        self.assertEqual(self.owner(b_node), c)

    def test_removing_a_pools_only_lane_dissolves_the_pool_and_keeps_its_nodes(self) -> None:
        pool_id, (only,) = self.pool(lanes=("Only",))
        node_id = self.add(PROCESS, 300.0, 60.0)
        position = self.position(node_id)

        self.assertTrue(self.scene.remove_swimlane_lane(only))

        self.assertNotIn(only, self.workspace.nodes)
        self.assertNotIn(pool_id, self.workspace.nodes)
        self.assertEqual(self.position(node_id), position)
        self.assertIsNone(self.owner(node_id))

    def test_deleting_a_lane_like_any_node_closes_its_gap_the_same_way(self) -> None:
        pool_id, (a, b, c) = self.pool()
        b_node = self.add(PROCESS, 300.0, 260.0)

        self.scene.remove_node(b)

        self.assertEqual(self.lane_order(pool_id), [a, c])
        self.assertEqual(self.owner(b_node), a)
        self.assert_stacked(pool_id)

    def test_deleting_a_pool_takes_its_lanes_and_keeps_what_they_hold(self) -> None:
        pool_id, lanes = self.pool()
        node_id = self.add(PROCESS, 300.0, 260.0)

        self.scene.remove_node(pool_id)

        self.assertTrue(set(lanes).isdisjoint(self.workspace.nodes))
        self.assertNotIn(pool_id, self.workspace.nodes)
        self.assertIn(node_id, self.workspace.nodes)

        second, second_lanes = self.pool(0.0, 1000.0)
        self.scene.select_node(second, False)
        self.assertTrue(self.scene.delete_selected_graph_items([]))
        self.assertTrue(set(second_lanes).isdisjoint(self.workspace.nodes))

    def test_copying_a_pool_copies_its_lanes(self) -> None:
        pool_id, lanes = self.pool()
        self.add(PROCESS, 300.0, 260.0)
        self.scene.select_node(pool_id, False)

        fragment = self.scene.serialize_selected_subgraph_fragment()

        self.assertEqual(sorted(node["type_id"] for node in fragment["nodes"]), sorted([POOL, LANE, LANE, LANE]))
        self.assertTrue(self.scene.paste_subgraph_fragment(fragment, 600.0, 1500.0))
        pools = self.scene.describe_swimlane_pools()
        self.assertEqual(len(pools), 2)
        for pool in pools:
            self.assertEqual(len(pool["lanes"]), 3)
            self.assert_stacked(pool["pool_node_id"])

    def test_a_lane_dropped_on_a_pool_joins_it_and_one_dropped_alone_stands_alone(self) -> None:
        pool_id, (a, b, c) = self.pool()

        # A lane joins at the slot its centre lands in: here between lanes a and b (centre y 250).
        joined = self.add(LANE, 300.0, 150.0)
        self.assertEqual(self.lane_order(pool_id), [a, joined, b, c])
        self.assert_stacked(pool_id)

        alone = self.add(LANE, 3000.0, 3000.0)
        self.assertEqual([pool["pool_node_id"] for pool in self.scene.describe_swimlane_pools()], [pool_id])
        self.assertEqual([lane["lane_node_id"] for lane in self.scene.describe_standalone_swimlane_lanes()], [alone])

    def test_assigning_nodes_places_them_after_what_the_lane_holds(self) -> None:
        pool_id, (a, b, c) = self.pool()
        held = self.add(PROCESS, 300.0, 250.0)
        loose = self.add(PROCESS, 3000.0, 3000.0)

        placed = self.scene.assign_nodes_to_swimlane_lane([loose], b)

        self.assertEqual(placed, [loose])
        self.assertEqual(self.owner(loose), b)
        held_rect = self.scene.node_bounds(held)
        self.assertGreater(self.position(loose)[0], held_rect.x() + held_rect.width())
        lx, ly, _lw, lh = self.frame(b)
        loose_rect = self.scene.node_bounds(loose)
        self.assertAlmostEqual(loose_rect.y() + loose_rect.height() * 0.5, ly + lh * 0.5)
        self.assertEqual(self.scene.assign_nodes_to_swimlane_lane([loose], b), [])

    def test_collapsing_a_pool_holds_its_lanes_and_nodes(self) -> None:
        pool_id, lanes = self.pool()
        node_id = self.add(PROCESS, 300.0, 260.0)

        self.assertTrue(self.scene.set_node_collapsed(pool_id, True))
        self.assertEqual(sorted(self.node(pool_id).held_member_ids), sorted([*lanes, node_id]))
        self.scene.move_node(pool_id, 400.0, 0.0)
        self.assertEqual(self.position(node_id), (700.0, 260.0))

        self.assertTrue(self.scene.set_node_collapsed(pool_id, False))
        self.assertEqual(self.lane_order(pool_id), lanes)
        self.assertEqual(self.owner(node_id), lanes[1])
        self.assert_stacked(pool_id)

    def test_turning_a_pool_keeps_each_node_in_its_lane(self) -> None:
        pool_id, (a, b) = self.pool(lanes=("A", "B"))
        first = self.add(PROCESS, 200.0, 60.0)
        second = self.add(PROCESS, 600.0, 260.0)

        depth = self.undo_depth()
        self.scene.set_node_property(pool_id, "orientation", "vertical")

        self.assertEqual(self.undo_depth(), depth + 1)
        self.assertEqual(self.describe(pool_id)["orientation"], "vertical")
        self.assertEqual({self.node(lane_id).properties["orientation"] for lane_id in (a, b)}, {"vertical"})
        self.assertEqual(self.lane_order(pool_id), [a, b])
        self.assertEqual((self.owner(first), self.owner(second)), (a, b))
        self.assert_stacked(pool_id)
        # Along the flow, second still comes after first.
        self.assertGreater(self.position(second)[1], self.position(first)[1])

    def test_undo_restores_the_pool_before_a_lane_drag(self) -> None:
        pool_id, (a, b, c) = self.pool()
        a_node = self.add(PROCESS, 300.0, 60.0)
        before = {node_id: self.position(node_id) for node_id in (a, b, c, a_node)}

        self.scene.move_nodes_by_delta([a, a_node], 0.0, 480.0)
        self.assertEqual(self.lane_order(pool_id), [b, c, a])
        history = self.context.runtime_history
        snapshot = history.undo_workspace(self.context.workspace_id(), self.workspace)
        self.assertIsNotNone(snapshot)
        self.scene.refresh_workspace_from_model(self.context.workspace_id())

        self.assertEqual({node_id: self.position(node_id) for node_id in (a, b, c, a_node)}, before)
        self.assertEqual(self.lane_order(pool_id), [a, b, c])


class SwimlaneLaneFirstTests(_SwimlaneCase):
    """A lane stands on its own; a pool forms around two or more lanes and dissolves when one is left."""

    def standalone_ids(self) -> list[str]:
        return [lane["lane_node_id"] for lane in self.scene.describe_standalone_swimlane_lanes()]

    def pool_ids(self) -> list[str]:
        return [pool["pool_node_id"] for pool in self.scene.describe_swimlane_pools()]

    def undo(self) -> None:
        self.assertIsNotNone(self.context.runtime_history.undo_workspace(self.context.workspace_id(), self.workspace))
        self.scene.refresh_workspace_from_model(self.context.workspace_id())

    def assert_inside_vertical(self, lane_id: str, node_id: str) -> None:
        lx, ly, lw, lh = self.frame(lane_id)
        rect = self.scene.node_bounds(node_id)
        self.assertGreaterEqual(rect.y(), ly + SWIMLANE_LANE_HEADER - 0.01)
        self.assertGreaterEqual(rect.x(), lx - 0.01)
        self.assertLessEqual(rect.x() + rect.width(), lx + lw + 0.01)
        self.assertLessEqual(rect.y() + rect.height(), ly + lh + 0.01)

    def place_centre(self, node_id: str, cx: float, cy: float) -> None:
        rect = self.scene.node_bounds(node_id)
        self.scene.move_node(node_id, cx - rect.width() * 0.5, cy - rect.height() * 0.5)

    def test_a_lane_on_its_own_holds_what_lands_in_it_and_grows_to_fit(self) -> None:
        lane = self.add(LANE, 100.0, 100.0)
        self.assertEqual((self.pool_ids(), self.standalone_ids()), ([], [lane]))
        x, y, w, h = self.frame(lane)
        self.assertEqual((x, y), (100.0, 100.0))
        node_id = self.add(PROCESS, 400.0, 150.0)
        self.assertEqual(self.owner(node_id), lane)
        self.assert_inside(lane, node_id)

        # Its centre still in the lane but running past the lane's end: the lane gets longer.
        self.place_centre(node_id, x + w - 10.0, y + h * 0.5)
        self.assertEqual(self.owner(node_id), lane)
        self.assert_inside(lane, node_id)
        self.assertGreater(self.frame(lane)[2], w)

    def test_a_plus_next_to_a_lane_forms_a_pool_around_it_without_moving_it(self) -> None:
        lane = self.add(LANE, 100.0, 100.0)
        node_id = self.add(PROCESS, 400.0, 150.0)
        lane_frame = self.frame(lane)
        node_position = self.position(node_id)
        depth = self.undo_depth()

        new_lane = self.scene.insert_swimlane_lane(lane, after=True)

        (pool_id,) = self.pool_ids()
        self.assertEqual(self.lane_order(pool_id), [lane, new_lane])
        self.assertEqual(self.frame(lane), lane_frame)
        self.assertEqual(self.position(node_id), node_position)
        self.assertEqual(self.frame(pool_id)[:2], (lane_frame[0] - SWIMLANE_POOL_HEADER, lane_frame[1]))
        self.assert_stacked(pool_id)
        self.assertEqual((self.owner(node_id), self.standalone_ids()), (lane, []))
        self.assertEqual((self.undo_depth(), self.last_action()), (depth + 1, ACTION_ADD_SWIMLANE_LANE))

        self.undo()
        self.assertEqual((self.pool_ids(), self.standalone_ids()), ([], [lane]))
        self.assertNotIn(new_lane, self.workspace.nodes)

    def test_a_plus_before_a_lane_puts_the_new_lane_first(self) -> None:
        lane = self.add(LANE, 100.0, 100.0)

        new_lane = self.scene.insert_swimlane_lane(lane, after=False)

        (pool_id,) = self.pool_ids()
        self.assertEqual(self.lane_order(pool_id), [new_lane, lane])
        self.assert_stacked(pool_id)

    def test_removing_down_to_one_lane_dissolves_the_pool_and_the_last_lane_keeps_the_room(self) -> None:
        pool_id, (a, b) = self.pool(lanes=("A", "B"))
        b_node = self.add(PROCESS, 300.0, 260.0)
        px, py, pw, ph = self.frame(pool_id)
        position = self.position(b_node)
        depth = self.undo_depth()

        self.assertTrue(self.scene.remove_swimlane_lane(b))

        self.assertNotIn(pool_id, self.workspace.nodes)
        self.assertEqual(self.standalone_ids(), [a])
        self.assertEqual(self.frame(a), (px + SWIMLANE_POOL_HEADER, py, pw - SWIMLANE_POOL_HEADER, ph))
        self.assertEqual(self.position(b_node), position)
        self.assertEqual(self.owner(b_node), a)
        self.assertEqual((self.undo_depth(), self.last_action()), (depth + 1, ACTION_REMOVE_SWIMLANE_LANE))

        self.undo()
        self.assertEqual(self.lane_order(pool_id), [a, b])

    def test_deleting_a_lane_of_a_two_lane_pool_dissolves_the_pool_too(self) -> None:
        pool_id, (a, b) = self.pool(lanes=("A", "B"))
        self.scene.select_node(b, False)

        self.assertTrue(self.scene.delete_selected_graph_items([]))

        self.assertNotIn(b, self.workspace.nodes)
        self.assertNotIn(pool_id, self.workspace.nodes)
        self.assertEqual(self.standalone_ids(), [a])

    def test_a_lane_dropped_on_a_lane_stacks_with_it_in_a_new_pool(self) -> None:
        first = self.add(LANE, 0.0, 0.0)
        second = self.add(LANE, 3000.0, 3000.0)
        second_node = self.add(PROCESS, 3300.0, 3050.0)

        # Its centre lands in the lower half of the first lane (y 180 of 0-200).
        self.scene.move_nodes_by_delta([second, second_node], -3000.0, -2920.0)

        (pool_id,) = self.pool_ids()
        self.assertEqual(self.lane_order(pool_id), [first, second])
        self.assertEqual(self.frame(first)[:2], (0.0, 0.0))
        self.assert_stacked(pool_id)
        self.assertEqual(self.owner(second_node), second)
        self.assert_inside(second, second_node)

    def test_a_lane_on_its_own_moves_freely_and_carries_what_it_holds(self) -> None:
        lane = self.add(LANE, 0.0, 0.0)
        node_id = self.add(PROCESS, 300.0, 50.0)

        self.scene.move_nodes_by_delta([lane, node_id], 500.0, 700.0)

        self.assertEqual(self.position(lane), (500.0, 700.0))
        self.assertEqual(self.position(node_id), (800.0, 750.0))
        self.assertEqual((self.standalone_ids(), self.owner(node_id)), ([lane], lane))

    def test_turning_a_lane_on_its_own_keeps_what_it_holds_along_and_across(self) -> None:
        lane = self.add(LANE, 100.0, 100.0)
        node_id = self.add(PROCESS, 400.0, 150.0)
        self.place_centre(node_id, 500.0, 250.0)  # 400 along the flow, 150 across the lane
        x, y, w, h = self.frame(lane)

        self.scene.set_node_property(lane, "orientation", "vertical")

        self.assertEqual(self.node(lane).properties["orientation"], "vertical")
        tx, ty, tw, th = self.frame(lane)
        # The lane keeps its corner and length; the node keeps its shape, so across the lane it may need more room.
        self.assertEqual((tx, ty, th), (x, y, w))
        self.assertGreaterEqual(tw, h)
        self.assert_inside_vertical(lane, node_id)
        turned = self.scene.node_bounds(node_id)
        self.assertAlmostEqual(turned.center().x(), 250.0)
        self.assertAlmostEqual(turned.center().y(), 500.0)
        self.assertEqual(self.owner(node_id), lane)

    def test_turning_a_lane_in_a_pool_turns_the_whole_pool(self) -> None:
        pool_id, (a, b) = self.pool(lanes=("A", "B"))

        self.scene.set_node_property(b, "orientation", "vertical")

        self.assertEqual(self.describe(pool_id)["orientation"], "vertical")
        self.assertEqual({self.node(lane_id).properties["orientation"] for lane_id in (a, b)}, {"vertical"})
        self.assert_stacked(pool_id)

    def test_reordering_a_lane_puts_it_in_that_slot_with_what_it_holds(self) -> None:
        pool_id, (a, b, c) = self.pool()
        c_node = self.add(PROCESS, 300.0, 460.0)
        depth = self.undo_depth()

        self.assertTrue(self.scene.reorder_swimlane_lane(c, 0))

        self.assertEqual(self.lane_order(pool_id), [c, a, b])
        self.assertEqual(self.owner(c_node), c)
        self.assert_inside(c, c_node)
        self.assert_stacked(pool_id)
        self.assertEqual((self.undo_depth(), self.last_action()), (depth + 1, ACTION_MOVE_SWIMLANE_LANE))
        self.assertFalse(self.scene.reorder_swimlane_lane(c, 0))

    def test_create_lane_places_a_lane_on_its_own(self) -> None:
        lane = self.scene.create_swimlane_lane(200.0, 300.0, orientation="vertical", title="QA")

        self.assertEqual(self.standalone_ids(), [lane])
        self.assertEqual(self.node(lane).title, "QA")
        self.assertEqual(
            self.frame(lane), (200.0, 300.0, SWIMLANE_DEFAULT_LANE_THICKNESS, SWIMLANE_DEFAULT_POOL_LENGTH)
        )

    def test_the_library_offers_the_lane_as_swimlane_and_not_the_pool(self) -> None:
        registry = shared_registry()
        items = build_registry_library_items(registry_specs=registry.all_specs(), data_types=registry.data_types)
        by_type = {item["type_id"]: item for item in items}

        self.assertNotIn(POOL, by_type)
        self.assertEqual(by_type[LANE]["display_name"], "Swimlane")


class SwimlanePreviewTests(_SwimlaneCase):
    """Live previews read the scene and change nothing; what they draw is what the commit lands."""

    @property
    def boundary(self):  # noqa: ANN201
        return self.scene._authoring_boundary  # noqa: SLF001

    def test_a_resize_preview_draws_what_the_commit_lands(self) -> None:
        pool_id, (a, b, c) = self.pool()
        c_node = self.add(PROCESS, 300.0, 460.0)
        x, y, w, h = self.frame(b)

        preview = self.boundary.preview_swimlane_resize(b, x, y, w, h + 120.0)

        self.assertEqual(set(preview["frames"]), {pool_id, b, c})
        self.assertEqual(set(preview["positions"]), {c_node})
        self.assertEqual(self.frame(b), (x, y, w, h))
        self.scene.set_node_geometry(b, x, y, w, h + 120.0)
        for node_id, frame in preview["frames"].items():
            self.assertEqual(list(self.frame(node_id)), frame)
        self.assertEqual(list(self.position(c_node)), preview["positions"][c_node])

    def test_a_resize_preview_stops_a_lane_at_what_it_holds(self) -> None:
        _pool_id, (_a, b, _c) = self.pool()
        b_node = self.add(PROCESS, 300.0, 260.0)
        x, y, w, _h = self.frame(b)

        preview = self.boundary.preview_swimlane_resize(b, x, y, w, 10.0)

        _fx, fy, _fw, fh = preview["frames"][b]
        rect = self.scene.node_bounds(b_node)
        self.assertGreaterEqual(fy + fh, rect.y() + rect.height() + PAD - 0.01)

    def test_a_resize_preview_of_a_lane_on_its_own(self) -> None:
        lane = self.add(LANE, 0.0, 0.0)
        x, y, w, h = self.frame(lane)

        preview = self.boundary.preview_swimlane_resize(lane, x, y, w + 200.0, h)

        self.assertEqual(preview["frames"], {lane: [x, y, w + 200.0, h]})

    def test_a_lane_drag_stays_in_its_pool_and_the_lanes_it_passes_make_room(self) -> None:
        pool_id, (a, b, c) = self.pool()
        b_node = self.add(PROCESS, 300.0, 260.0)
        b_position = self.position(b_node)

        # A's bottom edge (350) passes B's centre (300): A takes B's slot and B moves up by A's thickness.
        preview = self.boundary.preview_swimlane_lane_drag(a, 500.0, 150.0, "drag")

        self.assertEqual(preview["offset"], [0.0, 150.0])
        self.assertEqual((preview["current"], preview["index"]), (0, 1))
        self.assertEqual(set(preview["frames"]), {b})
        self.assertEqual(preview["frames"][b][1], self.frame(b)[1] - SWIMLANE_DEFAULT_LANE_THICKNESS)
        self.assertEqual(
            preview["positions"], {b_node: [b_position[0], b_position[1] - SWIMLANE_DEFAULT_LANE_THICKNESS]}
        )
        # A small nudge swaps nothing, and past the pool's end the lane stops in the last slot.
        self.assertEqual(self.boundary.preview_swimlane_lane_drag(a, 0.0, 40.0, "drag")["index"], 0)
        far = self.boundary.preview_swimlane_lane_drag(a, 0.0, 5000.0, "drag")
        self.assertEqual((far["offset"], far["index"]), ([0.0, 400.0], 2))
        up = self.boundary.preview_swimlane_lane_drag(c, 0.0, -5000.0, "drag")
        self.assertEqual((up["offset"], up["index"]), ([0.0, -400.0], 0))

        self.assertTrue(self.scene.reorder_swimlane_lane(a, preview["index"]))
        self.assertEqual(self.lane_order(pool_id), [b, a, c])

    def test_a_lane_on_its_own_has_no_reorder_preview(self) -> None:
        lane = self.add(LANE, 0.0, 0.0)

        self.assertEqual(self.boundary.preview_swimlane_lane_drag(lane, 0.0, 100.0, "drag"), {})

    def test_a_drop_preview_names_the_lane_a_node_lands_in(self) -> None:
        _pool_id, (a, b, _c) = self.pool()
        node_id = self.add(PROCESS, 300.0, 60.0)

        preview = self.boundary.preview_swimlane_drop([node_id], 0.0, 200.0, "drop")

        self.assertEqual(preview["targets"], [b])
        self.assertNotIn(node_id, preview["positions"])
        self.assertEqual(self.owner(node_id), a)

    def test_a_drop_preview_grows_the_lanes_past_their_end_as_the_commit_does(self) -> None:
        pool_id, (a, b, c) = self.pool()
        node_id = self.add(PROCESS, 300.0, 60.0)
        px, _py, pw, _ph = self.frame(pool_id)
        rect = self.scene.node_bounds(node_id)
        dx = (px + pw - 10.0) - rect.center().x()

        preview = self.boundary.preview_swimlane_drop([node_id], dx, 0.0, "drop")

        self.assertEqual(preview["targets"], [a])
        grown = rect.x() + dx + rect.width() + PAD
        for frame_id in (pool_id, a, b, c):
            self.assertAlmostEqual(preview["frames"][frame_id][0] + preview["frames"][frame_id][2], grown)
        self.assertNotIn(node_id, preview["frames"])
        self.scene.move_nodes_by_delta([node_id], dx, 0.0)
        for frame_id in (pool_id, a, b, c):
            self.assertEqual(list(self.frame(frame_id)), preview["frames"][frame_id])

    def test_a_drop_preview_of_a_lane_names_the_pool_or_lane_it_would_stack_with(self) -> None:
        pool_id, _lanes = self.pool()
        lane = self.add(LANE, 3000.0, 3000.0)
        other = self.add(LANE, 6000.0, 6000.0)

        self.assertEqual(self.boundary.preview_swimlane_drop([lane], -2700.0, -2900.0, "drop")["targets"], [pool_id])
        self.assertEqual(self.boundary.preview_swimlane_drop([lane], 3100.0, 3050.0, "drop")["targets"], [other])


if __name__ == "__main__":
    unittest.main()
