from __future__ import annotations

import unittest

from ea_node_editor.ui.shell.runtime_history import ACTION_EDIT_EDGE_LABEL, ACTION_GROUP_SELECTED_NODES
from tests.graph_track_b.scene_and_model import ACTION_ADD_NODE, GraphModel, RuntimeGraphHistory, ViewState


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

    def test_history_restores_full_mutable_workspace_state(self) -> None:
        model = GraphModel()
        history = RuntimeGraphHistory()
        workspace = model.active_workspace
        workspace_id = workspace.workspace_id

        shell = model.add_node(workspace_id, "core.subnode", "Shell", 120.0, 80.0)
        child = model.add_node(workspace_id, "core.logger", "Logger", 260.0, 120.0)
        workspace.nodes[child.node_id].parent_node_id = shell.node_id
        before_view = model.create_view(workspace_id, name="Nested Review")
        before_view.zoom = 1.75
        before_view.pan_x = 145.0
        before_view.pan_y = 230.0
        before_view.scope_path = [shell.node_id]
        workspace.active_view_id = before_view.view_id
        workspace.name = "Before State"
        workspace.dirty = True
        workspace.unresolved_node_docs = {
            "ghost_node": {
                "node_id": "ghost_node",
                "type_id": "missing.node",
                "title": "Ghost",
            }
        }
        workspace.unresolved_edge_docs = {
            "ghost_edge": {
                "edge_id": "ghost_edge",
                "source_node_id": child.node_id,
                "source_port_key": "exec_out",
                "target_node_id": "ghost_node",
                "target_port_key": "exec_in",
            }
        }
        workspace.authored_node_overrides = {
            child.node_id: {"parent_node_id": "ghost_node"},
        }

        before = history.capture_workspace(workspace)

        workspace.name = "After State"
        after_node = model.add_node(workspace_id, "core.end", "End", 420.0, 180.0)
        workspace.nodes = {after_node.node_id: after_node}
        workspace.edges = {}
        workspace.views = {
            "view_after": ViewState(
                view_id="view_after",
                name="After View",
                zoom=0.8,
                pan_x=-40.0,
                pan_y=25.0,
                scope_path=[],
            )
        }
        workspace.active_view_id = "view_after"
        workspace.dirty = False
        workspace.unresolved_node_docs = {
            "after_ghost": {
                "node_id": "after_ghost",
                "type_id": "missing.after",
                "title": "After Ghost",
            }
        }
        workspace.unresolved_edge_docs = {}
        workspace.authored_node_overrides = {
            after_node.node_id: {"parent_node_id": "after_ghost"},
        }

        history.record_action(workspace_id, ACTION_ADD_NODE, before, workspace)

        self.assertIsNotNone(history.undo_workspace(workspace_id, workspace))
        self.assertEqual(workspace.name, "Before State")
        self.assertEqual(set(workspace.nodes), {shell.node_id, child.node_id})
        self.assertEqual(workspace.nodes[child.node_id].parent_node_id, shell.node_id)
        self.assertEqual(workspace.active_view_id, before_view.view_id)
        self.assertEqual(len(workspace.views), 2)
        self.assertIn(before_view.view_id, workspace.views)
        self.assertAlmostEqual(workspace.views[before_view.view_id].zoom, 1.75, places=6)
        self.assertAlmostEqual(workspace.views[before_view.view_id].pan_x, 145.0, places=6)
        self.assertAlmostEqual(workspace.views[before_view.view_id].pan_y, 230.0, places=6)
        self.assertEqual(workspace.views[before_view.view_id].scope_path, [shell.node_id])
        self.assertTrue(workspace.dirty)
        self.assertEqual(
            workspace.unresolved_node_docs,
            {
                "ghost_node": {
                    "node_id": "ghost_node",
                    "type_id": "missing.node",
                    "title": "Ghost",
                }
            },
        )
        self.assertEqual(
            workspace.unresolved_edge_docs,
            {
                "ghost_edge": {
                    "edge_id": "ghost_edge",
                    "source_node_id": child.node_id,
                    "source_port_key": "exec_out",
                    "target_node_id": "ghost_node",
                    "target_port_key": "exec_in",
                }
            },
        )
        self.assertEqual(workspace.authored_node_overrides, {child.node_id: {"parent_node_id": "ghost_node"}})

        self.assertIsNotNone(history.redo_workspace(workspace_id, workspace))
        self.assertEqual(workspace.name, "After State")
        self.assertEqual(set(workspace.nodes), {after_node.node_id})
        self.assertEqual(set(workspace.views), {"view_after"})
        self.assertEqual(workspace.active_view_id, "view_after")
        self.assertAlmostEqual(workspace.views["view_after"].zoom, 0.8, places=6)
        self.assertAlmostEqual(workspace.views["view_after"].pan_x, -40.0, places=6)
        self.assertAlmostEqual(workspace.views["view_after"].pan_y, 25.0, places=6)
        self.assertFalse(workspace.dirty)
        self.assertEqual(
            workspace.unresolved_node_docs,
            {
                "after_ghost": {
                    "node_id": "after_ghost",
                    "type_id": "missing.after",
                    "title": "After Ghost",
                }
            },
        )
        self.assertEqual(workspace.unresolved_edge_docs, {})
        self.assertEqual(workspace.authored_node_overrides, {after_node.node_id: {"parent_node_id": "after_ghost"}})

    def test_persistent_node_elapsed_action_types_preserve_recorded_labels(self) -> None:
        model = GraphModel()
        history = RuntimeGraphHistory()
        workspace = model.active_workspace
        workspace_id = workspace.workspace_id

        before = history.capture_workspace(workspace)
        model.add_node(workspace_id, "core.start", "Start", 0.0, 0.0)
        self.assertTrue(history.record_action(workspace_id, ACTION_EDIT_EDGE_LABEL, before, workspace))

        undone = history.undo_workspace(workspace_id, workspace)
        self.assertIsNotNone(undone)
        assert undone is not None
        self.assertEqual(undone.action_type, ACTION_EDIT_EDGE_LABEL)

        redone = history.redo_workspace(workspace_id, workspace)
        self.assertIsNotNone(redone)
        assert redone is not None
        self.assertEqual(redone.action_type, ACTION_EDIT_EDGE_LABEL)

        history.clear_workspace(workspace_id)
        with history.grouped_action(workspace_id, ACTION_GROUP_SELECTED_NODES, workspace):
            model.add_node(workspace_id, "core.start", "Grouped Start", 40.0, 20.0)
            model.add_node(workspace_id, "core.end", "Grouped End", 320.0, 60.0)

        grouped = history.undo_workspace(workspace_id, workspace)
        self.assertIsNotNone(grouped)
        assert grouped is not None
        self.assertEqual(grouped.action_type, ACTION_GROUP_SELECTED_NODES)


__all__ = ["RuntimeGraphHistoryTrackBTests"]
