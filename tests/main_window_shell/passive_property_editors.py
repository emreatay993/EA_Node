from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from PyQt6.QtCore import QMetaObject
from PyQt6.QtQuick import QQuickItem

from tests.main_window_shell.base import *  # noqa: F401,F403
from tests.passive_property_editor_fixtures import register_passive_editor_fixture


class MainWindowShellPassivePropertyEditorsTests(MainWindowShellTestBase):
    def setUp(self) -> None:
        super().setUp()
        register_passive_editor_fixture(self.window.registry)

    def _walk_items(self, item: QQuickItem):
        yield item
        for child in item.childItems():
            yield from self._walk_items(child)

    def _inspector_property_object(self, object_name: str, property_key: str) -> QQuickItem:
        root_object = self.window.quick_widget.rootObject()
        self.assertIsNotNone(root_object)
        for item in self._walk_items(root_object):
            if item.objectName() != object_name:
                continue
            if str(item.property("propertyKey")) != property_key:
                continue
            if not bool(item.property("visible")):
                continue
            return item
        self.fail(f"Could not find {object_name!r} for property {property_key!r}.")

    def test_qml_textarea_editor_uses_explicit_apply_commit(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("tests.passive_editor_fixture", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        textarea = self._inspector_property_object("inspectorTextareaEditor", "notes_blob")
        apply_button = self._inspector_property_object("inspectorTextareaApplyButton", "notes_blob")
        updated_text = "Alpha\nBeta\nGamma"

        textarea.setProperty("text", updated_text)
        self.app.processEvents()

        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertNotEqual(node.properties["notes_blob"], updated_text)

        QMetaObject.invokeMethod(apply_button, "click")
        self.app.processEvents()

        self.assertEqual(node.properties["notes_blob"], updated_text)

    def test_qml_path_editor_browse_commits_selected_path(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("tests.passive_editor_fixture", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        picked_path = Path(self._env.temp_path) / "picked-asset.txt"
        picked_path.write_text("fixture", encoding="utf-8")

        path_editor = self._inspector_property_object("inspectorPathEditor", "media_ref")
        browse_button = self._inspector_property_object("inspectorPathBrowseButton", "media_ref")

        with patch("ea_node_editor.ui.shell.window.QFileDialog.getOpenFileName", return_value=(str(picked_path), "")):
            QMetaObject.invokeMethod(browse_button, "click")
            self.app.processEvents()

        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertEqual(node.properties["media_ref"], str(picked_path))
        self.assertEqual(str(path_editor.property("text")), str(picked_path))
