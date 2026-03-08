from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QObject, QMetaObject, Qt, Q_ARG
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

    def _active_workspace(self):
        workspace_id = self.window.workspace_manager.active_workspace_id()
        return workspace_id, self.window.model.project.workspaces[workspace_id]

    def _workspace_state(self) -> dict[str, object]:
        _workspace_id, workspace = self._active_workspace()
        nodes = {
            node_id: {
                "type_id": node.type_id,
                "title": node.title,
                "x": float(node.x),
                "y": float(node.y),
                "collapsed": bool(node.collapsed),
                "properties": dict(node.properties),
                "exposed_ports": dict(node.exposed_ports),
            }
            for node_id, node in workspace.nodes.items()
        }
        edges = {
            edge_id: (
                edge.source_node_id,
                edge.source_port_key,
                edge.target_node_id,
                edge.target_port_key,
            )
            for edge_id, edge in workspace.edges.items()
        }
        return {"nodes": nodes, "edges": edges}

    def _graph_canvas_item(self) -> QObject:
        root_object = self.window.quick_widget.rootObject()
        self.assertIsNotNone(root_object)
        graph_canvas = root_object.findChild(QObject, "graphCanvas")
        self.assertIsNotNone(graph_canvas)
        return graph_canvas

    def test_qml_shell_and_bridges_are_present(self) -> None:
        self.assertIsNotNone(self.window.quick_widget)
        self.assertIs(self.window.centralWidget(), self.window.quick_widget)
        self.assertIsNotNone(self.window.quick_widget.rootObject())
        self.assertIsNotNone(self.window.scene)
        self.assertIsNotNone(self.window.view)
        self.assertGreaterEqual(self.window.workspace_tabs.count(), 1)

    def test_qml_minimap_defaults_expanded_and_toggleable(self) -> None:
        graph_canvas = self._graph_canvas_item()
        self.assertTrue(bool(graph_canvas.property("minimapExpanded")))

        QMetaObject.invokeMethod(
            graph_canvas,
            "toggleMinimapExpanded",
            Qt.ConnectionType.DirectConnection,
        )
        self.app.processEvents()
        self.assertFalse(bool(graph_canvas.property("minimapExpanded")))

        QMetaObject.invokeMethod(
            graph_canvas,
            "toggleMinimapExpanded",
            Qt.ConnectionType.DirectConnection,
        )
        self.app.processEvents()
        self.assertTrue(bool(graph_canvas.property("minimapExpanded")))

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
        self.assertGreaterEqual(meta.indexOfMethod("request_duplicate_selected_nodes()"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("request_copy_selected_nodes()"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("request_cut_selected_nodes()"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("request_paste_selected_nodes()"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("request_undo()"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("request_redo()"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("request_align_selection_left()"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("request_align_selection_right()"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("request_align_selection_top()"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("request_align_selection_bottom()"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("request_distribute_selection_horizontally()"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("request_distribute_selection_vertically()"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("request_toggle_snap_to_grid()"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("request_open_subnode_scope(QString)"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("request_open_scope_breadcrumb(QString)"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("request_navigate_scope_parent()"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("request_navigate_scope_root()"), 0)
        self.assertGreaterEqual(
            meta.indexOfMethod("request_drop_node_from_library(QString,double,double,QString,QString,QString,QString)"),
            0,
        )

        with patch("ea_node_editor.ui.dialogs.workflow_settings_dialog.WorkflowSettingsDialog.exec", return_value=0):
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
        self.assertIn("A", _action_shortcuts(self.window.action_frame_all))
        self.assertIn("F", _action_shortcuts(self.window.action_frame_selection))
        self.assertIn("Shift+F", _action_shortcuts(self.window.action_center_selection))
        self.assertIn("Ctrl+Z", _action_shortcuts(self.window.action_undo))
        self.assertIn("Ctrl+Shift+Z", _action_shortcuts(self.window.action_redo))
        self.assertIn("Ctrl+Y", _action_shortcuts(self.window.action_redo))
        self.assertIn("Ctrl+K", _action_shortcuts(self.window.action_graph_search))
        self.assertIn("Ctrl+D", _action_shortcuts(self.window.action_duplicate_selection))
        self.assertIn("Ctrl+C", _action_shortcuts(self.window.action_copy_selection))
        self.assertIn("Ctrl+X", _action_shortcuts(self.window.action_cut_selection))
        self.assertIn("Ctrl+V", _action_shortcuts(self.window.action_paste_selection))
        self.assertIn("Alt+Left", _action_shortcuts(self.window.action_scope_parent))
        self.assertIn("Alt+Home", _action_shortcuts(self.window.action_scope_root))
        self.assertTrue(self.window.action_snap_to_grid.isCheckable())
        self.assertFalse(self.window.snap_to_grid_enabled)
        self.assertFalse(self.window.action_snap_to_grid.isChecked())

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

    def test_layout_actions_and_snap_toggle_are_undoable(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        node_a = self.window.scene.add_node_from_type("core.start", x=20.0, y=40.0)
        node_b = self.window.scene.add_node_from_type("core.end", x=320.0, y=180.0)
        node_c = self.window.scene.add_node_from_type("core.logger", x=640.0, y=80.0)
        self.window.scene.select_node(node_a, False)
        self.window.scene.select_node(node_b, True)
        self.window.scene.select_node(node_c, True)
        self.window.runtime_history.clear_workspace(workspace_id)
        before_state = self._workspace_state()

        self.window.action_distribute_horizontally.trigger()
        self.app.processEvents()
        after_distribute = self._workspace_state()
        self.assertNotEqual(after_distribute, before_state)
        self.assertEqual(self.window.runtime_history.undo_depth(workspace_id), 1)

        distributed_bounds = sorted(
            (self.window.scene.node_bounds(node_id) for node_id in (node_a, node_b, node_c)),
            key=lambda bounds: float(bounds.x()) if bounds is not None else 0.0,
        )
        self.assertTrue(all(bounds is not None for bounds in distributed_bounds))
        gap_01 = distributed_bounds[1].x() - (distributed_bounds[0].x() + distributed_bounds[0].width())
        gap_12 = distributed_bounds[2].x() - (distributed_bounds[1].x() + distributed_bounds[1].width())
        self.assertAlmostEqual(gap_01, gap_12, places=6)

        self.window.action_undo.trigger()
        self.app.processEvents()
        self.assertEqual(self._workspace_state(), before_state)
        self.window.action_redo.trigger()
        self.app.processEvents()
        self.assertEqual(self._workspace_state(), after_distribute)

        self.window.scene.move_node(node_a, 13.0, 17.0)
        self.window.scene.move_node(node_b, 171.0, 83.0)
        self.window.scene.select_node(node_a, False)
        self.window.scene.select_node(node_b, True)
        self.window.runtime_history.clear_workspace(workspace_id)

        self.assertFalse(self.window.snap_to_grid_enabled)
        self.window.action_snap_to_grid.trigger()
        self.assertTrue(self.window.snap_to_grid_enabled)
        self.assertTrue(self.window.action_snap_to_grid.isChecked())

        before_snap_layout = self._workspace_state()
        self.window.action_align_top.trigger()
        self.app.processEvents()
        after_snap_layout = self._workspace_state()
        self.assertNotEqual(after_snap_layout, before_snap_layout)
        self.assertEqual(self.window.runtime_history.undo_depth(workspace_id), 1)

        for node_id in (node_a, node_b):
            node = workspace.nodes[node_id]
            self.assertAlmostEqual(float(node.x) / 20.0, round(float(node.x) / 20.0), places=6)
            self.assertAlmostEqual(float(node.y) / 20.0, round(float(node.y) / 20.0), places=6)

        self.window.action_undo.trigger()
        self.app.processEvents()
        self.assertEqual(self._workspace_state(), before_snap_layout)

        self.window.action_snap_to_grid.trigger()
        self.assertFalse(self.window.snap_to_grid_enabled)
        self.assertFalse(self.window.action_snap_to_grid.isChecked())

    def test_align_overlap_posts_tidy_hint(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        _workspace = self.window.model.project.workspaces[workspace_id]
        node_a = self.window.scene.add_node_from_type("core.start", x=20.0, y=60.0)
        node_b = self.window.scene.add_node_from_type("core.end", x=340.0, y=60.0)
        node_c = self.window.scene.add_node_from_type("core.logger", x=680.0, y=60.0)
        self.window.scene.select_node(node_a, False)
        self.window.scene.select_node(node_b, True)
        self.window.scene.select_node(node_c, True)
        self.window.clear_graph_hint()
        self.assertFalse(self.window.graph_hint_visible)

        aligned = self.window.request_align_selection_right()
        self.assertTrue(aligned)
        self.app.processEvents()

        self.assertTrue(self.window.graph_hint_visible)
        self.assertEqual(
            self.window.graph_hint_message,
            "3 overlaps created. Press Distribute Vertically to tidy.",
        )

        root_object = self.window.quick_widget.rootObject()
        self.assertIsNotNone(root_object)
        graph_hint_overlay = root_object.findChild(QObject, "graphHintOverlay")
        self.assertIsNotNone(graph_hint_overlay)
        self.assertTrue(bool(graph_hint_overlay.property("visible")))

        self.window.clear_graph_hint()
        self.app.processEvents()
        self.assertFalse(self.window.graph_hint_visible)

    def test_graph_search_ranking_prefers_title_matches_and_limits_to_ten_results(self) -> None:
        workspace_a_id = self.window.workspace_manager.active_workspace_id()
        self.window.workspace_manager.rename_workspace(workspace_a_id, "Alpha Space")
        self.window._refresh_workspace_tabs()
        self.window._switch_workspace(workspace_a_id)

        prefix_id = self.window.scene.add_node_from_type("core.start", x=20.0, y=20.0)
        self.window.scene.set_node_title(prefix_id, "core. prefix title")
        substring_id = self.window.scene.add_node_from_type("core.start", x=220.0, y=20.0)
        self.window.scene.set_node_title(substring_id, "alpha core. substring")
        type_alpha_id = self.window.scene.add_node_from_type("core.start", x=420.0, y=20.0)
        self.window.scene.set_node_title(type_alpha_id, "Alpha")
        type_zulu_id = self.window.scene.add_node_from_type("core.start", x=620.0, y=20.0)
        self.window.scene.set_node_title(type_zulu_id, "Zulu")

        workspace_b_id = self.window.workspace_manager.create_workspace("Beta Space")
        self.window._refresh_workspace_tabs()
        self.window._switch_workspace(workspace_b_id)
        for index in range(12):
            node_id = self.window.scene.add_node_from_type("core.start", x=20.0 * index, y=120.0)
            self.window.scene.set_node_title(node_id, f"Node {index:02d}")
        self.app.processEvents()

        self.window.action_graph_search.trigger()
        self.window.set_graph_search_query("CORE.")
        self.app.processEvents()

        results = self.window.graph_search_results
        self.assertEqual(len(results), 10)
        self.assertEqual(results[0]["node_id"], prefix_id)
        self.assertEqual(results[1]["node_id"], substring_id)

        tail_keys = [(item["workspace_name"], item["node_title"]) for item in results[2:]]
        self.assertEqual(
            tail_keys,
            sorted(tail_keys, key=lambda value: (value[0].lower(), value[1].lower())),
        )

    def test_graph_search_matches_node_id_and_empty_or_missing_queries_are_safe_noops(self) -> None:
        node_id = self.window.scene.add_node_from_type("core.start", x=30.0, y=30.0)
        self.window.scene.set_node_title(node_id, "Plain Title")
        display_name_id = self.window.scene.add_node_from_type("core.python_script", x=260.0, y=40.0)
        self.window.scene.set_node_title(display_name_id, "Custom Script Title")
        self.app.processEvents()

        self.window.action_graph_search.trigger()
        self.window.set_graph_search_query(node_id[-6:].upper())
        self.app.processEvents()

        results = self.window.graph_search_results
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["node_id"], node_id)

        self.window.set_graph_search_query("PyThOn ScRiPt")
        self.app.processEvents()
        self.assertIn(display_name_id, {item["node_id"] for item in self.window.graph_search_results})

        self.window.set_graph_search_query("")
        self.assertEqual(self.window.graph_search_results, [])
        self.assertFalse(self.window.request_graph_search_accept())

        before_workspace_id = self.window.workspace_manager.active_workspace_id()
        before_selected_id = self.window.scene.selected_node_id()
        self.window.set_graph_search_query("zzzzz_missing_node_query")
        self.assertEqual(self.window.graph_search_results, [])
        self.assertFalse(self.window.request_graph_search_accept())
        self.assertEqual(self.window.workspace_manager.active_workspace_id(), before_workspace_id)
        self.assertEqual(self.window.scene.selected_node_id(), before_selected_id)

    def test_graph_search_jump_switches_workspace_reveals_parent_chain_and_centers_selection(self) -> None:
        source_workspace_id = self.window.workspace_manager.active_workspace_id()
        target_workspace_id = self.window.workspace_manager.create_workspace("Target Space")
        self.window._refresh_workspace_tabs()
        self.window._switch_workspace(target_workspace_id)

        parent_id = self.window.scene.add_node_from_type("core.start", x=140.0, y=80.0)
        child_id = self.window.scene.add_node_from_type("core.logger", x=640.0, y=360.0)
        target_workspace = self.window.model.project.workspaces[target_workspace_id]
        target_workspace.nodes[child_id].parent_node_id = parent_id
        self.window.scene.set_node_collapsed(parent_id, True)
        self.window.scene.set_node_title(child_id, "Needle Jump Node")
        self.app.processEvents()

        self.window._switch_workspace(source_workspace_id)
        self.window.view.set_zoom(0.65)
        self.window.view.centerOn(-420.0, -260.0)

        self.window.action_graph_search.trigger()
        self.window.set_graph_search_query("needle jump")
        self.app.processEvents()
        self.assertEqual(self.window.graph_search_highlight_index, 0)

        jumped = self.window.request_graph_search_accept()
        self.assertTrue(jumped)
        self.app.processEvents()

        self.assertEqual(self.window.workspace_manager.active_workspace_id(), target_workspace_id)
        self.assertFalse(target_workspace.nodes[parent_id].collapsed)
        self.assertEqual(self.window.scene.selected_node_id(), child_id)

        bounds = self.window.scene.node_bounds(child_id)
        self.assertIsNotNone(bounds)
        target_workspace.ensure_default_view()
        target_view = target_workspace.views[target_workspace.active_view_id]
        self.assertAlmostEqual(self.window.view.zoom, target_view.zoom, places=6)
        self.assertAlmostEqual(self.window.view.center_x, bounds.center().x(), places=6)
        self.assertAlmostEqual(self.window.view.center_y, bounds.center().y(), places=6)

        self.assertFalse(self.window.graph_search_open)
        self.assertEqual(self.window.graph_search_query, "")
        self.assertEqual(self.window.graph_search_results, [])

    def test_graph_search_keyboard_navigation_and_close_behavior(self) -> None:
        node_a_id = self.window.scene.add_node_from_type("core.start", x=50.0, y=50.0)
        node_b_id = self.window.scene.add_node_from_type("core.start", x=250.0, y=50.0)
        self.window.scene.set_node_title(node_a_id, "Search Candidate A")
        self.window.scene.set_node_title(node_b_id, "Search Candidate B")
        self.app.processEvents()

        self.window.action_graph_search.trigger()
        self.assertTrue(self.window.graph_search_open)
        self.window.set_graph_search_query("search candidate")
        self.app.processEvents()
        self.assertGreaterEqual(len(self.window.graph_search_results), 2)
        self.assertEqual(self.window.graph_search_highlight_index, 0)

        self.window.request_graph_search_move(1)
        self.assertEqual(self.window.graph_search_highlight_index, 1)
        self.window.request_graph_search_move(1)
        self.assertEqual(self.window.graph_search_highlight_index, 1)
        self.window.request_graph_search_move(-1)
        self.assertEqual(self.window.graph_search_highlight_index, 0)
        self.window.request_graph_search_move(-1)
        self.assertEqual(self.window.graph_search_highlight_index, 0)

        self.window.request_close_graph_search()
        self.assertFalse(self.window.graph_search_open)
        self.assertEqual(self.window.graph_search_query, "")
        self.assertEqual(self.window.graph_search_results, [])
        self.assertEqual(self.window.graph_search_highlight_index, -1)

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
            "PyQt6.QtWidgets.QInputDialog.getItem",
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

        with patch("PyQt6.QtWidgets.QInputDialog.getText", return_value=("Renamed Node", True)):
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

    def test_qml_request_duplicate_selected_nodes_duplicates_internal_edges_and_selects_result(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        source_id = self.window.scene.add_node_from_type("core.start", x=40.0, y=40.0)
        target_id = self.window.scene.add_node_from_type("core.end", x=280.0, y=40.0)
        external_id = self.window.scene.add_node_from_type("core.python_script", x=520.0, y=90.0)
        self.window.scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        self.window.scene.add_edge(source_id, "trigger", external_id, "payload")
        workspace = self.window.model.project.workspaces[workspace_id]
        before_nodes = len(workspace.nodes)
        before_edges = len(workspace.edges)

        workspace_b_id = self.window.workspace_manager.create_workspace("Secondary")
        self.window._refresh_workspace_tabs()
        self.window._switch_workspace(workspace_b_id)
        self.window.scene.add_node_from_type("core.logger", x=80.0, y=80.0)
        self.window._switch_workspace(workspace_id)
        self.app.processEvents()

        self.window.scene.select_node(source_id, False)
        self.window.scene.select_node(target_id, True)

        duplicated = self.window.request_duplicate_selected_nodes()
        self.assertTrue(duplicated)
        self.app.processEvents()

        workspace = self.window.model.project.workspaces[workspace_id]
        self.assertEqual(len(workspace.nodes), before_nodes + 2)
        self.assertEqual(len(workspace.edges), before_edges + 1)
        secondary_workspace = self.window.model.project.workspaces[workspace_b_id]
        self.assertEqual(len(secondary_workspace.nodes), 1)
        self.assertEqual(len(secondary_workspace.edges), 0)

        selected_duplicate_ids = {
            item["node_id"]
            for item in self.window.scene.nodes_model
            if item["selected"]
        }
        self.assertEqual(len(selected_duplicate_ids), 2)
        self.assertNotIn(source_id, selected_duplicate_ids)
        self.assertNotIn(target_id, selected_duplicate_ids)

        source_node = workspace.nodes[source_id]
        target_node = workspace.nodes[target_id]
        duplicate_source_id = ""
        duplicate_target_id = ""
        for node_id in selected_duplicate_ids:
            node = workspace.nodes[node_id]
            if (
                node.type_id == source_node.type_id
                and node.title == source_node.title
                and abs(node.x - (source_node.x + 40.0)) < 1e-6
                and abs(node.y - (source_node.y + 40.0)) < 1e-6
            ):
                duplicate_source_id = node_id
            if (
                node.type_id == target_node.type_id
                and node.title == target_node.title
                and abs(node.x - (target_node.x + 40.0)) < 1e-6
                and abs(node.y - (target_node.y + 40.0)) < 1e-6
            ):
                duplicate_target_id = node_id
        self.assertTrue(duplicate_source_id)
        self.assertTrue(duplicate_target_id)

        duplicated_internal_edges = [
            edge
            for edge in workspace.edges.values()
            if edge.source_node_id == duplicate_source_id
            and edge.source_port_key == "exec_out"
            and edge.target_node_id == duplicate_target_id
            and edge.target_port_key == "exec_in"
        ]
        self.assertEqual(len(duplicated_internal_edges), 1)
        duplicated_external_edges = [
            edge
            for edge in workspace.edges.values()
            if edge.source_node_id == duplicate_source_id and edge.source_port_key == "trigger"
        ]
        self.assertEqual(duplicated_external_edges, [])

    def test_qml_request_duplicate_selected_nodes_is_safe_noop_without_selection(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        self.window.scene.add_node_from_type("core.start", x=20.0, y=20.0)
        self.window.scene.clear_selection()
        workspace = self.window.model.project.workspaces[workspace_id]
        before_state = self._workspace_state()
        before_undo_depth = self.window.runtime_history.undo_depth(workspace_id)

        duplicated = self.window.request_duplicate_selected_nodes()
        self.assertFalse(duplicated)
        self.app.processEvents()

        self.assertEqual(self._workspace_state(), before_state)
        self.assertEqual(self.window.runtime_history.undo_depth(workspace_id), before_undo_depth)
        self.assertEqual(len(workspace.nodes), 1)

    def test_qml_request_copy_and_paste_selected_nodes_preserves_internal_edges_and_recenters_fragment(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        source_id = self.window.scene.add_node_from_type("core.start", x=60.0, y=50.0)
        target_id = self.window.scene.add_node_from_type("core.end", x=360.0, y=190.0)
        external_id = self.window.scene.add_node_from_type("core.python_script", x=680.0, y=90.0)
        self.window.scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        self.window.scene.add_edge(source_id, "trigger", external_id, "payload")
        workspace = self.window.model.project.workspaces[workspace_id]
        before_nodes = len(workspace.nodes)
        before_edges = len(workspace.edges)

        source_node = workspace.nodes[source_id]
        target_node = workspace.nodes[target_id]
        relative_dx = float(target_node.x) - float(source_node.x)
        relative_dy = float(target_node.y) - float(source_node.y)

        self.window.scene.select_node(source_id, False)
        self.window.scene.select_node(target_id, True)
        self.window.view.set_zoom(0.75)
        self.window.view.centerOn(980.0, -210.0)
        self.app.processEvents()

        copied = self.window.request_copy_selected_nodes()
        self.assertTrue(copied)
        pasted = self.window.request_paste_selected_nodes()
        self.assertTrue(pasted)
        self.app.processEvents()

        workspace = self.window.model.project.workspaces[workspace_id]
        self.assertEqual(len(workspace.nodes), before_nodes + 2)
        self.assertEqual(len(workspace.edges), before_edges + 1)

        pasted_node_ids = {
            item["node_id"]
            for item in self.window.scene.nodes_model
            if item["selected"]
        }
        self.assertEqual(len(pasted_node_ids), 2)
        self.assertNotIn(source_id, pasted_node_ids)
        self.assertNotIn(target_id, pasted_node_ids)

        pasted_source = None
        pasted_target = None
        for node_id in pasted_node_ids:
            node = workspace.nodes[node_id]
            if node.type_id == "core.start":
                pasted_source = node
            elif node.type_id == "core.end":
                pasted_target = node
        self.assertIsNotNone(pasted_source)
        self.assertIsNotNone(pasted_target)
        self.assertAlmostEqual(float(pasted_target.x) - float(pasted_source.x), relative_dx, places=6)
        self.assertAlmostEqual(float(pasted_target.y) - float(pasted_source.y), relative_dy, places=6)

        internal_edges = [
            edge
            for edge in workspace.edges.values()
            if edge.source_node_id == pasted_source.node_id
            and edge.source_port_key == "exec_out"
            and edge.target_node_id == pasted_target.node_id
            and edge.target_port_key == "exec_in"
        ]
        self.assertEqual(len(internal_edges), 1)
        external_edges = [
            edge
            for edge in workspace.edges.values()
            if edge.source_node_id == pasted_source.node_id and edge.source_port_key == "trigger"
        ]
        self.assertEqual(external_edges, [])

        selection_bounds = self.window.scene.selection_bounds()
        self.assertIsNotNone(selection_bounds)
        viewport_center = self.window.view.mapToScene(self.window.view.viewport().rect().center())
        self.assertAlmostEqual(selection_bounds.center().x(), viewport_center.x(), places=5)
        self.assertAlmostEqual(selection_bounds.center().y(), viewport_center.y(), places=5)

    def test_qml_request_paste_selected_nodes_into_other_workspace_selects_pasted_nodes(self) -> None:
        source_workspace_id = self.window.workspace_manager.active_workspace_id()
        source_a_id = self.window.scene.add_node_from_type("core.start", x=100.0, y=120.0)
        source_b_id = self.window.scene.add_node_from_type("core.end", x=340.0, y=140.0)
        self.window.scene.add_edge(source_a_id, "exec_out", source_b_id, "exec_in")
        source_workspace = self.window.model.project.workspaces[source_workspace_id]
        before_source_nodes = len(source_workspace.nodes)
        before_source_edges = len(source_workspace.edges)
        self.window.scene.select_node(source_a_id, False)
        self.window.scene.select_node(source_b_id, True)
        self.assertTrue(self.window.request_copy_selected_nodes())

        target_workspace_id = self.window.workspace_manager.create_workspace("Clipboard Target")
        self.window._refresh_workspace_tabs()
        self.window._switch_workspace(target_workspace_id)
        self.window.view.centerOn(-430.0, 280.0)
        target_workspace = self.window.model.project.workspaces[target_workspace_id]
        before_target_nodes = len(target_workspace.nodes)
        before_target_edges = len(target_workspace.edges)

        pasted = self.window.request_paste_selected_nodes()
        self.assertTrue(pasted)
        self.app.processEvents()

        target_workspace = self.window.model.project.workspaces[target_workspace_id]
        self.assertEqual(len(target_workspace.nodes), before_target_nodes + 2)
        self.assertEqual(len(target_workspace.edges), before_target_edges + 1)
        selected_pasted_ids = {
            item["node_id"]
            for item in self.window.scene.nodes_model
            if item["selected"]
        }
        self.assertEqual(len(selected_pasted_ids), 2)
        self.assertEqual(self.window.workspace_manager.active_workspace_id(), target_workspace_id)

        source_workspace = self.window.model.project.workspaces[source_workspace_id]
        self.assertEqual(len(source_workspace.nodes), before_source_nodes)
        self.assertEqual(len(source_workspace.edges), before_source_edges)

    def test_qml_request_paste_selected_nodes_offsets_repeated_paste_from_same_clipboard(self) -> None:
        source_id = self.window.scene.add_node_from_type("core.start", x=50.0, y=60.0)
        target_id = self.window.scene.add_node_from_type("core.end", x=240.0, y=110.0)
        self.window.scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        self.window.scene.select_node(source_id, False)
        self.window.scene.select_node(target_id, True)
        self.window.view.centerOn(300.0, -120.0)
        self.app.processEvents()

        self.assertTrue(self.window.request_copy_selected_nodes())

        self.assertTrue(self.window.request_paste_selected_nodes())
        self.app.processEvents()
        first_bounds = self.window.scene.selection_bounds()
        self.assertIsNotNone(first_bounds)

        self.assertTrue(self.window.request_paste_selected_nodes())
        self.app.processEvents()
        second_bounds = self.window.scene.selection_bounds()
        self.assertIsNotNone(second_bounds)

        viewport_center = self.window.view.mapToScene(self.window.view.viewport().rect().center())
        self.assertAlmostEqual(first_bounds.center().x(), viewport_center.x(), places=5)
        self.assertAlmostEqual(first_bounds.center().y(), viewport_center.y(), places=5)
        self.assertAlmostEqual(second_bounds.center().x(), viewport_center.x() + 40.0, places=5)
        self.assertAlmostEqual(second_bounds.center().y(), viewport_center.y() + 40.0, places=5)

    def test_qml_request_cut_selected_nodes_is_single_undoable_semantic_action(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        source_id = self.window.scene.add_node_from_type("core.start", x=80.0, y=70.0)
        target_id = self.window.scene.add_node_from_type("core.end", x=300.0, y=80.0)
        self.window.scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        self.window.scene.select_node(source_id, False)
        self.window.scene.select_node(target_id, True)
        before_state = self._workspace_state()
        before_depth = self.window.runtime_history.undo_depth(workspace_id)
        self.app.processEvents()

        cut = self.window.request_cut_selected_nodes()
        self.assertTrue(cut)
        self.app.processEvents()
        after_cut_state = self._workspace_state()
        self.assertNotEqual(after_cut_state, before_state)
        self.assertEqual(self.window.runtime_history.undo_depth(workspace_id), before_depth + 1)

        self.window.action_undo.trigger()
        self.app.processEvents()
        self.assertEqual(self._workspace_state(), before_state)

        self.window.action_redo.trigger()
        self.app.processEvents()
        self.assertEqual(self._workspace_state(), after_cut_state)

    def test_qml_request_paste_selected_nodes_ignores_invalid_and_foreign_clipboard_payloads(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        self.window.scene.add_node_from_type("core.start", x=25.0, y=35.0)
        before_state = self._workspace_state()
        before_depth = self.window.runtime_history.undo_depth(workspace_id)
        clipboard = self.app.clipboard()

        clipboard.setText("{not valid json")
        invalid_paste = self.window.request_paste_selected_nodes()
        self.assertFalse(invalid_paste)
        self.assertEqual(self._workspace_state(), before_state)
        self.assertEqual(self.window.runtime_history.undo_depth(workspace_id), before_depth)

        clipboard.setText('{"kind":"foreign-fragment","version":1,"nodes":[],"edges":[]}')
        foreign_paste = self.window.request_paste_selected_nodes()
        self.assertFalse(foreign_paste)
        self.assertEqual(self._workspace_state(), before_state)
        self.assertEqual(self.window.runtime_history.undo_depth(workspace_id), before_depth)

    def test_undo_redo_roundtrips_supported_graph_mutations(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()

        def assert_roundtrip(mutate, label: str) -> None:  # noqa: ANN001
            before_state = self._workspace_state()
            before_depth = self.window.runtime_history.undo_depth(workspace_id)
            mutate()
            self.app.processEvents()
            after_state = self._workspace_state()
            self.assertNotEqual(before_state, after_state, label)
            self.assertEqual(self.window.runtime_history.undo_depth(workspace_id), before_depth + 1, label)

            self.window.action_undo.trigger()
            self.app.processEvents()
            self.assertEqual(self._workspace_state(), before_state, f"{label}: undo")

            self.window.action_redo.trigger()
            self.app.processEvents()
            self.assertEqual(self._workspace_state(), after_state, f"{label}: redo")

        source_id = self.window.scene.add_node_from_type("core.start", x=40.0, y=40.0)
        target_id = self.window.scene.add_node_from_type("core.end", x=280.0, y=40.0)
        logger_id = self.window.scene.add_node_from_type("core.logger", x=520.0, y=120.0)
        self.app.processEvents()

        assert_roundtrip(
            lambda: self.window.scene.add_node_from_type("core.python_script", x=620.0, y=80.0),
            "add node",
        )

        edge_holder: dict[str, str] = {}

        def add_edge() -> None:
            edge_holder["edge_id"] = self.window.scene.add_edge(source_id, "exec_out", target_id, "exec_in")

        assert_roundtrip(add_edge, "add edge")
        primary_edge_id = edge_holder["edge_id"]

        assert_roundtrip(lambda: self.window.request_remove_edge(primary_edge_id), "remove edge")

        def rename_node() -> None:
            current_title = self.window.model.project.workspaces[workspace_id].nodes[source_id].title
            with patch("PyQt6.QtWidgets.QInputDialog.getText", return_value=(f"{current_title} (renamed)", True)):
                self.window.request_rename_node(source_id)

        assert_roundtrip(rename_node, "rename node")

        def toggle_collapse() -> None:
            self.window.scene.focus_node(source_id)
            self.window.set_selected_node_collapsed(not self.window.selected_node_collapsed)

        assert_roundtrip(toggle_collapse, "collapse toggle")

        self.window.scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        self.app.processEvents()

        def toggle_exposed_port() -> None:
            workspace = self.window.model.project.workspaces[workspace_id]
            source_node = workspace.nodes[source_id]
            current = bool(source_node.exposed_ports.get("exec_out", True))
            self.window.scene.focus_node(source_id)
            self.window.set_selected_port_exposed("exec_out", not current)

        assert_roundtrip(toggle_exposed_port, "exposed-port toggle")

        def edit_property() -> None:
            self.window.scene.focus_node(logger_id)
            self.window.set_selected_node_property("message", "updated through undo/redo roundtrip")

        assert_roundtrip(edit_property, "property edit")

        delete_node_id = self.window.scene.add_node_from_type("core.python_script", x=680.0, y=150.0)
        delete_edge_id = self.window.scene.add_edge(source_id, "trigger", delete_node_id, "payload")
        self.window.scene.select_node(delete_node_id, False)
        self.app.processEvents()
        assert_roundtrip(
            lambda: self.window.request_delete_selected_graph_items([delete_edge_id]),
            "delete-selected",
        )

        def move_node() -> None:
            workspace = self.window.model.project.workspaces[workspace_id]
            source_node = workspace.nodes[source_id]
            self.window.scene.move_node(source_id, source_node.x + 130.0, source_node.y + 75.0)

        assert_roundtrip(move_node, "node move")

        def move_group_nodes() -> None:
            self.window.scene.select_node(source_id, False)
            self.window.scene.select_node(logger_id, True)
            self.window.scene.move_nodes_by_delta([source_id, logger_id], 90.0, 35.0)

        assert_roundtrip(move_group_nodes, "group node move")

        def duplicate_selection() -> None:
            self.window.scene.select_node(source_id, False)
            self.window.scene.select_node(target_id, True)
            self.window.request_duplicate_selected_nodes()

        assert_roundtrip(duplicate_selection, "duplicate-selection")

        assert_roundtrip(lambda: self.window.request_remove_node(target_id), "remove node")

    def test_undo_redo_isolated_per_workspace_and_redo_clears_after_new_mutation(self) -> None:
        workspace_a_id = self.window.workspace_manager.active_workspace_id()
        node_a_id = self.window.scene.add_node_from_type("core.start", x=20.0, y=20.0)
        self.app.processEvents()

        workspace_b_id = self.window.workspace_manager.create_workspace("Secondary")
        self.window._refresh_workspace_tabs()
        self.window._switch_workspace(workspace_b_id)
        self.app.processEvents()

        self.assertEqual(self.window.runtime_history.undo_depth(workspace_b_id), 0)
        node_b_id = self.window.scene.add_node_from_type("core.end", x=40.0, y=40.0)
        self.app.processEvents()
        self.assertIn(node_b_id, self.window.model.project.workspaces[workspace_b_id].nodes)

        self.window.action_undo.trigger()
        self.app.processEvents()
        self.assertNotIn(node_b_id, self.window.model.project.workspaces[workspace_b_id].nodes)
        self.assertIn(node_a_id, self.window.model.project.workspaces[workspace_a_id].nodes)

        self.window.action_redo.trigger()
        self.app.processEvents()
        self.assertIn(node_b_id, self.window.model.project.workspaces[workspace_b_id].nodes)

        self.window.action_undo.trigger()
        self.app.processEvents()
        self.assertEqual(self.window.runtime_history.redo_depth(workspace_b_id), 1)

        replacement_node_id = self.window.scene.add_node_from_type("core.logger", x=120.0, y=50.0)
        self.app.processEvents()
        self.assertIn(replacement_node_id, self.window.model.project.workspaces[workspace_b_id].nodes)
        self.assertEqual(self.window.runtime_history.redo_depth(workspace_b_id), 0)

        before_failed_redo = self._workspace_state()
        self.window.action_redo.trigger()
        self.app.processEvents()
        self.assertEqual(self._workspace_state(), before_failed_redo)

        self.window._switch_workspace(workspace_a_id)
        self.app.processEvents()
        self.window.action_undo.trigger()
        self.app.processEvents()
        self.assertNotIn(node_a_id, self.window.model.project.workspaces[workspace_a_id].nodes)
        self.assertIn(replacement_node_id, self.window.model.project.workspaces[workspace_b_id].nodes)

    def test_new_and_duplicated_workspaces_start_with_empty_history(self) -> None:
        workspace_a_id = self.window.workspace_manager.active_workspace_id()
        self.window.scene.add_node_from_type("core.start", x=10.0, y=10.0)
        self.app.processEvents()
        self.assertGreater(self.window.runtime_history.undo_depth(workspace_a_id), 0)

        workspace_b_id = self.window.workspace_manager.create_workspace("New Workspace")
        self.window._refresh_workspace_tabs()
        self.assertEqual(self.window.runtime_history.undo_depth(workspace_b_id), 0)
        self.assertEqual(self.window.runtime_history.redo_depth(workspace_b_id), 0)

        self.window._switch_workspace(workspace_a_id)
        self.app.processEvents()
        duplicated_id = self.window.workspace_manager.duplicate_workspace(workspace_a_id)
        self.window._refresh_workspace_tabs()
        self.assertEqual(self.window.runtime_history.undo_depth(duplicated_id), 0)
        self.assertEqual(self.window.runtime_history.redo_depth(duplicated_id), 0)

    def test_new_project_clears_runtime_history_stacks(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        self.window.scene.add_node_from_type("core.start", x=0.0, y=0.0)
        self.app.processEvents()
        self.assertGreater(self.window.runtime_history.undo_depth(workspace_id), 0)

        self.window.action_new_project.trigger()
        self.app.processEvents()

        new_workspace_id = self.window.workspace_manager.active_workspace_id()
        self.assertEqual(self.window.runtime_history.undo_depth(new_workspace_id), 0)
        self.assertEqual(self.window.runtime_history.redo_depth(new_workspace_id), 0)

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

    def test_viewport_commands_frame_all_frame_selection_and_center_selection(self) -> None:
        node_a = self.window.scene.add_node_from_type("core.start", x=20.0, y=30.0)
        self.window.scene.add_node_from_type("core.end", x=540.0, y=260.0)
        self.app.processEvents()

        workspace_bounds = self.window.scene.workspace_scene_bounds()
        self.assertIsNotNone(workspace_bounds)
        self.window.view.set_zoom(0.6)
        self.window.view.centerOn(-220.0, -140.0)

        self.window.action_frame_all.trigger()
        self.app.processEvents()

        expected_all_zoom = self.window.view.fit_zoom_for_scene_rect(workspace_bounds)
        self.assertAlmostEqual(self.window.view.zoom, expected_all_zoom, places=6)
        self.assertAlmostEqual(self.window.view.center_x, workspace_bounds.center().x(), places=6)
        self.assertAlmostEqual(self.window.view.center_y, workspace_bounds.center().y(), places=6)

        self.window.scene.select_node(node_a)
        selection_bounds = self.window.scene.selection_bounds()
        self.assertIsNotNone(selection_bounds)

        self.window.action_frame_selection.trigger()
        self.app.processEvents()

        expected_selection_zoom = self.window.view.fit_zoom_for_scene_rect(selection_bounds)
        self.assertAlmostEqual(self.window.view.zoom, expected_selection_zoom, places=6)
        self.assertAlmostEqual(self.window.view.center_x, selection_bounds.center().x(), places=6)
        self.assertAlmostEqual(self.window.view.center_y, selection_bounds.center().y(), places=6)

        self.window.view.set_zoom(1.3)
        self.window.view.centerOn(900.0, -400.0)
        self.window.action_center_selection.trigger()
        self.app.processEvents()

        self.assertAlmostEqual(self.window.view.zoom, 1.3, places=6)
        self.assertAlmostEqual(self.window.view.center_x, selection_bounds.center().x(), places=6)
        self.assertAlmostEqual(self.window.view.center_y, selection_bounds.center().y(), places=6)

    def test_viewport_commands_are_noops_for_empty_graph_or_empty_selection(self) -> None:
        self.window.view.set_zoom(1.2)
        self.window.view.centerOn(55.0, -75.0)
        self.window.action_frame_all.trigger()
        self.app.processEvents()
        self.assertAlmostEqual(self.window.view.zoom, 1.2, places=6)
        self.assertAlmostEqual(self.window.view.center_x, 55.0, places=6)
        self.assertAlmostEqual(self.window.view.center_y, -75.0, places=6)

        self.window.scene.add_node_from_type("core.start", x=20.0, y=20.0)
        self.window.scene.clear_selection()
        self.window.view.set_zoom(0.9)
        self.window.view.centerOn(-25.0, 45.0)

        self.window.action_frame_selection.trigger()
        self.app.processEvents()
        self.assertAlmostEqual(self.window.view.zoom, 0.9, places=6)
        self.assertAlmostEqual(self.window.view.center_x, -25.0, places=6)
        self.assertAlmostEqual(self.window.view.center_y, 45.0, places=6)

        self.window.action_center_selection.trigger()
        self.app.processEvents()
        self.assertAlmostEqual(self.window.view.zoom, 0.9, places=6)
        self.assertAlmostEqual(self.window.view.center_x, -25.0, places=6)
        self.assertAlmostEqual(self.window.view.center_y, 45.0, places=6)


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

    def test_scope_navigation_updates_breadcrumbs_persists_scope_path_per_view_and_restores_runtime_camera(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        primary_view_id = workspace.active_view_id

        shell_id = self.window.scene.add_node_from_type("core.subnode", x=220.0, y=120.0)
        nested_node_id = self.window.scene.add_node_from_type("core.logger", x=80.0, y=90.0)
        workspace.nodes[nested_node_id].parent_node_id = shell_id
        self.window.scene.refresh_workspace_from_model(workspace_id)
        self.app.processEvents()

        breadcrumbs = self.window.active_scope_breadcrumb_items
        self.assertEqual(len(breadcrumbs), 1)
        self.assertEqual(breadcrumbs[0]["node_id"], "")
        self.assertEqual(self.window.scene.active_scope_path, [])

        self.window.view.set_zoom(1.25)
        self.window.view.centerOn(150.0, -40.0)
        self.assertTrue(self.window.request_open_subnode_scope(shell_id))
        self.app.processEvents()

        self.assertEqual(self.window.scene.active_scope_path, [shell_id])
        self.assertEqual(workspace.views[primary_view_id].scope_path, [shell_id])
        scoped_nodes = {item["node_id"] for item in self.window.scene.nodes_model}
        self.assertIn(nested_node_id, scoped_nodes)
        self.assertNotIn(shell_id, scoped_nodes)

        self.window.view.set_zoom(0.65)
        self.window.view.centerOn(880.0, 460.0)
        self.assertTrue(self.window.request_open_scope_breadcrumb(""))
        self.app.processEvents()

        self.assertEqual(self.window.scene.active_scope_path, [])
        self.assertEqual(workspace.views[primary_view_id].scope_path, [])
        self.assertAlmostEqual(self.window.view.zoom, 1.25, places=2)
        self.assertAlmostEqual(self.window.view.center_x, 150.0, delta=5.0)
        self.assertAlmostEqual(self.window.view.center_y, -40.0, delta=5.0)

        self.assertTrue(self.window.request_open_subnode_scope(shell_id))
        self.app.processEvents()
        self.assertEqual(self.window.scene.active_scope_path, [shell_id])
        self.assertAlmostEqual(self.window.view.zoom, 0.65, places=2)
        self.assertAlmostEqual(self.window.view.center_x, 880.0, delta=5.0)
        self.assertAlmostEqual(self.window.view.center_y, 460.0, delta=5.0)

        secondary_view_id = self.window.workspace_manager.create_view(workspace_id, name="V2")
        self.window.workspace_manager.set_active_view(workspace_id, primary_view_id)
        self.window.request_switch_view(secondary_view_id)
        self.app.processEvents()
        self.assertEqual(self.window.scene.active_scope_path, [])
        self.assertEqual(workspace.views[secondary_view_id].scope_path, [])

        self.window.request_switch_view(primary_view_id)
        self.app.processEvents()
        self.assertEqual(self.window.scene.active_scope_path, [shell_id])
        self.assertEqual(workspace.views[primary_view_id].scope_path, [shell_id])

    def test_qml_create_view_updates_active_view_items_and_allows_switching(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        initial_view_count = len(workspace.views)
        original_active_view_id = workspace.active_view_id

        with patch("PyQt6.QtWidgets.QInputDialog.getText", return_value=("Inspection", True)):
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
