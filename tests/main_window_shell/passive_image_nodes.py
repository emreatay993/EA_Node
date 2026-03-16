from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from PyQt6.QtCore import QMetaObject, QPoint, QPointF, Qt
from PyQt6.QtGui import QColor, QImage
from PyQt6.QtQuick import QQuickItem
from PyQt6.QtTest import QTest

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

    def _graph_node_child(self, node_id: str, object_name: str) -> QQuickItem:
        card = self._graph_node_card(node_id)
        for item in self._walk_items(card):
            if item.objectName() == object_name:
                return item
        self.fail(f"Could not find {object_name!r} for node {node_id!r}.")

    @staticmethod
    def _item_scene_center(item: QQuickItem) -> QPoint:
        scene_point = item.mapToScene(QPointF(item.width() * 0.5, item.height() * 0.5))
        return QPoint(round(scene_point.x()), round(scene_point.y()))

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
        self.assertEqual(set(items), {"source_path", "caption", "fit_mode"})
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

    def test_image_panel_crop_apply_persists_hidden_normalized_rect(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("passive.media.image_panel", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)

        image_path = Path(self._env.temp_path) / "croppable-image-node.png"
        image = QImage(40, 20, QImage.Format.Format_ARGB32)
        image.fill(QColor("#2c85bf"))
        self.assertTrue(image.save(str(image_path)))

        self.window.scene.set_node_property(node_id, "source_path", str(image_path))
        self.app.processEvents()

        surface = self._graph_node_child(node_id, "graphNodeMediaSurface")
        apply_button = self._graph_node_child(node_id, "graphNodeMediaCropApplyButton")

        surface.setProperty("cropModeActive", True)
        surface.setProperty("draftCropX", 0.1)
        surface.setProperty("draftCropY", 0.2)
        surface.setProperty("draftCropW", 0.5)
        surface.setProperty("draftCropH", 0.6)
        self.app.processEvents()

        QMetaObject.invokeMethod(apply_button, "click")
        self.app.processEvents()

        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertAlmostEqual(float(node.properties["crop_x"]), 0.1)
        self.assertAlmostEqual(float(node.properties["crop_y"]), 0.2)
        self.assertAlmostEqual(float(node.properties["crop_w"]), 0.5)
        self.assertAlmostEqual(float(node.properties["crop_h"]), 0.6)
        self.assertEqual(
            {item["key"] for item in self.window.selected_node_property_items},
            {"source_path", "caption", "fit_mode"},
        )

    def test_image_panel_crop_hover_action_button_triggers_crop_mode(self) -> None:
        node_id = self.window.scene.add_node_from_type("passive.media.image_panel", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)

        image_path = Path(self._env.temp_path) / "clickable-crop-button.png"
        image = QImage(40, 20, QImage.Format.Format_ARGB32)
        image.fill(QColor("#2c85bf"))
        self.assertTrue(image.save(str(image_path)))

        self.window.scene.set_node_property(node_id, "source_path", str(image_path))
        self.app.processEvents()

        card = self._graph_node_card(node_id)
        surface = self._graph_node_child(node_id, "graphNodeMediaSurface")
        hover_action_button = self._graph_node_child(node_id, "graphNodeSurfaceHoverActionButton")
        self.assertFalse(bool(surface.property("cropModeActive")))

        QTest.mouseMove(self.window.quick_widget, self._item_scene_center(card))
        self.app.processEvents()
        self.assertTrue(bool(hover_action_button.property("visible")))

        QMetaObject.invokeMethod(hover_action_button, "click")
        self.app.processEvents()
        self.assertTrue(bool(surface.property("cropModeActive")))
