from __future__ import annotations

import colorsys
import unittest
from unittest.mock import patch

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QComboBox, QLineEdit, QMessageBox, QWidget

from ea_node_editor.ui.dialogs.passive_style_controls import color_to_hex
from ea_node_editor.ui.dialogs.flow_edge_style_dialog import FlowEdgeStyleDialog
from ea_node_editor.ui.dialogs.passive_node_style_dialog import (
    PassiveNodeStyleDialog,
    _cie_lightness,
    _suggested_gradient_color,
)
from ea_node_editor.ui.passive_style_presets import built_in_style_presets


def _hex_rgb(value: str) -> tuple[float, float, float]:
    digits = value.lstrip("#")[-6:]
    return tuple(int(digits[index : index + 2], 16) / 255.0 for index in (0, 2, 4))


class PassiveNodeStyleDialogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = QApplication.instance() or QApplication([])

    def test_color_serialization_preserves_uppercase_rgb_and_argb_formats(self) -> None:
        rgb = QColor("#aa5500")
        argb = QColor("#336699")
        argb.setAlpha(0x80)

        self.assertEqual(color_to_hex(rgb), "#AA5500")
        self.assertEqual(color_to_hex(argb), "#80336699")

    def test_dialog_loads_and_saves_normalized_passive_node_style(self) -> None:
        dialog = PassiveNodeStyleDialog(
            initial_style={
                "fill_color": "#112233",
                "border_color": "#445566",
                "text_color": "#778899",
                "accent_color": "#AA5500",
                "header_color": "#010203",
                "border_width": 2.5,
                "corner_radius": 14,
                "font_size": 16,
                "font_weight": "bold",
                "gradient_enabled": True,
                "gradient_color": "#223344",
                "gradient_direction": "east",
                "header_gradient_enabled": False,
                "header_gradient_color": "#AABBCC",
                "header_gradient_direction": "west",
                "ignored": True,
            }
        )
        try:
            self.assertEqual(dialog.findChild(QLineEdit, "fill_color_value").text(), "#112233")
            self.assertEqual(dialog.findChild(QLineEdit, "border_width_value").text(), "2.5")
            self.assertEqual(dialog.findChild(QLineEdit, "corner_radius_value").text(), "14")
            self.assertEqual(dialog.findChild(QLineEdit, "font_size_value").text(), "16")
            self.assertEqual(dialog.font_weight_combo.currentData(), "bold")
            self.assertEqual(dialog.findChild(QComboBox, "gradient_mode_value").currentData(), "custom")
            self.assertEqual(dialog.findChild(QLineEdit, "gradient_color_value").text(), "#223344")
            self.assertEqual(dialog.findChild(QComboBox, "gradient_direction_value").currentData(), "east")
            self.assertIsNone(dialog.findChild(QLineEdit, "accent_color_value"))
            self.assertIsNone(dialog.findChild(QLineEdit, "header_color_value"))
            self.assertIsNone(dialog.findChild(QComboBox, "header_gradient_mode_value"))
            self.assertIsNone(dialog.findChild(QLineEdit, "header_gradient_color_value"))
            self.assertIsNone(dialog.findChild(QComboBox, "header_gradient_direction_value"))

            dialog.findChild(QLineEdit, "corner_radius_value").setText("18")
            dialog.findChild(QLineEdit, "font_size_value").setText("13")
            dialog.font_weight_combo.setCurrentIndex(dialog.font_weight_combo.findData("normal"))
            dialog.findChild(QLineEdit, "gradient_color_value").setText("#334455")
            direction_combo = dialog.findChild(QComboBox, "gradient_direction_value")
            direction_combo.setCurrentIndex(direction_combo.findData("radial"))

            self.assertEqual(
                dialog.node_style(),
                {
                    "fill_color": "#112233",
                    "border_color": "#445566",
                    "text_color": "#778899",
                    "border_width": 2.5,
                    "corner_radius": 18.0,
                    "font_size": 13,
                    "font_weight": "normal",
                    "gradient_enabled": True,
                    "gradient_color": "#334455",
                    "gradient_direction": "radial",
                },
            )
        finally:
            dialog.close()

    def test_invalid_passive_node_values_block_accept_until_fixed(self) -> None:
        dialog = PassiveNodeStyleDialog(initial_style={})
        try:
            dialog.findChild(QLineEdit, "fill_color_value").setText("#12345")
            dialog.findChild(QLineEdit, "border_width_value").setText("0")
            gradient_mode = dialog.findChild(QComboBox, "gradient_mode_value")
            gradient_mode.setCurrentIndex(gradient_mode.findData("custom"))

            with patch.object(QMessageBox, "warning", return_value=QMessageBox.StandardButton.Ok) as warning:
                dialog.apply_button.click()

            warning.assert_called_once()
            self.assertNotEqual(dialog.result(), dialog.DialogCode.Accepted)
            self.assertFalse(dialog.validation_message.isHidden())

            dialog.findChild(QLineEdit, "fill_color_value").setText("#123456")
            dialog.findChild(QLineEdit, "border_width_value").setText("1.5")
            dialog.findChild(QLineEdit, "gradient_color_value").setText("#654321")
            dialog.apply_button.click()

            self.assertEqual(dialog.result(), dialog.DialogCode.Accepted)
        finally:
            dialog.close()

    def test_clicking_passive_node_color_swatch_opens_picker_and_updates_value(self) -> None:
        dialog = PassiveNodeStyleDialog(initial_style={})
        try:
            swatch = dialog.findChild(QWidget, "fill_color_swatch")
            field = dialog.findChild(QLineEdit, "fill_color_value")

            self.assertIsNotNone(swatch)
            self.assertIsNotNone(field)

            with patch(
                "ea_node_editor.ui.dialogs.passive_style_controls.QColorDialog.getColor",
                return_value=QColor("#AA5500"),
            ) as get_color:
                QTest.mouseClick(swatch, Qt.MouseButton.LeftButton)
                self.app.processEvents()

            get_color.assert_called_once()
            self.assertEqual(field.text(), "#AA5500")
        finally:
            dialog.close()

    def test_dialog_reselects_matching_node_preset_on_reopen(self) -> None:
        dialog = PassiveNodeStyleDialog(
            initial_style={"fill_color": "#203040"},
            user_presets=[
                {
                    "preset_id": "node_preset_deadbeef",
                    "name": "Project Custom",
                    "style": {"fill_color": "#203040"},
                }
            ],
        )
        try:
            self.assertEqual(dialog.preset_combo.currentText(), "Project: Project Custom")
        finally:
            dialog.close()

    def test_applying_starter_presets_in_turn_loads_exactly_each_style(self) -> None:
        dialog = PassiveNodeStyleDialog(initial_style={"fill_color": "#203040", "corner_radius": 30, "font_size": 16})
        try:
            built_ins = built_in_style_presets("node")
            # Walk forward and back so corner radius, border width, and font size never leak between presets.
            for entry in [*built_ins, *reversed(built_ins)]:
                with self.subTest(preset=entry["name"]):
                    dialog.preset_combo.setCurrentIndex(dialog.preset_combo.findData(entry["preset_id"]))
                    dialog.apply_preset_button.click()

                    self.assertEqual(dialog.node_style(), entry["style"])
                    self.assertEqual(dialog.preset_combo.currentData(), entry["preset_id"])
        finally:
            dialog.close()

    def test_switching_gradient_to_custom_suggests_a_darker_shade_of_the_fill(self) -> None:
        dialog = PassiveNodeStyleDialog(initial_style={"fill_color": "#EFF5F1"})
        try:
            gradient_mode = dialog.findChild(QComboBox, "gradient_mode_value")
            gradient_color = dialog.findChild(QLineEdit, "gradient_color_value")

            gradient_mode.setCurrentIndex(gradient_mode.findData("custom"))

            self.assertEqual(gradient_color.text(), "#C0D7C7")
            self.assertEqual(
                dialog.node_style(),
                {
                    "fill_color": "#EFF5F1",
                    "gradient_enabled": True,
                    "gradient_color": "#C0D7C7",
                    "gradient_direction": "south",
                },
            )

            gradient_color.setText("#445566")
            gradient_mode.setCurrentIndex(gradient_mode.findData("off"))
            gradient_mode.setCurrentIndex(gradient_mode.findData("custom"))
            self.assertEqual(gradient_color.text(), "#445566")

            gradient_mode.setCurrentIndex(gradient_mode.findData("inherit"))
            gradient_color.setText("")
            dialog.findChild(QLineEdit, "fill_color_value").setText("")
            gradient_mode.setCurrentIndex(gradient_mode.findData("custom"))
            self.assertEqual(gradient_color.text(), "")
        finally:
            dialog.close()

    def test_suggested_gradient_color_keeps_hue_and_alpha(self) -> None:
        self.assertEqual(_suggested_gradient_color("#FFFFFF"), "#DDDDDD")
        self.assertEqual(_suggested_gradient_color("#2b3037"), "#15171A")
        self.assertEqual(_suggested_gradient_color("#80EFF5F1"), "#80C0D7C7")
        self.assertEqual(_suggested_gradient_color("#000000"), "#000000")

    def test_suggested_gradient_color_is_an_even_perceptual_step_for_every_starter(self) -> None:
        # Pale tints and dark cards should both get the same visible depth, and keep their hue.
        for entry in built_in_style_presets("node"):
            fill = entry["style"]["fill_color"]
            end = _suggested_gradient_color(fill)
            with self.subTest(preset=entry["name"], fill=fill, end=end):
                fill_rgb = _hex_rgb(fill)
                end_rgb = _hex_rgb(end)
                self.assertAlmostEqual(_cie_lightness(fill_rgb) - _cie_lightness(end_rgb), 12.0, delta=0.5)
                fill_hue = colorsys.rgb_to_hls(*fill_rgb)[0]
                end_hue = colorsys.rgb_to_hls(*end_rgb)[0]
                if colorsys.rgb_to_hls(*fill_rgb)[2] > 0.05:
                    self.assertAlmostEqual(fill_hue, end_hue, delta=0.02)

    def test_dialog_supports_project_local_node_preset_crud_with_read_only_starters(self) -> None:
        dialog = PassiveNodeStyleDialog(
            initial_style={"fill_color": "#102030"},
            user_presets=[
                {
                    "preset_id": "node_preset_deadbeef",
                    "name": "Project Custom",
                    "style": {"fill_color": "#203040"},
                }
            ],
        )
        try:
            self.assertGreaterEqual(dialog.preset_combo.count(), 4)
            self.assertEqual(dialog.preset_combo.currentText(), "Current Style")
            self.assertEqual(dialog.preset_combo.itemText(1).startswith("Starter:"), True)
            self.assertFalse(dialog.overwrite_preset_button.isEnabled())
            self.assertFalse(dialog.rename_preset_button.isEnabled())
            self.assertFalse(dialog.delete_preset_button.isEnabled())

            dialog.findChild(QLineEdit, "fill_color_value").setText("#334455")
            gradient_mode = dialog.findChild(QComboBox, "gradient_mode_value")
            gradient_mode.setCurrentIndex(gradient_mode.findData("custom"))
            dialog.findChild(QLineEdit, "gradient_color_value").setText("#445566")
            with patch("PyQt6.QtWidgets.QInputDialog.getText", return_value=("Review Theme", True)):
                dialog.save_preset_button.click()

            user_presets = dialog.user_presets()
            self.assertEqual(len(user_presets), 2)
            self.assertRegex(user_presets[1]["preset_id"], r"^node_preset_[0-9a-f]{8}$")
            self.assertEqual(user_presets[1]["name"], "Review Theme")
            self.assertEqual(
                user_presets[1]["style"],
                {
                    "fill_color": "#334455",
                    "gradient_enabled": True,
                    "gradient_color": "#445566",
                    "gradient_direction": "south",
                },
            )

            dialog.preset_combo.setCurrentIndex(dialog.preset_combo.findText("Project: Project Custom"))
            dialog.findChild(QLineEdit, "border_color_value").setText("#556677")
            self.assertEqual(dialog.preset_combo.currentText(), "Current Style")
            dialog.preset_combo.setCurrentIndex(dialog.preset_combo.findText("Project: Project Custom"))
            dialog.overwrite_preset_button.click()

            self.assertEqual(
                dialog.user_presets()[0]["style"],
                {
                    "fill_color": "#334455",
                    "border_color": "#556677",
                    "gradient_enabled": True,
                    "gradient_color": "#445566",
                    "gradient_direction": "south",
                },
            )

            with patch("PyQt6.QtWidgets.QInputDialog.getText", return_value=("Project Renamed", True)):
                dialog.rename_preset_button.click()
            self.assertEqual(dialog.user_presets()[0]["name"], "Project Renamed")

            with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
                dialog.delete_preset_button.click()

            self.assertEqual(
                dialog.user_presets(),
                [
                    {
                        "preset_id": user_presets[1]["preset_id"],
                        "name": "Review Theme",
                        "style": {
                            "fill_color": "#334455",
                            "gradient_enabled": True,
                            "gradient_color": "#445566",
                            "gradient_direction": "south",
                        },
                    }
                ],
            )
        finally:
            dialog.close()


class FlowEdgeStyleDialogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = QApplication.instance() or QApplication([])

    def test_dialog_loads_and_saves_normalized_flow_edge_style(self) -> None:
        dialog = FlowEdgeStyleDialog(
            initial_style={
                "stroke_color": "#224466",
                "stroke_width": 3.5,
                "stroke_pattern": "dashed",
                "arrow_head": "open",
                "path_mode": "pipe",
                "label_text_color": "#F0F4FB",
                "label_background_color": "#223344",
                "ignored": "value",
            }
        )
        try:
            self.assertEqual(dialog.findChild(QLineEdit, "stroke_color_value").text(), "#224466")
            self.assertEqual(dialog.findChild(QLineEdit, "stroke_width_value").text(), "3.5")
            self.assertEqual(dialog.stroke_pattern_combo.currentData(), "dashed")
            self.assertEqual(dialog.arrow_head_combo.currentData(), "open")
            self.assertEqual(dialog.path_mode_combo.currentData(), "pipe")

            dialog.findChild(QLineEdit, "label_background_color_value").setText("")
            dialog.stroke_pattern_combo.setCurrentIndex(dialog.stroke_pattern_combo.findData("dotted"))

            self.assertEqual(
                dialog.edge_style(),
                {
                    "stroke_color": "#224466",
                    "stroke_width": 3.5,
                    "stroke_pattern": "dotted",
                    "arrow_head": "open",
                    "path_mode": "pipe",
                    "label_text_color": "#F0F4FB",
                },
            )
        finally:
            dialog.close()

    def test_dialog_edits_arrow_ends_and_label_layout(self) -> None:
        dialog = FlowEdgeStyleDialog(
            initial_style={
                "arrow_tail": "open",
                "arrow_head": "none",
                "label_position": 0.375,
                "label_orientation": "follow_path",
            }
        )
        try:
            self.assertEqual(dialog.arrow_tail_combo.currentData(), "open")
            self.assertEqual(dialog.arrow_head_combo.currentData(), "none")
            self.assertEqual(
                [dialog.arrow_tail_combo.itemData(index) for index in range(dialog.arrow_tail_combo.count())],
                ["", "filled", "open", "none"],
            )
            self.assertEqual(dialog.findChild(QLineEdit, "label_position_value").text(), "37.5")
            self.assertEqual(dialog.label_orientation_combo.currentData(), "follow_path")

            dialog.arrow_tail_combo.setCurrentIndex(dialog.arrow_tail_combo.findData("filled"))
            dialog.arrow_head_combo.setCurrentIndex(dialog.arrow_head_combo.findData("filled"))
            dialog.findChild(QLineEdit, "label_position_value").setText("80")
            dialog.label_orientation_combo.setCurrentIndex(dialog.label_orientation_combo.findData(""))
            self.assertEqual(
                dialog.edge_style(),
                {"arrow_head": "filled", "arrow_tail": "filled", "label_position": 0.8},
            )
            # Blank means automatic placement.
            dialog.findChild(QLineEdit, "label_position_value").setText("")
            self.assertNotIn("label_position", dialog.edge_style())
        finally:
            dialog.close()

    def test_applying_an_edge_preset_keeps_the_edges_label_position(self) -> None:
        dialog = FlowEdgeStyleDialog(
            initial_style={"stroke_color": "#102030", "label_position": 0.2},
            user_presets=[
                {
                    "preset_id": "edge_preset_deadbeef",
                    "name": "Project Edge",
                    "style": {"stroke_color": "#203040", "label_position": 0.9},
                }
            ],
        )
        try:
            # Presets store appearance only; a saved label position never enters them.
            self.assertEqual(dialog.user_presets()[0]["style"], {"stroke_color": "#203040"})
            dialog.preset_combo.setCurrentIndex(dialog.preset_combo.findText("Project: Project Edge"))
            dialog.apply_preset_button.click()
            self.assertEqual(dialog.edge_style(), {"stroke_color": "#203040", "label_position": 0.2})
            # The per-edge placement does not stop the style matching its preset.
            self.assertEqual(dialog.preset_combo.currentText(), "Project: Project Edge")
            with patch("PyQt6.QtWidgets.QInputDialog.getText", return_value=("Placed", True)):
                dialog.save_preset_button.click()
            self.assertEqual(dialog.user_presets()[-1]["style"], {"stroke_color": "#203040"})
        finally:
            dialog.close()

    def test_label_position_outside_zero_to_hundred_blocks_accept(self) -> None:
        dialog = FlowEdgeStyleDialog(initial_style={})
        try:
            dialog.findChild(QLineEdit, "label_position_value").setText("150")
            with patch.object(QMessageBox, "warning", return_value=QMessageBox.StandardButton.Ok) as warning:
                dialog.apply_button.click()
            warning.assert_called_once()
            self.assertNotEqual(dialog.result(), dialog.DialogCode.Accepted)
            self.assertFalse(dialog.validation_message.isHidden())
            dialog.findChild(QLineEdit, "label_position_value").setText("50")
            dialog.apply_button.click()
            self.assertEqual(dialog.result(), dialog.DialogCode.Accepted)
            self.assertEqual(dialog.edge_style(), {"label_position": 0.5})
        finally:
            dialog.close()

    def test_invalid_flow_edge_values_block_accept_until_fixed(self) -> None:
        dialog = FlowEdgeStyleDialog(initial_style={})
        try:
            dialog.findChild(QLineEdit, "stroke_color_value").setText("#xyzxyz")
            dialog.findChild(QLineEdit, "stroke_width_value").setText("0")

            with patch.object(QMessageBox, "warning", return_value=QMessageBox.StandardButton.Ok) as warning:
                dialog.apply_button.click()

            warning.assert_called_once()
            self.assertNotEqual(dialog.result(), dialog.DialogCode.Accepted)
            self.assertFalse(dialog.validation_message.isHidden())

            dialog.findChild(QLineEdit, "stroke_color_value").setText("#224466")
            dialog.findChild(QLineEdit, "stroke_width_value").setText("2")
            dialog.apply_button.click()

            self.assertEqual(dialog.result(), dialog.DialogCode.Accepted)
        finally:
            dialog.close()

    def test_clicking_flow_edge_color_swatch_opens_picker_and_updates_value(self) -> None:
        dialog = FlowEdgeStyleDialog(initial_style={})
        try:
            swatch = dialog.findChild(QWidget, "stroke_color_swatch")
            field = dialog.findChild(QLineEdit, "stroke_color_value")

            self.assertIsNotNone(swatch)
            self.assertIsNotNone(field)

            with patch(
                "ea_node_editor.ui.dialogs.passive_style_controls.QColorDialog.getColor",
                return_value=QColor("#224466"),
            ) as get_color:
                QTest.mouseClick(swatch, Qt.MouseButton.LeftButton)
                self.app.processEvents()

            get_color.assert_called_once()
            self.assertEqual(field.text(), "#224466")
        finally:
            dialog.close()

    def test_dialog_reselects_matching_edge_preset_on_reopen(self) -> None:
        dialog = FlowEdgeStyleDialog(
            initial_style={"stroke_color": "#203040"},
            user_presets=[
                {
                    "preset_id": "edge_preset_deadbeef",
                    "name": "Project Edge",
                    "style": {"stroke_color": "#203040"},
                }
            ],
        )
        try:
            self.assertEqual(dialog.preset_combo.currentText(), "Project: Project Edge")
        finally:
            dialog.close()

    def test_applying_edge_preset_without_stroke_width_clears_the_field(self) -> None:
        dialog = FlowEdgeStyleDialog(
            initial_style={"stroke_color": "#102030", "stroke_width": 4},
            user_presets=[
                {
                    "preset_id": "edge_preset_deadbeef",
                    "name": "Project Edge",
                    "style": {"stroke_color": "#203040"},
                }
            ],
        )
        try:
            dialog.preset_combo.setCurrentIndex(dialog.preset_combo.findText("Project: Project Edge"))
            dialog.apply_preset_button.click()

            self.assertEqual(dialog.findChild(QLineEdit, "stroke_width_value").text(), "")
            self.assertEqual(dialog.edge_style(), {"stroke_color": "#203040"})
            self.assertEqual(dialog.preset_combo.currentText(), "Project: Project Edge")
        finally:
            dialog.close()

    def test_dialog_supports_project_local_edge_preset_crud_with_read_only_starters(self) -> None:
        dialog = FlowEdgeStyleDialog(
            initial_style={"stroke_color": "#102030"},
            user_presets=[
                {
                    "preset_id": "edge_preset_deadbeef",
                    "name": "Project Edge",
                    "style": {"stroke_color": "#203040"},
                }
            ],
        )
        try:
            self.assertGreaterEqual(dialog.preset_combo.count(), 4)
            self.assertEqual(dialog.preset_combo.currentText(), "Current Style")
            self.assertEqual(dialog.preset_combo.itemText(1).startswith("Starter:"), True)
            self.assertFalse(dialog.overwrite_preset_button.isEnabled())
            self.assertFalse(dialog.rename_preset_button.isEnabled())
            self.assertFalse(dialog.delete_preset_button.isEnabled())

            dialog.findChild(QLineEdit, "stroke_color_value").setText("#445566")
            with patch("PyQt6.QtWidgets.QInputDialog.getText", return_value=("Connector Link", True)):
                dialog.save_preset_button.click()

            user_presets = dialog.user_presets()
            self.assertEqual(len(user_presets), 2)
            self.assertRegex(user_presets[1]["preset_id"], r"^edge_preset_[0-9a-f]{8}$")
            self.assertEqual(user_presets[1]["name"], "Connector Link")
            self.assertEqual(user_presets[1]["style"], {"stroke_color": "#445566"})

            dialog.preset_combo.setCurrentIndex(dialog.preset_combo.findText("Project: Project Edge"))
            dialog.findChild(QLineEdit, "stroke_width_value").setText("2.5")
            self.assertEqual(dialog.preset_combo.currentText(), "Current Style")
            dialog.preset_combo.setCurrentIndex(dialog.preset_combo.findText("Project: Project Edge"))
            dialog.overwrite_preset_button.click()
            self.assertEqual(
                dialog.user_presets()[0]["style"],
                {
                    "stroke_color": "#445566",
                    "stroke_width": 2.5,
                },
            )

            with patch("PyQt6.QtWidgets.QInputDialog.getText", return_value=("Edge Renamed", True)):
                dialog.rename_preset_button.click()
            self.assertEqual(dialog.user_presets()[0]["name"], "Edge Renamed")

            with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
                dialog.delete_preset_button.click()

            self.assertEqual(
                dialog.user_presets(),
                [
                    {
                        "preset_id": user_presets[1]["preset_id"],
                        "name": "Connector Link",
                        "style": {"stroke_color": "#445566"},
                    }
                ],
            )
        finally:
            dialog.close()


if __name__ == "__main__":
    unittest.main()
