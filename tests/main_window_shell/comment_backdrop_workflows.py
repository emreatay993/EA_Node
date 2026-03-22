from __future__ import annotations

import gc

from PyQt6.QtQuick import QQuickItem

from tests.main_window_shell.base import MainWindowShellTestBase
from tests.qt_wait import wait_for_condition_or_raise

COMMENT_BACKDROP_TYPE_ID = "passive.annotation.comment_backdrop"
LOGGER_TYPE_ID = "core.logger"


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

    def _add_backdrop(self, x: float, y: float, width: float, height: float) -> str:
        node_id = self.window.scene.add_node_from_type(COMMENT_BACKDROP_TYPE_ID, x=x, y=y)
        self.window.scene.set_node_geometry(node_id, x, y, width, height)
        return node_id

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
