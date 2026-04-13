from __future__ import annotations

import inspect

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
    GraphCanvasCommandBridge,
    GraphCanvasQmlPreferenceTestBase,
    QMetaObject,
    QObject,
    QPoint,
    QQuickWindow,
    QTest,
    Qt,
    ViewportBridge,
    _GraphCanvasPerformancePreferenceBridge,
    _named_child_items,
    pyqtProperty,
    pyqtSignal,
    wait_for_condition_or_raise,
)

_CANVAS_IDLE_SETTLE_TIMEOUT_MS = 6500


class GraphCanvasQmlPreferencePerformanceTests(GraphCanvasQmlPreferenceTestBase):
    __test__ = True

    def test_viewport_applies_zoom_and_center_updates_without_forcing_viewport_cache_mode(self) -> None:
        world = self.canvas.findChild(QObject, "graphCanvasWorld")
        self.assertIsNotNone(world)
        self.assertFalse(bool(self.canvas.property("interactionActive")))
        self.assertFalse(bool(self.canvas.property("viewportInteractionWorldCacheActive")))
        self.assertTrue(bool(self.canvas.property("highQualityRendering")))

        self.view.set_zoom(2.5)
        self.view.centerOn(12.0, 18.0)
        self.app.processEvents()

        self.assertFalse(bool(self.canvas.property("interactionActive")))
        self.assertFalse(bool(self.canvas.property("viewportInteractionWorldCacheActive")))
        self.assertTrue(bool(self.canvas.property("highQualityRendering")))
        self.assertAlmostEqual(float(world.property("scale")), 2.5, places=6)
        expected_x = 1280.0 * 0.5 - ((12.0 + float(self.canvas.property("worldOffset"))) * 2.5)
        expected_y = 720.0 * 0.5 - ((18.0 + float(self.canvas.property("worldOffset"))) * 2.5)
        self.assertAlmostEqual(float(world.property("x")), expected_x, places=6)
        self.assertAlmostEqual(float(world.property("y")), expected_y, places=6)

    def test_graph_canvas_wheel_zoom_keeps_cursor_anchor_with_single_viewport_commit(self) -> None:
        self.view.centerOn(60.0, -30.0)
        self.app.processEvents()

        commits = 0

        def _count_commit() -> None:
            nonlocal commits
            commits += 1

        self.view.view_state_changed.connect(_count_commit)

        cursor_x = 920.0
        cursor_y = 410.0
        scene_before_x = float(self.canvas.screenToSceneX(cursor_x))
        scene_before_y = float(self.canvas.screenToSceneY(cursor_y))

        applied = self.canvas.applyWheelZoom(
            {"x": cursor_x, "y": cursor_y, "angleDelta": {"y": 120}, "inverted": False}
        )
        self.assertTrue(applied)
        self.app.processEvents()

        scene_after_x = float(self.canvas.screenToSceneX(cursor_x))
        scene_after_y = float(self.canvas.screenToSceneY(cursor_y))
        self.assertEqual(commits, 1)
        self.assertAlmostEqual(float(self.view.zoom_value), 1.15, places=6)
        self.assertAlmostEqual(scene_before_x, scene_after_x, places=6)
        self.assertAlmostEqual(scene_before_y, scene_after_y, places=6)

    def test_graph_canvas_right_hold_box_zoom_frames_viewport_rect(self) -> None:
        window = QQuickWindow()
        window.resize(1280, 720)
        self.canvas.setParentItem(window.contentItem())
        window.show()
        self.app.processEvents()

        start = QPoint(200, 120)
        end = QPoint(700, 370)

        try:
            QTest.mousePress(window, Qt.MouseButton.RightButton, Qt.KeyboardModifier.NoModifier, start)
            QTest.mouseMove(window, end)
            self.app.processEvents()

            wait_for_condition_or_raise(
                lambda: bool(self.canvas.property("interactionActive")),
                timeout_ms=500,
                app=self.app,
                timeout_message="Timed out waiting for graph canvas box-zoom drag to arm.",
            )

            QTest.mouseRelease(window, Qt.MouseButton.RightButton, Qt.KeyboardModifier.NoModifier, end)
            self.app.processEvents()

            self.assertAlmostEqual(float(self.view.zoom_value), 2.464, places=3)
            self.assertAlmostEqual(float(self.view.center_x), -190.0, places=3)
            self.assertAlmostEqual(float(self.view.center_y), -115.0, places=3)

            wait_for_condition_or_raise(
                lambda: not bool(self.canvas.property("interactionActive")),
                timeout_ms=_CANVAS_IDLE_SETTLE_TIMEOUT_MS,
                app=self.app,
                timeout_message="Timed out waiting for graph canvas box-zoom interaction to settle.",
            )
        finally:
            self.canvas.setParentItem(None)
            window.close()
            window.deleteLater()
            self.app.processEvents()

    def test_graph_canvas_performance_policy_resolves_max_performance_idle_without_visual_degradation(self) -> None:
        policy = self.canvas.findChild(QObject, "graphCanvasPerformancePolicy")
        background = self.canvas.findChild(QObject, "graphCanvasBackground")
        minimap_overlay = self.canvas.findChild(QObject, "graphCanvasMinimapOverlay")
        minimap_viewport = self.canvas.findChild(QObject, "graphCanvasMinimapViewport")
        self.assertIsNotNone(policy)
        self.assertIsNotNone(background)
        self.assertIsNotNone(minimap_overlay)
        self.assertIsNotNone(minimap_viewport)

        self.bridge.set_graphics_performance_mode_value("max_performance")
        self.app.processEvents()

        self.assertEqual(self.canvas.property("resolvedGraphicsPerformanceMode"), "max_performance")
        self.assertFalse(bool(self.canvas.property("mutationBurstActive")))
        self.assertFalse(bool(self.canvas.property("transientPerformanceActivityActive")))
        self.assertFalse(bool(self.canvas.property("transientDegradedWindowActive")))
        self.assertFalse(bool(self.canvas.property("viewportInteractionWorldCacheActive")))
        self.assertTrue(bool(self.canvas.property("highQualityRendering")))
        self.assertFalse(bool(self.canvas.property("edgeLabelSimplificationActive")))
        self.assertFalse(bool(self.canvas.property("gridSimplificationActive")))
        self.assertFalse(bool(self.canvas.property("minimapSimplificationActive")))
        self.assertFalse(bool(self.canvas.property("shadowSimplificationActive")))
        self.assertFalse(bool(self.canvas.property("snapshotProxyReuseActive")))
        self.assertTrue(bool(background.property("effectiveShowGrid")))
        self.assertTrue(bool(minimap_overlay.property("minimapContentVisible")))
        self.assertTrue(bool(minimap_viewport.property("visible")))
        self.assertEqual(policy.property("resolvedMode"), "max_performance")

    def test_graph_canvas_performance_policy_keeps_node_chrome_shadow_cache_stable_through_transient_windows(self) -> None:
        from PyQt6.QtCore import pyqtProperty, pyqtSignal

        node_id = "node_preference_cache_test"
        node_payload = {
            "node_id": node_id,
            "type_id": "core.logger",
            "title": "Logger",
            "x": 120.0,
            "y": 140.0,
            "width": 210.0,
            "height": 88.0,
            "accent": "#2F89FF",
            "collapsed": False,
            "selected": False,
            "runtime_behavior": "active",
            "surface_family": "standard",
            "surface_variant": "",
            "surface_metrics": {
                "default_width": 210.0,
                "default_height": 88.0,
                "min_width": 120.0,
                "min_height": 50.0,
                "collapsed_width": 130.0,
                "collapsed_height": 36.0,
                "header_height": 24.0,
                "header_top_margin": 4.0,
                "body_top": 30.0,
                "body_height": 30.0,
                "port_top": 60.0,
                "port_height": 18.0,
                "port_center_offset": 6.0,
                "port_side_margin": 8.0,
                "port_dot_radius": 3.5,
                "resize_handle_size": 16.0,
            },
            "visual_style": {},
            "can_enter_scope": False,
            "ports": [
                {
                    "key": "exec_in",
                    "label": "Exec In",
                    "direction": "in",
                    "kind": "exec",
                    "data_type": "exec",
                    "connected": False,
                },
                {
                    "key": "exec_out",
                    "label": "Exec Out",
                    "direction": "out",
                    "kind": "exec",
                    "data_type": "exec",
                    "connected": False,
                },
            ],
            "inline_properties": [
                {
                    "key": "message",
                    "label": "Message",
                    "inline_editor": "text",
                    "value": "log message",
                    "overridden_by_input": False,
                    "input_port_label": "message",
                }
            ],
        }

        class CanvasStateBridgeStub(QObject):
            graphics_preferences_changed = pyqtSignal()
            snap_to_grid_changed = pyqtSignal()
            scene_nodes_changed = pyqtSignal()
            scene_edges_changed = pyqtSignal()
            scene_selection_changed = pyqtSignal()
            view_state_changed = pyqtSignal()

            def __init__(self, preference_bridge: _GraphCanvasPerformancePreferenceBridge, viewport_bridge: ViewportBridge):
                super().__init__()
                self._preference_bridge = preference_bridge
                self._viewport_bridge = viewport_bridge
                self._nodes_model = [dict(node_payload)]
                self._selected_node_lookup: dict[str, bool] = {}
                self._preference_bridge.graphics_preferences_changed.connect(self.graphics_preferences_changed.emit)
                self._viewport_bridge.view_state_changed.connect(self.view_state_changed.emit)

            @pyqtProperty(QObject, constant=True)
            def viewport_bridge(self) -> ViewportBridge:
                return self._viewport_bridge

            @pyqtProperty(bool, notify=graphics_preferences_changed)
            def graphics_minimap_expanded(self) -> bool:
                return bool(self._preference_bridge.graphics_minimap_expanded)

            @pyqtProperty(bool, notify=graphics_preferences_changed)
            def graphics_show_grid(self) -> bool:
                return bool(self._preference_bridge.graphics_show_grid)

            @pyqtProperty(str, notify=graphics_preferences_changed)
            def graphics_grid_style(self) -> str:
                return str(self._preference_bridge.graphics_grid_style)

            @pyqtProperty(str, notify=graphics_preferences_changed)
            def graphics_edge_crossing_style(self) -> str:
                return str(self._preference_bridge.graphics_edge_crossing_style)

            @pyqtProperty(bool, notify=graphics_preferences_changed)
            def graphics_show_minimap(self) -> bool:
                return bool(self._preference_bridge.graphics_show_minimap)

            @pyqtProperty(bool, notify=graphics_preferences_changed)
            def graphics_node_shadow(self) -> bool:
                return bool(self._preference_bridge.graphics_node_shadow)

            @pyqtProperty(int, notify=graphics_preferences_changed)
            def graphics_shadow_strength(self) -> int:
                return int(self._preference_bridge.graphics_shadow_strength)

            @pyqtProperty(int, notify=graphics_preferences_changed)
            def graphics_shadow_softness(self) -> int:
                return int(self._preference_bridge.graphics_shadow_softness)

            @pyqtProperty(int, notify=graphics_preferences_changed)
            def graphics_shadow_offset(self) -> int:
                return int(self._preference_bridge.graphics_shadow_offset)

            @pyqtProperty(str, notify=graphics_preferences_changed)
            def graphics_performance_mode(self) -> str:
                return str(self._preference_bridge.graphics_performance_mode)

            @pyqtProperty(bool, notify=snap_to_grid_changed)
            def snap_to_grid_enabled(self) -> bool:
                return bool(self._preference_bridge.snap_to_grid_enabled)

            @pyqtProperty(float, constant=True)
            def snap_grid_size(self) -> float:
                return float(self._preference_bridge.snap_grid_size)

            @pyqtProperty("QVariantList", notify=scene_nodes_changed)
            def nodes_model(self) -> list[dict[str, object]]:
                return list(self._nodes_model)

            @pyqtProperty("QVariantList", notify=scene_nodes_changed)
            def minimap_nodes_model(self) -> list[dict[str, object]]:
                return list(self._nodes_model)

            @pyqtProperty("QVariantMap", notify=scene_nodes_changed)
            def workspace_scene_bounds_payload(self) -> dict[str, float]:
                return {
                    "x": 120.0,
                    "y": 140.0,
                    "width": 210.0,
                    "height": 88.0,
                }

            @pyqtProperty("QVariantList", notify=scene_edges_changed)
            def edges_model(self) -> list[dict[str, object]]:
                return []

            @pyqtProperty("QVariantMap", notify=scene_selection_changed)
            def selected_node_lookup(self) -> dict[str, bool]:
                return dict(self._selected_node_lookup)

            def select_node(self, node_id_value: str) -> None:
                normalized = str(node_id_value or "")
                self._selected_node_lookup = {normalized: True} if normalized else {}
                self.scene_selection_changed.emit()

            def are_port_kinds_compatible(self, _source_kind: str, _target_kind: str) -> bool:
                return True

            def are_data_types_compatible(self, _source_type: str, _target_type: str) -> bool:
                return True

        self._performance_preference_bridge = _GraphCanvasPerformancePreferenceBridge()
        self._performance_preference_bridge.set_graphics_performance_mode_value("max_performance")
        self._performance_state_bridge = CanvasStateBridgeStub(
            self._performance_preference_bridge,
            self.view,
        )

        self.canvas.deleteLater()
        self.app.processEvents()

        performance_command_bridge = GraphCanvasCommandBridge(view_bridge=self.view)
        self.canvas = self._create_canvas(
            {
                "canvasStateBridge": self._performance_state_bridge,
                "canvasCommandBridge": performance_command_bridge,
                "width": 1280.0,
                "height": 720.0,
            }
        )

        wait_for_condition_or_raise(
            lambda: len(_named_child_items(self.canvas, "graphNodeCard")) == 1,
            timeout_ms=200,
            app=self.app,
            timeout_message="Timed out waiting for graph canvas node host to appear.",
        )
        node_card = _named_child_items(self.canvas, "graphNodeCard")[0]
        background_layer = node_card.findChild(QObject, "graphNodeChromeBackgroundLayer")
        shadow_item = node_card.findChild(QObject, "graphNodeShadow")
        self.assertIsNotNone(background_layer)
        self.assertIsNotNone(shadow_item)
        self.assertTrue(bool(background_layer.property("cacheActive")))
        self.assertTrue(bool(background_layer.property("chromeCacheActive")))
        self.assertTrue(bool(background_layer.property("shadowCacheActive")))
        self.assertTrue(bool(shadow_item.property("cached")))

        baseline_key = str(background_layer.property("cacheKey") or "")
        self.assertTrue(baseline_key)
        self.assertFalse(bool(self.canvas.property("transientDegradedWindowActive")))

        applied = self.canvas.applyWheelZoom(
            {"x": 640.0, "y": 360.0, "angleDelta": {"y": 120}, "inverted": False}
        )
        self.assertTrue(applied)
        self.app.processEvents()

        self.assertTrue(bool(self.canvas.property("interactionActive")))
        self.assertTrue(bool(self.canvas.property("transientDegradedWindowActive")))
        self.assertEqual(str(background_layer.property("cacheKey") or ""), baseline_key)
        self.assertTrue(bool(shadow_item.property("cached")))

        wait_for_condition_or_raise(
            lambda: (
                not bool(self.canvas.property("interactionActive"))
                and not bool(self.canvas.property("transientDegradedWindowActive"))
                and str(background_layer.property("cacheKey") or "") == baseline_key
            ),
            timeout_ms=_CANVAS_IDLE_SETTLE_TIMEOUT_MS,
            app=self.app,
            timeout_message="Timed out waiting for cached node chrome/shadow state to recover after wheel zoom.",
        )
        self.assertEqual(str(background_layer.property("cacheKey") or ""), baseline_key)

        self._performance_state_bridge.select_node(node_id)
        wait_for_condition_or_raise(
            lambda: str(background_layer.property("cacheKey") or "") != baseline_key,
            timeout_ms=200,
            app=self.app,
            timeout_message="Timed out waiting for selection-border cache invalidation.",
        )
        selected_key = str(background_layer.property("cacheKey") or "")

        self._performance_preference_bridge.set_graphics_shadow_softness_value(35)
        wait_for_condition_or_raise(
            lambda: str(background_layer.property("cacheKey") or "") != selected_key,
            timeout_ms=200,
            app=self.app,
            timeout_message="Timed out waiting for shadow-preference cache invalidation.",
        )

    def test_graph_canvas_mutation_burst_policy_activates_and_recovers_with_existing_idle_window(self) -> None:
        policy = self.canvas.findChild(QObject, "graphCanvasPerformancePolicy")
        background = self.canvas.findChild(QObject, "graphCanvasBackground")
        minimap_overlay = self.canvas.findChild(QObject, "graphCanvasMinimapOverlay")
        minimap_viewport = self.canvas.findChild(QObject, "graphCanvasMinimapViewport")
        self.assertIsNotNone(policy)
        self.assertIsNotNone(background)
        self.assertIsNotNone(minimap_overlay)
        self.assertIsNotNone(minimap_viewport)

        self.bridge.set_graphics_performance_mode_value("max_performance")
        self.app.processEvents()

        QMetaObject.invokeMethod(
            policy,
            "noteStructuralMutation",
            Qt.ConnectionType.DirectConnection,
        )
        self.app.processEvents()

        self.assertTrue(bool(policy.property("mutationBurstActive")))
        self.assertTrue(bool(self.canvas.property("mutationBurstActive")))
        self.assertTrue(bool(self.canvas.property("transientPerformanceActivityActive")))
        self.assertTrue(bool(self.canvas.property("transientDegradedWindowActive")))
        self.assertFalse(bool(self.canvas.property("highQualityRendering")))
        self.assertTrue(bool(self.canvas.property("edgeLabelSimplificationActive")))
        self.assertTrue(bool(self.canvas.property("gridSimplificationActive")))
        self.assertTrue(bool(self.canvas.property("minimapSimplificationActive")))
        self.assertTrue(bool(self.canvas.property("shadowSimplificationActive")))
        self.assertTrue(bool(self.canvas.property("snapshotProxyReuseActive")))
        self.assertFalse(bool(background.property("effectiveShowGrid")))
        self.assertFalse(bool(minimap_overlay.property("minimapContentVisible")))
        self.assertFalse(bool(minimap_viewport.property("visible")))

        wait_for_condition_or_raise(
            lambda: not bool(self.canvas.property("mutationBurstActive")),
            timeout_ms=_CANVAS_IDLE_SETTLE_TIMEOUT_MS,
            app=self.app,
            timeout_message="Timed out waiting for synthetic mutation burst policy to settle.",
        )
        self.assertFalse(bool(self.canvas.property("transientPerformanceActivityActive")))
        self.assertFalse(bool(self.canvas.property("transientDegradedWindowActive")))
        self.assertTrue(bool(self.canvas.property("highQualityRendering")))
        self.assertFalse(bool(self.canvas.property("edgeLabelSimplificationActive")))
        self.assertFalse(bool(self.canvas.property("gridSimplificationActive")))
        self.assertFalse(bool(self.canvas.property("minimapSimplificationActive")))
        self.assertFalse(bool(self.canvas.property("shadowSimplificationActive")))
        self.assertFalse(bool(self.canvas.property("snapshotProxyReuseActive")))
        self.assertTrue(bool(background.property("effectiveShowGrid")))
        self.assertTrue(bool(minimap_overlay.property("minimapContentVisible")))
        self.assertTrue(bool(minimap_viewport.property("visible")))

    def test_edge_layer_gap_break_metadata_respects_style_and_performance_gates(self) -> None:
        edge_layer = self._create_edge_layer({"viewBridge": self.view})
        self.view.centerOn(200.0, 200.0)
        self.app.processEvents()

        def _bezier_edge(edge_id: str, sx: float, sy: float, tx: float, ty: float) -> dict[str, object]:
            return {
                "edge_id": edge_id,
                "source_node_id": "",
                "source_port_key": "",
                "target_node_id": "",
                "target_port_key": "",
                "source_port_kind": "data",
                "target_port_kind": "data",
                "edge_family": "standard",
                "label": "",
                "visual_style": {},
                "flow_style": {},
                "source_port_side": "right",
                "target_port_side": "left",
                "source_anchor_side": "right",
                "target_anchor_side": "left",
                "source_anchor_kind": "scene",
                "target_anchor_kind": "scene",
                "source_anchor_node_id": "",
                "target_anchor_node_id": "",
                "source_hidden_by_backdrop_id": "",
                "target_hidden_by_backdrop_id": "",
                "source_anchor_bounds": None,
                "target_anchor_bounds": None,
                "lane_bias": 0.0,
                "sx": sx,
                "sy": sy,
                "tx": tx,
                "ty": ty,
                "c1x": sx + 72.0,
                "c1y": sy,
                "c2x": tx - 72.0,
                "c2y": ty,
                "route": "bezier",
                "pipe_points": [],
                "color": "#7AA8FF",
                "data_type_warning": False,
            }

        selected_edge_id = "selected_over"
        plain_edge_id = "plain_under"
        edge_layer.setProperty(
            "edges",
            [
                _bezier_edge(selected_edge_id, 80.0, 320.0, 320.0, 80.0),
                _bezier_edge(plain_edge_id, 80.0, 80.0, 320.0, 320.0),
            ],
        )
        edge_layer.setProperty("selectedEdgeIds", [selected_edge_id])
        self.app.processEvents()
        edge_layer.requestRedraw()
        self.app.processEvents()

        baseline_under = edge_layer._visibleEdgeSnapshot(plain_edge_id).toVariant()
        baseline_selected = edge_layer._visibleEdgeSnapshot(selected_edge_id).toVariant()
        self.assertEqual(baseline_under["drawOrderIndex"], 0)
        self.assertEqual(baseline_selected["drawOrderIndex"], 1)
        self.assertEqual(baseline_under["crossingBreaks"], [])
        self.assertEqual(baseline_selected["crossingBreaks"], [])

        edge_layer.setProperty("edgeCrossingStyle", "gap_break")
        self.app.processEvents()
        edge_layer.requestRedraw()
        self.app.processEvents()

        decorated_under = edge_layer._visibleEdgeSnapshot(plain_edge_id).toVariant()
        decorated_selected = edge_layer._visibleEdgeSnapshot(selected_edge_id).toVariant()
        self.assertEqual(decorated_under["drawOrderIndex"], 0)
        self.assertEqual(decorated_selected["drawOrderIndex"], 1)
        self.assertGreaterEqual(len(decorated_under["crossingBreaks"]), 1)
        self.assertEqual(decorated_selected["crossingBreaks"], [])
        self.assertIn("centerX", decorated_under["crossingBreaks"][0])
        self.assertIn("tangentX", decorated_under["crossingBreaks"][0])

        self.view.set_zoom(2.0)
        edge_layer.setProperty("viewportInteractionActive", True)
        edge_layer.setProperty("transientPerformanceActivityActive", True)
        self.app.processEvents()
        edge_layer.requestRedraw()
        self.app.processEvents()

        active_under = edge_layer._visibleEdgeSnapshot(plain_edge_id).toVariant()
        active_selected = edge_layer._visibleEdgeSnapshot(selected_edge_id).toVariant()
        self.assertEqual(active_under["crossingBreaks"], decorated_under["crossingBreaks"])
        self.assertEqual(active_under["crossingSamplePoints"], decorated_under["crossingSamplePoints"])
        self.assertEqual(active_selected["crossingBreaks"], [])

        edge_layer.setProperty("viewportInteractionActive", False)
        edge_layer.setProperty("transientPerformanceActivityActive", False)
        self.app.processEvents()
        edge_layer.requestRedraw()
        self.app.processEvents()

        settled_under = edge_layer._visibleEdgeSnapshot(plain_edge_id).toVariant()
        settled_selected = edge_layer._visibleEdgeSnapshot(selected_edge_id).toVariant()
        self.assertGreaterEqual(len(settled_under["crossingBreaks"]), 1)
        self.assertNotEqual(
            settled_under["crossingBreaks"][0]["startDistance"],
            decorated_under["crossingBreaks"][0]["startDistance"],
        )
        self.assertNotEqual(settled_under["crossingSamplePoints"], decorated_under["crossingSamplePoints"])
        self.assertEqual(settled_selected["crossingBreaks"], [])

        edge_layer.setProperty("performanceMode", "max_performance")
        self.app.processEvents()
        edge_layer.requestRedraw()
        self.app.processEvents()

        suppressed_under = edge_layer._visibleEdgeSnapshot(plain_edge_id).toVariant()
        suppressed_selected = edge_layer._visibleEdgeSnapshot(selected_edge_id).toVariant()
        self.assertEqual(suppressed_under["crossingBreaks"], [])
        self.assertEqual(suppressed_selected["crossingBreaks"], [])

        edge_layer.setProperty("performanceMode", "full_fidelity")
        edge_layer.setProperty("transientDegradedWindowActive", True)
        self.app.processEvents()
        edge_layer.requestRedraw()
        self.app.processEvents()

        degraded_under = edge_layer._visibleEdgeSnapshot(plain_edge_id).toVariant()
        degraded_selected = edge_layer._visibleEdgeSnapshot(selected_edge_id).toVariant()
        self.assertEqual(degraded_under["crossingBreaks"], [])
        self.assertEqual(degraded_selected["crossingBreaks"], [])

        edge_layer.deleteLater()
        self.app.processEvents()

    def test_graph_canvas_propagates_visible_scene_rect_payload_to_edge_layer(self) -> None:
        edge_layer = self.canvas.findChild(QObject, "graphCanvasEdgeLayer")
        self.assertIsNotNone(edge_layer)

        payload = edge_layer.property("visibleSceneRectPayload")
        self.assertEqual(payload, {"x": -640.0, "y": -360.0, "width": 1280.0, "height": 720.0})

        self.view.set_zoom(2.0)
        self.view.centerOn(120.0, -60.0)
        self.app.processEvents()

        payload = edge_layer.property("visibleSceneRectPayload")
        self.assertEqual(payload, {"x": -200.0, "y": -240.0, "width": 640.0, "height": 360.0})

    def test_graph_canvas_coalesces_view_state_redraw_requests_per_commit(self) -> None:
        background = self.canvas.findChild(QObject, "graphCanvasBackground")
        edge_layer = self.canvas.findChild(QObject, "graphCanvasEdgeLayer")

        self.assertIsNotNone(background)
        self.assertIsNotNone(edge_layer)

        background_redraws = int(background.property("_redrawRequestCount"))
        edge_redraws = int(edge_layer.property("_redrawRequestCount"))
        background_cache_builds = int(background.property("_gridCacheBuildCount"))

        self.view.set_zoom(1.4)
        self.assertEqual(int(background.property("_redrawRequestCount")) - background_redraws, 0)
        self.assertEqual(int(edge_layer.property("_redrawRequestCount")) - edge_redraws, 0)
        wait_for_condition_or_raise(
            lambda: int(background.property("_redrawRequestCount")) - background_redraws == 1
            and int(edge_layer.property("_redrawRequestCount")) - edge_redraws == 1,
            timeout_ms=120,
            app=self.app,
            timeout_message="Timed out waiting for deferred zoom redraw flush.",
        )

        self.assertEqual(int(background.property("_redrawRequestCount")) - background_redraws, 1)
        self.assertEqual(int(edge_layer.property("_redrawRequestCount")) - edge_redraws, 1)
        self.assertEqual(int(background.property("_gridCacheBuildCount")) - background_cache_builds, 1)

        background_redraws = int(background.property("_redrawRequestCount"))
        edge_redraws = int(edge_layer.property("_redrawRequestCount"))
        background_cache_builds = int(background.property("_gridCacheBuildCount"))

        self.view.centerOn(18.0, -22.0)
        self.assertEqual(int(background.property("_redrawRequestCount")) - background_redraws, 0)
        self.assertEqual(int(edge_layer.property("_redrawRequestCount")) - edge_redraws, 0)
        wait_for_condition_or_raise(
            lambda: int(background.property("_redrawRequestCount")) - background_redraws == 1
            and int(edge_layer.property("_redrawRequestCount")) - edge_redraws == 1,
            timeout_ms=120,
            app=self.app,
            timeout_message="Timed out waiting for deferred pan redraw flush.",
        )

        self.assertEqual(int(background.property("_redrawRequestCount")) - background_redraws, 1)
        self.assertEqual(int(edge_layer.property("_redrawRequestCount")) - edge_redraws, 1)
        self.assertEqual(int(background.property("_gridCacheBuildCount")) - background_cache_builds, 0)

        commits = 0

        def _count_commit() -> None:
            nonlocal commits
            commits += 1

        self.view.view_state_changed.connect(_count_commit)
        background_redraws = int(background.property("_redrawRequestCount"))
        edge_redraws = int(edge_layer.property("_redrawRequestCount"))

        applied = self.canvas.applyWheelZoom(
            {"x": 920.0, "y": 410.0, "angleDelta": {"y": 120}, "inverted": False}
        )

        self.assertTrue(applied)
        self.assertEqual(commits, 1)
        self.assertEqual(int(background.property("_redrawRequestCount")) - background_redraws, 0)
        self.assertEqual(int(edge_layer.property("_redrawRequestCount")) - edge_redraws, 0)
        wait_for_condition_or_raise(
            lambda: int(background.property("_redrawRequestCount")) - background_redraws == 1
            and int(edge_layer.property("_redrawRequestCount")) - edge_redraws == 1,
            timeout_ms=120,
            app=self.app,
            timeout_message="Timed out waiting for deferred wheel redraw flush.",
        )

        self.assertEqual(int(background.property("_redrawRequestCount")) - background_redraws, 1)
        self.assertEqual(int(edge_layer.property("_redrawRequestCount")) - edge_redraws, 1)

    def test_graph_canvas_input_layers_disable_full_canvas_hover_tracking(self) -> None:
        marquee_area = self.canvas.findChild(QObject, "graphCanvasMarqueeArea")
        pan_area = self.canvas.findChild(QObject, "graphCanvasPanArea")

        self.assertIsNotNone(marquee_area)
        self.assertIsNotNone(pan_area)
        self.assertFalse(bool(marquee_area.property("hoverEnabled")))
        self.assertFalse(bool(pan_area.property("hoverEnabled")))

__all__ = ['GraphCanvasQmlPreferencePerformanceTests']
