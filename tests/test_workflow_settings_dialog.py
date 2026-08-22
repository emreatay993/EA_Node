from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication, QDialog, QWidget

from ea_node_editor.execution.managed_runtime import (
    ManagedRuntimeInstallResult,
    ManagedRuntimeStatus,
)
from ea_node_editor.settings import DEFAULT_WORKFLOW_SETTINGS, SCHEMA_VERSION
from ea_node_editor.ui.dialogs.workflow_settings_dialog import WorkflowSettingsDialog
from ea_node_editor.ui.shell.window import ShellWindow
from ea_node_editor.ui.shell.tooltip_policy import (
    TOOLTIP_CATEGORY_INACTIVE,
    TOOLTIP_CATEGORY_TUTORIAL,
    TOOLTIP_CATEGORY_WARNING,
)
from ea_node_editor.ui.shell.tooltip_manager import TooltipManager


class WorkflowSettingsDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QApplication.instance() or QApplication([])

    def _wait_until(self, predicate, *, timeout_ms: int = 3000) -> bool:  # noqa: ANN001
        import time

        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            QApplication.instance().processEvents()
            if predicate():
                return True
            time.sleep(0.01)
        return False

    def test_dialog_defaults_and_values_roundtrip(self) -> None:
        dialog = WorkflowSettingsDialog()
        try:
            values = dialog.values()
            self.assertEqual(values["solver_config"]["thread_count"], DEFAULT_WORKFLOW_SETTINGS["solver_config"]["thread_count"])
            dialog.project_name_edit.setText("PumpFlow")
            dialog.author_edit.setText("Engineer A")
            dialog.parallel_check.setChecked(False)
            dialog.python_path_edit.setText(r" C:\tools\python.exe ")
            values = dialog.values()
            self.assertEqual(values["general"]["project_name"], "PumpFlow")
            self.assertEqual(values["general"]["author"], "Engineer A")
            self.assertFalse(values["solver_config"]["enable_parallel"])
            self.assertEqual(values["environment"]["python_path"], r"C:\tools\python.exe")
            self.assertEqual(dialog.prepare_runtime_button.objectName(), "prepareCorexRuntimeButton")
            self.assertEqual(dialog.use_builtin_runtime_button.objectName(), "useBuiltInRuntimeButton")
            self.assertEqual(
                dialog.managed_runtime_status_label.objectName(),
                "managedRuntimeStatusLabel",
            )
            self.assertEqual(dialog.prepare_runtime_button.text(), "Create / Repair Managed Runtime")
            self.assertEqual(
                dialog.prepare_runtime_button.property("tooltip_category"),
                TOOLTIP_CATEGORY_TUTORIAL,
            )
            self.assertEqual(
                dialog.use_builtin_runtime_button.property("tooltip_category"),
                TOOLTIP_CATEGORY_TUTORIAL,
            )
            self.assertEqual(
                dialog.python_path_edit.property("tooltip_category"),
                TOOLTIP_CATEGORY_TUTORIAL,
            )
            self.assertEqual(
                dialog.managed_runtime_status_label.property("tooltip_category"),
                TOOLTIP_CATEGORY_INACTIVE,
            )
            self.assertEqual(dialog.workdir_edit.property("tooltip_category"), TOOLTIP_CATEGORY_WARNING)
            self.assertIn("Creates or repairs", dialog.prepare_runtime_button.toolTip())
            self.assertIn("built-in packaged COREX runtime", dialog.use_builtin_runtime_button.toolTip())
            self.assertIn("Leave empty", dialog.python_path_edit.toolTip())
            self.assertIn("does not enforce", dialog.workdir_edit.toolTip())
            dialog.use_builtin_runtime_button.click()
            self.assertEqual(dialog.values()["environment"]["python_path"], "")
        finally:
            dialog.close()

    def test_runtime_tooltips_follow_parent_category_preferences(self) -> None:
        parent = QWidget()
        parent.tooltip_manager = TooltipManager(  # type: ignore[attr-defined]
            tooltip_categories={
                TOOLTIP_CATEGORY_TUTORIAL: False,
                TOOLTIP_CATEGORY_WARNING: True,
                TOOLTIP_CATEGORY_INACTIVE: True,
            }
        )

        dialog = WorkflowSettingsDialog(parent=parent)
        try:
            self.assertEqual(dialog.prepare_runtime_button.toolTip(), "")
            self.assertEqual(dialog.use_builtin_runtime_button.toolTip(), "")
            self.assertEqual(dialog.python_path_edit.toolTip(), "")
            self.assertIn("does not enforce", dialog.workdir_edit.toolTip())
            self.assertIn("app-managed workflow runtime", dialog.managed_runtime_status_label.toolTip())
        finally:
            dialog.close()
            parent.close()

    def test_prepare_managed_runtime_success_sets_python_executable(self) -> None:
        runtime_python = r"C:\Users\tester\AppData\Roaming\COREX_Node_Editor\runtimes\default\Scripts\python.exe"

        def prepare_runtime() -> ManagedRuntimeInstallResult:
            return ManagedRuntimeInstallResult(
                success=True,
                python_executable=runtime_python,
                status=ManagedRuntimeStatus(
                    python_executable=runtime_python,
                    verified=True,
                    exists=True,
                ),
            )

        dialog = WorkflowSettingsDialog(managed_runtime_prepare=prepare_runtime)
        try:
            dialog.python_path_edit.setText(r"C:\old\python.exe")
            dialog.prepare_runtime_button.click()

            self.assertTrue(
                self._wait_until(
                    lambda: dialog.python_path_edit.text() == runtime_python
                    and dialog.prepare_runtime_button.isEnabled()
                    and dialog._managed_runtime_thread is None
                )
            )
            self.assertEqual(dialog.values()["environment"]["python_path"], runtime_python)
        finally:
            dialog.close()

    def test_prepare_managed_runtime_failure_preserves_python_executable(self) -> None:
        def prepare_runtime() -> ManagedRuntimeInstallResult:
            return ManagedRuntimeInstallResult(
                success=False,
                error="Could not find Python 3.10 or newer.",
            )

        dialog = WorkflowSettingsDialog(managed_runtime_prepare=prepare_runtime)
        try:
            dialog.python_path_edit.setText(r"C:\old\python.exe")
            dialog.prepare_runtime_button.click()

            self.assertTrue(
                self._wait_until(
                    lambda: "Could not find Python 3.10" in dialog.managed_runtime_status_label.text()
                    and dialog.prepare_runtime_button.isEnabled()
                    and dialog._managed_runtime_thread is None
                )
            )
            self.assertEqual(dialog.values()["environment"]["python_path"], r"C:\old\python.exe")
        finally:
            dialog.close()

    def test_show_workflow_settings_dialog_updates_project_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            session_path = Path(temp_dir) / "last_session.json"
            autosave_path = Path(temp_dir) / "autosave.cxproj"
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
                                "python_path": r"C:\tools\python.exe",
                                "working_directory": "",
                            },
                            "plugins": {"enabled": ["plugin.alpha"]},
                            "logging": {"level": "debug", "capture_console": True},
                        },
                    ):
                        window.show_workflow_settings_dialog()
                    settings = window.model.project.metadata["workflow_settings"]
                    self.assertEqual(settings["solver_config"]["thread_count"], 12)
                    self.assertEqual(settings["environment"]["python_path"], r"C:\tools\python.exe")
                    self.assertEqual(settings["plugins"]["enabled"], ["plugin.alpha"])
                    document = window.serializer.to_document(window.model.project)
                    self.assertEqual(document["schema_version"], SCHEMA_VERSION)
                    self.assertIn("workflow_settings", document["metadata"])
                finally:
                    window.close()
                    QApplication.instance().processEvents()


if __name__ == "__main__":
    unittest.main()
