from __future__ import annotations

import inspect
from pathlib import Path

from ea_node_editor.nodes import decorators as _node_decorators

if "category" not in inspect.signature(_node_decorators.node_type).parameters:
    _original_node_type = _node_decorators.node_type

    def _compat_node_type(*args, category=None, **kwargs):
        if category is not None and "category_path" not in kwargs:
            if isinstance(category, (list, tuple)):
                kwargs["category_path"] = tuple(str(value) for value in category if str(value))
            else:
                normalized_category = str(category or "").strip()
                if normalized_category:
                    kwargs["category_path"] = (normalized_category,)
        return _original_node_type(*args, **kwargs)

    _node_decorators.node_type = _compat_node_type

from tests.graph_track_b.qml_support import (
    GraphCanvasQmlPreferenceTestBase,
    QObject,
    wait_for_condition_or_raise,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _variant(value):
    return value.toVariant() if hasattr(value, "toVariant") else value


class GraphCanvasFrameCoalescingTests(GraphCanvasQmlPreferenceTestBase):
    __test__ = True

    def _scheduler(self) -> QObject:
        scheduler = self.canvas.findChild(QObject, "graphCanvasFrameScheduler")
        self.assertIsNotNone(scheduler)
        return scheduler

    def test_scheduler_uses_frame_budget_by_default(self) -> None:
        scheduler = self._scheduler()

        self.assertEqual(int(scheduler.property("frameBudgetMs")), 16)

    def test_explicit_viewport_interaction_hold_is_distinct_from_wheel_idle_recovery(self) -> None:
        self.canvas.beginViewportInteraction()
        self.app.processEvents()
        self.assertTrue(bool(self.canvas.property("interactionActive")))
        self.assertTrue(bool(self.canvas.property("viewportInteractionHeld")))

        self.canvas.noteViewportInteraction()
        self.app.processEvents()
        self.assertTrue(bool(self.canvas.property("viewportInteractionHeld")))

        self.canvas.finishViewportInteractionSoon()
        self.app.processEvents()
        self.assertFalse(bool(self.canvas.property("viewportInteractionHeld")))

    def test_scheduler_coalesces_bursty_pan_deltas_into_one_view_commit(self) -> None:
        scheduler = self._scheduler()
        start_x = float(self.view.center_x)
        start_y = float(self.view.center_y)
        raw_before = int(scheduler.property("rawPanInputEventCount"))
        flushed_before = int(scheduler.property("flushedPanUpdateCount"))

        deltas = [(3.0, -2.0), (4.5, 1.5), (-1.0, 5.0), (2.5, -3.0)]
        for dx, dy in deltas:
            self.assertTrue(scheduler.queuePanBy(self.view, dx, dy))

        self.assertEqual(int(scheduler.property("rawPanInputEventCount")) - raw_before, len(deltas))
        self.assertEqual(int(scheduler.property("flushedPanUpdateCount")), flushed_before)
        self.assertAlmostEqual(float(self.view.center_x), start_x + sum(dx for dx, _ in deltas), places=6)
        self.assertAlmostEqual(float(self.view.center_y), start_y + sum(dy for _, dy in deltas), places=6)

        wait_for_condition_or_raise(
            lambda: int(scheduler.property("flushedPanUpdateCount")) == flushed_before + 1,
            timeout_ms=500,
            app=self.app,
            timeout_message="Timed out waiting for coalesced pan flush.",
        )

        self.assertAlmostEqual(float(self.view.center_x), start_x + sum(dx for dx, _ in deltas), places=6)
        self.assertAlmostEqual(float(self.view.center_y), start_y + sum(dy for _, dy in deltas), places=6)
        self.assertEqual(int(scheduler.property("flushedPanUpdateCount")) - flushed_before, 1)

    def test_scheduler_coalesces_wheel_zoom_steps_without_losing_cursor_anchor(self) -> None:
        scheduler = self._scheduler()
        cursor_x = 920.0
        cursor_y = 410.0
        scene_before_x = float(self.canvas.screenToSceneX(cursor_x))
        scene_before_y = float(self.canvas.screenToSceneY(cursor_y))
        raw_before = int(scheduler.property("rawZoomInputEventCount"))
        flushed_before = int(scheduler.property("flushedZoomUpdateCount"))

        for _ in range(3):
            self.assertTrue(scheduler.queueWheelZoom(self.canvas, self.view, 120.0, cursor_x, cursor_y))

        self.assertEqual(int(scheduler.property("rawZoomInputEventCount")) - raw_before, 3)
        self.assertEqual(int(scheduler.property("flushedZoomUpdateCount")), flushed_before)
        self.assertAlmostEqual(float(self.view.zoom_value), 1.15 ** 3, places=6)
        self.assertAlmostEqual(float(self.canvas.screenToSceneX(cursor_x)), scene_before_x, places=5)
        self.assertAlmostEqual(float(self.canvas.screenToSceneY(cursor_y)), scene_before_y, places=5)

        wait_for_condition_or_raise(
            lambda: int(scheduler.property("flushedZoomUpdateCount")) == flushed_before + 1,
            timeout_ms=500,
            app=self.app,
            timeout_message="Timed out waiting for coalesced wheel zoom flush.",
        )

        self.assertAlmostEqual(float(self.view.zoom_value), 1.15 ** 3, places=6)
        self.assertAlmostEqual(float(self.canvas.screenToSceneX(cursor_x)), scene_before_x, places=5)
        self.assertAlmostEqual(float(self.canvas.screenToSceneY(cursor_y)), scene_before_y, places=5)
        self.assertEqual(int(scheduler.property("flushedZoomUpdateCount")) - flushed_before, 1)

    def test_live_drag_scalars_keep_latest_values_and_flush_once_per_frame(self) -> None:
        scheduler = self._scheduler()
        raw_before = int(scheduler.property("rawLiveDragInputEventCount"))
        flushed_before = int(scheduler.property("flushedLiveDragUpdateCount"))
        profile_before = int(self.canvas.property("profileLiveDragOffsetUpdateCount"))
        membership_freezes_before = int(self.canvas.property("profileLiveDragMembershipFreezeCount"))

        self.canvas.setLiveDragOffset("node_a", 8.0, 2.0)
        frozen_ids = _variant(self.canvas.property("liveDragNodeIds"))
        frozen_lookup = _variant(self.canvas.property("liveDragNodeLookup"))
        self.canvas.setLiveDragOffset("node_a", 16.0, 6.0)
        self.canvas.setLiveDragOffset("node_a", 24.0, 10.0)

        self.assertEqual(int(scheduler.property("rawLiveDragInputEventCount")) - raw_before, 3)
        self.assertEqual(
            int(self.canvas.property("profileLiveDragMembershipFreezeCount")) - membership_freezes_before,
            1,
        )
        self.assertEqual(int(scheduler.property("flushedLiveDragUpdateCount")), flushed_before)
        self.assertEqual(frozen_ids, ["node_a"])
        self.assertEqual(frozen_lookup, {"node_a": True})
        self.assertEqual(_variant(self.canvas.property("liveDragNodeIds")), frozen_ids)
        self.assertEqual(_variant(self.canvas.property("liveDragNodeLookup")), frozen_lookup)
        self.assertEqual(float(self.canvas.property("liveDragDx")), 0.0)
        self.assertEqual(float(self.canvas.property("liveDragDy")), 0.0)

        edge_layer = self.canvas.findChild(QObject, "graphCanvasEdgeLayer")
        self.assertIsNotNone(edge_layer)
        if edge_layer is None:
            self.fail("Expected graph canvas edge layer")
        self.assertEqual(_variant(edge_layer.property("dragNodeLookup")), {"node_a": True})
        self.assertEqual(float(edge_layer.property("dragDx")), 0.0)
        self.assertEqual(float(edge_layer.property("dragDy")), 0.0)

        wait_for_condition_or_raise(
            lambda: int(scheduler.property("flushedLiveDragUpdateCount")) == flushed_before + 1,
            timeout_ms=500,
            app=self.app,
            timeout_message="Timed out waiting for coalesced live-drag flush.",
        )

        self.assertEqual(_variant(self.canvas.property("liveDragNodeIds")), frozen_ids)
        self.assertEqual(_variant(self.canvas.property("liveDragNodeLookup")), frozen_lookup)
        self.assertEqual(float(self.canvas.property("liveDragDx")), 24.0)
        self.assertEqual(float(self.canvas.property("liveDragDy")), 10.0)
        self.assertEqual(_variant(edge_layer.property("dragNodeLookup")), frozen_lookup)
        self.assertEqual(float(edge_layer.property("dragDx")), 24.0)
        self.assertEqual(float(edge_layer.property("dragDy")), 10.0)
        self.assertEqual(int(self.canvas.property("profileLiveDragOffsetUpdateCount")) - profile_before, 1)

        self.canvas.clearLiveDragOffset()
        self.app.processEvents()
        self.assertEqual(_variant(self.canvas.property("liveDragNodeIds")), [])
        self.assertEqual(_variant(self.canvas.property("liveDragNodeLookup")), {})

    def test_native_overlay_suppression_tracks_live_drag_and_active_wire_drag(self) -> None:
        self.assertFalse(bool(self.canvas.property("nativeOverlaySuppressionActive")))

        self.canvas.setLiveDragOffset("node_a", 8.0, 2.0)
        self.app.processEvents()
        self.assertTrue(bool(self.canvas.property("nativeOverlaySuppressionActive")))

        self.canvas.clearLiveDragOffset()
        self.app.processEvents()
        self.assertFalse(bool(self.canvas.property("nativeOverlaySuppressionActive")))

        self.assertTrue(self.canvas.setProperty("wireDragState", {"active": True}))
        self.app.processEvents()
        self.assertTrue(bool(self.canvas.property("nativeOverlaySuppressionActive")))

        self.assertTrue(self.canvas.setProperty("wireDragState", None))
        self.app.processEvents()
        self.assertFalse(bool(self.canvas.property("nativeOverlaySuppressionActive")))

    def test_node_drag_fast_path_keeps_anchor_motion_on_live_offset_scheduler(self) -> None:
        qml_root = _REPO_ROOT / "ea_node_editor" / "ui_qml" / "components"
        gesture_text = (qml_root / "graph" / "GraphNodeHostGestureLayer.qml").read_text(encoding="utf-8")
        host_text = (qml_root / "graph" / "GraphNodeHost.qml").read_text(encoding="utf-8")
        delegate_text = (qml_root / "graph_canvas" / "GraphCanvasNodeDelegate.qml").read_text(encoding="utf-8")

        self.assertIn("drag.target: null", gesture_text)
        self.assertIn("manualDragActive", gesture_text)
        self.assertIn("nodeDragArea.mapToItem", gesture_text)
        self.assertIn("_emitDragOffset(mouse, false)", gesture_text)
        self.assertIn("suppressNextClick", gesture_text)
        self.assertNotIn("root.host.x - root.host.worldOffset - root.host.nodeData.x", gesture_text)
        self.assertNotIn("mouse.x) - pressLocalX", gesture_text)
        self.assertIn("liveDragDx: 0.0", delegate_text)
        self.assertIn("liveDragDy: 0.0", delegate_text)
        self.assertNotIn("liveDragDxForNode", delegate_text)
        self.assertNotIn("liveDragDyForNode", delegate_text)
        self.assertIn("x: card.liveDragDx", host_text)
        self.assertIn("y: card.liveDragDy", host_text)
        self.assertIn("canvasItem.snappedDragDelta", delegate_text)
        self.assertIn("if (!movedByCommit)", delegate_text)
        self.assertIn("bridge.move_nodes_by_delta", delegate_text)
        self.assertIn("bridge.move_node(nodeId, finalSnappedX, finalSnappedY);", delegate_text)

    def test_drag_membership_and_host_timers_use_one_canvas_owner(self) -> None:
        qml_root = _REPO_ROOT / "ea_node_editor" / "ui_qml" / "components"
        state_text = (qml_root / "graph_canvas" / "GraphCanvasSceneState.qml").read_text(encoding="utf-8")
        host_text = (qml_root / "graph" / "GraphNodeHost.qml").read_text(encoding="utf-8")
        scheduler_text = (qml_root / "graph_canvas" / "GraphCanvasFrameScheduler.qml").read_text(encoding="utf-8")

        self.assertIn("function _freezeLiveDragMembership(anchorNodeId)", state_text)
        self.assertIn("property var liveDragNodeLookup", state_text)
        self.assertIn("property real liveDragDx", state_text)
        self.assertNotIn("liveDragOffsets", state_text)
        self.assertNotIn("Timer {", host_text)
        self.assertIn("scheduleToolbarGrace", scheduler_text)
        self.assertIn("registerElapsedHost", scheduler_text)
