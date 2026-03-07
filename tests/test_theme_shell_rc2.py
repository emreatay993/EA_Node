from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from ea_node_editor.app import APP_STYLESHEET
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
        self._session_patch = patch(
            "ea_node_editor.ui.shell.window.recent_session_path",
            return_value=self._session_path,
        )
        self._autosave_patch = patch(
            "ea_node_editor.ui.shell.window.autosave_project_path",
            return_value=self._autosave_path,
        )
        self._session_patch.start()
        self._autosave_patch.start()
        self.window = ShellWindow()
        self.window.resize(1200, 800)
        self.window.show()
        self.app.processEvents()

    def tearDown(self) -> None:
        self.window.close()
        self.app.processEvents()
        self._session_patch.stop()
        self._autosave_patch.stop()
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


if __name__ == "__main__":
    unittest.main()
