from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from PyQt6.QtCore import QMetaObject
from PyQt6.QtGui import QColor
from PyQt6.QtQuick import QQuickItem

from tests.main_window_shell.base import *  # noqa: F401,F403
from tests.passive_property_editor_fixtures import register_passive_editor_fixture


class MainWindowShellPassivePropertyEditorsTests(SharedMainWindowShellTestBase):
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

    def test_path_pointer_file_mode_browse_uses_file_picker(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("io.path_pointer", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        picked_path = Path(self._env.temp_path) / "picked-path-pointer.txt"
        picked_path.write_text("fixture", encoding="utf-8")

        path_editor = self._inspector_property_object("inspectorPathEditor", "path")
        browse_button = self._inspector_property_object("inspectorPathBrowseButton", "path")

        with (
            patch(
                "ea_node_editor.ui.shell.host_presenter.QFileDialog.getOpenFileName",
                return_value=(str(picked_path), ""),
            ) as open_file_dialog,
            patch("ea_node_editor.ui.shell.host_presenter.QFileDialog.getExistingDirectory") as open_directory_dialog,
        ):
            QMetaObject.invokeMethod(browse_button, "click")
            self.app.processEvents()

        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertEqual(node.properties["path"], str(picked_path))
        self.assertEqual(str(path_editor.property("text")), str(picked_path))
        open_file_dialog.assert_called_once()
        open_directory_dialog.assert_not_called()

    def test_path_pointer_folder_mode_browse_uses_directory_picker(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("io.path_pointer", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()
        self.window.set_selected_node_property("mode", "folder")
        self.app.processEvents()

        picked_directory = Path(self._env.temp_path) / "picked-path-pointer-folder"
        picked_directory.mkdir(parents=True, exist_ok=True)

        path_editor = self._inspector_property_object("inspectorPathEditor", "path")
        browse_button = self._inspector_property_object("inspectorPathBrowseButton", "path")

        with (
            patch("ea_node_editor.ui.shell.host_presenter.QFileDialog.getOpenFileName") as open_file_dialog,
            patch(
                "ea_node_editor.ui.shell.host_presenter.QFileDialog.getExistingDirectory",
                return_value=str(picked_directory),
            ) as open_directory_dialog,
        ):
            QMetaObject.invokeMethod(browse_button, "click")
            self.app.processEvents()

        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertEqual(node.properties["path"], str(picked_directory))
        self.assertEqual(str(path_editor.property("text")), str(picked_directory))
        open_directory_dialog.assert_called_once()
        open_file_dialog.assert_not_called()

    def test_folder_explorer_current_path_browse_uses_directory_picker(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("io.folder_explorer", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        property_items = {
            str(item["key"]): item
            for item in self.window.selected_node_property_items
        }
        self.assertEqual(property_items["current_path"]["editor_mode"], "path")
        self.assertEqual(property_items["current_path"]["path_dialog_mode"], "folder")

        picked_directory = Path(self._env.temp_path) / "picked-folder-explorer-root"
        picked_directory.mkdir(parents=True, exist_ok=True)

        path_editor = self._inspector_property_object("inspectorPathEditor", "current_path")
        browse_button = self._inspector_property_object("inspectorPathBrowseButton", "current_path")

        self.assertEqual(str(path_editor.property("pathDialogMode")), "folder")
        self.assertEqual(str(browse_button.property("pathDialogMode")), "folder")

        with (
            patch("ea_node_editor.ui.shell.host_presenter.QFileDialog.getOpenFileName") as open_file_dialog,
            patch(
                "ea_node_editor.ui.shell.host_presenter.QFileDialog.getExistingDirectory",
                return_value=str(picked_directory),
            ) as open_directory_dialog,
        ):
            QMetaObject.invokeMethod(browse_button, "click")
            self.app.processEvents()

        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertEqual(node.properties["current_path"], str(picked_directory))
        self.assertEqual(str(path_editor.property("text")), str(picked_directory))
        open_directory_dialog.assert_called_once()
        open_file_dialog.assert_not_called()

    def test_qml_color_editor_picker_commits_selected_hex(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("tests.passive_editor_fixture", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        property_items = {
            str(item["key"]): item
            for item in self.window.selected_node_property_items
        }
        self.assertEqual(
            property_items["accent_color"]["editor_mode"],
            "color",
        )

        color_editor = self._inspector_property_object("inspectorColorEditor", "accent_color")
        pick_button = self._inspector_property_object("inspectorColorPickerButton", "accent_color")

        with patch(
            "ea_node_editor.ui.shell.host_presenter.QColorDialog.getColor",
            return_value=QColor("#AA5500"),
        ):
            QMetaObject.invokeMethod(pick_button, "click")
            self.app.processEvents()

        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertEqual(node.properties["accent_color"], "#AA5500")
        self.assertEqual(str(color_editor.property("text")), "#AA5500")

    def test_qml_color_editor_manual_hex_entry_commits_rgb_and_argb_values(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("tests.passive_editor_fixture", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        color_editor = self._inspector_property_object("inspectorColorEditor", "accent_color")
        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]

        color_editor.setProperty("text", "#112233")
        self.app.processEvents()
        QMetaObject.invokeMethod(color_editor, "editingFinished")
        self.app.processEvents()
        self.assertEqual(node.properties["accent_color"], "#112233")

        color_editor = self._inspector_property_object("inspectorColorEditor", "accent_color")
        color_editor.setProperty("text", "#80112233")
        self.app.processEvents()
        QMetaObject.invokeMethod(color_editor, "editingFinished")
        self.app.processEvents()
        self.assertEqual(node.properties["accent_color"], "#80112233")
