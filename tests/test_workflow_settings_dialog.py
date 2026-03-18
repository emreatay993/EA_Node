from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication, QDialog

from ea_node_editor.settings import DEFAULT_WORKFLOW_SETTINGS, SCHEMA_VERSION
from ea_node_editor.ui.dialogs.workflow_settings_dialog import WorkflowSettingsDialog
from ea_node_editor.ui.shell.window import ShellWindow


class WorkflowSettingsDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def test_dialog_defaults_and_values_roundtrip(self) -> None:
        dialog = WorkflowSettingsDialog()
        try:
            values = dialog.values()
            self.assertEqual(values["solver_config"]["thread_count"], DEFAULT_WORKFLOW_SETTINGS["solver_config"]["thread_count"])
            dialog.project_name_edit.setText("PumpFlow")
            dialog.author_edit.setText("Engineer A")
            dialog.parallel_check.setChecked(False)
            values = dialog.values()
            self.assertEqual(values["general"]["project_name"], "PumpFlow")
            self.assertEqual(values["general"]["author"], "Engineer A")
            self.assertFalse(values["solver_config"]["enable_parallel"])
        finally:
            dialog.close()

    def test_show_workflow_settings_dialog_updates_project_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            session_path = Path(temp_dir) / "last_session.json"
            autosave_path = Path(temp_dir) / "autosave.sfe"
            app_preferences_path = Path(temp_dir) / "app_preferences.json"
            global_custom_workflows_path = Path(temp_dir) / "custom_workflows_global.json"
            with patch("ea_node_editor.ui.shell.window.recent_session_path", return_value=session_path), patch(
                "ea_node_editor.ui.shell.window.autosave_project_path",
                return_value=autosave_path,
            ), patch(
                "ea_node_editor.ui.shell.controllers.app_preferences_controller.app_preferences_path",
                return_value=app_preferences_path,
            ), patch(
                "ea_node_editor.custom_workflows.global_store.global_custom_workflows_path",
                return_value=global_custom_workflows_path,
            ):
                window = ShellWindow()
                window.show()
                QApplication.instance().processEvents()
                try:
                    with patch.object(
                        WorkflowSettingsDialog,
                        "exec",
                        return_value=QDialog.DialogCode.Accepted,
                    ), patch.object(
                        WorkflowSettingsDialog,
                        "values",
                        return_value={
                            "general": {
                                "project_name": "Workflow QA",
                                "author": "QA",
                                "description": "",
                            },
                            "solver_config": {
                                "enable_parallel": True,
                                "thread_count": 12,
                                "memory_limit_gb": 24,
                            },
                            "environment": {
                                "python_path": "",
                                "working_directory": "",
                            },
                            "plugins": {"enabled": ["plugin.alpha"]},
                            "logging": {"level": "debug", "capture_console": True},
                        },
                    ):
                        window.show_workflow_settings_dialog()
                    settings = window.model.project.metadata["workflow_settings"]
                    self.assertEqual(settings["solver_config"]["thread_count"], 12)
                    self.assertEqual(settings["plugins"]["enabled"], ["plugin.alpha"])
                    document = window.serializer.to_document(window.model.project)
                    self.assertEqual(document["schema_version"], SCHEMA_VERSION)
                    self.assertIn("workflow_settings", document["metadata"])
                finally:
                    window.close()
                    QApplication.instance().processEvents()


if __name__ == "__main__":
    unittest.main()
