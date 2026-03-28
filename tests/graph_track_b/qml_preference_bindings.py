from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest

from PyQt6.QtCore import QPoint
from PyQt6.QtQuick import QQuickWindow
from PyQt6.QtTest import QTest

from ea_node_editor.ui_qml.graph_canvas_command_bridge import GraphCanvasCommandBridge
from ea_node_editor.ui_qml.graph_canvas_state_bridge import GraphCanvasStateBridge
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

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SUBPROCESS_TEST_RUNNER = (
    "import sys, unittest; "
    "target = sys.argv[1]; "
    "suite = unittest.defaultTestLoader.loadTestsFromName(target); "
    "result = unittest.TextTestRunner(verbosity=2).run(suite); "
    "sys.exit(0 if result.wasSuccessful() else 1)"
)
_EDGE_LAYER_QML_PATH = _GRAPH_CANVAS_QML_PATH.parent / "graph" / "EdgeLayer.qml"


def _named_child_items(root: QObject, object_name: str) -> list[QObject]:
    matches: list[QObject] = []

    def _walk(item: QObject | None) -> None:
        if item is None:
            return
        if item.objectName() == object_name:
            matches.append(item)
        child_items = getattr(item, "childItems", None)
        if callable(child_items):
            for child in child_items():
                _walk(child)

    _walk(root)
    return matches


class _GraphCanvasPerformancePreferenceBridge(_GraphCanvasPreferenceBridge):
    def __init__(self) -> None:
        super().__init__()
        self._graphics_node_shadow = True
        self._graphics_shadow_strength = 70
        self._graphics_shadow_softness = 50
        self._graphics_shadow_offset = 4
        self._graphics_performance_mode = "full_fidelity"

    @property
    def graphics_node_shadow(self) -> bool:
        return bool(self._graphics_node_shadow)

    @property
    def graphics_shadow_strength(self) -> int:
        return int(self._graphics_shadow_strength)

    @property
    def graphics_shadow_softness(self) -> int:
        return int(self._graphics_shadow_softness)

    @property
    def graphics_shadow_offset(self) -> int:
        return int(self._graphics_shadow_offset)

    @property
    def graphics_performance_mode(self) -> str:
        return str(self._graphics_performance_mode)

    def set_graphics_shadow_softness_value(self, value: int) -> None:
        normalized = int(value)
        if self._graphics_shadow_softness == normalized:
            return
        self._graphics_shadow_softness = normalized
        self.graphics_preferences_changed.emit()

    def set_graphics_performance_mode_value(self, value: str) -> None:
        normalized = str(value or "full_fidelity")
        if self._graphics_performance_mode == normalized:
            return
        self._graphics_performance_mode = normalized
        self.graphics_preferences_changed.emit()


class GraphCanvasQmlPreferenceBindingTests(unittest.TestCase):
    def _create_canvas(self, initial_properties: dict[str, object]) -> QObject:
        if hasattr(self.component, "createWithInitialProperties"):
            canvas = self.component.createWithInitialProperties(initial_properties)
        else:
            canvas = self.component.create()
            for key, value in initial_properties.items():
                canvas.setProperty(key, value)
        if canvas is None:
            errors = "\n".join(str(error) for error in self.component.errors())
            self.fail(f"Failed to instantiate GraphCanvas.qml:\n{errors}")
        self.app.processEvents()
        return canvas

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
        self.bridge = _GraphCanvasPerformancePreferenceBridge()
        self.view = ViewportBridge()
        self.view.set_viewport_size(1280.0, 720.0)
        self.canvas_state_bridge = GraphCanvasStateBridge(
            shell_window=self.bridge,  # type: ignore[arg-type]
            view_bridge=self.view,
        )
        self.canvas_command_bridge = GraphCanvasCommandBridge(
            shell_window=self.bridge,  # type: ignore[arg-type]
            view_bridge=self.view,
        )
        self.canvas = self._create_canvas(
            {
                "canvasStateBridge": self.canvas_state_bridge,
                "canvasCommandBridge": self.canvas_command_bridge,
                "width": 1280.0,
                "height": 720.0,
            }
        )

    def tearDown(self) -> None:
        if self.canvas is not None:
            self.canvas.deleteLater()
        self.app.processEvents()
        self.engine.deleteLater()
        self.app.processEvents()

    def test_graph_canvas_properties_follow_runtime_preference_updates(self) -> None:
        self.assertTrue(bool(self.canvas.property("showGrid")))
        self.assertEqual(str(self.canvas.property("gridStyle")), "lines")
        self.assertTrue(bool(self.canvas.property("minimapVisible")))
        self.assertTrue(bool(self.canvas.property("minimapExpanded")))
        self.assertTrue(bool(self.canvas.property("showPortLabels")))

        self.bridge.set_graphics_show_grid_value(False)
        self.bridge.set_graphics_show_minimap_value(False)
        self.bridge.set_graphics_minimap_expanded_value(False)
        self.bridge.set_graphics_show_port_labels_value(False)
        self.app.processEvents()

        self.assertFalse(bool(self.canvas.property("showGrid")))
        self.assertFalse(bool(self.canvas.property("minimapVisible")))
        self.assertFalse(bool(self.canvas.property("minimapExpanded")))
        self.assertFalse(bool(self.canvas.property("showPortLabels")))

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
                timeout_ms=500,
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
            timeout_ms=190,
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
            timeout_ms=1500,
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

    def test_edge_layer_applies_live_drag_offsets_to_recomputed_node_port_geometry(self) -> None:
        component = QQmlComponent(self.engine, QUrl.fromLocalFile(str(_EDGE_LAYER_QML_PATH)))
        if component.status() != QQmlComponent.Status.Ready:
            errors = "\n".join(str(error) for error in component.errors())
            self.fail(f"Failed to load EdgeLayer.qml:\n{errors}")

        if hasattr(component, "createWithInitialProperties"):
            edge_layer = component.createWithInitialProperties({"width": 1280.0, "height": 720.0})
        else:
            edge_layer = component.create()
            if edge_layer is not None:
                edge_layer.setProperty("width", 1280.0)
                edge_layer.setProperty("height", 720.0)
        if edge_layer is None:
            errors = "\n".join(str(error) for error in component.errors())
            self.fail(f"Failed to instantiate EdgeLayer.qml:\n{errors}")

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


class _SubprocessGraphCanvasQmlPreferenceBindingTest(unittest.TestCase):
    __test__ = False

    def __init__(self, target: str) -> None:
        super().__init__(methodName="runTest")
        self._target = target

    def id(self) -> str:
        return self._target

    def __str__(self) -> str:
        return self._target

    def shortDescription(self) -> str:
        return self._target

    def runTest(self) -> None:
        env = os.environ.copy()
        env.setdefault("QT_QPA_PLATFORM", "offscreen")
        result = subprocess.run(
            [sys.executable, "-c", _SUBPROCESS_TEST_RUNNER, self._target],
            cwd=_REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return
        output = "\n".join(
            part.strip()
            for part in (result.stdout, result.stderr)
            if part and part.strip()
        )
        self.fail(
            "Subprocess QML preference binding test failed for "
            f"{self._target} (exit={result.returncode}).\n{output}"
        )


def build_graph_canvas_qml_preference_binding_subprocess_suite(
    loader: unittest.TestLoader,
) -> unittest.TestSuite:
    suite = unittest.TestSuite()
    for test_name in loader.getTestCaseNames(GraphCanvasQmlPreferenceBindingTests):
        target = (
            f"{GraphCanvasQmlPreferenceBindingTests.__module__}."
            f"{GraphCanvasQmlPreferenceBindingTests.__qualname__}.{test_name}"
        )
        suite.addTest(_SubprocessGraphCanvasQmlPreferenceBindingTest(target))
    return suite


def load_tests(loader: unittest.TestLoader, _tests, _pattern):  # noqa: ANN001
    return build_graph_canvas_qml_preference_binding_subprocess_suite(loader)


__all__ = [
    "GraphCanvasQmlPreferenceBindingTests",
    "build_graph_canvas_qml_preference_binding_subprocess_suite",
]
