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
    def _mock_single_run_report(self) -> dict:
        return {
            "generated_at_utc": "2026-03-21T00:00:00+00:00",
            "config": {
                "performance_mode": "full_fidelity",
                "scenario": "synthetic_exec",
            },
            "environment": {
                "hostname": "test-host",
                "machine": "x86_64",
                "qt_qpa_platform": "windows",
                "qt_quick_backend": "",
                "qsg_rhi_backend": "",
            },
            "metrics": {
                "project_graph_load_ms": {"summary": {"p95": 10.0}},
                "pan_interaction_ms": {"summary": {"p95": 20.0}},
                "zoom_interaction_ms": {"summary": {"p95": 30.0}},
                "pan_zoom_combined_ms": {"summary": {"p95": 40.0}},
                "node_drag_control_ms": {"summary": {"p95": 50.0}},
            },
        }

    def _assert_heavy_media_scenario(self, performance_mode: str) -> None:
        report = run_benchmark(
            BenchmarkConfig(
                synthetic_graph=SyntheticGraphConfig(node_count=18, edge_count=30, seed=17),
                load_iterations=1,
                interaction_samples=1,
                interaction_warmup_samples=0,
                performance_mode=performance_mode,
                scenario="heavy_media",
            )
        )

        config = report["config"]
        interaction_benchmark = report["interaction_benchmark"]
        scenario_details = config["scenario_details"]
        node_mix = scenario_details["node_mix"]

        self.assertEqual(config["performance_mode"], performance_mode)
        self.assertEqual(config["scenario"], "heavy_media")
        self.assertEqual(scenario_details["fixture_strategy"], "generated_local_media_reuse")
        self.assertGreater(node_mix["image_panel_nodes"], 0)
        self.assertGreater(node_mix["pdf_panel_nodes"], 0)
        self.assertEqual(
            node_mix["execution_nodes"] + node_mix["image_panel_nodes"] + node_mix["pdf_panel_nodes"],
            18,
        )
        self.assertEqual(
            scenario_details["expected_media_surface_count"],
            node_mix["image_panel_nodes"] + node_mix["pdf_panel_nodes"],
        )
        self.assertEqual(interaction_benchmark["performance_mode"], performance_mode)
        self.assertEqual(interaction_benchmark["resolved_graphics_performance_mode"], performance_mode)
        self.assertEqual(interaction_benchmark["scenario"], "heavy_media")
        self.assertEqual(
            interaction_benchmark["media_surface_count"],
            scenario_details["expected_media_surface_count"],
        )
        self.assertTrue(interaction_benchmark["uses_actual_canvas_render_path"])

    def test_public_telemetry_import_path_remains_a_compatibility_surface(self) -> None:
        self.assertIs(telemetry_performance_harness.run_benchmark, ui_performance_harness.run_benchmark)
        self.assertEqual(
            telemetry_performance_harness.run_benchmark.__module__,
            "ea_node_editor.ui.perf.performance_harness",
        )

    def test_ui_perf_harness_keeps_extracted_interaction_and_baseline_helpers(self) -> None:
        harness_text = Path(ui_performance_harness.__file__).read_text(encoding="utf-8")

        self.assertIn("class _InteractionBenchmarkSamples:", harness_text)
        self.assertIn("def _baseline_series_run(", harness_text)
        self.assertIn("def _baseline_metric_series(", harness_text)
        self.assertIn("def _baseline_series_payload(", harness_text)

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
                interaction_warmup_samples=1,
            )
        )

        load_samples = report["metrics"]["project_graph_load_ms"]["samples"]
        pan_samples = report["metrics"]["pan_interaction_ms"]["samples"]
        zoom_samples = report["metrics"]["zoom_interaction_ms"]["samples"]
        combined_samples = report["metrics"]["pan_zoom_combined_ms"]["samples"]
        node_drag_control_samples = report["metrics"]["node_drag_control_ms"]["samples"]
        interaction_benchmark = report["interaction_benchmark"]
        phase_timings = report["phase_timings_ms"]

        self.assertEqual(len(load_samples), 2)
        self.assertEqual(len(pan_samples), 8)
        self.assertEqual(len(zoom_samples), 8)
        self.assertEqual(len(combined_samples), 8)
        self.assertEqual(len(node_drag_control_samples), 8)
        self.assertEqual(report["config"]["interaction_warmup_samples"], 1)
        self.assertEqual(len(phase_timings["project_graph_load_ms"]["samples"]), 2)
        self.assertEqual(len(phase_timings["canvas_setup_ms"]["samples"]), 1)
        self.assertEqual(len(phase_timings["canvas_warmup_ms"]["samples"]), 1)
        self.assertEqual(len(phase_timings["pan_interaction_ms"]["samples"]), 8)
        self.assertEqual(len(phase_timings["zoom_interaction_ms"]["samples"]), 8)
        self.assertEqual(len(phase_timings["node_drag_control_ms"]["samples"]), 8)

        self.assertGreaterEqual(report["metrics"]["project_graph_load_ms"]["summary"]["p95"], 0.0)
        self.assertGreaterEqual(report["metrics"]["pan_zoom_combined_ms"]["summary"]["p95"], 0.0)
        self.assertGreaterEqual(report["metrics"]["node_drag_control_ms"]["summary"]["p95"], 0.0)
        self.assertEqual(report["config"]["performance_mode"], "full_fidelity")
        self.assertEqual(report["config"]["scenario"], "synthetic_exec")
        self.assertEqual(report["config"]["scenario_details"]["node_mix"]["image_panel_nodes"], 0)
        self.assertEqual(report["config"]["scenario_details"]["node_mix"]["pdf_panel_nodes"], 0)
        self.assertEqual(interaction_benchmark["kind"], "graph_canvas_qml")
        self.assertEqual(
            interaction_benchmark["render_path"],
            "ea_node_editor/ui_qml/components/GraphCanvas.qml",
        )
        self.assertEqual(interaction_benchmark["viewport"], {"width": 1280, "height": 720})
        self.assertTrue(interaction_benchmark["uses_actual_canvas_render_path"])
        self.assertTrue(interaction_benchmark["steady_state_canvas_host_reused"])
        self.assertEqual(interaction_benchmark["warmup_samples"], 1)
        self.assertEqual(interaction_benchmark["performance_mode"], "full_fidelity")
        self.assertEqual(interaction_benchmark["resolved_graphics_performance_mode"], "full_fidelity")
        self.assertEqual(interaction_benchmark["scenario"], "synthetic_exec")
        self.assertEqual(interaction_benchmark["media_surface_count"], 0)
        self.assertIn("grabWindow", interaction_benchmark["measurement_driver"])

    def test_benchmark_runner_emits_baseline_series_with_machine_metadata(self) -> None:
        report = run_benchmark(
            BenchmarkConfig(
                synthetic_graph=SyntheticGraphConfig(node_count=60, edge_count=160, seed=11),
                load_iterations=1,
                interaction_samples=4,
                interaction_warmup_samples=1,
            ),
            baseline_runs=2,
            baseline_mode="interactive",
            baseline_tag="unit_test",
        )

        baseline_series = report["baseline_series"]
        self.assertEqual(baseline_series["mode"], "interactive")
        self.assertEqual(baseline_series["tag"], "unit_test")
        self.assertEqual(baseline_series["performance_mode"], "full_fidelity")
        self.assertEqual(baseline_series["scenario"], "synthetic_exec")
        self.assertEqual(baseline_series["run_count"], 2)
        self.assertEqual(len(baseline_series["runs"]), 2)

        first_run = baseline_series["runs"][0]
        self.assertIn("run_id", first_run)
        self.assertIn("generated_at_utc", first_run)
        self.assertEqual(first_run["performance_mode"], "full_fidelity")
        self.assertEqual(first_run["scenario"], "synthetic_exec")
        self.assertIn("environment", first_run)
        self.assertIn("metrics", first_run)
        self.assertIn("hostname", first_run["environment"])
        self.assertIn("machine", first_run["environment"])
        self.assertIn("qt_quick_backend", first_run["environment"])
        self.assertIn("qsg_rhi_backend", first_run["environment"])
        self.assertIn("load_p95_ms", first_run["metrics"])
        self.assertIn("pan_p95_ms", first_run["metrics"])
        self.assertIn("zoom_p95_ms", first_run["metrics"])
        self.assertIn("pan_zoom_p95_ms", first_run["metrics"])
        self.assertIn("node_drag_control_p95_ms", first_run["metrics"])

        metric_series = baseline_series["metric_series"]
        self.assertEqual(len(metric_series["load_p95_ms"]), 2)
        self.assertEqual(len(metric_series["pan_p95_ms"]), 2)
        self.assertEqual(len(metric_series["zoom_p95_ms"]), 2)
        self.assertEqual(len(metric_series["pan_zoom_p95_ms"]), 2)
        self.assertEqual(len(metric_series["node_drag_control_p95_ms"]), 2)

        variance_eval = baseline_series["variance_eval"]
        self.assertIn("load_p95_ms", variance_eval)
        self.assertIn("pan_p95_ms", variance_eval)
        self.assertIn("zoom_p95_ms", variance_eval)
        self.assertIn("pan_zoom_p95_ms", variance_eval)
        self.assertIn("node_drag_control_p95_ms", variance_eval)
        self.assertIn("pass", variance_eval["load_p95_ms"])
        self.assertIn("details", variance_eval["pan_zoom_p95_ms"])

    def test_windows_baseline_series_uses_subprocess_runner(self) -> None:
        sample_report = self._mock_single_run_report()
        with patch.dict(ui_performance_harness.os.environ, {"QT_QPA_PLATFORM": "windows"}, clear=False):
            with patch.object(
                ui_performance_harness,
                "_run_single_benchmark_subprocess",
                side_effect=[sample_report, sample_report],
            ) as subprocess_runner:
                with patch.object(ui_performance_harness, "_run_single_benchmark") as in_process_runner:
                    report = run_benchmark(
                        BenchmarkConfig(
                            synthetic_graph=SyntheticGraphConfig(node_count=60, edge_count=160, seed=11),
                            load_iterations=1,
                            interaction_samples=4,
                            interaction_warmup_samples=1,
                        ),
                        baseline_runs=2,
                        baseline_mode="interactive",
                        baseline_tag="unit_test",
                    )

        self.assertEqual(subprocess_runner.call_count, 2)
        in_process_runner.assert_not_called()
        self.assertEqual(report["baseline_series"]["run_count"], 2)
        self.assertEqual(len(report["baseline_series"]["runs"]), 2)

    def test_heavy_media_scenario_records_mode_and_media_mix(self) -> None:
        self._assert_heavy_media_scenario("max_performance")

    def test_heavy_media_full_fidelity_records_all_media_surfaces(self) -> None:
        self._assert_heavy_media_scenario("full_fidelity")

    def test_resolve_baseline_mode_auto(self) -> None:
        self.assertEqual(_resolve_baseline_mode("auto", "offscreen"), "offscreen")
        self.assertEqual(_resolve_baseline_mode("auto", "windows"), "interactive")
        self.assertEqual(_resolve_baseline_mode("interactive", "offscreen"), "interactive")
        self.assertEqual(_resolve_baseline_mode("offscreen", "windows"), "offscreen")


if __name__ == "__main__":
    unittest.main()
