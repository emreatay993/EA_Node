from __future__ import annotations

import unittest

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge

COMMENT_BACKDROP_TYPE_ID = "passive.annotation.comment_backdrop"


class CommentBackdropClipboardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = build_default_registry()
        self.model = GraphModel()
        self.workspace_id = self.model.active_workspace.workspace_id
        self.scene = GraphSceneBridge()
        self.scene.set_workspace(self.model, self.registry, self.workspace_id)

    def _scene_payload(self, node_id: str) -> dict[str, object]:
        for payload in [*self.scene.nodes_model, *self.scene.backdrop_nodes_model]:
            if str(payload.get("node_id", "")) == str(node_id):
                return payload
        raise AssertionError(f"Node payload {node_id!r} was not found.")

    def _wrap_nodes_in_backdrop(self, node_ids: list[str], *, collapsed: bool = False) -> str:
        backdrop_id = self.scene.wrap_node_ids_in_comment_backdrop(node_ids)
        self.assertTrue(backdrop_id)
        self.scene.set_node_collapsed(backdrop_id, collapsed)
        return backdrop_id

    def test_expanded_comment_backdrop_copy_keeps_descendants_explicit_only(self) -> None:
        logger_id = self.scene.add_node_from_type("core.logger", 110.0, 110.0)
        backdrop_id = self._wrap_nodes_in_backdrop([logger_id], collapsed=False)
        self.assertEqual(self._scene_payload(logger_id)["owner_backdrop_id"], backdrop_id)

        self.scene.select_node(backdrop_id, False)
        fragment = self.scene.serialize_selected_subgraph_fragment()

        self.assertIsNotNone(fragment)
        assert fragment is not None
        self.assertEqual({node["ref_id"] for node in fragment["nodes"]}, {backdrop_id})
        self.assertEqual(fragment["edges"], [])

    def test_collapsed_comment_backdrop_copy_includes_recursive_descendants_and_internal_edges(self) -> None:
        inner_start_id = self.scene.add_node_from_type("core.start", 220.0, 160.0)
        inner_backdrop_id = self._wrap_nodes_in_backdrop([inner_start_id], collapsed=False)
        outer_end_id = self.scene.add_node_from_type("core.end", 220.0, 360.0)
        outside_script_id = self.scene.add_node_from_type("core.python_script", 760.0, 240.0)
        self.scene.add_edge(inner_start_id, "exec_out", outer_end_id, "exec_in")
        self.scene.add_edge(inner_start_id, "trigger", outside_script_id, "payload")
        outer_backdrop_id = self._wrap_nodes_in_backdrop([inner_backdrop_id, outer_end_id], collapsed=True)

        self.scene.select_node(outer_backdrop_id, False)
        fragment = self.scene.serialize_selected_subgraph_fragment()

        self.assertIsNotNone(fragment)
        assert fragment is not None
        self.assertEqual(
            {node["ref_id"] for node in fragment["nodes"]},
            {outer_backdrop_id, inner_backdrop_id, inner_start_id, outer_end_id},
        )
        self.assertEqual(
            {
                (
                    edge["source_ref_id"],
                    edge["source_port_key"],
                    edge["target_ref_id"],
                    edge["target_port_key"],
                )
                for edge in fragment["edges"]
            },
            {(inner_start_id, "exec_out", outer_end_id, "exec_in")},
        )

    def test_duplicate_selected_collapsed_comment_backdrop_recomputes_membership_for_duplicates(self) -> None:
        start_id = self.scene.add_node_from_type("core.start", 280.0, 220.0)
        backdrop_id = self._wrap_nodes_in_backdrop([start_id], collapsed=True)
        workspace = self.model.project.workspaces[self.workspace_id]
        before_node_ids = set(workspace.nodes)

        self.scene.select_node(backdrop_id, False)
        duplicated = self.scene.duplicate_selected_subgraph()

        self.assertTrue(duplicated)
        new_node_ids = set(workspace.nodes) - before_node_ids
        self.assertEqual(len(new_node_ids), 2)

        duplicate_backdrop_id = next(
            node_id
            for node_id in new_node_ids
            if workspace.nodes[node_id].type_id == COMMENT_BACKDROP_TYPE_ID
        )
        duplicate_start_id = next(
            node_id
            for node_id in new_node_ids
            if workspace.nodes[node_id].type_id == "core.start"
        )
        self.assertAlmostEqual(workspace.nodes[duplicate_backdrop_id].x, workspace.nodes[backdrop_id].x + 40.0, places=6)
        self.assertAlmostEqual(workspace.nodes[duplicate_backdrop_id].y, workspace.nodes[backdrop_id].y + 40.0, places=6)
        self.assertAlmostEqual(workspace.nodes[duplicate_start_id].x, workspace.nodes[start_id].x + 40.0, places=6)
        self.assertAlmostEqual(workspace.nodes[duplicate_start_id].y, workspace.nodes[start_id].y + 40.0, places=6)

        self.scene.set_node_collapsed(duplicate_backdrop_id, False)
        duplicate_backdrop_payload = self._scene_payload(duplicate_backdrop_id)
        duplicate_start_payload = self._scene_payload(duplicate_start_id)
        self.assertEqual(duplicate_start_payload["owner_backdrop_id"], duplicate_backdrop_id)
        self.assertEqual(duplicate_backdrop_payload["member_node_ids"], [duplicate_start_id])

    def test_delete_selected_expanded_comment_backdrop_keeps_descendants(self) -> None:
        start_id = self.scene.add_node_from_type("core.start", 110.0, 110.0)
        backdrop_id = self._wrap_nodes_in_backdrop([start_id], collapsed=False)
        workspace = self.model.project.workspaces[self.workspace_id]

        self.scene.select_node(backdrop_id, False)
        deleted = self.scene.delete_selected_graph_items([])

        self.assertTrue(deleted)
        self.assertNotIn(backdrop_id, workspace.nodes)
        self.assertIn(start_id, workspace.nodes)

    def test_delete_selected_collapsed_comment_backdrop_removes_recursive_descendants(self) -> None:
        inner_start_id = self.scene.add_node_from_type("core.start", 220.0, 160.0)
        inner_backdrop_id = self._wrap_nodes_in_backdrop([inner_start_id], collapsed=False)
        outer_end_id = self.scene.add_node_from_type("core.end", 220.0, 360.0)
        outside_script_id = self.scene.add_node_from_type("core.python_script", 760.0, 240.0)
        self.scene.add_edge(inner_start_id, "exec_out", outer_end_id, "exec_in")
        self.scene.add_edge(inner_start_id, "trigger", outside_script_id, "payload")
        outer_backdrop_id = self._wrap_nodes_in_backdrop([inner_backdrop_id, outer_end_id], collapsed=True)
        workspace = self.model.project.workspaces[self.workspace_id]

        self.scene.select_node(outer_backdrop_id, False)
        deleted = self.scene.delete_selected_graph_items([])

        self.assertTrue(deleted)
        for removed_node_id in (outer_backdrop_id, inner_backdrop_id, inner_start_id, outer_end_id):
            self.assertNotIn(removed_node_id, workspace.nodes)
        self.assertIn(outside_script_id, workspace.nodes)
        self.assertEqual(list(workspace.edges), [])


if __name__ == "__main__":
    unittest.main()
