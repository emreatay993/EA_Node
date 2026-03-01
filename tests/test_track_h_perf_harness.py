from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from ea_node_editor.telemetry.performance_harness import (
    BenchmarkConfig,
    SyntheticGraphConfig,
    generate_synthetic_project,
    run_benchmark,
)


class TrackHPerformanceHarnessTests(unittest.TestCase):
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
                interaction_samples=24,
            )
        )

        load_samples = report["metrics"]["project_graph_load_ms"]["samples"]
        pan_samples = report["metrics"]["pan_interaction_ms"]["samples"]
        zoom_samples = report["metrics"]["zoom_interaction_ms"]["samples"]
        combined_samples = report["metrics"]["pan_zoom_combined_ms"]["samples"]

        self.assertEqual(len(load_samples), 2)
        self.assertEqual(len(pan_samples), 24)
        self.assertEqual(len(zoom_samples), 24)
        self.assertEqual(len(combined_samples), 24)

        self.assertGreaterEqual(report["metrics"]["project_graph_load_ms"]["summary"]["p95"], 0.0)
        self.assertGreaterEqual(report["metrics"]["pan_zoom_combined_ms"]["summary"]["p95"], 0.0)


if __name__ == "__main__":
    unittest.main()

