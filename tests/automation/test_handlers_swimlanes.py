# Purpose: Shell-free handler tests for the swimlane.* ops (create a pool and lanes, a standalone lane, add/remove/move lanes, pools forming and dissolving, assign nodes, describe) and a pool-only layout.tidy, with one-undo-step pins, typed errors, graph.apply batching and the client facade.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_swimlanes.py
from __future__ import annotations

import unittest
from typing import Any

from ea_node_editor.automation.client_api.structure import StructureApi
from ea_node_editor.automation.errors import INVALID_PARAMS, NO_EFFECT, NOT_FOUND
from tests.automation.harness import build_context, call, expect_error

POOL = "passive.annotation.swimlane_pool"
LANE = "passive.annotation.swimlane_lane"
PROCESS = "passive.flowchart.process"


class _SwimlaneHandlerCase(unittest.TestCase):
    def setUp(self) -> None:
        self.context = build_context()
        self.scene = self.context.scene

    def undo_depth(self) -> int:
        return self.context.runtime_history.undo_depth(self.context.workspace_id())

    def call_one_undo(self, op: str, params: dict[str, Any]) -> dict[str, Any]:
        before = self.undo_depth()
        result = call(self.context, op, params)
        self.assertEqual(self.undo_depth(), before + 1, f"{op} must add exactly one undo entry")
        return result

    def call_no_undo(self, op: str, params: dict[str, Any]) -> dict[str, Any]:
        before = self.undo_depth()
        result = call(self.context, op, params)
        self.assertEqual(self.undo_depth(), before, f"{op} must not add undo entries")
        return result

    def create(self, **params: Any) -> dict[str, Any]:
        return self.call_one_undo("swimlane.create_pool", {"x": 0, "y": 0, **params})


class SwimlaneOpTests(_SwimlaneHandlerCase):
    def test_create_pool_returns_its_lanes_in_stack_order(self) -> None:
        result = self.create(title="Order", lanes=["Customer", "Sales", "Warehouse"], lane_size=160, length=900)

        pool = result["pool"]
        self.assertEqual(pool["pool_node_id"], result["pool_node_id"])
        self.assertEqual(pool["title"], "Order")
        self.assertEqual(pool["orientation"], "horizontal")
        self.assertEqual(pool["lane_node_ids"], result["lane_node_ids"])
        self.assertEqual([lane["title"] for lane in pool["lanes"]], ["Customer", "Sales", "Warehouse"])
        workspace = self.context.active_workspace()
        self.assertEqual(workspace.nodes[result["pool_node_id"]].type_id, POOL)
        self.assertEqual(workspace.nodes[result["pool_node_id"]].custom_width, 900.0)
        self.assertEqual({workspace.nodes[lane_id].custom_height for lane_id in result["lane_node_ids"]}, {160.0})
        self.assertEqual({workspace.nodes[lane_id].type_id for lane_id in result["lane_node_ids"]}, {LANE})

    def test_create_pool_defaults_to_three_lanes_and_takes_a_vertical_orientation(self) -> None:
        default = self.create()
        vertical = self.create(orientation="vertical", lanes=["A", "B"])

        self.assertEqual(len(default["lane_node_ids"]), 3)
        self.assertEqual(vertical["pool"]["orientation"], "vertical")
        workspace = self.context.active_workspace()
        first, second = (workspace.nodes[lane_id] for lane_id in vertical["lane_node_ids"])
        self.assertEqual(second.x, first.x + first.custom_width)
        expect_error(self.context, "swimlane.create_pool", {"x": 0, "y": 0, "lanes": ["A", " "]}, INVALID_PARAMS)
        expect_error(self.context, "swimlane.create_pool", {"x": 0, "y": 0, "lane_size": 20}, INVALID_PARAMS)

    def test_add_move_and_remove_lanes(self) -> None:
        created = self.create(lanes=["A", "B"])
        pool_id = created["pool_node_id"]
        a, b = created["lane_node_ids"]

        added = self.call_one_undo("swimlane.add_lane", {"pool_node_id": pool_id, "title": "First", "index": 0})
        self.assertEqual(added["lane_node_ids"], [added["lane_node_id"], a, b])

        moved = self.call_one_undo("swimlane.move_lane", {"lane_node_id": added["lane_node_id"], "index": 9})
        self.assertEqual(moved["lane_node_ids"], [a, b, added["lane_node_id"]])
        expect_error(self.context, "swimlane.move_lane", {"lane_node_id": a, "index": 0}, NO_EFFECT)

        removed = self.call_one_undo("swimlane.remove_lane", {"lane_node_id": b})
        self.assertEqual(removed["removed_lane_node_id"], b)
        self.assertEqual(removed["lane_node_ids"], [a, added["lane_node_id"]])
        self.assertNotIn(b, self.context.active_workspace().nodes)

    def test_assign_moves_nodes_into_a_lane_once(self) -> None:
        created = self.create(lanes=["A", "B"])
        a, b = created["lane_node_ids"]
        first = self.scene.add_node_from_type(PROCESS, 3000.0, 3000.0)
        second = self.scene.add_node_from_type(PROCESS, 3400.0, 3000.0)

        result = self.call_one_undo("swimlane.assign", {"node_ids": [first, second], "lane_node_id": b})

        self.assertEqual(result["assigned_node_ids"], [first, second])
        lanes = {lane["lane_node_id"]: lane["node_ids"] for lane in result["pool"]["lanes"]}
        self.assertEqual(sorted(lanes[b]), sorted([first, second]))
        self.assertEqual(lanes[a], [])
        expect_error(self.context, "swimlane.assign", {"node_ids": [first], "lane_node_id": b}, NO_EFFECT)
        expect_error(self.context, "swimlane.assign", {"node_ids": [a], "lane_node_id": b}, INVALID_PARAMS)

    def test_describe_lists_every_pool_or_one(self) -> None:
        first = self.create(lanes=["A", "B"])
        second = self.create(lanes=["C", "D"], y=2000)
        self.scene.set_node_collapsed(second["pool_node_id"], True)
        solo = self.call_one_undo("swimlane.create_lane", {"x": 0, "y": 4000, "title": "Solo"})

        every = self.call_no_undo("swimlane.describe", {})
        one = self.call_no_undo("swimlane.describe", {"pool_node_id": first["pool_node_id"]})

        self.assertEqual(
            sorted((pool["pool_node_id"], pool["collapsed"], len(pool["lanes"])) for pool in every["pools"]),
            sorted([(first["pool_node_id"], False, 2), (second["pool_node_id"], True, 0)]),
        )
        self.assertEqual(
            [(lane["lane_node_id"], lane["title"], lane["orientation"]) for lane in every["lanes"]],
            [(solo["lane_node_id"], "Solo", "horizontal")],
        )
        self.assertEqual([pool["pool_node_id"] for pool in one["pools"]], [first["pool_node_id"]])
        self.assertEqual(one["lanes"], [])

    def test_wrong_node_kinds_and_unknown_ids_fail_before_any_change(self) -> None:
        created = self.create(lanes=["A", "B"])
        process = self.scene.add_node_from_type(PROCESS, 3000.0, 0.0)
        before = self.undo_depth()

        expect_error(self.context, "swimlane.create_pool", {"x": 0, "y": 0, "lanes": ["Only"]}, INVALID_PARAMS)
        expect_error(self.context, "swimlane.add_lane", {"pool_node_id": process}, INVALID_PARAMS)
        expect_error(self.context, "swimlane.add_lane", {"pool_node_id": created["lane_node_ids"][0]}, INVALID_PARAMS)
        expect_error(self.context, "swimlane.add_lane", {"lane_node_id": created["pool_node_id"]}, INVALID_PARAMS)
        expect_error(self.context, "swimlane.add_lane", {}, INVALID_PARAMS)
        expect_error(
            self.context,
            "swimlane.add_lane",
            {"pool_node_id": created["pool_node_id"], "lane_node_id": created["lane_node_ids"][0]},
            INVALID_PARAMS,
        )
        expect_error(self.context, "swimlane.remove_lane", {"lane_node_id": created["pool_node_id"]}, INVALID_PARAMS)
        expect_error(self.context, "swimlane.move_lane", {"lane_node_id": "node_missing", "index": 0}, NOT_FOUND)
        expect_error(self.context, "swimlane.describe", {"pool_node_id": process}, INVALID_PARAMS)
        self.scene.set_node_collapsed(created["pool_node_id"], True)
        before = self.undo_depth()
        expect_error(self.context, "swimlane.add_lane", {"pool_node_id": created["pool_node_id"]}, INVALID_PARAMS)
        self.assertEqual(self.undo_depth(), before)

    def test_layout_tidy_takes_a_single_pool(self) -> None:
        created = self.create(lanes=["A", "B"])
        a, b = created["lane_node_ids"]
        first = self.scene.add_node_from_type(PROCESS, 700.0, 60.0)
        second = self.scene.add_node_from_type(PROCESS, 200.0, 260.0)
        call(self.context, "edge.connect", {"source_node_id": first, "source_port": "right", "target_node_id": second, "target_port": "left"})

        result = self.call_one_undo("layout.tidy", {"node_ids": [created["pool_node_id"]]})

        self.assertTrue(result["changed"])
        workspace = self.context.active_workspace()
        self.assertLess(workspace.nodes[first].x, workspace.nodes[second].x)

    def test_graph_apply_builds_a_pool_and_fills_its_lanes_in_one_step(self) -> None:
        before = self.undo_depth()
        result = call(
            self.context,
            "graph.apply",
            {
                "ops": [
                    {"id": "pool", "op": "swimlane.create_pool", "params": {"x": 0, "y": 0, "lanes": ["Customer", "Sales"]}},
                    {"id": "ask", "op": "node.add", "params": {"type_id": PROCESS, "x": 3000, "y": 0, "title": "Ask"}},
                    {"id": "quote", "op": "node.add", "params": {"type_id": PROCESS, "x": 3400, "y": 0, "title": "Quote"}},
                    {"op": "swimlane.assign", "params": {"node_ids": ["$ask"], "lane_node_id": "$pool.lane_node_ids.0"}},
                    {"op": "swimlane.assign", "params": {"node_ids": ["$quote"], "lane_node_id": "$pool.lane_node_ids.1"}},
                    {"op": "edge.connect", "params": {"source_node_id": "$ask", "source_port": "right", "target_node_id": "$quote", "target_port": "left"}},
                    {"op": "layout.tidy", "params": {"node_ids": ["$pool"]}},
                ]
            },
        )

        self.assertEqual(self.undo_depth(), before + 1)
        pool = call(self.context, "swimlane.describe", {})["pools"][0]
        titles = {lane["title"]: lane["node_ids"] for lane in pool["lanes"]}
        workspace = self.context.active_workspace()
        self.assertEqual([workspace.nodes[node_id].title for node_id in titles["Customer"]], ["Ask"])
        self.assertEqual([workspace.nodes[node_id].title for node_id in titles["Sales"]], ["Quote"])
        self.assertIsNotNone(result)


class _RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def call(self, op: str, params: dict[str, Any] | None = None, **_kwargs: Any) -> dict[str, Any]:
        self.calls.append((op, dict(params or {})))
        return {"ok": True}


class SwimlaneFacadeTests(unittest.TestCase):
    def test_structure_facade_builds_swimlane_params(self) -> None:
        client = _RecordingClient()
        api = StructureApi(client)
        api.create_pool(0, 10, title="Order", orientation="vertical", lanes=("A", "B"), lane_size=160, length=900)
        api.create_pool(5, 5)
        api.add_lane("pool", title="C", index=1)
        api.add_lane("pool")
        api.remove_lane("lane")
        api.move_lane("lane", 2)
        api.assign_to_lane("node", "lane")
        api.assign_to_lane(["n1", "n2"], "lane")
        api.describe_pools()
        api.describe_pools("pool")
        self.assertEqual(
            client.calls,
            [
                (
                    "swimlane.create_pool",
                    {
                        "x": 0.0,
                        "y": 10.0,
                        "title": "Order",
                        "orientation": "vertical",
                        "lanes": ["A", "B"],
                        "lane_size": 160.0,
                        "length": 900.0,
                    },
                ),
                ("swimlane.create_pool", {"x": 5.0, "y": 5.0}),
                ("swimlane.add_lane", {"pool_node_id": "pool", "title": "C", "index": 1}),
                ("swimlane.add_lane", {"pool_node_id": "pool"}),
                ("swimlane.remove_lane", {"lane_node_id": "lane"}),
                ("swimlane.move_lane", {"lane_node_id": "lane", "index": 2}),
                ("swimlane.assign", {"node_ids": ["node"], "lane_node_id": "lane"}),
                ("swimlane.assign", {"node_ids": ["n1", "n2"], "lane_node_id": "lane"}),
                ("swimlane.describe", {}),
                ("swimlane.describe", {"pool_node_id": "pool"}),
            ],
        )


class SwimlaneLaneFirstOpTests(_SwimlaneHandlerCase):
    def test_a_lane_on_its_own_then_a_lane_next_to_it_forms_a_pool(self) -> None:
        solo = self.call_one_undo("swimlane.create_lane", {"x": 100, "y": 100, "title": "Customer"})
        lane_id = solo["lane_node_id"]
        self.assertEqual(solo["pool_node_id"], "")
        workspace = self.context.active_workspace()
        self.assertEqual(workspace.nodes[lane_id].type_id, LANE)
        self.assertEqual((workspace.nodes[lane_id].x, workspace.nodes[lane_id].y), (100.0, 100.0))

        added = self.call_one_undo("swimlane.add_lane", {"lane_node_id": lane_id, "title": "Sales"})

        self.assertTrue(added["pool_node_id"])
        self.assertEqual(added["lane_node_ids"], [lane_id, added["lane_node_id"]])
        self.assertEqual(workspace.nodes[added["pool_node_id"]].type_id, POOL)
        self.assertEqual(workspace.nodes[added["lane_node_id"]].title, "Sales")
        before = self.call_one_undo("swimlane.add_lane", {"lane_node_id": lane_id, "after": False})
        self.assertEqual(before["lane_node_ids"][:2], [before["lane_node_id"], lane_id])

    def test_removing_down_to_one_lane_reports_the_dissolved_pool(self) -> None:
        created = self.create(lanes=["A", "B"])
        a, b = created["lane_node_ids"]

        removed = self.call_one_undo("swimlane.remove_lane", {"lane_node_id": b})

        self.assertEqual(removed["dissolved_pool_node_id"], created["pool_node_id"])
        self.assertEqual(removed["lane_node_ids"], [a])
        self.assertNotIn(created["pool_node_id"], self.context.active_workspace().nodes)
        described = self.call_no_undo("swimlane.describe", {})
        self.assertEqual(([pool["pool_node_id"] for pool in described["pools"]], [lane["lane_node_id"] for lane in described["lanes"]]), ([], [a]))
        last = self.call_one_undo("swimlane.remove_lane", {"lane_node_id": a})
        self.assertEqual((last["dissolved_pool_node_id"], last["lane_node_ids"]), ("", []))

    def test_assign_to_a_lane_on_its_own(self) -> None:
        solo = self.call_one_undo("swimlane.create_lane", {"x": 0, "y": 0, "orientation": "vertical"})
        node_id = self.scene.add_node_from_type(PROCESS, 3000.0, 3000.0)

        result = self.call_one_undo("swimlane.assign", {"node_ids": [node_id], "lane_node_id": solo["lane_node_id"]})

        self.assertIsNone(result["pool"])
        self.assertEqual(result["lane"]["node_ids"], [node_id])
        self.assertEqual(result["lane"]["orientation"], "vertical")

    def test_a_lane_colour_is_a_property(self) -> None:
        created = self.create(lanes=["A", "B"])
        a = created["lane_node_ids"][0]

        self.call_one_undo("node.update", {"node_id": a, "properties": {"color": "#e8a33d"}})

        described = self.call_no_undo("swimlane.describe", {"pool_node_id": created["pool_node_id"]})
        self.assertEqual(described["pools"][0]["lanes"][0]["color"], "#e8a33d")


if __name__ == "__main__":
    unittest.main()
