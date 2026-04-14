from __future__ import annotations

import time
import unittest

from ea_node_editor.graph.model import GraphModel
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.settings import DEFAULT_GRAPHICS_SETTINGS
from ea_node_editor.ui_qml.graph_canvas_state_bridge import GraphCanvasStateBridge
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge
from tests.graph_track_b import (
    qml_preference_performance_suite as _performance_suite,
    qml_preference_rendering_suite as _rendering_suite,
)
from tests.graph_track_b.qml_support import build_graph_canvas_qml_preference_subprocess_suite

_GRAPH_CANVAS_ROOT_BINDINGS_QML_PATH = (
    _rendering_suite._GRAPH_CANVAS_QML_PATH.parent / "graph_canvas" / "GraphCanvasRootBindings.qml"
)
_GRAPH_SHARED_TYPOGRAPHY_QML_PATH = _rendering_suite._NODE_CARD_QML_PATH.parent / "GraphSharedTypography.qml"


class _GraphCanvasTypographyPreferenceBridge(_rendering_suite.QObject):
    graphics_preferences_changed = _rendering_suite.pyqtSignal()
    snap_to_grid_changed = _rendering_suite.pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._graphics_show_grid = True
        self._graphics_grid_style = "lines"
        self._graphics_show_minimap = True
        self._graphics_minimap_expanded = True
        self._graphics_show_port_labels = True
        self._graphics_show_tooltips = True
        self._graphics_edge_crossing_style = "none"
        self._graphics_node_shadow = True
        self._graphics_shadow_strength = 70
        self._graphics_shadow_softness = 50
        self._graphics_shadow_offset = 4
        self._graphics_performance_mode = "full_fidelity"
        self._graphics_graph_label_pixel_size = 10
        self._graphics_graph_node_icon_pixel_size_override: int | None = None
        self._graphics_expand_collision_avoidance = dict(
            DEFAULT_GRAPHICS_SETTINGS["interaction"]["expand_collision_avoidance"]
        )

    @property
    def graphics_show_grid(self) -> bool:
        return bool(self._graphics_show_grid)

    @property
    def graphics_grid_style(self) -> str:
        return str(self._graphics_grid_style)

    @property
    def graphics_show_minimap(self) -> bool:
        return bool(self._graphics_show_minimap)

    @property
    def graphics_minimap_expanded(self) -> bool:
        return bool(self._graphics_minimap_expanded)

    @property
    def graphics_show_port_labels(self) -> bool:
        return bool(self._graphics_show_port_labels)

    @property
    def graphics_show_tooltips(self) -> bool:
        return bool(self._graphics_show_tooltips)

    @property
    def graphics_edge_crossing_style(self) -> str:
        return str(self._graphics_edge_crossing_style)

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

    @property
    def graphics_graph_label_pixel_size(self) -> int:
        return int(self._graphics_graph_label_pixel_size)

    @property
    def graphics_graph_node_icon_pixel_size_override(self) -> int | None:
        return self._graphics_graph_node_icon_pixel_size_override

    @property
    def graphics_node_title_icon_pixel_size(self) -> int:
        override = self._graphics_graph_node_icon_pixel_size_override
        return int(self._graphics_graph_label_pixel_size if override is None else override)

    @property
    def graphics_expand_collision_avoidance(self) -> dict[str, object]:
        return dict(self._graphics_expand_collision_avoidance)

    def set_graphics_graph_label_pixel_size_value(self, value: int) -> None:
        normalized = max(8, min(int(value), 18))
        if self._graphics_graph_label_pixel_size == normalized:
            return
        self._graphics_graph_label_pixel_size = normalized
        self.graphics_preferences_changed.emit()

    def set_graphics_show_tooltips_value(self, value: bool) -> None:
        normalized = bool(value)
        if self._graphics_show_tooltips == normalized:
            return
        self._graphics_show_tooltips = normalized
        self.graphics_preferences_changed.emit()

    def set_graphics_graph_node_icon_pixel_size_override_value(self, value: int | None) -> None:
        normalized = None if value is None else max(8, min(int(value), 50))
        if self._graphics_graph_node_icon_pixel_size_override == normalized:
            return
        self._graphics_graph_node_icon_pixel_size_override = normalized
        self.graphics_preferences_changed.emit()

    def set_graphics_expand_collision_avoidance_value(self, value: dict[str, object]) -> None:
        normalized = dict(value)
        if self._graphics_expand_collision_avoidance == normalized:
            return
        self._graphics_expand_collision_avoidance = normalized
        self.graphics_preferences_changed.emit()


class GraphCanvasQmlPreferenceBindingTests(
    _rendering_suite.GraphCanvasQmlPreferenceRenderingTests,
    _performance_suite.GraphCanvasQmlPreferencePerformanceTests,
):
    """Stable regression entrypoint for packetized Track-B QML preference coverage."""

    __test__ = True

    def _load_qml_component(self, path) -> _rendering_suite.QQmlComponent:
        component = _rendering_suite.QQmlComponent(self.engine, _rendering_suite.QUrl.fromLocalFile(str(path)))
        if component.status() != _rendering_suite.QQmlComponent.Status.Ready:
            errors = "\n".join(str(error) for error in component.errors())
            self.fail(f"Failed to load {path.name}:\n{errors}")
        return component

    def _create_component(self, path, initial_properties: dict[str, object]) -> _rendering_suite.QObject:
        component = self._load_qml_component(path)
        if hasattr(component, "createWithInitialProperties"):
            instance = component.createWithInitialProperties(initial_properties)
        else:
            instance = component.create()
            if instance is not None:
                for key, value in initial_properties.items():
                    instance.setProperty(key, value)
        if instance is None:
            errors = "\n".join(str(error) for error in component.errors())
            self.fail(f"Failed to instantiate {path.name}:\n{errors}")
        self.app.processEvents()
        return instance

    def test_expand_collision_avoidance_bridge_projection_follows_preference_source(self) -> None:
        preference_bridge = _GraphCanvasTypographyPreferenceBridge()
        state_bridge = GraphCanvasStateBridge(
            shell_window=preference_bridge,  # type: ignore[arg-type]
            view_bridge=self.view,
        )
        seen = {"count": 0}
        state_bridge.graphics_preferences_changed.connect(lambda: seen.__setitem__("count", seen["count"] + 1))

        try:
            self.assertEqual(
                state_bridge.graphics_expand_collision_avoidance,
                DEFAULT_GRAPHICS_SETTINGS["interaction"]["expand_collision_avoidance"],
            )

            updated = {
                "enabled": False,
                "strategy": "nearest",
                "scope": "all_movable",
                "radius_mode": "unbounded",
                "local_radius_preset": "large",
                "gap_preset": "tight",
                "animate": False,
            }
            preference_bridge.set_graphics_expand_collision_avoidance_value(updated)
            self.app.processEvents()

            self.assertEqual(state_bridge.graphics_expand_collision_avoidance, updated)
            self.assertEqual(seen["count"], 1)
        finally:
            state_bridge.deleteLater()
            preference_bridge.deleteLater()
            self.app.processEvents()

    def _assert_persistent_node_elapsed_footer_rendering(self) -> None:
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

        class CanvasStateBridgeStub(_rendering_suite.QObject):
            graphics_preferences_changed = _rendering_suite.pyqtSignal()
            scene_nodes_changed = _rendering_suite.pyqtSignal()
            failure_highlight_changed = _rendering_suite.pyqtSignal()
            node_execution_state_changed = _rendering_suite.pyqtSignal()

            def __init__(
                self,
                preference_bridge: _rendering_suite._GraphCanvasPreferenceBridge,
                view_bridge: _rendering_suite.ViewportBridge,
            ) -> None:
                super().__init__()
                self._preference_bridge = preference_bridge
                self._view_bridge = view_bridge
                self._nodes_model = [dict(node_payload)]
                self._running_node_lookup: dict[str, bool] = {}
                self._completed_node_lookup: dict[str, bool] = {}
                self._failed_node_lookup: dict[str, bool] = {}
                self._running_node_started_at_ms_lookup: dict[str, float] = {}
                self._node_elapsed_ms_lookup: dict[str, float] = {}
                self._failed_node_revision = 0
                self._node_execution_revision = 0
                self._preference_bridge.graphics_preferences_changed.connect(self.graphics_preferences_changed.emit)

            @_rendering_suite.pyqtProperty(_rendering_suite.QObject, constant=True)
            def viewport_bridge(self) -> _rendering_suite.ViewportBridge:
                return self._view_bridge

            @_rendering_suite.pyqtProperty(bool, notify=graphics_preferences_changed)
            def graphics_minimap_expanded(self) -> bool:
                return bool(self._preference_bridge.graphics_minimap_expanded)

            @_rendering_suite.pyqtProperty(bool, notify=graphics_preferences_changed)
            def graphics_show_grid(self) -> bool:
                return bool(self._preference_bridge.graphics_show_grid)

            @_rendering_suite.pyqtProperty(str, notify=graphics_preferences_changed)
            def graphics_grid_style(self) -> str:
                return str(self._preference_bridge.graphics_grid_style)

            @_rendering_suite.pyqtProperty(str, notify=graphics_preferences_changed)
            def graphics_edge_crossing_style(self) -> str:
                return str(self._preference_bridge.graphics_edge_crossing_style)

            @_rendering_suite.pyqtProperty(bool, notify=graphics_preferences_changed)
            def graphics_show_minimap(self) -> bool:
                return bool(self._preference_bridge.graphics_show_minimap)

            @_rendering_suite.pyqtProperty(bool, notify=graphics_preferences_changed)
            def graphics_show_port_labels(self) -> bool:
                return bool(self._preference_bridge.graphics_show_port_labels)

            @_rendering_suite.pyqtProperty(bool, notify=graphics_preferences_changed)
            def graphics_node_shadow(self) -> bool:
                return True

            @_rendering_suite.pyqtProperty(int, notify=graphics_preferences_changed)
            def graphics_shadow_strength(self) -> int:
                return 70

            @_rendering_suite.pyqtProperty(int, notify=graphics_preferences_changed)
            def graphics_shadow_softness(self) -> int:
                return 50

            @_rendering_suite.pyqtProperty(int, notify=graphics_preferences_changed)
            def graphics_shadow_offset(self) -> int:
                return 4

            @_rendering_suite.pyqtProperty(str, notify=graphics_preferences_changed)
            def graphics_performance_mode(self) -> str:
                return "full_fidelity"

            @_rendering_suite.pyqtProperty("QVariantList", notify=scene_nodes_changed)
            def nodes_model(self) -> list[dict[str, object]]:
                return list(self._nodes_model)

            @_rendering_suite.pyqtProperty("QVariantList", constant=True)
            def backdrop_nodes_model(self) -> list[dict[str, object]]:
                return []

            @_rendering_suite.pyqtProperty("QVariantList", constant=True)
            def edges_model(self) -> list[dict[str, object]]:
                return []

            @_rendering_suite.pyqtProperty("QVariantMap", constant=True)
            def selected_node_lookup(self) -> dict[str, bool]:
                return {}

            @_rendering_suite.pyqtProperty("QVariantMap", constant=True)
            def workspace_scene_bounds_payload(self) -> dict[str, float]:
                return {}

            @_rendering_suite.pyqtProperty("QVariantMap", notify=failure_highlight_changed)
            def failed_node_lookup(self) -> dict[str, bool]:
                return dict(self._failed_node_lookup)

            @_rendering_suite.pyqtProperty(int, notify=failure_highlight_changed)
            def failed_node_revision(self) -> int:
                return int(self._failed_node_revision)

            @_rendering_suite.pyqtProperty(str, notify=failure_highlight_changed)
            def failed_node_title(self) -> str:
                return "Logger" if self._failed_node_lookup else ""

            @_rendering_suite.pyqtProperty("QVariantMap", notify=node_execution_state_changed)
            def running_node_lookup(self) -> dict[str, bool]:
                return dict(self._running_node_lookup)

            @_rendering_suite.pyqtProperty("QVariantMap", notify=node_execution_state_changed)
            def completed_node_lookup(self) -> dict[str, bool]:
                return dict(self._completed_node_lookup)

            @_rendering_suite.pyqtProperty("QVariantMap", notify=node_execution_state_changed)
            def running_node_started_at_ms_lookup(self) -> dict[str, float]:
                return dict(self._running_node_started_at_ms_lookup)

            @_rendering_suite.pyqtProperty("QVariantMap", notify=node_execution_state_changed)
            def node_elapsed_ms_lookup(self) -> dict[str, float]:
                return dict(self._node_elapsed_ms_lookup)

            @_rendering_suite.pyqtProperty(int, notify=node_execution_state_changed)
            def node_execution_revision(self) -> int:
                return int(self._node_execution_revision)

            def set_running_node_state(self, tracked_node_id: str, started_at_ms: float) -> None:
                self._running_node_lookup = {str(tracked_node_id): True}
                self._completed_node_lookup = {}
                self._running_node_started_at_ms_lookup = {str(tracked_node_id): float(started_at_ms)}
                self._node_execution_revision += 1
                self.node_execution_state_changed.emit()

            def set_completed_node_state(self, tracked_node_id: str, elapsed_ms: float) -> None:
                self._running_node_lookup = {}
                self._completed_node_lookup = {str(tracked_node_id): True}
                self._running_node_started_at_ms_lookup = {}
                self._node_elapsed_ms_lookup = {str(tracked_node_id): float(elapsed_ms)}
                self._node_execution_revision += 1
                self.node_execution_state_changed.emit()

            def clear_terminal_execution_state(self) -> None:
                self._running_node_lookup = {}
                self._completed_node_lookup = {}
                self._running_node_started_at_ms_lookup = {}
                self._node_execution_revision += 1
                self.node_execution_state_changed.emit()

            def clear_cached_elapsed(self) -> None:
                self._node_elapsed_ms_lookup = {}
                self._node_execution_revision += 1
                self.node_execution_state_changed.emit()

            def set_failed_node_state(self, tracked_node_id: str) -> None:
                self._failed_node_lookup = {str(tracked_node_id): True}
                self._failed_node_revision += 1
                self.failure_highlight_changed.emit()

        self.canvas.deleteLater()
        self.app.processEvents()

        canvas_state_bridge = CanvasStateBridgeStub(self.bridge, self.view)
        canvas_command_bridge = _rendering_suite.GraphCanvasCommandBridge(
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

        _rendering_suite.wait_for_condition_or_raise(
            lambda: len(_rendering_suite._named_child_items(self.canvas, "graphNodeCard")) == 1,
            timeout_ms=200,
            app=self.app,
            timeout_message="Timed out waiting for graph canvas execution-visualization node host to appear.",
        )
        node_card = _rendering_suite._named_child_items(self.canvas, "graphNodeCard")[0]
        background_layer = node_card.findChild(_rendering_suite.QObject, "graphNodeChromeBackgroundLayer")
        running_halo = node_card.findChild(_rendering_suite.QObject, "graphNodeRunningHalo")
        running_pulse_halo = node_card.findChild(_rendering_suite.QObject, "graphNodeRunningPulseHalo")
        completed_flash_halo = node_card.findChild(_rendering_suite.QObject, "graphNodeCompletedFlashHalo")
        elapsed_timer = node_card.findChild(_rendering_suite.QObject, "graphNodeElapsedTimer")
        self.assertIsNotNone(background_layer)
        self.assertIsNotNone(running_halo)
        self.assertIsNotNone(running_pulse_halo)
        self.assertIsNotNone(completed_flash_halo)
        self.assertIsNotNone(elapsed_timer)
        if (
            background_layer is None
            or running_halo is None
            or running_pulse_halo is None
            or completed_flash_halo is None
            or elapsed_timer is None
        ):
            self.fail("Expected graph canvas execution chrome items to exist")

        self.assertEqual(str(background_layer.property("effectiveBorderState")), "idle")
        self.assertEqual(dict(self.canvas.property("runningNodeLookup")), {})
        self.assertEqual(dict(self.canvas.property("completedNodeLookup")), {})
        self.assertFalse(bool(elapsed_timer.property("visible")))

        idle_key = str(background_layer.property("cacheKey") or "")
        started_at_ms = (time.time() * 1000.0) - 2100.0
        completed_elapsed_ms = 3487.0

        canvas_state_bridge.set_running_node_state(node_id, started_at_ms)
        _rendering_suite.wait_for_condition_or_raise(
            lambda: bool(node_card.property("isRunningNode"))
            and str(background_layer.property("effectiveBorderState")) == "running"
            and bool(elapsed_timer.property("visible"))
            and bool(elapsed_timer.property("liveElapsedActive"))
            and abs(float(elapsed_timer.property("startedAtMs")) - started_at_ms) < 16.0
            and float(elapsed_timer.property("elapsedMilliseconds")) >= 1700.0,
            timeout_ms=500,
            app=self.app,
            timeout_message="Timed out waiting for lookup-backed live elapsed footer rendering on graph canvas host.",
        )

        self.assertTrue(bool(node_card.property("renderActive")))
        self.assertEqual(int(node_card.property("z")), 31)
        self.assertEqual(dict(self.canvas.property("runningNodeLookup")), {node_id: True})
        self.assertEqual(self.canvas.property("runningNodeStartedAtMsLookup"), {node_id: started_at_ms})
        self.assertEqual(
            _rendering_suite._color_name(background_layer.property("effectiveOutlineColor")),
            _rendering_suite._color_name(node_card.property("runningOutlineColor")),
        )
        self.assertTrue(bool(running_halo.property("visible")))
        self.assertTrue(bool(running_pulse_halo.property("visible")))

        running_key = str(background_layer.property("cacheKey") or "")
        self.assertNotEqual(running_key, idle_key)
        self.assertIn("|running|", running_key)

        canvas_state_bridge.set_completed_node_state(node_id, completed_elapsed_ms)
        _rendering_suite.wait_for_condition_or_raise(
            lambda: bool(node_card.property("isCompletedNode"))
            and not bool(node_card.property("isRunningNode"))
            and str(background_layer.property("effectiveBorderState")) == "completed"
            and bool(elapsed_timer.property("visible"))
            and bool(elapsed_timer.property("cachedElapsedActive"))
            and str(elapsed_timer.property("text") or "") == "3.5s",
            timeout_ms=300,
            app=self.app,
            timeout_message="Timed out waiting for cached elapsed footer rendering on graph canvas host.",
        )

        self.assertEqual(int(node_card.property("z")), 29)
        self.assertEqual(dict(self.canvas.property("runningNodeLookup")), {})
        self.assertEqual(dict(self.canvas.property("completedNodeLookup")), {node_id: True})
        self.assertEqual(self.canvas.property("nodeElapsedMsLookup"), {node_id: completed_elapsed_ms})
        self.assertFalse(bool(elapsed_timer.property("liveElapsedActive")))
        self.assertAlmostEqual(float(elapsed_timer.property("cachedElapsedMilliseconds")), completed_elapsed_ms, places=2)
        self.assertEqual(
            _rendering_suite._color_name(elapsed_timer.property("color")),
            _rendering_suite._color_name(node_card.property("completedElapsedFooterColor")),
        )
        self.assertAlmostEqual(
            float(elapsed_timer.property("opacity")),
            float(node_card.property("completedElapsedFooterOpacity")),
            places=2,
        )
        self.assertFalse(bool(running_halo.property("visible")))
        self.assertFalse(bool(running_pulse_halo.property("visible")))

        _rendering_suite.QTest.qWait(80)
        self.app.processEvents()
        self.assertGreater(float(background_layer.property("completedFlashProgress")), 0.0)

        completed_key = str(background_layer.property("cacheKey") or "")
        self.assertNotEqual(completed_key, running_key)
        self.assertIn("|completed|", completed_key)

        canvas_state_bridge.clear_terminal_execution_state()
        _rendering_suite.wait_for_condition_or_raise(
            lambda: not bool(node_card.property("isCompletedNode"))
            and not bool(node_card.property("isRunningNode"))
            and bool(elapsed_timer.property("visible"))
            and bool(elapsed_timer.property("cachedElapsedActive")),
            timeout_ms=300,
            app=self.app,
            timeout_message="Timed out waiting for cached elapsed footer persistence after terminal cleanup.",
        )

        canvas_state_bridge.clear_cached_elapsed()
        _rendering_suite.wait_for_condition_or_raise(
            lambda: not bool(elapsed_timer.property("visible"))
            and not bool(elapsed_timer.property("cachedElapsedActive")),
            timeout_ms=300,
            app=self.app,
            timeout_message="Timed out waiting for cached elapsed footer invalidation on graph canvas host.",
        )

        canvas_state_bridge.set_running_node_state(node_id, (time.time() * 1000.0) - 1600.0)
        _rendering_suite.wait_for_condition_or_raise(
            lambda: bool(node_card.property("isRunningNode"))
            and bool(elapsed_timer.property("visible"))
            and bool(elapsed_timer.property("liveElapsedActive")),
            timeout_ms=300,
            app=self.app,
            timeout_message="Timed out waiting for live elapsed footer to restore before failure-priority check.",
        )

        canvas_state_bridge.set_failed_node_state(node_id)
        _rendering_suite.wait_for_condition_or_raise(
            lambda: str(background_layer.property("effectiveBorderState")) == "failed"
            and not bool(elapsed_timer.property("visible")),
            timeout_ms=300,
            app=self.app,
            timeout_message="Timed out waiting for failure priority to hide the elapsed footer.",
        )

        self.assertEqual(dict(self.canvas.property("failedNodeLookup")), {node_id: True})
        self.assertEqual(
            _rendering_suite._color_name(background_layer.property("effectiveOutlineColor")),
            _rendering_suite._color_name(node_card.property("failureOutlineColor")),
        )
        self.assertFalse(bool(running_halo.property("visible")))
        self.assertFalse(bool(running_pulse_halo.property("visible")))
        self.assertFalse(bool(completed_flash_halo.property("visible")))
        self.assertFalse(bool(elapsed_timer.property("liveElapsedActive")))
        self.assertFalse(bool(elapsed_timer.property("cachedElapsedActive")))
        self.assertIn("|failed|", str(background_layer.property("cacheKey") or ""))

    def test_graph_typography_qml_contract_graph_typography_inline_edge_root_bindings_and_shared_roles_follow_preference_projection(
        self,
    ) -> None:
        preference_bridge = _GraphCanvasTypographyPreferenceBridge()
        state_bridge = GraphCanvasStateBridge(
            shell_window=preference_bridge,  # type: ignore[arg-type]
            view_bridge=self.view,
        )
        root_bindings = self._create_component(
            _GRAPH_CANVAS_ROOT_BINDINGS_QML_PATH,
            {"canvasStateBridge": state_bridge},
        )
        typography = self._create_component(
            _GRAPH_SHARED_TYPOGRAPHY_QML_PATH,
            {"graphLabelPixelSize": int(root_bindings.property("graphLabelPixelSize"))},
        )

        try:
            self.assertEqual(int(root_bindings.property("graphLabelPixelSize")), 10)
            expected_defaults = {
                "nodeTitlePixelSize": 12,
                "portLabelPixelSize": 10,
                "elapsedFooterPixelSize": 10,
                "inlinePropertyPixelSize": 10,
                "badgePixelSize": 9,
                "edgeLabelPixelSize": 11,
                "edgePillPixelSize": 12,
                "execArrowPortPixelSize": 18,
                "nodeTitleFontWeight": 700,
                "portLabelFontWeight": 400,
                "inlinePropertyFontWeight": 400,
                "badgeFontWeight": 700,
                "edgeLabelFontWeight": 500,
                "edgePillFontWeight": 600,
                "execArrowPortFontWeight": 900,
            }
            for property_name, expected_value in expected_defaults.items():
                with self.subTest(property_name=property_name, expected_value=expected_value):
                    self.assertEqual(int(typography.property(property_name)), expected_value)

            preference_bridge.set_graphics_graph_label_pixel_size_value(16)
            _rendering_suite.wait_for_condition_or_raise(
                lambda: int(root_bindings.property("graphLabelPixelSize")) == 16,
                timeout_ms=200,
                app=self.app,
                timeout_message="Timed out waiting for GraphCanvasRootBindings to project graph label pixel size.",
            )
            typography.setProperty("graphLabelPixelSize", int(root_bindings.property("graphLabelPixelSize")))
            self.app.processEvents()

            expected_updated_sizes = {
                "nodeTitlePixelSize": 18,
                "portLabelPixelSize": 16,
                "elapsedFooterPixelSize": 16,
                "inlinePropertyPixelSize": 16,
                "badgePixelSize": 15,
                "edgeLabelPixelSize": 17,
                "edgePillPixelSize": 18,
                "execArrowPortPixelSize": 24,
            }
            for property_name, expected_value in expected_updated_sizes.items():
                with self.subTest(property_name=property_name, expected_value=expected_value):
                    self.assertEqual(int(typography.property(property_name)), expected_value)
        finally:
            typography.deleteLater()
            root_bindings.deleteLater()
            self.app.processEvents()

    def test_graph_typography_dialog_qml_bindings_follow_bridge_projection(self) -> None:
        preference_bridge = _GraphCanvasTypographyPreferenceBridge()
        state_bridge = GraphCanvasStateBridge(
            shell_window=preference_bridge,  # type: ignore[arg-type]
            view_bridge=self.view,
        )
        root_bindings = self._create_component(
            _GRAPH_CANVAS_ROOT_BINDINGS_QML_PATH,
            {"canvasStateBridge": state_bridge},
        )
        typography = self._create_component(
            _GRAPH_SHARED_TYPOGRAPHY_QML_PATH,
            {"graphLabelPixelSize": int(root_bindings.property("graphLabelPixelSize"))},
        )

        try:
            self.assertEqual(int(root_bindings.property("graphLabelPixelSize")), 10)
            self.assertEqual(int(typography.property("graphLabelPixelSize")), 10)
            self.assertEqual(int(typography.property("nodeTitlePixelSize")), 12)

            preference_bridge.set_graphics_graph_label_pixel_size_value(16)
            _rendering_suite.wait_for_condition_or_raise(
                lambda: int(root_bindings.property("graphLabelPixelSize")) == 16,
                timeout_ms=200,
                app=self.app,
                timeout_message="Timed out waiting for dialog-owned typography preference projection to reach root bindings.",
            )
            typography.setProperty("graphLabelPixelSize", int(root_bindings.property("graphLabelPixelSize")))
            self.app.processEvents()

            self.assertEqual(int(typography.property("graphLabelPixelSize")), 16)
            self.assertEqual(int(typography.property("portLabelPixelSize")), 16)
            self.assertEqual(int(typography.property("nodeTitlePixelSize")), 18)
        finally:
            typography.deleteLater()
            root_bindings.deleteLater()
            self.app.processEvents()

    def test_graph_tooltip_qml_bindings_follow_bridge_projection(self) -> None:
        preference_bridge = _GraphCanvasTypographyPreferenceBridge()
        state_bridge = GraphCanvasStateBridge(
            shell_window=preference_bridge,  # type: ignore[arg-type]
            view_bridge=self.view,
        )
        root_bindings = self._create_component(
            _GRAPH_CANVAS_ROOT_BINDINGS_QML_PATH,
            {"canvasStateBridge": state_bridge},
        )

        try:
            self.assertTrue(bool(state_bridge.graphics_show_tooltips))
            self.assertTrue(bool(root_bindings.property("showTooltips")))

            preference_bridge.set_graphics_show_tooltips_value(False)
            _rendering_suite.wait_for_condition_or_raise(
                lambda: not bool(root_bindings.property("showTooltips")),
                timeout_ms=200,
                app=self.app,
                timeout_message="Timed out waiting for GraphCanvasRootBindings to project tooltip visibility policy.",
            )

            self.assertFalse(bool(state_bridge.graphics_show_tooltips))
            self.assertFalse(bool(root_bindings.property("showTooltips")))
        finally:
            root_bindings.deleteLater()
            self.app.processEvents()

    def test_graph_node_icon_size_qml_bindings_project_effective_size_without_text_role_drift(self) -> None:
        preference_bridge = _GraphCanvasTypographyPreferenceBridge()
        state_bridge = GraphCanvasStateBridge(
            shell_window=preference_bridge,  # type: ignore[arg-type]
            view_bridge=self.view,
        )
        root_bindings = self._create_component(
            _GRAPH_CANVAS_ROOT_BINDINGS_QML_PATH,
            {"canvasStateBridge": state_bridge},
        )
        typography = self._create_component(
            _GRAPH_SHARED_TYPOGRAPHY_QML_PATH,
            {
                "graphLabelPixelSize": int(root_bindings.property("graphLabelPixelSize")),
                "graphNodeIconPixelSize": int(root_bindings.property("nodeTitleIconPixelSize")),
            },
        )

        try:
            self.assertEqual(int(root_bindings.property("graphLabelPixelSize")), 10)
            self.assertIsNone(root_bindings.property("graphNodeIconPixelSizeOverride"))
            self.assertEqual(int(root_bindings.property("nodeTitleIconPixelSize")), 10)
            self.assertEqual(int(typography.property("nodeTitleIconPixelSize")), 10)
            self.assertEqual(int(typography.property("nodeTitlePixelSize")), 12)

            preference_bridge.set_graphics_graph_label_pixel_size_value(16)
            _rendering_suite.wait_for_condition_or_raise(
                lambda: int(root_bindings.property("nodeTitleIconPixelSize")) == 16,
                timeout_ms=200,
                app=self.app,
                timeout_message="Timed out waiting for automatic node title icon size to follow graph label size.",
            )
            typography.setProperty("graphLabelPixelSize", int(root_bindings.property("graphLabelPixelSize")))
            typography.setProperty("graphNodeIconPixelSize", int(root_bindings.property("nodeTitleIconPixelSize")))
            self.app.processEvents()

            self.assertEqual(int(typography.property("nodeTitleIconPixelSize")), 16)
            self.assertEqual(int(typography.property("nodeTitlePixelSize")), 18)

            preference_bridge.set_graphics_graph_node_icon_pixel_size_override_value(12)
            _rendering_suite.wait_for_condition_or_raise(
                lambda: int(root_bindings.property("nodeTitleIconPixelSize")) == 12
                and int(root_bindings.property("graphNodeIconPixelSizeOverride")) == 12,
                timeout_ms=200,
                app=self.app,
                timeout_message="Timed out waiting for explicit node title icon size override projection.",
            )
            typography.setProperty("graphNodeIconPixelSize", int(root_bindings.property("nodeTitleIconPixelSize")))
            self.app.processEvents()

            self.assertEqual(int(typography.property("nodeTitleIconPixelSize")), 12)
            self.assertEqual(int(typography.property("nodeTitlePixelSize")), 18)
            self.assertEqual(int(typography.property("portLabelPixelSize")), 16)
        finally:
            typography.deleteLater()
            root_bindings.deleteLater()
            self.app.processEvents()

    def test_graph_typography_qml_contract_scene_refresh_updates_standard_metrics_and_edge_geometry(
        self,
    ) -> None:
        preference_bridge = _GraphCanvasTypographyPreferenceBridge()
        scene = GraphSceneBridge(preference_bridge)
        scene.bind_graph_theme_bridge(GraphThemeBridge(preference_bridge, theme_id="graph_stitch_dark"))
        model = GraphModel()
        registry = build_default_registry()
        workspace_id = model.active_workspace.workspace_id
        scene.set_workspace(model, registry, workspace_id)

        source_id = scene.add_node_from_type("core.logger", 40.0, 60.0)
        target_id = scene.add_node_from_type("core.end", 460.0, 80.0)
        edge_id = scene.add_edge(source_id, "exec_out", target_id, "exec_in")
        scene.set_node_port_label(source_id, "message", "Primary Input Payload")
        scene.set_node_port_label(source_id, "exec_out", "Dispatch Result Token")
        scene.refresh_workspace_from_model(workspace_id)

        baseline_nodes = {item["node_id"]: item for item in scene.nodes_model}
        baseline_edges = {item["edge_id"]: item for item in scene.edges_model}
        baseline_source_payload = baseline_nodes[source_id]
        baseline_edge_payload = baseline_edges[edge_id]

        seen = {"nodes": 0, "edges": 0}
        scene.nodes_changed.connect(lambda: seen.__setitem__("nodes", seen["nodes"] + 1))
        scene.edges_changed.connect(lambda: seen.__setitem__("edges", seen["edges"] + 1))

        preference_bridge.set_graphics_graph_label_pixel_size_value(16)
        scene.refresh_workspace_from_model(workspace_id)

        updated_nodes = {item["node_id"]: item for item in scene.nodes_model}
        updated_edges = {item["edge_id"]: item for item in scene.edges_model}
        updated_source_payload = updated_nodes[source_id]
        updated_edge_payload = updated_edges[edge_id]

        self.assertGreaterEqual(seen["nodes"], 1)
        self.assertGreaterEqual(seen["edges"], 1)
        self.assertGreater(
            float(updated_source_payload["surface_metrics"]["standard_title_full_width"]),
            float(baseline_source_payload["surface_metrics"]["standard_title_full_width"]),
        )
        self.assertGreater(
            float(updated_source_payload["surface_metrics"]["standard_port_label_min_width"]),
            float(baseline_source_payload["surface_metrics"]["standard_port_label_min_width"]),
        )
        self.assertGreater(float(updated_source_payload["width"]), float(baseline_source_payload["width"]))
        self.assertGreater(
            float(updated_edge_payload["source_anchor_bounds"]["width"]),
            float(baseline_edge_payload["source_anchor_bounds"]["width"]),
        )
        self.assertGreater(float(updated_edge_payload["sx"]), float(baseline_edge_payload["sx"]))

    def test_graph_typography_host_chrome_canvas_bindings_update_standard_title_ports_and_elapsed_footer(
        self,
    ) -> None:
        preference_bridge = _GraphCanvasTypographyPreferenceBridge()
        node_id = "node_typography_host_chrome"
        started_at_ms = (time.time() * 1000.0) - 2100.0
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
                "body_left_margin": 8.0,
                "body_right_margin": 8.0,
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

        class CanvasStateBridgeStub(_rendering_suite.QObject):
            graphics_preferences_changed = _rendering_suite.pyqtSignal()
            scene_nodes_changed = _rendering_suite.pyqtSignal()
            failure_highlight_changed = _rendering_suite.pyqtSignal()
            node_execution_state_changed = _rendering_suite.pyqtSignal()

            def __init__(
                self,
                preference_bridge: _GraphCanvasTypographyPreferenceBridge,
                view_bridge: _rendering_suite.ViewportBridge,
            ) -> None:
                super().__init__()
                self._preference_bridge = preference_bridge
                self._view_bridge = view_bridge
                self._preference_bridge.graphics_preferences_changed.connect(self.graphics_preferences_changed.emit)

            @_rendering_suite.pyqtProperty(_rendering_suite.QObject, constant=True)
            def viewport_bridge(self) -> _rendering_suite.ViewportBridge:
                return self._view_bridge

            @_rendering_suite.pyqtProperty(bool, notify=graphics_preferences_changed)
            def graphics_minimap_expanded(self) -> bool:
                return bool(self._preference_bridge.graphics_minimap_expanded)

            @_rendering_suite.pyqtProperty(bool, notify=graphics_preferences_changed)
            def graphics_show_grid(self) -> bool:
                return bool(self._preference_bridge.graphics_show_grid)

            @_rendering_suite.pyqtProperty(str, notify=graphics_preferences_changed)
            def graphics_grid_style(self) -> str:
                return str(self._preference_bridge.graphics_grid_style)

            @_rendering_suite.pyqtProperty(str, notify=graphics_preferences_changed)
            def graphics_edge_crossing_style(self) -> str:
                return str(self._preference_bridge.graphics_edge_crossing_style)

            @_rendering_suite.pyqtProperty(bool, notify=graphics_preferences_changed)
            def graphics_show_minimap(self) -> bool:
                return bool(self._preference_bridge.graphics_show_minimap)

            @_rendering_suite.pyqtProperty(bool, notify=graphics_preferences_changed)
            def graphics_show_port_labels(self) -> bool:
                return bool(self._preference_bridge.graphics_show_port_labels)

            @_rendering_suite.pyqtProperty(bool, notify=graphics_preferences_changed)
            def graphics_node_shadow(self) -> bool:
                return True

            @_rendering_suite.pyqtProperty(int, notify=graphics_preferences_changed)
            def graphics_shadow_strength(self) -> int:
                return 70

            @_rendering_suite.pyqtProperty(int, notify=graphics_preferences_changed)
            def graphics_shadow_softness(self) -> int:
                return 50

            @_rendering_suite.pyqtProperty(int, notify=graphics_preferences_changed)
            def graphics_shadow_offset(self) -> int:
                return 4

            @_rendering_suite.pyqtProperty(str, notify=graphics_preferences_changed)
            def graphics_performance_mode(self) -> str:
                return "full_fidelity"

            @_rendering_suite.pyqtProperty(int, notify=graphics_preferences_changed)
            def graphics_graph_label_pixel_size(self) -> int:
                return int(self._preference_bridge.graphics_graph_label_pixel_size)

            @_rendering_suite.pyqtProperty("QVariant", notify=graphics_preferences_changed)
            def graphics_graph_node_icon_pixel_size_override(self) -> int | None:
                return self._preference_bridge.graphics_graph_node_icon_pixel_size_override

            @_rendering_suite.pyqtProperty(int, notify=graphics_preferences_changed)
            def graphics_node_title_icon_pixel_size(self) -> int:
                return int(self._preference_bridge.graphics_node_title_icon_pixel_size)

            @_rendering_suite.pyqtProperty("QVariantList", notify=scene_nodes_changed)
            def nodes_model(self) -> list[dict[str, object]]:
                return [dict(node_payload)]

            @_rendering_suite.pyqtProperty("QVariantList", constant=True)
            def backdrop_nodes_model(self) -> list[dict[str, object]]:
                return []

            @_rendering_suite.pyqtProperty("QVariantList", constant=True)
            def edges_model(self) -> list[dict[str, object]]:
                return []

            @_rendering_suite.pyqtProperty("QVariantMap", constant=True)
            def selected_node_lookup(self) -> dict[str, bool]:
                return {}

            @_rendering_suite.pyqtProperty("QVariantMap", constant=True)
            def workspace_scene_bounds_payload(self) -> dict[str, float]:
                return {}

            @_rendering_suite.pyqtProperty("QVariantMap", notify=failure_highlight_changed)
            def failed_node_lookup(self) -> dict[str, bool]:
                return {}

            @_rendering_suite.pyqtProperty(int, notify=failure_highlight_changed)
            def failed_node_revision(self) -> int:
                return 0

            @_rendering_suite.pyqtProperty(str, notify=failure_highlight_changed)
            def failed_node_title(self) -> str:
                return ""

            @_rendering_suite.pyqtProperty("QVariantMap", notify=node_execution_state_changed)
            def running_node_lookup(self) -> dict[str, bool]:
                return {node_id: True}

            @_rendering_suite.pyqtProperty("QVariantMap", notify=node_execution_state_changed)
            def completed_node_lookup(self) -> dict[str, bool]:
                return {}

            @_rendering_suite.pyqtProperty("QVariantMap", notify=node_execution_state_changed)
            def running_node_started_at_ms_lookup(self) -> dict[str, float]:
                return {node_id: started_at_ms}

            @_rendering_suite.pyqtProperty("QVariantMap", notify=node_execution_state_changed)
            def node_elapsed_ms_lookup(self) -> dict[str, float]:
                return {}

            @_rendering_suite.pyqtProperty(int, notify=node_execution_state_changed)
            def node_execution_revision(self) -> int:
                return 1

        self.canvas.deleteLater()
        self.app.processEvents()

        canvas_state_bridge = CanvasStateBridgeStub(preference_bridge, self.view)
        canvas_command_bridge = _rendering_suite.GraphCanvasCommandBridge(
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

        _rendering_suite.wait_for_condition_or_raise(
            lambda: len(_rendering_suite._named_child_items(self.canvas, "graphNodeCard")) == 1,
            timeout_ms=200,
            app=self.app,
            timeout_message="Timed out waiting for graph canvas typography host to appear.",
        )
        node_card = _rendering_suite._named_child_items(self.canvas, "graphNodeCard")[0]
        typography = node_card.findChild(_rendering_suite.QObject, "graphSharedTypography")
        title = node_card.findChild(_rendering_suite.QObject, "graphNodeTitle")
        elapsed_timer = node_card.findChild(_rendering_suite.QObject, "graphNodeElapsedTimer")
        input_labels = _rendering_suite._named_child_items(node_card, "graphNodeInputPortLabel")
        output_labels = _rendering_suite._named_child_items(node_card, "graphNodeOutputPortLabel")
        data_input_label = next(item for item in input_labels if str(item.property("text") or "") == "Message")
        exec_input_label = next(item for item in input_labels if str(item.property("text") or "") == "\u27A1")
        exec_output_label = next(item for item in output_labels if str(item.property("text") or "") == "\u27A1")

        self.assertIsNotNone(typography)
        self.assertIsNotNone(title)
        self.assertIsNotNone(elapsed_timer)
        if typography is None or title is None or elapsed_timer is None:
            self.fail("Expected graph canvas typography host chrome items to exist")

        _rendering_suite.wait_for_condition_or_raise(
            lambda: bool(elapsed_timer.property("visible")) and bool(elapsed_timer.property("liveElapsedActive")),
            timeout_ms=300,
            app=self.app,
            timeout_message="Timed out waiting for live elapsed footer to appear on the typography host.",
        )

        self.assertEqual(int(typography.property("nodeTitlePixelSize")), 12)
        self.assertEqual(title.property("font").pixelSize(), 12)
        self.assertEqual(title.property("font").weight(), int(typography.property("nodeTitleFontWeight")))
        self.assertEqual(data_input_label.property("font").pixelSize(), 10)
        self.assertEqual(data_input_label.property("font").weight(), int(typography.property("portLabelFontWeight")))
        self.assertEqual(exec_input_label.property("font").pixelSize(), 18)
        self.assertEqual(exec_input_label.property("font").weight(), int(typography.property("execArrowPortFontWeight")))
        self.assertEqual(exec_output_label.property("font").pixelSize(), 18)
        self.assertEqual(exec_output_label.property("font").weight(), int(typography.property("execArrowPortFontWeight")))
        self.assertEqual(elapsed_timer.property("font").pixelSize(), 10)

        preference_bridge.set_graphics_graph_label_pixel_size_value(16)
        _rendering_suite.wait_for_condition_or_raise(
            lambda: int(typography.property("nodeTitlePixelSize")) == 18
            and title.property("font").pixelSize() == 18
            and data_input_label.property("font").pixelSize() == 16
            and exec_input_label.property("font").pixelSize() == 24
            and exec_output_label.property("font").pixelSize() == 24
            and elapsed_timer.property("font").pixelSize() == 16,
            timeout_ms=300,
            app=self.app,
            timeout_message="Timed out waiting for graph typography preference updates to reach host chrome.",
        )

        self.assertEqual(title.property("font").weight(), int(typography.property("nodeTitleFontWeight")))
        self.assertEqual(data_input_label.property("font").weight(), int(typography.property("portLabelFontWeight")))
        self.assertEqual(exec_input_label.property("font").weight(), int(typography.property("execArrowPortFontWeight")))
        self.assertEqual(exec_output_label.property("font").weight(), int(typography.property("execArrowPortFontWeight")))

    def test_node_execution_visualization_graph_canvas_host_chrome_follows_bridge_state_priority(self) -> None:
        self._assert_persistent_node_elapsed_footer_rendering()

    def test_persistent_node_elapsed_footer_graph_canvas_host_renders_live_and_cached_timing_states(self) -> None:
        self._assert_persistent_node_elapsed_footer_rendering()


def build_graph_canvas_qml_preference_binding_subprocess_suite(
    loader: unittest.TestLoader,
) -> unittest.TestSuite:
    return build_graph_canvas_qml_preference_subprocess_suite(
        loader,
        GraphCanvasQmlPreferenceBindingTests,
    )


def load_tests(loader: unittest.TestLoader, _tests, _pattern):  # noqa: ANN001
    return build_graph_canvas_qml_preference_binding_subprocess_suite(loader)


__all__ = [
    "GraphCanvasQmlPreferenceBindingTests",
    "build_graph_canvas_qml_preference_binding_subprocess_suite",
]


if __name__ == "__main__":
    unittest.main()
