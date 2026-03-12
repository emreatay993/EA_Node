from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QDialog

from ea_node_editor.app import APP_STYLESHEET
from ea_node_editor.ui.dialogs.graphics_settings_dialog import GraphicsSettingsDialog
from ea_node_editor.ui.shell.window import ShellWindow


class ThemeShellRc2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyleSheet(APP_STYLESHEET)

    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self._session_path = Path(self._temp_dir.name) / "last_session.json"
        self._autosave_path = Path(self._temp_dir.name) / "autosave.sfe"
        self._app_preferences_path = Path(self._temp_dir.name) / "app_preferences.json"
        self._global_custom_workflows_path = Path(self._temp_dir.name) / "custom_workflows_global.json"
        self._session_patch = patch(
            "ea_node_editor.ui.shell.window.recent_session_path",
            return_value=self._session_path,
        )
        self._autosave_patch = patch(
            "ea_node_editor.ui.shell.window.autosave_project_path",
            return_value=self._autosave_path,
        )
        self._app_preferences_patch = patch(
            "ea_node_editor.ui.shell.controllers.app_preferences_controller.app_preferences_path",
            return_value=self._app_preferences_path,
        )
        self._global_custom_workflows_patch = patch(
            "ea_node_editor.custom_workflows.global_store.global_custom_workflows_path",
            return_value=self._global_custom_workflows_path,
        )
        self._session_patch.start()
        self._autosave_patch.start()
        self._app_preferences_patch.start()
        self._global_custom_workflows_patch.start()
        self.window = ShellWindow()
        self.window.resize(1200, 800)
        self.window.show()
        self.app.processEvents()

    def tearDown(self) -> None:
        self.window.close()
        self.app.processEvents()
        self._session_patch.stop()
        self._autosave_patch.stop()
        self._app_preferences_patch.stop()
        self._global_custom_workflows_patch.stop()
        self._temp_dir.cleanup()

    def test_stylesheet_is_generated_from_stitch_tokens(self) -> None:
        self.assertIn("#60CDFF", APP_STYLESHEET)
        self.assertIn("QStatusBar#mainStatusBar", APP_STYLESHEET)
        self.assertIn("QDockWidget::title", APP_STYLESHEET)

    def test_script_editor_action_is_wired_in_qml_shell(self) -> None:
        self.assertFalse(self.window.script_editor.visible)
        self.window.action_toggle_script_editor.trigger()
        self.app.processEvents()
        self.assertTrue(self.window.script_editor.visible)
        self.assertTrue(self.window.action_toggle_script_editor.isChecked())
        metadata = self.window.model.project.metadata
        self.assertTrue(metadata["ui"]["script_editor"]["visible"])

    def test_workflow_settings_action_exists(self) -> None:
        self.assertIsNotNone(self.window.action_workflow_settings)
        self.assertEqual(self.window.action_workflow_settings.text(), "Workflow Settings")

    def test_graphics_settings_action_persists_preferences_and_updates_shell_state(self) -> None:
        self.assertIsNotNone(self.window.action_graphics_settings)
        self.assertEqual(self.window.action_graphics_settings.text(), "Graphics Settings")
        self.assertEqual(len(self.window.action_graphics_settings.shortcuts()), 0)

        updated_graphics = {
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
        }

        with patch.object(GraphicsSettingsDialog, "exec", return_value=QDialog.DialogCode.Accepted), patch.object(
            GraphicsSettingsDialog,
            "values",
            return_value=updated_graphics,
        ):
            self.window.show_graphics_settings_dialog()
        self.app.processEvents()

        self.assertFalse(self.window.graphics_show_grid)
        self.assertFalse(self.window.graphics_show_minimap)
        self.assertFalse(self.window.graphics_minimap_expanded)
        self.assertTrue(self.window.snap_to_grid_enabled)
        self.assertTrue(self.window.action_snap_to_grid.isChecked())
        self.assertEqual(self.window.active_theme_id, "stitch_light")

        persisted = json.loads(self._app_preferences_path.read_text(encoding="utf-8"))
        self.assertEqual(persisted["graphics"], updated_graphics)


if __name__ == "__main__":
    unittest.main()
