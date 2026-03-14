from __future__ import annotations

import copy
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from ea_node_editor.settings import DEFAULT_GRAPHICS_SETTINGS
from ea_node_editor.ui.dialogs.graphics_settings_dialog import GraphicsSettingsDialog
from ea_node_editor.ui.dialogs.sectioned_settings_dialog import SectionedSettingsDialog
from ea_node_editor.ui.graph_theme import graph_theme_choices, resolve_graph_theme


class GraphicsSettingsDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_dialog_defaults_and_values_roundtrip(self) -> None:
        dialog = GraphicsSettingsDialog()
        try:
            self.assertIsInstance(dialog, SectionedSettingsDialog)
            self.assertEqual(dialog.values(), DEFAULT_GRAPHICS_SETTINGS)
            self.assertTrue(dialog.follow_shell_theme_check.isChecked())
            self.assertFalse(dialog.graph_theme_combo.isEnabled())

            dialog.show_grid_check.setChecked(False)
            dialog.show_minimap_check.setChecked(False)
            dialog.minimap_expanded_check.setChecked(False)
            dialog.snap_to_grid_check.setChecked(True)
            dialog.theme_combo.setCurrentIndex(dialog.theme_combo.findData("stitch_light"))
            dialog.follow_shell_theme_check.setChecked(False)
            dialog.graph_theme_combo.setCurrentIndex(dialog.graph_theme_combo.findData("graph_stitch_light"))

            expected = copy.deepcopy(DEFAULT_GRAPHICS_SETTINGS)
            expected["canvas"]["show_grid"] = False
            expected["canvas"]["show_minimap"] = False
            expected["canvas"]["minimap_expanded"] = False
            expected["interaction"]["snap_to_grid"] = True
            expected["theme"]["theme_id"] = "stitch_light"
            expected["graph_theme"]["follow_shell_theme"] = False
            expected["graph_theme"]["selected_theme_id"] = "graph_stitch_light"
            self.assertEqual(
                dialog.values(),
                expected,
            )
        finally:
            dialog.close()

    def test_dialog_roundtrips_custom_graph_theme_library_without_manager_ui(self) -> None:
        custom_theme = copy.deepcopy(resolve_graph_theme("graph_stitch_light").as_dict())
        custom_theme["theme_id"] = "custom_graph_theme_deadbeef"
        custom_theme["label"] = "Ocean Wire"
        available_graph_themes = graph_theme_choices([custom_theme])
        initial_settings = copy.deepcopy(DEFAULT_GRAPHICS_SETTINGS)
        initial_settings["graph_theme"] = {
            "follow_shell_theme": False,
            "selected_theme_id": custom_theme["theme_id"],
            "custom_themes": [custom_theme],
        }

        dialog = GraphicsSettingsDialog(
            initial_settings=initial_settings,
            available_graph_themes=available_graph_themes,
        )
        try:
            self.assertEqual(dialog.graph_theme_combo.count(), len(available_graph_themes))
            self.assertEqual(dialog.graph_theme_combo.currentData(), custom_theme["theme_id"])
            self.assertTrue(dialog.graph_theme_combo.isEnabled())

            values = dialog.values()
            self.assertEqual(values["graph_theme"]["selected_theme_id"], custom_theme["theme_id"])
            self.assertEqual(values["graph_theme"]["custom_themes"][0]["theme_id"], custom_theme["theme_id"])
            self.assertEqual(values["graph_theme"]["custom_themes"][0]["label"], "Ocean Wire")
        finally:
            dialog.close()

    def test_dialog_normalizes_invalid_initial_settings(self) -> None:
        dialog = GraphicsSettingsDialog(
            initial_settings={
                "canvas": {
                    "show_grid": False,
                    "show_minimap": "no",
                    "minimap_expanded": False,
                },
                "interaction": {
                    "snap_to_grid": True,
                },
                "theme": {
                    "theme_id": "unknown_theme",
                },
                "graph_theme": {
                    "follow_shell_theme": "no",
                    "selected_theme_id": "unknown_graph_theme",
                },
            }
        )
        try:
            self.assertEqual(dialog.section_list.count(), 3)
            self.assertEqual(dialog.theme_combo.count(), 2)
            self.assertEqual(dialog.graph_theme_combo.count(), len(graph_theme_choices()))
            self.assertTrue(dialog.follow_shell_theme_check.isChecked())
            self.assertFalse(dialog.graph_theme_combo.isEnabled())
            expected = copy.deepcopy(DEFAULT_GRAPHICS_SETTINGS)
            expected["canvas"]["show_grid"] = False
            expected["canvas"]["minimap_expanded"] = False
            expected["interaction"]["snap_to_grid"] = True
            self.assertEqual(
                dialog.values(),
                expected,
            )
        finally:
            dialog.close()

    def test_follow_shell_toggle_enables_explicit_graph_theme_selection(self) -> None:
        dialog = GraphicsSettingsDialog()
        try:
            self.assertFalse(dialog.graph_theme_combo.isEnabled())

            dialog.follow_shell_theme_check.setChecked(False)
            self.assertTrue(dialog.graph_theme_combo.isEnabled())

            dialog.follow_shell_theme_check.setChecked(True)
            self.assertFalse(dialog.graph_theme_combo.isEnabled())
        finally:
            dialog.close()

    def test_manage_graph_themes_callback_updates_theme_library_and_selection(self) -> None:
        custom_theme = copy.deepcopy(resolve_graph_theme("graph_stitch_light").as_dict())
        custom_theme["theme_id"] = "custom_graph_theme_deadbeef"
        custom_theme["label"] = "Ocean Wire"
        received_settings: list[dict[str, object]] = []

        def manage_graph_themes(graph_theme_settings: dict[str, object]) -> dict[str, object]:
            received_settings.append(copy.deepcopy(graph_theme_settings))
            return {
                "follow_shell_theme": False,
                "selected_theme_id": custom_theme["theme_id"],
                "custom_themes": [custom_theme],
            }

        dialog = GraphicsSettingsDialog(manage_graph_themes_callback=manage_graph_themes)
        try:
            self.assertTrue(dialog.manage_graph_themes_button.isEnabled())

            dialog.manage_graph_themes_button.click()

            self.assertEqual(len(received_settings), 1)
            self.assertTrue(received_settings[0]["follow_shell_theme"])
            self.assertEqual(received_settings[0]["selected_theme_id"], "graph_stitch_dark")
            self.assertEqual(received_settings[0]["custom_themes"], [])
            self.assertEqual(dialog.graph_theme_combo.count(), len(graph_theme_choices([custom_theme])))
            self.assertEqual(dialog.graph_theme_combo.currentData(), custom_theme["theme_id"])
            self.assertTrue(dialog.graph_theme_combo.isEnabled())
            self.assertFalse(dialog.follow_shell_theme_check.isChecked())

            values = dialog.values()
            self.assertFalse(values["graph_theme"]["follow_shell_theme"])
            self.assertEqual(values["graph_theme"]["selected_theme_id"], custom_theme["theme_id"])
            self.assertEqual(values["graph_theme"]["custom_themes"][0]["label"], "Ocean Wire")
        finally:
            dialog.close()

    def test_manage_graph_themes_button_is_disabled_without_callback(self) -> None:
        dialog = GraphicsSettingsDialog()
        try:
            self.assertFalse(dialog.manage_graph_themes_button.isEnabled())
            with patch.object(dialog, "_open_graph_theme_manager") as open_manager:
                dialog.manage_graph_themes_button.click()
            open_manager.assert_not_called()
        finally:
            dialog.close()


if __name__ == "__main__":
    unittest.main()
