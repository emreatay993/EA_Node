from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QRectF
from PyQt6.QtWidgets import QApplication

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.ui.shell.runtime_history import ACTION_ADD_NODE, RuntimeGraphHistory
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

    def test_workspace_and_selection_bounds_helpers(self) -> None:
        node_a = self.scene.add_node_from_type("core.start", 10.0, 20.0)
        node_b = self.scene.add_node_from_type("core.end", 340.0, 160.0)

        workspace_bounds = self.scene.workspace_scene_bounds()
        self.assertIsNotNone(workspace_bounds)
        node_a_bounds = self.scene.node_bounds(node_a)
        node_b_bounds = self.scene.node_bounds(node_b)
        self.assertIsNotNone(node_a_bounds)
        self.assertIsNotNone(node_b_bounds)
        expected_workspace_bounds = node_a_bounds.united(node_b_bounds)
        self.assertAlmostEqual(workspace_bounds.x(), expected_workspace_bounds.x(), places=6)
        self.assertAlmostEqual(workspace_bounds.y(), expected_workspace_bounds.y(), places=6)
        self.assertAlmostEqual(workspace_bounds.width(), expected_workspace_bounds.width(), places=6)
        self.assertAlmostEqual(workspace_bounds.height(), expected_workspace_bounds.height(), places=6)

        self.scene.select_node(node_b)
        selection_bounds = self.scene.selection_bounds()
        self.assertIsNotNone(selection_bounds)
        self.assertAlmostEqual(selection_bounds.x(), node_b_bounds.x(), places=6)
        self.assertAlmostEqual(selection_bounds.y(), node_b_bounds.y(), places=6)
        self.assertAlmostEqual(selection_bounds.width(), node_b_bounds.width(), places=6)
        self.assertAlmostEqual(selection_bounds.height(), node_b_bounds.height(), places=6)

        self.scene.clear_selection()
        self.assertIsNone(self.scene.selection_bounds())

    def test_minimap_payload_tracks_selection_and_fallback_bounds(self) -> None:
        empty_bounds = self.scene.workspace_scene_bounds_payload
        self.assertAlmostEqual(empty_bounds["x"], -1600.0, places=6)
        self.assertAlmostEqual(empty_bounds["y"], -900.0, places=6)
        self.assertAlmostEqual(empty_bounds["width"], 3200.0, places=6)
        self.assertAlmostEqual(empty_bounds["height"], 1800.0, places=6)
        self.assertEqual(self.scene.minimap_nodes_model, [])

        node_a = self.scene.add_node_from_type("core.start", 30.0, 40.0)
        node_b = self.scene.add_node_from_type("core.end", 390.0, 200.0)
        self.scene.select_node(node_b)

        minimap_payload = {item["node_id"]: item for item in self.scene.minimap_nodes_model}
        self.assertIn(node_a, minimap_payload)
        self.assertIn(node_b, minimap_payload)
        self.assertFalse(minimap_payload[node_a]["selected"])
        self.assertTrue(minimap_payload[node_b]["selected"])

        workspace_bounds = self.scene.workspace_scene_bounds_payload
        node_a_bounds = self.scene.node_bounds(node_a)
        node_b_bounds = self.scene.node_bounds(node_b)
        self.assertIsNotNone(node_a_bounds)
        self.assertIsNotNone(node_b_bounds)
        expected_workspace_bounds = node_a_bounds.united(node_b_bounds)
        self.assertLessEqual(workspace_bounds["x"], expected_workspace_bounds.x())
        self.assertLessEqual(workspace_bounds["y"], expected_workspace_bounds.y())
        self.assertGreaterEqual(workspace_bounds["x"] + workspace_bounds["width"], expected_workspace_bounds.x() + expected_workspace_bounds.width())
        self.assertGreaterEqual(
            workspace_bounds["y"] + workspace_bounds["height"],
            expected_workspace_bounds.y() + expected_workspace_bounds.height(),
        )
        self.assertGreaterEqual(workspace_bounds["width"], 3200.0)
        self.assertGreaterEqual(workspace_bounds["height"], 1800.0)

    def test_move_nodes_by_delta_moves_group_with_single_history_entry(self) -> None:
        history = RuntimeGraphHistory()
        self.scene.bind_runtime_history(history)
        node_a = self.scene.add_node_from_type("core.start", 20.0, 30.0)
        node_b = self.scene.add_node_from_type("core.end", 360.0, 170.0)
        history.clear_workspace(self.workspace_id)
        workspace = self.model.project.workspaces[self.workspace_id]

        before_dx = workspace.nodes[node_b].x - workspace.nodes[node_a].x
        before_dy = workspace.nodes[node_b].y - workspace.nodes[node_a].y

        moved = self.scene.move_nodes_by_delta([node_a, node_b], 55.0, -25.0)
        self.assertTrue(moved)
        self.assertEqual(history.undo_depth(self.workspace_id), 1)
        self.assertAlmostEqual(workspace.nodes[node_a].x, 75.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_a].y, 5.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_b].x, 415.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_b].y, 145.0, places=6)

        after_dx = workspace.nodes[node_b].x - workspace.nodes[node_a].x
        after_dy = workspace.nodes[node_b].y - workspace.nodes[node_a].y
        self.assertAlmostEqual(before_dx, after_dx, places=6)
        self.assertAlmostEqual(before_dy, after_dy, places=6)

        self.assertIsNotNone(history.undo_workspace(self.workspace_id, workspace))
        self.scene.refresh_workspace_from_model(self.workspace_id)
        self.assertAlmostEqual(workspace.nodes[node_a].x, 20.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_a].y, 30.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_b].x, 360.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_b].y, 170.0, places=6)

        self.assertIsNotNone(history.redo_workspace(self.workspace_id, workspace))
        self.scene.refresh_workspace_from_model(self.workspace_id)
        self.assertAlmostEqual(workspace.nodes[node_a].x, 75.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_a].y, 5.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_b].x, 415.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_b].y, 145.0, places=6)

    def test_duplicate_selected_subgraph_offsets_nodes_and_internal_edges_only(self) -> None:
        history = RuntimeGraphHistory()
        self.scene.bind_runtime_history(history)
        source_id = self.scene.add_node_from_type("core.start", 10.0, 20.0)
        target_id = self.scene.add_node_from_type("core.end", 280.0, 40.0)
        external_id = self.scene.add_node_from_type("core.python_script", 520.0, 80.0)
        self.scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        self.scene.add_edge(source_id, "trigger", external_id, "payload")
        self.scene.select_node(source_id, False)
        self.scene.select_node(target_id, True)
        history.clear_workspace(self.workspace_id)

        duplicated = self.scene.duplicate_selected_subgraph()
        self.assertTrue(duplicated)
        self.assertEqual(history.undo_depth(self.workspace_id), 1)

        workspace = self.model.project.workspaces[self.workspace_id]
        self.assertEqual(len(workspace.nodes), 5)
        self.assertEqual(len(workspace.edges), 3)

        duplicated_ids = [item.node.node_id for item in self.scene.selectedItems()]
        self.assertEqual(len(duplicated_ids), 2)
        self.assertNotIn(source_id, duplicated_ids)
        self.assertNotIn(target_id, duplicated_ids)

        source_node = workspace.nodes[source_id]
        target_node = workspace.nodes[target_id]
        duplicated_source_id = ""
        duplicated_target_id = ""
        for node_id in duplicated_ids:
            node = workspace.nodes[node_id]
            if (
                node.type_id == source_node.type_id
                and node.title == source_node.title
                and abs(node.x - (source_node.x + 40.0)) < 1e-6
                and abs(node.y - (source_node.y + 40.0)) < 1e-6
            ):
                duplicated_source_id = node_id
            if (
                node.type_id == target_node.type_id
                and node.title == target_node.title
                and abs(node.x - (target_node.x + 40.0)) < 1e-6
                and abs(node.y - (target_node.y + 40.0)) < 1e-6
            ):
                duplicated_target_id = node_id
        self.assertTrue(duplicated_source_id)
        self.assertTrue(duplicated_target_id)

        duplicated_internal_edges = [
            edge
            for edge in workspace.edges.values()
            if edge.source_node_id == duplicated_source_id
            and edge.target_node_id == duplicated_target_id
            and edge.source_port_key == "exec_out"
            and edge.target_port_key == "exec_in"
        ]
        self.assertEqual(len(duplicated_internal_edges), 1)
        duplicated_external_edges = [
            edge
            for edge in workspace.edges.values()
            if edge.source_node_id == duplicated_source_id and edge.source_port_key == "trigger"
        ]
        self.assertEqual(duplicated_external_edges, [])


class RuntimeGraphHistoryTrackBTests(unittest.TestCase):
    def test_history_is_isolated_per_workspace_and_clears_redo_on_new_commit(self) -> None:
        model = GraphModel()
        history = RuntimeGraphHistory()
        workspace_a_id = model.active_workspace.workspace_id
        workspace_b_id = model.create_workspace(name="Secondary").workspace_id
        workspace_a = model.project.workspaces[workspace_a_id]
        workspace_b = model.project.workspaces[workspace_b_id]

        before_a = history.capture_workspace(workspace_a)
        model.add_node(workspace_a_id, "core.start", "Start A", 0.0, 0.0)
        history.record_action(workspace_a_id, ACTION_ADD_NODE, before_a, workspace_a)

        before_b = history.capture_workspace(workspace_b)
        model.add_node(workspace_b_id, "core.end", "End B", 240.0, 100.0)
        history.record_action(workspace_b_id, ACTION_ADD_NODE, before_b, workspace_b)

        self.assertEqual(history.undo_depth(workspace_a_id), 1)
        self.assertEqual(history.undo_depth(workspace_b_id), 1)

        undone = history.undo_workspace(workspace_a_id, workspace_a)
        self.assertIsNotNone(undone)
        self.assertEqual(len(workspace_a.nodes), 0)
        self.assertEqual(len(workspace_b.nodes), 1)
        self.assertEqual(history.redo_depth(workspace_a_id), 1)
        self.assertEqual(history.redo_depth(workspace_b_id), 0)

        before_new = history.capture_workspace(workspace_a)
        model.add_node(workspace_a_id, "core.logger", "Logger A", 80.0, 30.0)
        history.record_action(workspace_a_id, ACTION_ADD_NODE, before_new, workspace_a)
        self.assertEqual(history.redo_depth(workspace_a_id), 0)
        self.assertEqual(history.undo_depth(workspace_a_id), 1)

    def test_grouped_action_commits_single_history_entry(self) -> None:
        model = GraphModel()
        history = RuntimeGraphHistory()
        workspace_id = model.active_workspace.workspace_id
        workspace = model.project.workspaces[workspace_id]

        with history.grouped_action(workspace_id, ACTION_ADD_NODE, workspace):
            model.add_node(workspace_id, "core.start", "Start", 0.0, 0.0)
            model.add_node(workspace_id, "core.end", "End", 280.0, 40.0)

        self.assertEqual(history.undo_depth(workspace_id), 1)
        history.undo_workspace(workspace_id, workspace)
        self.assertEqual(len(workspace.nodes), 0)


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

    def test_visible_scene_rect_reflects_viewport_center_and_zoom(self) -> None:
        view = ViewportBridge()
        view.set_viewport_size(1000.0, 500.0)
        view.set_zoom(2.0)
        view.centerOn(10.0, 20.0)

        rect = view.visible_scene_rect()
        self.assertAlmostEqual(rect.x(), -240.0, places=6)
        self.assertAlmostEqual(rect.y(), -105.0, places=6)
        self.assertAlmostEqual(rect.width(), 500.0, places=6)
        self.assertAlmostEqual(rect.height(), 250.0, places=6)

    def test_frame_scene_rect_applies_padding_and_respects_zoom_clamp(self) -> None:
        view = ViewportBridge()
        view.set_viewport_size(1280.0, 720.0)

        self.assertTrue(view.frame_scene_rect(QRectF(100.0, 50.0, 400.0, 200.0)))
        self.assertAlmostEqual(view.zoom, 2.8, places=6)
        self.assertAlmostEqual(view.center_x, 300.0, places=6)
        self.assertAlmostEqual(view.center_y, 150.0, places=6)

        self.assertTrue(view.frame_scene_rect(QRectF(-10.0, -10.0, 20.0, 20.0)))
        self.assertAlmostEqual(view.zoom, 3.0, places=6)

    def test_frame_scene_rect_rejects_empty_bounds(self) -> None:
        view = ViewportBridge()
        view.set_viewport_size(1280.0, 720.0)
        view.set_zoom(1.5)
        view.centerOn(11.0, -9.0)

        self.assertFalse(view.frame_scene_rect(QRectF()))
        self.assertAlmostEqual(view.zoom, 1.5, places=6)
        self.assertAlmostEqual(view.center_x, 11.0, places=6)
        self.assertAlmostEqual(view.center_y, -9.0, places=6)

    def test_visible_scene_rect_payload_and_center_helper(self) -> None:
        view = ViewportBridge()
        view.set_viewport_size(800.0, 600.0)
        view.set_zoom(2.0)
        view.centerOn(100.0, -50.0)

        payload = view.visible_scene_rect_payload
        self.assertAlmostEqual(payload["x"], -100.0, places=6)
        self.assertAlmostEqual(payload["y"], -200.0, places=6)
        self.assertAlmostEqual(payload["width"], 400.0, places=6)
        self.assertAlmostEqual(payload["height"], 300.0, places=6)

        payload_from_slot = view.visible_scene_rect_map()
        self.assertEqual(payload_from_slot, payload)

        view.center_on_scene_point(240.0, 120.0)
        self.assertAlmostEqual(view.center_x, 240.0, places=6)
        self.assertAlmostEqual(view.center_y, 120.0, places=6)


if __name__ == "__main__":
    unittest.main()
