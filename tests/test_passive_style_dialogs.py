from __future__ import annotations

import unittest
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication, QLineEdit, QMessageBox

from ea_node_editor.ui.dialogs.flow_edge_style_dialog import FlowEdgeStyleDialog
from ea_node_editor.ui.dialogs.passive_node_style_dialog import PassiveNodeStyleDialog


class PassiveNodeStyleDialogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = QApplication.instance() or QApplication([])

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
                "ignored": True,
            }
        )
        try:
            self.assertEqual(dialog.findChild(QLineEdit, "fill_color_value").text(), "#112233")
            self.assertEqual(dialog.findChild(QLineEdit, "border_width_value").text(), "2.5")
            self.assertEqual(dialog.findChild(QLineEdit, "corner_radius_value").text(), "14")
            self.assertEqual(dialog.findChild(QLineEdit, "font_size_value").text(), "16")
            self.assertEqual(dialog.font_weight_combo.currentData(), "bold")

            dialog.findChild(QLineEdit, "accent_color_value").setText("")
            dialog.findChild(QLineEdit, "corner_radius_value").setText("18")
            dialog.findChild(QLineEdit, "font_size_value").setText("13")
            dialog.font_weight_combo.setCurrentIndex(dialog.font_weight_combo.findData("normal"))

            self.assertEqual(
                dialog.node_style(),
                {
                    "fill_color": "#112233",
                    "border_color": "#445566",
                    "text_color": "#778899",
                    "header_color": "#010203",
                    "border_width": 2.5,
                    "corner_radius": 18.0,
                    "font_size": 13,
                    "font_weight": "normal",
                },
            )
        finally:
            dialog.close()

    def test_invalid_passive_node_values_block_accept_until_fixed(self) -> None:
        dialog = PassiveNodeStyleDialog(initial_style={})
        try:
            dialog.findChild(QLineEdit, "fill_color_value").setText("#12345")
            dialog.findChild(QLineEdit, "border_width_value").setText("0")

            with patch.object(QMessageBox, "warning", return_value=QMessageBox.StandardButton.Ok) as warning:
                dialog.apply_button.click()

            warning.assert_called_once()
            self.assertNotEqual(dialog.result(), dialog.DialogCode.Accepted)
            self.assertFalse(dialog.validation_message.isHidden())

            dialog.findChild(QLineEdit, "fill_color_value").setText("#123456")
            dialog.findChild(QLineEdit, "border_width_value").setText("1.5")
            dialog.apply_button.click()

            self.assertEqual(dialog.result(), dialog.DialogCode.Accepted)
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

            dialog.findChild(QLineEdit, "label_background_color_value").setText("")
            dialog.stroke_pattern_combo.setCurrentIndex(dialog.stroke_pattern_combo.findData("dotted"))

            self.assertEqual(
                dialog.edge_style(),
                {
                    "stroke_color": "#224466",
                    "stroke_width": 3.5,
                    "stroke_pattern": "dotted",
                    "arrow_head": "open",
                    "label_text_color": "#F0F4FB",
                },
            )
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


if __name__ == "__main__":
    unittest.main()
