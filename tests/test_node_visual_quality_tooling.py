from __future__ import annotations

import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ea_node_editor.ui.perf.node_visual_quality import (
    TARGET_IDS, WORKSPACE_ID, SettingsAnimationEvidence, SettingsAnimationMonitor, build_visual_quality_project,
    capture_viewport_size, validate_capture_frame, validate_control_renderer, wait_for_changed_render,
)


class VisualQualityToolingTests(unittest.TestCase):
    def test_animation_monitor_retains_progress_and_stop_within_one_event_drain(self):
        class Signal:
            def __init__(self):
                self.callbacks = []
            def connect(self, callback):
                self.callbacks.append(callback)
            def disconnect(self, callback):
                self.callbacks.remove(callback)
            def emit(self):
                for callback in self.callbacks:
                    callback()

        state = {"running": False, "remaining": 0, "height": 180, "time": 1.0}
        running_changed, remaining_changed = Signal(), Signal()
        card = SimpleNamespace(
            settingsGroupAnimationRunningChanged=running_changed,
            _settingsGroupAnimationRemainingChanged=remaining_changed,
            property=lambda key: state["running" if key == "settingsGroupAnimationRunning" else "remaining"],
            width=lambda: 300, height=lambda: state["height"],
        )
        host = SimpleNamespace(frame_render_timestamp_index=lambda: 2)
        monitor = SettingsAnimationMonitor(card, host)
        evidence = monitor.start(1.0)
        with patch("ea_node_editor.ui.perf.node_visual_quality.time.perf_counter", side_effect=lambda: state["time"]):
            state.update(running=True, remaining=1, time=1.01)
            running_changed.emit()
            # Both notifications occur before processEvents() returns to the poller.
            state.update(remaining=0, height=500, time=1.18)
            remaining_changed.emit()
            state.update(running=False, time=1.19)
            running_changed.emit()
            monitor.poll()
        result = evidence.result([1.02, 1.06, 1.17, 1.21])
        self.assertEqual([sample["remaining"] for sample in result["progress_samples"]], [1, 0])
        self.assertEqual(result["active_frame_count"], 3)
        self.assertTrue(result["observed_completion"])
        monitor.close()
        self.assertEqual(running_changed.callbacks, [])
        self.assertEqual(remaining_changed.callbacks, [])

    def test_benchmark_viewport_defaults_unchanged_and_capture_override_is_explicit(self):
        from ea_node_editor.ui.perf.performance_harness import _resolve_canvas_viewport_size
        self.assertEqual(_resolve_canvas_viewport_size(), (1280, 720))
        self.assertEqual(_resolve_canvas_viewport_size((800, 450)), (800, 450))
        with self.assertRaises(ValueError):
            _resolve_canvas_viewport_size((0, 450))

    def test_capture_viewport_fits_available_logical_screen_with_margins(self):
        self.assertEqual(capture_viewport_size(1920, 1040), (1280, 720))
        width, height = capture_viewport_size(960, 520)
        self.assertLessEqual(width, 960 - 64)
        self.assertLessEqual(height, 520 - 64)
        self.assertLessEqual(abs(width / height - 16 / 9), .005)

    def test_empty_and_flat_capture_frames_are_rejected(self):
        from PyQt6.QtGui import QColor, QImage
        with self.assertRaisesRegex(RuntimeError, "Empty capture"):
            validate_capture_frame(QImage(), [])
        frame = QImage(8, 8, QImage.Format.Format_RGBA8888)
        frame.fill(QColor(30, 30, 30))
        with self.assertRaisesRegex(RuntimeError, "Uniform capture"):
            validate_capture_frame(frame, [])
        frame.setPixelColor(3, 4, QColor(100, 150, 200))
        self.assertTrue(validate_capture_frame(frame, ["ordinary QML diagnostic"])["nonuniform_pixels"])
        with self.assertRaisesRegex(RuntimeError, "Graphics device failure"):
            validate_capture_frame(frame, ["Device loss detected in Present()"])
        with self.assertRaisesRegex(RuntimeError, "Graphics device failure"):
            validate_capture_frame(frame, ["Failed to create readback staging texture COM 0x887a0005"])

    def test_fixture_has_stable_production_nodes_and_round_trips(self):
        from ea_node_editor.nodes.bootstrap import build_default_registry
        from ea_node_editor.persistence.serializer import JsonProjectSerializer

        registry = build_default_registry()
        serializer = JsonProjectSerializer(registry)
        first = serializer.to_document(build_visual_quality_project(node_count=200))
        second = serializer.to_document(build_visual_quality_project(node_count=200))
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        restored = serializer.from_document(first)
        workspace = restored.workspaces[WORKSPACE_ID]
        self.assertEqual(len(workspace.nodes), 200)
        self.assertTrue(set(TARGET_IDS.values()).issubset(workspace.nodes))
        for node in workspace.nodes.values():
            spec = registry.get_spec(node.type_id)
            self.assertTrue(set(node.expanded_settings_group_ids).issubset({g.group_id for g in spec.settings_groups}))
        self.assertEqual(workspace.nodes[TARGET_IDS["switch"]].properties["value"], True)
        self.assertEqual(workspace.nodes[TARGET_IDS["switch_off"]].properties["value"], False)
        self.assertEqual(len(workspace.edges), 2)

    def _host(self, states):
        state = {"iteration": -1, "clock": 1.0, "updates": 0}
        frames = []
        def process():
            state["iteration"] += 1
            state["clock"] += 0.01
            frames.append(state["clock"])
        def update():
            state["updates"] += 1
        return SimpleNamespace(
            app=SimpleNamespace(processEvents=process), widget=None,
            window=SimpleNamespace(update=update), _frame_render_timestamps=frames,
            frame_render_timestamp_index=lambda: len(frames),
        ), state, lambda: states[min(state["iteration"], len(states)-1)]

    def test_render_before_state_change_cannot_complete_sample(self):
        host, state, changed = self._host([False, False, True, True])
        with patch("ea_node_editor.ui.perf.node_visual_quality.time.perf_counter", side_effect=lambda: state["clock"]), \
             patch("ea_node_editor.ui.perf.node_visual_quality.time.sleep"):
            result = wait_for_changed_render(host, changed=changed, started=1.0)
        self.assertEqual(result["state_observed_frame"], 3)
        self.assertEqual(result["completion_frame"], 4)
        self.assertAlmostEqual(result["elapsed_ms"], 40)
        self.assertEqual(state["updates"], 1)

    def test_reverted_state_requires_new_observation_and_later_frame(self):
        host, state, changed = self._host([True, False, True, True])
        with patch("ea_node_editor.ui.perf.node_visual_quality.time.perf_counter", side_effect=lambda: state["clock"]), \
             patch("ea_node_editor.ui.perf.node_visual_quality.time.sleep"):
            result = wait_for_changed_render(host, changed=changed, started=1.0)
        self.assertEqual(result["state_observed_frame"], 3)
        self.assertEqual(result["completion_frame"], 4)

    def test_no_state_change_fails_even_while_frames_arrive(self):
        host, state, changed = self._host([False])
        with patch("ea_node_editor.ui.perf.node_visual_quality.time.perf_counter", side_effect=lambda: state["clock"]), \
             patch("ea_node_editor.ui.perf.node_visual_quality.time.sleep"):
            with self.assertRaisesRegex(RuntimeError, "state did not change"):
                wait_for_changed_render(host, changed=changed, started=1.0, timeout_ms=30)

    def test_cli_opt_in_preserves_default_behavior(self):
        from ea_node_editor.ui.perf.performance_harness import BenchmarkConfig, _parse_args
        self.assertFalse(BenchmarkConfig().control_interactions)
        self.assertFalse(_parse_args([]).control_interactions)
        self.assertTrue(_parse_args(["--control-interactions"]).control_interactions)

    def test_absent_animation_is_not_a_zero_time_success(self):
        animation = SettingsAnimationEvidence(1.0)
        animation.observe(running=False, remaining=0, width=300, height=180,
                          timestamp=1.05, frame_index=1)
        with self.assertRaisesRegex(RuntimeError, "absent or disabled"):
            animation.result([1.01, 1.04])

    def test_incomplete_animation_fails_even_with_frames_and_progress(self):
        animation = SettingsAnimationEvidence(1.0)
        for timestamp, remaining, height in ((1.01, 1, 180), (1.1, .4, 350)):
            animation.observe(running=True, remaining=remaining, width=300, height=height,
                              timestamp=timestamp, frame_index=2)
        with self.assertRaisesRegex(RuntimeError, "did not complete"):
            animation.result([1.02, 1.05, 1.09])

    def test_completed_animation_reports_only_active_frame_intervals(self):
        animation = SettingsAnimationEvidence(1.0)
        animation.observe(running=True, remaining=1, width=300, height=180,
                          timestamp=1.01, frame_index=1)
        animation.observe(running=True, remaining=.3, width=300, height=400,
                          timestamp=1.12, frame_index=3)
        animation.observe(running=False, remaining=0, width=300, height=500,
                          timestamp=1.19, frame_index=4)
        result = animation.result([1.005, 1.02, 1.06, 1.11, 1.18, 1.21])
        self.assertEqual(result["raw_frame_count"], 6)
        self.assertEqual(result["active_frame_count"], 4)
        self.assertAlmostEqual(result["completion_duration_ms"], 190)
        self.assertEqual(len(result["frame_intervals_ms"]), 3)
        self.assertAlmostEqual(result["frame_intervals_ms"][-1], 70)
        self.assertTrue(result["observed_completion"])

    def test_completed_animation_without_active_frames_fails(self):
        animation = SettingsAnimationEvidence(1.0)
        animation.observe(running=True, remaining=1, width=300, height=180,
                          timestamp=1.01, frame_index=1)
        animation.observe(running=True, remaining=.3, width=300, height=400,
                          timestamp=1.12, frame_index=1)
        animation.observe(running=False, remaining=0, width=300, height=500,
                          timestamp=1.19, frame_index=1)
        with self.assertRaisesRegex(RuntimeError, "fewer than two active"):
            animation.result([1.005, 1.21])

    def test_completed_animation_without_progress_fails(self):
        animation = SettingsAnimationEvidence(1.0)
        animation.observe(running=True, remaining=1, width=300, height=180,
                          timestamp=1.01, frame_index=1)
        animation.observe(running=False, remaining=0, width=300, height=500,
                          timestamp=1.19, frame_index=4)
        with self.assertRaisesRegex(RuntimeError, "progress was not observed"):
            animation.result([1.02, 1.06, 1.11, 1.18])

    def test_nondisplay_renderer_is_not_acceptance_evidence(self):
        with self.assertRaisesRegex(RuntimeError, "not acceptance evidence"):
            validate_control_renderer({"qt_qpa_platform": "offscreen", "graphics_api": "Software"})
        validate_control_renderer({"qt_qpa_platform": "windows", "graphics_api": "Direct3D11Rhi"})


if __name__ == "__main__":
    unittest.main()
