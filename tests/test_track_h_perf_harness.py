from __future__ import annotations

import runpy
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from ea_node_editor.telemetry import performance_harness as telemetry_performance_harness
from ea_node_editor.telemetry.performance_harness import (
    BenchmarkConfig,
    SyntheticGraphConfig,
    _resolve_baseline_mode,
    generate_synthetic_project,
    run_benchmark,
)
from ea_node_editor.ui.perf import performance_harness as ui_performance_harness


class TrackHPerformanceHarnessTests(unittest.TestCase):
    def test_public_telemetry_import_path_remains_a_compatibility_surface(self) -> None:
        self.assertIs(telemetry_performance_harness.run_benchmark, ui_performance_harness.run_benchmark)
        self.assertEqual(
            telemetry_performance_harness.run_benchmark.__module__,
            "ea_node_editor.ui.perf.performance_harness",
        )

    def test_public_telemetry_module_execution_delegates_to_ui_main(self) -> None:
        delegated_main = Mock(return_value=23)

        with patch.object(ui_performance_harness, "main", delegated_main):
            with self.assertRaises(SystemExit) as exit_info:
                runpy.run_path(str(Path(telemetry_performance_harness.__file__)), run_name="__main__")

        delegated_main.assert_called_once_with()
        self.assertEqual(exit_info.exception.code, 23)

    def test_generate_synthetic_project_hits_target_scale(self) -> None:
        project = generate_synthetic_project(SyntheticGraphConfig(node_count=1000, edge_count=5000, seed=42))
        workspace = project.workspaces[project.active_workspace_id]

        self.assertEqual(len(workspace.nodes), 1000)
        self.assertEqual(len(workspace.edges), 5000)

    def test_benchmark_runner_reports_expected_metric_shapes(self) -> None:
        report = run_benchmark(
            BenchmarkConfig(
                synthetic_graph=SyntheticGraphConfig(node_count=80, edge_count=220, seed=7),
                load_iterations=2,
                interaction_samples=8,
            )
        )

        load_samples = report["metrics"]["project_graph_load_ms"]["samples"]
        pan_samples = report["metrics"]["pan_interaction_ms"]["samples"]
        zoom_samples = report["metrics"]["zoom_interaction_ms"]["samples"]
        combined_samples = report["metrics"]["pan_zoom_combined_ms"]["samples"]
        interaction_benchmark = report["interaction_benchmark"]

        self.assertEqual(len(load_samples), 2)
        self.assertEqual(len(pan_samples), 8)
        self.assertEqual(len(zoom_samples), 8)
        self.assertEqual(len(combined_samples), 8)

        self.assertGreaterEqual(report["metrics"]["project_graph_load_ms"]["summary"]["p95"], 0.0)
        self.assertGreaterEqual(report["metrics"]["pan_zoom_combined_ms"]["summary"]["p95"], 0.0)
        self.assertEqual(interaction_benchmark["kind"], "graph_canvas_qml")
        self.assertEqual(
            interaction_benchmark["render_path"],
            "ea_node_editor/ui_qml/components/GraphCanvas.qml",
        )
        self.assertEqual(interaction_benchmark["viewport"], {"width": 1280, "height": 720})
        self.assertTrue(interaction_benchmark["uses_actual_canvas_render_path"])
        self.assertIn("grabWindow", interaction_benchmark["measurement_driver"])

    def test_benchmark_runner_emits_baseline_series_with_machine_metadata(self) -> None:
        report = run_benchmark(
            BenchmarkConfig(
                synthetic_graph=SyntheticGraphConfig(node_count=60, edge_count=160, seed=11),
                load_iterations=1,
                interaction_samples=8,
            ),
            baseline_runs=2,
            baseline_mode="interactive",
            baseline_tag="unit_test",
        )

        baseline_series = report["baseline_series"]
        self.assertEqual(baseline_series["mode"], "interactive")
        self.assertEqual(baseline_series["tag"], "unit_test")
        self.assertEqual(baseline_series["run_count"], 2)
        self.assertEqual(len(baseline_series["runs"]), 2)

        first_run = baseline_series["runs"][0]
        self.assertIn("run_id", first_run)
        self.assertIn("generated_at_utc", first_run)
        self.assertIn("environment", first_run)
        self.assertIn("metrics", first_run)
        self.assertIn("hostname", first_run["environment"])
        self.assertIn("machine", first_run["environment"])
        self.assertIn("qt_quick_backend", first_run["environment"])
        self.assertIn("qsg_rhi_backend", first_run["environment"])
        self.assertIn("load_p95_ms", first_run["metrics"])
        self.assertIn("pan_zoom_p95_ms", first_run["metrics"])

        variance_eval = baseline_series["variance_eval"]
        self.assertIn("load_p95_ms", variance_eval)
        self.assertIn("pan_zoom_p95_ms", variance_eval)
        self.assertIn("pass", variance_eval["load_p95_ms"])
        self.assertIn("details", variance_eval["pan_zoom_p95_ms"])

    def test_resolve_baseline_mode_auto(self) -> None:
        self.assertEqual(_resolve_baseline_mode("auto", "offscreen"), "offscreen")
        self.assertEqual(_resolve_baseline_mode("auto", "windows"), "interactive")
        self.assertEqual(_resolve_baseline_mode("interactive", "offscreen"), "interactive")
        self.assertEqual(_resolve_baseline_mode("offscreen", "windows"), "offscreen")


if __name__ == "__main__":
    unittest.main()
