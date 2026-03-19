from __future__ import annotations

import unittest
from unittest import mock

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.ui.shell.controllers.project_session_controller import ProjectSessionController
from ea_node_editor.ui.shell.state import ShellProjectSessionState


class _ScriptEditorStub:
    def __init__(self) -> None:
        self.visible = False
        self.floating = False
        self.focus_calls = 0
        self.nodes = []

    def set_visible(self, value: bool) -> None:
        self.visible = bool(value)

    def set_floating(self, value: bool) -> None:
        self.floating = bool(value)

    def focus_editor(self) -> None:
        self.focus_calls += 1

    def set_node(self, node) -> None:  # noqa: ANN001
        self.nodes.append(node)


class _ActionToggleStub:
    def __init__(self) -> None:
        self.checked = False

    def setChecked(self, value: bool) -> None:  # noqa: N802
        self.checked = bool(value)


class _SceneStub:
    def __init__(self, selected_node_id: str = "") -> None:
        self._selected_node_id = selected_node_id

    def selected_node_id(self) -> str:
        return self._selected_node_id


class _ProjectHostStub:
    def __init__(self) -> None:
        self.project_session_state = ShellProjectSessionState()
        self.model = GraphModel()
        self.script_editor = _ScriptEditorStub()
        self.action_toggle_script_editor = _ActionToggleStub()
        self.scene = _SceneStub()
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
        self.assertIn("passive_style_presets", metadata["ui"])

    def test_recent_project_paths_are_normalized_deduplicated_and_capped(self) -> None:
        host = _ProjectHostStub()
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
        self.assertEqual(host.project_session_state.recent_project_paths, normalized)
        self.assertEqual(host.refresh_calls, 1)

    def test_add_and_remove_recent_project_paths_normalize_suffixes(self) -> None:
        host = _ProjectHostStub()
        controller = ProjectSessionController(host)  # type: ignore[arg-type]

        with mock.patch.object(controller, "persist_session") as persist_session:
            controller.set_recent_project_paths(["alpha.sfe", "beta.sfe"], persist=False)
            updated = controller.add_recent_project_path("beta", persist=True)
            self.assertEqual(updated[:2], ["beta.sfe", "alpha.sfe"])

            updated = controller.remove_recent_project_path("alpha", persist=True)
            self.assertEqual(updated, ["beta.sfe"])
            self.assertEqual(persist_session.call_count, 2)

    def test_restore_script_editor_state_requires_selected_node_for_visibility(self) -> None:
        host = _ProjectHostStub()
        host.model.project.metadata = {
            "ui": {
                "script_editor": {
                    "visible": True,
                    "floating": True,
                }
            }
        }
        controller = ProjectSessionController(host)  # type: ignore[arg-type]

        controller.restore_script_editor_state()
        self.assertTrue(host.script_editor.floating)
        self.assertFalse(host.script_editor.visible)
        self.assertFalse(host.action_toggle_script_editor.checked)

        host.scene = _SceneStub(selected_node_id="node_1")
        controller.restore_script_editor_state()
        self.assertTrue(host.script_editor.visible)
        self.assertTrue(host.action_toggle_script_editor.checked)


if __name__ == "__main__":
    unittest.main()
