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
            self.assertEqual(
                [dialog.section_list.item(index).text() for index in range(dialog.section_list.count())],
                ["Canvas", "Interaction", "Performance", "Theme", "Layout"],
            )
            self.assertEqual(dialog.values(), DEFAULT_GRAPHICS_SETTINGS)
            self.assertEqual(dialog.show_port_labels_check.objectName(), "graphicsSettingsShowPortLabelsCheck")
            self.assertEqual(
                dialog.edge_crossing_style_combo.objectName(),
                "graphicsSettingsEdgeCrossingStyleCombo",
            )
            self.assertTrue(dialog.show_port_labels_check.isChecked())
            self.assertEqual(dialog.edge_crossing_style_combo.currentData(), "none")
            self.assertTrue(dialog.full_fidelity_mode_button.isChecked())
            self.assertFalse(dialog.max_performance_mode_button.isChecked())
            self.assertTrue(dialog.expand_collision_enabled_check.isChecked())
            self.assertEqual(
                dialog.expand_collision_enabled_check.objectName(),
                "graphicsSettingsExpandCollisionAvoidanceEnabledCheck",
            )
            self.assertEqual(
                dialog.expand_collision_strategy_combo.objectName(),
                "graphicsSettingsExpandCollisionAvoidanceStrategyCombo",
            )
            self.assertEqual(dialog.expand_collision_strategy_combo.currentData(), "nearest")
            self.assertEqual(dialog.expand_collision_scope_combo.currentData(), "all_movable")
            self.assertEqual(dialog.expand_collision_radius_mode_combo.currentData(), "local")
            self.assertEqual(dialog.expand_collision_local_radius_preset_combo.currentData(), "medium")
            self.assertEqual(dialog.expand_collision_gap_preset_combo.currentData(), "normal")
            self.assertTrue(dialog.expand_collision_animate_check.isChecked())
            self.assertTrue(dialog.follow_shell_theme_check.isChecked())
            self.assertFalse(dialog.graph_theme_combo.isEnabled())

            dialog.show_grid_check.setChecked(False)
            dialog.grid_style_combo.setCurrentIndex(dialog.grid_style_combo.findData("points"))
            dialog.edge_crossing_style_combo.setCurrentIndex(dialog.edge_crossing_style_combo.findData("gap_break"))
            dialog.show_minimap_check.setChecked(False)
            dialog.show_port_labels_check.setChecked(False)
            dialog.minimap_expanded_check.setChecked(False)
            dialog.snap_to_grid_check.setChecked(True)
            dialog.expand_collision_enabled_check.setChecked(False)
            dialog.expand_collision_radius_mode_combo.setCurrentIndex(
                dialog.expand_collision_radius_mode_combo.findData("unbounded")
            )
            dialog.expand_collision_local_radius_preset_combo.setCurrentIndex(
                dialog.expand_collision_local_radius_preset_combo.findData("large")
            )
            dialog.expand_collision_gap_preset_combo.setCurrentIndex(
                dialog.expand_collision_gap_preset_combo.findData("tight")
            )
            dialog.expand_collision_animate_check.setChecked(False)
            dialog.max_performance_mode_button.setChecked(True)
            dialog.tab_strip_density_combo.setCurrentIndex(dialog.tab_strip_density_combo.findData("regular"))
            dialog.theme_combo.setCurrentIndex(dialog.theme_combo.findData("stitch_light"))
            dialog.follow_shell_theme_check.setChecked(False)
            dialog.graph_theme_combo.setCurrentIndex(dialog.graph_theme_combo.findData("graph_stitch_light"))

            expected = copy.deepcopy(DEFAULT_GRAPHICS_SETTINGS)
            expected["canvas"]["show_grid"] = False
            expected["canvas"]["grid_style"] = "points"
            expected["canvas"]["edge_crossing_style"] = "gap_break"
            expected["canvas"]["show_minimap"] = False
            expected["canvas"]["show_port_labels"] = False
            expected["canvas"]["minimap_expanded"] = False
            expected["interaction"]["snap_to_grid"] = True
            expected["interaction"]["expand_collision_avoidance"] = {
                "enabled": False,
                "strategy": "nearest",
                "scope": "all_movable",
                "radius_mode": "unbounded",
                "local_radius_preset": "large",
                "gap_preset": "tight",
                "animate": False,
            }
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
                    "edge_crossing_style": "arc-weld",
                    "show_minimap": "no",
                    "show_port_labels": False,
                    "minimap_expanded": False,
                },
                "interaction": {
                    "snap_to_grid": True,
                    "expand_collision_avoidance": {
                        "enabled": "yes",
                        "strategy": "farthest",
                        "scope": "selection",
                        "radius_mode": "global",
                        "local_radius_preset": "tiny",
                        "gap_preset": "huge",
                        "animate": "yes",
                    },
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
            self.assertEqual(dialog.section_list.count(), 5)
            self.assertEqual(dialog.theme_combo.count(), 2)
            self.assertEqual(dialog.graph_theme_combo.count(), len(graph_theme_choices()))
            self.assertTrue(dialog.full_fidelity_mode_button.isChecked())
            self.assertFalse(dialog.max_performance_mode_button.isChecked())
            self.assertTrue(dialog.follow_shell_theme_check.isChecked())
            self.assertFalse(dialog.graph_theme_combo.isEnabled())
            self.assertTrue(dialog.expand_collision_enabled_check.isChecked())
            self.assertEqual(dialog.expand_collision_strategy_combo.currentData(), "nearest")
            self.assertEqual(dialog.expand_collision_scope_combo.currentData(), "all_movable")
            self.assertEqual(dialog.expand_collision_radius_mode_combo.currentData(), "local")
            self.assertEqual(dialog.expand_collision_local_radius_preset_combo.currentData(), "medium")
            self.assertEqual(dialog.expand_collision_gap_preset_combo.currentData(), "normal")
            self.assertTrue(dialog.expand_collision_animate_check.isChecked())
            self.assertFalse(dialog.show_port_labels_check.isChecked())
            self.assertEqual(dialog.grid_style_combo.currentData(), "lines")
            self.assertEqual(dialog.edge_crossing_style_combo.currentData(), "none")
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

    def test_grid_style_control_tracks_grid_visibility_and_roundtrips_selection(self) -> None:
        dialog = GraphicsSettingsDialog(
            initial_settings={
                "canvas": {
                    "show_grid": True,
                    "grid_style": "points",
                }
            }
        )
        try:
            self.assertTrue(dialog.show_grid_check.isChecked())
            self.assertFalse(dialog._grid_style_container.isHidden())
            self.assertEqual(dialog.grid_style_combo.objectName(), "graphicsSettingsGridStyleCombo")
            self.assertEqual(dialog.grid_style_combo.currentData(), "points")

            dialog.show_grid_check.setChecked(False)
            self.assertTrue(dialog._grid_style_container.isHidden())
            self.assertEqual(dialog.values()["canvas"]["grid_style"], "points")

            dialog.show_grid_check.setChecked(True)
            self.assertFalse(dialog._grid_style_container.isHidden())
        finally:
            dialog.close()

    def test_graph_typography_dialog_theme_page_spinbox_roundtrips_app_global_size(self) -> None:
        dialog = GraphicsSettingsDialog()
        try:
            self.assertEqual(
                dialog.graph_label_pixel_size_spin.objectName(),
                "graphicsSettingsGraphLabelPixelSizeSpin",
            )
            self.assertEqual(dialog.graph_label_pixel_size_spin.minimum(), 8)
            self.assertEqual(dialog.graph_label_pixel_size_spin.maximum(), 18)
            self.assertEqual(dialog.graph_label_pixel_size_spin.value(), 10)
            self.assertEqual(dialog.values()["typography"]["graph_label_pixel_size"], 10)

            dialog.graph_label_pixel_size_spin.setValue(16)

            values = dialog.values()
            self.assertEqual(values["typography"]["graph_label_pixel_size"], 16)
            self.assertEqual(values["theme"], DEFAULT_GRAPHICS_SETTINGS["theme"])
            self.assertEqual(values["graph_theme"], DEFAULT_GRAPHICS_SETTINGS["graph_theme"])
        finally:
            dialog.close()

    def test_graph_node_icon_size_dialog_defaults_to_automatic_graph_label_size(self) -> None:
        dialog = GraphicsSettingsDialog()
        try:
            self.assertEqual(
                dialog.graph_node_icon_size_override_check.objectName(),
                "graphicsSettingsGraphNodeIconSizeOverrideCheck",
            )
            self.assertEqual(
                dialog.graph_node_icon_pixel_size_spin.objectName(),
                "graphicsSettingsGraphNodeIconPixelSizeOverrideSpin",
            )
            self.assertFalse(dialog.graph_node_icon_size_override_check.isChecked())
            self.assertFalse(dialog.graph_node_icon_pixel_size_spin.isEnabled())
            self.assertEqual(dialog.graph_node_icon_pixel_size_spin.minimum(), 8)
            self.assertEqual(dialog.graph_node_icon_pixel_size_spin.maximum(), 18)
            self.assertEqual(dialog.graph_node_icon_pixel_size_spin.value(), 10)
            self.assertIsNone(dialog.values()["typography"]["graph_node_icon_pixel_size_override"])
        finally:
            dialog.close()

    def test_graph_node_icon_size_dialog_roundtrips_explicit_override(self) -> None:
        dialog = GraphicsSettingsDialog(
            initial_settings={
                "typography": {
                    "graph_label_pixel_size": 14,
                    "graph_node_icon_pixel_size_override": 17,
                }
            }
        )
        try:
            self.assertTrue(dialog.graph_node_icon_size_override_check.isChecked())
            self.assertTrue(dialog.graph_node_icon_pixel_size_spin.isEnabled())
            self.assertEqual(dialog.graph_label_pixel_size_spin.value(), 14)
            self.assertEqual(dialog.graph_node_icon_pixel_size_spin.value(), 17)

            dialog.graph_node_icon_pixel_size_spin.setValue(15)

            values = dialog.values()
            self.assertEqual(values["typography"]["graph_label_pixel_size"], 14)
            self.assertEqual(values["typography"]["graph_node_icon_pixel_size_override"], 15)
        finally:
            dialog.close()

    def test_graph_node_icon_size_dialog_can_disable_override_without_changing_label_size(self) -> None:
        dialog = GraphicsSettingsDialog(
            initial_settings={
                "typography": {
                    "graph_label_pixel_size": 16,
                    "graph_node_icon_pixel_size_override": 12,
                }
            }
        )
        try:
            dialog.graph_node_icon_size_override_check.setChecked(False)

            values = dialog.values()
            self.assertFalse(dialog.graph_node_icon_pixel_size_spin.isEnabled())
            self.assertEqual(values["typography"]["graph_label_pixel_size"], 16)
            self.assertIsNone(values["typography"]["graph_node_icon_pixel_size_override"])
        finally:
            dialog.close()

    def test_graph_node_icon_size_dialog_normalizes_invalid_and_clamped_initial_settings(self) -> None:
        cases = (
            ("boolean", True, False, 13, None),
            ("low", 2, True, 8, 8),
            ("high", 42, True, 18, 18),
        )

        for label, override, checked, spin_value, expected_override in cases:
            with self.subTest(case=label):
                dialog = GraphicsSettingsDialog(
                    initial_settings={
                        "typography": {
                            "graph_label_pixel_size": 13,
                            "graph_node_icon_pixel_size_override": override,
                        }
                    }
                )
                try:
                    self.assertEqual(dialog.graph_node_icon_size_override_check.isChecked(), checked)
                    self.assertEqual(dialog.graph_node_icon_pixel_size_spin.value(), spin_value)
                    self.assertEqual(
                        dialog.values()["typography"]["graph_node_icon_pixel_size_override"],
                        expected_override,
                    )
                finally:
                    dialog.close()

    def test_graph_typography_dialog_normalizes_missing_and_invalid_payloads(self) -> None:
        cases = (
            ("missing-block", {}, 10),
            ("invalid-block", {"typography": "large"}, 10),
            ("non-integer", {"typography": {"graph_label_pixel_size": "11"}}, 10),
            ("low", {"typography": {"graph_label_pixel_size": 4}}, 8),
            ("high", {"typography": {"graph_label_pixel_size": 24}}, 18),
        )

        for label, initial_settings, expected in cases:
            with self.subTest(case=label):
                dialog = GraphicsSettingsDialog(initial_settings=initial_settings)
                try:
                    self.assertEqual(dialog.graph_label_pixel_size_spin.value(), expected)
                    self.assertEqual(dialog.values()["typography"]["graph_label_pixel_size"], expected)
                finally:
                    dialog.close()


if __name__ == "__main__":
    unittest.main()
