from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from ea_node_editor.settings import DEFAULT_GRAPHICS_SETTINGS
from ea_node_editor.ui.dialogs.graphics_settings_dialog import GraphicsSettingsDialog
from ea_node_editor.ui.dialogs.sectioned_settings_dialog import SectionedSettingsDialog


class GraphicsSettingsDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_dialog_defaults_and_values_roundtrip(self) -> None:
        dialog = GraphicsSettingsDialog()
        try:
            self.assertIsInstance(dialog, SectionedSettingsDialog)
            self.assertEqual(dialog.values(), DEFAULT_GRAPHICS_SETTINGS)

            dialog.show_grid_check.setChecked(False)
            dialog.show_minimap_check.setChecked(False)
            dialog.minimap_expanded_check.setChecked(False)
            dialog.snap_to_grid_check.setChecked(True)
            dialog.theme_combo.setCurrentIndex(dialog.theme_combo.findData("stitch_light"))

            self.assertEqual(
                dialog.values(),
                {
                    "canvas": {
                        "show_grid": False,
                        "show_minimap": False,
                        "minimap_expanded": False,
                    },
                    "interaction": {
                        "snap_to_grid": True,
                    },
                    "theme": {
                        "theme_id": "stitch_light",
                    },
                },
            )
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
            }
        )
        try:
            self.assertEqual(dialog.section_list.count(), 3)
            self.assertEqual(dialog.theme_combo.count(), 2)
            self.assertEqual(
                dialog.values(),
                {
                    "canvas": {
                        "show_grid": False,
                        "show_minimap": True,
                        "minimap_expanded": False,
                    },
                    "interaction": {
                        "snap_to_grid": True,
                    },
                    "theme": {
                        "theme_id": "stitch_dark",
                    },
                },
            )
        finally:
            dialog.close()


if __name__ == "__main__":
    unittest.main()
