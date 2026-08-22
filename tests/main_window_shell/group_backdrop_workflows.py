from __future__ import annotations

import gc

from PyQt6.QtCore import QObject, QPoint, QPointF, Qt
from PyQt6.QtQuick import QQuickItem
from PyQt6.QtTest import QTest

from tests.main_window_shell.base import MainWindowShellTestBase, _action_shortcuts
from tests.qt_wait import wait_for_condition_or_raise

GROUP_BACKDROP_TYPE_ID = "passive.annotation.group_backdrop"
LOGGER_TYPE_ID = "core.logger"


def _menu_action_texts(menu: QObject) -> list[str]:
    actions = menu.property("visibleActions") or []
    if hasattr(actions, "toVariant"):
        actions = actions.toVariant()
    visible_actions: list[dict[str, object]] = []
    for action in actions:
        if hasattr(action, "toVariant"):
            action = action.toVariant()
        if isinstance(action, dict):
            visible_actions.append(action)
    return [str(action.get("text", "")) for action in visible_actions]


def _menu_actions_by_text(menu: QObject) -> dict[str, dict[str, object]]:
    actions = menu.property("visibleActions") or []
    if hasattr(actions, "toVariant"):
        actions = actions.toVariant()
    actions_by_text: dict[str, dict[str, object]] = {}
    for action in actions:
        if hasattr(action, "toVariant"):
            action = action.toVariant()
        if isinstance(action, dict):
            text = str(action.get("text", ""))
            actions_by_text[text] = action
    return actions_by_text


class MainWindowShellGroupBackdropWorkflowTests(MainWindowShellTestBase):
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

    def _graph_node_card(self, node_id: str, *, object_name: str = "graphNodeCard") -> QQuickItem:
        graph_canvas = self._graph_canvas_item()
        for item in self._walk_items(graph_canvas):
            if item.objectName() != object_name:
                continue
            node_data = item.property("nodeData") or {}
            if str(node_data.get("node_id", "")) == node_id:
                return self._hold_qml_ref(item)
        self.fail(f"Could not find {object_name!r} for node {node_id!r}.")

    def _graph_node_child(
        self,
        node_id: str,
        *,
        card_object_name: str,
        child_object_name: str,
        property_key: str | None = None,
    ) -> QQuickItem:
        card = self._graph_node_card(node_id, object_name=card_object_name)
        for item in self._walk_items(card):
            if item.objectName() != child_object_name:
                continue
            if property_key is not None and str(item.property("propertyKey") or "") != property_key:
                continue
            return self._hold_qml_ref(item)
        self.fail(
            f"Could not find child {child_object_name!r} for node {node_id!r} on {card_object_name!r}."
        )

    def _add_group_backdrop(self, x: float, y: float, width: float, height: float) -> str:
        node_id = self.window.scene.add_node_from_type(GROUP_BACKDROP_TYPE_ID, x=x, y=y)
        self.window.scene.set_node_geometry(node_id, x, y, width, height)
        return node_id

    @staticmethod
    def _payload_node_ids(payloads: list[dict[str, object]]) -> set[str]:
        return {str(item.get("node_id", "")) for item in payloads}

    def test_group_backdrop_library_and_drop_creation_paths_place_group_backdrops(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]

        self.window.set_library_query("group")
        self.window.set_library_category("")
        self.window.set_library_data_type("")
        self.window.set_library_direction("")
        self.app.processEvents()

        matching_items = [
            item
            for item in self.window.filtered_node_library_items
            if str(item.get("type_id", "")) == GROUP_BACKDROP_TYPE_ID
        ]
        self.assertEqual(len(matching_items), 1)

        before_ids = set(workspace.nodes)
        self.window.request_add_node_from_library(GROUP_BACKDROP_TYPE_ID)
        self.app.processEvents()

        added_ids = set(workspace.nodes) - before_ids
        self.assertEqual(len(added_ids), 1)
        added_id = next(iter(added_ids))
        added_node = workspace.nodes[added_id]
        self.assertEqual(added_node.type_id, GROUP_BACKDROP_TYPE_ID)
        self.assertEqual(added_node.title, "")
        self.assertEqual(added_node.properties, {"title": ""})
        self.assertTrue(any(item["node_id"] == added_id for item in self.window.scene.backdrop_nodes_model))

        before_ids = set(workspace.nodes)
        created = self.window.request_drop_node_from_library(
            GROUP_BACKDROP_TYPE_ID,
            420.0,
            300.0,
            "",
            "",
            "",
            "",
        )
        self.assertTrue(created)
        self.app.processEvents()

        dropped_ids = set(workspace.nodes) - before_ids
        self.assertEqual(len(dropped_ids), 1)
        dropped_id = next(iter(dropped_ids))
        dropped_node = workspace.nodes[dropped_id]
        self.assertEqual(dropped_node.type_id, GROUP_BACKDROP_TYPE_ID)
        self.assertEqual(dropped_node.title, "")
        self.assertEqual(dropped_node.properties, {"title": ""})
        self.assertAlmostEqual(float(dropped_node.x), 420.0, places=6)
        self.assertAlmostEqual(float(dropped_node.y), 300.0, places=6)
        self.assertTrue(any(item["node_id"] == dropped_id for item in self.window.scene.backdrop_nodes_model))

    def test_group_backdrop_wrap_action_shortcut_c_creates_group_backdrop_without_touching_group_shortcuts(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        first_id = self.window.scene.add_node_from_type(LOGGER_TYPE_ID, x=140.0, y=120.0)
        second_id = self.window.scene.add_node_from_type(LOGGER_TYPE_ID, x=360.0, y=250.0)
        self.window.scene.select_node(first_id, False)
        self.window.scene.select_node(second_id, True)
        self.app.processEvents()

        self.assertIn("C", _action_shortcuts(self.window.action_wrap_selection_in_group_backdrop))
        self.assertIn("Ctrl+Alt+G", _action_shortcuts(self.window.action_group_selection))
        self.assertIn("Ctrl+Shift+G", _action_shortcuts(self.window.action_ungroup_selection))

        before_ids = set(workspace.nodes)
        self.window.quick_widget.setFocus()
        self.app.processEvents()
        QTest.keyClick(self.window.quick_widget, Qt.Key.Key_C)
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: len(set(workspace.nodes) - before_ids) == 1,
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for the C shortcut to wrap the selection in a group.",
        )

        added_ids = set(workspace.nodes) - before_ids
        backdrop_id = next(iter(added_ids))
        backdrop_node = workspace.nodes[backdrop_id]
        self.assertEqual(backdrop_node.type_id, GROUP_BACKDROP_TYPE_ID)
        self.assertEqual(backdrop_node.title, "")
        self.assertEqual(backdrop_node.properties, {"title": ""})
        self.assertLessEqual(
            float(backdrop_node.x),
            min(float(workspace.nodes[first_id].x), float(workspace.nodes[second_id].x)),
        )
        self.assertLessEqual(
            float(backdrop_node.y),
            min(float(workspace.nodes[first_id].y), float(workspace.nodes[second_id].y)),
        )
        self.assertEqual(self.window.scene.selected_node_lookup, {backdrop_id: True})

    def test_multi_selection_canvas_context_menu_wraps_selection_in_group_backdrop(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        graph_canvas = self._graph_canvas_item()
        selection_context_popup = graph_canvas.findChild(QObject, "graphCanvasSelectionContextPopup")
        self.assertIsNotNone(selection_context_popup)

        first_id = self.window.scene.add_node_from_type(LOGGER_TYPE_ID, x=140.0, y=120.0)
        second_id = self.window.scene.add_node_from_type(LOGGER_TYPE_ID, x=360.0, y=250.0)

        self.window.scene.select_node(first_id, False)
        self.app.processEvents()
        self.assertNotIn("Wrap into Group", _menu_action_texts(selection_context_popup))

        self.window.scene.select_node(second_id, True)
        self.app.processEvents()
        self.assertIn("Wrap into Group", _menu_action_texts(selection_context_popup))

        before_ids = set(workspace.nodes)
        graph_canvas.setProperty("selectionContextVisible", True)
        selection_context_popup.actionTriggered.emit("wrap_selection_in_group_backdrop")
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: len(set(workspace.nodes) - before_ids) == 1,
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for the selection context menu to wrap nodes in a group.",
        )

        added_ids = set(workspace.nodes) - before_ids
        backdrop_id = next(iter(added_ids))
        backdrop_node = workspace.nodes[backdrop_id]
        self.assertEqual(backdrop_node.type_id, GROUP_BACKDROP_TYPE_ID)
        self.assertEqual(backdrop_node.title, "")
        self.assertEqual(backdrop_node.properties, {"title": ""})
        self.assertEqual(self.window.scene.selected_node_lookup, {backdrop_id: True})
        self.assertFalse(bool(graph_canvas.property("selectionContextVisible")))

    def test_multi_selection_same_size_actions_only_resize_passive_nodes(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        graph_canvas = self._graph_canvas_item()
        selection_context_popup = graph_canvas.findChild(QObject, "graphCanvasSelectionContextPopup")
        self.assertIsNotNone(selection_context_popup)

        active_primary = self.window.scene.add_node_from_type(LOGGER_TYPE_ID, x=140.0, y=120.0)
        active_target = self.window.scene.add_node_from_type(LOGGER_TYPE_ID, x=360.0, y=250.0)
        passive_primary = self.window.scene.add_node_from_type("passive.flowchart.process", x=620.0, y=280.0)
        passive_target = self.window.scene.add_node_from_type("passive.flowchart.process", x=860.0, y=320.0)
        workspace.nodes[active_primary].custom_width = 400.0
        workspace.nodes[active_primary].custom_height = 240.0
        workspace.nodes[active_target].custom_width = 260.0
        workspace.nodes[active_target].custom_height = 180.0
        workspace.nodes[passive_primary].custom_width = 320.0
        workspace.nodes[passive_primary].custom_height = 220.0
        workspace.nodes[passive_target].custom_width = 240.0
        workspace.nodes[passive_target].custom_height = 160.0
        self.window.scene.refresh_workspace_from_model(workspace_id)

        self.window.scene.select_node(active_primary, False)
        self.window.scene.select_node(active_target, True)
        self.app.processEvents()

        actions = _menu_actions_by_text(selection_context_popup)
        self.assertFalse(bool(actions.get("Set Same Width", {}).get("enabled", False)))
        self.assertFalse(bool(actions.get("Set Same Height", {}).get("enabled", False)))

        self.window.scene.select_node(passive_primary, False)
        self.window.scene.select_node(passive_target, True)
        self.window.scene.select_node(active_primary, True)
        self.window.scene.select_node(active_target, True)
        self.app.processEvents()

        actions = _menu_actions_by_text(selection_context_popup)
        self.assertTrue(bool(actions.get("Set Same Width", {}).get("enabled", False)))
        self.assertTrue(bool(actions.get("Set Same Height", {}).get("enabled", False)))

        graph_canvas.setProperty("selectionContextVisible", True)
        selection_context_popup.actionTriggered.emit("set_selection_same_type_width")
        self.app.processEvents()
        wait_for_condition_or_raise(
            lambda: abs(float(workspace.nodes[passive_target].custom_width or 0.0) - 320.0) < 0.01,
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for same-type selection width resize.",
        )
        self.assertAlmostEqual(workspace.nodes[active_target].custom_width or 0.0, 260.0, places=6)
        self.assertFalse(bool(graph_canvas.property("selectionContextVisible")))

        graph_canvas.setProperty("selectionContextVisible", True)
        selection_context_popup.actionTriggered.emit("set_selection_same_type_height")
        self.app.processEvents()
        wait_for_condition_or_raise(
            lambda: abs(float(workspace.nodes[passive_target].custom_height or 0.0) - 220.0) < 0.01,
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for same-type selection height resize.",
        )
        self.assertAlmostEqual(workspace.nodes[active_target].custom_height or 0.0, 180.0, places=6)
        self.assertFalse(bool(graph_canvas.property("selectionContextVisible")))

    def test_group_backdrop_context_menu_rename_updates_title_and_title_property(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        graph_canvas = self._graph_canvas_item()
        node_context_popup = graph_canvas.findChild(QObject, "graphCanvasNodeContextPopup")
        self.assertIsNotNone(node_context_popup)

        backdrop_id = self._add_group_backdrop(160.0, 120.0, 380.0, 260.0)
        self.app.processEvents()

        graph_canvas.setProperty("nodeContextNodeId", backdrop_id)
        graph_canvas.setProperty("nodeContextVisible", True)
        self.app.processEvents()

        title_editor = self._graph_node_child(
            backdrop_id,
            card_object_name="graphNodeCard",
            child_object_name="graphNodeTitleEditor",
        )
        self.assertFalse(bool(title_editor.property("visible")))

        node_context_popup.actionTriggered.emit("rename_node")
        self.app.processEvents()

        self.assertFalse(bool(graph_canvas.property("nodeContextVisible")))
        wait_for_condition_or_raise(
            lambda: bool(title_editor.property("visible")),
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for the group inline title editor to activate.",
        )

        self.assertTrue(bool(graph_canvas.commitNodeSurfaceProperty(backdrop_id, "title", "Mesh Extraction")))
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: workspace.nodes[backdrop_id].title == "Mesh Extraction",
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for the inline rename to reach the workspace model.",
        )

        backdrop = workspace.nodes[backdrop_id]
        self.assertEqual(backdrop.title, "Mesh Extraction")
        self.assertEqual(backdrop.properties["title"], "Mesh Extraction")

    def test_group_backdrop_context_menu_peek_inside_is_only_for_collapsed_group_backdrops(self) -> None:
        graph_canvas = self._graph_canvas_item()
        node_context_popup = graph_canvas.findChild(QObject, "graphCanvasNodeContextPopup")
        self.assertIsNotNone(node_context_popup)

        backdrop_id = self._add_group_backdrop(160.0, 120.0, 380.0, 260.0)
        logger_id = self.window.scene.add_node_from_type(LOGGER_TYPE_ID, x=720.0, y=180.0)
        self.app.processEvents()

        graph_canvas.setProperty("nodeContextNodeId", backdrop_id)
        self.app.processEvents()
        self.assertNotIn("Peek Inside", _menu_action_texts(node_context_popup))

        self.window.scene.set_node_collapsed(backdrop_id, True)
        self.app.processEvents()
        graph_canvas.setProperty("nodeContextNodeId", "")
        self.app.processEvents()
        graph_canvas.setProperty("nodeContextNodeId", backdrop_id)
        self.app.processEvents()
        self.assertIn("Peek Inside", _menu_action_texts(node_context_popup))

        graph_canvas.setProperty("nodeContextNodeId", logger_id)
        self.app.processEvents()
        self.assertNotIn("Peek Inside", _menu_action_texts(node_context_popup))

    def test_collapsed_group_backdrop_keeps_group_title_icon_source(self) -> None:
        backdrop_id = self._add_group_backdrop(160.0, 120.0, 380.0, 260.0)
        self.window.scene.set_node_collapsed(backdrop_id, True)
        self.window.scene.clear_selection()
        self.app.processEvents()

        title_text = self._graph_node_child(
            backdrop_id,
            card_object_name="graphNodeCard",
            child_object_name="graphNodeTitle",
        )
        group_icon = self._graph_node_child(
            backdrop_id,
            card_object_name="graphNodeCard",
            child_object_name="graphNodeGroupTitleIcon",
        )
        title_icon = self._graph_node_child(
            backdrop_id,
            card_object_name="graphNodeCard",
            child_object_name="graphNodeTitleIcon",
        )

        wait_for_condition_or_raise(
            lambda: bool(group_icon.property("visible")),
            timeout_ms=500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for the collapsed group header icon.",
        )

        source = group_icon.property("source")
        if hasattr(source, "toString"):
            source = source.toString()

        self.assertEqual(str(title_text.property("text") or ""), "")
        self.assertTrue(bool(group_icon.property("visible")))
        self.assertFalse(bool(title_icon.property("visible")))
        self.assertTrue(str(source).startswith("image://ui-icons/comment?size="))

    def test_comment_peek_shows_direct_members_only_remains_editable_and_exits(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        active_view = workspace.views[workspace.active_view_id]
        graph_canvas = self._graph_canvas_item()
        node_context_popup = graph_canvas.findChild(QObject, "graphCanvasNodeContextPopup")
        self.assertIsNotNone(node_context_popup)

        outer_id = self._add_group_backdrop(60.0, 60.0, 760.0, 520.0)
        inner_id = self._add_group_backdrop(170.0, 150.0, 320.0, 240.0)
        direct_logger_id = self.window.scene.add_node_from_type(LOGGER_TYPE_ID, x=520.0, y=240.0)
        nested_logger_id = self.window.scene.add_node_from_type(LOGGER_TYPE_ID, x=230.0, y=220.0)
        outside_logger_id = self.window.scene.add_node_from_type(LOGGER_TYPE_ID, x=980.0, y=240.0)
        self.window.scene.set_node_collapsed(outer_id, True)
        self.app.processEvents()

        self.assertEqual(self.window.scene.active_scope_path, [])
        self.assertEqual(active_view.scope_path, [])

        graph_canvas.setProperty("nodeContextNodeId", outer_id)
        graph_canvas.setProperty("nodeContextVisible", True)
        self.app.processEvents()
        self.assertIn("Peek Inside", _menu_action_texts(node_context_popup))
        node_context_popup.actionTriggered.emit("open_comment_peek")
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: self.window.scene.active_comment_peek_node_id == outer_id,
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for comment peek to activate.",
        )

        visible_nodes = self._payload_node_ids(self.window.scene.nodes_model)
        visible_backdrops = self._payload_node_ids(self.window.scene.backdrop_nodes_model)
        self.assertEqual(visible_nodes, {direct_logger_id})
        self.assertEqual(visible_backdrops, {outer_id, inner_id})
        self.assertNotIn(nested_logger_id, visible_nodes)
        self.assertNotIn(outside_logger_id, visible_nodes)
        self.assertEqual(self.window.scene.active_scope_path, [])
        self.assertEqual(active_view.scope_path, [])

        self.window.scene.move_node(direct_logger_id, 540.0, 260.0)
        self.app.processEvents()
        self.assertAlmostEqual(float(workspace.nodes[direct_logger_id].x), 540.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[direct_logger_id].y), 260.0, places=6)
        self.assertEqual(self.window.scene.active_comment_peek_node_id, outer_id)

        graph_canvas.setProperty("nodeContextNodeId", outer_id)
        graph_canvas.setProperty("nodeContextVisible", True)
        self.app.processEvents()
        self.assertIn("Exit Peek", _menu_action_texts(node_context_popup))
        node_context_popup.actionTriggered.emit("close_comment_peek")
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: self.window.scene.active_comment_peek_node_id == "",
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for explicit comment peek exit.",
        )
        self.assertIn(outside_logger_id, self._payload_node_ids(self.window.scene.nodes_model))

        self.assertTrue(self.window.scene.open_comment_peek(outer_id))
        self.app.processEvents()
        self.assertEqual(self.window.scene.active_comment_peek_node_id, outer_id)
        scene_point = graph_canvas.mapToScene(QPointF(12.0, 12.0))
        QTest.mouseClick(
            self.window.quick_widget,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(round(scene_point.x()), round(scene_point.y())),
        )
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: self.window.scene.active_comment_peek_node_id == "",
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for comment peek click-away dismissal.",
        )
        self.assertEqual(self.window.scene.active_scope_path, [])
        self.assertEqual(active_view.scope_path, [])

    def test_group_backdrop_wrap_action_is_no_op_for_empty_selection(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        self.window.scene.clear_selection()
        self.app.processEvents()
        self.window.runtime_history.clear_workspace(workspace_id)

        before_ids = set(workspace.nodes)
        self.window.action_wrap_selection_in_group_backdrop.trigger()
        self.app.processEvents()

        self.assertEqual(set(workspace.nodes), before_ids)
        self.assertEqual(self.window.scene.selected_node_lookup, {})
        self.assertEqual(self.window.runtime_history.undo_depth(workspace_id), 0)

    def test_group_title_is_empty_until_selected_then_double_click_edits_it_without_inspector_fields(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        backdrop_id = self._add_group_backdrop(160.0, 120.0, 380.0, 260.0)
        self.window.scene.clear_selection()
        self.app.processEvents()

        primary_card = self._graph_node_card(backdrop_id)
        primary_title = self._graph_node_child(
            backdrop_id,
            card_object_name="graphNodeCard",
            child_object_name="graphNodeTitle",
        )
        self.assertEqual(workspace.nodes[backdrop_id].title, "")
        self.assertEqual(workspace.nodes[backdrop_id].properties, {"title": ""})
        self.assertEqual(str(primary_title.property("text") or ""), "")

        scene_point = primary_card.mapToScene(QPointF(primary_card.width() * 0.5, primary_card.height() * 0.5))
        QTest.mouseClick(
            self.window.quick_widget,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(round(scene_point.x()), round(scene_point.y())),
        )
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: self.window.scene.selected_node_lookup == {backdrop_id: True},
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for the group to become selected.",
        )

        input_card = self._graph_node_card(backdrop_id, object_name="graphGroupBackdropInputCard")
        overlay_title = self._graph_node_child(
            backdrop_id,
            card_object_name="graphGroupBackdropInputCard",
            child_object_name="graphNodeTitle",
        )
        title_editor = self._graph_node_child(
            backdrop_id,
            card_object_name="graphGroupBackdropInputCard",
            child_object_name="graphNodeTitleEditor",
        )
        object_names = {item.objectName() for item in self._walk_items(primary_card)} | {
            item.objectName() for item in self._walk_items(input_card)
        }
        self.assertEqual(str(overlay_title.property("text") or ""), "Double click to edit title")
        self.assertTrue(bool(overlay_title.property("visible")))
        self.assertEqual(self.window.selected_node_property_items, [])
        self.assertNotIn("graphNodeGroupBackdropRichTextBlock", object_names)
        self.assertNotIn("graphNodeGroupBackdropBodyText", object_names)
        self.assertNotIn("graphGroupBackdropBodyEditor", object_names)
        self.assertNotIn("graphGroupBackdropBodyEditorField", object_names)

        scene_point = overlay_title.mapToScene(QPointF(overlay_title.width() * 0.5, overlay_title.height() * 0.5))
        QTest.mouseDClick(
            self.window.quick_widget,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            QPoint(round(scene_point.x()), round(scene_point.y())),
        )
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: bool(title_editor.property("visible")),
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for double-click title editing.",
        )
        self.assertEqual(str(title_editor.property("text") or ""), "")
        self.assertTrue(bool(self._graph_canvas_item().commitNodeSurfaceProperty(backdrop_id, "title", "Mesh Extraction")))
        self.app.processEvents()
        self.assertEqual(workspace.nodes[backdrop_id].title, "Mesh Extraction")
        self.assertEqual(workspace.nodes[backdrop_id].properties, {"title": "Mesh Extraction"})

    def test_group_backdrop_drag_moves_nested_descendants_as_single_undoable_action(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        outer_id = self._add_group_backdrop(60.0, 60.0, 760.0, 520.0)
        inner_id = self._add_group_backdrop(170.0, 150.0, 320.0, 240.0)
        inner_logger_id = self.window.scene.add_node_from_type(LOGGER_TYPE_ID, x=220.0, y=200.0)
        outer_logger_id = self.window.scene.add_node_from_type(LOGGER_TYPE_ID, x=550.0, y=300.0)
        outside_logger_id = self.window.scene.add_node_from_type(LOGGER_TYPE_ID, x=940.0, y=260.0)
        self.window.scene.select_node(outer_id, False)
        self.app.processEvents()
        self.window.runtime_history.clear_workspace(workspace_id)

        outer_card = self._graph_node_card(outer_id, object_name="graphGroupBackdropInputCard")
        outer_card.dragFinished.emit(outer_id, 150.0, 120.0, True)
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: abs(float(workspace.nodes[outer_id].x) - 150.0) < 0.01,
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for backdrop drag to update the workspace model.",
        )

        self.assertAlmostEqual(float(workspace.nodes[outer_id].x), 150.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outer_id].y), 120.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_id].x), 260.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_id].y), 210.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_logger_id].x), 310.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_logger_id].y), 260.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outer_logger_id].x), 640.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outer_logger_id].y), 360.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outside_logger_id].x), 940.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outside_logger_id].y), 260.0, places=6)
        self.assertEqual(self.window.scene.selected_node_lookup, {outer_id: True})
        self.assertEqual(self.window.runtime_history.undo_depth(workspace_id), 1)

        self.window.action_undo.trigger()
        wait_for_condition_or_raise(
            lambda: abs(float(workspace.nodes[outer_id].x) - 60.0) < 0.01,
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for backdrop drag undo.",
        )
        self.assertAlmostEqual(float(workspace.nodes[inner_id].x), 170.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_logger_id].x), 220.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outer_logger_id].x), 550.0, places=6)

        self.window.action_redo.trigger()
        wait_for_condition_or_raise(
            lambda: abs(float(workspace.nodes[outer_id].x) - 150.0) < 0.01,
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for backdrop drag redo.",
        )
        self.assertAlmostEqual(float(workspace.nodes[inner_id].x), 260.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_logger_id].x), 310.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outer_logger_id].x), 640.0, places=6)

    def test_group_backdrop_resize_recomputes_nested_membership_without_moving_unrelated_nodes(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        outer_id = self._add_group_backdrop(100.0, 100.0, 760.0, 520.0)
        inner_id = self._add_group_backdrop(220.0, 170.0, 320.0, 240.0)
        inner_logger_id = self.window.scene.add_node_from_type(LOGGER_TYPE_ID, x=260.0, y=220.0)
        outside_logger_id = self.window.scene.add_node_from_type(LOGGER_TYPE_ID, x=980.0, y=240.0)
        self.window.scene.select_node(outer_id, False)
        self.app.processEvents()
        self.window.runtime_history.clear_workspace(workspace_id)

        outer_card = self._graph_node_card(outer_id, object_name="graphGroupBackdropInputCard")
        outer_card.resizeFinished.emit(outer_id, 100.0, 100.0, 240.0, 160.0)
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: abs(float(workspace.nodes[outer_id].custom_width or 0.0) - 260.0) < 0.01,
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for backdrop resize to update the workspace model.",
        )

        inner_payload = next(item for item in self.window.scene.backdrop_nodes_model if item["node_id"] == inner_id)
        inner_logger_payload = next(item for item in self.window.scene.nodes_model if item["node_id"] == inner_logger_id)
        outside_logger_payload = next(item for item in self.window.scene.nodes_model if item["node_id"] == outside_logger_id)

        self.assertAlmostEqual(float(workspace.nodes[outer_id].x), 100.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outer_id].y), 100.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outer_id].custom_width or 0.0), 260.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outer_id].custom_height or 0.0), 180.0, places=6)
        self.assertEqual(inner_payload["owner_backdrop_id"], "")
        self.assertEqual(inner_logger_payload["owner_backdrop_id"], inner_id)
        self.assertEqual(outside_logger_payload["owner_backdrop_id"], "")
        self.assertAlmostEqual(float(workspace.nodes[inner_id].x), 220.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_id].y), 170.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_logger_id].x), 260.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[inner_logger_id].y), 220.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outside_logger_id].x), 980.0, places=6)
        self.assertAlmostEqual(float(workspace.nodes[outside_logger_id].y), 240.0, places=6)
        self.assertEqual(self.window.runtime_history.undo_depth(workspace_id), 1)

        self.window.action_undo.trigger()
        wait_for_condition_or_raise(
            lambda: abs(float(workspace.nodes[outer_id].custom_width or 0.0) - 760.0) < 0.01,
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for backdrop resize undo.",
        )
        inner_payload = next(item for item in self.window.scene.backdrop_nodes_model if item["node_id"] == inner_id)
        self.assertEqual(inner_payload["owner_backdrop_id"], outer_id)

        self.window.action_redo.trigger()
        wait_for_condition_or_raise(
            lambda: abs(float(workspace.nodes[outer_id].custom_width or 0.0) - 260.0) < 0.01,
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for backdrop resize redo.",
        )
        inner_payload = next(item for item in self.window.scene.backdrop_nodes_model if item["node_id"] == inner_id)
        self.assertEqual(inner_payload["owner_backdrop_id"], "")
