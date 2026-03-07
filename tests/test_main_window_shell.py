from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QMetaObject, Qt, Q_ARG
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QApplication, QMessageBox

from ea_node_editor.app import APP_STYLESHEET
from ea_node_editor.ui.main_window import MainWindow


def _action_shortcuts(action) -> set[str]:  # noqa: ANN001
    return {
        sequence.toString(QKeySequence.SequenceFormat.PortableText)
        for sequence in action.shortcuts()
    }


class MainWindowShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyleSheet(APP_STYLESHEET)

    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self._session_path = Path(self._temp_dir.name) / "last_session.json"
        self._autosave_path = Path(self._temp_dir.name) / "autosave.sfe"
        self._session_patch = patch(
            "ea_node_editor.ui.main_window.recent_session_path",
            return_value=self._session_path,
        )
        self._autosave_patch = patch(
            "ea_node_editor.ui.main_window.autosave_project_path",
            return_value=self._autosave_path,
        )
        self._session_patch.start()
        self._autosave_patch.start()
        self.window = MainWindow()
        self.window.resize(1200, 800)
        self.window.show()
        self.app.processEvents()

    def tearDown(self) -> None:
        self.window.close()
        self.app.processEvents()
        self._session_patch.stop()
        self._autosave_patch.stop()
        self._temp_dir.cleanup()

    def test_qml_shell_and_bridges_are_present(self) -> None:
        self.assertIsNotNone(self.window.quick_widget)
        self.assertIs(self.window.centralWidget(), self.window.quick_widget)
        self.assertIsNotNone(self.window.scene)
        self.assertIsNotNone(self.window.view)
        self.assertGreaterEqual(self.window.workspace_tabs.count(), 1)

    def test_qml_invokable_slots_exist_for_shell_buttons(self) -> None:
        meta = self.window.metaObject()
        self.assertGreaterEqual(meta.indexOfMethod("open_workflow_settings()"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("toggle_script_editor()"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("toggle_script_editor(bool)"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("connect_ports_from_qml(QString,QString,QString,QString)"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("remove_edge_from_qml(QString)"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("remove_node_from_qml(QString)"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("rename_node_from_qml(QString)"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("delete_selected_graph_items(QVariantList)"), 0)

        with patch("ea_node_editor.ui.main_window.WorkflowSettingsDialog.exec", return_value=0):
            QMetaObject.invokeMethod(
                self.window,
                "open_workflow_settings",
                Qt.ConnectionType.DirectConnection,
            )
        QMetaObject.invokeMethod(
            self.window,
            "toggle_script_editor",
            Qt.ConnectionType.DirectConnection,
            Q_ARG(bool, False),
        )
        self.app.processEvents()
        self.assertFalse(self.window.script_editor.visible)

    def test_status_api_contract_updates_visible_values(self) -> None:
        self.window.set_engine_state("running", "Job #12")
        self.window.set_job_counts(2, 3, 4, 1)
        self.window.set_metrics(37.0, 4.3, 16.0)
        self.window.set_notification_counts(5, 2)
        self.app.processEvents()

        self.assertEqual(self.window.status_engine.icon(), "Run")
        self.assertEqual(self.window.status_engine.text(), "Running (Job #12)")
        self.assertEqual(self.window.status_jobs.text(), "R:2 Q:3 D:4 F:1")
        self.assertEqual(self.window.status_metrics.text(), "CPU:37% RAM:4.3/16.0 GB")
        self.assertEqual(self.window.status_notifications.text(), "W:5 E:2")

    def test_command_actions_and_workspace_shortcuts_are_wired(self) -> None:
        self.window.workspace_manager.create_workspace("Second")
        self.window._refresh_workspace_tabs()
        self.window.workspace_tabs.setCurrentIndex(0)
        self.app.processEvents()

        self.window.action_next_workspace.trigger()
        self.app.processEvents()
        self.assertEqual(self.window.workspace_tabs.currentIndex(), 1)

        self.window.action_prev_workspace.trigger()
        self.app.processEvents()
        self.assertEqual(self.window.workspace_tabs.currentIndex(), 0)

        self.assertIn("Ctrl+Tab", _action_shortcuts(self.window.action_next_workspace))
        self.assertIn("Ctrl+PgDown", _action_shortcuts(self.window.action_next_workspace))
        self.assertIn("Ctrl+Shift+Tab", _action_shortcuts(self.window.action_prev_workspace))
        self.assertIn("Ctrl+PgUp", _action_shortcuts(self.window.action_prev_workspace))

        with patch.object(self.window.execution_client, "start_run", return_value="run_test") as start_run:
            self.window.action_run.trigger()
            self.app.processEvents()
            start_run.assert_called_once()

        self.window._active_run_id = "run_test"
        with patch.object(self.window.execution_client, "stop_run") as stop_run:
            self.window.action_stop.trigger()
            self.app.processEvents()
            stop_run.assert_called_once_with("run_test")

        self.window._engine_state_value = "running"
        self.window._update_run_actions()
        with patch.object(self.window.execution_client, "pause_run") as pause_run:
            self.window.action_pause.trigger()
            self.app.processEvents()
            pause_run.assert_called_once_with("run_test")

        self.window._engine_state_value = "paused"
        self.window._update_run_actions()
        with patch.object(self.window.execution_client, "resume_run") as resume_run:
            self.window.action_pause.trigger()
            self.app.processEvents()
            resume_run.assert_called_once_with("run_test")

    def test_file_menu_new_project_resets_to_blank_project(self) -> None:
        self.window.scene.add_node_from_type("core.start", x=40.0, y=40.0)
        self.window.workspace_manager.create_workspace("Second")
        self.window._refresh_workspace_tabs()
        self.window.project_path = str(Path(self._temp_dir.name) / "existing_project.sfe")
        self.app.processEvents()

        file_menu = None
        for action in self.window.menuBar().actions():
            if action.text() == "&File":
                file_menu = action.menu()
                break
        self.assertIsNotNone(file_menu)
        file_entries = [action.text() for action in file_menu.actions() if not action.isSeparator()]
        self.assertIn("New Project", file_entries)
        self.assertIn("Ctrl+N", _action_shortcuts(self.window.action_new_project))

        self.window.action_new_project.trigger()
        self.app.processEvents()

        self.assertEqual(self.window.project_path, "")
        self.assertEqual(self.window.project_display_name, "EA Node Editor - untitled.sfe")
        self.assertEqual(len(self.window.model.project.workspaces), 1)
        active_workspace_id = self.window.workspace_manager.active_workspace_id()
        active_workspace = self.window.model.project.workspaces[active_workspace_id]
        self.assertEqual(active_workspace.nodes, {})
        self.assertEqual(active_workspace.edges, {})
        self.assertFalse(active_workspace.dirty)

    def test_qml_connect_selected_supports_additive_selection(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        source_id = self.window.scene.add_node_from_type("core.start", x=40.0, y=40.0)
        target_id = self.window.scene.add_node_from_type("core.end", x=280.0, y=40.0)
        self.window.scene.select_node(source_id)
        self.window.scene.select_node(target_id, True)
        self.app.processEvents()

        self.window.connect_selected_from_qml()
        self.app.processEvents()

        edges = self.window.model.project.workspaces[workspace_id].edges
        self.assertEqual(len(edges), 1)

    def test_qml_connect_ports_orients_bidirectional_drag_request(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        source_id = self.window.scene.add_node_from_type("core.start", x=40.0, y=40.0)
        target_id = self.window.scene.add_node_from_type("core.end", x=280.0, y=40.0)
        self.app.processEvents()

        created = self.window.connect_ports_from_qml(source_id, "exec_out", target_id, "exec_in")
        self.assertTrue(created)
        edge_id = next(iter(self.window.model.project.workspaces[workspace_id].edges))
        removed = self.window.remove_edge_from_qml(edge_id)
        self.assertTrue(removed)
        self.app.processEvents()

        created_reversed = self.window.connect_ports_from_qml(target_id, "exec_in", source_id, "exec_out")
        self.assertTrue(created_reversed)
        edges = self.window.model.project.workspaces[workspace_id].edges
        self.assertEqual(len(edges), 1)
        edge = next(iter(edges.values()))
        self.assertEqual(edge.source_node_id, source_id)
        self.assertEqual(edge.target_node_id, target_id)
        self.assertEqual(edge.source_port_key, "exec_out")
        self.assertEqual(edge.target_port_key, "exec_in")

    def test_qml_connect_ports_rejects_same_direction(self) -> None:
        source_id = self.window.scene.add_node_from_type("core.start", x=40.0, y=40.0)
        target_id = self.window.scene.add_node_from_type("core.logger", x=280.0, y=40.0)
        self.app.processEvents()

        created = self.window.connect_ports_from_qml(source_id, "exec_out", target_id, "exec_out")
        self.assertFalse(created)

    def test_qml_remove_edge_from_qml_mutates_model(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        source_id = self.window.scene.add_node_from_type("core.start", x=40.0, y=40.0)
        target_id = self.window.scene.add_node_from_type("core.end", x=280.0, y=40.0)
        edge_id = self.window.scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        self.app.processEvents()

        removed = self.window.remove_edge_from_qml(edge_id)
        self.assertTrue(removed)
        self.assertNotIn(edge_id, self.window.model.project.workspaces[workspace_id].edges)

    def test_qml_remove_node_from_qml_removes_incident_edges(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        source_id = self.window.scene.add_node_from_type("core.start", x=40.0, y=40.0)
        target_id = self.window.scene.add_node_from_type("core.end", x=280.0, y=40.0)
        edge_id = self.window.scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        self.app.processEvents()

        removed = self.window.remove_node_from_qml(source_id)
        self.assertTrue(removed)
        workspace = self.window.model.project.workspaces[workspace_id]
        self.assertNotIn(source_id, workspace.nodes)
        self.assertNotIn(edge_id, workspace.edges)

    def test_qml_rename_node_from_qml_updates_title(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("core.start", x=40.0, y=40.0)
        self.app.processEvents()

        with patch("ea_node_editor.ui.main_window.QInputDialog.getText", return_value=("Renamed Node", True)):
            renamed = self.window.rename_node_from_qml(node_id)
        self.assertTrue(renamed)
        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertEqual(node.title, "Renamed Node")

    def test_qml_delete_selected_graph_items_removes_nodes_and_edges(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        source_id = self.window.scene.add_node_from_type("core.start", x=40.0, y=40.0)
        target_id = self.window.scene.add_node_from_type("core.python_script", x=320.0, y=40.0)
        removable_node_id = self.window.scene.add_node_from_type("core.logger", x=520.0, y=40.0)
        edge_id = self.window.scene.add_edge(source_id, "trigger", target_id, "payload")
        self.window.scene.select_node(removable_node_id, False)
        self.app.processEvents()

        deleted = self.window.delete_selected_graph_items([edge_id])
        self.assertTrue(deleted)
        workspace = self.window.model.project.workspaces[workspace_id]
        self.assertNotIn(edge_id, workspace.edges)
        self.assertNotIn(removable_node_id, workspace.nodes)

    def test_qml_rect_selection_supports_replace_and_additive_modes(self) -> None:
        node_a = self.window.scene.add_node_from_type("core.start", x=20.0, y=20.0)
        node_b = self.window.scene.add_node_from_type("core.end", x=360.0, y=30.0)
        self.app.processEvents()

        self.window.scene.select_nodes_in_rect(0.0, 0.0, 280.0, 180.0)
        self.app.processEvents()
        selected_after_replace = {
            item["node_id"]
            for item in self.window.scene.nodes_model
            if item["selected"]
        }
        self.assertEqual(selected_after_replace, {node_a})

        self.window.scene.select_nodes_in_rect(300.0, 0.0, 700.0, 200.0, True)
        self.app.processEvents()
        selected_after_additive = {
            item["node_id"]
            for item in self.window.scene.nodes_model
            if item["selected"]
        }
        self.assertEqual(selected_after_additive, {node_a, node_b})

    def test_qml_parallel_edges_between_same_nodes_use_distinct_lanes(self) -> None:
        source_id = self.window.scene.add_node_from_type("core.start", x=40.0, y=40.0)
        target_id = self.window.scene.add_node_from_type("core.logger", x=320.0, y=60.0)
        self.window.scene.set_node_collapsed(source_id, True)
        self.window.scene.set_node_collapsed(target_id, True)
        self.app.processEvents()

        edge_a = self.window.scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        edge_b = self.window.scene.add_edge(source_id, "trigger", target_id, "message")
        self.app.processEvents()

        edges_by_id = {item["edge_id"]: item for item in self.window.scene.edges_model}
        self.assertIn(edge_a, edges_by_id)
        self.assertIn(edge_b, edges_by_id)
        c1_gap = abs(edges_by_id[edge_a]["c1y"] - edges_by_id[edge_b]["c1y"])
        c2_gap = abs(edges_by_id[edge_a]["c2y"] - edges_by_id[edge_b]["c2y"])
        self.assertGreater(c1_gap, 8.0)
        self.assertGreater(c2_gap, 8.0)

    def test_qml_backward_edge_routes_outside_connected_node_bounds(self) -> None:
        source_id = self.window.scene.add_node_from_type("core.start", x=360.0, y=80.0)
        target_id = self.window.scene.add_node_from_type("core.logger", x=120.0, y=220.0)
        self.app.processEvents()

        self.window.scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        self.app.processEvents()

        nodes_by_id = {item["node_id"]: item for item in self.window.scene.nodes_model}
        source_node = nodes_by_id[source_id]
        target_node = nodes_by_id[target_id]
        edge = self.window.scene.edges_model[0]

        source_right = source_node["x"] + source_node["width"]
        target_left = target_node["x"]
        source_top = source_node["y"]
        source_bottom = source_node["y"] + source_node["height"]
        target_top = target_node["y"]
        target_bottom = target_node["y"] + target_node["height"]

        self.assertGreater(edge["c1x"], source_right)
        self.assertLess(edge["c2x"], target_left)
        self.assertEqual(edge["route"], "pipe")

        pipe_points = edge["pipe_points"]
        self.assertGreaterEqual(len(pipe_points), 6)
        self.assertAlmostEqual(pipe_points[0]["x"], edge["sx"], places=4)
        self.assertAlmostEqual(pipe_points[0]["y"], edge["sy"], places=4)
        self.assertAlmostEqual(pipe_points[-1]["x"], edge["tx"], places=4)
        self.assertAlmostEqual(pipe_points[-1]["y"], edge["ty"], places=4)
        self.assertGreater(pipe_points[1]["x"], source_right)
        self.assertLess(pipe_points[-2]["x"], target_left)
        self.assertAlmostEqual(pipe_points[2]["y"], pipe_points[3]["y"], places=4)
        self.assertGreater(pipe_points[2]["y"], source_bottom)
        self.assertLess(pipe_points[2]["y"], target_top)
        self.assertTrue(pipe_points[2]["y"] < source_top or pipe_points[2]["y"] > source_bottom)
        self.assertTrue(pipe_points[2]["y"] < target_top or pipe_points[2]["y"] > target_bottom)

    def test_qml_library_filter_slots_apply_category_direction_and_type(self) -> None:
        self.window.set_library_query("")
        self.window.set_library_category("Input / Output")
        self.window.set_library_direction("in")
        self.window.set_library_data_type("path")
        self.app.processEvents()

        type_ids = {item["type_id"] for item in self.window.filtered_node_library_items}
        self.assertIn("io.file_read", type_ids)
        self.assertIn("io.file_write", type_ids)
        self.assertIn("io.excel_read", type_ids)
        self.assertIn("io.excel_write", type_ids)
        self.assertNotIn("core.logger", type_ids)

    def test_qml_selected_node_inspector_mutations_update_graph_model(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("core.logger", x=80.0, y=60.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        self.assertTrue(self.window.has_selected_node)
        property_keys = {item["key"] for item in self.window.selected_node_property_items}
        self.assertIn("message", property_keys)
        port_keys = {item["key"] for item in self.window.selected_node_port_items}
        self.assertIn("exec_in", port_keys)

        self.window.set_selected_node_property("message", "updated in qml inspector")
        self.window.set_selected_port_exposed("exec_in", False)
        self.window.set_selected_node_collapsed(True)
        self.app.processEvents()

        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertEqual(node.properties["message"], "updated in qml inspector")
        self.assertFalse(node.exposed_ports["exec_in"])
        self.assertTrue(node.collapsed)

    def test_qml_node_payload_port_list_tracks_exposed_ports(self) -> None:
        node_id = self.window.scene.add_node_from_type("core.start", x=0.0, y=0.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        initial_nodes = self.window.scene.nodes_model
        start_payload = next(item for item in initial_nodes if item["node_id"] == node_id)
        initial_ports = {port["key"] for port in start_payload["ports"]}
        self.assertEqual(initial_ports, {"exec_out", "trigger"})

        self.window.scene.set_exposed_port(node_id, "exec_out", False)
        self.app.processEvents()

        updated_nodes = self.window.scene.nodes_model
        updated_payload = next(item for item in updated_nodes if item["node_id"] == node_id)
        updated_ports = {port["key"] for port in updated_payload["ports"]}
        self.assertEqual(updated_ports, {"trigger"})


    def test_script_editor_action_focuses_editor_when_script_node_selected(self) -> None:
        script_node_id = self.window.scene.add_node_from_type("core.python_script", x=80.0, y=60.0)
        self.window.scene.focus_node(script_node_id)
        self.app.processEvents()

        self.window.action_toggle_script_editor.trigger()
        self.app.processEvents()

        self.assertTrue(self.window.script_editor.visible)
        self.assertEqual(self.window.script_editor.current_node_id, script_node_id)
        self.assertTrue(self.window.script_editor.has_focus)

    def test_multi_view_and_workspace_switch_retains_independent_camera_state(self) -> None:
        first_workspace_id = self.window.workspace_manager.active_workspace_id()
        first_v1_id = self.window.model.project.workspaces[first_workspace_id].active_view_id

        self.window.view.set_zoom(1.4)
        self.window.view.centerOn(110.0, 210.0)
        self.app.processEvents()

        self.window._save_active_view_state()
        first_v2_id = self.window.workspace_manager.create_view(first_workspace_id, name="V2")
        self.window._restore_active_view_state()
        self.window.view.set_zoom(0.7)
        self.window.view.centerOn(-55.0, 75.0)
        first_node_id = self.window.scene.add_node_from_type("core.start", x=20.0, y=30.0)
        self.app.processEvents()

        second_workspace_id = self.window.workspace_manager.create_workspace("Second")
        self.window._refresh_workspace_tabs()
        self.window._switch_workspace(second_workspace_id)
        self.window.view.set_zoom(2.0)
        self.window.view.centerOn(400.0, -125.0)
        self.app.processEvents()

        self.window._switch_workspace(first_workspace_id)
        self.app.processEvents()
        self.assertEqual(
            self.window.model.project.workspaces[first_workspace_id].active_view_id,
            first_v2_id,
        )
        self.assertAlmostEqual(self.window.view.zoom, 0.7, places=2)
        self.assertAlmostEqual(self.window.view.center_x, -55.0, delta=5.0)
        self.assertAlmostEqual(self.window.view.center_y, 75.0, delta=5.0)
        self.assertIn(first_node_id, self.window.model.project.workspaces[first_workspace_id].nodes)

        self.window._switch_view(first_v1_id)
        self.app.processEvents()
        self.assertAlmostEqual(self.window.view.zoom, 1.4, places=2)
        self.assertAlmostEqual(self.window.view.center_x, 110.0, delta=5.0)
        self.assertAlmostEqual(self.window.view.center_y, 210.0, delta=5.0)

    def test_qml_create_view_updates_active_view_items_and_allows_switching(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        initial_view_count = len(workspace.views)
        original_active_view_id = workspace.active_view_id

        with patch("ea_node_editor.ui.main_window.QInputDialog.getText", return_value=("Inspection", True)):
            self.window.create_view_from_qml()
        self.app.processEvents()

        updated_workspace = self.window.model.project.workspaces[workspace_id]
        self.assertEqual(len(updated_workspace.views), initial_view_count + 1)
        self.assertEqual(self.window.active_view_name, "Inspection")

        active_items = [item for item in self.window.active_view_items if item.get("active")]
        self.assertEqual(len(active_items), 1)
        self.assertEqual(active_items[0]["label"], "Inspection")
        self.assertEqual(updated_workspace.active_view_id, active_items[0]["view_id"])

        self.window.switch_view_from_qml(original_active_view_id)
        self.app.processEvents()
        self.assertEqual(self.window.model.project.workspaces[workspace_id].active_view_id, original_active_view_id)

    def test_closing_dirty_workspace_honors_unsaved_warning(self) -> None:
        first_workspace_id = self.window.workspace_manager.active_workspace_id()
        self.window.workspace_manager.create_workspace("Second")
        self.window._refresh_workspace_tabs()
        self.window._switch_workspace(first_workspace_id)
        self.window.scene.add_node_from_type("core.start", x=0.0, y=0.0)
        self.app.processEvents()

        first_index = -1
        for index in range(self.window.workspace_tabs.count()):
            if self.window.workspace_tabs.tabData(index) == first_workspace_id:
                first_index = index
                break
        self.assertGreaterEqual(first_index, 0)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            self.window._on_workspace_tab_close(first_index)
        self.assertIn(first_workspace_id, self.window.model.project.workspaces)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            self.window._on_workspace_tab_close(first_index)
        self.assertNotIn(first_workspace_id, self.window.model.project.workspaces)

    def test_session_restore_recovers_workspace_order_active_workspace_and_view_camera(self) -> None:
        first_workspace_id = self.window.workspace_manager.active_workspace_id()
        second_workspace_id = self.window.workspace_manager.create_workspace("Second")
        third_workspace_id = self.window.workspace_manager.create_workspace("Third")
        self.window.workspace_manager.move_workspace(2, 1)
        self.window._refresh_workspace_tabs()

        self.window._switch_workspace(third_workspace_id)
        third_v2_id = self.window.workspace_manager.create_view(third_workspace_id, name="V2")
        self.window._switch_view(third_v2_id)
        self.window.view.set_zoom(1.65)
        self.window.view.centerOn(222.0, -111.0)
        self.window._persist_session()
        self.app.processEvents()

        expected_order = [
            self.window.workspace_tabs.tabData(index)
            for index in range(self.window.workspace_tabs.count())
        ]
        self.assertEqual(expected_order, [first_workspace_id, third_workspace_id, second_workspace_id])

        restored = MainWindow()
        restored.resize(1200, 800)
        restored.show()
        self.app.processEvents()
        try:
            restored_order = [
                restored.workspace_tabs.tabData(index)
                for index in range(restored.workspace_tabs.count())
            ]
            self.assertEqual(restored_order, expected_order)
            self.assertEqual(restored.workspace_manager.active_workspace_id(), third_workspace_id)
            self.assertEqual(
                restored.model.project.workspaces[third_workspace_id].active_view_id,
                third_v2_id,
            )
            self.assertAlmostEqual(restored.view.zoom, 1.65, places=2)
            self.assertAlmostEqual(restored.view.center_x, 222.0, delta=3.0)
            self.assertAlmostEqual(restored.view.center_y, -111.0, delta=3.0)
        finally:
            restored.close()
            self.app.processEvents()

    def test_autosave_tick_writes_snapshot_and_keeps_valid_project_doc(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("core.start", x=5.0, y=7.0)
        self.app.processEvents()

        self.window._autosave_tick()
        self.assertTrue(self._autosave_path.exists())

        autosave_doc = json.loads(self._autosave_path.read_text(encoding="utf-8"))
        workspace_docs = {
            workspace["workspace_id"]: workspace for workspace in autosave_doc.get("workspaces", [])
        }
        self.assertIn(workspace_id, workspace_docs)
        saved_nodes = {node["node_id"] for node in workspace_docs[workspace_id].get("nodes", [])}
        self.assertIn(node_id, saved_nodes)

    def test_recovery_prompt_accept_loads_newer_autosave(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        baseline_doc = self.window.serializer.to_document(self.window.model.project)
        self._session_path.write_text(
            json.dumps(
                {
                    "project_path": "",
                    "last_manual_save_ts": 0.0,
                    "project_doc": baseline_doc,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        recovered_node_id = self.window.scene.add_node_from_type("core.start", x=20.0, y=30.0)
        recovered_doc = self.window.serializer.to_document(self.window.model.project)
        self._autosave_path.write_text(
            json.dumps(recovered_doc, indent=2, sort_keys=True, ensure_ascii=True),
            encoding="utf-8",
        )

        with patch.object(MainWindow, "_prompt_recover_autosave", return_value=QMessageBox.StandardButton.Yes):
            restored = MainWindow()
            restored.resize(1200, 800)
            restored.show()
            self.app.processEvents()
            try:
                restored_workspace = restored.model.project.workspaces[workspace_id]
                self.assertIn(recovered_node_id, restored_workspace.nodes)
                self.assertFalse(self._autosave_path.exists())
            finally:
                restored.close()
                self.app.processEvents()

    def test_recovery_prompt_reject_keeps_session_state_and_discards_autosave(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        baseline_node_id = self.window.scene.add_node_from_type("core.start", x=10.0, y=10.0)
        baseline_doc = self.window.serializer.to_document(self.window.model.project)
        self._session_path.write_text(
            json.dumps(
                {
                    "project_path": "",
                    "last_manual_save_ts": 0.0,
                    "project_doc": baseline_doc,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        self.window.scene.add_node_from_type("core.logger", x=120.0, y=10.0)
        autosave_doc = self.window.serializer.to_document(self.window.model.project)
        self._autosave_path.write_text(
            json.dumps(autosave_doc, indent=2, sort_keys=True, ensure_ascii=True),
            encoding="utf-8",
        )

        with patch.object(MainWindow, "_prompt_recover_autosave", return_value=QMessageBox.StandardButton.No):
            restored = MainWindow()
            restored.resize(1200, 800)
            restored.show()
            self.app.processEvents()
            try:
                restored_workspace = restored.model.project.workspaces[workspace_id]
                self.assertIn(baseline_node_id, restored_workspace.nodes)
                self.assertEqual(len(restored_workspace.nodes), 1)
                self.assertFalse(self._autosave_path.exists())
            finally:
                restored.close()
                self.app.processEvents()

    def test_restore_session_handles_corrupted_session_and_autosave_files(self) -> None:
        self._session_path.write_text("{bad json", encoding="utf-8")
        self._autosave_path.write_text("{bad json", encoding="utf-8")
        os.utime(self._autosave_path, None)

        with patch.object(MainWindow, "_prompt_recover_autosave", return_value=QMessageBox.StandardButton.Yes):
            restored = MainWindow()
            restored.resize(1200, 800)
            restored.show()
            self.app.processEvents()
            try:
                self.assertGreaterEqual(len(restored.model.project.workspaces), 1)
                self.assertFalse(self._autosave_path.exists())
            finally:
                restored.close()
                self.app.processEvents()

    def test_recovery_prompt_is_deferred_until_main_window_is_visible(self) -> None:
        baseline_doc = self.window.serializer.to_document(self.window.model.project)
        self._session_path.write_text(
            json.dumps(
                {
                    "project_path": "",
                    "last_manual_save_ts": 0.0,
                    "project_doc": baseline_doc,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        self.window.scene.add_node_from_type("core.start", x=20.0, y=30.0)
        recovered_doc = self.window.serializer.to_document(self.window.model.project)
        self._autosave_path.write_text(
            json.dumps(recovered_doc, indent=2, sort_keys=True, ensure_ascii=True),
            encoding="utf-8",
        )

        with patch.object(MainWindow, "_prompt_recover_autosave", return_value=QMessageBox.StandardButton.No) as prompt:
            restored = MainWindow()
            self.assertEqual(prompt.call_count, 0)
            restored.resize(1200, 800)
            restored.show()
            self.app.processEvents()
            try:
                self.assertGreaterEqual(prompt.call_count, 1)
                self.assertFalse(self._autosave_path.exists())
            finally:
                restored.close()
                self.app.processEvents()

    def test_stream_log_events_are_scoped_to_active_run(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        self.window._active_run_id = "run_live"
        self.window._active_run_workspace_id = workspace_id
        self.window._set_run_ui_state("running", "Running", 1, 0, 0, 0)

        self.window.execution_event.emit(
            {
                "type": "log",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": "node_stream",
                "level": "info",
                "message": "[stdout] tick_ui_0",
            }
        )
        self.window.execution_event.emit(
            {
                "type": "log",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": "node_stream",
                "level": "info",
                "message": "[stderr] warn_ui_0",
            }
        )
        self.window.execution_event.emit(
            {
                "type": "log",
                "run_id": "run_stale",
                "workspace_id": workspace_id,
                "node_id": "node_stream",
                "level": "info",
                "message": "[stdout] should_not_appear",
            }
        )
        self.app.processEvents()

        output_text = self.window.console_panel.output_text
        self.assertIn("[stdout] tick_ui_0", output_text)
        self.assertIn("[stderr] warn_ui_0", output_text)
        self.assertNotIn("should_not_appear", output_text)
        self.assertEqual(self.window._engine_state_value, "running")

    def test_stale_run_events_do_not_mutate_active_run_ui(self) -> None:
        self.window._active_run_id = "run_live"
        self.window._set_run_ui_state("running", "Running", 1, 0, 0, 0)
        initial_error_count = self.window.console_panel.error_count

        self.window.execution_event.emit(
            {
                "type": "run_failed",
                "run_id": "run_stale",
                "workspace_id": self.window.workspace_manager.active_workspace_id(),
                "node_id": "",
                "error": "stale failure",
                "traceback": "traceback",
            }
        )
        self.app.processEvents()

        self.assertEqual(self.window._active_run_id, "run_live")
        self.assertEqual(self.window._engine_state_value, "running")
        self.assertEqual(self.window.status_jobs.text(), "R:1 Q:0 D:0 F:0")
        self.assertEqual(self.window.console_panel.error_count, initial_error_count)

    def test_failure_focus_reveals_parent_chain_when_present(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]

        parent_id = self.window.scene.add_node_from_type("core.start", x=0.0, y=0.0)
        child_id = self.window.scene.add_node_from_type("core.logger", x=140.0, y=0.0)
        workspace.nodes[child_id].parent_node_id = parent_id
        self.window.scene.set_node_collapsed(parent_id, True)
        self.assertTrue(workspace.nodes[parent_id].collapsed)

        with patch.object(QMessageBox, "critical") as critical:
            self.window._focus_failed_node(workspace_id, child_id, "boom")

        self.app.processEvents()
        self.assertFalse(workspace.nodes[parent_id].collapsed)
        self.assertEqual(self.window.scene.selected_node_id(), child_id)
        critical.assert_called_once()

    def test_run_failed_event_centers_failed_node_and_reports_exception_details(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        failed_node_id = self.window.scene.add_node_from_type("core.python_script", x=860.0, y=640.0)
        node_item = self.window.scene.node_item(failed_node_id)
        self.assertIsNotNone(node_item)
        if node_item is None:
            self.fail("Expected failed node item to exist")
        expected_center = node_item.sceneBoundingRect().center()

        self.window._active_run_id = "run_live"
        self.window._active_run_workspace_id = workspace_id
        self.window._set_run_ui_state("running", "Running", 1, 0, 0, 0)

        with patch.object(QMessageBox, "critical") as critical:
            self.window.execution_event.emit(
                {
                    "type": "run_failed",
                    "run_id": "run_live",
                    "workspace_id": workspace_id,
                    "node_id": failed_node_id,
                    "error": "RuntimeError: boom",
                    "traceback": "traceback: line 1",
                }
            )
            self.app.processEvents()

        self.assertAlmostEqual(self.window.view.center_x, expected_center.x(), delta=8.0)
        self.assertAlmostEqual(self.window.view.center_y, expected_center.y(), delta=8.0)
        self.assertEqual(self.window.scene.selected_node_id(), failed_node_id)

        errors_text = self.window.console_panel.errors_text
        self.assertIn("RuntimeError: boom", errors_text)
        self.assertIn("traceback: line 1", errors_text)
        critical.assert_called_once()
        critical_args = critical.call_args.args
        self.assertEqual(critical_args[1], "Workflow Error")
        self.assertEqual(critical_args[2], "RuntimeError: boom")


if __name__ == "__main__":
    unittest.main()
