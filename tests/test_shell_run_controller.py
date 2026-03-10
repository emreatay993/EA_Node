from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QMessageBox

from ea_node_editor.app import APP_STYLESHEET
from ea_node_editor.ui.shell.window import ShellWindow


class ShellRunControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyleSheet(APP_STYLESHEET)

    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self._session_path = Path(self._temp_dir.name) / "last_session.json"
        self._autosave_path = Path(self._temp_dir.name) / "autosave.sfe"
        self._global_custom_workflows_path = Path(self._temp_dir.name) / "custom_workflows_global.json"
        self._session_patch = patch(
            "ea_node_editor.ui.shell.window.recent_session_path",
            return_value=self._session_path,
        )
        self._autosave_patch = patch(
            "ea_node_editor.ui.shell.window.autosave_project_path",
            return_value=self._autosave_path,
        )
        self._global_custom_workflows_patch = patch(
            "ea_node_editor.custom_workflows.global_store.global_custom_workflows_path",
            return_value=self._global_custom_workflows_path,
        )
        self._session_patch.start()
        self._autosave_patch.start()
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
        self._global_custom_workflows_patch.stop()
        self._temp_dir.cleanup()

    def test_stream_log_events_are_scoped_to_active_run(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        self.window._active_run_id = "run_live"
        self.window._active_run_workspace_id = workspace_id
        self.window._set_run_ui_state("running", "Running", 1, 0, 0, 0)

        self.window.execution_event.emit(
            {
                "type": "log",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": "node_stream",
                "level": "info",
                "message": "[stdout] tick_ui_0",
            }
        )
        self.window.execution_event.emit(
            {
                "type": "log",
                "run_id": "run_live",
                "workspace_id": workspace_id,
                "node_id": "node_stream",
                "level": "info",
                "message": "[stderr] warn_ui_0",
            }
        )
        self.window.execution_event.emit(
            {
                "type": "log",
                "run_id": "run_stale",
                "workspace_id": workspace_id,
                "node_id": "node_stream",
                "level": "info",
                "message": "[stdout] should_not_appear",
            }
        )
        self.app.processEvents()

        output_text = self.window.console_panel.output_text
        self.assertIn("[stdout] tick_ui_0", output_text)
        self.assertIn("[stderr] warn_ui_0", output_text)
        self.assertNotIn("should_not_appear", output_text)
        self.assertEqual(self.window._engine_state_value, "running")

    def test_stale_run_events_do_not_mutate_active_run_ui(self) -> None:
        self.window._active_run_id = "run_live"
        self.window._set_run_ui_state("running", "Running", 1, 0, 0, 0)
        initial_error_count = self.window.console_panel.error_count

        self.window.execution_event.emit(
            {
                "type": "run_failed",
                "run_id": "run_stale",
                "workspace_id": self.window.workspace_manager.active_workspace_id(),
                "node_id": "",
                "error": "stale failure",
                "traceback": "traceback",
            }
        )
        self.app.processEvents()

        self.assertEqual(self.window._active_run_id, "run_live")
        self.assertEqual(self.window._engine_state_value, "running")
        self.assertEqual(self.window.status_jobs.text(), "R:1 Q:0 D:0 F:0")
        self.assertEqual(self.window.console_panel.error_count, initial_error_count)

    def test_failure_focus_reveals_parent_chain_when_present(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]

        parent_id = self.window.scene.add_node_from_type("core.start", x=0.0, y=0.0)
        child_id = self.window.scene.add_node_from_type("core.logger", x=140.0, y=0.0)
        workspace.nodes[child_id].parent_node_id = parent_id
        self.window.scene.set_node_collapsed(parent_id, True)
        self.assertTrue(workspace.nodes[parent_id].collapsed)

        with patch.object(QMessageBox, "critical") as critical:
            self.window._focus_failed_node(workspace_id, child_id, "boom")

        self.app.processEvents()
        self.assertFalse(workspace.nodes[parent_id].collapsed)
        self.assertEqual(self.window.scene.selected_node_id(), child_id)
        critical.assert_called_once()

    def test_run_failed_event_centers_failed_node_and_reports_exception_details(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        failed_node_id = self.window.scene.add_node_from_type("core.python_script", x=860.0, y=640.0)
        node_item = self.window.scene.node_item(failed_node_id)
        self.assertIsNotNone(node_item)
        if node_item is None:
            self.fail("Expected failed node item to exist")
        expected_center = node_item.sceneBoundingRect().center()

        self.window._active_run_id = "run_live"
        self.window._active_run_workspace_id = workspace_id
        self.window._set_run_ui_state("running", "Running", 1, 0, 0, 0)

        with patch.object(QMessageBox, "critical") as critical:
            self.window.execution_event.emit(
                {
                    "type": "run_failed",
                    "run_id": "run_live",
                    "workspace_id": workspace_id,
                    "node_id": failed_node_id,
                    "error": "RuntimeError: boom",
                    "traceback": "traceback: line 1",
                }
            )
            self.app.processEvents()

        self.assertAlmostEqual(self.window.view.center_x, expected_center.x(), delta=8.0)
        self.assertAlmostEqual(self.window.view.center_y, expected_center.y(), delta=8.0)
        self.assertEqual(self.window.scene.selected_node_id(), failed_node_id)

        errors_text = self.window.console_panel.errors_text
        self.assertIn("RuntimeError: boom", errors_text)
        self.assertIn("traceback: line 1", errors_text)
        critical.assert_called_once()
        critical_args = critical.call_args.args
        self.assertEqual(critical_args[1], "Workflow Error")
        self.assertEqual(critical_args[2], "RuntimeError: boom")


if __name__ == "__main__":
    unittest.main()
