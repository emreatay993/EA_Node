from __future__ import annotations

import time
import unittest

from tests.graph_track_b import (
    qml_preference_performance_suite as _performance_suite,
    qml_preference_rendering_suite as _rendering_suite,
)
from tests.graph_track_b.qml_support import build_graph_canvas_qml_preference_subprocess_suite


class GraphCanvasQmlPreferenceBindingTests(
    _rendering_suite.GraphCanvasQmlPreferenceRenderingTests,
    _performance_suite.GraphCanvasQmlPreferencePerformanceTests,
):
    """Stable regression entrypoint for packetized Track-B QML preference coverage."""

    __test__ = True

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
