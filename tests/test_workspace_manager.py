from __future__ import annotations

import unittest

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.workspace.manager import WorkspaceManager


class WorkspaceManagerTests(unittest.TestCase):
    def test_manager_normalizes_workspace_order_and_active_workspace_from_project_state(self) -> None:
        model = GraphModel()
        first = model.active_workspace.workspace_id
        second = model.create_workspace("Second").workspace_id
        third = model.create_workspace("Third").workspace_id
        model.project.metadata = {"workspace_order": [third, "missing", first, third]}
        model.project.active_workspace_id = "missing"

        manager = WorkspaceManager(model)

        self.assertEqual(model.project.metadata["workspace_order"], [third, first, second])
        self.assertEqual(manager.active_workspace_id(), third)
        self.assertEqual(
            [workspace.workspace_id for workspace in manager.list_workspaces()],
            [third, first, second],
        )

    def test_duplicate_workspace_inserts_clone_after_source_in_authoritative_order(self) -> None:
        model = GraphModel()
        first = model.active_workspace.workspace_id
        second = model.create_workspace("Second").workspace_id
        third = model.create_workspace("Third").workspace_id
        manager = WorkspaceManager(model)
        manager.move_workspace(2, 1)

        duplicated = manager.duplicate_workspace(third)

        self.assertEqual(
            model.project.metadata["workspace_order"],
            [first, third, duplicated, second],
        )
        self.assertEqual(manager.active_workspace_id(), duplicated)

    def test_close_workspace_promotes_the_next_workspace_in_authoritative_order(self) -> None:
        model = GraphModel()
        first = model.active_workspace.workspace_id
        second = model.create_workspace("Second").workspace_id
        third = model.create_workspace("Third").workspace_id
        manager = WorkspaceManager(model)
        manager.move_workspace(2, 1)
        manager.set_active_workspace(third)

        manager.close_workspace(third)

        self.assertEqual(model.project.metadata["workspace_order"], [first, second])
        self.assertEqual(manager.active_workspace_id(), second)


if __name__ == "__main__":
    unittest.main()
