from __future__ import annotations

import gc
import os
from pathlib import Path
from unittest.mock import patch

from PyQt6.QtCore import QMetaObject, QPoint, QPointF, Qt, Q_ARG
from PyQt6.QtGui import QColor, QImage
from PyQt6.QtQml import QJSValue
from PyQt6.QtQuick import QQuickItem
from PyQt6.QtTest import QTest

from tests.main_window_shell.base import *  # noqa: F401,F403
from tests.qt_wait import wait_for_condition_or_raise

_DIRECT_ENV = "EA_NODE_EDITOR_PASSIVE_IMAGE_NODES_DIRECT"


class MainWindowShellPassiveImageNodesTests(SharedMainWindowShellTestBase):
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

    def _wait_for_media_preview(self, surface: QQuickItem, timeout_ms: int = 5000) -> None:
        wait_for_condition_or_raise(
            lambda: str(surface.property("previewState")) in {"ready", "error"},
            timeout_ms=timeout_ms,
            poll_interval_ms=25,
            app=self.app,
            timeout_message="Timed out waiting for media preview to settle.",
        )
        self.assertEqual(str(surface.property("previewState")), "ready")

    def _find_qml_item(self, object_name: str) -> QQuickItem | None:
        root_object = self.window.quick_widget.rootObject()
        self.assertIsNotNone(root_object)
        for item in self._walk_items(root_object):
            if item.objectName() == object_name:
                return self._hold_qml_ref(item)
        return None

    def _open_inspector_property_group(self, property_key: str) -> None:
        self.window.shell_inspector_presenter.set_property_pane_variant("smart_groups")
        self.app.processEvents()

        property_items = {
            str(item["key"]): item
            for item in self.window.selected_node_property_items
        }
        property_item = property_items[property_key]
        group_name = str(property_item.get("group") or "Properties")
        smart_groups_body = self._find_qml_item("inspectorSmartGroupsBody")
        self.assertIsNotNone(smart_groups_body)
        assert smart_groups_body is not None
        smart_groups_body.setProperty("expandedMap", {f"static:{group_name}": True})
        self.app.processEvents()

    def _inspector_property_object(self, object_name: str, property_key: str) -> QQuickItem:
        self._open_inspector_property_group(property_key)
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
        self.assertEqual(set(items), {"source_path", "fit_mode"})
        self.assertEqual(items["source_path"]["editor_mode"], "path")
        self.assertEqual(items["fit_mode"]["editor_mode"], "enum")

        self._inspector_property_object("inspectorPathEditor", "source_path")

    def test_image_panel_path_editor_browse_commits_external_path_by_default(self) -> None:
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
        self.assertEqual(str(path_editor.property("text")), node.properties["source_path"])
        self.assertIsNone(node.custom_width)
        self.assertIsNone(node.custom_height)
        self.assertGreater(float(node_payload["height"]), initial_height)
        self.assertAlmostEqual(float(updated_card.height()), float(node_payload["height"]), places=3)

    def test_image_panel_path_editor_storage_combo_can_choose_internal_copy(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("passive.media.image_panel", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        picked_path = Path(self._env.temp_path) / "picked-external-image-node.png"
        image = QImage(12, 24, QImage.Format.Format_ARGB32)
        image.fill(QColor("#2c85bf"))
        self.assertTrue(image.save(str(picked_path)))

        items = {item["key"]: item for item in self.window.selected_node_property_items}
        self.assertTrue(items["source_path"]["path_supports_managed_copy"])
        self.assertTrue(items["source_path"]["path_supports_external_link"])

        path_editor = self._inspector_property_object("inspectorPathEditor", "source_path")
        storage_combo = self._inspector_property_object("inspectorPathSourceStorageComboBox", "source_path")
        browse_button = self._inspector_property_object("inspectorPathBrowseButton", "source_path")
        self.assertEqual(str(storage_combo.property("currentText")), "External")
        storage_combo.setProperty("currentIndex", 1)
        self.app.processEvents()

        with patch("ea_node_editor.ui.shell.window.QFileDialog.getOpenFileName", return_value=(str(picked_path), "")):
            QMetaObject.invokeMethod(browse_button, "click")
            self.app.processEvents()

        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertTrue(str(node.properties["source_path"]).startswith("temp://"))
        self.assertEqual(str(path_editor.property("text")), node.properties["source_path"])
        wait_for_condition_or_raise(
            lambda: str(storage_combo.property("currentText")) == "Internal",
            app=self.app,
            timeout_message=lambda: f"Expected Internal source storage, got {storage_combo.property('currentText')!r}.",
        )
        items = {item["key"]: item for item in self.window.selected_node_property_items}
        self.assertEqual(items["source_path"]["path_current_source_mode"], "managed_copy")
        staged_path = self.window.project_session_controller.project_artifact_store().resolve_staged_path(
            node.properties["source_path"]
        )
        self.assertIsNotNone(staged_path)
        assert staged_path is not None
        self.assertEqual(staged_path.name, picked_path.name)

    def test_video_panel_path_editor_storage_combo_can_choose_internal_copy(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("passive.media.video_panel", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        picked_path = Path(self._env.temp_path) / "picked-video-panel-clip.mp4"
        picked_path.write_bytes(b"video fixture")

        items = {item["key"]: item for item in self.window.selected_node_property_items}
        self.assertTrue(items["source_path"]["path_supports_managed_copy"])
        self.assertTrue(items["source_path"]["path_supports_external_link"])

        path_editor = self._inspector_property_object("inspectorPathEditor", "source_path")
        storage_combo = self._inspector_property_object("inspectorPathSourceStorageComboBox", "source_path")
        browse_button = self._inspector_property_object("inspectorPathBrowseButton", "source_path")
        self.assertEqual(str(storage_combo.property("currentText")), "External")
        storage_combo.setProperty("currentIndex", 1)
        self.app.processEvents()

        with patch("ea_node_editor.ui.shell.window.QFileDialog.getOpenFileName", return_value=(str(picked_path), "")):
            QMetaObject.invokeMethod(browse_button, "click")
            self.app.processEvents()

        node = self.window.model.project.workspaces[workspace_id].nodes[node_id]
        self.assertTrue(str(node.properties["source_path"]).startswith("temp://"))
        self.assertEqual(str(path_editor.property("text")), node.properties["source_path"])
        wait_for_condition_or_raise(
            lambda: str(storage_combo.property("currentText")) == "Internal",
            app=self.app,
            timeout_message=lambda: f"Expected Internal source storage, got {storage_combo.property('currentText')!r}.",
        )
        items = {item["key"]: item for item in self.window.selected_node_property_items}
        self.assertEqual(items["source_path"]["path_current_source_mode"], "managed_copy")
        staged_path = self.window.project_session_controller.project_artifact_store().resolve_staged_path(
            node.properties["source_path"]
        )
        self.assertIsNotNone(staged_path)
        assert staged_path is not None
        self.assertEqual(staged_path.name, picked_path.name)

    def test_image_panel_toolbar_browse_action_commits_without_node_drag(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("passive.media.image_panel", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        picked_path = Path(self._env.temp_path) / "graph-inline-picked-image.png"
        image = QImage(18, 12, QImage.Format.Format_ARGB32)
        image.fill(QColor("#2c85bf"))
        self.assertTrue(image.save(str(picked_path)))

        surface = self._graph_node_child(node_id, "graphNodeMediaSurface")
        actions_value = surface.property("surfaceActions")
        if isinstance(actions_value, QJSValue):
            actions_value = actions_value.toVariant()
        actions = list(actions_value or [])
        edit_source_action = next(
            action for action in actions if dict(action).get("id") == "editSource"
        )
        self.assertEqual(dict(edit_source_action).get("icon"), "search")
        self.assertTrue(bool(dict(edit_source_action).get("enabled")))

        workspace = self.window.model.project.workspaces[workspace_id]
        initial_x = float(workspace.nodes[node_id].x)
        initial_y = float(workspace.nodes[node_id].y)

        with patch("ea_node_editor.ui.shell.window.QFileDialog.getOpenFileName", return_value=(str(picked_path), "")):
            QMetaObject.invokeMethod(
                surface,
                "dispatchSurfaceAction",
                Qt.ConnectionType.DirectConnection,
                Q_ARG("QVariant", "editSource"),
            )
            self.app.processEvents()

        node = workspace.nodes[node_id]
        self.assertEqual(self.window.scene.selected_node_id(), node_id)
        self.assertEqual(node.properties["source_path"], str(picked_path))
        self.assertAlmostEqual(float(node.x), initial_x, places=6)
        self.assertAlmostEqual(float(node.y), initial_y, places=6)

    def test_image_panel_toolbar_internalize_action_copies_file_and_flips_storage_mode(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("passive.media.image_panel", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)
        self.app.processEvents()

        external_path = Path(self._env.temp_path) / "graph-inline-external-image.png"
        image = QImage(18, 12, QImage.Format.Format_ARGB32)
        image.fill(QColor("#2c85bf"))
        self.assertTrue(image.save(str(external_path)))
        self.window.scene.set_node_property(node_id, "source_path", str(external_path))
        self.app.processEvents()

        surface = self._graph_node_child(node_id, "graphNodeMediaSurface")
        storage_combo = self._inspector_property_object("inspectorPathSourceStorageComboBox", "source_path")
        self.assertEqual(str(storage_combo.property("currentText")), "External")

        actions_value = surface.property("surfaceActions")
        if isinstance(actions_value, QJSValue):
            actions_value = actions_value.toVariant()
        actions = [dict(action) for action in list(actions_value or [])]
        internalize_action = next(action for action in actions if action.get("id") == "internalizeSource")
        self.assertEqual(internalize_action.get("icon"), "internalize-source")
        self.assertEqual(internalize_action.get("label"), "Copy into project")
        self.assertTrue(bool(internalize_action.get("enabled")))

        workspace = self.window.model.project.workspaces[workspace_id]
        with patch("ea_node_editor.ui.shell.window.QFileDialog.getOpenFileName") as dialog_mock:
            QMetaObject.invokeMethod(
                surface,
                "dispatchSurfaceAction",
                Qt.ConnectionType.DirectConnection,
                Q_ARG("QVariant", "internalizeSource"),
            )
            self.app.processEvents()
            dialog_mock.assert_not_called()

        node = workspace.nodes[node_id]
        self.assertTrue(str(node.properties["source_path"]).startswith("temp://"))
        wait_for_condition_or_raise(
            lambda: str(
                self._inspector_property_object("inspectorPathEditor", "source_path").property("text")
            ) == node.properties["source_path"],
            app=self.app,
            timeout_message=lambda: (
                "Expected path editor to show the staged source ref, got "
                f"{self._inspector_property_object('inspectorPathEditor', 'source_path').property('text')!r}."
            ),
        )
        staged_path = self.window.project_session_controller.project_artifact_store().resolve_staged_path(
            node.properties["source_path"]
        )
        self.assertIsNotNone(staged_path)
        assert staged_path is not None
        self.assertEqual(staged_path.name, external_path.name)
        self.assertEqual(staged_path.read_bytes(), external_path.read_bytes())
        wait_for_condition_or_raise(
            lambda: str(
                self._inspector_property_object("inspectorPathSourceStorageComboBox", "source_path").property(
                    "currentText"
                )
            ) == "Internal",
            app=self.app,
            timeout_message=lambda: (
                "Expected Internal source storage, got "
                f"{self._inspector_property_object('inspectorPathSourceStorageComboBox', 'source_path').property('currentText')!r}."
            ),
        )
        items = {item["key"]: item for item in self.window.selected_node_property_items}
        self.assertEqual(items["source_path"]["path_current_source_mode"], "managed_copy")

        surface = self._graph_node_child(node_id, "graphNodeMediaSurface")
        actions_value = surface.property("surfaceActions")
        if isinstance(actions_value, QJSValue):
            actions_value = actions_value.toVariant()
        actions = [dict(action) for action in list(actions_value or [])]
        self.assertNotIn("internalizeSource", {action.get("id") for action in actions})
        source_action = next(action for action in actions if action.get("id") == "editSource")
        storage_actions = [dict(action) for action in source_action["popoverActions"]]
        self.assertFalse(bool(storage_actions[0].get("checked", False)))
        self.assertTrue(bool(storage_actions[1].get("checked", False)))

    def test_image_panel_save_crop_action_replaces_source_with_internal_png(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("passive.media.image_panel", x=120.0, y=80.0)
        self.window.scene.focus_node(node_id)

        image_path = Path(self._env.temp_path) / "image-crop-source.png"
        image = QImage(40, 20, QImage.Format.Format_ARGB32)
        image.fill(QColor("#2c85bf"))
        self.assertTrue(image.save(str(image_path)))

        self.window.scene.set_node_properties(
            node_id,
            {
                "source_path": str(image_path),
                "crop_x": 0.25,
                "crop_y": 0.25,
                "crop_w": 0.5,
                "crop_h": 0.5,
            },
        )
        self.app.processEvents()

        surface = self._graph_node_child(node_id, "graphNodeMediaSurface")
        self._wait_for_media_preview(surface)

        actions_value = surface.property("surfaceActions")
        if isinstance(actions_value, QJSValue):
            actions_value = actions_value.toVariant()
        actions = [dict(action) for action in list(actions_value or [])]
        save_crop_action = next(action for action in actions if action.get("id") == "save_crop_image")
        self.assertTrue(bool(save_crop_action.get("enabled")))

        workspace = self.window.model.project.workspaces[workspace_id]
        with patch("ea_node_editor.ui.shell.window.QFileDialog.getOpenFileName") as dialog_mock:
            QMetaObject.invokeMethod(
                surface,
                "dispatchSurfaceAction",
                Qt.ConnectionType.DirectConnection,
                Q_ARG("QVariant", "save_crop_image"),
            )
            self.app.processEvents()
            dialog_mock.assert_not_called()

        node = workspace.nodes[node_id]
        self.assertTrue(str(node.properties["source_path"]).startswith("temp://"))
        self.assertAlmostEqual(float(node.properties["crop_x"]), 0.0)
        self.assertAlmostEqual(float(node.properties["crop_y"]), 0.0)
        self.assertAlmostEqual(float(node.properties["crop_w"]), 1.0)
        self.assertAlmostEqual(float(node.properties["crop_h"]), 1.0)

        staged_path = self.window.project_session_controller.project_artifact_store().resolve_staged_path(
            node.properties["source_path"]
        )
        self.assertIsNotNone(staged_path)
        assert staged_path is not None
        self.assertEqual(staged_path.suffix.lower(), ".png")
        cropped = QImage(str(staged_path))
        self.assertFalse(cropped.isNull())
        self.assertEqual(cropped.width(), 20)
        self.assertEqual(cropped.height(), 10)
        wait_for_condition_or_raise(
            lambda: str(
                self._inspector_property_object("inspectorPathSourceStorageComboBox", "source_path").property(
                    "currentText"
                )
            ) == "Internal",
            app=self.app,
            timeout_message=lambda: (
                "Expected Internal source storage, got "
                f"{self._inspector_property_object('inspectorPathSourceStorageComboBox', 'source_path').property('currentText')!r}."
            ),
        )

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
            {"source_path", "fit_mode"},
        )

    def test_image_panel_crop_action_does_not_start_host_drag(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        node_id = self.window.scene.add_node_from_type("passive.media.image_panel", x=120.0, y=80.0)
        other_node_id = self.window.scene.add_node_from_type("core.constant", x=420.0, y=80.0)

        image_path = Path(self._env.temp_path) / "clickable-crop-button.png"
        image = QImage(40, 20, QImage.Format.Format_ARGB32)
        image.fill(QColor("#2c85bf"))
        self.assertTrue(image.save(str(image_path)))

        self.window.scene.set_node_property(node_id, "source_path", str(image_path))
        self.window.scene.focus_node(other_node_id)
        self.app.processEvents()

        card = self._graph_node_card(node_id)
        surface = self._graph_node_child(node_id, "graphNodeMediaSurface")
        self._wait_for_media_preview(surface)
        workspace = self.window.model.project.workspaces[workspace_id]
        initial_x = float(workspace.nodes[node_id].x)
        initial_y = float(workspace.nodes[node_id].y)
        nodes_changed: list[str] = []

        def _record_nodes_changed() -> None:
            nodes_changed.append("nodes")

        self.window.scene.nodes_changed.connect(_record_nodes_changed)
        self.addCleanup(self.window.scene.nodes_changed.disconnect, _record_nodes_changed)

        self.assertFalse(bool(surface.property("cropModeActive")))
        card = self._graph_node_card(node_id)
        crop_button_candidates = [
            item
            for item in self._walk_items(card)
            if item.objectName() == "graphNodeMediaCropButton"
        ]
        self.assertEqual(crop_button_candidates, [])
        self.assertNotEqual(self.window.scene.selected_node_id(), node_id)

        QTest.mouseMove(self.window.quick_widget, self._item_widget_center(card))
        self.app.processEvents()

        surface_actions_value = surface.property("surfaceActions")
        if isinstance(surface_actions_value, QJSValue):
            surface_actions_value = surface_actions_value.toVariant()
        surface_actions = list(surface_actions_value or [])
        crop_action = next(
            action for action in surface_actions if action["id"] == "crop"
        )
        self.assertTrue(bool(crop_action["enabled"]))

        nodes_count_before = len(nodes_changed)
        QMetaObject.invokeMethod(
            surface,
            "dispatchSurfaceAction",
            Q_ARG("QVariant", "crop"),
        )
        self.app.processEvents()

        surface = self._graph_node_child(node_id, "graphNodeMediaSurface")
        node = workspace.nodes[node_id]
        self.assertEqual(len(nodes_changed), nodes_count_before)
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

    def test_image_panel_crop_handles_expose_expected_cursor_and_hit_slop(self) -> None:
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
        self.assertTrue(bool(top_left_handle.property("hoverEnabled")))
        self.assertGreater(float(top_left_handle.width()), float(top_left_visual.width()))
        self.assertGreater(float(top_left_handle.height()), float(top_left_visual.height()))
