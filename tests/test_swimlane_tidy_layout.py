# Purpose: Lane-aware Tidy tests: the pure pool layout (layer columns shared by every lane, one row per lane, stacking inside a lane, both orientations) and the scene Tidy on real pools (lanes kept, one undo step, repeatable).
# Map: feature_routes/swimlane_pools_lanes
# Tests: tests/test_swimlane_tidy_layout.py
from __future__ import annotations

import unittest

from ea_node_editor.graph.swimlane_layout import (
    SWIMLANE_CONTENT_PADDING,
    SWIMLANE_LANE_HEADER,
    SWIMLANE_MIN_LANE_THICKNESS,
    SWIMLANE_POOL_HEADER,
)
from ea_node_editor.graph.transform_tidy_layout import (
    DEFAULT_TIDY_COLUMN_GAP,
    DEFAULT_TIDY_ROW_GAP,
    TIDY_MODE_IN_PLACE,
    TidyItem,
    TidySettings,
    TidyWire,
    build_tidy_layout,
)
from tests.automation.harness import build_context
from tests.test_swimlane_scene_ops import _SwimlaneCase

PAD = SWIMLANE_CONTENT_PADDING
PROCESS = "passive.flowchart.process"
START = "passive.flowchart.start"
DECISION = "passive.flowchart.decision"


def _wire(wire_id: str, source: str, target: str, sides: tuple[str, str] = ("right", "left")) -> TidyWire:
    return TidyWire(
        wire_id=wire_id,
        source_id=source,
        target_id=target,
        source_side=sides[0],
        target_side=sides[1],
        source_offset=(100.0, 40.0),
        target_offset=(0.0, 40.0),
    )


class PoolLayoutTests(unittest.TestCase):
    """A horizontal pool (x 0, y 0) with lanes a, b, c of 200 px and 100 x 80 steps scattered in them."""

    def pool_items(self, members: dict[str, tuple[str, float, float]], *, orientation: str = "horizontal"):  # noqa: ANN201
        vertical = orientation == "vertical"

        def rect(x: float, y: float, width: float, height: float) -> tuple[float, float, float, float]:
            return (y, x, height, width) if vertical else (x, y, width, height)

        items = [TidyItem("pool", *rect(0.0, 0.0, 1200.0, 600.0), is_group=True, swimlane_pool=orientation)]
        for index, lane_id in enumerate(("a", "b", "c")):
            items.append(
                TidyItem(
                    lane_id,
                    *rect(SWIMLANE_POOL_HEADER, index * 200.0, 1200.0 - SWIMLANE_POOL_HEADER, 200.0),
                    parent_group_id="pool",
                    is_group=True,
                    swimlane_lane=True,
                )
            )
        for item_id, (lane_id, x, y) in members.items():
            items.append(TidyItem(item_id, *rect(x, y, 100.0, 80.0), parent_group_id=lane_id))
        return items

    def layout(self, items, wires, **settings):  # noqa: ANN001, ANN201
        result = build_tidy_layout(items, wires, TidySettings(**settings))
        by_id = {item.item_id: item for item in items}

        def final(item_id: str) -> tuple[float, float, float, float]:
            item = by_id[item_id]
            x, y = result.positions.get(item_id, (item.x, item.y))
            width, height = result.group_sizes.get(item_id, (item.width, item.height))
            return (x, y, width, height)

        return result, final

    def test_steps_take_layer_columns_along_the_flow_and_stay_in_their_lanes(self) -> None:
        items = self.pool_items(
            {
                "start": ("a", 900.0, 60.0),
                "check": ("b", 500.0, 250.0),
                "ship": ("c", 200.0, 450.0),
                "done": ("a", 300.0, 20.0),
            }
        )
        wires = [_wire("w1", "start", "check"), _wire("w2", "check", "ship"), _wire("w3", "ship", "done")]

        result, final = self.layout(items, wires)

        self.assertEqual(result.laid_out_level_count, 1)
        content_left = SWIMLANE_POOL_HEADER + SWIMLANE_LANE_HEADER + PAD
        step = 100.0 + DEFAULT_TIDY_COLUMN_GAP
        self.assertEqual([final(item_id)[0] for item_id in ("start", "check", "ship", "done")],
                         [content_left + index * step for index in range(4)])
        # One row per lane, centred in it; every lane is sized to what it holds.
        thickness = max(SWIMLANE_MIN_LANE_THICKNESS, 80.0 + 2 * PAD)
        self.assertEqual([final(lane_id)[1] for lane_id in ("a", "b", "c")], [0.0, thickness, 2 * thickness])
        self.assertEqual({final(lane_id)[3] for lane_id in ("a", "b", "c")}, {thickness})
        for item_id, lane_index in (("start", 0), ("check", 1), ("ship", 2), ("done", 0)):
            self.assertEqual(final(item_id)[1], lane_index * thickness + (thickness - 80.0) / 2)
        pool = final("pool")
        self.assertEqual(pool[:2], (0.0, 0.0))
        self.assertEqual(pool[3], 3 * thickness)
        self.assertEqual(pool[2], content_left + 3 * step + 100.0 + PAD)
        self.assertEqual({final(lane_id)[2] for lane_id in ("a", "b", "c")}, {pool[2] - SWIMLANE_POOL_HEADER})

    def test_two_steps_of_one_lane_in_the_same_layer_stack_across_the_lane(self) -> None:
        items = self.pool_items({"root": ("a", 100.0, 60.0), "left": ("b", 300.0, 210.0), "right": ("b", 300.0, 300.0)})
        wires = [_wire("w1", "root", "left"), _wire("w2", "root", "right")]

        _result, final = self.layout(items, wires)

        self.assertEqual(final("left")[0], final("right")[0])
        self.assertEqual(final("right")[1] - final("left")[1], 80.0 + DEFAULT_TIDY_ROW_GAP)
        self.assertEqual(final("b")[3], 2 * 80.0 + DEFAULT_TIDY_ROW_GAP + 2 * PAD)

    def test_unwired_steps_take_the_first_free_columns_of_their_lane(self) -> None:
        items = self.pool_items({"x": ("a", 100.0, 60.0), "y": ("a", 400.0, 60.0), "lone": ("a", 700.0, 60.0)})
        wires = [_wire("w1", "x", "y")]

        _result, final = self.layout(items, wires)

        content_left = SWIMLANE_POOL_HEADER + SWIMLANE_LANE_HEADER + PAD
        step = 100.0 + DEFAULT_TIDY_COLUMN_GAP
        # x and y hold columns 0 and 1 of lane a; the unwired step takes column 2 there.
        self.assertEqual([final(item_id)[0] for item_id in ("x", "y", "lone")], [content_left + i * step for i in range(3)])

    def test_a_vertical_pool_lays_the_flow_out_top_to_bottom(self) -> None:
        items = self.pool_items(
            {"start": ("a", 700.0, 60.0), "next": ("b", 100.0, 250.0)},
            orientation="vertical",
        )
        wires = [_wire("w1", "start", "next", ("bottom", "top"))]

        _result, final = self.layout(items, wires)

        start, following = final("start"), final("next")
        self.assertLess(start[1] + start[3], following[1])  # the flow runs down
        self.assertGreater(following[0], start[0])  # lane b is right of lane a
        self.assertEqual(final("a")[0], 0.0)
        self.assertEqual(final("b")[0], final("a")[0] + final("a")[2])
        self.assertEqual(final("a")[1], SWIMLANE_POOL_HEADER)

    def test_in_place_mode_keeps_the_current_column_order(self) -> None:
        items = self.pool_items({"first": ("b", 150.0, 250.0), "second": ("a", 600.0, 40.0), "third": ("c", 900.0, 470.0)})

        _result, final = self.layout(items, [], mode=TIDY_MODE_IN_PLACE)

        xs = [final(item_id)[0] for item_id in ("first", "second", "third")]
        self.assertEqual(xs, sorted(xs))
        self.assertEqual(len(set(xs)), 3)


class SceneSwimlaneTidyTests(_SwimlaneCase):
    def build_flow(self):  # noqa: ANN201
        pool_id, (customer, sales, warehouse) = self.pool(lanes=("Customer", "Sales", "Warehouse"))
        steps = {
            "start": self.add(START, 900.0, 40.0),
            "order": self.add(PROCESS, 200.0, 250.0),
            "check": self.add(DECISION, 700.0, 230.0),
            "pick": self.add(PROCESS, 300.0, 450.0),
            "ship": self.add(PROCESS, 800.0, 470.0),
            "done": self.add(START, 250.0, 80.0),
        }
        chain = ("start", "order", "check", "pick", "ship", "done")
        for source, target in zip(chain, chain[1:]):
            self.assertTrue(self.scene.add_edge(steps[source], "right", steps[target], "left"))
        lanes = {"Customer": customer, "Sales": sales, "Warehouse": warehouse}
        return pool_id, lanes, steps

    def test_tidy_lays_a_pool_out_lane_by_lane_in_one_undo_step(self) -> None:
        pool_id, lanes, steps = self.build_flow()
        owners = {name: self.owner(node_id) for name, node_id in steps.items()}
        depth = self.undo_depth()

        outcome = self.scene.tidy_layout([pool_id])

        self.assertTrue(outcome["changed"])
        self.assertEqual(outcome["membership_conflict_node_ids"], [])
        self.assertEqual(self.undo_depth(), depth + 1)
        self.assertEqual({name: self.owner(node_id) for name, node_id in steps.items()}, owners)
        xs = [self.scene.node_bounds(steps[name]).x() for name in ("start", "order", "check", "pick", "ship", "done")]
        self.assertEqual(xs, sorted(xs))
        self.assertEqual(len(set(round(x) for x in xs)), 6)
        for name in steps:
            self.assert_inside(owners[name], steps[name])
        # Steps of one lane share its centre line.
        for first, second in (("start", "done"), ("pick", "ship")):
            a = self.scene.node_bounds(steps[first])
            b = self.scene.node_bounds(steps[second])
            self.assertAlmostEqual(a.y() + a.height() / 2, b.y() + b.height() / 2)
        self.assert_stacked(pool_id)

        repeat = self.scene.tidy_layout([pool_id])
        self.assertFalse(repeat["changed"])
        self.assertEqual(self.undo_depth(), depth + 1)

    def test_tidying_a_lane_tidies_its_pool(self) -> None:
        pool_id, lanes, steps = self.build_flow()

        outcome = self.scene.tidy_layout([lanes["Sales"]])

        self.assertTrue(outcome["changed"])
        self.assertIn(pool_id, outcome["resized_group_ids"])
        self.assertEqual(set(steps.values()) - set(outcome["arranged_node_ids"]), set())

    def test_tidying_the_whole_scope_keeps_a_pool_laid_out_lane_by_lane(self) -> None:
        pool_id, lanes, steps = self.build_flow()
        outside = self.add(PROCESS, 3000.0, 3000.0)

        outcome = self.scene.tidy_layout(None)

        self.assertTrue(outcome["changed"])
        self.assertEqual(self.owner(outside), None)
        for name, lane_name in (("start", "Customer"), ("order", "Sales"), ("pick", "Warehouse")):
            self.assertEqual(self.owner(steps[name]), lanes[lane_name])
        self.assert_stacked(pool_id)

    def test_the_automation_op_tidies_one_pool(self) -> None:
        from tests.automation.harness import call

        pool_id, lanes, steps = self.build_flow()

        result = call(self.context, "layout.tidy", {"node_ids": [pool_id]})

        self.assertTrue(result["changed"])
        self.assertEqual(result["membership_conflict_node_ids"], [])


if __name__ == "__main__":
    unittest.main()
