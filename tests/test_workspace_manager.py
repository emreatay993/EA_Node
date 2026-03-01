from __future__ import annotations

import unittest

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.workspace.manager import WorkspaceManager


class WorkspaceManagerTests(unittest.TestCase):
    def test_create_duplicate_and_reorder(self) -> None:
        model = GraphModel()
        manager = WorkspaceManager(model)
        first = manager.active_workspace_id()
        second = manager.create_workspace("Second")
        duplicate = manager.duplicate_workspace(second)
        refs = manager.list_workspaces()
        self.assertEqual(len(refs), 3)
        ids = [ref.workspace_id for ref in refs]
        self.assertIn(first, ids)
        self.assertIn(second, ids)
        self.assertIn(duplicate, ids)

        from_index = ids.index(duplicate)
        manager.move_workspace(from_index, 0)
        moved_ids = [ref.workspace_id for ref in manager.list_workspaces()]
        self.assertEqual(moved_ids[0], duplicate)

    def test_workspace_lifecycle_operations_remain_consistent(self) -> None:
        model = GraphModel()
        manager = WorkspaceManager(model)
        first = manager.active_workspace_id()

        manager.rename_workspace(first, "Primary")
        self.assertEqual(model.project.workspaces[first].name, "Primary")

        second = manager.create_workspace("Second")
        duplicate = manager.duplicate_workspace(second)
        ordered = [ref.workspace_id for ref in manager.list_workspaces()]
        self.assertEqual(ordered, [first, second, duplicate])

        manager.set_active_workspace(first)
        self.assertEqual(manager.active_workspace_id(), first)

        manager.close_workspace(second)
        ordered_after_close = [ref.workspace_id for ref in manager.list_workspaces()]
        self.assertEqual(ordered_after_close, [first, duplicate])
        self.assertEqual(manager.active_workspace_id(), first)

        manager.close_workspace(duplicate)
        self.assertEqual([ref.workspace_id for ref in manager.list_workspaces()], [first])
        with self.assertRaises(ValueError):
            manager.close_workspace(first)

    def test_closing_active_workspace_selects_adjacent_tab_by_order(self) -> None:
        model = GraphModel()
        manager = WorkspaceManager(model)
        first = manager.active_workspace_id()
        second = manager.create_workspace("Second")
        third = manager.create_workspace("Third")

        manager.move_workspace(2, 1)
        self.assertEqual(
            [ref.workspace_id for ref in manager.list_workspaces()],
            [first, third, second],
        )

        manager.set_active_workspace(third)
        manager.close_workspace(third)
        self.assertEqual(manager.active_workspace_id(), second)
        self.assertEqual([ref.workspace_id for ref in manager.list_workspaces()], [first, second])


if __name__ == "__main__":
    unittest.main()
