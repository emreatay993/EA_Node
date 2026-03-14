from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QDialog

from ea_node_editor.settings import DEFAULT_APP_PREFERENCES, DEFAULT_GRAPHICS_SETTINGS
from ea_node_editor.ui.dialogs.graphics_settings_dialog import GraphicsSettingsDialog
from ea_node_editor.ui.graph_theme import (
    GRAPH_CATEGORY_ACCENT_TOKENS_V1,
    GRAPH_STITCH_DARK_EDGE_TOKENS_V1,
    GRAPH_STITCH_DARK_NODE_TOKENS_V1,
    GRAPH_STITCH_LIGHT_EDGE_TOKENS_V1,
    GRAPH_STITCH_LIGHT_NODE_TOKENS_V1,
)
from ea_node_editor.ui.shell.window import ShellWindow
from ea_node_editor.ui.theme import build_theme_stylesheet


class GraphThemeShellTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self._session_path = Path(self._temp_dir.name) / "last_session.json"
        self._autosave_path = Path(self._temp_dir.name) / "autosave.sfe"
        self._app_preferences_path = Path(self._temp_dir.name) / "app_preferences.json"
        self._global_custom_workflows_path = Path(self._temp_dir.name) / "custom_workflows_global.json"
        self._session_patch = patch(
            "ea_node_editor.ui.shell.window.recent_session_path",
            return_value=self._session_path,
        )
        self._autosave_patch = patch(
            "ea_node_editor.ui.shell.window.autosave_project_path",
            return_value=self._autosave_path,
        )
        self._app_preferences_patch = patch(
            "ea_node_editor.ui.shell.controllers.app_preferences_controller.app_preferences_path",
            return_value=self._app_preferences_path,
        )
        self._global_custom_workflows_patch = patch(
            "ea_node_editor.custom_workflows.global_store.global_custom_workflows_path",
            return_value=self._global_custom_workflows_path,
        )
        self._session_patch.start()
        self._autosave_patch.start()
        self._app_preferences_patch.start()
        self._global_custom_workflows_patch.start()
        self.window = ShellWindow()
        self.window.show()
        self.app.processEvents()

    def tearDown(self) -> None:
        self.window.close()
        self.app.processEvents()
        self._session_patch.stop()
        self._autosave_patch.stop()
        self._app_preferences_patch.stop()
        self._global_custom_workflows_patch.stop()
        self._temp_dir.cleanup()

    def _recreate_window(self) -> None:
        self.window.close()
        self.app.processEvents()
        self.window = ShellWindow()
        self.window.show()
        self.app.processEvents()

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
