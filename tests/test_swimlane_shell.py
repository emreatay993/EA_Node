# Purpose: Mounted-shell swimlane checks the scene tests cannot prove: the lane and pool context-menu rows and their commands, lanes stacking and hit-testing above their pool, the lane title turned into its band, and the collapsed pool pill.
# Map: feature_routes/swimlane_pools_lanes
# Tests: tests/test_swimlane_shell.py
from __future__ import annotations

import pytest
from PyQt6.QtCore import QObject
from PyQt6.QtQuick import QQuickItem

from tests.main_window_shell.base import SharedMainWindowShellTestBase
from tests.qt_wait import wait_for_condition_or_raise

pytestmark = pytest.mark.xdist_group("p03_main_window_shell")

POOL = "passive.annotation.swimlane_pool"


def _menu_rows(menu: QObject) -> list[tuple[str, bool]]:
    actions = menu.property("visibleActions") or []
    if hasattr(actions, "toVariant"):
        actions = actions.toVariant()
    rows = []
    for action in actions:
        value = action.toVariant() if hasattr(action, "toVariant") else action
        rows.append((str(value.get("text", "")), bool(value.get("enabled", True))))
    return rows


def _node_data(item: QQuickItem) -> dict:
    data = item.property("nodeData")
    if hasattr(data, "toVariant"):
        data = data.toVariant()
    return data if isinstance(data, dict) else {}


class SwimlaneShellTests(SharedMainWindowShellTestBase):
    def _pool(self) -> tuple[str, list[str]]:
        pool_id = self.window.scene.add_node_from_type(POOL, x=100.0, y=100.0)
        self.app.processEvents()
        [described] = [
            pool for pool in self.window.scene.describe_swimlane_pools() if pool["pool_node_id"] == pool_id
        ]
        return pool_id, list(described["lane_node_ids"])

    def _lane_order(self, pool_id: str) -> list[str]:
        return next(
            list(pool["lane_node_ids"])
            for pool in self.window.scene.describe_swimlane_pools()
            if pool["pool_node_id"] == pool_id
        )

    def _open_menu(self, node_id: str) -> QObject:
        canvas = self._graph_canvas_item()
        menu = canvas.findChild(QObject, "graphCanvasNodeContextPopup")
        self.assertIsNotNone(menu)
        canvas.setProperty("nodeContextNodeId", "")
        self.app.processEvents()
        canvas.setProperty("nodeContextNodeId", node_id)
        canvas.setProperty("nodeContextVisible", True)
        self.app.processEvents()
        return menu

    def _hosts(self, layer_name: str) -> dict[str, QQuickItem]:
        layer = self._find_qml_item(layer_name)
        self.assertIsNotNone(layer)
        return {
            str(_node_data(item).get("node_id", "")): item
            for item in self._walk_items(layer)
            if item.objectName() in ("graphNodeCard", "graphGroupBackdropInputCard") and _node_data(item)
        }

    def test_lane_and_pool_menus_offer_the_lane_commands(self) -> None:
        pool_id, lanes = self._pool()

        lane_rows = _menu_rows(self._open_menu(lanes[0]))
        self.assertEqual(
            lane_rows[:6],
            [
                ("Insert Lane Above", True),
                ("Insert Lane Below", True),
                ("Move Lane Up", False),
                ("Move Lane Down", True),
                ("Tidy Lanes", True),
                ("Remove Lane", True),
            ],
        )
        self.assertEqual(_menu_rows(self._open_menu(lanes[-1]))[2:4], [("Move Lane Up", True), ("Move Lane Down", False)])
        self.assertEqual(_menu_rows(self._open_menu(pool_id))[:2], [("Add Lane", True), ("Tidy Lanes", True)])

    def test_menu_commands_edit_the_pool(self) -> None:
        pool_id, lanes = self._pool()

        self._open_menu(lanes[0]).actionTriggered.emit("node_context::swimlane_insert_after")
        self.app.processEvents()
        order = self._lane_order(pool_id)
        self.assertEqual(len(order), 4)
        self.assertEqual((order[0], order[2], order[3]), tuple(lanes))

        self._open_menu(lanes[0]).actionTriggered.emit("node_context::swimlane_move_after")
        self.app.processEvents()
        order = self._lane_order(pool_id)
        self.assertEqual(order[1], lanes[0])

        self._open_menu(order[0]).actionTriggered.emit("node_context::swimlane_remove")
        self.app.processEvents()
        self.assertEqual(len(self._lane_order(pool_id)), 3)
        self.assertFalse(bool(self._graph_canvas_item().property("nodeContextVisible")))

    def test_lanes_stack_above_their_pool_and_turn_their_title_into_the_band(self) -> None:
        pool_id, lanes = self._pool()
        self.window.scene.select_node(pool_id, False)
        self.app.processEvents()

        for layer_name in ("graphCanvasBackdropLayer", "graphCanvasBackdropInputLayer"):
            hosts = self._hosts(layer_name)
            # A selected pool still stays under its lanes, so a click in a lane reaches the lane.
            self.assertGreater(hosts[lanes[0]].z(), hosts[pool_id].z(), layer_name)

        lane_host = self._hosts("graphCanvasBackdropInputLayer")[lanes[0]]
        title = next(item for item in self._walk_items(lane_host) if item.objectName() == "graphNodeTitleDisplay")
        self.assertEqual(title.rotation(), -90.0)
        # Rotated about its top-left at the band's bottom end: it runs up the band, inside it.
        self.assertLess(title.x() + title.height(), 40.0 + 0.01)
        self.assertAlmostEqual(title.y(), lane_host.height() - 12.0)
        self.assertAlmostEqual(title.width(), lane_host.height() - 24.0)

    def test_a_lane_is_renamed_through_its_turned_title(self) -> None:
        pool_id, lanes = self._pool()
        canvas = self._graph_canvas_item()
        host = self._hosts("graphCanvasBackdropInputLayer")[lanes[1]]
        header = next(item for item in self._walk_items(host) if item.objectName() == "graphNodeHeaderLayer")

        # A point in the lane's band, halfway up it, hits the turned title.
        self.assertTrue(header.requestTitleEditAt(20.0, host.height() / 2.0))
        self.app.processEvents()
        editor = next(item for item in self._walk_items(host) if item.objectName() == "graphNodeTitleEditor")
        self.assertTrue(bool(editor.property("visible")))
        self.assertEqual(editor.rotation(), -90.0)
        header.commitTitleEdit("Engineering")
        self.app.processEvents()

        self.assertEqual(self.window.model.active_workspace.nodes[lanes[1]].title, "Engineering")
        self.assertTrue(canvas.requestInlineRenameForNode(pool_id))

    def test_a_collapsed_pool_is_a_pill_with_the_pool_glyph_and_an_upright_title(self) -> None:
        pool_id, lanes = self._pool()
        self.window.scene.set_node_collapsed(pool_id, True)
        self.window.scene.clear_selection()
        self.app.processEvents()

        def pool_child(object_name: str) -> QQuickItem | None:
            for card in self._walk_items(self._graph_canvas_item()):
                if card.objectName() == "graphNodeCard" and _node_data(card).get("node_id") == pool_id:
                    return next((item for item in self._walk_items(card) if item.objectName() == object_name), None)
            return None

        wait_for_condition_or_raise(
            lambda: bool(pool_child("graphNodeGroupTitleIcon") and pool_child("graphNodeGroupTitleIcon").isVisible()),
            timeout_ms=1000,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for the collapsed pool's icon.",
        )
        # The pool glyph, not the Group's comment glyph, so a collapsed pool reads apart from a collapsed Group.
        self.assertIn("layout-dashboard", str(pool_child("graphNodeGroupTitleIcon").property("source").toString()))
        self.assertEqual(pool_child("graphNodeTitleDisplay").rotation(), 0.0)
        # The lanes are hidden with the pool.
        shown_lanes = {
            _node_data(card).get("node_id")
            for card in self._walk_items(self._graph_canvas_item())
            if card.objectName() == "graphNodeCard" and card.isVisible()
        } & set(lanes)
        self.assertFalse(shown_lanes)

