from __future__ import annotations

from tests.graph_track_b.qml_support import (
    GraphCanvasCommandBridge,
    GraphCanvasQmlPreferenceTestBase,
    GraphModel,
    GraphSceneBridge,
    QObject,
    QMetaObject,
    QQmlComponent,
    QQuickWindow,
    QTest,
    Qt,
    QUrl,
    ViewportBridge,
    _GRAPH_CANVAS_QML_PATH,
    _NODE_CARD_QML_PATH,
    _GraphCanvasPreferenceBridge,
    _build_edge_crossing_pipe_registry,
    _named_child_items,
    pyqtProperty,
    pyqtSignal,
    wait_for_condition_or_raise,
)
from tests.graph_track_b.theme_support import (
    STITCH_DARK_V1,
    STITCH_LIGHT_V1,
    _alpha_color_name,
    _color_name,
)


class GraphCanvasQmlPreferenceRenderingTests(GraphCanvasQmlPreferenceTestBase):
    def test_graph_canvas_properties_follow_runtime_preference_updates(self) -> None:
        edge_layer = self.canvas.findChild(QObject, "graphCanvasEdgeLayer")
        self.assertIsNotNone(edge_layer)
        self.assertTrue(bool(self.canvas.property("showGrid")))
        self.assertEqual(str(self.canvas.property("gridStyle")), "lines")
        self.assertEqual(str(self.canvas.property("edgeCrossingStyle")), "none")
        self.assertTrue(bool(self.canvas.property("minimapVisible")))
        self.assertTrue(bool(self.canvas.property("minimapExpanded")))
        self.assertTrue(bool(self.canvas.property("showPortLabels")))
        self.assertEqual(str(edge_layer.property("edgeCrossingStyle")), "none")

        self.bridge.set_graphics_show_grid_value(False)
        self.bridge.set_graphics_show_minimap_value(False)
        self.bridge.set_graphics_minimap_expanded_value(False)
        self.bridge.set_graphics_show_port_labels_value(False)
        self.bridge.set_graphics_edge_crossing_style_value("gap_break")
        self.app.processEvents()

        self.assertFalse(bool(self.canvas.property("showGrid")))
        self.assertFalse(bool(self.canvas.property("minimapVisible")))
        self.assertFalse(bool(self.canvas.property("minimapExpanded")))
        self.assertFalse(bool(self.canvas.property("showPortLabels")))
        self.assertEqual(str(self.canvas.property("edgeCrossingStyle")), "gap_break")
        self.assertEqual(str(edge_layer.property("edgeCrossingStyle")), "gap_break")

    def test_graph_canvas_root_packetization_helpers_remain_registered(self) -> None:
        graph_canvas_text = _GRAPH_CANVAS_QML_PATH.read_text(encoding="utf-8")
        graph_canvas_lines = graph_canvas_text.splitlines()
        root_bindings_text = (_GRAPH_CANVAS_QML_PATH.parent / "graph_canvas" / "GraphCanvasRootBindings.qml").read_text(
            encoding="utf-8"
        )
        root_layers_text = (_GRAPH_CANVAS_QML_PATH.parent / "graph_canvas" / "GraphCanvasRootLayers.qml").read_text(
            encoding="utf-8"
        )
        root_api_text = (_GRAPH_CANVAS_QML_PATH.parent / "graph_canvas" / "GraphCanvasRootApi.js").read_text(
            encoding="utf-8"
        )

        self.assertLessEqual(len(graph_canvas_lines), 700)
        self.assertIn('import "graph_canvas/GraphCanvasRootApi.js" as GraphCanvasRootApi', graph_canvas_text)
        self.assertIn("GraphCanvasComponents.GraphCanvasRootBindings {", graph_canvas_text)
        self.assertIn("GraphCanvasComponents.GraphCanvasRootLayers {", graph_canvas_text)
        self.assertIn("property alias backgroundLayerItem: backgroundLayer", root_layers_text)
        self.assertIn("property alias edgeLayerItem: edgeLayer", root_layers_text)
        self.assertIn("readonly property var canvasStateBridgeRef: root.canvasStateBridge || null", root_bindings_text)
        self.assertIn("function snapToGridValue(canvasStateBridge, value) {", root_api_text)

    def test_graph_canvas_background_switches_between_line_and_point_grid_modes(self) -> None:
        background = self.canvas.findChild(QObject, "graphCanvasBackground")
        self.assertIsNotNone(background)
        self.assertEqual(str(background.property("gridStyle")), "lines")
        self.assertEqual(str(background.property("effectiveGridStyle")), "lines")

        self.bridge.set_graphics_grid_style_value("points")
        self.app.processEvents()

        self.assertEqual(str(self.canvas.property("gridStyle")), "points")
        self.assertEqual(str(background.property("gridStyle")), "points")
        self.assertEqual(str(background.property("effectiveGridStyle")), "points")

    def test_graph_canvas_passes_port_label_preference_into_graph_node_hosts(self) -> None:
        from PyQt6.QtCore import pyqtProperty, pyqtSignal

        node_payload = {
            "node_id": "node_port_label_preference_test",
            "type_id": "core.logger",
            "title": "Logger",
            "x": 120.0,
            "y": 140.0,
            "width": 210.0,
            "height": 88.0,
            "accent": "#2F89FF",
            "collapsed": False,
            "selected": False,
            "can_enter_scope": False,
            "surface_family": "standard",
            "surface_variant": "",
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
            "inline_properties": [],
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
        }

        class CanvasStateBridgeStub(QObject):
            graphics_preferences_changed = pyqtSignal()
            scene_nodes_changed = pyqtSignal()

            def __init__(self, preference_bridge: _GraphCanvasPreferenceBridge) -> None:
                super().__init__()
                self._preference_bridge = preference_bridge
                self._nodes_model = [dict(node_payload)]
                self._preference_bridge.graphics_preferences_changed.connect(self.graphics_preferences_changed.emit)

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
            def graphics_show_port_labels(self) -> bool:
                return bool(self._preference_bridge.graphics_show_port_labels)

            @pyqtProperty(bool, notify=graphics_preferences_changed)
            def graphics_node_shadow(self) -> bool:
                return True

            @pyqtProperty(int, notify=graphics_preferences_changed)
            def graphics_shadow_strength(self) -> int:
                return 70

            @pyqtProperty(int, notify=graphics_preferences_changed)
            def graphics_shadow_softness(self) -> int:
                return 50

            @pyqtProperty(int, notify=graphics_preferences_changed)
            def graphics_shadow_offset(self) -> int:
                return 4

            @pyqtProperty(str, notify=graphics_preferences_changed)
            def graphics_performance_mode(self) -> str:
                return "full_fidelity"

            @pyqtProperty("QVariantList", notify=scene_nodes_changed)
            def nodes_model(self) -> list[dict[str, object]]:
                return list(self._nodes_model)

        self.canvas.deleteLater()
        self.app.processEvents()

        canvas_state_bridge = CanvasStateBridgeStub(self.bridge)
        canvas_command_bridge = GraphCanvasCommandBridge(
            shell_window=self.bridge,  # type: ignore[arg-type]
            view_bridge=self.view,
        )
        self.canvas = self._create_canvas(
            {
                "canvasStateBridge": canvas_state_bridge,
                "canvasCommandBridge": canvas_command_bridge,
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

        self.assertTrue(bool(self.canvas.property("showPortLabels")))
        self.assertTrue(bool(node_card.property("showPortLabelsPreference")))
        self.assertFalse(bool(node_card.property("_tooltipOnlyPortLabelsActive")))

        self.bridge.set_graphics_show_port_labels_value(False)
        wait_for_condition_or_raise(
            lambda: (
                not bool(self.canvas.property("showPortLabels"))
                and not bool(node_card.property("showPortLabelsPreference"))
            ),
            timeout_ms=200,
            app=self.app,
            timeout_message="Timed out waiting for graph canvas port-label preference propagation.",
        )

        self.assertTrue(bool(node_card.property("_tooltipOnlyPortLabelsActive")))

    def test_node_execution_visualization_graph_canvas_host_chrome_follows_bridge_state_priority(self) -> None:
        node_id = "node_execution_visualization"
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
            "can_enter_scope": False,
            "surface_family": "standard",
            "surface_variant": "",
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
            "inline_properties": [],
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
        }

        class CanvasStateBridgeStub(QObject):
            graphics_preferences_changed = pyqtSignal()
            scene_nodes_changed = pyqtSignal()
            failure_highlight_changed = pyqtSignal()
            node_execution_state_changed = pyqtSignal()

            def __init__(
                self,
                preference_bridge: _GraphCanvasPreferenceBridge,
                view_bridge: ViewportBridge,
            ) -> None:
                super().__init__()
                self._preference_bridge = preference_bridge
                self._view_bridge = view_bridge
                self._nodes_model = [dict(node_payload)]
                self._running_node_lookup: dict[str, bool] = {}
                self._completed_node_lookup: dict[str, bool] = {}
                self._failed_node_lookup: dict[str, bool] = {}
                self._failed_node_revision = 0
                self._node_execution_revision = 0
                self._preference_bridge.graphics_preferences_changed.connect(self.graphics_preferences_changed.emit)

            @pyqtProperty(QObject, constant=True)
            def viewport_bridge(self) -> ViewportBridge:
                return self._view_bridge

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
            def graphics_show_port_labels(self) -> bool:
                return bool(self._preference_bridge.graphics_show_port_labels)

            @pyqtProperty(bool, notify=graphics_preferences_changed)
            def graphics_node_shadow(self) -> bool:
                return True

            @pyqtProperty(int, notify=graphics_preferences_changed)
            def graphics_shadow_strength(self) -> int:
                return 70

            @pyqtProperty(int, notify=graphics_preferences_changed)
            def graphics_shadow_softness(self) -> int:
                return 50

            @pyqtProperty(int, notify=graphics_preferences_changed)
            def graphics_shadow_offset(self) -> int:
                return 4

            @pyqtProperty(str, notify=graphics_preferences_changed)
            def graphics_performance_mode(self) -> str:
                return "full_fidelity"

            @pyqtProperty("QVariantList", notify=scene_nodes_changed)
            def nodes_model(self) -> list[dict[str, object]]:
                return list(self._nodes_model)

            @pyqtProperty("QVariantList", constant=True)
            def backdrop_nodes_model(self) -> list[dict[str, object]]:
                return []

            @pyqtProperty("QVariantList", constant=True)
            def edges_model(self) -> list[dict[str, object]]:
                return []

            @pyqtProperty("QVariantMap", constant=True)
            def selected_node_lookup(self) -> dict[str, bool]:
                return {}

            @pyqtProperty("QVariantMap", constant=True)
            def workspace_scene_bounds_payload(self) -> dict[str, float]:
                return {}

            @pyqtProperty("QVariantMap", notify=failure_highlight_changed)
            def failed_node_lookup(self) -> dict[str, bool]:
                return dict(self._failed_node_lookup)

            @pyqtProperty(int, notify=failure_highlight_changed)
            def failed_node_revision(self) -> int:
                return int(self._failed_node_revision)

            @pyqtProperty(str, notify=failure_highlight_changed)
            def failed_node_title(self) -> str:
                return "Logger" if self._failed_node_lookup else ""

            @pyqtProperty("QVariantMap", notify=node_execution_state_changed)
            def running_node_lookup(self) -> dict[str, bool]:
                return dict(self._running_node_lookup)

            @pyqtProperty("QVariantMap", notify=node_execution_state_changed)
            def completed_node_lookup(self) -> dict[str, bool]:
                return dict(self._completed_node_lookup)

            @pyqtProperty(int, notify=node_execution_state_changed)
            def node_execution_revision(self) -> int:
                return int(self._node_execution_revision)

            def set_running_node_state(self, tracked_node_id: str) -> None:
                self._running_node_lookup = {str(tracked_node_id): True}
                self._completed_node_lookup = {}
                self._node_execution_revision += 1
                self.node_execution_state_changed.emit()

            def set_completed_node_state(self, tracked_node_id: str) -> None:
                self._running_node_lookup = {}
                self._completed_node_lookup = {str(tracked_node_id): True}
                self._node_execution_revision += 1
                self.node_execution_state_changed.emit()

            def set_failed_node_state(self, tracked_node_id: str) -> None:
                self._failed_node_lookup = {str(tracked_node_id): True}
                self._failed_node_revision += 1
                self.failure_highlight_changed.emit()

        self.canvas.deleteLater()
        self.app.processEvents()

        canvas_state_bridge = CanvasStateBridgeStub(self.bridge, self.view)
        canvas_command_bridge = GraphCanvasCommandBridge(
            shell_window=self.bridge,  # type: ignore[arg-type]
            view_bridge=self.view,
        )
        self.canvas = self._create_canvas(
            {
                "canvasStateBridge": canvas_state_bridge,
                "canvasCommandBridge": canvas_command_bridge,
                "width": 1280.0,
                "height": 720.0,
            }
        )

        wait_for_condition_or_raise(
            lambda: len(_named_child_items(self.canvas, "graphNodeCard")) == 1,
            timeout_ms=200,
            app=self.app,
            timeout_message="Timed out waiting for graph canvas execution-visualization node host to appear.",
        )
        node_card = _named_child_items(self.canvas, "graphNodeCard")[0]
        background_layer = node_card.findChild(QObject, "graphNodeChromeBackgroundLayer")
        running_halo = node_card.findChild(QObject, "graphNodeRunningHalo")
        running_pulse_halo = node_card.findChild(QObject, "graphNodeRunningPulseHalo")
        completed_flash_halo = node_card.findChild(QObject, "graphNodeCompletedFlashHalo")
        elapsed_timer = node_card.findChild(QObject, "graphNodeElapsedTimer")
        self.assertIsNotNone(background_layer)
        self.assertIsNotNone(running_halo)
        self.assertIsNotNone(running_pulse_halo)
        self.assertIsNotNone(completed_flash_halo)
        self.assertIsNotNone(elapsed_timer)

        self.assertEqual(str(background_layer.property("effectiveBorderState")), "idle")
        self.assertEqual(dict(self.canvas.property("runningNodeLookup")), {})
        self.assertEqual(dict(self.canvas.property("completedNodeLookup")), {})
        self.assertFalse(bool(elapsed_timer.property("visible")))

        idle_key = str(background_layer.property("cacheKey") or "")

        canvas_state_bridge.set_running_node_state(node_id)
        wait_for_condition_or_raise(
            lambda: bool(node_card.property("isRunningNode"))
            and str(background_layer.property("effectiveBorderState")) == "running"
            and bool(elapsed_timer.property("visible")),
            timeout_ms=200,
            app=self.app,
            timeout_message="Timed out waiting for running execution chrome on graph canvas host.",
        )

        self.assertTrue(bool(node_card.property("renderActive")))
        self.assertEqual(int(node_card.property("z")), 31)
        self.assertEqual(dict(self.canvas.property("runningNodeLookup")), {node_id: True})
        self.assertEqual(
            _color_name(background_layer.property("effectiveOutlineColor")),
            _color_name(node_card.property("runningOutlineColor")),
        )
        self.assertTrue(bool(running_halo.property("visible")))
        self.assertTrue(bool(running_pulse_halo.property("visible")))

        running_key = str(background_layer.property("cacheKey") or "")
        self.assertNotEqual(running_key, idle_key)
        self.assertIn("|running|", running_key)

        wait_for_condition_or_raise(
            lambda: str(elapsed_timer.property("text") or "") != "0.0s",
            timeout_ms=500,
            app=self.app,
            timeout_message="Timed out waiting for graph canvas elapsed timer to advance.",
        )

        canvas_state_bridge.set_completed_node_state(node_id)
        wait_for_condition_or_raise(
            lambda: bool(node_card.property("isCompletedNode"))
            and not bool(node_card.property("isRunningNode"))
            and str(background_layer.property("effectiveBorderState")) == "completed"
            and not bool(elapsed_timer.property("visible")),
            timeout_ms=200,
            app=self.app,
            timeout_message="Timed out waiting for completed execution chrome on graph canvas host.",
        )

        self.assertEqual(int(node_card.property("z")), 29)
        self.assertEqual(dict(self.canvas.property("runningNodeLookup")), {})
        self.assertEqual(dict(self.canvas.property("completedNodeLookup")), {node_id: True})
        self.assertEqual(
            _color_name(background_layer.property("effectiveOutlineColor")),
            _color_name(node_card.property("completedOutlineColor")),
        )
        self.assertFalse(bool(running_halo.property("visible")))
        self.assertFalse(bool(running_pulse_halo.property("visible")))

        QTest.qWait(80)
        self.app.processEvents()
        self.assertGreater(float(background_layer.property("completedFlashProgress")), 0.0)

        completed_key = str(background_layer.property("cacheKey") or "")
        self.assertNotEqual(completed_key, running_key)
        self.assertIn("|completed|", completed_key)

        canvas_state_bridge.set_failed_node_state(node_id)
        wait_for_condition_or_raise(
            lambda: str(background_layer.property("effectiveBorderState")) == "failed",
            timeout_ms=200,
            app=self.app,
            timeout_message="Timed out waiting for failure priority to override execution chrome.",
        )

        self.assertEqual(dict(self.canvas.property("failedNodeLookup")), {node_id: True})
        self.assertEqual(
            _color_name(background_layer.property("effectiveOutlineColor")),
            _color_name(node_card.property("failureOutlineColor")),
        )
        self.assertFalse(bool(running_halo.property("visible")))
        self.assertFalse(bool(running_pulse_halo.property("visible")))
        self.assertFalse(bool(completed_flash_halo.property("visible")))
        self.assertIn("|failed|", str(background_layer.property("cacheKey") or ""))

    def test_execution_edge_progress_visualization_edge_canvas_diagnostics_follow_renderer_contract(self) -> None:
        edge_layer = self._create_edge_layer()
        edge_canvas_layer = edge_layer.findChild(QObject, "graphCanvasEdgeCanvasLayer")
        self.assertIsNotNone(edge_canvas_layer)
        if edge_canvas_layer is None:
            self.fail("Expected EdgeCanvasLayer to expose a stable object name")
        window = QQuickWindow()
        window.resize(1280, 720)
        edge_layer.setParentItem(window.contentItem())
        window.show()
        self.app.processEvents()

        def bezier_edge(
            edge_id: str,
            *,
            source_port_kind: str,
            target_port_kind: str = "exec",
            color: str = "#7AA8FF",
        ) -> dict[str, object]:
            return {
                "edge_id": edge_id,
                "source_node_id": "source",
                "source_port_key": "out",
                "target_node_id": "target",
                "target_port_key": "in",
                "source_port_kind": source_port_kind,
                "target_port_kind": target_port_kind,
                "edge_family": "standard",
                "label": "",
                "visual_style": {},
                "flow_style": {},
                "source_port_side": "right",
                "target_port_side": "left",
                "source_anchor_side": "right",
                "target_anchor_side": "left",
                "source_anchor_kind": "node",
                "target_anchor_kind": "node",
                "source_anchor_node_id": "",
                "target_anchor_node_id": "",
                "source_hidden_by_backdrop_id": "",
                "target_hidden_by_backdrop_id": "",
                "source_anchor_bounds": {"x": 80.0, "y": 80.0, "width": 40.0, "height": 40.0},
                "target_anchor_bounds": {"x": 320.0, "y": 80.0, "width": 40.0, "height": 40.0},
                "lane_bias": 0.0,
                "sx": 80.0,
                "sy": 80.0,
                "tx": 320.0,
                "ty": 80.0,
                "c1x": 160.0,
                "c1y": 80.0,
                "c2x": 240.0,
                "c2y": 80.0,
                "route": "bezier",
                "pipe_points": [],
                "color": color,
                "data_type_warning": False,
            }

        flow_edge = {
            "edge_id": "flow_edge",
            "source_node_id": "flow_source",
            "source_port_key": "flow_out",
            "target_node_id": "flow_target",
            "target_port_key": "flow_in",
            "source_port_kind": "flow",
            "target_port_kind": "flow",
            "edge_family": "flow",
            "label": "",
            "visual_style": {},
            "flow_style": {},
            "source_port_side": "bottom",
            "target_port_side": "top",
            "source_anchor_side": "bottom",
            "target_anchor_side": "top",
            "source_anchor_kind": "node",
            "target_anchor_kind": "node",
            "source_anchor_node_id": "",
            "target_anchor_node_id": "",
            "source_hidden_by_backdrop_id": "",
            "target_hidden_by_backdrop_id": "",
            "source_anchor_bounds": {"x": 80.0, "y": 200.0, "width": 40.0, "height": 40.0},
            "target_anchor_bounds": {"x": 320.0, "y": 200.0, "width": 40.0, "height": 40.0},
            "lane_bias": 0.0,
            "sx": 100.0,
            "sy": 220.0,
            "tx": 340.0,
            "ty": 220.0,
            "c1x": 160.0,
            "c1y": 220.0,
            "c2x": 280.0,
            "c2y": 220.0,
            "route": "bezier",
            "pipe_points": [],
            "color": "#A0A8B8",
            "data_type_warning": False,
        }

        edge_layer.setProperty(
            "edges",
            [
                bezier_edge("exec_dimmed", source_port_kind="exec"),
                bezier_edge("exec_selected", source_port_kind="completed", color="#6CE7FF"),
                bezier_edge("exec_previewed", source_port_kind="failed", color="#FFB36B"),
                bezier_edge("data_edge", source_port_kind="data", target_port_kind="data", color="#55AA66"),
                flow_edge,
            ],
        )
        edge_layer.setProperty("selectedEdgeIds", ["exec_selected"])
        edge_layer.setProperty("previewEdgeId", "exec_previewed")
        edge_layer.requestRedraw()
        self.app.processEvents()

        def _paint(edge_id: str) -> dict[str, object] | None:
            diagnostics = edge_canvas_layer.property("_paintDiagnosticsByEdgeId")
            if hasattr(diagnostics, "toVariant"):
                diagnostics = diagnostics.toVariant()
            diagnostics = diagnostics or {}
            if not isinstance(diagnostics, dict):
                diagnostics = dict(diagnostics)
            payload = diagnostics.get(edge_id)
            if hasattr(payload, "toVariant"):
                payload = payload.toVariant()
            if payload is None:
                return None
            return payload if isinstance(payload, dict) else dict(payload)

        wait_for_condition_or_raise(
            lambda: all(_paint(edge_id) is not None for edge_id in ("exec_dimmed", "exec_selected", "exec_previewed", "data_edge", "flow_edge")),
            timeout_ms=400,
            app=self.app,
            timeout_message="Timed out waiting for execution-edge renderer diagnostics.",
        )

        idle_exec = _paint("exec_dimmed")
        self.assertIsNotNone(idle_exec)
        if idle_exec is None:
            self.fail("Expected idle execution-edge diagnostics")
        self.assertFalse(bool(idle_exec["executionVisualizationActive"]))
        self.assertEqual(float(idle_exec["strokeAlpha"]), 1.0)
        self.assertAlmostEqual(float(idle_exec["strokeWidthScreenPx"]), 2.0, places=6)
        self.assertEqual(float(idle_exec["flashAlpha"]), 0.0)

        edge_layer.setProperty("nodeExecutionRevision", 1)
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: bool((_paint("exec_dimmed") or {}).get("executionVisualizationActive")),
            timeout_ms=400,
            app=self.app,
            timeout_message="Timed out waiting for active execution-edge renderer state.",
        )

        dimmed = _paint("exec_dimmed")
        selected = _paint("exec_selected")
        previewed = _paint("exec_previewed")
        data_edge = _paint("data_edge")
        flow_edge_paint = _paint("flow_edge")
        self.assertIsNotNone(dimmed)
        self.assertIsNotNone(selected)
        self.assertIsNotNone(previewed)
        self.assertIsNotNone(data_edge)
        self.assertIsNotNone(flow_edge_paint)
        if None in (dimmed, selected, previewed, data_edge, flow_edge_paint):
            self.fail("Expected execution-edge renderer diagnostics after activation")

        self.assertTrue(bool(dimmed["executionDimmedActive"]))
        self.assertEqual(float(dimmed["strokeAlpha"]), 0.35)
        self.assertAlmostEqual(float(dimmed["strokeWidthScreenPx"]), 1.7, places=6)
        self.assertEqual(float(dimmed["flashAlpha"]), 0.0)

        self.assertFalse(bool(selected["executionDimmedActive"]))
        self.assertEqual(float(selected["strokeAlpha"]), 1.0)
        self.assertAlmostEqual(float(selected["strokeWidthScreenPx"]), 3.0, places=6)
        self.assertEqual(
            _color_name(selected["strokeColor"]),
            _color_name(edge_layer.property("selectedStrokeColor")),
        )

        self.assertFalse(bool(previewed["executionDimmedActive"]))
        self.assertEqual(float(previewed["strokeAlpha"]), 1.0)
        self.assertAlmostEqual(float(previewed["strokeWidthScreenPx"]), 2.8, places=6)
        self.assertEqual(
            _color_name(previewed["strokeColor"]),
            _color_name(edge_layer.property("previewStrokeColor")),
        )

        self.assertFalse(bool(data_edge["executionDimmedActive"]))
        self.assertFalse(bool(data_edge["flowEdge"]))
        self.assertEqual(float(data_edge["strokeAlpha"]), 1.0)
        self.assertAlmostEqual(float(data_edge["strokeWidthScreenPx"]), 2.0, places=6)

        self.assertTrue(bool(flow_edge_paint["flowEdge"]))
        self.assertEqual(float(flow_edge_paint["strokeAlpha"]), 1.0)
        self.assertAlmostEqual(float(flow_edge_paint["strokeWidthScreenPx"]), 2.0, places=6)
        self.assertEqual(
            _color_name(flow_edge_paint["strokeColor"]),
            _color_name(edge_layer.property("flowDefaultStrokeColor")),
        )

        edge_layer.setProperty("nodeExecutionRevision", 2)
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: not bool((_paint("exec_dimmed") or {}).get("executionVisualizationActive")),
            timeout_ms=400,
            app=self.app,
            timeout_message="Timed out waiting for no-progress execution-edge cleanup diagnostics.",
        )

        cleaned_without_progress = _paint("exec_dimmed")
        self.assertIsNotNone(cleaned_without_progress)
        if cleaned_without_progress is None:
            self.fail("Expected no-progress execution-edge cleanup diagnostics")
        self.assertFalse(bool(cleaned_without_progress["executionVisualizationActive"]))
        self.assertFalse(bool(cleaned_without_progress["executionDimmedActive"]))
        self.assertEqual(float(cleaned_without_progress["strokeAlpha"]), 1.0)
        self.assertAlmostEqual(float(cleaned_without_progress["strokeWidthScreenPx"]), 2.0, places=6)
        self.assertEqual(float(cleaned_without_progress["flashAlpha"]), 0.0)

        edge_layer.setProperty("nodeExecutionRevision", 3)
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: bool((_paint("exec_dimmed") or {}).get("executionVisualizationActive")),
            timeout_ms=400,
            app=self.app,
            timeout_message="Timed out waiting for execution-edge lifecycle reactivation.",
        )

        edge_layer.setProperty("progressedExecutionEdgeLookup", {"exec_dimmed": True})
        edge_layer.setProperty("nodeExecutionRevision", 4)
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: float(((_paint("exec_dimmed") or {}).get("flashAlpha", 0.0))) > 0.0,
            timeout_ms=400,
            app=self.app,
            timeout_message="Timed out waiting for execution-edge flash diagnostics.",
        )

        progressed = _paint("exec_dimmed")
        self.assertIsNotNone(progressed)
        if progressed is None:
            self.fail("Expected progressed execution-edge diagnostics")
        self.assertFalse(bool(progressed["executionDimmedActive"]))
        self.assertTrue(bool(progressed["executionProgressed"]))
        self.assertEqual(float(progressed["strokeAlpha"]), 1.0)
        self.assertAlmostEqual(float(progressed["strokeWidthScreenPx"]), 2.0, places=6)
        self.assertLessEqual(float(progressed["flashAlpha"]), 0.55)
        self.assertGreater(float(progressed["flashAlpha"]), 0.0)
        self.assertAlmostEqual(float(progressed["flashWidthScreenPx"]), 3.4, places=6)
        self.assertEqual(_color_name(progressed["flashColor"]), _color_name(progressed["baseColor"]))

        wait_for_condition_or_raise(
            lambda: float(((_paint("exec_dimmed") or {}).get("flashAlpha", -1.0))) == 0.0,
            timeout_ms=800,
            app=self.app,
            timeout_message="Timed out waiting for execution-edge flash cleanup.",
        )

        edge_layer.setProperty("progressedExecutionEdgeLookup", {})
        edge_layer.setProperty("nodeExecutionRevision", 5)
        self.app.processEvents()

        wait_for_condition_or_raise(
            lambda: not bool((_paint("exec_dimmed") or {}).get("executionVisualizationActive")),
            timeout_ms=400,
            app=self.app,
            timeout_message="Timed out waiting for execution-edge renderer cleanup.",
        )

        cleaned = _paint("exec_dimmed")
        self.assertIsNotNone(cleaned)
        if cleaned is None:
            self.fail("Expected cleaned execution-edge diagnostics")
        self.assertFalse(bool(cleaned["executionDimmedActive"]))
        self.assertEqual(float(cleaned["strokeAlpha"]), 1.0)
        self.assertAlmostEqual(float(cleaned["strokeWidthScreenPx"]), 2.0, places=6)
        self.assertEqual(float(cleaned["flashAlpha"]), 0.0)

        edge_layer.setParentItem(None)
        window.close()
        window.deleteLater()
        edge_layer.deleteLater()
        self.app.processEvents()

    def test_toggle_minimap_expanded_routes_through_bridge_slot(self) -> None:
        self.assertEqual(self.bridge.minimap_update_history, [])
        self.assertTrue(bool(self.canvas.property("minimapExpanded")))

        QMetaObject.invokeMethod(
            self.canvas,
            "toggleMinimapExpanded",
            Qt.ConnectionType.DirectConnection,
        )
        self.app.processEvents()

        self.assertEqual(self.bridge.minimap_update_history, [False])
        self.assertFalse(self.bridge.graphics_minimap_expanded)
        self.assertFalse(bool(self.canvas.property("minimapExpanded")))

    def test_canvas_qml_theme_surfaces_follow_runtime_theme_changes(self) -> None:
        background = self.canvas.findChild(QObject, "graphCanvasBackground")
        minimap_overlay = self.canvas.findChild(QObject, "graphCanvasMinimapOverlay")
        minimap_toggle = self.canvas.findChild(QObject, "graphCanvasMinimapToggle")
        minimap_viewport_rect = self.canvas.findChild(QObject, "graphCanvasMinimapViewportRect")
        drop_preview = self.canvas.findChild(QObject, "graphCanvasDropPreview")
        edge_layer = self.canvas.findChild(QObject, "graphCanvasEdgeLayer")
        marquee_rect = self.canvas.findChild(QObject, "graphCanvasMarqueeRect")

        self.assertIsNotNone(background)
        self.assertIsNotNone(minimap_overlay)
        self.assertIsNotNone(minimap_toggle)
        self.assertIsNotNone(minimap_viewport_rect)
        self.assertIsNotNone(drop_preview)
        self.assertIsNotNone(edge_layer)
        self.assertIsNotNone(marquee_rect)

        self.assertEqual(_color_name(background.property("backgroundFillColor")), STITCH_DARK_V1.canvas_bg)
        self.assertEqual(_color_name(background.property("minorGridColor")), STITCH_DARK_V1.canvas_minor_grid)
        self.assertEqual(
            _color_name(minimap_overlay.property("color"), include_alpha=True),
            _alpha_color_name(STITCH_DARK_V1.panel_bg, 0.64),
        )
        self.assertEqual(_color_name(minimap_toggle.property("color")), STITCH_DARK_V1.toolbar_bg)
        self.assertEqual(
            _color_name(minimap_viewport_rect.property("color"), include_alpha=True),
            _alpha_color_name(STITCH_DARK_V1.accent, 0.18),
        )
        self.assertEqual(
            _color_name(drop_preview.property("color"), include_alpha=True),
            _alpha_color_name(STITCH_DARK_V1.panel_bg, 0.66),
        )
        self.assertEqual(
            _color_name(edge_layer.property("selectedStrokeColor")),
            self.graph_theme_bridge.edge_palette["selected_stroke"],
        )
        self.assertEqual(
            _color_name(edge_layer.property("invalidDragStrokeColor")),
            self.graph_theme_bridge.edge_palette["invalid_drag_stroke"],
        )
        self.assertEqual(_color_name(edge_layer.property("flowDefaultStrokeColor")), STITCH_DARK_V1.muted_fg)
        self.assertEqual(_color_name(edge_layer.property("flowDefaultLabelTextColor")), STITCH_DARK_V1.panel_title_fg)
        self.assertEqual(
            _color_name(edge_layer.property("flowDefaultLabelBackgroundColor")),
            STITCH_DARK_V1.panel_bg,
        )
        self.assertEqual(
            _color_name(marquee_rect.property("color"), include_alpha=True),
            _alpha_color_name(STITCH_DARK_V1.accent, 0.2),
        )

        self.theme_bridge.apply_theme("stitch_light")
        self.graph_theme_bridge.apply_theme("graph_stitch_light")
        self.app.processEvents()

        self.assertEqual(_color_name(background.property("backgroundFillColor")), STITCH_LIGHT_V1.canvas_bg)
        self.assertEqual(_color_name(background.property("minorGridColor")), STITCH_LIGHT_V1.canvas_minor_grid)
        self.assertEqual(
            _color_name(minimap_overlay.property("color"), include_alpha=True),
            _alpha_color_name(STITCH_LIGHT_V1.panel_bg, 0.64),
        )
        self.assertEqual(_color_name(minimap_toggle.property("color")), STITCH_LIGHT_V1.toolbar_bg)
        self.assertEqual(
            _color_name(minimap_viewport_rect.property("color"), include_alpha=True),
            _alpha_color_name(STITCH_LIGHT_V1.accent, 0.18),
        )
        self.assertEqual(
            _color_name(drop_preview.property("color"), include_alpha=True),
            _alpha_color_name(STITCH_LIGHT_V1.panel_bg, 0.66),
        )
        self.assertEqual(
            _color_name(edge_layer.property("selectedStrokeColor")),
            self.graph_theme_bridge.edge_palette["selected_stroke"],
        )
        self.assertEqual(
            _color_name(edge_layer.property("invalidDragStrokeColor")),
            self.graph_theme_bridge.edge_palette["invalid_drag_stroke"],
        )
        self.assertEqual(_color_name(edge_layer.property("flowDefaultStrokeColor")), STITCH_LIGHT_V1.muted_fg)
        self.assertEqual(_color_name(edge_layer.property("flowDefaultLabelTextColor")), STITCH_LIGHT_V1.panel_title_fg)
        self.assertEqual(
            _color_name(edge_layer.property("flowDefaultLabelBackgroundColor")),
            STITCH_LIGHT_V1.panel_bg,
        )
        self.assertEqual(
            _color_name(marquee_rect.property("color"), include_alpha=True),
            _alpha_color_name(STITCH_LIGHT_V1.accent, 0.2),
        )

    def test_graph_canvas_world_stacks_above_edge_layer(self) -> None:
        edge_layer = self.canvas.findChild(QObject, "graphCanvasEdgeLayer")
        world = self.canvas.findChild(QObject, "graphCanvasWorld")

        self.assertIsNotNone(edge_layer)
        self.assertIsNotNone(world)
        parent_item = world.parentItem()
        self.assertIsNotNone(parent_item)
        self.assertIs(parent_item, edge_layer.parentItem())
        sibling_items = list(parent_item.childItems())
        self.assertIn(edge_layer, sibling_items)
        self.assertIn(world, sibling_items)
        self.assertLess(sibling_items.index(edge_layer), sibling_items.index(world))

    def test_graph_canvas_live_resize_geometry_propagates_to_edge_layer(self) -> None:
        edge_layer = self.canvas.findChild(QObject, "graphCanvasEdgeLayer")
        self.assertIsNotNone(edge_layer)

        payload = {"node_resize_test": {"x": 180.0, "y": 120.0, "width": 260.0, "height": 144.0}}
        self.canvas.setProperty("liveNodeGeometry", payload)
        self.app.processEvents()

        self.assertEqual(self.canvas.property("liveNodeGeometry"), payload)
        self.assertEqual(edge_layer.property("liveNodeGeometry"), payload)

    def test_edge_layer_applies_live_drag_offsets_to_recomputed_node_port_geometry(self) -> None:
        edge_layer = self._create_edge_layer()

        surface_metrics = {
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
        }
        nodes = [
            {
                "node_id": "source",
                "type_id": "core.logger",
                "title": "Source",
                "x": 100.0,
                "y": 100.0,
                "width": 210.0,
                "height": 88.0,
                "surface_family": "standard",
                "surface_variant": "",
                "collapsed": False,
                "ports": [
                    {
                        "key": "out",
                        "label": "Out",
                        "direction": "out",
                        "kind": "data",
                        "data_type": "str",
                        "connected": False,
                        "side": "right",
                    }
                ],
                "surface_metrics": surface_metrics,
            },
            {
                "node_id": "target",
                "type_id": "core.logger",
                "title": "Target",
                "x": 400.0,
                "y": 100.0,
                "width": 210.0,
                "height": 88.0,
                "surface_family": "standard",
                "surface_variant": "",
                "collapsed": False,
                "ports": [
                    {
                        "key": "in",
                        "label": "In",
                        "direction": "in",
                        "kind": "data",
                        "data_type": "str",
                        "connected": False,
                        "side": "left",
                    }
                ],
                "surface_metrics": surface_metrics,
            },
        ]
        edge_payload = {
            "edge_id": "edge_drag_offset_test",
            "source_node_id": "source",
            "source_port_key": "out",
            "target_node_id": "target",
            "target_port_key": "in",
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
            "source_anchor_kind": "node",
            "target_anchor_kind": "node",
            "source_anchor_node_id": "source",
            "target_anchor_node_id": "target",
            "source_hidden_by_backdrop_id": "",
            "target_hidden_by_backdrop_id": "",
            "source_anchor_bounds": {"x": 100.0, "y": 100.0, "width": 210.0, "height": 88.0},
            "target_anchor_bounds": {"x": 400.0, "y": 100.0, "width": 210.0, "height": 88.0},
            "lane_bias": 0.0,
            "sx": 310.0,
            "sy": 144.0,
            "tx": 400.0,
            "ty": 144.0,
            "c1x": 366.0,
            "c1y": 144.0,
            "c2x": 344.0,
            "c2y": 144.0,
            "route": "bezier",
            "pipe_points": [],
            "color": "#7AA8FF",
            "data_type_warning": False,
        }

        edge_layer.setProperty("nodes", nodes)
        edge_layer.setProperty("edges", [edge_payload])
        self.app.processEvents()
        edge_layer.requestRedraw()
        self.app.processEvents()

        baseline_snapshot = edge_layer._visibleEdgeSnapshot("edge_drag_offset_test").toVariant()
        baseline_geometry = dict(baseline_snapshot["geometry"])
        baseline_redraws = int(edge_layer.property("_redrawRequestCount"))

        edge_layer.setProperty("dragOffsets", {"source": {"dx": 40.0, "dy": 20.0}})
        wait_for_condition_or_raise(
            lambda: int(edge_layer.property("_redrawRequestCount")) > baseline_redraws,
            timeout_ms=200,
            app=self.app,
            timeout_message="Timed out waiting for edge-layer drag offset redraw.",
        )

        offset_snapshot = edge_layer._visibleEdgeSnapshot("edge_drag_offset_test").toVariant()
        offset_geometry = dict(offset_snapshot["geometry"])
        self.assertAlmostEqual(offset_geometry["sx"], baseline_geometry["sx"] + 40.0, places=6)
        self.assertAlmostEqual(offset_geometry["sy"], baseline_geometry["sy"] + 20.0, places=6)
        self.assertAlmostEqual(offset_geometry["c1x"], baseline_geometry["c1x"] + 40.0, places=6)
        self.assertAlmostEqual(offset_geometry["c1y"], baseline_geometry["c1y"] + 20.0, places=6)
        self.assertAlmostEqual(offset_geometry["tx"], baseline_geometry["tx"], places=6)
        self.assertAlmostEqual(offset_geometry["ty"], baseline_geometry["ty"], places=6)

        edge_layer.deleteLater()
        self.app.processEvents()

    def test_edge_layer_gap_break_marks_only_under_edge_for_pipe_pipe_crossings(self) -> None:
        edge_layer = self._create_edge_layer({"viewBridge": self.view})
        self.view.centerOn(280.0, 220.0)
        self.app.processEvents()

        model = GraphModel()
        scene = GraphSceneBridge()
        scene.set_workspace(
            model,
            _build_edge_crossing_pipe_registry(),
            model.active_workspace.workspace_id,
        )
        upper_right_id = scene.add_node_from_type("tests.edge_crossing_pipe_probe_node", 420.0, 40.0)
        lower_left_id = scene.add_node_from_type("tests.edge_crossing_pipe_probe_node", 40.0, 300.0)
        lower_right_id = scene.add_node_from_type("tests.edge_crossing_pipe_probe_node", 420.0, 300.0)
        upper_left_id = scene.add_node_from_type("tests.edge_crossing_pipe_probe_node", 40.0, 40.0)
        under_edge_id = scene.add_edge(upper_right_id, "flow_out", lower_left_id, "flow_in")
        over_edge_id = scene.add_edge(lower_right_id, "flow_out", upper_left_id, "flow_in")

        edge_layer.setProperty("nodes", scene.nodes_model)
        edge_layer.setProperty("edges", scene.edges_model)
        edge_layer.setProperty("edgeCrossingStyle", "gap_break")
        self.app.processEvents()
        edge_layer.requestRedraw()
        self.app.processEvents()

        snapshots = [
            edge_layer._visibleEdgeSnapshot(under_edge_id).toVariant(),
            edge_layer._visibleEdgeSnapshot(over_edge_id).toVariant(),
        ]
        snapshots.sort(key=lambda payload: payload["drawOrderIndex"])
        lower_snapshot, upper_snapshot = snapshots
        self.assertEqual(lower_snapshot["geometry"]["route"], "pipe")
        self.assertEqual(upper_snapshot["geometry"]["route"], "pipe")
        self.assertEqual(lower_snapshot["drawOrderIndex"], 0)
        self.assertEqual(upper_snapshot["drawOrderIndex"], 1)
        self.assertGreaterEqual(len(lower_snapshot["crossingBreaks"]), 1)
        self.assertEqual(upper_snapshot["crossingBreaks"], [])
        self.assertIn("centerDistance", lower_snapshot["crossingBreaks"][0])
        self.assertIn("tangentY", lower_snapshot["crossingBreaks"][0])

        edge_layer.deleteLater()
        self.app.processEvents()

    def test_a_node_card_theme_neutrals_follow_runtime_theme_changes(self) -> None:
        component = QQmlComponent(self.engine, QUrl.fromLocalFile(str(_NODE_CARD_QML_PATH)))
        if component.status() != QQmlComponent.Status.Ready:
            errors = "\n".join(str(error) for error in component.errors())
            self.fail(f"Failed to load NodeCard.qml:\n{errors}")
        node_payload = {
            "node_id": "node_theme_test",
            "type_id": "core.logger",
            "title": "Logger",
            "x": 120.0,
            "y": 120.0,
            "width": 210.0,
            "height": 132.0,
            "accent": "#2F89FF",
            "collapsed": False,
            "selected": False,
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
                    "key": "message",
                    "label": "Message",
                    "direction": "in",
                    "kind": "data",
                    "data_type": "str",
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
                },
                {
                    "key": "level",
                    "label": "Level",
                    "inline_editor": "enum",
                    "value": "info",
                    "enum_values": ["info", "warning", "error"],
                    "overridden_by_input": False,
                    "input_port_label": "",
                },
            ],
        }
        if hasattr(component, "createWithInitialProperties"):
            node_card = component.createWithInitialProperties({"nodeData": node_payload})
        else:
            node_card = component.create()
            node_card.setProperty("nodeData", node_payload)
        if node_card is None:
            errors = "\n".join(str(error) for error in component.errors())
            self.fail(f"Failed to instantiate NodeCard.qml:\n{errors}")
        self.app.processEvents()

        self.assertEqual(_color_name(node_card.property("color")), self.graph_theme_bridge.node_palette["card_bg"])
        self.assertEqual(_color_name(node_card.property("headerColor")), self.graph_theme_bridge.node_palette["header_bg"])
        self.assertEqual(_color_name(node_card.property("inlineRowColor")), self.graph_theme_bridge.node_palette["inline_row_bg"])
        self.assertEqual(
            _color_name(node_card.property("inlineInputBackgroundColor")),
            self.graph_theme_bridge.node_palette["inline_input_bg"],
        )
        self.assertEqual(
            _color_name(node_card.property("portLabelColor")),
            self.graph_theme_bridge.node_palette["port_label_fg"],
        )
        self.assertEqual(
            _color_name(node_card.basePortColor("exec")),
            _color_name(self.graph_theme_bridge.port_kind_palette["exec"]),
        )
        self.assertEqual(
            _color_name(node_card.basePortColor("data")),
            _color_name(self.graph_theme_bridge.port_kind_palette["data"]),
        )
        self.assertEqual(
            _color_name(node_card.basePortColor("completed")),
            _color_name(self.graph_theme_bridge.port_kind_palette["completed"]),
        )
        self.assertEqual(
            _color_name(node_card.basePortColor("failed")),
            _color_name(self.graph_theme_bridge.port_kind_palette["failed"]),
        )

        self.theme_bridge.apply_theme("stitch_light")
        self.graph_theme_bridge.apply_theme("graph_stitch_light")
        self.app.processEvents()

        self.assertEqual(_color_name(node_card.property("color")), self.graph_theme_bridge.node_palette["card_bg"])
        self.assertEqual(_color_name(node_card.property("headerColor")), self.graph_theme_bridge.node_palette["header_bg"])
        self.assertEqual(_color_name(node_card.property("inlineRowColor")), self.graph_theme_bridge.node_palette["inline_row_bg"])
        self.assertEqual(
            _color_name(node_card.property("inlineInputBackgroundColor")),
            self.graph_theme_bridge.node_palette["inline_input_bg"],
        )
        self.assertEqual(
            _color_name(node_card.property("portLabelColor")),
            self.graph_theme_bridge.node_palette["port_label_fg"],
        )
        self.assertEqual(
            _color_name(node_card.basePortColor("exec")),
            _color_name(self.graph_theme_bridge.port_kind_palette["exec"]),
        )
        self.assertEqual(
            _color_name(node_card.basePortColor("data")),
            _color_name(self.graph_theme_bridge.port_kind_palette["data"]),
        )
        self.assertEqual(
            _color_name(node_card.basePortColor("completed")),
            _color_name(self.graph_theme_bridge.port_kind_palette["completed"]),
        )
        self.assertEqual(
            _color_name(node_card.basePortColor("failed")),
            _color_name(self.graph_theme_bridge.port_kind_palette["failed"]),
        )

        node_card.deleteLater()
        self.app.processEvents()

__all__ = ['GraphCanvasQmlPreferenceRenderingTests']
