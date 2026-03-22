from __future__ import annotations

from unittest.mock import patch

from tests.main_window_shell.base import *  # noqa: F401,F403

COMMENT_BACKDROP_TYPE_ID = "passive.annotation.comment_backdrop"


def _selected_node_ids(window: ShellWindow) -> set[str]:
    return set(window.scene.selected_node_lookup)


def _scene_payload(window: ShellWindow, node_id: str) -> dict[str, object]:
    for payload in [*window.scene.nodes_model, *window.scene.backdrop_nodes_model]:
        if str(payload.get("node_id", "")) == str(node_id):
            return payload
    raise AssertionError(f"Node payload {node_id!r} was not found.")


class MainWindowShellEditClipboardHistoryTests(SharedMainWindowShellTestBase):
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

    def test_qml_request_rename_node_updates_title_for_scoped_and_collapsed_nodes(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        scoped_node_id = self.window.scene.add_node_from_type("core.subnode", x=40.0, y=40.0)
        collapsed_node_id = self.window.scene.add_node_from_type("core.logger", x=280.0, y=40.0)
        self.window.scene.set_node_collapsed(collapsed_node_id, True)
        self.app.processEvents()

        with patch(
            "PyQt6.QtWidgets.QInputDialog.getText",
            side_effect=[("Scoped Shell", True), ("Collapsed Logger", True)],
        ):
            scoped_renamed = self.window.request_rename_node(scoped_node_id)
            collapsed_renamed = self.window.request_rename_node(collapsed_node_id)

        self.assertTrue(scoped_renamed)
        self.assertTrue(collapsed_renamed)
        workspace = self.window.model.project.workspaces[workspace_id]
        self.assertEqual(workspace.nodes[scoped_node_id].title, "Scoped Shell")
        self.assertEqual(workspace.nodes[collapsed_node_id].title, "Collapsed Logger")

    def test_qml_request_rename_selected_port_updates_subnode_pin_label(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        shell_id = self.window.scene.add_node_from_type("core.subnode", x=120.0, y=80.0)
        self.window.scene.focus_node(shell_id)
        self.app.processEvents()

        port_node_id = self.window.request_add_selected_subnode_pin("out")
        self.assertTrue(port_node_id)

        with patch("PyQt6.QtWidgets.QInputDialog.getText", return_value=("Renamed Port", True)):
            renamed = self.window.request_rename_selected_port(port_node_id)

        self.assertTrue(renamed)
        workspace = self.window.model.project.workspaces[workspace_id]
        self.assertEqual(workspace.nodes[port_node_id].properties["label"], "Renamed Port")
        port_items = {item["key"]: item for item in self.window.selected_node_port_items}
        self.assertIn(port_node_id, port_items)
        self.assertEqual(port_items[port_node_id]["label"], "Renamed Port")

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

        selected_duplicate_ids = _selected_node_ids(self.window)
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

    def test_qml_request_group_and_ungroup_selected_nodes_are_single_undoable_actions(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        source_id = self.window.scene.add_node_from_type("core.start", x=20.0, y=40.0)
        grouped_logger_id = self.window.scene.add_node_from_type("core.logger", x=320.0, y=60.0)
        grouped_constant_id = self.window.scene.add_node_from_type("core.constant", x=220.0, y=190.0)
        target_id = self.window.scene.add_node_from_type("core.end", x=640.0, y=90.0)
        external_script_id = self.window.scene.add_node_from_type("core.python_script", x=700.0, y=230.0)
        self.window.scene.add_edge(source_id, "exec_out", grouped_logger_id, "exec_in")
        self.window.scene.add_edge(grouped_constant_id, "as_text", grouped_logger_id, "message")
        self.window.scene.add_edge(grouped_logger_id, "exec_out", target_id, "exec_in")
        self.window.scene.add_edge(grouped_constant_id, "value", external_script_id, "payload")
        self.app.processEvents()
        workspace = self.window.model.project.workspaces[workspace_id]
        initial_edge_signature = {
            (edge.source_node_id, edge.source_port_key, edge.target_node_id, edge.target_port_key)
            for edge in workspace.edges.values()
        }

        self.window.scene.select_node(grouped_logger_id, False)
        self.window.scene.select_node(grouped_constant_id, True)
        initial_state = self._workspace_state()
        self.window.runtime_history.clear_workspace(workspace_id)

        grouped = self.window.request_group_selected_nodes()
        self.assertTrue(grouped)
        grouped_state = self._workspace_state()
        self.assertNotEqual(grouped_state, initial_state)
        self.assertEqual(self.window.runtime_history.undo_depth(workspace_id), 1)

        self.window.action_undo.trigger()
        self.app.processEvents()
        self.assertEqual(self._workspace_state(), initial_state)

        self.window.action_redo.trigger()
        self.app.processEvents()
        self.assertEqual(self._workspace_state(), grouped_state)

        workspace = self.window.model.project.workspaces[workspace_id]
        shell_ids = [
            node_id
            for node_id, node in workspace.nodes.items()
            if node.type_id == "core.subnode" and node.parent_node_id is None
        ]
        self.assertEqual(len(shell_ids), 1)
        shell_id = shell_ids[0]

        self.window.scene.select_node(shell_id, False)
        self.window.runtime_history.clear_workspace(workspace_id)
        ungrouped = self.window.request_ungroup_selected_nodes()
        self.assertTrue(ungrouped)
        ungrouped_edge_signature = {
            (edge.source_node_id, edge.source_port_key, edge.target_node_id, edge.target_port_key)
            for edge in workspace.edges.values()
        }
        self.assertEqual(ungrouped_edge_signature, initial_edge_signature)
        self.assertEqual(workspace.nodes[grouped_logger_id].parent_node_id, None)
        self.assertEqual(workspace.nodes[grouped_constant_id].parent_node_id, None)
        remaining_subnode_types = {
            node.type_id for node in workspace.nodes.values() if node.type_id.startswith("core.subnode")
        }
        self.assertEqual(remaining_subnode_types, set())
        self.assertEqual(self.window.runtime_history.undo_depth(workspace_id), 1)

        self.window.action_undo.trigger()
        self.app.processEvents()
        self.assertEqual(self._workspace_state(), grouped_state)

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

        original_selection_bounds = self.window.scene.selection_bounds()
        self.assertIsNotNone(original_selection_bounds)
        original_center = original_selection_bounds.center()

        copied = self.window.request_copy_selected_nodes()
        self.assertTrue(copied)
        pasted = self.window.request_paste_selected_nodes()
        self.assertTrue(pasted)
        self.app.processEvents()

        workspace = self.window.model.project.workspaces[workspace_id]
        self.assertEqual(len(workspace.nodes), before_nodes + 2)
        self.assertEqual(len(workspace.edges), before_edges + 1)

        pasted_node_ids = _selected_node_ids(self.window)
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
        self.assertAlmostEqual(selection_bounds.center().x(), original_center.x() + 40.0, places=5)
        self.assertAlmostEqual(selection_bounds.center().y(), original_center.y() + 40.0, places=5)

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
        selected_pasted_ids = _selected_node_ids(self.window)
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

        original_bounds = self.window.scene.selection_bounds()
        self.assertIsNotNone(original_bounds)
        original_center = original_bounds.center()

        self.assertTrue(self.window.request_copy_selected_nodes())

        self.assertTrue(self.window.request_paste_selected_nodes())
        self.app.processEvents()
        first_bounds = self.window.scene.selection_bounds()
        self.assertIsNotNone(first_bounds)

        self.assertTrue(self.window.request_paste_selected_nodes())
        self.app.processEvents()
        second_bounds = self.window.scene.selection_bounds()
        self.assertIsNotNone(second_bounds)

        self.assertAlmostEqual(first_bounds.center().x(), original_center.x() + 40.0, places=5)
        self.assertAlmostEqual(first_bounds.center().y(), original_center.y() + 40.0, places=5)
        self.assertAlmostEqual(second_bounds.center().x(), original_center.x() + 80.0, places=5)
        self.assertAlmostEqual(second_bounds.center().y(), original_center.y() + 80.0, places=5)

    def test_comment_backdrop_copy_and_paste_for_expanded_backdrop_keeps_descendants_explicit_only(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        logger_id = self.window.scene.add_node_from_type("core.logger", x=110.0, y=110.0)
        backdrop_id = self.window.scene.wrap_node_ids_in_comment_backdrop([logger_id])
        self.assertTrue(backdrop_id)
        self.window.scene.set_node_collapsed(backdrop_id, False)
        self.app.processEvents()

        workspace = self.window.model.project.workspaces[workspace_id]
        before_nodes = len(workspace.nodes)
        before_backdrops = len(
            [node for node in workspace.nodes.values() if node.type_id == COMMENT_BACKDROP_TYPE_ID]
        )

        self.window.scene.select_node(backdrop_id, False)
        self.assertTrue(self.window.request_copy_selected_nodes())
        self.assertTrue(self.window.request_paste_selected_nodes())
        self.app.processEvents()

        workspace = self.window.model.project.workspaces[workspace_id]
        self.assertEqual(len(workspace.nodes), before_nodes + 1)
        self.assertEqual(
            len([node for node in workspace.nodes.values() if node.type_id == COMMENT_BACKDROP_TYPE_ID]),
            before_backdrops + 1,
        )
        self.assertEqual(len([node for node in workspace.nodes.values() if node.type_id == "core.logger"]), 1)

        selected_pasted_ids = _selected_node_ids(self.window)
        self.assertEqual(len(selected_pasted_ids), 1)
        pasted_backdrop_id = next(iter(selected_pasted_ids))
        self.assertNotEqual(pasted_backdrop_id, backdrop_id)
        self.assertEqual(workspace.nodes[pasted_backdrop_id].type_id, COMMENT_BACKDROP_TYPE_ID)
        self.assertEqual(_scene_payload(self.window, pasted_backdrop_id)["member_node_ids"], [])

    def test_comment_backdrop_copy_and_paste_for_collapsed_backdrop_includes_descendants_and_internal_edges(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        start_id = self.window.scene.add_node_from_type("core.start", x=220.0, y=160.0)
        end_id = self.window.scene.add_node_from_type("core.end", x=220.0, y=360.0)
        outside_script_id = self.window.scene.add_node_from_type("core.python_script", x=760.0, y=240.0)
        self.window.scene.add_edge(start_id, "exec_out", end_id, "exec_in")
        self.window.scene.add_edge(start_id, "trigger", outside_script_id, "payload")
        backdrop_id = self.window.scene.wrap_node_ids_in_comment_backdrop([start_id, end_id])
        self.assertTrue(backdrop_id)
        self.window.scene.set_node_collapsed(backdrop_id, True)
        self.app.processEvents()

        workspace = self.window.model.project.workspaces[workspace_id]
        before_nodes = len(workspace.nodes)
        before_edges = len(workspace.edges)

        self.window.scene.select_node(backdrop_id, False)
        self.assertTrue(self.window.request_copy_selected_nodes())
        self.assertTrue(self.window.request_paste_selected_nodes())
        self.app.processEvents()

        workspace = self.window.model.project.workspaces[workspace_id]
        self.assertEqual(len(workspace.nodes), before_nodes + 3)
        self.assertEqual(len(workspace.edges), before_edges + 1)

        selected_pasted_ids = _selected_node_ids(self.window)
        self.assertEqual(len(selected_pasted_ids), 3)
        pasted_backdrop_id = next(
            node_id for node_id in selected_pasted_ids if workspace.nodes[node_id].type_id == COMMENT_BACKDROP_TYPE_ID
        )
        pasted_start_id = next(
            node_id for node_id in selected_pasted_ids if workspace.nodes[node_id].type_id == "core.start"
        )
        pasted_end_id = next(
            node_id for node_id in selected_pasted_ids if workspace.nodes[node_id].type_id == "core.end"
        )
        self.assertAlmostEqual(workspace.nodes[pasted_backdrop_id].x, workspace.nodes[backdrop_id].x + 40.0, places=6)
        self.assertAlmostEqual(workspace.nodes[pasted_end_id].x, workspace.nodes[end_id].x + 40.0, places=6)
        self.window.scene.set_node_collapsed(pasted_backdrop_id, False)
        self.app.processEvents()
        self.assertEqual(_scene_payload(self.window, pasted_end_id)["owner_backdrop_id"], pasted_backdrop_id)

        duplicated_internal_edges = [
            edge
            for edge in workspace.edges.values()
            if edge.source_node_id == pasted_start_id
            and edge.source_port_key == "exec_out"
            and edge.target_node_id == pasted_end_id
            and edge.target_port_key == "exec_in"
        ]
        self.assertEqual(len(duplicated_internal_edges), 1)
        duplicated_boundary_edges = [
            edge
            for edge in workspace.edges.values()
            if edge.source_node_id == pasted_start_id and edge.source_port_key == "trigger"
        ]
        self.assertEqual(duplicated_boundary_edges, [])

    def test_comment_backdrop_delete_respects_expanded_and_collapsed_semantics(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        expanded_logger_id = self.window.scene.add_node_from_type("core.logger", x=110.0, y=110.0)
        expanded_backdrop_id = self.window.scene.wrap_node_ids_in_comment_backdrop([expanded_logger_id])
        self.assertTrue(expanded_backdrop_id)
        self.window.scene.set_node_collapsed(expanded_backdrop_id, False)

        collapsed_start_id = self.window.scene.add_node_from_type("core.start", x=220.0, y=160.0)
        collapsed_end_id = self.window.scene.add_node_from_type("core.end", x=220.0, y=360.0)
        self.window.scene.add_edge(collapsed_start_id, "exec_out", collapsed_end_id, "exec_in")
        collapsed_backdrop_id = self.window.scene.wrap_node_ids_in_comment_backdrop([collapsed_start_id, collapsed_end_id])
        self.assertTrue(collapsed_backdrop_id)
        self.window.scene.set_node_collapsed(collapsed_backdrop_id, True)
        self.app.processEvents()

        workspace = self.window.model.project.workspaces[workspace_id]

        self.window.scene.select_node(expanded_backdrop_id, False)
        self.assertTrue(self.window.request_delete_selected_graph_items([]))
        self.app.processEvents()
        self.assertNotIn(expanded_backdrop_id, workspace.nodes)
        self.assertIn(expanded_logger_id, workspace.nodes)

        self.window.scene.select_node(collapsed_backdrop_id, False)
        self.assertTrue(self.window.request_delete_selected_graph_items([]))
        self.app.processEvents()
        for removed_node_id in (collapsed_backdrop_id, collapsed_start_id, collapsed_end_id):
            self.assertNotIn(removed_node_id, workspace.nodes)

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
