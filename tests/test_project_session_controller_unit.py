from __future__ import annotations

import unittest

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.ui.shell.controllers.project_session_controller import ProjectSessionController


class _ProjectHostStub:
    def __init__(self) -> None:
        self.model = GraphModel()


class _RecentProjectsHostStub:
    def __init__(self) -> None:
        self.recent_project_paths: list[str] = []
        self.refresh_calls = 0

    def _refresh_recent_projects_menu(self) -> None:
        self.refresh_calls += 1


class ProjectSessionControllerUnitTests(unittest.TestCase):
    def test_metadata_defaults_are_merged_without_dropping_existing_values(self) -> None:
        host = _ProjectHostStub()
        host.model.project.metadata = {
            "workflow_settings": {
                "solver_config": {"thread_count": 16},
            },
            "ui": {
                "script_editor": {"visible": True},
            },
        }
        controller = ProjectSessionController(host)  # type: ignore[arg-type]

        controller.ensure_project_metadata_defaults()

        metadata = host.model.project.metadata
        self.assertEqual(metadata["workflow_settings"]["solver_config"]["thread_count"], 16)
        self.assertIn("memory_limit_gb", metadata["workflow_settings"]["solver_config"])
        self.assertTrue(metadata["ui"]["script_editor"]["visible"])
        self.assertIn("floating", metadata["ui"]["script_editor"])

    def test_recent_project_paths_are_normalized_deduplicated_and_capped(self) -> None:
        host = _RecentProjectsHostStub()
        controller = ProjectSessionController(host)  # type: ignore[arg-type]

        normalized = controller.set_recent_project_paths(
            [
                " first_project ",
                "first_project.sfe",
                "",
                ".",
                *(f"project_{index}" for index in range(2, 20)),
            ],
            persist=False,
        )

        self.assertEqual(normalized[0], "first_project.sfe")
        self.assertEqual(len(normalized), 10)
        self.assertEqual(len(set(normalized)), len(normalized))
        self.assertEqual(host.recent_project_paths, normalized)
        self.assertEqual(host.refresh_calls, 1)


if __name__ == "__main__":
    unittest.main()
