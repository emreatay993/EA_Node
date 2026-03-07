from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge


class GraphModelTrackBTests(unittest.TestCase):
    def test_add_move_connect_remove_node_operations(self) -> None:
        model = GraphModel()
        workspace_id = model.active_workspace.workspace_id
        source = model.add_node(workspace_id, "core.start", "Start", 0.0, 0.0)
        target = model.add_node(workspace_id, "core.end", "End", 300.0, 80.0)

        model.set_node_position(workspace_id, source.node_id, 25.0, 45.0)
        moved = model.project.workspaces[workspace_id].nodes[source.node_id]
        self.assertEqual((moved.x, moved.y), (25.0, 45.0))

        edge = model.add_edge(workspace_id, source.node_id, "exec_out", target.node_id, "exec_in")
        duplicate = model.add_edge(workspace_id, source.node_id, "exec_out", target.node_id, "exec_in")
        self.assertEqual(edge.edge_id, duplicate.edge_id)
        self.assertEqual(len(model.project.workspaces[workspace_id].edges), 1)

        model.remove_node(workspace_id, source.node_id)
        workspace = model.project.workspaces[workspace_id]
        self.assertNotIn(source.node_id, workspace.nodes)
        self.assertEqual(workspace.edges, {})


class GraphSceneBridgeTrackBTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.registry = build_default_registry()
        self.model = GraphModel()
        self.workspace_id = self.model.active_workspace.workspace_id
        self.scene = GraphSceneBridge()
        self.scene.set_workspace(self.model, self.registry, self.workspace_id)
        self.view = ViewportBridge()
        self.view.set_viewport_size(1280.0, 720.0)

    def test_selection_signal_reports_select_and_clear(self) -> None:
        node_id = self.scene.add_node_from_type("core.start", 0.0, 0.0)
        events: list[str] = []
        self.scene.node_selected.connect(events.append)

        self.scene.focus_node(node_id)
        self.assertEqual(events[-1], node_id)

        self.scene.clearSelection()
        self.assertEqual(events[-1], "")

    def test_connect_move_and_remove_keep_model_and_scene_in_sync(self) -> None:
        source_id = self.scene.add_node_from_type("core.start", 0.0, 0.0)
        target_id = self.scene.add_node_from_type("core.end", 320.0, 40.0)
        edge_id = self.scene.connect_nodes(source_id, target_id)

        self.scene.move_node(source_id, 120.0, 90.0)

        workspace = self.model.project.workspaces[self.workspace_id]
        source_model = workspace.nodes[source_id]
        self.assertAlmostEqual(source_model.x, 120.0, places=4)
        self.assertAlmostEqual(source_model.y, 90.0, places=4)

        self.scene.remove_edge(edge_id)
        self.assertNotIn(edge_id, workspace.edges)
        self.assertIsNone(self.scene.edge_item(edge_id))

        new_edge_id = self.scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        self.scene.remove_node(source_id)
        self.assertNotIn(source_id, workspace.nodes)
        self.assertNotIn(new_edge_id, workspace.edges)
        self.assertIsNone(self.scene.node_item(source_id))
        self.assertIsNone(self.scene.edge_item(new_edge_id))

    def test_collapse_expand_updates_node_payload(self) -> None:
        source_id = self.scene.add_node_from_type("core.start", 0.0, 0.0)
        self.scene.set_node_collapsed(source_id, True)

        payload = {item["node_id"]: item for item in self.scene.nodes_model}
        self.assertTrue(payload[source_id]["collapsed"])
        self.assertLess(payload[source_id]["width"], 150.0)

        self.scene.set_node_collapsed(source_id, False)
        payload = {item["node_id"]: item for item in self.scene.nodes_model}
        self.assertFalse(payload[source_id]["collapsed"])

    def test_hiding_connected_port_removes_edges_immediately(self) -> None:
        source_id = self.scene.add_node_from_type("core.start", 0.0, 0.0)
        target_id = self.scene.add_node_from_type("core.python_script", 320.0, 30.0)
        edge_id = self.scene.add_edge(source_id, "trigger", target_id, "payload")

        self.scene.set_exposed_port(source_id, "trigger", False)

        workspace = self.model.project.workspaces[self.workspace_id]
        self.assertNotIn(edge_id, workspace.edges)
        self.assertIsNone(self.scene.edge_item(edge_id))

    def test_connect_nodes_uses_only_currently_exposed_ports(self) -> None:
        source_id = self.scene.add_node_from_type("core.constant", 0.0, 0.0)
        target_id = self.scene.add_node_from_type("core.logger", 320.0, 30.0)
        self.scene.set_exposed_port(source_id, "value", False)
        self.scene.set_exposed_port(source_id, "as_text", False)

        with self.assertRaises(ValueError):
            self.scene.connect_nodes(source_id, target_id)

    def test_add_edge_rejects_exec_to_data_kind_mismatch(self) -> None:
        source_id = self.scene.add_node_from_type("core.start", 0.0, 0.0)
        target_id = self.scene.add_node_from_type("core.logger", 320.0, 30.0)

        with self.assertRaises(ValueError):
            self.scene.add_edge(source_id, "exec_out", target_id, "message")


class ViewportBridgeTrackBTests(unittest.TestCase):
    def test_viewport_applies_zoom_and_center_updates(self) -> None:
        view = ViewportBridge()
        view.set_zoom(2.5)
        self.assertAlmostEqual(view.zoom, 2.5, places=6)

        view.centerOn(12.0, 18.0)
        self.assertAlmostEqual(view.center_x, 12.0, places=6)
        self.assertAlmostEqual(view.center_y, 18.0, places=6)

        view.pan_by(5.0, -3.0)
        self.assertAlmostEqual(view.center_x, 17.0, places=6)
        self.assertAlmostEqual(view.center_y, 15.0, places=6)


if __name__ == "__main__":
    unittest.main()
