from __future__ import annotations

from tests.main_window_shell.base import *  # noqa: F401,F403


class MainWindowShellViewLibraryInspectorTests(MainWindowShellTestBase):
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

    def test_qml_subnode_library_category_contains_pin_nodes(self) -> None:
        self.window.set_library_query("")
        self.window.set_library_category("Subnode")
        self.window.set_library_direction("")
        self.window.set_library_data_type("")
        self.app.processEvents()

        library_items = {
            item["type_id"]: item
            for item in self.window.filtered_node_library_items
        }
        self.assertIn("core.subnode_input", library_items)
        self.assertIn("core.subnode_output", library_items)
        self.assertEqual(library_items["core.subnode_input"]["category"], "Subnode")
        self.assertEqual(library_items["core.subnode_output"]["category"], "Subnode")
        pin_types = self.window.pin_data_type_options
        self.assertIn("any", pin_types)
        self.assertIn("json", pin_types)
        self.assertIn("str", pin_types)

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

    def test_qml_pin_inspector_updates_parent_shell_ports(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        custom_data_type = "pressure_tensor"

        shell_id = self.window.scene.add_node_from_type("core.subnode", x=220.0, y=120.0)
        self.assertTrue(self.window.request_open_subnode_scope(shell_id))
        pin_id = self.window.scene.add_node_from_type("core.subnode_input", x=40.0, y=40.0)
        self.window.scene.focus_node(pin_id)
        self.app.processEvents()

        self.assertTrue(self.window.selected_node_is_subnode_pin)
        self.assertEqual(
            [item["key"] for item in self.window.selected_node_property_items],
            ["label", "kind", "data_type"],
        )
        self.assertEqual(self.window.selected_node_port_items, [])

        self.window.set_selected_node_property("label", "Payload In")
        self.window.set_selected_node_property("kind", "data")
        self.window.set_selected_node_property("data_type", custom_data_type)
        self.app.processEvents()

        self.assertTrue(self.window.request_navigate_scope_parent())
        self.window.scene.focus_node(shell_id)
        self.app.processEvents()

        shell_payload = next(item for item in self.window.scene.nodes_model if item["node_id"] == shell_id)
        shell_ports = {port["key"]: port for port in shell_payload["ports"]}
        self.assertIn(pin_id, shell_ports)
        self.assertEqual(shell_ports[pin_id]["label"], "Payload In")
        self.assertEqual(shell_ports[pin_id]["kind"], "data")
        self.assertEqual(shell_ports[pin_id]["data_type"], custom_data_type)

        shell_port_items = {item["key"]: item for item in self.window.selected_node_port_items}
        self.assertIn(pin_id, shell_port_items)
        self.assertEqual(shell_port_items[pin_id]["label"], "Payload In")
        self.assertEqual(workspace.nodes[pin_id].parent_node_id, shell_id)
        self.assertIn(custom_data_type, self.window.pin_data_type_options)

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
