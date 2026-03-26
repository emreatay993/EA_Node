from __future__ import annotations

import gc
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from PyQt6.QtCore import QMetaObject, QPoint, QPointF, Qt
from PyQt6.QtGui import QColor, QImage
from PyQt6.QtQuick import QQuickItem
from PyQt6.QtTest import QTest

from tests.main_window_shell.base import *  # noqa: F401,F403
from tests.qt_wait import wait_for_condition_or_raise

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DIRECT_ENV = "EA_NODE_EDITOR_PASSIVE_IMAGE_NODES_DIRECT"


class _PytestSubprocessPassiveImageNodeClassTest(unittest.TestCase):
    __test__ = False

    _pytest_nodeid = "tests/main_window_shell/passive_image_nodes.py::MainWindowShellPassiveImageNodesTests"

    def test_class_runs_in_subprocess(self) -> None:
        env = os.environ.copy()
        env.setdefault("QT_QPA_PLATFORM", "offscreen")
        env[_DIRECT_ENV] = "1"
        result = subprocess.run(
            [sys.executable, "-m", "pytest", self._pytest_nodeid, "-q"],
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
        raise AssertionError(
            f"Subprocess passive image node test failed for {self._pytest_nodeid} "
            f"(exit={result.returncode}).\n{output}"
        )


class MainWindowShellPassiveImageNodesTests(MainWindowShellTestBase):
    __test__ = os.environ.get(_DIRECT_ENV) == "1"

    def setUp(self) -> None:
        super().setUp()
        self._held_qml_refs: list[QQuickItem] = []

    def tearDown(self) -> None:
        try:
            super().tearDown()
        finally:
            self._held_qml_refs = []
            gc.collect()

    def _hold_qml_ref(self, item: QQuickItem) -> QQuickItem:
        self._held_qml_refs.append(item)
        return item

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
                return self._hold_qml_ref(item)
        self.fail(f"Could not find graphNodeCard for node {node_id!r}.")

    def _graph_node_child(self, node_id: str, object_name: str) -> QQuickItem:
        card = self._graph_node_card(node_id)
        for item in self._walk_items(card):
            if item.objectName() == object_name:
                return self._hold_qml_ref(item)
        self.fail(f"Could not find {object_name!r} for node {node_id!r}.")

    def _open_media_inline_editors(self, node_id: str) -> QQuickItem:
        surface = self._graph_node_child(node_id, "graphNodeMediaSurface")
        surface.setProperty("inlineEditorsOpened", True)
        self.app.processEvents()
        return surface

    def _graph_node_child_with_property(
        self,
        node_id: str,
        object_name: str,
        property_name: str,
        expected_value: str,
    ) -> QQuickItem:
        card = self._graph_node_card(node_id)
        for item in self._walk_items(card):
            if item.objectName() != object_name:
                continue
            if str(item.property(property_name)) == expected_value:
                return self._hold_qml_ref(item)
        self.fail(
            f"Could not find {object_name!r} for node {node_id!r} "
            f"with {property_name!r}={expected_value!r}."
        )

    @staticmethod
    def _item_scene_center(item: QQuickItem) -> QPoint:
        scene_point = item.mapToScene(QPointF(item.width() * 0.5, item.height() * 0.5))
        return QPoint(round(scene_point.x()), round(scene_point.y()))

    def _item_widget_center(self, item: QQuickItem) -> QPoint:
        item_window = item.window()
        self.assertIsNotNone(item_window)
        scene_point = self._item_scene_center(item)
        global_point = item_window.mapToGlobal(scene_point)
        return self.window.quick_widget.mapFromGlobal(global_point)

    def _wait_for_media_preview(self, surface: QQuickItem, timeout_ms: int = 2000) -> None:
        wait_for_condition_or_raise(
            lambda: str(surface.property("previewState")) == "ready",
            timeout_ms=timeout_ms,
            poll_interval_ms=25,
            app=self.app,
            timeout_message="Timed out waiting for media preview to become ready.",
        )

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
            return self._hold_qml_ref(item)
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
        self.assertTrue(str(node.properties["source_path"]).startswith("artifact-stage://"))
        self.assertEqual(str(path_editor.property("text")), node.properties["source_path"])
        self.assertIsNone(node.custom_width)
        self.assertIsNone(node.custom_height)
        self.assertGreater(float(node_payload["height"]), initial_height)
        self.assertAlmostEqual(float(updated_card.height()), float(node_payload["height"]), places=3)

    def test_image_panel_inline_path_editor_commits_without_node_drag(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("passive.media.image_panel", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        picked_path = Path(self._env.temp_path) / "graph-inline-picked-image.png"
        image = QImage(18, 12, QImage.Format.Format_ARGB32)
        image.fill(QColor("#2c85bf"))
        self.assertTrue(image.save(str(picked_path)))

        self._open_media_inline_editors(node_id)
        path_editor = self._graph_node_child_with_property(
            node_id,
            "graphNodeInlinePathEditor",
            "propertyKey",
            "source_path",
        )
        browse_button = self._graph_node_child_with_property(
            node_id,
            "graphNodeInlinePathBrowseButton",
            "propertyKey",
            "source_path",
        )
        self.assertTrue(bool(path_editor.property("visible")))
        self.assertTrue(bool(browse_button.property("visible")))
        workspace = self.window.model.project.workspaces[workspace_id]
        initial_x = float(workspace.nodes[node_id].x)
        initial_y = float(workspace.nodes[node_id].y)

        with patch("ea_node_editor.ui.shell.window.QFileDialog.getOpenFileName", return_value=(str(picked_path), "")):
            QMetaObject.invokeMethod(browse_button, "click")
            self.app.processEvents()

        node = workspace.nodes[node_id]
        self.assertEqual(self.window.scene.selected_node_id(), node_id)
        self.assertTrue(str(node.properties["source_path"]).startswith("artifact-stage://"))
        self.assertEqual(str(path_editor.property("text")), node.properties["source_path"])
        self.assertAlmostEqual(float(node.x), initial_x, places=6)
        self.assertAlmostEqual(float(node.y), initial_y, places=6)

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
        self._wait_for_media_preview(surface)
        apply_button = self._graph_node_child(node_id, "graphNodeMediaCropApplyButton")
        applied_viewport = self._graph_node_child(node_id, "graphNodeMediaAppliedImageViewport")
        applied_image = self._graph_node_child(node_id, "graphNodeMediaAppliedImage")
        initial_applied_width = float(applied_image.width())
        initial_applied_x = float(applied_image.x())

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
        surface = self._graph_node_child(node_id, "graphNodeMediaSurface")
        applied_viewport = self._graph_node_child(node_id, "graphNodeMediaAppliedImageViewport")
        applied_image = self._graph_node_child(node_id, "graphNodeMediaAppliedImage")
        self.assertTrue(bool(surface.property("hasEffectiveCrop")))
        self.assertGreater(float(applied_image.width()), initial_applied_width)
        self.assertLess(float(applied_image.x()), initial_applied_x)
        self.assertGreater(float(applied_viewport.width()), 0.0)
        self.assertEqual(
            {item["key"] for item in self.window.selected_node_property_items},
            {"source_path", "caption", "fit_mode"},
        )

    def test_image_panel_crop_button_click_does_not_start_host_drag(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("passive.media.image_panel", x=120.0, y=80.0)
        other_node_id = self.window.scene.add_node_from_type("core.start", x=420.0, y=80.0)

        image_path = Path(self._env.temp_path) / "clickable-crop-button.png"
        image = QImage(40, 20, QImage.Format.Format_ARGB32)
        image.fill(QColor("#2c85bf"))
        self.assertTrue(image.save(str(image_path)))

        self.window.scene.set_node_property(node_id, "source_path", str(image_path))
        self.window.scene.focus_node(other_node_id)
        self.app.processEvents()

        card = self._graph_node_card(node_id)
        surface = self._graph_node_child(node_id, "graphNodeMediaSurface")
        crop_button = self._graph_node_child(node_id, "graphNodeMediaCropButton")
        workspace = self.window.model.project.workspaces[workspace_id]
        initial_x = float(workspace.nodes[node_id].x)
        initial_y = float(workspace.nodes[node_id].y)
        nodes_changed: list[str] = []
        self.window.scene.nodes_changed.connect(lambda: nodes_changed.append("nodes"))

        self.assertFalse(bool(surface.property("cropModeActive")))
        self.assertNotEqual(self.window.scene.selected_node_id(), node_id)

        QTest.mouseMove(self.window.quick_widget, self._item_widget_center(card))
        self.app.processEvents()
        self.assertTrue(bool(crop_button.property("visible")))

        nodes_count_before = len(nodes_changed)
        QMetaObject.invokeMethod(crop_button, "click")
        self.app.processEvents()

        surface = self._graph_node_child(node_id, "graphNodeMediaSurface")
        node = workspace.nodes[node_id]
        self.assertEqual(len(nodes_changed), nodes_count_before)
        self.assertEqual(self.window.scene.selected_node_id(), node_id)
        self.assertTrue(bool(surface.property("cropModeActive")))
        self.assertAlmostEqual(float(node.x), initial_x, places=6)
        self.assertAlmostEqual(float(node.y), initial_y, places=6)

    def test_image_panel_crop_apply_closes_when_crop_is_unchanged(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("passive.media.image_panel", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)

        image_path = Path(self._env.temp_path) / "unchanged-crop-image-node.png"
        image = QImage(40, 20, QImage.Format.Format_ARGB32)
        image.fill(QColor("#2c85bf"))
        self.assertTrue(image.save(str(image_path)))

        self.window.scene.set_node_property(node_id, "source_path", str(image_path))
        self.window.scene.set_node_property(node_id, "crop_x", 0.1)
        self.window.scene.set_node_property(node_id, "crop_y", 0.2)
        self.window.scene.set_node_property(node_id, "crop_w", 0.5)
        self.window.scene.set_node_property(node_id, "crop_h", 0.6)
        self.app.processEvents()

        surface = self._graph_node_child(node_id, "graphNodeMediaSurface")
        self._wait_for_media_preview(surface)
        apply_button = self._graph_node_child(node_id, "graphNodeMediaCropApplyButton")

        surface.setProperty("cropModeActive", True)
        surface.setProperty("draftCropX", 0.1)
        surface.setProperty("draftCropY", 0.2)
        surface.setProperty("draftCropW", 0.5)
        surface.setProperty("draftCropH", 0.6)
        self.app.processEvents()
        self.assertTrue(bool(surface.property("cropModeActive")))

        QMetaObject.invokeMethod(apply_button, "click")
        self.app.processEvents()

        self.assertFalse(bool(surface.property("cropModeActive")))
        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertAlmostEqual(float(node.properties["crop_x"]), 0.1)
        self.assertAlmostEqual(float(node.properties["crop_y"]), 0.2)
        self.assertAlmostEqual(float(node.properties["crop_w"]), 0.5)
        self.assertAlmostEqual(float(node.properties["crop_h"]), 0.6)

    def test_image_panel_crop_apply_and_cancel_clicks_bypass_host_drag(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("passive.media.image_panel", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)

        image_path = Path(self._env.temp_path) / "apply-cancel-crop-button.png"
        image = QImage(40, 20, QImage.Format.Format_ARGB32)
        image.fill(QColor("#2c85bf"))
        self.assertTrue(image.save(str(image_path)))

        self.window.scene.set_node_property(node_id, "source_path", str(image_path))
        self.app.processEvents()

        surface = self._graph_node_child(node_id, "graphNodeMediaSurface")
        self._wait_for_media_preview(surface)
        workspace = self.window.model.project.workspaces[workspace_id]
        initial_x = float(workspace.nodes[node_id].x)
        initial_y = float(workspace.nodes[node_id].y)

        surface.setProperty("cropModeActive", True)
        surface.setProperty("draftCropX", 0.1)
        surface.setProperty("draftCropY", 0.2)
        surface.setProperty("draftCropW", 0.5)
        surface.setProperty("draftCropH", 0.6)
        self.app.processEvents()

        apply_button = self._graph_node_child(node_id, "graphNodeMediaCropApplyButton")
        self.assertTrue(bool(apply_button.property("visible")))

        QMetaObject.invokeMethod(apply_button, "click")
        self.app.processEvents()

        node = workspace.nodes[node_id]
        surface = self._graph_node_child(node_id, "graphNodeMediaSurface")
        self.assertFalse(bool(surface.property("cropModeActive")))
        self.assertAlmostEqual(float(node.properties["crop_x"]), 0.1)
        self.assertAlmostEqual(float(node.properties["crop_y"]), 0.2)
        self.assertAlmostEqual(float(node.properties["crop_w"]), 0.5)
        self.assertAlmostEqual(float(node.properties["crop_h"]), 0.6)
        self.assertAlmostEqual(float(node.x), initial_x, places=6)
        self.assertAlmostEqual(float(node.y), initial_y, places=6)

        surface.setProperty("cropModeActive", True)
        surface.setProperty("draftCropX", 0.2)
        surface.setProperty("draftCropY", 0.1)
        surface.setProperty("draftCropW", 0.4)
        surface.setProperty("draftCropH", 0.7)
        self.app.processEvents()

        cancel_button = self._graph_node_child(node_id, "graphNodeMediaCropCancelButton")
        self.assertTrue(bool(cancel_button.property("visible")))

        QMetaObject.invokeMethod(cancel_button, "click")
        self.app.processEvents()

        surface = self._graph_node_child(node_id, "graphNodeMediaSurface")
        node = workspace.nodes[node_id]
        self.assertFalse(bool(surface.property("cropModeActive")))
        self.assertAlmostEqual(float(node.properties["crop_x"]), 0.1)
        self.assertAlmostEqual(float(node.properties["crop_y"]), 0.2)
        self.assertAlmostEqual(float(node.properties["crop_w"]), 0.5)
        self.assertAlmostEqual(float(node.properties["crop_h"]), 0.6)
        self.assertAlmostEqual(float(node.x), initial_x, places=6)
        self.assertAlmostEqual(float(node.y), initial_y, places=6)

    def test_image_panel_crop_handles_report_expected_cursor_and_hover(self) -> None:
        node_id = self.window.scene.add_node_from_type("passive.media.image_panel", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)

        image_path = Path(self._env.temp_path) / "draggable-crop-handles.png"
        image = QImage(40, 20, QImage.Format.Format_ARGB32)
        image.fill(QColor("#2c85bf"))
        self.assertTrue(image.save(str(image_path)))

        self.window.scene.set_node_property(node_id, "source_path", str(image_path))
        surface = self._graph_node_child(node_id, "graphNodeMediaSurface")
        self._wait_for_media_preview(surface)

        surface.setProperty("cropModeActive", True)
        self.app.processEvents()

        top_left_handle = self._graph_node_child_with_property(
            node_id,
            "graphNodeMediaCropHandleMouseArea",
            "handleId",
            "top_left",
        )
        top_left_visual = self._graph_node_child_with_property(
            node_id,
            "graphNodeMediaCropHandle",
            "handleId",
            "top_left",
        )
        self.assertEqual(
            top_left_handle.property("cursorShape"),
            Qt.CursorShape.SizeFDiagCursor,
        )
        self.assertGreater(float(top_left_handle.width()), float(top_left_visual.width()))
        self.assertGreater(float(top_left_handle.height()), float(top_left_visual.height()))

        handle_window = top_left_handle.window()
        self.assertIsNotNone(handle_window)
        scene_point = top_left_visual.mapToScene(QPointF(top_left_visual.width() + 4, top_left_visual.height() * 0.5))
        start_point = QPoint(round(scene_point.x()), round(scene_point.y()))
        QTest.mouseMove(handle_window, start_point)
        self.assertTrue(bool(top_left_handle.property("containsMouse")))
        self.assertEqual(self.window.quick_widget.cursor().shape(), Qt.CursorShape.SizeFDiagCursor)


class MainWindowShellPassiveImageNodesSubprocessTests(_PytestSubprocessPassiveImageNodeClassTest):
    __test__ = os.environ.get(_DIRECT_ENV) != "1"


def load_tests(loader, standard_tests, pattern):
    if os.environ.get(_DIRECT_ENV) == "1":
        return standard_tests

    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(MainWindowShellPassiveImageNodesSubprocessTests))
    return suite
