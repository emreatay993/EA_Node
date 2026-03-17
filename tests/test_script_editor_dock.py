from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

from tests.main_window_shell.base import MainWindowShellTestBase

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SHELL_TEST_RUNNER = (
    "import sys, unittest; "
    "target = sys.argv[1]; "
    "suite = unittest.defaultTestLoader.loadTestsFromName(target); "
    "result = unittest.TextTestRunner(verbosity=2).run(suite); "
    "sys.exit(0 if result.wasSuccessful() else 1)"
)


class ScriptEditorDockTests(MainWindowShellTestBase):
    def test_script_editor_binds_to_selected_python_script_node(self) -> None:
        script_node_id = self.window.scene.add_node_from_type("core.python_script", x=40.0, y=40.0)
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        workspace.nodes[script_node_id].properties["script"] = "output_data = 42"

        self.window.scene.focus_node(script_node_id)
        self.app.processEvents()

        self.window.set_script_editor_panel_visible(True)
        self.app.processEvents()
        self.assertEqual(self.window.script_editor.current_node_id, script_node_id)
        self.assertEqual(self.window.script_editor.current_node_label, workspace.nodes[script_node_id].title)
        self.assertNotIn(script_node_id, self.window.script_editor.current_node_label)
        self.assertIn("output_data = 42", self.window.script_editor.script_text)

        self.window.script_editor.set_script_text("output_data = input_data\nx = 7\n")
        self.window.script_editor.apply()
        self.app.processEvents()
        self.assertEqual(workspace.nodes[script_node_id].properties["script"], "output_data = input_data\nx = 7\n")

    def test_script_editor_state_persists_in_metadata(self) -> None:
        self.assertFalse(self.window.model.project.metadata["ui"]["script_editor"]["visible"])
        self.window.set_script_editor_panel_visible(True)
        self.app.processEvents()
        self.assertTrue(self.window.model.project.metadata["ui"]["script_editor"]["visible"])
        self.window.set_script_editor_panel_visible(False)
        self.app.processEvents()
        self.assertFalse(self.window.model.project.metadata["ui"]["script_editor"]["visible"])

    def test_script_editor_exposes_cursor_diagnostics_and_dirty_state(self) -> None:
        script_node_id = self.window.scene.add_node_from_type("core.python_script", x=40.0, y=40.0)
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        workspace.nodes[script_node_id].properties["script"] = "alpha = 1\nbeta = 2\n"

        self.window.scene.focus_node(script_node_id)
        self.window.set_script_editor_panel_visible(True)
        self.app.processEvents()

        self.window.script_editor.set_script_text("alpha = 123\nbeta = 2\n")
        self.window.script_editor.set_cursor_metrics(1, 6, 5, 5)
        self.app.processEvents()

        self.assertTrue(self.window.script_editor.dirty)
        self.assertIn("Ln 1, Col 6", self.window.script_editor.cursor_label)
        self.assertIn("Sel 5", self.window.script_editor.cursor_label)
        self.assertIn("Pos 5", self.window.script_editor.cursor_label)

    def test_set_script_editor_panel_visible_focuses_editor_for_script_node(self) -> None:
        script_node_id = self.window.scene.add_node_from_type("core.python_script", x=40.0, y=40.0)
        self.window.scene.focus_node(script_node_id)
        self.app.processEvents()

        self.window.set_script_editor_panel_visible(True)
        self.app.processEvents()

        self.assertTrue(self.window.script_editor.has_focus)


class _SubprocessShellWindowTest(unittest.TestCase):
    __test__ = False

    def __init__(self, target: str) -> None:
        super().__init__(methodName="runTest")
        self._target = target

    def id(self) -> str:
        return self._target

    def __str__(self) -> str:
        return self._target

    def shortDescription(self) -> str:
        return self._target

    def runTest(self) -> None:
        env = os.environ.copy()
        env.setdefault("QT_QPA_PLATFORM", "offscreen")
        result = subprocess.run(
            [sys.executable, "-c", _SHELL_TEST_RUNNER, self._target],
            cwd=_REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return
        output = "\n".join(
            part.strip()
            for part in (result.stdout, result.stderr)
            if part and part.strip()
        )
        self.fail(
            f"Subprocess shell test failed for {self._target} "
            f"(exit={result.returncode}).\n{output}"
        )


def load_tests(loader: unittest.TestLoader, _tests, _pattern):  # noqa: ANN001
    suite = unittest.TestSuite()
    for test_name in loader.getTestCaseNames(ScriptEditorDockTests):
        target = f"{ScriptEditorDockTests.__module__}.{ScriptEditorDockTests.__qualname__}.{test_name}"
        suite.addTest(_SubprocessShellWindowTest(target))
    return suite


if __name__ == "__main__":
    unittest.main()
