from __future__ import annotations

import gc

from PyQt6.QtCore import QObject, Qt
from PyQt6.QtQuick import QQuickItem
from PyQt6.QtTest import QTest

from tests.main_window_shell.base import MainWindowShellTestBase, _action_shortcuts
from tests.qt_wait import wait_for_condition_or_raise

COMMENT_BACKDROP_TYPE_ID = "passive.annotation.comment_backdrop"
LOGGER_TYPE_ID = "core.logger"


def _menu_action_texts(menu: QObject) -> list[str]:
    actions = menu.property("visibleActions") or []
    if hasattr(actions, "toVariant"):
        actions = actions.toVariant()
    texts: list[str] = []
    for action in actions:
        if hasattr(action, "toVariant"):
            action = action.toVariant()
        if isinstance(action, dict):
            texts.append(str(action.get("text", "")))
    return texts


class MainWindowShellCommentBackdropWorkflowTests(MainWindowShellTestBase):
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

    def _add_backdrop(self, x: float, y: float, width: float, height: float) -> str:
        node_id = self.window.scene.add_node_from_type(COMMENT_BACKDROP_TYPE_ID, x=x, y=y)
        self.window.scene.set_node_geometry(node_id, x, y, width, height)
        return node_id

    def test_comment_backdrop_library_and_drop_creation_paths_place_backdrops(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]

        self.window.set_library_query("comment backdrop")
        self.window.set_library_category("")
        self.window.set_library_data_type("")
        self.window.set_library_direction("")
        self.app.processEvents()

        matching_items = [
            item
            for item in self.window.filtered_node_library_items
            if str(item.get("type_id", "")) == COMMENT_BACKDROP_TYPE_ID
        ]
        self.assertEqual(len(matching_items), 1)

        before_ids = set(workspace.nodes)
        self.window.request_add_node_from_library(COMMENT_BACKDROP_TYPE_ID)
        self.app.processEvents()

        added_ids = set(workspace.nodes) - before_ids
        self.assertEqual(len(added_ids), 1)
        added_id = next(iter(added_ids))
        self.assertEqual(workspace.nodes[added_id].type_id, COMMENT_BACKDROP_TYPE_ID)
        self.assertTrue(any(item["node_id"] == added_id for item in self.window.scene.backdrop_nodes_model))

        before_ids = set(workspace.nodes)
        created = self.window.request_drop_node_from_library(
            COMMENT_BACKDROP_TYPE_ID,
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
        self.assertEqual(dropped_node.type_id, COMMENT_BACKDROP_TYPE_ID)
        self.assertAlmostEqual(float(dropped_node.x), 420.0, places=6)
        self.assertAlmostEqual(float(dropped_node.y), 300.0, places=6)
        self.assertTrue(any(item["node_id"] == dropped_id for item in self.window.scene.backdrop_nodes_model))

    def test_comment_backdrop_wrap_action_shortcut_c_creates_backdrop_without_touching_group_shortcuts(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        first_id = self.window.scene.add_node_from_type(LOGGER_TYPE_ID, x=140.0, y=120.0)
        second_id = self.window.scene.add_node_from_type(LOGGER_TYPE_ID, x=360.0, y=250.0)
        self.window.scene.select_node(first_id, False)
        self.window.scene.select_node(second_id, True)
        self.app.processEvents()

        self.assertIn("C", _action_shortcuts(self.window.action_wrap_selection_in_comment_backdrop))
        self.assertIn("Ctrl+G", _action_shortcuts(self.window.action_group_selection))
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
            timeout_message="Timed out waiting for the C shortcut to wrap the selection in a comment backdrop.",
        )

        added_ids = set(workspace.nodes) - before_ids
        backdrop_id = next(iter(added_ids))
        backdrop_node = workspace.nodes[backdrop_id]
        self.assertEqual(backdrop_node.type_id, COMMENT_BACKDROP_TYPE_ID)
        self.assertLessEqual(
            float(backdrop_node.x),
            min(float(workspace.nodes[first_id].x), float(workspace.nodes[second_id].x)),
        )
        self.assertLessEqual(
            float(backdrop_node.y),
            min(float(workspace.nodes[first_id].y), float(workspace.nodes[second_id].y)),
        )
        self.assertEqual(self.window.scene.selected_node_lookup, {backdrop_id: True})

    def test_multi_selection_canvas_context_menu_wraps_selection_in_comment_backdrop(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        graph_canvas = self._graph_canvas_item()
        selection_context_popup = graph_canvas.findChild(QObject, "graphCanvasSelectionContextPopup")
        self.assertIsNotNone(selection_context_popup)

        first_id = self.window.scene.add_node_from_type(LOGGER_TYPE_ID, x=140.0, y=120.0)
        second_id = self.window.scene.add_node_from_type(LOGGER_TYPE_ID, x=360.0, y=250.0)

        self.window.scene.select_node(first_id, False)
        self.app.processEvents()
        self.assertNotIn("Wrap into frame", _menu_action_texts(selection_context_popup))

        self.window.scene.select_node(second_id, True)
        self.app.processEvents()
        self.assertIn("Wrap into frame", _menu_action_texts(selection_context_popup))

        before_ids = set(workspace.nodes)
        graph_canvas.setProperty("selectionContextVisible", True)
        selection_context_popup.actionTriggered.emit("wrap_into_frame")
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: len(set(workspace.nodes) - before_ids) == 1,
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for the selection context menu to wrap nodes in a comment backdrop.",
        )

        added_ids = set(workspace.nodes) - before_ids
        backdrop_id = next(iter(added_ids))
        backdrop_node = workspace.nodes[backdrop_id]
        self.assertEqual(backdrop_node.type_id, COMMENT_BACKDROP_TYPE_ID)
        self.assertEqual(self.window.scene.selected_node_lookup, {backdrop_id: True})
        self.assertFalse(bool(graph_canvas.property("selectionContextVisible")))

    def test_comment_backdrop_wrap_action_is_no_op_for_empty_selection(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        self.window.scene.clear_selection()
        self.app.processEvents()
        self.window.runtime_history.clear_workspace(workspace_id)

        before_ids = set(workspace.nodes)
        self.window.action_wrap_selection_in_comment_backdrop.trigger()
        self.app.processEvents()

        self.assertEqual(set(workspace.nodes), before_ids)
        self.assertEqual(self.window.scene.selected_node_lookup, {})
        self.assertEqual(self.window.runtime_history.undo_depth(workspace_id), 0)

    def test_comment_backdrop_inline_body_commit_stays_in_sync_with_inspector_edits(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        backdrop_id = self._add_backdrop(160.0, 120.0, 380.0, 260.0)
        self.window.scene.select_node(backdrop_id, False)
        self.app.processEvents()

        self._graph_node_child(
            backdrop_id,
            card_object_name="graphCommentBackdropInputCard",
            child_object_name="graphCommentBackdropBodyEditor",
        )
        self._graph_node_child(
            backdrop_id,
            card_object_name="graphCommentBackdropInputCard",
            child_object_name="graphCommentBackdropBodyEditorField",
            property_key="body",
        )

        card = self._graph_node_card(backdrop_id, object_name="graphCommentBackdropInputCard")
        card.inlinePropertyCommitted.emit(backdrop_id, "body", "Inline backdrop notes")
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: str(workspace.nodes[backdrop_id].properties.get("body", "")) == "Inline backdrop notes",
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for inline backdrop body edits to reach the workspace model.",
        )

        self.window.workspace_graph_edit_controller.set_selected_node_property("body", "Inspector backdrop notes")
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: str(
                self._graph_node_child(
                    backdrop_id,
                    card_object_name="graphCommentBackdropInputCard",
                    child_object_name="graphCommentBackdropBodyEditor",
                ).property("committedText")
                or ""
            ) == "Inspector backdrop notes",
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for inspector body edits to reach the backdrop inline editor.",
        )

        refreshed_body_editor = self._graph_node_child(
            backdrop_id,
            card_object_name="graphCommentBackdropInputCard",
            child_object_name="graphCommentBackdropBodyEditor",
        )
        refreshed_body_field = self._graph_node_child(
            backdrop_id,
            card_object_name="graphCommentBackdropInputCard",
            child_object_name="graphCommentBackdropBodyEditorField",
            property_key="body",
        )
        self.assertEqual(str(workspace.nodes[backdrop_id].properties.get("body", "")), "Inspector backdrop notes")
        self.assertEqual(str(refreshed_body_editor.property("committedText") or ""), "Inspector backdrop notes")
        self.assertEqual(str(refreshed_body_field.property("text") or ""), "Inspector backdrop notes")

    def test_backdrop_drag_moves_nested_descendants_as_single_undoable_action(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        outer_id = self._add_backdrop(60.0, 60.0, 760.0, 520.0)
        inner_id = self._add_backdrop(170.0, 150.0, 320.0, 240.0)
        inner_logger_id = self.window.scene.add_node_from_type(LOGGER_TYPE_ID, x=220.0, y=200.0)
        outer_logger_id = self.window.scene.add_node_from_type(LOGGER_TYPE_ID, x=550.0, y=300.0)
        outside_logger_id = self.window.scene.add_node_from_type(LOGGER_TYPE_ID, x=940.0, y=260.0)
        self.window.scene.select_node(outer_id, False)
        self.app.processEvents()
        self.window.runtime_history.clear_workspace(workspace_id)

        outer_card = self._graph_node_card(outer_id, object_name="graphCommentBackdropInputCard")
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

    def test_backdrop_resize_recomputes_nested_membership_without_moving_unrelated_nodes(self) -> None:
        workspace_id = self.window.workspace_manager.active_workspace_id()
        workspace = self.window.model.project.workspaces[workspace_id]
        outer_id = self._add_backdrop(100.0, 100.0, 760.0, 520.0)
        inner_id = self._add_backdrop(220.0, 170.0, 320.0, 240.0)
        inner_logger_id = self.window.scene.add_node_from_type(LOGGER_TYPE_ID, x=260.0, y=220.0)
        outside_logger_id = self.window.scene.add_node_from_type(LOGGER_TYPE_ID, x=980.0, y=240.0)
        self.window.scene.select_node(outer_id, False)
        self.app.processEvents()
        self.window.runtime_history.clear_workspace(workspace_id)

        outer_card = self._graph_node_card(outer_id, object_name="graphCommentBackdropInputCard")
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
