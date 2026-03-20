from __future__ import annotations

import unittest

from tests.graph_track_b.scene_and_model import (
    QApplication,
    GraphThemeBridge,
    QObject,
    QQmlComponent,
    QQmlEngine,
    QMetaObject,
    Qt,
    QUrl,
    STITCH_DARK_V1,
    STITCH_LIGHT_V1,
    ThemeBridge,
    ViewportBridge,
    _GRAPH_CANVAS_QML_PATH,
    _NODE_CARD_QML_PATH,
    _GraphCanvasPreferenceBridge,
    _alpha_color_name,
    _color_name,
)
from tests.qt_wait import wait_for_condition_or_raise


def _main_window_graphics_state(*, performance_mode: str = "full_fidelity") -> dict[str, object]:
    return {
        "graphics_show_grid": True,
        "graphics_show_minimap": True,
        "graphics_minimap_expanded": True,
        "graphics_node_shadow": True,
        "graphics_shadow_strength": 70,
        "graphics_shadow_softness": 50,
        "graphics_shadow_offset": 4,
        "graphics_performance_mode": performance_mode,
        "snap_to_grid_enabled": False,
        "snap_grid_size": 20.0,
    }


class GraphCanvasQmlPreferenceBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = QApplication.instance() or QApplication([])
        self.engine = QQmlEngine()
        self.theme_bridge = ThemeBridge(theme_id="stitch_dark")
        self.graph_theme_bridge = GraphThemeBridge(theme_id="graph_stitch_dark")
        self.engine.rootContext().setContextProperty("themeBridge", self.theme_bridge)
        self.engine.rootContext().setContextProperty("graphThemeBridge", self.graph_theme_bridge)
        self.component = QQmlComponent(self.engine, QUrl.fromLocalFile(str(_GRAPH_CANVAS_QML_PATH)))
        if self.component.status() != QQmlComponent.Status.Ready:
            errors = "\n".join(str(error) for error in self.component.errors())
            self.fail(f"Failed to load GraphCanvas.qml:\n{errors}")
        self.bridge = _GraphCanvasPreferenceBridge()
        self.view = ViewportBridge()
        self.view.set_viewport_size(1280.0, 720.0)
        initial_properties = {
            "mainWindowBridge": self.bridge,
            "viewBridge": self.view,
            "width": 1280.0,
            "height": 720.0,
        }
        if hasattr(self.component, "createWithInitialProperties"):
            self.canvas = self.component.createWithInitialProperties(initial_properties)
        else:
            self.canvas = self.component.create()
            for key, value in initial_properties.items():
                self.canvas.setProperty(key, value)
        if self.canvas is None:
            errors = "\n".join(str(error) for error in self.component.errors())
            self.fail(f"Failed to instantiate GraphCanvas.qml:\n{errors}")
        self.app.processEvents()

    def tearDown(self) -> None:
        if self.canvas is not None:
            self.canvas.deleteLater()
        self.app.processEvents()
        self.engine.deleteLater()
        self.app.processEvents()

    def test_graph_canvas_properties_follow_runtime_preference_updates(self) -> None:
        self.assertTrue(bool(self.canvas.property("showGrid")))
        self.assertTrue(bool(self.canvas.property("minimapVisible")))
        self.assertTrue(bool(self.canvas.property("minimapExpanded")))

        self.bridge.set_graphics_show_grid_value(False)
        self.bridge.set_graphics_show_minimap_value(False)
        self.bridge.set_graphics_minimap_expanded_value(False)
        self.app.processEvents()

        self.assertFalse(bool(self.canvas.property("showGrid")))
        self.assertFalse(bool(self.canvas.property("minimapVisible")))
        self.assertFalse(bool(self.canvas.property("minimapExpanded")))

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

    def test_graph_canvas_performance_policy_resolves_max_performance_idle_without_visual_degradation(self) -> None:
        policy = self.canvas.findChild(QObject, "graphCanvasPerformancePolicy")
        self.assertIsNotNone(policy)

        self.canvas.setProperty("mainWindowBridge", _main_window_graphics_state(performance_mode="max_performance"))
        self.app.processEvents()

        self.assertEqual(self.canvas.property("resolvedGraphicsPerformanceMode"), "max_performance")
        self.assertFalse(bool(self.canvas.property("mutationBurstActive")))
        self.assertFalse(bool(self.canvas.property("transientPerformanceActivityActive")))
        self.assertFalse(bool(self.canvas.property("transientDegradedWindowActive")))
        self.assertFalse(bool(self.canvas.property("viewportInteractionWorldCacheActive")))
        self.assertTrue(bool(self.canvas.property("highQualityRendering")))
        self.assertFalse(bool(self.canvas.property("edgeLabelSimplificationActive")))
        self.assertEqual(policy.property("resolvedMode"), "max_performance")

    def test_graph_canvas_mutation_burst_policy_activates_and_recovers_with_existing_idle_window(self) -> None:
        policy = self.canvas.findChild(QObject, "graphCanvasPerformancePolicy")
        self.assertIsNotNone(policy)

        self.canvas.setProperty("mainWindowBridge", _main_window_graphics_state(performance_mode="max_performance"))
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
        self.assertTrue(bool(self.canvas.property("highQualityRendering")))
        self.assertFalse(bool(self.canvas.property("edgeLabelSimplificationActive")))

        wait_for_condition_or_raise(
            lambda: not bool(self.canvas.property("mutationBurstActive")),
            timeout_ms=190,
            app=self.app,
            timeout_message="Timed out waiting for synthetic mutation burst policy to settle.",
        )
        self.assertFalse(bool(self.canvas.property("transientPerformanceActivityActive")))
        self.assertFalse(bool(self.canvas.property("transientDegradedWindowActive")))
        self.assertTrue(bool(self.canvas.property("highQualityRendering")))

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
        child_objects = list(self.canvas.children())
        self.assertIn(edge_layer, child_objects)
        self.assertIn(world, child_objects)
        self.assertLess(child_objects.index(edge_layer), child_objects.index(world))

    def test_graph_canvas_live_resize_geometry_propagates_to_edge_layer(self) -> None:
        edge_layer = self.canvas.findChild(QObject, "graphCanvasEdgeLayer")
        self.assertIsNotNone(edge_layer)

        payload = {"node_resize_test": {"x": 180.0, "y": 120.0, "width": 260.0, "height": 144.0}}
        self.canvas.setProperty("liveNodeGeometry", payload)
        self.app.processEvents()

        self.assertEqual(self.canvas.property("liveNodeGeometry"), payload)
        self.assertEqual(edge_layer.property("liveNodeGeometry"), payload)

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

        self.view.set_zoom(1.4)
        self.app.processEvents()

        self.assertEqual(int(background.property("_redrawRequestCount")) - background_redraws, 1)
        self.assertEqual(int(edge_layer.property("_redrawRequestCount")) - edge_redraws, 1)

        background_redraws = int(background.property("_redrawRequestCount"))
        edge_redraws = int(edge_layer.property("_redrawRequestCount"))

        self.view.centerOn(18.0, -22.0)
        self.app.processEvents()

        self.assertEqual(int(background.property("_redrawRequestCount")) - background_redraws, 1)
        self.assertEqual(int(edge_layer.property("_redrawRequestCount")) - edge_redraws, 1)

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


__all__ = ["GraphCanvasQmlPreferenceBindingTests"]
