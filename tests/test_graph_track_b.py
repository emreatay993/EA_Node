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

    def test_subnode_shell_ports_follow_direct_pin_sort_and_pin_properties(self) -> None:
        shell_id = self.scene.add_node_from_type("core.subnode", 200.0, 120.0)
        pin_in_exec = self.scene.add_node_from_type("core.subnode_input", 30.0, 10.0)
        pin_in_data = self.scene.add_node_from_type("core.subnode_input", 30.0, 10.0)
        pin_out_data = self.scene.add_node_from_type("core.subnode_output", 90.0, 10.0)
        pin_out_failed = self.scene.add_node_from_type("core.subnode_output", 20.0, 50.0)
        non_pin_child = self.scene.add_node_from_type("core.logger", 60.0, 15.0)
        nested_pin = self.scene.add_node_from_type("core.subnode_input", 15.0, 5.0)

        workspace = self.model.project.workspaces[self.workspace_id]
        workspace.nodes[pin_in_exec].parent_node_id = shell_id
        workspace.nodes[pin_in_data].parent_node_id = shell_id
        workspace.nodes[pin_out_data].parent_node_id = shell_id
        workspace.nodes[pin_out_failed].parent_node_id = shell_id
        workspace.nodes[non_pin_child].parent_node_id = shell_id
        workspace.nodes[nested_pin].parent_node_id = non_pin_child

        self.scene.set_node_property(pin_in_exec, "label", "Exec In")
        self.scene.set_node_property(pin_in_exec, "kind", "exec")
        self.scene.set_node_property(pin_in_exec, "data_type", "str")
        self.scene.set_node_property(pin_in_data, "label", "Flag In")
        self.scene.set_node_property(pin_in_data, "kind", "data")
        self.scene.set_node_property(pin_in_data, "data_type", "bool")
        self.scene.set_node_property(pin_out_data, "label", "Result Out")
        self.scene.set_node_property(pin_out_data, "kind", "data")
        self.scene.set_node_property(pin_out_data, "data_type", "float")
        self.scene.set_node_property(pin_out_failed, "label", "Failure Out")
        self.scene.set_node_property(pin_out_failed, "kind", "failed")
        self.scene.set_node_property(pin_out_failed, "data_type", "str")
        self.scene.refresh_workspace_from_model(self.workspace_id)

        root_payload = {item["node_id"]: item for item in self.scene.nodes_model}
        shell_ports = root_payload[shell_id]["ports"]
        direct_pins = [pin_in_exec, pin_in_data, pin_out_data, pin_out_failed]
        expected_order = sorted(
            direct_pins,
            key=lambda node_id: (
                float(workspace.nodes[node_id].y),
                float(workspace.nodes[node_id].x),
                node_id,
            ),
        )
        self.assertEqual([port["key"] for port in shell_ports], expected_order)
        self.assertEqual(len(shell_ports), 4)

        shell_port_by_key = {port["key"]: port for port in shell_ports}
        self.assertEqual(shell_port_by_key[pin_in_exec]["label"], "Exec In")
        self.assertEqual(shell_port_by_key[pin_in_exec]["direction"], "in")
        self.assertEqual(shell_port_by_key[pin_in_exec]["kind"], "exec")
        self.assertEqual(shell_port_by_key[pin_in_exec]["data_type"], "any")
        self.assertEqual(shell_port_by_key[pin_in_data]["label"], "Flag In")
        self.assertEqual(shell_port_by_key[pin_in_data]["direction"], "in")
        self.assertEqual(shell_port_by_key[pin_in_data]["data_type"], "bool")
        self.assertEqual(shell_port_by_key[pin_out_data]["label"], "Result Out")
        self.assertEqual(shell_port_by_key[pin_out_data]["direction"], "out")
        self.assertEqual(shell_port_by_key[pin_out_data]["data_type"], "float")
        self.assertEqual(shell_port_by_key[pin_out_failed]["label"], "Failure Out")
        self.assertEqual(shell_port_by_key[pin_out_failed]["direction"], "out")
        self.assertEqual(shell_port_by_key[pin_out_failed]["kind"], "failed")
        self.assertEqual(shell_port_by_key[pin_out_failed]["data_type"], "any")

        self.assertNotIn(pin_in_exec, root_payload)
        self.assertTrue(self.scene.open_subnode_scope(shell_id))

        nested_payload = {item["node_id"]: item for item in self.scene.nodes_model}
        self.assertIn(pin_in_exec, nested_payload)
        pin_payload = nested_payload[pin_in_exec]["ports"]
        self.assertEqual(len(pin_payload), 1)
        self.assertEqual(pin_payload[0]["key"], "pin")
        self.assertEqual(pin_payload[0]["label"], "Exec In")
        self.assertEqual(pin_payload[0]["kind"], "exec")
        self.assertEqual(pin_payload[0]["data_type"], "any")

    def test_scope_navigation_filters_nodes_edges_and_assigns_new_nodes_to_active_scope(self) -> None:
        shell_id = self.scene.add_node_from_type("core.subnode", 200.0, 120.0)
        root_source_id = self.scene.add_node_from_type("core.start", 20.0, 30.0)
        root_target_id = self.scene.add_node_from_type("core.end", 520.0, 30.0)
        pin_in = self.scene.add_node_from_type("core.subnode_input", 30.0, 30.0)
        pin_out = self.scene.add_node_from_type("core.subnode_output", 90.0, 30.0)
        nested_logger = self.scene.add_node_from_type("core.logger", 160.0, 120.0)
        workspace = self.model.project.workspaces[self.workspace_id]
        workspace.nodes[pin_in].parent_node_id = shell_id
        workspace.nodes[pin_out].parent_node_id = shell_id
        workspace.nodes[nested_logger].parent_node_id = shell_id
        self.scene.set_node_property(pin_in, "kind", "exec")
        self.scene.set_node_property(pin_out, "kind", "exec")
        self.scene.refresh_workspace_from_model(self.workspace_id)

        # Root scope only shows direct workspace children.
        root_node_ids = {item["node_id"] for item in self.scene.nodes_model}
        self.assertEqual(root_node_ids, {shell_id, root_source_id, root_target_id})
        self.assertEqual(self.scene.active_scope_path, [])
        self.assertEqual([item["node_id"] for item in self.scene.scope_breadcrumb_model], [""])

        self.scene.add_edge(root_source_id, "exec_out", root_target_id, "exec_in")
        self.scene.add_edge(root_source_id, "exec_out", shell_id, pin_in)
        self.assertEqual({item["edge_id"] for item in self.scene.edges_model}, set(workspace.edges))

        self.assertTrue(self.scene.open_subnode_scope(shell_id))
        self.assertEqual(self.scene.active_scope_path, [shell_id])
        breadcrumb_ids = [item["node_id"] for item in self.scene.scope_breadcrumb_model]
        self.assertEqual(breadcrumb_ids, ["", shell_id])

        nested_node_ids = {item["node_id"] for item in self.scene.nodes_model}
        self.assertEqual(nested_node_ids, {pin_in, pin_out, nested_logger})
        self.assertEqual(self.scene.edges_model, [])

        created_inside_scope = self.scene.add_node_from_type("core.constant", 300.0, 150.0)
        self.assertEqual(workspace.nodes[created_inside_scope].parent_node_id, shell_id)

        self.assertTrue(self.scene.navigate_scope_parent())
        self.assertEqual(self.scene.active_scope_path, [])
        self.assertFalse(self.scene.navigate_scope_parent())
        self.assertFalse(self.scene.navigate_scope_root())

    def test_connect_nodes_uses_dynamic_subnode_default_ports(self) -> None:
        source_id = self.scene.add_node_from_type("core.start", 20.0, 30.0)
        shell_id = self.scene.add_node_from_type("core.subnode", 260.0, 30.0)
        target_id = self.scene.add_node_from_type("core.end", 520.0, 30.0)
        pin_in = self.scene.add_node_from_type("core.subnode_input", 40.0, 40.0)
        pin_out = self.scene.add_node_from_type("core.subnode_output", 80.0, 40.0)

        workspace = self.model.project.workspaces[self.workspace_id]
        workspace.nodes[pin_in].parent_node_id = shell_id
        workspace.nodes[pin_out].parent_node_id = shell_id
        self.scene.set_node_property(pin_in, "kind", "exec")
        self.scene.set_node_property(pin_out, "kind", "exec")
        self.scene.refresh_workspace_from_model(self.workspace_id)

        edge_into_shell_id = self.scene.connect_nodes(source_id, shell_id)
        edge_out_of_shell_id = self.scene.connect_nodes(shell_id, target_id)

        edge_into_shell = workspace.edges[edge_into_shell_id]
        edge_out_of_shell = workspace.edges[edge_out_of_shell_id]
        self.assertEqual(edge_into_shell.source_node_id, source_id)
        self.assertEqual(edge_into_shell.source_port_key, "exec_out")
        self.assertEqual(edge_into_shell.target_node_id, shell_id)
        self.assertEqual(edge_into_shell.target_port_key, pin_in)
        self.assertEqual(edge_out_of_shell.source_node_id, shell_id)
        self.assertEqual(edge_out_of_shell.source_port_key, pin_out)
        self.assertEqual(edge_out_of_shell.target_node_id, target_id)
        self.assertEqual(edge_out_of_shell.target_port_key, "exec_in")

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

    def test_layout_actions_align_and_distribute_selected_nodes_with_grouped_history(self) -> None:
        history = RuntimeGraphHistory()
        self.scene.bind_runtime_history(history)
        node_a = self.scene.add_node_from_type("core.start", 40.0, 20.0)
        node_b = self.scene.add_node_from_type("core.end", 320.0, 210.0)
        node_c = self.scene.add_node_from_type("core.logger", 640.0, 80.0)
        workspace = self.model.project.workspaces[self.workspace_id]
        self.scene.select_node(node_a, False)
        self.scene.select_node(node_b, True)
        self.scene.select_node(node_c, True)
        history.clear_workspace(self.workspace_id)

        moved = self.scene.align_selected_nodes("left")
        self.assertTrue(moved)
        self.assertEqual(history.undo_depth(self.workspace_id), 1)

        left_edges = []
        for node_id in (node_a, node_b, node_c):
            bounds = self.scene.node_bounds(node_id)
            self.assertIsNotNone(bounds)
            left_edges.append(bounds.x())
        for left in left_edges[1:]:
            self.assertAlmostEqual(left, left_edges[0], places=6)

        self.assertIsNotNone(history.undo_workspace(self.workspace_id, workspace))
        self.scene.refresh_workspace_from_model(self.workspace_id)
        self.assertAlmostEqual(workspace.nodes[node_a].x, 40.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_b].x, 320.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_c].x, 640.0, places=6)

        self.assertIsNotNone(history.redo_workspace(self.workspace_id, workspace))
        self.scene.refresh_workspace_from_model(self.workspace_id)
        self.assertAlmostEqual(workspace.nodes[node_a].x, 40.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_b].x, 40.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_c].x, 40.0, places=6)

        self.model.set_node_position(self.workspace_id, node_a, 10.0, 30.0)
        self.model.set_node_position(self.workspace_id, node_b, 290.0, 120.0)
        self.model.set_node_position(self.workspace_id, node_c, 700.0, 260.0)
        self.scene.refresh_workspace_from_model(self.workspace_id)
        history.clear_workspace(self.workspace_id)

        before_sorted = sorted(
            (self.scene.node_bounds(node_id) for node_id in (node_a, node_b, node_c)),
            key=lambda bounds: float(bounds.x()) if bounds is not None else 0.0,
        )
        self.assertTrue(all(bounds is not None for bounds in before_sorted))
        moved = self.scene.distribute_selected_nodes("horizontal")
        self.assertTrue(moved)
        self.assertEqual(history.undo_depth(self.workspace_id), 1)

        after_sorted = sorted(
            (self.scene.node_bounds(node_id) for node_id in (node_a, node_b, node_c)),
            key=lambda bounds: float(bounds.x()) if bounds is not None else 0.0,
        )
        self.assertTrue(all(bounds is not None for bounds in after_sorted))
        first_before = before_sorted[0]
        last_before = before_sorted[-1]
        first_after = after_sorted[0]
        last_after = after_sorted[-1]
        self.assertIsNotNone(first_before)
        self.assertIsNotNone(last_before)
        self.assertIsNotNone(first_after)
        self.assertIsNotNone(last_after)
        self.assertAlmostEqual(first_after.x(), first_before.x(), places=6)
        self.assertAlmostEqual(last_after.x(), last_before.x(), places=6)

        gap_01 = after_sorted[1].x() - (after_sorted[0].x() + after_sorted[0].width())
        gap_12 = after_sorted[2].x() - (after_sorted[1].x() + after_sorted[1].width())
        self.assertAlmostEqual(gap_01, gap_12, places=6)

    def test_layout_actions_snap_to_grid_and_small_selections_are_safe_noops(self) -> None:
        history = RuntimeGraphHistory()
        self.scene.bind_runtime_history(history)
        node_a = self.scene.add_node_from_type("core.start", 13.0, 17.0)
        node_b = self.scene.add_node_from_type("core.end", 171.0, 83.0)
        workspace = self.model.project.workspaces[self.workspace_id]
        history.clear_workspace(self.workspace_id)

        self.scene.select_node(node_a, False)
        self.assertFalse(self.scene.align_selected_nodes("left"))
        self.assertFalse(self.scene.distribute_selected_nodes("horizontal"))
        self.assertEqual(history.undo_depth(self.workspace_id), 0)

        self.scene.select_node(node_b, True)
        moved = self.scene.align_selected_nodes("top", snap_to_grid=True)
        self.assertTrue(moved)
        self.assertEqual(history.undo_depth(self.workspace_id), 1)

        for node_id in (node_a, node_b):
            node = workspace.nodes[node_id]
            self.assertAlmostEqual(float(node.x) / 20.0, round(float(node.x) / 20.0), places=6)
            self.assertAlmostEqual(float(node.y) / 20.0, round(float(node.y) / 20.0), places=6)

        self.assertIsNotNone(history.undo_workspace(self.workspace_id, workspace))
        self.scene.refresh_workspace_from_model(self.workspace_id)
        self.assertAlmostEqual(workspace.nodes[node_a].x, 13.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_a].y, 17.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_b].x, 171.0, places=6)
        self.assertAlmostEqual(workspace.nodes[node_b].y, 83.0, places=6)

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

    def test_group_selected_nodes_creates_subnode_pins_and_single_history_entry(self) -> None:
        history = RuntimeGraphHistory()
        self.scene.bind_runtime_history(history)
        source_id = self.scene.add_node_from_type("core.start", 20.0, 40.0)
        grouped_logger_id = self.scene.add_node_from_type("core.logger", 320.0, 60.0)
        grouped_constant_id = self.scene.add_node_from_type("core.constant", 220.0, 190.0)
        target_id = self.scene.add_node_from_type("core.end", 640.0, 90.0)
        external_script_id = self.scene.add_node_from_type("core.python_script", 700.0, 230.0)

        self.scene.add_edge(source_id, "exec_out", grouped_logger_id, "exec_in")
        self.scene.add_edge(grouped_constant_id, "as_text", grouped_logger_id, "message")
        self.scene.add_edge(grouped_logger_id, "exec_out", target_id, "exec_in")
        self.scene.add_edge(grouped_constant_id, "value", external_script_id, "payload")
        workspace = self.model.project.workspaces[self.workspace_id]

        self.scene.select_node(grouped_logger_id, False)
        self.scene.select_node(grouped_constant_id, True)
        history.clear_workspace(self.workspace_id)

        grouped = self.scene.group_selected_nodes()
        self.assertTrue(grouped)
        self.assertEqual(history.undo_depth(self.workspace_id), 1)

        shell_id = self.scene.selected_node_id()
        self.assertIsNotNone(shell_id)
        assert shell_id is not None
        shell_node = workspace.nodes[shell_id]
        self.assertEqual(shell_node.type_id, "core.subnode")
        self.assertIsNone(shell_node.parent_node_id)
        self.assertEqual(workspace.nodes[grouped_logger_id].parent_node_id, shell_id)
        self.assertEqual(workspace.nodes[grouped_constant_id].parent_node_id, shell_id)

        pin_ids = [
            node_id
            for node_id, node in workspace.nodes.items()
            if node.parent_node_id == shell_id and node.type_id in {"core.subnode_input", "core.subnode_output"}
        ]
        self.assertEqual(len(pin_ids), 3)
        shell_payload = next(item for item in self.scene.nodes_model if item["node_id"] == shell_id)
        shell_port_labels = {str(port.get("label", "")) for port in shell_payload["ports"]}
        self.assertEqual(shell_port_labels, {"exec_in", "exec_out", "value"})

        grouped_ids = {grouped_logger_id, grouped_constant_id}
        outer_ids = {source_id, target_id, external_script_id}
        for edge in workspace.edges.values():
            self.assertFalse(edge.source_node_id in outer_ids and edge.target_node_id in grouped_ids)
            self.assertFalse(edge.source_node_id in grouped_ids and edge.target_node_id in outer_ids)

        edge_tuples = {
            (edge.source_node_id, edge.source_port_key, edge.target_node_id, edge.target_port_key)
            for edge in workspace.edges.values()
        }
        incoming_shell_edges = [edge for edge in edge_tuples if edge[0] == source_id and edge[2] == shell_id]
        self.assertEqual(len(incoming_shell_edges), 1)
        outgoing_shell_target_edges = [edge for edge in edge_tuples if edge[0] == shell_id and edge[2] == target_id]
        self.assertEqual(len(outgoing_shell_target_edges), 1)
        outgoing_shell_script_edges = [
            edge
            for edge in edge_tuples
            if edge[0] == shell_id and edge[2] == external_script_id and edge[3] == "payload"
        ]
        self.assertEqual(len(outgoing_shell_script_edges), 1)

    def test_ungroup_selected_subnode_restores_wiring_and_single_history_entry(self) -> None:
        self.scene.bind_runtime_history(RuntimeGraphHistory())
        source_id = self.scene.add_node_from_type("core.start", 20.0, 40.0)
        grouped_logger_id = self.scene.add_node_from_type("core.logger", 320.0, 60.0)
        grouped_constant_id = self.scene.add_node_from_type("core.constant", 220.0, 190.0)
        target_id = self.scene.add_node_from_type("core.end", 640.0, 90.0)
        external_script_id = self.scene.add_node_from_type("core.python_script", 700.0, 230.0)

        self.scene.add_edge(source_id, "exec_out", grouped_logger_id, "exec_in")
        self.scene.add_edge(grouped_constant_id, "as_text", grouped_logger_id, "message")
        self.scene.add_edge(grouped_logger_id, "exec_out", target_id, "exec_in")
        self.scene.add_edge(grouped_constant_id, "value", external_script_id, "payload")
        workspace = self.model.project.workspaces[self.workspace_id]
        expected_edges = {
            (source_id, "exec_out", grouped_logger_id, "exec_in"),
            (grouped_constant_id, "as_text", grouped_logger_id, "message"),
            (grouped_logger_id, "exec_out", target_id, "exec_in"),
            (grouped_constant_id, "value", external_script_id, "payload"),
        }

        self.scene.select_node(grouped_logger_id, False)
        self.scene.select_node(grouped_constant_id, True)
        self.assertTrue(self.scene.group_selected_nodes())

        shell_id = self.scene.selected_node_id()
        self.assertIsNotNone(shell_id)
        assert shell_id is not None
        pin_ids_before = {
            node_id
            for node_id, node in workspace.nodes.items()
            if node.parent_node_id == shell_id and node.type_id in {"core.subnode_input", "core.subnode_output"}
        }
        self.assertTrue(pin_ids_before)

        history = RuntimeGraphHistory()
        self.scene.bind_runtime_history(history)
        history.clear_workspace(self.workspace_id)

        self.scene.select_node(shell_id, False)
        ungrouped = self.scene.ungroup_selected_subnode()
        self.assertTrue(ungrouped)
        self.assertEqual(history.undo_depth(self.workspace_id), 1)

        self.assertNotIn(shell_id, workspace.nodes)
        for pin_id in pin_ids_before:
            self.assertNotIn(pin_id, workspace.nodes)
        self.assertEqual(workspace.nodes[grouped_logger_id].parent_node_id, None)
        self.assertEqual(workspace.nodes[grouped_constant_id].parent_node_id, None)

        edge_tuples = {
            (edge.source_node_id, edge.source_port_key, edge.target_node_id, edge.target_port_key)
            for edge in workspace.edges.values()
        }
        self.assertEqual(edge_tuples, expected_edges)

    def test_group_selected_nodes_rejects_mixed_scope_selection(self) -> None:
        root_node_id = self.scene.add_node_from_type("core.start", 40.0, 40.0)
        shell_id = self.scene.add_node_from_type("core.subnode", 260.0, 120.0)
        nested_node_id = self.scene.add_node_from_type("core.logger", 280.0, 180.0)
        workspace = self.model.project.workspaces[self.workspace_id]
        workspace.nodes[nested_node_id].parent_node_id = shell_id
        self.scene.refresh_workspace_from_model(self.workspace_id)

        self.scene._selected_node_ids = [root_node_id, nested_node_id]
        self.assertFalse(self.scene.group_selected_nodes())
        self.assertEqual(
            len([node for node in workspace.nodes.values() if node.type_id == "core.subnode"]),
            1,
        )


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
