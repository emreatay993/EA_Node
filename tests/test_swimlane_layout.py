# Purpose: Unit tests for the pure swimlane geometry: stacking, nudges and growth, lane lookup, lane removal, and edge-aware lane/pool resizes in both orientations.
# Map: feature_routes/swimlane_pools_lanes
# Tests: tests/test_swimlane_layout.py
from __future__ import annotations

import unittest

from ea_node_editor.graph.swimlane_layout import (
    SWIMLANE_CONTENT_PADDING as PAD,
    SWIMLANE_LANE_HEADER,
    SWIMLANE_MIN_LANE_THICKNESS,
    SWIMLANE_POOL_HEADER,
    SwimlaneLaneState,
    absorb_removed_swimlane_lane,
    new_swimlane_pool_frames,
    order_swimlane_lanes,
    resolve_swimlane_lane_resize,
    resolve_swimlane_pool_resize,
    restack_swimlane_pool,
    swimlane_lane_index_at,
)
from ea_node_editor.graph.transform_layout_ops import LayoutNodeBounds

H = "horizontal"
V = "vertical"


def rect(node_id: str, x: float, y: float, width: float, height: float) -> LayoutNodeBounds:
    return LayoutNodeBounds(node_id, float(x), float(y), float(width), float(height))


def lane(lane_id: str, x: float, y: float, width: float, height: float, *items: LayoutNodeBounds) -> SwimlaneLaneState:
    return SwimlaneLaneState(lane_id=lane_id, bounds=rect(lane_id, x, y, width, height), item_bounds=tuple(items))


class NewPoolFrameTests(unittest.TestCase):
    def test_horizontal_pool_stacks_rows_right_of_its_title_band(self) -> None:
        frames = new_swimlane_pool_frames(100.0, 50.0, H, ["a", "b", "c"], pool_id="p", lane_thickness=200.0, length=1000.0)

        self.assertEqual(frames.pool, rect("p", 100.0, 50.0, 1000.0, 600.0))
        self.assertEqual(
            frames.lanes,
            (
                rect("a", 100.0 + SWIMLANE_POOL_HEADER, 50.0, 1000.0 - SWIMLANE_POOL_HEADER, 200.0),
                rect("b", 100.0 + SWIMLANE_POOL_HEADER, 250.0, 1000.0 - SWIMLANE_POOL_HEADER, 200.0),
                rect("c", 100.0 + SWIMLANE_POOL_HEADER, 450.0, 1000.0 - SWIMLANE_POOL_HEADER, 200.0),
            ),
        )

    def test_vertical_pool_is_the_transposed_picture(self) -> None:
        frames = new_swimlane_pool_frames(100.0, 50.0, V, ["a", "b"], pool_id="p", lane_thickness=240.0, length=900.0)

        self.assertEqual(frames.pool, rect("p", 100.0, 50.0, 480.0, 900.0))
        self.assertEqual(
            frames.lanes,
            (
                rect("a", 100.0, 50.0 + SWIMLANE_POOL_HEADER, 240.0, 900.0 - SWIMLANE_POOL_HEADER),
                rect("b", 340.0, 50.0 + SWIMLANE_POOL_HEADER, 240.0, 900.0 - SWIMLANE_POOL_HEADER),
            ),
        )


class RestackTests(unittest.TestCase):
    def test_restack_closes_gaps_and_carries_each_lanes_items(self) -> None:
        pool = rect("p", 0.0, 0.0, 1000.0, 400.0)
        lanes = [
            lane("a", 40.0, 0.0, 960.0, 200.0, rect("n1", 200.0, 60.0, 200.0, 80.0)),
            # Pushed 50 px down and 50 px sideways with its node (a make-room push): the restack puts both back under
            # lane a.
            lane("b", 90.0, 250.0, 960.0, 200.0, rect("n2", 350.0, 310.0, 200.0, 80.0)),
        ]

        result = restack_swimlane_pool(pool, H, lanes)

        self.assertEqual(result.lanes, (rect("a", 40.0, 0.0, 960.0, 200.0), rect("b", 40.0, 200.0, 960.0, 200.0)))
        self.assertEqual(result.pool, rect("p", 0.0, 0.0, 1000.0, 400.0))
        self.assertEqual(result.item_offsets, {"n2": (-50.0, -50.0)})

    def test_items_crossing_a_start_side_are_nudged_in_and_end_sides_grow(self) -> None:
        pool = rect("p", 0.0, 0.0, 1000.0, 400.0)
        # n1 overlaps lane a's role band and top edge; n2 sticks out below lane b and past the pool's right edge.
        lanes = [
            lane("a", 40.0, 0.0, 960.0, 200.0, rect("n1", 50.0, -10.0, 200.0, 80.0)),
            lane("b", 40.0, 200.0, 960.0, 200.0, rect("n2", 900.0, 300.0, 200.0, 160.0)),
        ]

        result = restack_swimlane_pool(pool, H, lanes)

        content_left = 40.0 + SWIMLANE_LANE_HEADER + PAD
        self.assertEqual(result.item_offsets["n1"], (content_left - 50.0, PAD + 10.0))
        self.assertNotIn("n2", result.item_offsets)
        self.assertEqual(result.lanes[1].bottom, 460.0 + PAD)  # grown to n2's bottom plus padding
        self.assertEqual(result.pool.right, 1100.0 + PAD)
        self.assertEqual({lane_rect.right for lane_rect in result.lanes}, {1100.0 + PAD})

    def test_vertical_restack_moves_items_along_x(self) -> None:
        pool = rect("p", 0.0, 0.0, 400.0, 1000.0)
        lanes = [
            lane("a", 0.0, 40.0, 200.0, 960.0),
            lane("b", 260.0, 40.0, 200.0, 960.0, rect("n", 300.0, 300.0, 120.0, 80.0)),
        ]

        result = restack_swimlane_pool(pool, V, lanes)

        self.assertEqual(result.lanes[1], rect("b", 200.0, 40.0, 200.0, 960.0))
        self.assertEqual(result.item_offsets, {"n": (-60.0, 0.0)})

    def test_lane_less_pool_keeps_its_items_inside_its_body(self) -> None:
        pool = rect("p", 0.0, 0.0, 600.0, 300.0)

        result = restack_swimlane_pool(pool, H, [], pool_items=[rect("n", 10.0, 250.0, 100.0, 100.0)])

        self.assertEqual(result.item_offsets, {"n": (SWIMLANE_POOL_HEADER + PAD - 10.0, 0.0)})
        self.assertEqual(result.pool.bottom, 350.0 + PAD)


class LaneLookupTests(unittest.TestCase):
    def test_the_lane_level_with_a_point_holds_it(self) -> None:
        pool = rect("p", 0.0, 0.0, 1000.0, 400.0)
        lanes = [rect("a", 40.0, 0.0, 960.0, 200.0), rect("b", 40.0, 200.0, 960.0, 200.0)]

        self.assertEqual(swimlane_lane_index_at(pool, H, lanes, (500.0, 100.0)), 0)
        self.assertEqual(swimlane_lane_index_at(pool, H, lanes, (500.0, 250.0)), 1)
        self.assertEqual(swimlane_lane_index_at(pool, H, lanes, (10.0, 399.0)), 1)  # the title band counts
        self.assertIsNone(swimlane_lane_index_at(pool, H, lanes, (1200.0, 100.0)))
        self.assertIsNone(swimlane_lane_index_at(pool, H, [], (500.0, 100.0)))

    def test_order_follows_the_stack_axis(self) -> None:
        lanes = [rect("a", 0.0, 300.0, 100.0, 100.0), rect("b", 0.0, 0.0, 100.0, 100.0), rect("c", 500.0, 150.0, 100.0, 100.0)]

        self.assertEqual(order_swimlane_lanes(lanes, H), ["b", "c", "a"])
        # a and b share an x centre: the previous order breaks the tie.
        self.assertEqual(order_swimlane_lanes(lanes, V, previous_order=["b", "a", "c"]), ["b", "a", "c"])
        self.assertEqual(order_swimlane_lanes(lanes, V, previous_order=["a", "b", "c"]), ["a", "b", "c"])


class RemoveLaneTests(unittest.TestCase):
    def test_the_lane_before_takes_the_removed_band_and_nothing_moves(self) -> None:
        pool = rect("p", 0.0, 0.0, 1000.0, 600.0)
        lanes = [
            lane("a", 40.0, 0.0, 960.0, 200.0, rect("n1", 200.0, 60.0, 200.0, 80.0)),
            lane("b", 40.0, 200.0, 960.0, 200.0, rect("n2", 200.0, 260.0, 200.0, 80.0)),
            lane("c", 40.0, 400.0, 960.0, 200.0),
        ]

        remaining = absorb_removed_swimlane_lane(lanes, "b", H)
        result = restack_swimlane_pool(pool, H, remaining)

        self.assertEqual([state.lane_id for state in remaining], ["a", "c"])
        self.assertEqual(result.lanes, (rect("a", 40.0, 0.0, 960.0, 400.0), rect("c", 40.0, 400.0, 960.0, 200.0)))
        self.assertEqual(result.item_offsets, {})
        self.assertEqual(result.pool, pool)

    def test_removing_the_first_lane_grows_the_next_one_upwards(self) -> None:
        pool = rect("p", 0.0, 0.0, 1000.0, 400.0)
        lanes = [
            lane("a", 40.0, 0.0, 960.0, 200.0, rect("n1", 200.0, 60.0, 200.0, 80.0)),
            lane("b", 40.0, 200.0, 960.0, 200.0, rect("n2", 200.0, 260.0, 200.0, 80.0)),
        ]

        result = restack_swimlane_pool(pool, H, absorb_removed_swimlane_lane(lanes, "a", H))

        self.assertEqual(result.lanes, (rect("b", 40.0, 0.0, 960.0, 400.0),))
        self.assertEqual(result.item_offsets, {})


class ResizeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pool = rect("p", 0.0, 0.0, 1000.0, 600.0)
        self.lanes = [
            lane("a", 40.0, 0.0, 960.0, 200.0, rect("n1", 200.0, 60.0, 200.0, 80.0)),
            lane("b", 40.0, 200.0, 960.0, 200.0, rect("n2", 300.0, 260.0, 200.0, 80.0)),
            lane("c", 40.0, 400.0, 960.0, 200.0, rect("n3", 400.0, 460.0, 200.0, 80.0)),
        ]

    def resize_lane(self, lane_id: str, requested: LayoutNodeBounds, orientation: str = H):
        request = resolve_swimlane_lane_resize(self.pool, orientation, self.lanes, lane_id, requested)
        self.assertIsNotNone(request)
        return restack_swimlane_pool(
            self.pool,
            orientation,
            request.lanes,
            stack_start=request.stack_start,
            cross_start=request.cross_start,
            cross_end=request.cross_end,
        )

    def test_growing_a_lanes_end_edge_pushes_the_lanes_after_it(self) -> None:
        result = self.resize_lane("b", rect("b", 40.0, 200.0, 960.0, 300.0))

        self.assertEqual([lane_rect.y for lane_rect in result.lanes], [0.0, 200.0, 500.0])
        self.assertEqual(result.lanes[1].height, 300.0)
        self.assertEqual(result.item_offsets, {"n3": (0.0, 100.0)})
        self.assertEqual(result.pool.height, 700.0)

    def test_moving_a_lanes_start_edge_moves_the_lanes_before_it_and_the_pool_start(self) -> None:
        result = self.resize_lane("b", rect("b", 40.0, 150.0, 960.0, 250.0))

        self.assertEqual([lane_rect.y for lane_rect in result.lanes], [-50.0, 150.0, 400.0])
        self.assertEqual(result.item_offsets, {"n1": (0.0, -50.0)})
        self.assertEqual((result.pool.y, result.pool.height), (-50.0, 650.0))

    def test_a_lane_never_shrinks_past_what_it_holds(self) -> None:
        result = self.resize_lane("b", rect("b", 40.0, 200.0, 960.0, 50.0))

        self.assertEqual(result.lanes[1].bottom, 340.0 + PAD)
        self.assertEqual(result.item_offsets["n3"], (0.0, 340.0 + PAD - 400.0))

    def test_a_lane_never_shrinks_below_the_minimum(self) -> None:
        self.lanes[1] = lane("b", 40.0, 200.0, 960.0, 200.0)

        result = self.resize_lane("b", rect("b", 40.0, 200.0, 960.0, 10.0))

        self.assertEqual(result.lanes[1].height, SWIMLANE_MIN_LANE_THICKNESS)

    def test_resizing_a_lane_along_the_flow_resizes_every_lane_and_the_pool(self) -> None:
        result = self.resize_lane("a", rect("a", 40.0, 0.0, 1360.0, 200.0))

        self.assertEqual({lane_rect.right for lane_rect in result.lanes}, {1400.0})
        self.assertEqual(result.pool.right, 1400.0)

    def test_the_flow_start_edge_stops_before_the_role_band_would_cover_a_node(self) -> None:
        result = self.resize_lane("a", rect("a", 300.0, 0.0, 700.0, 200.0))

        self.assertEqual(result.lanes[0].x, 200.0 - SWIMLANE_LANE_HEADER - PAD)
        self.assertEqual(result.pool.x, 200.0 - SWIMLANE_LANE_HEADER - PAD - SWIMLANE_POOL_HEADER)
        self.assertEqual(result.item_offsets, {})

    def test_pool_stack_edges_resize_the_first_and_last_lanes(self) -> None:
        request = resolve_swimlane_pool_resize(self.pool, H, self.lanes, rect("p", 0.0, -100.0, 1000.0, 800.0))
        result = restack_swimlane_pool(
            self.pool,
            H,
            request.lanes,
            stack_start=request.stack_start,
            cross_start=request.cross_start,
            cross_end=request.cross_end,
        )

        self.assertEqual([lane_rect.height for lane_rect in result.lanes], [300.0, 200.0, 300.0])
        self.assertEqual(result.pool, rect("p", 0.0, -100.0, 1000.0, 800.0))
        self.assertEqual(result.item_offsets, {})

    def test_vertical_lane_resize_uses_the_transposed_edges(self) -> None:
        self.pool = rect("p", 0.0, 0.0, 400.0, 1000.0)
        self.lanes = [lane("a", 0.0, 40.0, 200.0, 960.0), lane("b", 200.0, 40.0, 200.0, 960.0)]

        result = self.resize_lane("a", rect("a", 0.0, 40.0, 260.0, 960.0), orientation=V)

        self.assertEqual(result.lanes[1], rect("b", 260.0, 40.0, 200.0, 960.0))
        self.assertEqual(result.pool.width, 460.0)


if __name__ == "__main__":
    unittest.main()
