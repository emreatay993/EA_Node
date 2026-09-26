# Purpose: .cxproj round trip for swimlane pools: pool and lane records (type, orientation, role names, colours, frames), lane order and lane membership after reload, standalone lanes, and a collapsed pool's stored member list.
# Map: feature_routes/swimlane_pools_lanes
# Tests: tests/test_swimlane_persistence.py
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.ui.shell.runtime_history import RuntimeGraphHistory
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from tests.automation.harness import build_context, ensure_app, shared_registry

POOL = "passive.annotation.swimlane_pool"
LANE = "passive.annotation.swimlane_lane"
PROCESS = "passive.flowchart.process"
# Membership is derived from geometry on every load, never written into the document.
_RUNTIME_MEMBERSHIP_KEYS = ("owner_backdrop_id", "member_node_ids", "member_backdrop_ids", "contained_node_ids")


class SwimlaneProjectRoundTripTests(unittest.TestCase):
    def setUp(self) -> None:
        self.context = build_context()
        self.scene = self.context.scene
        self._temp = tempfile.TemporaryDirectory()
        self.addCleanup(self._temp.cleanup)

    def _structure(self, scene: GraphSceneBridge) -> list[tuple]:
        pools = sorted(
            (
                pool["pool_node_id"],
                pool["title"],
                pool["orientation"],
                pool["collapsed"],
                tuple(
                    (lane["lane_node_id"], lane["title"], lane["color"], tuple(lane["node_ids"]))
                    for lane in pool["lanes"]
                ),
            )
            for pool in scene.describe_swimlane_pools()
        )
        standalone = sorted(
            ("", lane["title"], lane["orientation"], False, ((lane["lane_node_id"], lane["title"], lane["color"], tuple(lane["node_ids"])),))
            for lane in scene.describe_standalone_swimlane_lanes()
        )
        return [*pools, *standalone]

    def _reload(self, path: Path) -> tuple[GraphModel, GraphSceneBridge]:
        ensure_app()
        project = JsonProjectSerializer(shared_registry()).load(str(path))
        model = GraphModel(project)
        scene = GraphSceneBridge()
        scene.set_workspace(model, shared_registry(), self.context.workspace_id())
        scene.bind_runtime_history(RuntimeGraphHistory())
        return model, scene

    def test_pools_lanes_and_membership_survive_a_cxproj_round_trip(self) -> None:
        scene = self.scene
        pool_id, (customer, sales) = scene.create_swimlane_pool(0.0, 0.0, title="Order", lane_titles=["Customer", "Sales"])
        first = scene.add_node_from_type(PROCESS, 300.0, 60.0)
        second = scene.add_node_from_type(PROCESS, 700.0, 260.0)
        self.assertTrue(scene.add_edge(first, "right", second, "left"))
        scene.tidy_layout([pool_id])
        vertical_id, vertical_lanes = scene.create_swimlane_pool(
            2000.0, 0.0, title="Support", orientation="vertical", lane_titles=["Agent", "Engineer"]
        )
        scene.add_node_from_type(PROCESS, 2020.0, 300.0)
        scene.set_node_property(customer, "color", "#e8a33d")
        solo = scene.create_swimlane_lane(4000.0, 0.0, title="Solo")
        solo_node = scene.add_node_from_type(PROCESS, 4100.0, 60.0)
        folded_id, folded_lanes = scene.create_swimlane_pool(0.0, 2000.0, title="Folded", lane_titles=["X"])
        folded_node = scene.add_node_from_type(PROCESS, 300.0, 2060.0)
        self.assertTrue(scene.set_node_collapsed(folded_id, True))
        workspace = self.context.active_workspace()
        folded_held = tuple(sorted(workspace.nodes[folded_id].held_member_ids))
        self.assertEqual(folded_held, tuple(sorted([*folded_lanes, folded_node])))
        # Collapsing froze each lane's own list too (a lane hidden in a collapsed pool is an identity Group).
        lane_held = {lane_id: workspace.nodes[lane_id].held_member_ids for lane_id in folded_lanes}
        self.assertEqual(lane_held, {folded_lanes[0]: (folded_node,)})
        before = self._structure(scene)
        frames_before = {
            node_id: (node.x, node.y, node.custom_width, node.custom_height, dict(node.properties))
            for node_id, node in workspace.nodes.items()
            if node.type_id in (POOL, LANE)
        }

        path = Path(self._temp.name) / "swimlanes.cxproj"
        JsonProjectSerializer(shared_registry()).save(str(path), self.context.stored_model.project)

        document = json.loads(path.read_text(encoding="utf-8"))
        node_docs = {doc["node_id"]: doc for workspace_doc in document["workspaces"] for doc in workspace_doc["nodes"]}
        self.assertEqual(node_docs[pool_id]["type_id"], POOL)
        self.assertEqual(node_docs[pool_id]["properties"], {"title": "Order", "orientation": "horizontal"})
        self.assertEqual(
            node_docs[customer]["properties"], {"title": "Customer", "orientation": "horizontal", "color": "#e8a33d"}
        )
        self.assertEqual(node_docs[solo]["type_id"], LANE)
        self.assertEqual(node_docs[vertical_lanes[0]]["properties"]["orientation"], "vertical")
        self.assertEqual(sorted(node_docs[folded_id]["held_member_ids"]), sorted(folded_held))
        for doc in node_docs.values():
            for key in _RUNTIME_MEMBERSHIP_KEYS:
                self.assertNotIn(key, doc)

        # The load itself (before any scene fills in missing lists) keeps the pool's and its lanes' member lists.
        loaded = JsonProjectSerializer(shared_registry()).load(str(path)).workspaces[self.context.workspace_id()]
        self.assertEqual(tuple(sorted(loaded.nodes[folded_id].held_member_ids or ())), folded_held)
        self.assertEqual({lane_id: loaded.nodes[lane_id].held_member_ids for lane_id in folded_lanes}, lane_held)

        model, reloaded = self._reload(path)

        reloaded_workspace = model.project.workspaces[self.context.workspace_id()]
        self.assertEqual(
            {
                node_id: (node.x, node.y, node.custom_width, node.custom_height, dict(node.properties))
                for node_id, node in reloaded_workspace.nodes.items()
                if node.type_id in (POOL, LANE)
            },
            frames_before,
        )
        self.assertEqual(self._structure(reloaded), before)
        # The collapsed pool kept its identity list through the load-time member-list sanitising.
        self.assertEqual(tuple(sorted(reloaded_workspace.nodes[folded_id].held_member_ids)), folded_held)
        self.assertTrue(reloaded.set_node_collapsed(folded_id, False))
        folded = next(pool for pool in reloaded.describe_swimlane_pools() if pool["pool_node_id"] == folded_id)
        self.assertEqual(folded["lane_node_ids"], list(folded_lanes))
        self.assertEqual(folded["lanes"][0]["node_ids"], [folded_node])
        self.assertEqual(vertical_id in {pool["pool_node_id"] for pool in reloaded.describe_swimlane_pools()}, True)
        self.assertEqual(sales in reloaded_workspace.nodes, True)
        # A standalone lane stays on its own and keeps what it holds.
        solo_lanes = {lane["lane_node_id"]: lane["node_ids"] for lane in reloaded.describe_standalone_swimlane_lanes()}
        self.assertEqual(solo_lanes, {solo: [solo_node]})

    def test_a_reloaded_pool_keeps_restacking_its_lanes(self) -> None:
        pool_id, (a, b) = self.scene.create_swimlane_pool(0.0, 0.0, lane_titles=["A", "B"])
        node_id = self.scene.add_node_from_type(PROCESS, 300.0, 260.0)
        path = Path(self._temp.name) / "restack.cxproj"
        JsonProjectSerializer(shared_registry()).save(str(path), self.context.stored_model.project)

        model, reloaded = self._reload(path)
        workspace = model.project.workspaces[self.context.workspace_id()]
        lane = workspace.nodes[a]
        reloaded.set_node_geometry(a, lane.x, lane.y, lane.custom_width, 320.0)

        self.assertEqual(workspace.nodes[b].y, 320.0)
        self.assertEqual(workspace.nodes[node_id].y, 380.0)
        self.assertEqual(workspace.nodes[pool_id].custom_height, 520.0)


if __name__ == "__main__":
    unittest.main()
