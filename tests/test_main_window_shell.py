from __future__ import annotations

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
from ea_node_editor.ui.shell.window import ShellWindow


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
            "ea_node_editor.ui.shell.window.recent_session_path",
            return_value=self._session_path,
        )
        self._autosave_patch = patch(
            "ea_node_editor.ui.shell.window.autosave_project_path",
            return_value=self._autosave_path,
        )
        self._session_patch.start()
        self._autosave_patch.start()
        self.window = ShellWindow()
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
        self.assertIsNotNone(self.window.quick_widget.rootObject())
        self.assertIsNotNone(self.window.scene)
        self.assertIsNotNone(self.window.view)
        self.assertGreaterEqual(self.window.workspace_tabs.count(), 1)

    def test_qml_invokable_slots_exist_for_shell_buttons(self) -> None:
        meta = self.window.metaObject()
        self.assertGreaterEqual(meta.indexOfMethod("show_workflow_settings_dialog()"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("set_script_editor_panel_visible()"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("set_script_editor_panel_visible(bool)"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("request_connect_ports(QString,QString,QString,QString)"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("request_remove_edge(QString)"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("request_remove_node(QString)"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("request_rename_node(QString)"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("request_delete_selected_graph_items(QVariantList)"), 0)
        self.assertGreaterEqual(
            meta.indexOfMethod("request_drop_node_from_library(QString,double,double,QString,QString,QString,QString)"),
            0,
        )

        with patch("ea_node_editor.ui.shell.window.WorkflowSettingsDialog.exec", return_value=0):
            QMetaObject.invokeMethod(
                self.window,
                "show_workflow_settings_dialog",
                Qt.ConnectionType.DirectConnection,
            )
        QMetaObject.invokeMethod(
            self.window,
            "set_script_editor_panel_visible",
            Qt.ConnectionType.DirectConnection,
            Q_ARG(bool, False),
        )
        self.app.processEvents()
        self.assertFalse(self.window.script_editor.visible)

    def test_status_api_contract_updates_visible_values(self) -> None:
        self.window.update_engine_status("running", "Job #12")
        self.window.update_job_counters(2, 3, 4, 1)
        self.window.update_system_metrics(37.0, 4.3, 16.0)
        self.window.update_notification_counters(5, 2)
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

        self.window.request_connect_selected_nodes()
        self.app.processEvents()

        edges = self.window.model.project.workspaces[workspace_id].edges
        self.assertEqual(len(edges), 1)

    def test_qml_connect_ports_orients_bidirectional_drag_request(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        source_id = self.window.scene.add_node_from_type("core.start", x=40.0, y=40.0)
        target_id = self.window.scene.add_node_from_type("core.end", x=280.0, y=40.0)
        self.app.processEvents()

        created = self.window.request_connect_ports(source_id, "exec_out", target_id, "exec_in")
        self.assertTrue(created)
        edge_id = next(iter(self.window.model.project.workspaces[workspace_id].edges))
        removed = self.window.request_remove_edge(edge_id)
        self.assertTrue(removed)
        self.app.processEvents()

        created_reversed = self.window.request_connect_ports(target_id, "exec_in", source_id, "exec_out")
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

        created = self.window.request_connect_ports(source_id, "exec_out", target_id, "exec_out")
        self.assertFalse(created)

    def test_qml_connect_ports_rejects_exec_to_data_kind_mismatch(self) -> None:
        source_id = self.window.scene.add_node_from_type("core.start", x=40.0, y=40.0)
        target_id = self.window.scene.add_node_from_type("core.logger", x=280.0, y=40.0)
        self.app.processEvents()

        created = self.window.request_connect_ports(source_id, "exec_out", target_id, "message")
        self.assertFalse(created)

    def test_qml_request_drop_node_from_library_places_node_at_exact_scene_position(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        placed = self.window.request_drop_node_from_library(
            "core.start",
            123.5,
            456.25,
            "",
            "",
            "",
            "",
        )
        self.assertTrue(placed)
        self.app.processEvents()

        node_id = self.window.scene.selected_node_id()
        self.assertTrue(node_id)
        workspace = self.window.model.project.workspaces[workspace_id]
        node = workspace.nodes[node_id]
        self.assertAlmostEqual(node.x, 123.5, places=4)
        self.assertAlmostEqual(node.y, 456.25, places=4)
        self.assertEqual(len(workspace.edges), 0)

    def test_qml_request_drop_node_from_library_port_target_autoconnects_single_candidate(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        target_id = self.window.scene.add_node_from_type("core.end", x=360.0, y=40.0)
        self.app.processEvents()

        created = self.window.request_drop_node_from_library(
            "core.start",
            120.0,
            60.0,
            "port",
            target_id,
            "exec_in",
            "",
        )
        self.assertTrue(created)
        self.app.processEvents()

        workspace = self.window.model.project.workspaces[workspace_id]
        self.assertEqual(len(workspace.edges), 1)
        new_node_id = self.window.scene.selected_node_id()
        self.assertTrue(new_node_id)
        edge = next(iter(workspace.edges.values()))
        self.assertEqual(edge.source_node_id, new_node_id)
        self.assertEqual(edge.source_port_key, "exec_out")
        self.assertEqual(edge.target_node_id, target_id)
        self.assertEqual(edge.target_port_key, "exec_in")

    def test_qml_request_drop_node_from_library_port_target_ambiguous_uses_prompt_selection(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        target_id = self.window.scene.add_node_from_type("core.logger", x=360.0, y=40.0)
        self.app.processEvents()

        with patch(
            "ea_node_editor.ui.shell.window.QInputDialog.getItem",
            return_value=("Constant.as_text -> Logger.message", True),
        ):
            created = self.window.request_drop_node_from_library(
                "core.constant",
                160.0,
                90.0,
                "port",
                target_id,
                "message",
                "",
            )
        self.assertTrue(created)
        self.app.processEvents()

        workspace = self.window.model.project.workspaces[workspace_id]
        self.assertEqual(len(workspace.edges), 1)
        edge = next(iter(workspace.edges.values()))
        self.assertEqual(edge.target_node_id, target_id)
        self.assertEqual(edge.target_port_key, "message")
        self.assertEqual(edge.source_port_key, "as_text")

    def test_qml_request_drop_node_from_library_edge_target_inserts_inline(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        source_id = self.window.scene.add_node_from_type("core.start", x=20.0, y=20.0)
        target_id = self.window.scene.add_node_from_type("core.end", x=380.0, y=20.0)
        edge_id = self.window.scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        self.app.processEvents()

        created = self.window.request_drop_node_from_library(
            "core.logger",
            210.0,
            90.0,
            "edge",
            "",
            "",
            edge_id,
        )
        self.assertTrue(created)
        self.app.processEvents()

        workspace = self.window.model.project.workspaces[workspace_id]
        self.assertNotIn(edge_id, workspace.edges)
        self.assertEqual(len(workspace.edges), 2)
        new_node_id = self.window.scene.selected_node_id()
        self.assertTrue(new_node_id)

        edge_tuples = {
            (edge.source_node_id, edge.source_port_key, edge.target_node_id, edge.target_port_key)
            for edge in workspace.edges.values()
        }
        self.assertIn((source_id, "exec_out", new_node_id, "exec_in"), edge_tuples)
        self.assertIn((new_node_id, "exec_out", target_id, "exec_in"), edge_tuples)

    def test_qml_request_drop_node_from_library_falls_back_to_node_only_when_no_valid_connection(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        target_id = self.window.scene.add_node_from_type("core.logger", x=320.0, y=20.0)
        self.app.processEvents()

        created = self.window.request_drop_node_from_library(
            "core.start",
            120.0,
            140.0,
            "port",
            target_id,
            "exec_out",
            "",
        )
        self.assertTrue(created)
        self.app.processEvents()

        workspace = self.window.model.project.workspaces[workspace_id]
        self.assertEqual(len(workspace.edges), 0)
        new_node_id = self.window.scene.selected_node_id()
        self.assertTrue(new_node_id)
        self.assertIn(new_node_id, workspace.nodes)

    def test_qml_request_remove_edge_mutates_model(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        source_id = self.window.scene.add_node_from_type("core.start", x=40.0, y=40.0)
        target_id = self.window.scene.add_node_from_type("core.end", x=280.0, y=40.0)
        edge_id = self.window.scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        self.app.processEvents()

        removed = self.window.request_remove_edge(edge_id)
        self.assertTrue(removed)
        self.assertNotIn(edge_id, self.window.model.project.workspaces[workspace_id].edges)

    def test_qml_request_remove_node_removes_incident_edges(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        source_id = self.window.scene.add_node_from_type("core.start", x=40.0, y=40.0)
        target_id = self.window.scene.add_node_from_type("core.end", x=280.0, y=40.0)
        edge_id = self.window.scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        self.app.processEvents()

        removed = self.window.request_remove_node(source_id)
        self.assertTrue(removed)
        workspace = self.window.model.project.workspaces[workspace_id]
        self.assertNotIn(source_id, workspace.nodes)
        self.assertNotIn(edge_id, workspace.edges)

    def test_qml_request_rename_node_updates_title(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("core.start", x=40.0, y=40.0)
        self.app.processEvents()

        with patch("ea_node_editor.ui.shell.window.QInputDialog.getText", return_value=("Renamed Node", True)):
            renamed = self.window.request_rename_node(node_id)
        self.assertTrue(renamed)
        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertEqual(node.title, "Renamed Node")

    def test_qml_request_delete_selected_graph_items_removes_nodes_and_edges(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        source_id = self.window.scene.add_node_from_type("core.start", x=40.0, y=40.0)
        target_id = self.window.scene.add_node_from_type("core.python_script", x=320.0, y=40.0)
        removable_node_id = self.window.scene.add_node_from_type("core.logger", x=520.0, y=40.0)
        edge_id = self.window.scene.add_edge(source_id, "trigger", target_id, "payload")
        self.window.scene.select_node(removable_node_id, False)
        self.app.processEvents()

        deleted = self.window.request_delete_selected_graph_items([edge_id])
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

        with patch("ea_node_editor.ui.shell.window.QInputDialog.getText", return_value=("Inspection", True)):
            self.window.request_create_view()
        self.app.processEvents()

        updated_workspace = self.window.model.project.workspaces[workspace_id]
        self.assertEqual(len(updated_workspace.views), initial_view_count + 1)
        self.assertEqual(self.window.active_view_name, "Inspection")

        active_items = [item for item in self.window.active_view_items if item.get("active")]
        self.assertEqual(len(active_items), 1)
        self.assertEqual(active_items[0]["label"], "Inspection")
        self.assertEqual(updated_workspace.active_view_id, active_items[0]["view_id"])

        self.window.request_switch_view(original_active_view_id)
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

if __name__ == "__main__":
    unittest.main()
