from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.settings import SCHEMA_VERSION
from ea_node_editor.workspace.manager import WorkspaceManager

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "persistence"


class SerializerTests(unittest.TestCase):
    def test_round_trip_preserves_workspace_view_and_graph(self) -> None:
        model = GraphModel()
        workspace = model.active_workspace
        view = model.create_view(workspace.workspace_id, name="V2")
        model.set_active_view(workspace.workspace_id, view.view_id)
        node_a = model.add_node(workspace.workspace_id, "core.start", "Start", 10, 20)
        node_b = model.add_node(workspace.workspace_id, "core.end", "End", 80, 120)
        edge = model.add_edge(workspace.workspace_id, node_a.node_id, "exec_out", node_b.node_id, "exec_in")

        serializer = JsonProjectSerializer()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.sfe"
            serializer.save(str(path), model.project)
            loaded = serializer.load(str(path))

        self.assertEqual(loaded.active_workspace_id, workspace.workspace_id)
        loaded_ws = loaded.workspaces[workspace.workspace_id]
        self.assertEqual(loaded_ws.active_view_id, view.view_id)
        self.assertIn(node_a.node_id, loaded_ws.nodes)
        self.assertIn(node_b.node_id, loaded_ws.nodes)
        self.assertIn(edge.edge_id, loaded_ws.edges)

    def test_round_trip_preserves_workspace_order_active_workspace_and_view_cameras(self) -> None:
        model = GraphModel()
        manager = WorkspaceManager(model)
        first = manager.active_workspace_id()
        second = manager.create_workspace("Second")
        manager.move_workspace(1, 0)
        manager.set_active_workspace(second)

        first_ws = model.project.workspaces[first]
        first_v1 = first_ws.views[first_ws.active_view_id]
        first_v1.zoom = 1.1
        first_v1.pan_x = 10.0
        first_v1.pan_y = 20.0
        first_v2 = model.create_view(first, name="V2")
        model.project.workspaces[first].views[first_v2.view_id].zoom = 1.8
        model.project.workspaces[first].views[first_v2.view_id].pan_x = 150.0
        model.project.workspaces[first].views[first_v2.view_id].pan_y = -45.0
        model.set_active_view(first, first_v2.view_id)

        second_ws = model.project.workspaces[second]
        second_v1 = second_ws.views[second_ws.active_view_id]
        second_v1.zoom = 0.85
        second_v1.pan_x = -12.0
        second_v1.pan_y = 34.0
        second_v2 = model.create_view(second, name="V2")
        model.project.workspaces[second].views[second_v2.view_id].zoom = 2.2
        model.project.workspaces[second].views[second_v2.view_id].pan_x = 300.0
        model.project.workspaces[second].views[second_v2.view_id].pan_y = 99.0
        model.set_active_view(second, second_v2.view_id)

        serializer = JsonProjectSerializer()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "project.sfe"
            serializer.save(str(path), model.project)
            loaded = serializer.load(str(path))

        self.assertEqual(loaded.metadata.get("workspace_order"), [second, first])
        self.assertEqual(loaded.active_workspace_id, second)
        self.assertEqual(loaded.workspaces[first].active_view_id, first_v2.view_id)
        self.assertEqual(loaded.workspaces[second].active_view_id, second_v2.view_id)
        self.assertEqual(loaded.workspaces[first].views[first_v1.view_id].zoom, 1.1)
        self.assertEqual(loaded.workspaces[first].views[first_v1.view_id].pan_x, 10.0)
        self.assertEqual(loaded.workspaces[first].views[first_v1.view_id].pan_y, 20.0)
        self.assertEqual(loaded.workspaces[first].views[first_v2.view_id].zoom, 1.8)
        self.assertEqual(loaded.workspaces[first].views[first_v2.view_id].pan_x, 150.0)
        self.assertEqual(loaded.workspaces[first].views[first_v2.view_id].pan_y, -45.0)
        self.assertEqual(loaded.workspaces[second].views[second_v1.view_id].zoom, 0.85)
        self.assertEqual(loaded.workspaces[second].views[second_v1.view_id].pan_x, -12.0)
        self.assertEqual(loaded.workspaces[second].views[second_v1.view_id].pan_y, 34.0)
        self.assertEqual(loaded.workspaces[second].views[second_v2.view_id].zoom, 2.2)
        self.assertEqual(loaded.workspaces[second].views[second_v2.view_id].pan_x, 300.0)
        self.assertEqual(loaded.workspaces[second].views[second_v2.view_id].pan_y, 99.0)

    def test_save_output_is_deterministic_and_uses_workspace_order(self) -> None:
        model = GraphModel()
        manager = WorkspaceManager(model)
        first = manager.active_workspace_id()
        second = manager.create_workspace("Second")
        manager.move_workspace(1, 0)
        manager.set_active_workspace(second)

        workspace = model.project.workspaces[second]
        workspace.ensure_default_view()
        view = workspace.views[workspace.active_view_id]
        view.zoom = 1.42
        view.pan_x = -30.0
        view.pan_y = 45.0
        source = model.add_node(second, "core.start", "Start", 12.0, 20.0)
        target = model.add_node(second, "core.logger", "Logger", 80.0, 20.0)
        edge = model.add_edge(second, source.node_id, "trigger", target.node_id, "message")
        self.assertIsNotNone(edge.edge_id)

        serializer = JsonProjectSerializer()
        doc = serializer.to_document(model.project)
        self.assertEqual(doc["workspace_order"], [second, first])
        self.assertEqual([ws["workspace_id"] for ws in doc["workspaces"]], [second, first])
        self.assertEqual(doc["active_workspace_id"], second)

        with tempfile.TemporaryDirectory() as temp_dir:
            path_a = Path(temp_dir) / "a.sfe"
            path_b = Path(temp_dir) / "b.sfe"
            serializer.save(str(path_a), model.project)
            serializer.save(str(path_b), model.project)
            self.assertEqual(path_a.read_text(encoding="utf-8"), path_b.read_text(encoding="utf-8"))

    def test_migrate_v0_fixture_adds_defaults_and_normalizes_workspace_and_view(self) -> None:
        serializer = JsonProjectSerializer()
        payload = json.loads((FIXTURES_DIR / "schema_v0_minimal.json").read_text(encoding="utf-8"))
        project = serializer.from_document(payload)

        self.assertEqual(project.schema_version, SCHEMA_VERSION)
        self.assertEqual(project.active_workspace_id, "ws_a")
        self.assertEqual(project.metadata.get("workspace_order"), ["ws_a", "ws_b"])
        self.assertEqual(project.workspaces["ws_b"].active_view_id, "view_b1")

    def test_migrate_v0_fixture_repairs_invalid_hidden_and_duplicate_edges(self) -> None:
        serializer = JsonProjectSerializer()
        payload = json.loads((FIXTURES_DIR / "schema_v0_inconsistent.json").read_text(encoding="utf-8"))
        project = serializer.from_document(payload)

        self.assertEqual(project.schema_version, SCHEMA_VERSION)
        workspace = project.workspaces["ws_legacy"]
        self.assertNotIn("node_unknown", workspace.nodes)
        self.assertEqual(set(workspace.edges), {"edge_valid"})
        edge = workspace.edges["edge_valid"]
        self.assertEqual(
            (edge.source_node_id, edge.source_port_key, edge.target_node_id, edge.target_port_key),
            ("node_start", "trigger", "node_logger", "message"),
        )
        self.assertEqual(project.metadata.get("workspace_order"), ["ws_legacy"])


if __name__ == "__main__":
    unittest.main()
