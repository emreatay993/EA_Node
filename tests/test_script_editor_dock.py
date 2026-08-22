from __future__ import annotations

import sys
from types import SimpleNamespace
import unittest
from unittest import mock

from ea_node_editor.ui_qml.script_editor_model import ScriptEditorModel
from tests.main_window_shell.base import MainWindowShellTestBase
from tests.shell_isolation_runtime import format_child_output
from tests.shell_isolation_runtime import run_shell_isolation_target
from tests.shell_isolation_runtime import ShellIsolationTarget
from tests.shell_isolation_runtime import ShellIsolationTargetTimeout

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
        workspace.nodes[script_node_id].properties["script"] = "result = 42"

        self.window.scene.focus_node(script_node_id)
        self.app.processEvents()

        self.window.set_script_editor_panel_visible(True)
        self.app.processEvents()
        self.assertEqual(self.window.script_editor.current_node_id, script_node_id)
        self.assertEqual(self.window.script_editor.current_node_label, workspace.nodes[script_node_id].title)
        self.assertNotIn(script_node_id, self.window.script_editor.current_node_label)
        self.assertIn("result = 42", self.window.script_editor.script_text)

        self.window.script_editor.set_script_text("result = payload\nx = 7\n")
        self.assertTrue(self.window.script_editor.apply())
        self.app.processEvents()
        self.assertEqual(workspace.nodes[script_node_id].properties["script"], "result = payload\nx = 7\n")
        self.assertFalse(self.window.script_editor.dirty)

    def test_script_apply_failure_keeps_draft_dirty(self) -> None:
        editor = ScriptEditorModel()
        editor.set_node(
            SimpleNamespace(
                node_id="node_script",
                type_id="core.python_script",
                title="Script",
                properties={"script": "result = payload"},
            )
        )
        editor.set_script_text("result = payload + 1")

        self.assertFalse(editor.apply())
        self.assertTrue(editor.dirty)
        self.assertEqual(editor.script_text, "result = payload + 1")

    def test_script_draft_survives_same_node_dynamic_port_refresh(self) -> None:
        script_node_id = self.window.scene.add_node_from_type(
            "core.python_script",
            x=40.0,
            y=40.0,
        )
        self.window.scene.focus_node(script_node_id)
        self.window.set_script_editor_panel_visible(True)
        self.app.processEvents()
        self.window.script_editor.set_script_text("result = payload + 1")

        with mock.patch.object(
            self.window.script_editor,
            "set_node",
            wraps=self.window.script_editor.set_node,
        ) as set_node:
            new_port_key = self.window.scene.insert_dynamic_port(
                script_node_id,
                "inputs",
                1,
            )
            self.app.processEvents()

        self.assertTrue(new_port_key)
        set_node.assert_not_called()
        self.assertTrue(self.window.script_editor.dirty)
        self.assertEqual(self.window.script_editor.script_text, "result = payload + 1")

    def test_script_editor_state_persists_in_metadata(self) -> None:
        self.assertFalse(self.window.model.project.metadata["ui"]["script_editor"]["visible"])
        self.window.set_script_editor_panel_visible(True)
        self.app.processEvents()
        self.assertTrue(self.window.model.project.metadata["ui"]["script_editor"]["visible"])
        self.window.set_script_editor_panel_visible(False)
        self.app.processEvents()
        self.assertFalse(self.window.model.project.metadata["ui"]["script_editor"]["visible"])

    def test_script_editor_panel_width_persists_in_metadata(self) -> None:
        self.assertEqual(self.window.model.project.metadata["ui"]["script_editor"]["width"], 0.0)
        self.window.script_editor.set_width(640.0)
        self.app.processEvents()
        self.assertEqual(self.window.script_editor.panel_width, 640.0)
        self.assertEqual(self.window.model.project.metadata["ui"]["script_editor"]["width"], 0.0)

        self.window.project_session_controller.persist_script_editor_state()
        self.assertEqual(self.window.model.project.metadata["ui"]["script_editor"]["width"], 640.0)

        # Negative widths fall back to "unset" so the panel uses its responsive default.
        self.window.script_editor.set_width(-25.0)
        self.app.processEvents()
        self.assertEqual(self.window.script_editor.panel_width, 0.0)

        self.window.project_session_controller.persist_script_editor_state()
        self.assertEqual(self.window.model.project.metadata["ui"]["script_editor"]["width"], 0.0)

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
        target = ShellIsolationTarget(
            target_id=self._target,
            command=(sys.executable, "-c", _SHELL_TEST_RUNNER, self._target),
        )
        try:
            result = run_shell_isolation_target(target)
        except ShellIsolationTargetTimeout as exc:
            self.fail(str(exc))
        if result.returncode == 0:
            return
        self.fail(
            f"Subprocess shell test failed for {self._target} "
            f"(exit={result.returncode}).\n{format_child_output(result)}"
        )


def load_tests(loader: unittest.TestLoader, _tests, _pattern):  # noqa: ANN001
    suite = unittest.TestSuite()
    for test_name in loader.getTestCaseNames(ScriptEditorDockTests):
        target = f"{ScriptEditorDockTests.__module__}.{ScriptEditorDockTests.__qualname__}.{test_name}"
        suite.addTest(_SubprocessShellWindowTest(target))
    return suite


if __name__ == "__main__":
    unittest.main()
