from __future__ import annotations

import argparse
import json
import os
import platform
import random
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Force a deterministic non-interactive platform plugin for headless runs.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from ea_node_editor.graph.model import EdgeInstance, GraphModel, NodeInstance, ProjectData, ViewState, WorkspaceData
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.persistence.serializer import JsonProjectSerializer
from ea_node_editor.ui_qml.graph_scene_bridge import GraphSceneBridge
from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge


@dataclass(slots=True, frozen=True)
class SyntheticGraphConfig:
    node_count: int = 1000
    edge_count: int = 5000
    seed: int = 1337


@dataclass(slots=True, frozen=True)
class BenchmarkConfig:
    synthetic_graph: SyntheticGraphConfig = SyntheticGraphConfig()
    load_iterations: int = 5
    interaction_samples: int = 200
    interaction_zoom_min: float = 0.5
    interaction_zoom_max: float = 2.0


_BASELINE_VARIANCE_THRESHOLDS = {
    "load_p95_ms": {
        "max_cv": 0.25,
        "max_range_ms": 500.0,
    },
    "pan_zoom_p95_ms": {
        "max_cv": 0.20,
        "max_range_ms": 8.0,
    },
}


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * (percentile / 100.0)
    lower_index = int(rank)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    lower_value = ordered[lower_index]
    upper_value = ordered[upper_index]
    fraction = rank - lower_index
    return float(lower_value + (upper_value - lower_value) * fraction)


def _metric_summary_ms(samples: list[float]) -> dict[str, float]:
    if not samples:
        return {"min": 0.0, "max": 0.0, "mean": 0.0, "p50": 0.0, "p95": 0.0}
    return {
        "min": float(min(samples)),
        "max": float(max(samples)),
        "mean": float(statistics.fmean(samples)),
        "p50": _percentile(samples, 50.0),
        "p95": _percentile(samples, 95.0),
    }


def _coefficient_of_variation(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = statistics.fmean(values)
    if mean == 0.0:
        return 0.0
    return float(statistics.pstdev(values) / mean)


def _resolve_baseline_mode(requested_mode: str, qt_qpa_platform: str) -> str:
    mode = requested_mode.strip().lower()
    if mode in {"interactive", "offscreen"}:
        return mode
    if mode != "auto":
        return "offscreen"
    normalized_platform = qt_qpa_platform.strip().lower()
    if normalized_platform in {"", "offscreen"}:
        return "offscreen"
    return "interactive"


def _collect_environment_snapshot() -> dict[str, Any]:
    uname = platform.uname()
    return {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "qt_qpa_platform": os.environ.get("QT_QPA_PLATFORM", ""),
        "cpu_count": os.cpu_count(),
        "hostname": uname.node,
        "system": uname.system,
        "release": uname.release,
        "machine": uname.machine,
        "processor": uname.processor,
    }


def generate_synthetic_project(config: SyntheticGraphConfig) -> ProjectData:
    if config.node_count < 3:
        raise ValueError("node_count must be at least 3")
    if config.edge_count < config.node_count - 1:
        raise ValueError("edge_count must be at least node_count - 1 to keep baseline chain connectivity")

    project = ProjectData(project_id="proj_perf_h", name="track_h_perf")
    workspace_id = "ws_perf_h"
    workspace = WorkspaceData(workspace_id=workspace_id, name="Perf Workspace")
    workspace.views["view_perf_h"] = ViewState(
        view_id="view_perf_h",
        name="V1",
        zoom=1.0,
        pan_x=0.0,
        pan_y=0.0,
    )
    workspace.active_view_id = "view_perf_h"

    node_ids: list[str] = []
    max_cols = 40
    spacing_x = 220.0
    spacing_y = 140.0
    for index in range(config.node_count):
        node_id = f"node_{index:04d}"
        node_ids.append(node_id)
        if index == 0:
            type_id = "core.start"
            title = "Start"
        elif index == config.node_count - 1:
            type_id = "core.end"
            title = "End"
        else:
            type_id = "core.logger"
            title = f"Logger {index}"

        col = index % max_cols
        row = index // max_cols
        workspace.nodes[node_id] = NodeInstance(
            node_id=node_id,
            type_id=type_id,
            title=title,
            x=col * spacing_x,
            y=row * spacing_y,
            properties={},
            exposed_ports={},
        )

    edge_connections: list[tuple[str, str, str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()

    for index in range(config.node_count - 1):
        connection = (node_ids[index], "exec_out", node_ids[index + 1], "exec_in")
        edge_connections.append(connection)
        seen.add(connection)

    source_candidates = node_ids[:-1]
    target_candidates = node_ids[1:]
    generator = random.Random(config.seed)

    while len(edge_connections) < config.edge_count:
        source_id = generator.choice(source_candidates)
        target_id = generator.choice(target_candidates)
        if source_id == target_id:
            continue
        connection = (source_id, "exec_out", target_id, "exec_in")
        if connection in seen:
            continue
        edge_connections.append(connection)
        seen.add(connection)

    for index, (source_id, source_port, target_id, target_port) in enumerate(edge_connections):
        edge_id = f"edge_{index:05d}"
        workspace.edges[edge_id] = EdgeInstance(
            edge_id=edge_id,
            source_node_id=source_id,
            source_port_key=source_port,
            target_node_id=target_id,
            target_port_key=target_port,
        )

    project.workspaces[workspace_id] = workspace
    project.active_workspace_id = workspace_id
    project.metadata["workspace_order"] = [workspace_id]
    return project


def _bind_scene_for_workspace(
    *,
    app: QApplication,
    model: GraphModel,
    workspace_id: str,
) -> tuple[GraphSceneBridge, ViewportBridge]:
    registry = build_default_registry()
    scene = GraphSceneBridge()
    view = ViewportBridge()
    view.set_viewport_size(1280.0, 720.0)
    scene.set_workspace(model, registry, workspace_id)
    app.processEvents()
    return scene, view


def _workspace_bounds(workspace: WorkspaceData) -> tuple[float, float, float, float]:
    if not workspace.nodes:
        return -5000.0, 5000.0, -5000.0, 5000.0
    xs = [float(node.x) for node in workspace.nodes.values()]
    ys = [float(node.y) for node in workspace.nodes.values()]
    margin_x = 800.0
    margin_y = 500.0
    return (
        min(xs) - margin_x,
        max(xs) + margin_x,
        min(ys) - margin_y,
        max(ys) + margin_y,
    )


def benchmark_load_times_ms(*, doc: dict[str, Any], workspace_id: str, iterations: int) -> list[float]:
    app = QApplication.instance() or QApplication([])
    serializer = JsonProjectSerializer(build_default_registry())
    samples: list[float] = []

    for _ in range(iterations):
        started = time.perf_counter()
        project = serializer.from_document(doc)
        model = GraphModel(project)
        scene, view = _bind_scene_for_workspace(app=app, model=model, workspace_id=workspace_id)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        samples.append(elapsed_ms)
        view.deleteLater()
        scene.deleteLater()
        app.processEvents()

    return samples


def benchmark_pan_zoom_ms(
    *,
    doc: dict[str, Any],
    workspace_id: str,
    samples: int,
    seed: int,
    zoom_min: float,
    zoom_max: float,
) -> dict[str, list[float]]:
    if samples <= 0:
        raise ValueError("samples must be > 0")
    app = QApplication.instance() or QApplication([])
    serializer = JsonProjectSerializer(build_default_registry())
    project = serializer.from_document(doc)
    model = GraphModel(project)
    scene, view = _bind_scene_for_workspace(app=app, model=model, workspace_id=workspace_id)
    workspace = model.project.workspaces[workspace_id]

    random_gen = random.Random(seed)
    left, right, top, bottom = _workspace_bounds(workspace)
    pan_samples_ms: list[float] = []
    zoom_samples_ms: list[float] = []

    for index in range(samples):
        current_center = view.mapToScene(view.viewport().rect().center())
        pan_x = max(
            left,
            min(right, current_center.x() + random_gen.uniform(-180.0, 180.0)),
        )
        pan_y = max(
            top,
            min(bottom, current_center.y() + random_gen.uniform(-120.0, 120.0)),
        )
        started = time.perf_counter()
        view.centerOn(pan_x, pan_y)
        app.processEvents()
        pan_samples_ms.append((time.perf_counter() - started) * 1000.0)

        zoom_step = 1.05 if index % 2 == 0 else (1.0 / 1.05)
        zoom = max(zoom_min, min(zoom_max, view.zoom * zoom_step))
        started = time.perf_counter()
        view.set_zoom(zoom)
        app.processEvents()
        zoom_samples_ms.append((time.perf_counter() - started) * 1000.0)

    view.deleteLater()
    scene.deleteLater()
    app.processEvents()

    combined = [pan + zoom for pan, zoom in zip(pan_samples_ms, zoom_samples_ms, strict=True)]
    return {
        "pan_ms": pan_samples_ms,
        "zoom_ms": zoom_samples_ms,
        "combined_ms": combined,
    }


def _run_single_benchmark(config: BenchmarkConfig) -> dict[str, Any]:
    project = generate_synthetic_project(config.synthetic_graph)
    serializer = JsonProjectSerializer(build_default_registry())
    doc = serializer.to_document(project)
    workspace_id = project.active_workspace_id

    load_samples = benchmark_load_times_ms(
        doc=doc,
        workspace_id=workspace_id,
        iterations=config.load_iterations,
    )
    interaction_samples = benchmark_pan_zoom_ms(
        doc=doc,
        workspace_id=workspace_id,
        samples=config.interaction_samples,
        seed=config.synthetic_graph.seed,
        zoom_min=config.interaction_zoom_min,
        zoom_max=config.interaction_zoom_max,
    )

    pan_summary = _metric_summary_ms(interaction_samples["pan_ms"])
    zoom_summary = _metric_summary_ms(interaction_samples["zoom_ms"])
    combined_summary = _metric_summary_ms(interaction_samples["combined_ms"])
    load_summary = _metric_summary_ms(load_samples)
    interaction_frame_p95 = max(pan_summary["p95"], zoom_summary["p95"])

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": _collect_environment_snapshot(),
        "config": {
            "synthetic_graph": asdict(config.synthetic_graph),
            "load_iterations": config.load_iterations,
            "interaction_samples": config.interaction_samples,
            "interaction_zoom_min": config.interaction_zoom_min,
            "interaction_zoom_max": config.interaction_zoom_max,
        },
        "metrics": {
            "project_graph_load_ms": {
                "samples": load_samples,
                "summary": load_summary,
            },
            "pan_interaction_ms": {
                "samples": interaction_samples["pan_ms"],
                "summary": pan_summary,
            },
            "zoom_interaction_ms": {
                "samples": interaction_samples["zoom_ms"],
                "summary": zoom_summary,
            },
            "pan_zoom_combined_ms": {
                "samples": interaction_samples["combined_ms"],
                "summary": combined_summary,
            },
        },
        "requirements_eval": {
            "REQ-PERF-001": {
                "pass": config.synthetic_graph.node_count >= 1000 and config.synthetic_graph.edge_count >= 5000,
                "details": f"Generated graph size {config.synthetic_graph.node_count} nodes / {config.synthetic_graph.edge_count} edges",
            },
            "REQ-PERF-002": {
                "pass": interaction_frame_p95 <= 33.0,
                "details": (
                    f"Pan p95={pan_summary['p95']:.3f} ms, "
                    f"Zoom p95={zoom_summary['p95']:.3f} ms "
                    f"(frame p95 target <= 33 ms)"
                ),
            },
            "REQ-PERF-003": {
                "pass": load_summary["p95"] < 3000.0,
                "details": f"Project+graph load p95={load_summary['p95']:.3f} ms (target < 3000 ms)",
            },
        },
        "limitations": [
            "Measurements are from a Python-level harness and include event-loop processing overhead.",
            "Runs use Qt offscreen platform (QT_QPA_PLATFORM=offscreen), so GPU/compositor behavior differs from interactive desktop rendering.",
            "Absolute timings are machine- and load-dependent; compare trends on the same hardware for regressions.",
        ],
    }


def run_benchmark(
    config: BenchmarkConfig,
    *,
    baseline_runs: int = 1,
    baseline_mode: str = "offscreen",
    baseline_tag: str = "local",
) -> dict[str, Any]:
    if baseline_runs <= 0:
        raise ValueError("baseline_runs must be > 0")

    full_runs: list[dict[str, Any]] = []
    series_runs: list[dict[str, Any]] = []
    for run_index in range(1, baseline_runs + 1):
        run_report = _run_single_benchmark(config)
        full_runs.append(run_report)
        metrics = run_report["metrics"]
        load_p95 = float(metrics["project_graph_load_ms"]["summary"]["p95"])
        pan_zoom_p95 = float(metrics["pan_zoom_combined_ms"]["summary"]["p95"])
        series_runs.append(
            {
                "run_id": f"run_{run_index:02d}",
                "generated_at_utc": run_report["generated_at_utc"],
                "mode": baseline_mode,
                "tag": baseline_tag,
                "environment": run_report["environment"],
                "metrics": {
                    "load_p95_ms": load_p95,
                    "pan_zoom_p95_ms": pan_zoom_p95,
                },
            }
        )

    latest_report = dict(full_runs[-1])

    load_p95_series = [float(run["metrics"]["load_p95_ms"]) for run in series_runs]
    pan_zoom_p95_series = [float(run["metrics"]["pan_zoom_p95_ms"]) for run in series_runs]

    load_cv = _coefficient_of_variation(load_p95_series)
    pan_zoom_cv = _coefficient_of_variation(pan_zoom_p95_series)
    load_range = max(load_p95_series) - min(load_p95_series) if load_p95_series else 0.0
    pan_zoom_range = max(pan_zoom_p95_series) - min(pan_zoom_p95_series) if pan_zoom_p95_series else 0.0

    load_threshold = _BASELINE_VARIANCE_THRESHOLDS["load_p95_ms"]
    pan_zoom_threshold = _BASELINE_VARIANCE_THRESHOLDS["pan_zoom_p95_ms"]
    enough_runs = baseline_runs >= 2

    latest_report["baseline_series"] = {
        "mode": baseline_mode,
        "tag": baseline_tag,
        "run_count": baseline_runs,
        "runs": series_runs,
        "variance_thresholds": _BASELINE_VARIANCE_THRESHOLDS,
        "variance_eval": {
            "load_p95_ms": {
                "pass": (load_cv <= load_threshold["max_cv"] and load_range <= load_threshold["max_range_ms"])
                if enough_runs
                else True,
                "cv": load_cv,
                "range_ms": load_range,
                "requires_min_runs": 2,
                "details": (
                    f"cv={load_cv:.4f} (<= {load_threshold['max_cv']:.2f}), "
                    f"range={load_range:.3f} ms (<= {load_threshold['max_range_ms']:.1f} ms)"
                ),
            },
            "pan_zoom_p95_ms": {
                "pass": (
                    pan_zoom_cv <= pan_zoom_threshold["max_cv"]
                    and pan_zoom_range <= pan_zoom_threshold["max_range_ms"]
                )
                if enough_runs
                else True,
                "cv": pan_zoom_cv,
                "range_ms": pan_zoom_range,
                "requires_min_runs": 2,
                "details": (
                    f"cv={pan_zoom_cv:.4f} (<= {pan_zoom_threshold['max_cv']:.2f}), "
                    f"range={pan_zoom_range:.3f} ms (<= {pan_zoom_threshold['max_range_ms']:.1f} ms)"
                ),
            },
        },
        "triage_policy": [
            "If variance check fails, first rerun 3x on the same machine with no background workloads.",
            "If variance remains high, classify by hardware tier (CPU/GPU/RAM/display) and keep separate baselines.",
            "Investigate regressions only when thresholds fail on at least two consecutive runs in the same hardware tier.",
        ],
        "notes": (
            "Variance checks are informative when run_count >= 2. "
            "Single-run captures still provide point-in-time regression evidence."
        ),
    }
    return latest_report


def _write_markdown_report(report: dict[str, Any], path: Path) -> None:
    metrics = report["metrics"]
    load = metrics["project_graph_load_ms"]["summary"]
    pan = metrics["pan_interaction_ms"]["summary"]
    zoom = metrics["zoom_interaction_ms"]["summary"]
    combined = metrics["pan_zoom_combined_ms"]["summary"]
    baseline_series = report.get("baseline_series", {})

    lines: list[str] = []
    lines.append("# Track H Benchmark Report")
    lines.append("")
    lines.append(f"- Generated (UTC): `{report['generated_at_utc']}`")
    lines.append("- Command:")
    lines.append("  `venv\\Scripts\\python -m ea_node_editor.telemetry.performance_harness`")
    lines.append(f"- Platform: `{report['environment']['platform']}`")
    lines.append(f"- Python: `{report['environment']['python_version']}`")
    lines.append(f"- Qt platform: `{report['environment']['qt_qpa_platform']}`")
    lines.append("")
    lines.append("## Config")
    lines.append("")
    cfg = report["config"]
    graph_cfg = cfg["synthetic_graph"]
    lines.append(f"- Synthetic graph: `{graph_cfg['node_count']}` nodes / `{graph_cfg['edge_count']}` edges")
    lines.append(f"- Seed: `{graph_cfg['seed']}`")
    lines.append(f"- Load iterations: `{cfg['load_iterations']}`")
    lines.append(f"- Pan/zoom samples: `{cfg['interaction_samples']}`")
    lines.append("")
    lines.append("## Metrics (ms)")
    lines.append("")
    lines.append("| Metric | p50 | p95 | Mean | Min | Max |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    lines.append(
        f"| Project + graph load | {load['p50']:.3f} | {load['p95']:.3f} | {load['mean']:.3f} | {load['min']:.3f} | {load['max']:.3f} |"
    )
    lines.append(
        f"| Pan interaction | {pan['p50']:.3f} | {pan['p95']:.3f} | {pan['mean']:.3f} | {pan['min']:.3f} | {pan['max']:.3f} |"
    )
    lines.append(
        f"| Zoom interaction | {zoom['p50']:.3f} | {zoom['p95']:.3f} | {zoom['mean']:.3f} | {zoom['min']:.3f} | {zoom['max']:.3f} |"
    )
    lines.append(
        f"| Pan + zoom (combined) | {combined['p50']:.3f} | {combined['p95']:.3f} | {combined['mean']:.3f} | {combined['min']:.3f} | {combined['max']:.3f} |"
    )
    lines.append("")
    lines.append("## Requirement Check")
    lines.append("")
    lines.append("| Requirement | Result | Details |")
    lines.append("|---|---|---|")
    for requirement_id, entry in report["requirements_eval"].items():
        result = "PASS" if entry["pass"] else "FAIL"
        lines.append(f"| {requirement_id} | {result} | {entry['details']} |")
    lines.append("")
    if baseline_series:
        lines.append("## Baseline Series")
        lines.append("")
        lines.append(f"- Mode: `{baseline_series.get('mode', 'offscreen')}`")
        lines.append(f"- Tag: `{baseline_series.get('tag', 'local')}`")
        lines.append(f"- Run count: `{baseline_series.get('run_count', 0)}`")
        lines.append("")
        lines.append("| Run | Mode | Load p95 (ms) | Pan+Zoom p95 (ms) | Qt Platform | Machine |")
        lines.append("|---|---|---:|---:|---|---|")
        for run in baseline_series.get("runs", []):
            env = run.get("environment", {})
            run_metrics = run.get("metrics", {})
            lines.append(
                "| "
                f"{run.get('run_id', '')} | "
                f"{run.get('mode', '')} | "
                f"{float(run_metrics.get('load_p95_ms', 0.0)):.3f} | "
                f"{float(run_metrics.get('pan_zoom_p95_ms', 0.0)):.3f} | "
                f"{env.get('qt_qpa_platform', '')} | "
                f"{env.get('machine', '')} |"
            )
        lines.append("")
        lines.append("### Variance Policy")
        lines.append("")
        thresholds = baseline_series.get("variance_thresholds", {})
        variance_eval = baseline_series.get("variance_eval", {})
        lines.append("| Metric | CV Threshold | Range Threshold (ms) | Observed CV | Observed Range (ms) | Result |")
        lines.append("|---|---:|---:|---:|---:|---|")
        for metric_key in ("load_p95_ms", "pan_zoom_p95_ms"):
            threshold = thresholds.get(metric_key, {})
            observed = variance_eval.get(metric_key, {})
            result = "PASS" if observed.get("pass", False) else "FAIL"
            lines.append(
                "| "
                f"{metric_key} | "
                f"{float(threshold.get('max_cv', 0.0)):.2f} | "
                f"{float(threshold.get('max_range_ms', 0.0)):.1f} | "
                f"{float(observed.get('cv', 0.0)):.4f} | "
                f"{float(observed.get('range_ms', 0.0)):.3f} | "
                f"{result} |"
            )
        lines.append("")
        lines.append("### Triage")
        lines.append("")
        for item in baseline_series.get("triage_policy", []):
            lines.append(f"- {item}")
        note = str(baseline_series.get("notes", "")).strip()
        if note:
            lines.append("")
            lines.append(f"- Note: {note}")
        lines.append("")
    lines.append("## Limitations")
    lines.append("")
    for item in report["limitations"]:
        lines.append(f"- {item}")
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Track H performance harness for EA Node Editor.")
    parser.add_argument("--nodes", type=int, default=1000, help="Synthetic node count.")
    parser.add_argument("--edges", type=int, default=5000, help="Synthetic edge count.")
    parser.add_argument("--seed", type=int, default=1337, help="Deterministic random seed.")
    parser.add_argument("--load-iterations", type=int, default=5, help="Project/graph load iterations.")
    parser.add_argument("--interaction-samples", type=int, default=200, help="Pan/zoom sample count.")
    parser.add_argument(
        "--baseline-runs",
        type=int,
        default=1,
        help="Number of repeated baseline runs for variance analysis.",
    )
    parser.add_argument(
        "--baseline-mode",
        choices=("auto", "offscreen", "interactive"),
        default="auto",
        help="Label for run mode; auto resolves from active Qt platform.",
    )
    parser.add_argument(
        "--baseline-tag",
        type=str,
        default="local",
        help="Free-form tag for grouping baseline runs (e.g., pilot_hw_a).",
    )
    parser.add_argument(
        "--qt-platform",
        type=str,
        default="",
        help="Optional override for QT_QPA_PLATFORM before creating QApplication.",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=Path("docs/specs/perf"),
        help="Output folder for benchmark reports.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.qt_platform:
        os.environ["QT_QPA_PLATFORM"] = args.qt_platform
    resolved_mode = _resolve_baseline_mode(args.baseline_mode, os.environ.get("QT_QPA_PLATFORM", ""))
    config = BenchmarkConfig(
        synthetic_graph=SyntheticGraphConfig(
            node_count=args.nodes,
            edge_count=args.edges,
            seed=args.seed,
        ),
        load_iterations=args.load_iterations,
        interaction_samples=args.interaction_samples,
    )
    report = run_benchmark(
        config,
        baseline_runs=args.baseline_runs,
        baseline_mode=resolved_mode,
        baseline_tag=args.baseline_tag,
    )

    report_dir: Path = args.report_dir
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "track_h_benchmark_report.json"
    md_path = report_dir / "TRACK_H_BENCHMARK_REPORT.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    _write_markdown_report(report, md_path)

    load = report["metrics"]["project_graph_load_ms"]["summary"]
    pan_zoom = report["metrics"]["pan_zoom_combined_ms"]["summary"]
    baseline = report.get("baseline_series", {})
    print(f"Benchmark report written: {md_path}")
    print(f"Benchmark data written:   {json_path}")
    if baseline:
        print(
            "baseline_mode="
            f"{baseline.get('mode', 'offscreen')} baseline_runs={baseline.get('run_count', 1)}"
        )
    print(f"load_p50_ms={load['p50']:.3f}")
    print(f"load_p95_ms={load['p95']:.3f}")
    print(f"pan_zoom_p50_ms={pan_zoom['p50']:.3f}")
    print(f"pan_zoom_p95_ms={pan_zoom['p95']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
