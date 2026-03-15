from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication, QDialog

from ea_node_editor.graph.model import ProjectData
from ea_node_editor.ui.passive_style_presets import (
    PassiveStylePresetCatalog,
    built_in_style_presets,
)
from ea_node_editor.ui.shell.window import ShellWindow


class PassiveStylePresetCatalogTests(unittest.TestCase):
    def test_catalog_exposes_read_only_starters_without_serializing_them(self) -> None:
        catalog = PassiveStylePresetCatalog("node", [])

        built_ins = built_in_style_presets("node")
        edge_built_ins = built_in_style_presets("edge")

        self.assertTrue(built_ins)
        self.assertTrue(edge_built_ins)
        self.assertEqual(catalog.user_presets(), [])
        self.assertEqual(catalog.entries()[: len(built_ins)], built_ins)
        self.assertTrue(all(entry.get("read_only") for entry in built_ins))

        saved = catalog.save_new("Project Accent", {"fill_color": "#112233", "border_width": "2.5"})
        assert saved is not None

        self.assertFalse(saved.get("read_only"))
        self.assertRegex(saved["preset_id"], r"^node_preset_[0-9a-f]{8}$")
        self.assertEqual(
            catalog.user_presets(),
            [
                {
                    "preset_id": saved["preset_id"],
                    "name": "Project Accent",
                    "style": {
                        "fill_color": "#112233",
                        "border_width": 2.5,
                    },
                }
            ],
        )


class PassiveStylePresetProjectScopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = QApplication.instance() or QApplication([])

    def test_shell_uses_current_project_preset_library_when_projects_switch(self) -> None:
        window = ShellWindow()
        window._persist_session = lambda project_doc=None: None

        class FakePassiveNodeStyleDialog:
            DialogCode = QDialog.DialogCode
            seen_user_presets: list[list[dict[str, object]]] = []
            next_user_presets: list[dict[str, object]] = []
            next_result = QDialog.DialogCode.Rejected

            def __init__(self, initial_style=None, parent=None, *, user_presets=None) -> None:
                FakePassiveNodeStyleDialog.seen_user_presets.append(copy.deepcopy(user_presets or []))

            def exec(self) -> int:
                return int(FakePassiveNodeStyleDialog.next_result)

            def user_presets(self) -> list[dict[str, object]]:
                return copy.deepcopy(FakePassiveNodeStyleDialog.next_user_presets)

            def node_style(self) -> dict[str, object]:
                return {"fill_color": "#778899"}

        try:
            project_a = ProjectData(
                project_id="proj_a",
                name="Project A",
                metadata={
                    "ui": {
                        "passive_style_presets": {
                            "node_presets": [
                                {
                                    "preset_id": "node_preset_aa11bb22",
                                    "name": "A Only",
                                    "style": {"fill_color": "#112233"},
                                }
                            ],
                            "edge_presets": [],
                        }
                    }
                },
            )
            window.project_session_controller._install_project(project_a, project_path="")
            window._ensure_project_metadata_defaults()
            workspace_id_a = window.workspace_manager.active_workspace_id()
            node_a = window.model.add_node(workspace_id_a, "passive.flowchart.process", "A", 10.0, 20.0)

            FakePassiveNodeStyleDialog.next_user_presets = [
                {
                    "preset_id": "node_preset_cc33dd44",
                    "name": "A Updated",
                    "style": {"fill_color": "#445566"},
                }
            ]

            with patch("ea_node_editor.ui.dialogs.PassiveNodeStyleDialog", FakePassiveNodeStyleDialog):
                self.assertIsNone(window.edit_passive_node_style(node_a.node_id))

            self.assertEqual(
                FakePassiveNodeStyleDialog.seen_user_presets[0],
                [
                    {
                        "preset_id": "node_preset_aa11bb22",
                        "name": "A Only",
                        "style": {"fill_color": "#112233"},
                    }
                ],
            )
            self.assertEqual(
                project_a.metadata["ui"]["passive_style_presets"]["node_presets"],
                [
                    {
                        "preset_id": "node_preset_cc33dd44",
                        "name": "A Updated",
                        "style": {"fill_color": "#445566"},
                    }
                ],
            )

            project_b = ProjectData(
                project_id="proj_b",
                name="Project B",
                metadata={
                    "ui": {
                        "passive_style_presets": {
                            "node_presets": [
                                {
                                    "preset_id": "node_preset_ee55ff66",
                                    "name": "B Only",
                                    "style": {"fill_color": "#AABBCC"},
                                }
                            ],
                            "edge_presets": [],
                        }
                    }
                },
            )
            window.project_session_controller._install_project(project_b, project_path="")
            window._ensure_project_metadata_defaults()
            workspace_id_b = window.workspace_manager.active_workspace_id()
            node_b = window.model.add_node(workspace_id_b, "passive.flowchart.process", "B", 40.0, 50.0)

            FakePassiveNodeStyleDialog.next_user_presets = [
                {
                    "preset_id": "node_preset_ee55ff66",
                    "name": "B Only",
                    "style": {"fill_color": "#AABBCC"},
                }
            ]

            with patch("ea_node_editor.ui.dialogs.PassiveNodeStyleDialog", FakePassiveNodeStyleDialog):
                self.assertIsNone(window.edit_passive_node_style(node_b.node_id))

            self.assertEqual(
                FakePassiveNodeStyleDialog.seen_user_presets[1],
                [
                    {
                        "preset_id": "node_preset_ee55ff66",
                        "name": "B Only",
                        "style": {"fill_color": "#AABBCC"},
                    }
                ],
            )
            self.assertEqual(
                project_a.metadata["ui"]["passive_style_presets"]["node_presets"],
                [
                    {
                        "preset_id": "node_preset_cc33dd44",
                        "name": "A Updated",
                        "style": {"fill_color": "#445566"},
                    }
                ],
            )
            self.assertEqual(
                project_b.metadata["ui"]["passive_style_presets"]["node_presets"],
                [
                    {
                        "preset_id": "node_preset_ee55ff66",
                        "name": "B Only",
                        "style": {"fill_color": "#AABBCC"},
                    }
                ],
            )
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
