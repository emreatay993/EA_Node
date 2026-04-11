from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from PyQt6.QtWidgets import QDialog

from ea_node_editor.settings import DEFAULT_APP_PREFERENCES, DEFAULT_GRAPHICS_SETTINGS
from ea_node_editor.ui.dialogs.graphics_settings_dialog import GraphicsSettingsDialog
from ea_node_editor.ui.graph_theme import (
    GRAPH_CATEGORY_ACCENT_TOKENS_V1,
    GRAPH_STITCH_DARK_EDGE_TOKENS_V1,
    GRAPH_STITCH_DARK_NODE_TOKENS_V1,
    GRAPH_STITCH_LIGHT_EDGE_TOKENS_V1,
    GRAPH_STITCH_LIGHT_NODE_TOKENS_V1,
    resolve_category_accent,
    resolve_graph_theme,
)
from ea_node_editor.ui.theme import build_theme_stylesheet
from tests.main_window_shell.base import SharedMainWindowShellTestBase

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SHELL_TEST_RUNNER = (
    "import sys, unittest; "
    "target = sys.argv[1]; "
    "suite = unittest.defaultTestLoader.loadTestsFromName(target); "
    "result = unittest.TextTestRunner(verbosity=2).run(suite); "
    "sys.exit(0 if result.wasSuccessful() else 1)"
)


class GraphThemeShellTests(SharedMainWindowShellTestBase):

    def _recreate_window(self) -> None:
        self._reopen_shared_window()

    def _set_graphics(self, *, theme_id: str, graph_theme: dict[str, object] | None = None) -> None:
        graphics = copy.deepcopy(DEFAULT_GRAPHICS_SETTINGS)
        graphics["theme"]["theme_id"] = theme_id
        if graph_theme is not None:
            graphics["graph_theme"] = graph_theme
        self.window.app_preferences_controller.set_graphics_settings(graphics, host=self.window)
        self.app.processEvents()

    def _write_preferences(self, graphics: dict[str, object]) -> None:
        document = copy.deepcopy(DEFAULT_APP_PREFERENCES)
        document["graphics"] = copy.deepcopy(graphics)
        self._app_preferences_path.write_text(json.dumps(document), encoding="utf-8")

    def test_graph_theme_bridge_is_exposed_with_startup_payload(self) -> None:
        graph_theme_bridge = self.window.quick_widget.rootContext().contextProperty("graphThemeBridge")

        self.assertIsNotNone(graph_theme_bridge)
        self.assertEqual(graph_theme_bridge.theme_id, "graph_stitch_dark")
        self.assertEqual(graph_theme_bridge.node_palette["card_bg"], GRAPH_STITCH_DARK_NODE_TOKENS_V1.card_bg)
        self.assertEqual(
            graph_theme_bridge.edge_palette["selected_stroke"],
            GRAPH_STITCH_DARK_EDGE_TOKENS_V1.selected_stroke,
        )
        self.assertEqual(graph_theme_bridge.theme["theme_id"], "graph_stitch_dark")

    def test_graph_theme_bridge_follows_shell_theme_changes_by_default(self) -> None:
        self._set_graphics(theme_id="stitch_light")

        self.assertEqual(self.window.theme_bridge.theme_id, "stitch_light")
        self.assertEqual(self.window.graph_theme_bridge.theme_id, "graph_stitch_light")
        self.assertEqual(self.window.graph_theme_bridge.node_palette["card_bg"], GRAPH_STITCH_LIGHT_NODE_TOKENS_V1.card_bg)
        self.assertEqual(self.app.styleSheet(), build_theme_stylesheet("stitch_light"))

    def test_graph_theme_bridge_allows_explicit_theme_selection(self) -> None:
        self._set_graphics(
            theme_id="stitch_dark",
            graph_theme={
                "follow_shell_theme": False,
                "selected_theme_id": "graph_stitch_light",
                "custom_themes": [],
            },
        )

        self.assertEqual(self.window.theme_bridge.theme_id, "stitch_dark")
        self.assertEqual(self.window.graph_theme_bridge.theme_id, "graph_stitch_light")
        self.assertEqual(self.window.graph_theme_bridge.node_palette["card_bg"], GRAPH_STITCH_LIGHT_NODE_TOKENS_V1.card_bg)
        self.assertEqual(self.app.styleSheet(), build_theme_stylesheet("stitch_dark"))

    def test_graph_theme_bridge_resolves_persisted_explicit_theme_on_startup(self) -> None:
        graphics = copy.deepcopy(DEFAULT_GRAPHICS_SETTINGS)
        graphics["theme"]["theme_id"] = "stitch_light"
        graphics["graph_theme"] = {
            "follow_shell_theme": False,
            "selected_theme_id": "graph_stitch_dark",
            "custom_themes": [],
        }
        self._write_preferences(graphics)
        self._recreate_window()

        self.assertEqual(self.window.theme_bridge.theme_id, "stitch_light")
        self.assertEqual(self.window.graph_theme_bridge.theme_id, "graph_stitch_dark")
        self.assertEqual(self.window.graph_theme_bridge.node_palette["card_bg"], GRAPH_STITCH_DARK_NODE_TOKENS_V1.card_bg)
        self.assertEqual(self.app.styleSheet(), build_theme_stylesheet("stitch_light"))

    def test_graphics_settings_dialog_persists_and_applies_explicit_graph_theme(self) -> None:
        updated_graphics = copy.deepcopy(DEFAULT_GRAPHICS_SETTINGS)
        updated_graphics["theme"]["theme_id"] = "stitch_dark"
        updated_graphics["graph_theme"] = {
            "follow_shell_theme": False,
            "selected_theme_id": "graph_stitch_light",
            "custom_themes": [],
        }

        with patch.object(GraphicsSettingsDialog, "exec", return_value=QDialog.DialogCode.Accepted), patch.object(
            GraphicsSettingsDialog,
            "values",
            return_value=updated_graphics,
        ):
            self.window.show_graphics_settings_dialog()
        self.app.processEvents()

        self.assertEqual(self.window.theme_bridge.theme_id, "stitch_dark")
        self.assertEqual(self.window.graph_theme_bridge.theme_id, "graph_stitch_light")
        self.assertEqual(self.window.graph_theme_bridge.node_palette["card_bg"], GRAPH_STITCH_LIGHT_NODE_TOKENS_V1.card_bg)
        persisted = json.loads(self._app_preferences_path.read_text(encoding="utf-8"))
        self.assertEqual(persisted["graphics"], updated_graphics)

    def test_graph_scene_payloads_follow_runtime_graph_theme_changes(self) -> None:
        start_id = self.window.scene.add_node_from_type("core.start", 20.0, 20.0)
        constant_id = self.window.scene.add_node_from_type("core.constant", 220.0, 20.0)
        branch_id = self.window.scene.add_node_from_type("core.branch", 500.0, 20.0)
        edge_id = self.window.scene.add_edge(constant_id, "as_text", branch_id, "condition")

        nodes_payload = {item["node_id"]: item for item in self.window.scene.nodes_model}
        edges_payload = {item["edge_id"]: item for item in self.window.scene.edges_model}
        self.assertEqual(nodes_payload[start_id]["accent"], GRAPH_CATEGORY_ACCENT_TOKENS_V1.core)
        self.assertTrue(edges_payload[edge_id]["data_type_warning"])
        self.assertEqual(edges_payload[edge_id]["color"], GRAPH_STITCH_DARK_EDGE_TOKENS_V1.warning_stroke)

        self._set_graphics(
            theme_id="stitch_dark",
            graph_theme={
                "follow_shell_theme": False,
                "selected_theme_id": "graph_stitch_light",
                "custom_themes": [],
            },
        )

        self.assertEqual(self.window.graph_theme_bridge.theme_id, "graph_stitch_light")
        nodes_payload = {item["node_id"]: item for item in self.window.scene.nodes_model}
        edges_payload = {item["edge_id"]: item for item in self.window.scene.edges_model}
        self.assertEqual(nodes_payload[start_id]["accent"], GRAPH_CATEGORY_ACCENT_TOKENS_V1.core)
        self.assertEqual(edges_payload[edge_id]["color"], GRAPH_STITCH_LIGHT_EDGE_TOKENS_V1.warning_stroke)

    def test_nested_category_registry_graph_theme_resolves_accent_from_root_segment(self) -> None:
        theme = resolve_graph_theme("graph_stitch_dark")

        self.assertEqual(
            resolve_category_accent(theme, ("Ansys DPF", "Compute")),
            resolve_category_accent(theme, ("Ansys DPF",)),
        )
        self.assertEqual(
            resolve_category_accent(theme, ("Core", "Input")),
            GRAPH_CATEGORY_ACCENT_TOKENS_V1.core,
        )
        self.assertEqual(
            resolve_category_accent(theme, ("External Tools", "Input")),
            GRAPH_CATEGORY_ACCENT_TOKENS_V1.default,
        )


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
    for test_name in loader.getTestCaseNames(GraphThemeShellTests):
        target = f"{GraphThemeShellTests.__module__}.{GraphThemeShellTests.__qualname__}.{test_name}"
        suite.addTest(_SubprocessShellWindowTest(target))
    return suite


if __name__ == "__main__":
    unittest.main()
