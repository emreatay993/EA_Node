from __future__ import annotations

from tests.main_window_shell.base import *  # noqa: F401,F403
from tests.main_window_shell.base import _action_shortcuts


class MainWindowShellBasicsAndSearchTests(MainWindowShellTestBase):
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
        self.assertGreaterEqual(meta.indexOfMethod("request_group_selected_nodes()"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("request_ungroup_selected_nodes()"), 0)
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
        self.assertGreaterEqual(meta.indexOfMethod("request_publish_custom_workflow_from_selected()"), 0)
        self.assertGreaterEqual(meta.indexOfMethod("request_publish_custom_workflow_from_scope()"), 0)

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
        self.assertIn("Ctrl+G", _action_shortcuts(self.window.action_group_selection))
        self.assertIn("Ctrl+Shift+G", _action_shortcuts(self.window.action_ungroup_selection))
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

    def test_graph_search_jump_opens_subnode_scope_for_nested_match(self) -> None:
        source_workspace_id = self.window.workspace_manager.active_workspace_id()
        target_workspace_id = self.window.workspace_manager.create_workspace("Scoped Search Target")
        self.window._refresh_workspace_tabs()
        self.window._switch_workspace(target_workspace_id)

        shell_id = self.window.scene.add_node_from_type("core.subnode", x=260.0, y=150.0)
        nested_node_id = self.window.scene.add_node_from_type("core.logger", x=120.0, y=100.0)
        target_workspace = self.window.model.project.workspaces[target_workspace_id]
        target_workspace.nodes[nested_node_id].parent_node_id = shell_id
        self.window.scene.refresh_workspace_from_model(target_workspace_id)
        self.window.scene.set_node_title(nested_node_id, "Nested Needle Result")
        self.app.processEvents()

        self.window._switch_workspace(source_workspace_id)
        self.window.action_graph_search.trigger()
        self.window.set_graph_search_query("nested needle")
        self.app.processEvents()

        jumped = self.window.request_graph_search_accept()
        self.assertTrue(jumped)
        self.app.processEvents()

        self.assertEqual(self.window.workspace_manager.active_workspace_id(), target_workspace_id)
        self.assertEqual(self.window.scene.active_scope_path, [shell_id])
        self.assertEqual(self.window.scene.selected_node_id(), nested_node_id)
        visible_node_ids = {item["node_id"] for item in self.window.scene.nodes_model}
        self.assertIn(nested_node_id, visible_node_ids)
        self.assertNotIn(shell_id, visible_node_ids)

    def test_failure_focus_opens_scope_for_nested_node(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        shell_id = self.window.scene.add_node_from_type("core.subnode", x=220.0, y=110.0)
        nested_node_id = self.window.scene.add_node_from_type("core.python_script", x=120.0, y=90.0)
        workspace = self.window.model.project.workspaces[workspace_id]
        workspace.nodes[nested_node_id].parent_node_id = shell_id
        self.window.scene.refresh_workspace_from_model(workspace_id)
        self.app.processEvents()

        self.assertEqual(self.window.scene.active_scope_path, [])
        self.window.workspace_library_controller.focus_failed_node(workspace_id, nested_node_id, "")
        self.app.processEvents()

        self.assertEqual(self.window.scene.active_scope_path, [shell_id])
        self.assertEqual(self.window.scene.selected_node_id(), nested_node_id)
        bounds = self.window.scene.selection_bounds()
        self.assertIsNotNone(bounds)
        self.assertAlmostEqual(self.window.view.center_x, bounds.center().x(), places=6)
        self.assertAlmostEqual(self.window.view.center_y, bounds.center().y(), places=6)

    def test_run_failed_event_for_nested_node_opens_scope_and_focuses_inner_node(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        shell_id = self.window.scene.add_node_from_type("core.subnode", x=260.0, y=120.0)
        nested_node_id = self.window.scene.add_node_from_type("core.python_script", x=120.0, y=90.0)
        workspace = self.window.model.project.workspaces[workspace_id]
        workspace.nodes[nested_node_id].parent_node_id = shell_id
        self.window.scene.refresh_workspace_from_model(workspace_id)
        self.app.processEvents()

        self.window._active_run_id = "run_live"
        self.window._active_run_workspace_id = workspace_id
        self.window._set_run_ui_state("running", "Running", 1, 0, 0, 0)

        with patch.object(QMessageBox, "critical") as critical:
            self.window.execution_event.emit(
                {
                    "type": "run_failed",
                    "run_id": "run_live",
                    "workspace_id": workspace_id,
                    "node_id": nested_node_id,
                    "error": "RuntimeError: nested failure",
                    "traceback": "traceback: nested",
                }
            )
            self.app.processEvents()

        self.assertEqual(self.window.scene.active_scope_path, [shell_id])
        self.assertEqual(self.window.scene.selected_node_id(), nested_node_id)
        self.assertEqual(self.window._active_run_id, "")
        critical.assert_called_once()

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
