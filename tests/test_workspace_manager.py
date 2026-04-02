from __future__ import annotations

import unittest

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.persistence.overlay import (
    capture_workspace_persistence_state,
    restore_workspace_persistence_state,
)
from ea_node_editor.workspace.manager import WorkspaceManager


class WorkspaceManagerTests(unittest.TestCase):
    def test_manager_normalizes_workspace_order_and_active_workspace_from_project_state(self) -> None:
        model = GraphModel()
        manager = WorkspaceManager(model)
        first = manager.active_workspace_id()
        second = manager.create_workspace("Second")
        third = manager.create_workspace("Third")
        model.project.metadata = {"workspace_order": [third, "missing", first, third]}
        model.project.active_workspace_id = "missing"
        manager = WorkspaceManager(model)

        self.assertEqual(model.project.metadata["workspace_order"], [third, first, second])
        self.assertEqual(manager.active_workspace_id(), third)
        self.assertEqual(
            [workspace.workspace_id for workspace in manager.list_workspaces()],
            [third, first, second],
        )

    def test_create_workspace_appends_to_authoritative_order_and_activates_the_new_workspace(self) -> None:
        model = GraphModel()
        manager = WorkspaceManager(model)
        first = manager.active_workspace_id()

        second = manager.create_workspace("Second")

        self.assertEqual(model.project.metadata["workspace_order"], [first, second])
        self.assertEqual(manager.active_workspace_id(), second)

    def test_duplicate_workspace_inserts_clone_after_source_in_authoritative_order(self) -> None:
        model = GraphModel()
        manager = WorkspaceManager(model)
        first = manager.active_workspace_id()
        second = manager.create_workspace("Second")
        third = manager.create_workspace("Third")
        manager.move_workspace(2, 1)

        duplicated = manager.duplicate_workspace(third)

        self.assertEqual(
            model.project.metadata["workspace_order"],
            [first, third, duplicated, second],
        )
        self.assertEqual(manager.active_workspace_id(), duplicated)

    def test_duplicate_workspace_preserves_externalized_persistence_overlay(self) -> None:
        model = GraphModel()
        manager = WorkspaceManager(model)
        source = model.active_workspace
        state = capture_workspace_persistence_state(source)
        state.replace_unresolved_node_docs(
            {"node_missing": {"node_id": "node_missing", "type_id": "plugin.missing"}}
        )
        restore_workspace_persistence_state(source, state)

        duplicated_id = manager.duplicate_workspace(source.workspace_id)
        duplicate = model.project.workspaces[duplicated_id]
        duplicate_state = capture_workspace_persistence_state(duplicate)

        self.assertEqual(
            duplicate_state.unresolved_node_docs,
            {"node_missing": {"node_id": "node_missing", "type_id": "plugin.missing"}},
        )

        duplicate_state.unresolved_node_docs["node_missing"]["type_id"] = "plugin.changed"
        restore_workspace_persistence_state(duplicate, duplicate_state)

        self.assertEqual(
            capture_workspace_persistence_state(source).unresolved_node_docs["node_missing"]["type_id"],
            "plugin.missing",
        )

    def test_close_workspace_promotes_the_next_workspace_in_authoritative_order(self) -> None:
        model = GraphModel()
        manager = WorkspaceManager(model)
        first = manager.active_workspace_id()
        second = manager.create_workspace("Second")
        third = manager.create_workspace("Third")
        manager.move_workspace(2, 1)
        manager.set_active_workspace(third)

        manager.close_workspace(third)

        self.assertEqual(model.project.metadata["workspace_order"], [first, second])
        self.assertEqual(manager.active_workspace_id(), second)


if __name__ == "__main__":
    unittest.main()
