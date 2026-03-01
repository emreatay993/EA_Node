from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from ea_node_editor.ui.main_window import MainWindow


class ScriptEditorDockRc2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self._session_path = Path(self._temp_dir.name) / "last_session.json"
        self._autosave_path = Path(self._temp_dir.name) / "autosave.sfe"
        self._session_patch = patch(
            "ea_node_editor.ui.main_window.recent_session_path",
            return_value=self._session_path,
        )
        self._autosave_patch = patch(
            "ea_node_editor.ui.main_window.autosave_project_path",
            return_value=self._autosave_path,
        )
        self._session_patch.start()
        self._autosave_patch.start()
        self.window = MainWindow()
        self.window.show()
        self.app.processEvents()

    def tearDown(self) -> None:
        self.window.close()
        self.app.processEvents()
        self._session_patch.stop()
        self._autosave_patch.stop()
        self._temp_dir.cleanup()

    def test_script_editor_binds_to_selected_python_script_node(self) -> None:
        script_node_id = self.window.scene.add_node_from_type("core.python_script", x=40.0, y=40.0)
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        workspace.nodes[script_node_id].properties["script"] = "output_data = 42"

        self.window.scene.focus_node(script_node_id)
        self.app.processEvents()

        self.window.toggle_script_editor()
        self.app.processEvents()
        self.assertEqual(self.window.script_editor_dock.current_node_id, script_node_id)
        self.assertIn("output_data = 42", self.window.script_editor_dock.editor.toPlainText())

        self.window.script_editor_dock.editor.setPlainText("output_data = input_data\nx = 7\n")
        self.window.script_editor_dock._apply()
        self.app.processEvents()
        self.assertEqual(workspace.nodes[script_node_id].properties["script"], "output_data = input_data\nx = 7\n")

    def test_script_editor_state_persists_in_metadata(self) -> None:
        self.assertFalse(self.window.model.project.metadata["ui"]["script_editor"]["visible"])
        self.window.toggle_script_editor()
        self.app.processEvents()
        self.assertTrue(self.window.model.project.metadata["ui"]["script_editor"]["visible"])
        self.window.toggle_script_editor(False)
        self.app.processEvents()
        self.assertFalse(self.window.model.project.metadata["ui"]["script_editor"]["visible"])


if __name__ == "__main__":
    unittest.main()

