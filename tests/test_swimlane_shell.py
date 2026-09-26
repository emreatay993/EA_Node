# Purpose: Mounted-shell swimlane checks the scene tests cannot prove: the lane and pool context-menu rows and their commands, the floating toolbar's orientation switch, lanes stacking and hit-testing above their pool, the lane title turned into its band, the collapsed pool pill, a standalone lane's frame, the hover + buttons, and the live previews (resize, lane reorder drag and its commit, the drop-target lane).
# Map: feature_routes/swimlane_pools_lanes
# Tests: tests/test_swimlane_shell.py
from __future__ import annotations

import pytest
from PyQt6.QtCore import QObject, QPoint, QPointF, QRectF
from PyQt6.QtQuick import QQuickItem
from PyQt6.QtTest import QTest

from tests.main_window_shell.base import SharedMainWindowShellTestBase
from tests.qt_wait import wait_for_condition_or_raise

pytestmark = pytest.mark.xdist_group("p03_main_window_shell")

POOL = "passive.annotation.swimlane_pool"
LANE = "passive.annotation.swimlane_lane"
PROCESS = "passive.flowchart.process"
SWITCH_ORIENTATION = "swimlane_switch_orientation"


def _variant(value):  # noqa: ANN001, ANN202
    return value.toVariant() if hasattr(value, "toVariant") else value


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
            lane_rows[:7],
            [
                ("Insert Lane Above", True),
                ("Insert Lane Below", True),
                ("Move Lane Up", False),
                ("Move Lane Down", True),
                ("Tidy Lanes", True),
                ("Switch to Vertical Lanes", True),
                ("Remove Lane", True),
            ],
        )
        self.assertEqual(_menu_rows(self._open_menu(lanes[-1]))[2:4], [("Move Lane Up", True), ("Move Lane Down", False)])
        self.assertEqual(
            _menu_rows(self._open_menu(pool_id))[:3],
            [("Add Lane", True), ("Tidy Lanes", True), ("Switch to Vertical Lanes", True)],
        )
        # A standalone lane: adding a lane next to it forms a pool; there is nothing to move it past.
        solo = self.window.scene.create_swimlane_lane(4000.0, 0.0, title="Solo")
        self.app.processEvents()
        self.assertEqual(
            _menu_rows(self._open_menu(solo))[:5],
            [
                ("Insert Lane Above", True),
                ("Insert Lane Below", True),
                ("Tidy Lane", True),
                ("Switch to Vertical Lanes", True),
                ("Remove Lane", True),
            ],
        )

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


    # -- lane-first and live previews ---------------------------------------------------------------------------

    def _surface_child(self, host: QQuickItem, object_name: str) -> QQuickItem | None:
        return next((item for item in self._walk_items(host) if item.objectName() == object_name), None)

    def _flush(self) -> None:
        scheduler = self._graph_canvas_item().findChild(QObject, "graphCanvasFrameScheduler")
        if scheduler is not None:
            scheduler.flushPendingRedraws()
        self.app.processEvents()

    def _live_geometry(self) -> dict:
        return dict(_variant(self._graph_canvas_item().property("liveNodeGeometry")) or {})

    def test_a_standalone_lane_draws_its_own_frame_and_a_pooled_lane_does_not(self) -> None:
        pool_id, lanes = self._pool()
        solo = self.window.scene.create_swimlane_lane(4000.0, 0.0, title="Solo")
        self.app.processEvents()
        visual = self._hosts("graphCanvasBackdropLayer")

        self.assertTrue(self._surface_child(visual[solo], "graphNodeSwimlanePoolFrame").isVisible())
        self.assertFalse(self._surface_child(visual[solo], "graphNodeSwimlaneLaneDivider").isVisible())
        self.assertFalse(self._surface_child(visual[lanes[1]], "graphNodeSwimlanePoolFrame").isVisible())
        self.assertTrue(self._surface_child(visual[lanes[1]], "graphNodeSwimlaneLaneDivider").isVisible())

    def test_hovering_a_lane_shows_plus_buttons_that_add_a_lane_there(self) -> None:
        solo = self.window.scene.create_swimlane_lane(100.0, 100.0, title="Solo")
        self.app.processEvents()
        # Frame the lane's start (clear of the minimap corner) at a zoom the buttons show at (0.45 and up).
        self.window.view.frame_scene_rect(QRectF(100.0, 50.0, 700.0, 300.0))
        self.app.processEvents()
        host = self._hosts("graphCanvasBackdropInputLayer")[solo]
        before = self._surface_child(host, "graphNodeSwimlaneInsertBeforeButton")
        after = self._surface_child(host, "graphNodeSwimlaneInsertAfterButton")
        self.assertFalse(after.isVisible())

        point = host.mapToScene(QPointF(host.width() * 0.3, host.height() * 0.5))
        for step in range(3):  # the first move enters the view; hover follows the next ones
            QTest.mouseMove(self.window.quick_widget, QPoint(int(point.x()) + step, int(point.y())))
            self.app.processEvents()
        wait_for_condition_or_raise(
            lambda: after.isVisible() and before.isVisible(),
            timeout_ms=1000,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for the lane's + buttons.",
        )
        centre = after.mapToItem(host, QPointF(after.width() / 2, after.height() / 2))
        # The button owns its press: a lane drag never starts there.
        self.assertTrue(host._surfaceClaimsBodyInteractionAt(centre.x(), centre.y()))

        after.clicked.emit()
        self.app.processEvents()

        [pool] = self.window.scene.describe_swimlane_pools()
        self.assertEqual(pool["lane_node_ids"][0], solo)
        self.assertEqual(len(pool["lane_node_ids"]), 2)
        QTest.mouseMove(self.window.quick_widget, QPoint(2, 2))
        self.app.processEvents()

    def test_a_lane_resize_previews_its_whole_pool_while_held(self) -> None:
        pool_id, lanes = self._pool()
        workspace = self.window.model.active_workspace
        node_id = self.window.scene.add_node_from_type(PROCESS, 400.0, 560.0)  # in the last lane
        self.app.processEvents()
        lane = workspace.nodes[lanes[1]]
        x, y, w, h = lane.x, lane.y, lane.custom_width, lane.custom_height
        host = self._hosts("graphCanvasBackdropInputLayer")[lanes[1]]

        host.resizePreviewChanged.emit(lanes[1], x, y, w, h + 100.0, True)
        self.app.processEvents()

        geometry = self._live_geometry()
        self.assertEqual(set(geometry), {pool_id, lanes[1], lanes[2], node_id})
        self.assertAlmostEqual(geometry[lanes[1]]["height"], h + 100.0)
        self.assertAlmostEqual(geometry[lanes[2]]["y"], workspace.nodes[lanes[2]].y + 100.0)
        self.assertAlmostEqual(geometry[node_id]["y"], workspace.nodes[node_id].y + 100.0)
        self.assertAlmostEqual(geometry[pool_id]["height"], workspace.nodes[pool_id].custom_height + 100.0)
        # The model is untouched until the release commits.
        self.assertEqual(workspace.nodes[lanes[1]].custom_height, h)

        host.resizePreviewChanged.emit(lanes[1], x, y, w, h + 100.0, False)
        host.resizeFinished.emit(lanes[1], x, y, w, h + 100.0)
        self.app.processEvents()
        self.assertEqual(self._live_geometry(), {})
        self.assertEqual(workspace.nodes[lanes[1]].custom_height, h + 100.0)
        self.assertEqual(workspace.nodes[lanes[2]].y, y + h + 100.0)

    def test_a_lane_drag_stays_in_its_pool_and_commits_a_reorder(self) -> None:
        pool_id, lanes = self._pool()
        workspace = self.window.model.active_workspace
        canvas = self._graph_canvas_item()
        history = self.window.runtime_history
        depth = history.undo_depth(workspace.workspace_id)

        canvas.setLiveDragOffset(lanes[0], 300.0, 150.0, "", False)
        self._flush()

        # Kept on the stack axis; the lane it passes (the second) makes room.
        self.assertEqual((canvas.property("liveDragDx"), canvas.property("liveDragDy")), (0.0, 150.0))
        geometry = self._live_geometry()
        self.assertEqual(set(geometry), {lanes[1]})
        self.assertAlmostEqual(geometry[lanes[1]]["y"], workspace.nodes[lanes[0]].y)
        self.assertEqual(workspace.nodes[lanes[0]].y, 100.0)

        host = self._hosts("graphCanvasBackdropInputLayer")[lanes[0]]
        lane = workspace.nodes[lanes[0]]
        host.dragFinished.emit(lanes[0], lane.x + 300.0, lane.y + 150.0, True, "", False)
        self.app.processEvents()

        self.assertEqual(self._lane_order(pool_id), [lanes[1], lanes[0], lanes[2]])
        self.assertEqual(history.undo_depth(workspace.workspace_id), depth + 1)
        self.assertEqual(self._live_geometry(), {})
        self.assertEqual(canvas.property("liveDragAnchorNodeId"), "")

    def test_dragging_a_node_lights_up_the_lane_it_would_join(self) -> None:
        pool_id, lanes = self._pool()
        node_id = self.window.scene.add_node_from_type(PROCESS, 400.0, 160.0)  # in the first lane
        self.app.processEvents()
        canvas = self._graph_canvas_item()

        canvas.setLiveDragOffset(node_id, 0.0, 200.0, "", False)
        self._flush()

        self.assertEqual(dict(_variant(canvas.property("swimlaneDropTargetLookup"))), {lanes[1]: True})
        visual = self._hosts("graphCanvasBackdropLayer")
        self.assertTrue(self._surface_child(visual[lanes[1]], "graphNodeSwimlaneDropTarget").isVisible())
        self.assertFalse(self._surface_child(visual[lanes[0]], "graphNodeSwimlaneDropTarget").isVisible())

        canvas.clearLiveDragOffset()
        self.app.processEvents()
        self.assertEqual(dict(_variant(canvas.property("swimlaneDropTargetLookup")) or {}), {})


    # -- the Inspector's Lanes section --------------------------------------------------------------------------

    def _inspector_rows(self) -> list[dict]:
        return [dict(_variant(row)) for row in _variant(self.window.shell_inspector_bridge.selected_node_swimlane_lane_items)]

    def test_the_inspector_lists_a_pools_lanes_and_edits_them(self) -> None:
        pool_id, lanes = self._pool()
        workspace = self.window.model.active_workspace
        bridge = self.window.shell_inspector_bridge
        self.window.scene.select_node(pool_id, False)
        self.app.processEvents()

        self.assertTrue(bridge.selected_node_is_swimlane)
        self.assertEqual([row["lane_node_id"] for row in self._inspector_rows()], lanes)

        self.assertTrue(bridge.move_selected_swimlane_lane(lanes[0], 1))
        self.assertTrue(bridge.set_selected_swimlane_lane_title(lanes[2], "Warehouse"))
        self.assertTrue(bridge.set_selected_swimlane_lane_color(lanes[2], "#3fb37f"))
        self.app.processEvents()
        rows = self._inspector_rows()
        self.assertEqual([row["lane_node_id"] for row in rows], [lanes[1], lanes[0], lanes[2]])
        self.assertEqual((rows[2]["title"], rows[2]["color"]), ("Warehouse", "#3fb37f"))
        self.assertEqual(workspace.nodes[lanes[2]].properties["color"], "#3fb37f")
        self.assertFalse(bridge.set_selected_swimlane_lane_title(lanes[2], "  "))

        added = bridge.add_selected_swimlane_lane()
        self.assertTrue(added)
        self.assertEqual(self._lane_order(pool_id)[-1], added)
        self.assertTrue(bridge.remove_selected_swimlane_lane(added))
        self.assertEqual(len(self._lane_order(pool_id)), 3)

    def test_the_inspector_lanes_list_follows_canvas_edits_while_the_pool_is_selected(self) -> None:
        pool_id, lanes = self._pool()
        self.window.scene.select_node(pool_id, False)
        self.app.processEvents()
        pane = self._find_qml_item("inspectorPane")

        # A lane command from the canvas menu (the pool stays selected) refreshes the Lanes section.
        self._open_menu(lanes[2]).actionTriggered.emit("node_context::swimlane_move_before")
        wait_for_condition_or_raise(
            lambda: [str(_variant(row).get("lane_node_id")) for row in _variant(pane.property("selectedNodeSwimlaneLaneItems")) or []]
            == [lanes[0], lanes[2], lanes[1]],
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message="Timed out waiting for the Inspector's Lanes rows to follow the canvas reorder.",
        )
        card = next(item for item in self._walk_items(pane) if item.objectName() == "inspectorSwimlaneLanesCard")
        self.assertTrue(card.isVisible())


    # -- the floating toolbar -----------------------------------------------------------------------------------

    def _toolbar_actions(self, node_id: str) -> dict[str, dict]:
        """Select ``node_id`` alone and return its floating toolbar's actions by id."""
        self.window.scene.select_node(node_id, False)
        toolbar = self._find_qml_item("graphNodeFloatingToolbar")
        self.assertIsNotNone(toolbar)

        def actions() -> dict[str, dict]:
            host_data = _variant(toolbar.property("hostNodeData")) or {}
            if str(host_data.get("node_id", "")) != node_id or not bool(toolbar.property("toolbarActive")):
                return {}
            listed = [_variant(action) for action in _variant(toolbar.property("actionList")) or []]
            return {str(action.get("id", "")): action for action in listed}

        wait_for_condition_or_raise(
            lambda: bool(actions()),
            timeout_ms=1500,
            poll_interval_ms=20,
            app=self.app,
            timeout_message=f"Timed out waiting for the floating toolbar of {node_id}.",
        )
        return actions()

    def _click_orientation_switch(self, expected_tooltip: str) -> None:
        button = self._find_qml_item("graphNodeFloatingToolbarAction_" + SWITCH_ORIENTATION)
        self.assertIsNotNone(button)
        self.assertTrue(button.isVisible() and button.isEnabled())
        self.assertEqual(button.property("tooltipText"), expected_tooltip)
        button.clicked.emit()
        self.app.processEvents()

    def test_the_floating_toolbar_switches_a_lanes_whole_pool_to_the_other_orientation(self) -> None:
        pool_id, lanes = self._pool()
        workspace = self.window.model.active_workspace
        history = self.window.runtime_history
        depth = history.undo_depth(workspace.workspace_id)

        # The button names the orientation it switches to; on a lane in a pool it says the pool turns.
        action = self._toolbar_actions(lanes[1])[SWITCH_ORIENTATION]
        self.assertEqual(
            (action["label"], action["icon"], action["kind"], action.get("description")),
            ("Switch to vertical lanes", "swimlane-vertical", "surface", "Turns the whole pool"),
        )
        self._click_orientation_switch("Switch to vertical lanes\nTurns the whole pool")

        self.assertEqual(
            {workspace.nodes[node_id].properties["orientation"] for node_id in (pool_id, *lanes)},
            {"vertical"},
        )
        self.assertEqual(self._lane_order(pool_id), lanes)
        self.assertEqual(history.undo_depth(workspace.workspace_id), depth + 1)

        # The pool's own button switches back.
        action = self._toolbar_actions(pool_id)[SWITCH_ORIENTATION]
        self.assertEqual(
            (action["label"], action["icon"], action.get("description")),
            ("Switch to horizontal lanes", "swimlane-horizontal", None),
        )
        self._click_orientation_switch("Switch to horizontal lanes")
        self.assertEqual(workspace.nodes[pool_id].properties["orientation"], "horizontal")
        self.assertEqual(self._lane_order(pool_id), lanes)
        self.assertEqual(history.undo_depth(workspace.workspace_id), depth + 2)

    def test_the_floating_toolbar_turns_a_standalone_lane_and_skips_a_collapsed_pool(self) -> None:
        solo = self.window.scene.create_swimlane_lane(4000.0, 0.0, title="Solo")
        self.app.processEvents()
        workspace = self.window.model.active_workspace
        width, height = workspace.nodes[solo].custom_width, workspace.nodes[solo].custom_height

        self.assertNotIn("description", self._toolbar_actions(solo)[SWITCH_ORIENTATION])
        self._click_orientation_switch("Switch to vertical lanes")

        lane = workspace.nodes[solo]
        self.assertEqual(lane.properties["orientation"], "vertical")
        # It turns about its corner: length and thickness swap axes.
        self.assertAlmostEqual(lane.custom_width, height)
        self.assertAlmostEqual(lane.custom_height, width)

        # A collapsed pool keeps its orientation, as in its context menu.
        pool_id, _lanes = self._pool()
        self.window.scene.set_node_collapsed(pool_id, True)
        self.app.processEvents()
        actions = self._toolbar_actions(pool_id)
        self.assertIn("toggle_node_collapsed", actions)
        self.assertNotIn(SWITCH_ORIENTATION, actions)
