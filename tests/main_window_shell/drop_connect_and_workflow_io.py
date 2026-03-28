from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from tests.main_window_shell.base import *  # noqa: F401,F403
from tests.main_window_shell.base import _action_shortcuts


class MainWindowShellDropConnectAndWorkflowIOTests(SharedMainWindowShellTestBase):
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
        self.assertEqual(self.window.project_display_name, "COREX Node Editor - untitled.sfe")
        self.assertEqual(len(self.window.model.project.workspaces), 1)
        active_workspace_id = self.window.workspace_manager.active_workspace_id()
        active_workspace = self.window.model.project.workspaces[active_workspace_id]
        self.assertEqual(active_workspace.nodes, {})
        self.assertEqual(active_workspace.edges, {})
        self.assertFalse(active_workspace.dirty)

    def test_recent_files_menu_tracks_saved_projects_and_restores_from_session(self) -> None:
        alpha_path = Path(self._temp_dir.name) / "projects" / "alpha_project.sfe"
        alpha_path.parent.mkdir(parents=True, exist_ok=True)

        self.window.project_path = str(alpha_path)
        self.window._save_project()
        self.app.processEvents()

        self.assertEqual(self.window.recent_project_paths, [str(alpha_path)])
        recent_actions = [action for action in self.window.menu_recent_projects.actions() if not action.isSeparator()]
        self.assertEqual(recent_actions[0].text(), f"1. alpha_project.sfe [{alpha_path.parent}]")
        self.assertFalse(recent_actions[0].isEnabled())
        self.assertEqual(recent_actions[-1].text(), "Clear Recent Files")

        session_payload = json.loads(self._session_path.read_text(encoding="utf-8"))
        self.assertEqual(session_payload["recent_project_paths"], [str(alpha_path)])

        self._reopen_shared_window()
        restored = self.window
        self.assertEqual(restored.recent_project_paths, [str(alpha_path)])
        restored_actions = [action for action in restored.menu_recent_projects.actions() if not action.isSeparator()]
        self.assertEqual(restored_actions[0].text(), f"1. alpha_project.sfe [{alpha_path.parent}]")
        self.assertFalse(restored_actions[0].isEnabled())

    def test_recent_files_menu_action_opens_selected_project(self) -> None:
        alpha_path = Path(self._temp_dir.name) / "alpha_project.sfe"
        beta_path = Path(self._temp_dir.name) / "beta_project.sfe"

        alpha_node_id = self.window.scene.add_node_from_type("core.start", x=40.0, y=40.0)
        self.window.project_path = str(alpha_path)
        self.window._save_project()
        self.app.processEvents()

        self.window._new_project()
        beta_node_id = self.window.scene.add_node_from_type("core.logger", x=160.0, y=40.0)
        self.window.project_path = str(beta_path)
        self.window._save_project()
        self.app.processEvents()

        recent_actions = [action for action in self.window.menu_recent_projects.actions() if not action.isSeparator()]
        self.assertEqual(self.window.recent_project_paths, [str(beta_path), str(alpha_path)])
        self.assertFalse(recent_actions[0].isEnabled())
        recent_actions[1].trigger()
        self.app.processEvents()

        self.assertEqual(self.window.project_path, str(alpha_path))
        self.assertEqual(self.window.recent_project_paths, [str(alpha_path), str(beta_path)])
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        self.assertIn(alpha_node_id, workspace.nodes)
        self.assertNotIn(beta_node_id, workspace.nodes)

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

    def test_qml_connect_ports_rejects_same_node_logic_flow_edge(self) -> None:
        node_id = self.window.scene.add_node_from_type("core.logger", x=40.0, y=40.0)
        self.app.processEvents()

        created = self.window.request_connect_ports(node_id, "exec_out", node_id, "exec_in")
        self.assertFalse(created)

    def test_qml_connect_ports_rejects_exec_to_data_kind_mismatch(self) -> None:
        source_id = self.window.scene.add_node_from_type("core.start", x=40.0, y=40.0)
        target_id = self.window.scene.add_node_from_type("core.logger", x=280.0, y=40.0)
        self.app.processEvents()

        created = self.window.request_connect_ports(source_id, "exec_out", target_id, "message")
        self.assertFalse(created)

    def test_qml_connect_ports_surfaces_graph_hint_for_mutually_exclusive_dpf_inputs(self) -> None:
        result_file_id = self.window.scene.add_node_from_type("dpf.result_file", x=40.0, y=40.0)
        model_id = self.window.scene.add_node_from_type("dpf.model", x=280.0, y=40.0)
        self.app.processEvents()

        self.assertTrue(self.window.request_connect_ports(result_file_id, "result_file", model_id, "result_file"))
        self.window.clear_graph_hint()
        self.app.processEvents()

        created = self.window.request_connect_ports(result_file_id, "normalized_path", model_id, "path")
        self.assertFalse(created)
        self.assertTrue(self.window.graph_hint_visible)
        self.assertEqual(self.window.graph_hint_message, "Can't connect path while result_file is active.")

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

    def test_qml_connection_quick_insert_filters_results_and_accepts_choice(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        source_id = self.window.scene.add_node_from_type("core.start", x=60.0, y=40.0)
        self.app.processEvents()

        opened = self.window.request_open_connection_quick_insert(
            source_id,
            "exec_out",
            220.0,
            80.0,
            340.0,
            180.0,
        )
        self.assertTrue(opened)
        self.assertTrue(self.window.connection_quick_insert_open)
        self.assertGreater(len(self.window.connection_quick_insert_results), 0)

        self.window.set_connection_quick_insert_query("end")
        self.app.processEvents()

        results = self.window.connection_quick_insert_results
        self.assertTrue(results)
        self.assertTrue(all("end" in str(item["display_name"]).lower() for item in results))

        chosen_index = next(
            index
            for index, item in enumerate(results)
            if item.get("type_id") == "core.end"
        )
        created = self.window.request_connection_quick_insert_choose(chosen_index)
        self.assertTrue(created)
        self.app.processEvents()

        workspace = self.window.model.project.workspaces[workspace_id]
        self.assertFalse(self.window.connection_quick_insert_open)
        self.assertEqual(len(workspace.edges), 1)
        edge = next(iter(workspace.edges.values()))
        self.assertEqual(edge.source_node_id, source_id)
        self.assertEqual(edge.source_port_key, "exec_out")
        new_node_id = self.window.scene.selected_node_id()
        self.assertTrue(new_node_id)
        self.assertEqual(edge.target_node_id, new_node_id)
        self.assertEqual(edge.target_port_key, "exec_in")

    def test_qml_connection_quick_insert_rejects_already_connected_input(self) -> None:
        source_id = self.window.scene.add_node_from_type("core.start", x=40.0, y=40.0)
        target_id = self.window.scene.add_node_from_type("core.end", x=320.0, y=40.0)
        self.window.scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        self.app.processEvents()

        opened = self.window.request_open_connection_quick_insert(
            target_id,
            "exec_in",
            220.0,
            40.0,
            240.0,
            140.0,
        )
        self.assertFalse(opened)
        self.assertFalse(self.window.connection_quick_insert_open)
        self.assertEqual(self.window.connection_quick_insert_results, [])

    def test_qml_custom_workflow_publish_appears_in_library_and_places_independent_snapshots(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        source_shell_id, _source_pin_id = self._create_publishable_subnode(
            shell_title="Reusable Scope",
            output_label="Exec A",
        )

        published = self.window.request_publish_custom_workflow_from_selected()
        self.assertTrue(published)
        self.app.processEvents()

        self.window.set_library_query("")
        self.window.set_library_category("Custom Workflows")
        self.window.set_library_direction("")
        self.window.set_library_data_type("")
        self.app.processEvents()

        custom_items = [
            item
            for item in self.window.filtered_node_library_items
            if item.get("category") == "Custom Workflows"
        ]
        self.assertEqual(len(custom_items), 1)
        custom_item = custom_items[0]
        self.assertTrue(str(custom_item["type_id"]).startswith("custom_workflow:"))
        self.assertEqual(custom_item["ports"][0]["kind"], "exec")

        def _inserted_root_shell(inserted_ids: set[str]) -> str:
            for node_id in sorted(inserted_ids):
                node = workspace.nodes[node_id]
                if node.type_id != "core.subnode":
                    continue
                if node.parent_node_id in inserted_ids:
                    continue
                return node_id
            return ""

        baseline_node_ids = set(workspace.nodes)
        placed_once = self.window.request_drop_node_from_library(
            custom_item["type_id"],
            560.0,
            180.0,
            "",
            "",
            "",
            "",
        )
        self.assertTrue(placed_once)
        self.app.processEvents()
        after_first_ids = set(workspace.nodes)
        first_inserted_ids = after_first_ids.difference(baseline_node_ids)
        self.assertTrue(first_inserted_ids)
        first_shell_id = _inserted_root_shell(first_inserted_ids)
        self.assertTrue(first_shell_id)

        placed_twice = self.window.request_drop_node_from_library(
            custom_item["type_id"],
            820.0,
            240.0,
            "",
            "",
            "",
            "",
        )
        self.assertTrue(placed_twice)
        self.app.processEvents()
        after_second_ids = set(workspace.nodes)
        second_inserted_ids = after_second_ids.difference(after_first_ids)
        self.assertTrue(second_inserted_ids)
        self.assertTrue(first_inserted_ids.isdisjoint(second_inserted_ids))
        second_shell_id = _inserted_root_shell(second_inserted_ids)
        self.assertTrue(second_shell_id)

        def _output_pin_label(shell_id: str) -> str:
            output_pins = [
                node
                for node in workspace.nodes.values()
                if node.parent_node_id == shell_id and node.type_id == "core.subnode_output"
            ]
            self.assertEqual(len(output_pins), 1)
            return str(output_pins[0].properties.get("label", ""))

        self.assertEqual(_output_pin_label(first_shell_id), "Exec A")
        self.assertEqual(_output_pin_label(second_shell_id), "Exec A")
        self.assertNotEqual(first_shell_id, source_shell_id)
        self.assertNotEqual(second_shell_id, source_shell_id)

    def test_qml_delete_custom_workflow_removes_item_from_library_and_metadata(self) -> None:
        source_shell_id, _source_pin_id = self._create_publishable_subnode(
            shell_title="Delete Target",
            output_label="Exec Out",
        )
        self.window.scene.focus_node(source_shell_id)
        self.assertTrue(self.window.request_publish_custom_workflow_from_selected())
        self.app.processEvents()

        custom_item = next(
            item
            for item in self.window.filtered_node_library_items
            if item.get("category") == "Custom Workflows"
        )
        workflow_id = str(custom_item.get("workflow_id", ""))
        self.assertTrue(workflow_id)

        deleted = self.window.request_delete_custom_workflow_from_library(workflow_id)
        self.assertTrue(deleted)
        self.app.processEvents()

        self.assertEqual(self.window.model.project.metadata.get("custom_workflows", []), [])
        self.assertFalse(
            [
                item
                for item in self.window.filtered_node_library_items
                if item.get("category") == "Custom Workflows"
            ]
        )

    def test_qml_rename_custom_workflow_updates_library_and_metadata(self) -> None:
        source_shell_id, _source_pin_id = self._create_publishable_subnode(
            shell_title="Rename Target",
            output_label="Exec Out",
        )
        self.window.scene.focus_node(source_shell_id)
        self.assertTrue(self.window.request_publish_custom_workflow_from_selected())
        self.app.processEvents()

        custom_item = next(
            item
            for item in self.window.filtered_node_library_items
            if item.get("category") == "Custom Workflows" and item.get("display_name") == "Rename Target"
        )
        workflow_id = str(custom_item.get("workflow_id", ""))
        self.assertTrue(workflow_id)

        with patch("PyQt6.QtWidgets.QInputDialog.getText", return_value=("Renamed Workflow", True)):
            renamed = self.window.request_rename_custom_workflow_from_library(workflow_id)
        self.assertTrue(renamed)
        self.app.processEvents()

        definitions = self.window.model.project.metadata.get("custom_workflows", [])
        self.assertEqual(len(definitions), 1)
        self.assertEqual(definitions[0]["name"], "Renamed Workflow")
        self.assertEqual(definitions[0]["revision"], 1)

        updated_item = next(
            item
            for item in self.window.filtered_node_library_items
            if item.get("category") == "Custom Workflows" and item.get("workflow_id") == workflow_id
        )
        self.assertEqual(updated_item.get("display_name"), "Renamed Workflow")

    def test_qml_set_custom_workflow_scope_moves_local_item_to_global(self) -> None:
        source_shell_id, _source_pin_id = self._create_publishable_subnode(
            shell_title="Scope Switch",
            output_label="Exec Out",
        )
        self.window.scene.focus_node(source_shell_id)
        self.assertTrue(self.window.request_publish_custom_workflow_from_selected())
        self.app.processEvents()

        custom_item = next(
            item
            for item in self.window.filtered_node_library_items
            if item.get("category") == "Custom Workflows" and item.get("display_name") == "Scope Switch"
        )
        workflow_id = str(custom_item.get("workflow_id", ""))
        self.assertTrue(workflow_id)
        self.assertEqual(custom_item.get("workflow_scope"), "local")

        switched = self.window.request_set_custom_workflow_scope(workflow_id, "global")
        self.assertTrue(switched)
        self.app.processEvents()
        self.assertEqual(self.window.model.project.metadata.get("custom_workflows", []), [])

        updated_item = next(
            item
            for item in self.window.filtered_node_library_items
            if item.get("category") == "Custom Workflows" and item.get("workflow_id") == workflow_id
        )
        self.assertEqual(updated_item.get("workflow_scope"), "global")

    def test_qml_custom_workflow_export_import_round_trip_preserves_snapshot_fidelity(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        source_shell_id, _source_pin_id = self._create_publishable_subnode(
            shell_title="Exportable Scope",
            output_label="Exec Export",
        )
        self.window.scene.focus_node(source_shell_id)
        self.assertTrue(self.window.request_publish_custom_workflow_from_selected())
        self.app.processEvents()

        definitions = self.window.model.project.metadata.get("custom_workflows", [])
        self.assertEqual(len(definitions), 1)
        original_definition = copy.deepcopy(definitions[0])

        with tempfile.TemporaryDirectory() as temp_dir:
            export_target = Path(temp_dir) / "exported_custom_workflow"
            self.window.workspace_library_controller._prompt_custom_workflow_export_definition = (  # type: ignore[method-assign]
                lambda definitions: definitions[0]
            )
            with (
                patch(
                    "PyQt6.QtWidgets.QFileDialog.getSaveFileName",
                    return_value=(str(export_target), "Custom Workflow (*.eawf)"),
                ),
                patch("PyQt6.QtWidgets.QMessageBox.information"),
                patch("PyQt6.QtWidgets.QMessageBox.warning"),
            ):
                self.window._export_custom_workflow()
            self.app.processEvents()

            export_path = export_target.with_suffix(".eawf")
            self.assertTrue(export_path.exists())
            self.assertEqual(import_custom_workflow_file(export_path), original_definition)

            self.window.model.project.metadata["custom_workflows"] = []
            self.window.project_meta_changed.emit()
            self.window.node_library_changed.emit()
            self.app.processEvents()
            self.assertFalse(
                [
                    item
                    for item in self.window.filtered_node_library_items
                    if item.get("category") == "Custom Workflows"
                ]
            )

            with (
                patch(
                    "PyQt6.QtWidgets.QFileDialog.getOpenFileName",
                    return_value=(str(export_path), "Custom Workflow (*.eawf)"),
                ),
                patch("PyQt6.QtWidgets.QMessageBox.information"),
                patch("PyQt6.QtWidgets.QMessageBox.warning"),
            ):
                self.window._import_custom_workflow()
            self.app.processEvents()

        imported_definitions = self.window.model.project.metadata.get("custom_workflows", [])
        self.assertEqual(imported_definitions, [original_definition])

        custom_item = next(
            item
            for item in self.window.filtered_node_library_items
            if item.get("category") == "Custom Workflows"
        )
        existing_ids = set(workspace.nodes)
        self.assertTrue(
            self.window.request_drop_node_from_library(
                custom_item["type_id"],
                780.0,
                260.0,
                "",
                "",
                "",
                "",
            )
        )
        self.app.processEvents()

        inserted_ids = set(workspace.nodes).difference(existing_ids)
        inserted_shell_id = next(
            node_id
            for node_id in sorted(inserted_ids)
            if workspace.nodes[node_id].type_id == "core.subnode"
            and workspace.nodes[node_id].parent_node_id not in inserted_ids
        )
        inserted_output = next(
            node
            for node in workspace.nodes.values()
            if node.parent_node_id == inserted_shell_id and node.type_id == "core.subnode_output"
        )
        self.assertEqual(str(inserted_output.properties.get("label", "")), "Exec Export")

    def test_qml_install_project_emits_library_refresh_for_restored_custom_workflows(self) -> None:
        source_shell_id, _source_pin_id = self._create_publishable_subnode(
            shell_title="Restored Custom Workflow",
            output_label="Exec A",
        )
        self.window.scene.focus_node(source_shell_id)
        self.assertTrue(self.window.request_publish_custom_workflow_from_selected())
        self.app.processEvents()

        restored_project = self.window.serializer.from_document(
            self.window.serializer.to_document(self.window.model.project)
        )
        library_changed = {"count": 0}

        def _mark_library_changed() -> None:
            library_changed["count"] += 1

        self.window.node_library_changed.connect(_mark_library_changed)
        self.window.project_session_controller._install_project(restored_project, project_path="restored.sfe")
        self.window.workspace_library_controller.refresh_workspace_tabs()
        self.window.workspace_library_controller.switch_workspace(self.window.workspace_manager.active_workspace_id())
        self.app.processEvents()

        self.assertGreaterEqual(library_changed["count"], 1)

        custom_category_rows = [
            row
            for row in self.window.grouped_node_library_items
            if row.get("kind") == "category" and row.get("category") == "Custom Workflows"
        ]
        self.assertTrue(custom_category_rows)

    def test_qml_library_categories_start_collapsed_on_project_install(self) -> None:
        library_pane = self._library_pane_item()
        self.app.processEvents()

        def _collapsed_map() -> dict[str, bool]:
            raw_value = library_pane.property("collapsedCategories")
            if hasattr(raw_value, "toVariant"):
                raw_value = raw_value.toVariant()
            if not isinstance(raw_value, dict):
                return {}
            return {str(key): bool(value) for key, value in raw_value.items()}

        for category in {
            row["category"] for row in self.window.grouped_node_library_items if row.get("kind") == "category"
        }:
            self.assertTrue(_collapsed_map().get(category, False))

        library_pane.setProperty("collapsedCategories", {"Flow Control": False, "Custom Workflows": False})
        self.app.processEvents()

        source_shell_id, _source_pin_id = self._create_publishable_subnode(
            shell_title="Collapsed Restore Workflow",
            output_label="Exec A",
        )
        self.window.scene.focus_node(source_shell_id)
        self.assertTrue(self.window.request_publish_custom_workflow_from_selected())
        self.app.processEvents()

        restored_project = self.window.serializer.from_document(
            self.window.serializer.to_document(self.window.model.project)
        )
        self.window.project_session_controller._install_project(restored_project, project_path="collapsed-reset.sfe")
        self.window.workspace_library_controller.refresh_workspace_tabs()
        self.window.workspace_library_controller.switch_workspace(self.window.workspace_manager.active_workspace_id())
        self.app.processEvents()

        collapsed_categories = _collapsed_map()
        restored_categories = {
            row["category"] for row in self.window.grouped_node_library_items if row.get("kind") == "category"
        }
        self.assertIn("Custom Workflows", restored_categories)
        for category in restored_categories:
            self.assertTrue(bool(collapsed_categories.get(category, False)))

    def test_qml_custom_workflow_update_changes_future_placements_only(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        source_shell_id, source_pin_id = self._create_publishable_subnode(
            shell_title="Updatable Scope",
            output_label="Exec A",
        )

        self.assertTrue(self.window.request_publish_custom_workflow_from_selected())
        self.app.processEvents()
        custom_item = next(
            item
            for item in self.window.filtered_node_library_items
            if item.get("category") == "Custom Workflows"
        )

        target_a = self.window.scene.add_node_from_type("core.end", x=940.0, y=40.0)
        baseline_node_ids = set(workspace.nodes)
        placed_first = self.window.request_drop_node_from_library(
            custom_item["type_id"],
            520.0,
            120.0,
            "port",
            target_a,
            "exec_in",
            "",
        )
        self.assertTrue(placed_first)
        self.app.processEvents()
        after_first_ids = set(workspace.nodes)
        first_inserted_ids = after_first_ids.difference(baseline_node_ids)
        first_shell_id = next(
            node_id
            for node_id in sorted(first_inserted_ids)
            if workspace.nodes[node_id].type_id == "core.subnode" and workspace.nodes[node_id].parent_node_id not in first_inserted_ids
        )

        self.assertTrue(self.window.request_open_subnode_scope(source_shell_id))
        self.window.scene.set_node_property(source_pin_id, "label", "Exec B")
        self.assertTrue(self.window.request_navigate_scope_parent())
        self.window.scene.focus_node(source_shell_id)
        self.app.processEvents()

        self.assertTrue(self.window.request_publish_custom_workflow_from_selected())
        self.app.processEvents()

        metadata_definitions = self.window.model.project.metadata.get("custom_workflows", [])
        self.assertEqual(len(metadata_definitions), 1)
        self.assertEqual(metadata_definitions[0]["revision"], 2)

        target_b = self.window.scene.add_node_from_type("core.end", x=980.0, y=220.0)
        placed_second = self.window.request_drop_node_from_library(
            custom_item["type_id"],
            760.0,
            260.0,
            "port",
            target_b,
            "exec_in",
            "",
        )
        self.assertTrue(placed_second)
        self.app.processEvents()
        after_second_ids = set(workspace.nodes)
        second_inserted_ids = after_second_ids.difference(after_first_ids)
        second_shell_id = next(
            node_id
            for node_id in sorted(second_inserted_ids)
            if workspace.nodes[node_id].type_id == "core.subnode" and workspace.nodes[node_id].parent_node_id not in second_inserted_ids
        )

        def _output_pin_label(shell_id: str) -> str:
            output_pin = next(
                node
                for node in workspace.nodes.values()
                if node.parent_node_id == shell_id and node.type_id == "core.subnode_output"
            )
            return str(output_pin.properties.get("label", ""))

        self.assertEqual(_output_pin_label(first_shell_id), "Exec A")
        self.assertEqual(_output_pin_label(second_shell_id), "Exec B")

        first_auto_edge_exists = any(
            edge.source_node_id == first_shell_id
            and edge.target_node_id == target_a
            and edge.target_port_key == "exec_in"
            for edge in workspace.edges.values()
        )
        second_auto_edge_exists = any(
            edge.source_node_id == second_shell_id
            and edge.target_node_id == target_b
            and edge.target_port_key == "exec_in"
            for edge in workspace.edges.values()
        )
        self.assertTrue(first_auto_edge_exists)
        self.assertTrue(second_auto_edge_exists)

    def test_qml_custom_workflow_publish_from_scope_and_reinsert_in_same_scope_preserves_parent_on_reload(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        source_shell_id, _source_pin_id = self._create_publishable_subnode(
            shell_title="Subnode1",
            output_label="Exec A",
        )

        self.assertTrue(self.window.request_open_subnode_scope(source_shell_id))
        self.app.processEvents()
        self.assertEqual(self.window.scene.active_scope_path, [source_shell_id])
        self.assertTrue(self.window.request_publish_custom_workflow_from_scope())
        self.app.processEvents()

        custom_item = next(
            item
            for item in self.window.filtered_node_library_items
            if item.get("category") == "Custom Workflows" and item.get("display_name") == "Subnode1"
        )
        existing_ids = set(workspace.nodes)
        self.assertTrue(
            self.window.request_drop_node_from_library(
                custom_item["type_id"],
                620.0,
                300.0,
                "",
                "",
                "",
                "",
            )
        )
        self.app.processEvents()

        inserted_ids = set(workspace.nodes).difference(existing_ids)
        inserted_shell_id = next(
            node_id
            for node_id in sorted(inserted_ids)
            if workspace.nodes[node_id].type_id == "core.subnode" and node_id != source_shell_id
        )
        self.assertEqual(workspace.nodes[inserted_shell_id].parent_node_id, source_shell_id)
        self.assertNotEqual(workspace.nodes[inserted_shell_id].parent_node_id, inserted_shell_id)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "scope_reinsert_custom_workflow.sfe"
            self.window.serializer.save(str(path), self.window.model.project)
            loaded = self.window.serializer.load(str(path))

        loaded_workspace = loaded.workspaces[workspace_id]
        self.assertIn(inserted_shell_id, loaded_workspace.nodes)
        self.assertEqual(loaded_workspace.nodes[inserted_shell_id].parent_node_id, source_shell_id)

    def test_qml_nested_custom_workflow_drop_opens_without_crash_and_survives_save_load(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        outer_id, _inner_id = self._create_nested_outer_inner_subnodes()

        self.window.scene.focus_node(outer_id)
        self.assertTrue(self.window.request_publish_custom_workflow_from_selected())
        self.app.processEvents()

        custom_item = next(
            item
            for item in self.window.filtered_node_library_items
            if item.get("category") == "Custom Workflows" and item.get("display_name") == "Outer"
        )
        existing_ids = set(workspace.nodes)
        self.assertTrue(
            self.window.request_drop_node_from_library(
                custom_item["type_id"],
                880.0,
                360.0,
                "",
                "",
                "",
                "",
            )
        )
        self.app.processEvents()

        inserted_ids = set(workspace.nodes).difference(existing_ids)
        dropped_outer_id = next(
            node_id
            for node_id in sorted(inserted_ids)
            if workspace.nodes[node_id].type_id == "core.subnode"
            and workspace.nodes[node_id].parent_node_id not in inserted_ids
        )
        self.assertTrue(self.window.request_open_subnode_scope(dropped_outer_id))
        self.app.processEvents()
        self.assertEqual(self.window.scene.active_scope_path, [dropped_outer_id])

        dropped_inner_id = next(
            node_id
            for node_id in inserted_ids
            if workspace.nodes[node_id].type_id == "core.subnode"
            and workspace.nodes[node_id].parent_node_id == dropped_outer_id
        )
        self.assertTrue(self.window.request_open_subnode_scope(dropped_inner_id))
        self.app.processEvents()
        self.assertEqual(self.window.scene.active_scope_path, [dropped_outer_id, dropped_inner_id])

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "nested_custom_workflow.sfe"
            self.window.serializer.save(str(path), self.window.model.project)
            loaded = self.window.serializer.load(str(path))

        loaded_workspace = loaded.workspaces[workspace_id]
        self.assertIn(dropped_outer_id, loaded_workspace.nodes)
        self.assertIn(dropped_inner_id, loaded_workspace.nodes)
        self.assertEqual(loaded_workspace.nodes[dropped_inner_id].parent_node_id, dropped_outer_id)

        loaded_outer_children = {
            node.node_id
            for node in loaded_workspace.nodes.values()
            if node.parent_node_id == dropped_outer_id
        }
        self.assertIn(dropped_inner_id, loaded_outer_children)

        loaded_edge_tuples = {
            (edge.source_node_id, edge.source_port_key, edge.target_node_id, edge.target_port_key)
            for edge in loaded_workspace.edges.values()
        }
        bridging_edges = [
            edge
            for edge in loaded_edge_tuples
            if edge[0] == dropped_inner_id or edge[2] == dropped_inner_id
        ]
        self.assertTrue(bridging_edges)
