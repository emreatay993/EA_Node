from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from ea_node_editor.settings import DEFAULT_GRAPHICS_SETTINGS
from ea_node_editor.ui.dialogs.graphics_settings_dialog import GraphicsSettingsDialog
from ea_node_editor.ui.dialogs.sectioned_settings_dialog import SectionedSettingsDialog
from ea_node_editor.ui.graph_theme import graph_theme_choices, resolve_graph_theme


class GraphicsSettingsDialogTests(unittest.TestCase):

    def test_dialog_defaults_and_values_roundtrip(self) -> None:
        dialog = GraphicsSettingsDialog()
        try:
            self.assertIsInstance(dialog, SectionedSettingsDialog)
            self.assertEqual(dialog.values(), DEFAULT_GRAPHICS_SETTINGS)
            self.assertEqual(dialog.show_port_labels_check.objectName(), "graphicsSettingsShowPortLabelsCheck")
            self.assertTrue(dialog.show_port_labels_check.isChecked())
            self.assertTrue(dialog.full_fidelity_mode_button.isChecked())
            self.assertFalse(dialog.max_performance_mode_button.isChecked())
            self.assertTrue(dialog.follow_shell_theme_check.isChecked())
            self.assertFalse(dialog.graph_theme_combo.isEnabled())

            dialog.show_grid_check.setChecked(False)
            dialog.show_minimap_check.setChecked(False)
            dialog.show_port_labels_check.setChecked(False)
            dialog.minimap_expanded_check.setChecked(False)
            dialog.snap_to_grid_check.setChecked(True)
            dialog.max_performance_mode_button.setChecked(True)
            dialog.tab_strip_density_combo.setCurrentIndex(dialog.tab_strip_density_combo.findData("regular"))
            dialog.theme_combo.setCurrentIndex(dialog.theme_combo.findData("stitch_light"))
            dialog.follow_shell_theme_check.setChecked(False)
            dialog.graph_theme_combo.setCurrentIndex(dialog.graph_theme_combo.findData("graph_stitch_light"))

            expected = copy.deepcopy(DEFAULT_GRAPHICS_SETTINGS)
            expected["canvas"]["show_grid"] = False
            expected["canvas"]["show_minimap"] = False
            expected["canvas"]["show_port_labels"] = False
            expected["canvas"]["minimap_expanded"] = False
            expected["interaction"]["snap_to_grid"] = True
            expected["performance"]["mode"] = "max_performance"
            expected["shell"]["tab_strip_density"] = "regular"
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
                    "show_port_labels": False,
                    "minimap_expanded": False,
                },
                "interaction": {
                    "snap_to_grid": True,
                },
                "performance": {
                    "mode": "warp_speed",
                },
                "shell": {
                    "tab_strip_density": "huge",
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
            self.assertEqual(dialog.section_list.count(), 4)
            self.assertEqual(dialog.theme_combo.count(), 2)
            self.assertEqual(dialog.graph_theme_combo.count(), len(graph_theme_choices()))
            self.assertTrue(dialog.full_fidelity_mode_button.isChecked())
            self.assertFalse(dialog.max_performance_mode_button.isChecked())
            self.assertTrue(dialog.follow_shell_theme_check.isChecked())
            self.assertFalse(dialog.graph_theme_combo.isEnabled())
            self.assertFalse(dialog.show_port_labels_check.isChecked())
            expected = copy.deepcopy(DEFAULT_GRAPHICS_SETTINGS)
            expected["canvas"]["show_grid"] = False
            expected["canvas"]["show_port_labels"] = False
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
            self.assertEqual(dialog.graph_theme_combo.currentData(), "graph_stitch_dark")

            dialog.follow_shell_theme_check.setChecked(False)
            self.assertTrue(dialog.graph_theme_combo.isEnabled())
            dialog.graph_theme_combo.setCurrentIndex(dialog.graph_theme_combo.findData("graph_stitch_light"))
            self.assertEqual(dialog.graph_theme_combo.currentData(), "graph_stitch_light")

            dialog.follow_shell_theme_check.setChecked(True)
            self.assertFalse(dialog.graph_theme_combo.isEnabled())
            self.assertEqual(dialog.graph_theme_combo.currentData(), "graph_stitch_dark")

            dialog.theme_combo.setCurrentIndex(dialog.theme_combo.findData("stitch_light"))
            self.assertEqual(dialog.graph_theme_combo.currentData(), "graph_stitch_light")

            dialog.follow_shell_theme_check.setChecked(False)
            self.assertTrue(dialog.graph_theme_combo.isEnabled())
            self.assertEqual(dialog.graph_theme_combo.currentData(), "graph_stitch_light")
        finally:
            dialog.close()

    def test_follow_shell_preserves_previous_explicit_graph_theme_in_values(self) -> None:
        custom_theme = copy.deepcopy(resolve_graph_theme("graph_stitch_light").as_dict())
        custom_theme["theme_id"] = "custom_graph_theme_deadbeef"
        custom_theme["label"] = "Ocean Wire"
        dialog = GraphicsSettingsDialog(
            initial_settings={
                "theme": {"theme_id": "stitch_dark"},
                "graph_theme": {
                    "follow_shell_theme": False,
                    "selected_theme_id": custom_theme["theme_id"],
                    "custom_themes": [custom_theme],
                },
            },
            available_graph_themes=graph_theme_choices([custom_theme]),
        )
        try:
            self.assertEqual(dialog.graph_theme_combo.currentData(), custom_theme["theme_id"])

            dialog.follow_shell_theme_check.setChecked(True)
            self.assertEqual(dialog.graph_theme_combo.currentData(), "graph_stitch_dark")

            values = dialog.values()
            self.assertTrue(values["graph_theme"]["follow_shell_theme"])
            self.assertEqual(values["graph_theme"]["selected_theme_id"], custom_theme["theme_id"])

            dialog.follow_shell_theme_check.setChecked(False)
            self.assertEqual(dialog.graph_theme_combo.currentData(), custom_theme["theme_id"])
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

    def test_dialog_shows_active_renderer_as_read_only_runtime_info(self) -> None:
        dialog = GraphicsSettingsDialog(active_renderer_label="Direct3D 11")
        try:
            self.assertEqual(dialog.active_renderer_value_label.text(), "Direct3D 11")
            self.assertTrue(
                bool(
                    dialog.active_renderer_value_label.textInteractionFlags()
                    & Qt.TextInteractionFlag.TextSelectableByMouse
                )
            )
            self.assertEqual(dialog.values(), DEFAULT_GRAPHICS_SETTINGS)
        finally:
            dialog.close()

    def test_dialog_shows_performance_mode_copy_and_initial_selection(self) -> None:
        dialog = GraphicsSettingsDialog(
            initial_settings={
                "performance": {
                    "mode": "max_performance",
                }
            }
        )
        try:
            self.assertEqual(
                dialog.performance_mode_summary_label.text(),
                "Choose the app-wide graphics mode used across the shell and graph canvas.",
            )
            self.assertEqual(dialog.full_fidelity_mode_button.objectName(), "graphicsSettingsFullFidelityModeRadio")
            self.assertEqual(dialog.full_fidelity_mode_button.text(), "Full Fidelity")
            self.assertEqual(
                dialog.full_fidelity_mode_copy_label.text(),
                "Keeps normal visual quality and applies only invisible structural optimizations.",
            )
            self.assertEqual(dialog.max_performance_mode_button.objectName(), "graphicsSettingsMaxPerformanceModeRadio")
            self.assertEqual(dialog.max_performance_mode_button.text(), "Max Performance")
            self.assertEqual(
                dialog.max_performance_mode_copy_label.text(),
                "Temporarily simplifies whole-canvas rendering during pan, zoom, and burst edits; idle quality restores automatically.",
            )
            self.assertFalse(dialog.full_fidelity_mode_button.isChecked())
            self.assertTrue(dialog.max_performance_mode_button.isChecked())
            self.assertEqual(dialog.values()["performance"]["mode"], "max_performance")
        finally:
            dialog.close()

    def test_clicking_performance_mode_option_card_updates_selection(self) -> None:
        dialog = GraphicsSettingsDialog()
        try:
            dialog.show()
            QApplication.instance().processEvents()

            self.assertTrue(dialog.full_fidelity_mode_button.isChecked())
            self.assertEqual(dialog.full_fidelity_mode_option.property("performanceModeSelected"), True)
            self.assertEqual(dialog.max_performance_mode_option.property("performanceModeSelected"), False)

            QTest.mouseClick(
                dialog.max_performance_mode_option,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier,
            )
            QApplication.instance().processEvents()

            self.assertFalse(dialog.full_fidelity_mode_button.isChecked())
            self.assertTrue(dialog.max_performance_mode_button.isChecked())
            self.assertEqual(dialog.full_fidelity_mode_option.property("performanceModeSelected"), False)
            self.assertEqual(dialog.max_performance_mode_option.property("performanceModeSelected"), True)
            self.assertEqual(dialog.values()["performance"]["mode"], "max_performance")
        finally:
            dialog.close()


if __name__ == "__main__":
    unittest.main()
