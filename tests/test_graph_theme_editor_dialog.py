from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QLineEdit, QMessageBox

from ea_node_editor.settings import DEFAULT_APP_PREFERENCES
from ea_node_editor.ui.dialogs.graph_theme_editor_dialog import GraphThemeEditorDialog
from ea_node_editor.ui.graph_theme import resolve_graph_theme
from ea_node_editor.ui.shell.window import ShellWindow


def _custom_theme(theme_id: str = "custom_graph_theme_deadbeef", label: str = "Ocean Wire") -> dict[str, object]:
    custom_theme = copy.deepcopy(resolve_graph_theme("graph_stitch_light").as_dict())
    custom_theme["theme_id"] = theme_id
    custom_theme["label"] = label
    return custom_theme


class GraphThemeEditorDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_dialog_groups_built_in_and_custom_themes_and_previews_tokens_read_only(self) -> None:
        custom_theme = _custom_theme()
        dialog = GraphThemeEditorDialog(
            initial_settings={
                "follow_shell_theme": True,
                "selected_theme_id": "graph_stitch_dark",
                "custom_themes": [custom_theme],
            }
        )
        try:
            self.assertEqual(dialog.theme_tree.topLevelItemCount(), 2)
            self.assertEqual(dialog.theme_tree.topLevelItem(0).text(0), "Built-in Themes")
            self.assertEqual(dialog.theme_tree.topLevelItem(1).text(0), "Custom Themes")
            self.assertEqual(dialog.theme_tree.topLevelItem(0).childCount(), 2)
            self.assertEqual(dialog.theme_tree.topLevelItem(1).childCount(), 1)

            self.assertEqual(dialog.theme_id_field.text(), "graph_stitch_dark")
            self.assertEqual(dialog.theme_mode_field.text(), "Built-in theme (read-only)")
            self.assertFalse(dialog.rename_button.isEnabled())
            self.assertFalse(dialog.delete_button.isEnabled())
            self.assertTrue(dialog.duplicate_button.isEnabled())
            self.assertTrue(dialog.use_selected_button.isEnabled())

            card_bg_value = dialog.findChild(QLineEdit, "node_tokens_card_bg_value")
            self.assertIsNotNone(card_bg_value)
            self.assertTrue(card_bg_value.isReadOnly())
            self.assertEqual(card_bg_value.text(), resolve_graph_theme("graph_stitch_dark").node_tokens.card_bg)
        finally:
            dialog.close()

    def test_library_management_commands_update_custom_theme_list(self) -> None:
        dialog = GraphThemeEditorDialog(
            initial_settings={
                "follow_shell_theme": True,
                "selected_theme_id": "graph_stitch_dark",
                "custom_themes": [],
            }
        )
        try:
            dialog.duplicate_button.click()
            self.assertEqual(dialog.theme_tree.topLevelItem(1).childCount(), 1)
            duplicated_theme_id = dialog.theme_id_field.text()
            self.assertTrue(duplicated_theme_id.startswith("custom_graph_theme_"))
            self.assertEqual(dialog.theme_name_field.text(), "Graph Stitch Dark Copy")
            self.assertTrue(dialog.rename_button.isEnabled())
            self.assertTrue(dialog.delete_button.isEnabled())

            with patch("PyQt6.QtWidgets.QInputDialog.getText", return_value=("Ocean Wire", True)):
                dialog.rename_button.click()
            self.assertEqual(dialog.theme_name_field.text(), "Ocean Wire")

            with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
                dialog.delete_button.click()
            self.assertEqual(dialog.theme_tree.topLevelItem(1).childCount(), 0)
            self.assertEqual(dialog.theme_id_field.text(), "graph_stitch_dark")
            self.assertFalse(dialog.rename_button.isEnabled())
            self.assertFalse(dialog.delete_button.isEnabled())

            dialog.new_button.click()
            self.assertEqual(dialog.theme_tree.topLevelItem(1).childCount(), 1)
            self.assertTrue(dialog.theme_id_field.text().startswith("custom_graph_theme_"))
            self.assertEqual(dialog.theme_name_field.text(), "Custom Graph Theme")
        finally:
            dialog.close()

    def test_use_selected_returns_explicit_graph_theme_settings(self) -> None:
        custom_theme = _custom_theme()
        dialog = GraphThemeEditorDialog(
            initial_settings={
                "follow_shell_theme": True,
                "selected_theme_id": "graph_stitch_dark",
                "custom_themes": [custom_theme],
            }
        )
        try:
            dialog.theme_tree.setCurrentItem(dialog._theme_items[custom_theme["theme_id"]])
            dialog.use_selected_button.click()

            self.assertTrue(dialog.use_selected_requested)
            self.assertEqual(dialog.result(), dialog.DialogCode.Accepted)
            settings = dialog.graph_theme_settings()
            self.assertFalse(settings["follow_shell_theme"])
            self.assertEqual(settings["selected_theme_id"], custom_theme["theme_id"])
            self.assertEqual(settings["custom_themes"][0]["label"], custom_theme["label"])
        finally:
            dialog.close()

    def test_reject_keeps_library_changes_for_close_style_exit(self) -> None:
        dialog = GraphThemeEditorDialog(
            initial_settings={
                "follow_shell_theme": True,
                "selected_theme_id": "graph_stitch_dark",
                "custom_themes": [],
            }
        )
        try:
            dialog.new_button.click()
            created_theme_id = dialog.theme_id_field.text()

            dialog.reject()

            self.assertEqual(dialog.result(), dialog.DialogCode.Accepted)
            self.assertFalse(dialog.use_selected_requested)
            settings = dialog.graph_theme_settings()
            self.assertEqual(len(settings["custom_themes"]), 1)
            self.assertEqual(settings["custom_themes"][0]["theme_id"], created_theme_id)
        finally:
            dialog.close()


class GraphThemeEditorShellFlowTests(unittest.TestCase):
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

    def test_shell_flow_persists_manager_result(self) -> None:
        custom_theme = _custom_theme()
        updated_graph_theme = {
            "follow_shell_theme": False,
            "selected_theme_id": custom_theme["theme_id"],
            "custom_themes": [custom_theme],
        }

        with patch.object(ShellWindow, "edit_graph_theme_settings", return_value=updated_graph_theme):
            self.window.show_graph_theme_editor_dialog()
        self.app.processEvents()

        persisted = json.loads(self._app_preferences_path.read_text(encoding="utf-8"))
        expected_document = copy.deepcopy(DEFAULT_APP_PREFERENCES)
        expected_document["graphics"]["graph_theme"] = updated_graph_theme

        self.assertEqual(persisted["graphics"]["graph_theme"], expected_document["graphics"]["graph_theme"])
        self.assertEqual(self.window.graph_theme_bridge.theme_id, custom_theme["theme_id"])


if __name__ == "__main__":
    unittest.main()
