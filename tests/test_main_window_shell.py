from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QApplication, QMessageBox, QStatusBar, QToolBar

from ea_node_editor.app import APP_STYLESHEET
from ea_node_editor.ui.main_window import MainWindow


def _action_shortcuts(action) -> set[str]:  # noqa: ANN001
    return {
        sequence.toString(QKeySequence.SequenceFormat.PortableText)
        for sequence in action.shortcuts()
    }


class MainWindowShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyleSheet(APP_STYLESHEET)

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
        self.window.resize(1200, 800)
        self.window.show()
        self.app.processEvents()

    def tearDown(self) -> None:
        self.window.close()
        self.app.processEvents()
        self._session_patch.stop()
        self._autosave_patch.stop()
        self._temp_dir.cleanup()

    def test_shell_layout_zones_are_present(self) -> None:
        self.assertIsNotNone(self.window.menuBar())
        self.assertGreaterEqual(len(self.window.findChildren(QToolBar)), 1)
        self.assertIsInstance(self.window.statusBar(), QStatusBar)
        self.assertIsNotNone(self.window.node_library_panel)
        self.assertIsNotNone(self.window.view)
        self.assertIsNotNone(self.window.workspace_tabs)
        self.assertIsNotNone(self.window.console_panel)

        view_pos = self.window.view.mapTo(self.window, QPoint(0, 0))
        tabs_pos = self.window.workspace_tabs.mapTo(self.window, QPoint(0, 0))
        console_pos = self.window.console_panel.mapTo(self.window, QPoint(0, 0))
        self.assertGreater(tabs_pos.y(), view_pos.y())
        self.assertGreater(console_pos.y(), tabs_pos.y())

    def test_status_api_contract_updates_visible_values(self) -> None:
        self.window.set_engine_state("running", "Job #12")
        self.window.set_job_counts(2, 3, 4, 1)
        self.window.set_metrics(37.0, 4.3, 16.0)
        self.window.set_notification_counts(5, 2)
        self.app.processEvents()

        self.assertEqual(self.window.status_engine.icon(), "Run")
        self.assertEqual(self.window.status_engine.text(), "Running (Job #12)")
        self.assertEqual(self.window.status_jobs.text(), "R:2 Q:3 D:4 F:1")
        self.assertEqual(self.window.status_metrics.text(), "CPU:37% RAM:4.3/16.0 GB")
        self.assertEqual(self.window.status_notifications.text(), "W:5 E:2")

    def test_command_actions_and_workspace_shortcuts_are_wired(self) -> None:
        self.window.workspace_manager.create_workspace("Second")
        self.window._refresh_workspace_tabs()
        self.window.workspace_tabs.setCurrentIndex(0)
        self.app.processEvents()

        self.window.action_next_workspace.trigger()
        self.app.processEvents()
        self.assertEqual(self.window.workspace_tabs.currentIndex(), 1)

        self.window.action_prev_workspace.trigger()
        self.app.processEvents()
        self.assertEqual(self.window.workspace_tabs.currentIndex(), 0)

        self.assertIn("Ctrl+Tab", _action_shortcuts(self.window.action_next_workspace))
        self.assertIn("Ctrl+PgDown", _action_shortcuts(self.window.action_next_workspace))
        self.assertIn("Ctrl+Shift+Tab", _action_shortcuts(self.window.action_prev_workspace))
        self.assertIn("Ctrl+PgUp", _action_shortcuts(self.window.action_prev_workspace))

        with patch.object(self.window.execution_client, "start_run", return_value="run_test") as start_run:
            self.window.action_run.trigger()
            self.app.processEvents()
            start_run.assert_called_once()

        self.window._active_run_id = "run_test"
        with patch.object(self.window.execution_client, "stop_run") as stop_run:
            self.window.action_stop.trigger()
            self.app.processEvents()
            stop_run.assert_called_once_with("run_test")

        self.window._engine_state_value = "running"
        self.window._update_run_actions()
        with patch.object(self.window.execution_client, "pause_run") as pause_run:
            self.window.action_pause.trigger()
            self.app.processEvents()
            pause_run.assert_called_once_with("run_test")

        self.window._engine_state_value = "paused"
        self.window._update_run_actions()
        with patch.object(self.window.execution_client, "resume_run") as resume_run:
            self.window.action_pause.trigger()
            self.app.processEvents()
            resume_run.assert_called_once_with("run_test")

    def test_multi_view_and_workspace_switch_retains_independent_camera_state(self) -> None:
        first_workspace_id = self.window.workspace_manager.active_workspace_id()
        first_v1_id = self.window.model.project.workspaces[first_workspace_id].active_view_id

        self.window.view.set_zoom(1.4)
        self.window.view.centerOn(110.0, 210.0)
        self.app.processEvents()

        self.window._save_active_view_state()
        first_v2_id = self.window.workspace_manager.create_view(first_workspace_id, name="V2")
        self.window._restore_active_view_state()
        self.window._refresh_view_button()
        self.window.view.set_zoom(0.7)
        self.window.view.centerOn(-55.0, 75.0)
        first_node_id = self.window.scene.add_node_from_type("core.start", x=20.0, y=30.0)
        self.app.processEvents()

        second_workspace_id = self.window.workspace_manager.create_workspace("Second")
        self.window._refresh_workspace_tabs()
        self.window._switch_workspace(second_workspace_id)
        self.window.view.set_zoom(2.0)
        self.window.view.centerOn(400.0, -125.0)
        self.app.processEvents()

        self.window._switch_workspace(first_workspace_id)
        self.app.processEvents()
        self.assertEqual(
            self.window.model.project.workspaces[first_workspace_id].active_view_id,
            first_v2_id,
        )
        self.assertAlmostEqual(self.window.view.zoom, 0.7, places=2)
        center = self.window.view.mapToScene(self.window.view.viewport().rect().center())
        self.assertAlmostEqual(center.x(), -55.0, delta=5.0)
        self.assertAlmostEqual(center.y(), 75.0, delta=5.0)
        self.assertIn(first_node_id, self.window.model.project.workspaces[first_workspace_id].nodes)

        self.window._switch_view(first_v1_id)
        self.app.processEvents()
        self.assertAlmostEqual(self.window.view.zoom, 1.4, places=2)
        center = self.window.view.mapToScene(self.window.view.viewport().rect().center())
        self.assertAlmostEqual(center.x(), 110.0, delta=5.0)
        self.assertAlmostEqual(center.y(), 210.0, delta=5.0)

    def test_closing_dirty_workspace_honors_unsaved_warning(self) -> None:
        first_workspace_id = self.window.workspace_manager.active_workspace_id()
        self.window.workspace_manager.create_workspace("Second")
        self.window._refresh_workspace_tabs()
        self.window._switch_workspace(first_workspace_id)
        self.window.scene.add_node_from_type("core.start", x=0.0, y=0.0)
        self.app.processEvents()

        first_index = -1
        for index in range(self.window.workspace_tabs.count()):
            if self.window.workspace_tabs.tabData(index) == first_workspace_id:
                first_index = index
                break
        self.assertGreaterEqual(first_index, 0)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            self.window._on_workspace_tab_close(first_index)
        self.assertIn(first_workspace_id, self.window.model.project.workspaces)

        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            self.window._on_workspace_tab_close(first_index)
        self.assertNotIn(first_workspace_id, self.window.model.project.workspaces)

    def test_session_restore_recovers_workspace_order_active_workspace_and_view_camera(self) -> None:
        first_workspace_id = self.window.workspace_manager.active_workspace_id()
        second_workspace_id = self.window.workspace_manager.create_workspace("Second")
        third_workspace_id = self.window.workspace_manager.create_workspace("Third")
        self.window.workspace_manager.move_workspace(2, 1)
        self.window._refresh_workspace_tabs()

        self.window._switch_workspace(third_workspace_id)
        third_v2_id = self.window.workspace_manager.create_view(third_workspace_id, name="V2")
        self.window._switch_view(third_v2_id)
        self.window.view.set_zoom(1.65)
        self.window.view.centerOn(222.0, -111.0)
        self.window._persist_session()
        self.app.processEvents()

        expected_order = [
            self.window.workspace_tabs.tabData(index)
            for index in range(self.window.workspace_tabs.count())
        ]
        self.assertEqual(expected_order, [first_workspace_id, third_workspace_id, second_workspace_id])

        restored = MainWindow()
        restored.resize(1200, 800)
        restored.show()
        self.app.processEvents()
        try:
            restored_order = [
                restored.workspace_tabs.tabData(index)
                for index in range(restored.workspace_tabs.count())
            ]
            self.assertEqual(restored_order, expected_order)
            self.assertEqual(restored.workspace_manager.active_workspace_id(), third_workspace_id)
            self.assertEqual(
                restored.model.project.workspaces[third_workspace_id].active_view_id,
                third_v2_id,
            )
            self.assertAlmostEqual(restored.view.zoom, 1.65, places=2)
            center = restored.view.mapToScene(restored.view.viewport().rect().center())
            self.assertAlmostEqual(center.x(), 222.0, delta=3.0)
            self.assertAlmostEqual(center.y(), -111.0, delta=3.0)
        finally:
            restored.close()
            self.app.processEvents()

    def test_autosave_tick_writes_snapshot_and_keeps_valid_project_doc(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("core.start", x=5.0, y=7.0)
        self.app.processEvents()

        self.window._autosave_tick()
        self.assertTrue(self._autosave_path.exists())

        autosave_doc = json.loads(self._autosave_path.read_text(encoding="utf-8"))
        workspace_docs = {
            workspace["workspace_id"]: workspace for workspace in autosave_doc.get("workspaces", [])
        }
        self.assertIn(workspace_id, workspace_docs)
        saved_nodes = {node["node_id"] for node in workspace_docs[workspace_id].get("nodes", [])}
        self.assertIn(node_id, saved_nodes)

    def test_node_library_add_uses_selected_item_when_current_row_is_unset(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        baseline_count = len(workspace.nodes)

        panel = self.window.node_library_panel
        target_item = None
        for index in range(panel.list_widget.count()):
            candidate = panel.list_widget.item(index)
            if candidate is not None and candidate.text() == "[Core] Start":
                target_item = candidate
                break
        self.assertIsNotNone(target_item)
        if target_item is None:
            self.fail("Expected [Core] Start item in node library list.")

        panel.list_widget.clearSelection()
        panel.list_widget.setCurrentRow(-1)
        target_item.setSelected(True)
        panel._on_add_clicked()
        self.app.processEvents()

        workspace_after = self.window.model.project.workspaces[workspace_id]
        self.assertEqual(len(workspace_after.nodes), baseline_count + 1)

    def test_recovery_prompt_accept_loads_newer_autosave(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        baseline_doc = self.window.serializer.to_document(self.window.model.project)
        self._session_path.write_text(
            json.dumps(
                {
                    "project_path": "",
                    "last_manual_save_ts": 0.0,
                    "project_doc": baseline_doc,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        recovered_node_id = self.window.scene.add_node_from_type("core.start", x=20.0, y=30.0)
        recovered_doc = self.window.serializer.to_document(self.window.model.project)
        self._autosave_path.write_text(
            json.dumps(recovered_doc, indent=2, sort_keys=True, ensure_ascii=True),
            encoding="utf-8",
        )

        with patch.object(MainWindow, "_prompt_recover_autosave", return_value=QMessageBox.StandardButton.Yes):
            restored = MainWindow()
            restored.resize(1200, 800)
            restored.show()
            self.app.processEvents()
            try:
                restored_workspace = restored.model.project.workspaces[workspace_id]
                self.assertIn(recovered_node_id, restored_workspace.nodes)
                self.assertFalse(self._autosave_path.exists())
            finally:
                restored.close()
                self.app.processEvents()

    def test_recovery_prompt_reject_keeps_session_state_and_discards_autosave(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        baseline_node_id = self.window.scene.add_node_from_type("core.start", x=10.0, y=10.0)
        baseline_doc = self.window.serializer.to_document(self.window.model.project)
        self._session_path.write_text(
            json.dumps(
                {
                    "project_path": "",
                    "last_manual_save_ts": 0.0,
                    "project_doc": baseline_doc,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        self.window.scene.add_node_from_type("core.logger", x=120.0, y=10.0)
        autosave_doc = self.window.serializer.to_document(self.window.model.project)
        self._autosave_path.write_text(
            json.dumps(autosave_doc, indent=2, sort_keys=True, ensure_ascii=True),
            encoding="utf-8",
        )

        with patch.object(MainWindow, "_prompt_recover_autosave", return_value=QMessageBox.StandardButton.No):
            restored = MainWindow()
            restored.resize(1200, 800)
            restored.show()
            self.app.processEvents()
            try:
                restored_workspace = restored.model.project.workspaces[workspace_id]
                self.assertIn(baseline_node_id, restored_workspace.nodes)
                self.assertEqual(len(restored_workspace.nodes), 1)
                self.assertFalse(self._autosave_path.exists())
            finally:
                restored.close()
                self.app.processEvents()

    def test_restore_session_handles_corrupted_session_and_autosave_files(self) -> None:
        self._session_path.write_text("{bad json", encoding="utf-8")
        self._autosave_path.write_text("{bad json", encoding="utf-8")
        os.utime(self._autosave_path, None)

        with patch.object(MainWindow, "_prompt_recover_autosave", return_value=QMessageBox.StandardButton.Yes):
            restored = MainWindow()
            restored.resize(1200, 800)
            restored.show()
            self.app.processEvents()
            try:
                self.assertGreaterEqual(len(restored.model.project.workspaces), 1)
                self.assertFalse(self._autosave_path.exists())
            finally:
                restored.close()
                self.app.processEvents()

    def test_recovery_prompt_is_deferred_until_main_window_is_visible(self) -> None:
        baseline_doc = self.window.serializer.to_document(self.window.model.project)
        self._session_path.write_text(
            json.dumps(
                {
                    "project_path": "",
                    "last_manual_save_ts": 0.0,
                    "project_doc": baseline_doc,
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

        self.window.scene.add_node_from_type("core.start", x=20.0, y=30.0)
        recovered_doc = self.window.serializer.to_document(self.window.model.project)
        self._autosave_path.write_text(
            json.dumps(recovered_doc, indent=2, sort_keys=True, ensure_ascii=True),
            encoding="utf-8",
        )

        with patch.object(MainWindow, "_prompt_recover_autosave", return_value=QMessageBox.StandardButton.No) as prompt:
            restored = MainWindow()
            self.assertEqual(prompt.call_count, 0)
            restored.resize(1200, 800)
            restored.show()
            self.app.processEvents()
            try:
                self.assertGreaterEqual(prompt.call_count, 1)
                self.assertFalse(self._autosave_path.exists())
            finally:
                restored.close()
                self.app.processEvents()

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

        output_text = self.window.console_panel.output.toPlainText()
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

        center = self.window.view.mapToScene(self.window.view.viewport().rect().center())
        self.assertAlmostEqual(center.x(), expected_center.x(), delta=8.0)
        self.assertAlmostEqual(center.y(), expected_center.y(), delta=8.0)
        self.assertEqual(self.window.scene.selected_node_id(), failed_node_id)

        errors_text = self.window.console_panel.errors.toPlainText()
        self.assertIn("RuntimeError: boom", errors_text)
        self.assertIn("traceback: line 1", errors_text)
        critical.assert_called_once()
        critical_args = critical.call_args.args
        self.assertEqual(critical_args[1], "Workflow Error")
        self.assertEqual(critical_args[2], "RuntimeError: boom")


if __name__ == "__main__":
    unittest.main()
