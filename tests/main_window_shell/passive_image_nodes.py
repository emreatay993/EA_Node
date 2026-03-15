from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from PyQt6.QtCore import QMetaObject
from PyQt6.QtGui import QColor, QImage
from PyQt6.QtQuick import QQuickItem

from tests.main_window_shell.base import *  # noqa: F401,F403


class MainWindowShellPassiveImageNodesTests(MainWindowShellTestBase):
    def _walk_items(self, item: QQuickItem):
        yield item
        for child in item.childItems():
            yield from self._walk_items(child)

    def _graph_node_card(self, node_id: str) -> QQuickItem:
        graph_canvas = self._graph_canvas_item()
        for item in self._walk_items(graph_canvas):
            if item.objectName() != "graphNodeCard":
                continue
            node_data = item.property("nodeData") or {}
            if str(node_data.get("node_id", "")) == node_id:
                return item
        self.fail(f"Could not find graphNodeCard for node {node_id!r}.")

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

    def test_image_panel_inspector_exposes_locked_editor_modes(self) -> None:
        node_id = self.window.scene.add_node_from_type("passive.media.image_panel", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        items = {item["key"]: item for item in self.window.selected_node_property_items}
        self.assertEqual(items["source_path"]["editor_mode"], "path")
        self.assertEqual(items["caption"]["editor_mode"], "textarea")
        self.assertEqual(items["fit_mode"]["editor_mode"], "enum")

        self._inspector_property_object("inspectorPathEditor", "source_path")
        self._inspector_property_object("inspectorTextareaEditor", "caption")

    def test_image_panel_path_editor_browse_commits_selected_path(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("passive.media.image_panel", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()
        initial_card = self._graph_node_card(node_id)
        initial_height = float(initial_card.height())

        picked_path = Path(self._env.temp_path) / "picked-image-node.png"
        image = QImage(12, 24, QImage.Format.Format_ARGB32)
        image.fill(QColor("#2c85bf"))
        self.assertTrue(image.save(str(picked_path)))

        path_editor = self._inspector_property_object("inspectorPathEditor", "source_path")
        browse_button = self._inspector_property_object("inspectorPathBrowseButton", "source_path")

        with patch("ea_node_editor.ui.shell.window.QFileDialog.getOpenFileName", return_value=(str(picked_path), "")):
            QMetaObject.invokeMethod(browse_button, "click")
            self.app.processEvents()

        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        node_payload = next(item for item in self.window.scene.nodes_model if item["node_id"] == node_id)
        updated_card = self._graph_node_card(node_id)
        self.assertEqual(node.properties["source_path"], str(picked_path))
        self.assertEqual(str(path_editor.property("text")), str(picked_path))
        self.assertIsNone(node.custom_width)
        self.assertIsNone(node.custom_height)
        self.assertGreater(float(node_payload["height"]), initial_height)
        self.assertAlmostEqual(float(updated_card.height()), float(node_payload["height"]), places=3)
