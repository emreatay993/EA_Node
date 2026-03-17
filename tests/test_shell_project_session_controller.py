from __future__ import annotations

import gc
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtCore import QEvent, QUrl
from PyQt6.QtWidgets import QMessageBox

from ea_node_editor.ui.shell.window import ShellWindow
from tests.main_window_shell.base import MainWindowShellTestBase

_SCENARIO_ARG = "--scenario"
_PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _run_named_scenario(name: str) -> int:
    suite = unittest.TestSuite([_ShellProjectSessionControllerScenarios(name)])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


class _ShellProjectSessionControllerScenarios(MainWindowShellTestBase):
    __test__ = False

    def tearDown(self) -> None:
        app = self.app
        try:
            super().tearDown()
        finally:
            for widget in list(app.topLevelWidgets()):
                widget.close()
                widget.deleteLater()
            app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            app.processEvents()
            app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            app.processEvents()
            gc.collect()

    def _dispose_secondary_window(self, window: ShellWindow) -> None:
        for timer_name in ("metrics_timer", "graph_hint_timer", "autosave_timer"):
            timer = getattr(window, timer_name, None)
            if timer is not None:
                timer.stop()
        window.close()
        quick_widget = getattr(window, "quick_widget", None)
        if quick_widget is not None:
            window.takeCentralWidget()
            quick_widget.setSource(QUrl())
            quick_widget.hide()
            quick_widget.deleteLater()
            window.quick_widget = None
        window.deleteLater()
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.app.processEvents()

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

        restored = ShellWindow()
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
            self.assertAlmostEqual(restored.view.center_x, 222.0, delta=3.0)
            self.assertAlmostEqual(restored.view.center_y, -111.0, delta=3.0)
        finally:
            self._dispose_secondary_window(restored)

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

        with patch.object(ShellWindow, "_prompt_recover_autosave", return_value=QMessageBox.StandardButton.Yes):
            restored = ShellWindow()
            restored.resize(1200, 800)
            restored.show()
            self.app.processEvents()
            try:
                restored_workspace = restored.model.project.workspaces[workspace_id]
                self.assertIn(recovered_node_id, restored_workspace.nodes)
                self.assertFalse(self._autosave_path.exists())
            finally:
                self._dispose_secondary_window(restored)

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

        with patch.object(ShellWindow, "_prompt_recover_autosave", return_value=QMessageBox.StandardButton.No):
            restored = ShellWindow()
            restored.resize(1200, 800)
            restored.show()
            self.app.processEvents()
            try:
                restored_workspace = restored.model.project.workspaces[workspace_id]
                self.assertIn(baseline_node_id, restored_workspace.nodes)
                self.assertEqual(len(restored_workspace.nodes), 1)
                self.assertFalse(self._autosave_path.exists())
            finally:
                self._dispose_secondary_window(restored)

    def test_recovery_prompt_is_skipped_when_autosave_matches_restored_session(self) -> None:
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
        self._autosave_path.write_text(
            json.dumps(baseline_doc, indent=2, sort_keys=True, ensure_ascii=True),
            encoding="utf-8",
        )

        with patch.object(ShellWindow, "_prompt_recover_autosave") as prompt:
            restored = ShellWindow()
            restored.resize(1200, 800)
            restored.show()
            self.app.processEvents()
            try:
                self.assertEqual(prompt.call_count, 0)
                self.assertFalse(self._autosave_path.exists())
            finally:
                self._dispose_secondary_window(restored)

    def test_restore_session_handles_corrupted_session_and_autosave_files(self) -> None:
        self._session_path.write_text("{bad json", encoding="utf-8")
        self._autosave_path.write_text("{bad json", encoding="utf-8")
        os.utime(self._autosave_path, None)

        with patch.object(ShellWindow, "_prompt_recover_autosave", return_value=QMessageBox.StandardButton.Yes):
            restored = ShellWindow()
            restored.resize(1200, 800)
            restored.show()
            self.app.processEvents()
            try:
                self.assertGreaterEqual(len(restored.model.project.workspaces), 1)
                self.assertFalse(self._autosave_path.exists())
            finally:
                self._dispose_secondary_window(restored)

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

        with patch.object(ShellWindow, "_prompt_recover_autosave", return_value=QMessageBox.StandardButton.No) as prompt:
            restored = ShellWindow()
            self.assertEqual(prompt.call_count, 0)
            restored.resize(1200, 800)
            restored.show()
            self.app.processEvents()
            try:
                self.assertGreaterEqual(prompt.call_count, 1)
                self.assertFalse(self._autosave_path.exists())
            finally:
                self._dispose_secondary_window(restored)


class ShellProjectSessionControllerTests(unittest.TestCase):
    maxDiff = None

    def _run_scenario(self, scenario_name: str) -> None:
        env = os.environ.copy()
        env.setdefault("QT_QPA_PLATFORM", "offscreen")
        completed = subprocess.run(
            [sys.executable, "-m", "tests.test_shell_project_session_controller", _SCENARIO_ARG, scenario_name],
            cwd=_PROJECT_ROOT,
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        output = "\n".join(
            part
            for part in (completed.stdout.strip(), completed.stderr.strip())
            if part
        )
        self.assertEqual(
            completed.returncode,
            0,
            output or f"Scenario {scenario_name} failed without output.",
        )

    def test_session_restore_recovers_workspace_order_active_workspace_and_view_camera(self) -> None:
        self._run_scenario("test_session_restore_recovers_workspace_order_active_workspace_and_view_camera")

    def test_autosave_tick_writes_snapshot_and_keeps_valid_project_doc(self) -> None:
        self._run_scenario("test_autosave_tick_writes_snapshot_and_keeps_valid_project_doc")

    def test_recovery_prompt_accept_loads_newer_autosave(self) -> None:
        self._run_scenario("test_recovery_prompt_accept_loads_newer_autosave")

    def test_recovery_prompt_reject_keeps_session_state_and_discards_autosave(self) -> None:
        self._run_scenario("test_recovery_prompt_reject_keeps_session_state_and_discards_autosave")

    def test_recovery_prompt_is_skipped_when_autosave_matches_restored_session(self) -> None:
        self._run_scenario("test_recovery_prompt_is_skipped_when_autosave_matches_restored_session")

    def test_restore_session_handles_corrupted_session_and_autosave_files(self) -> None:
        self._run_scenario("test_restore_session_handles_corrupted_session_and_autosave_files")

    def test_recovery_prompt_is_deferred_until_main_window_is_visible(self) -> None:
        self._run_scenario("test_recovery_prompt_is_deferred_until_main_window_is_visible")


def load_tests(loader, _tests, _pattern):  # noqa: ANN001
    return loader.loadTestsFromTestCase(ShellProjectSessionControllerTests)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == _SCENARIO_ARG:
        raise SystemExit(_run_named_scenario(sys.argv[2]))
    unittest.main()
