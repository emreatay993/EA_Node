"""Detailed pan/zoom canvas profiler for EA Node Editor.

Goal
----
Pinpoint what causes lag in the GraphCanvas during pan/zoom interactions on
high-DPI desktops, especially when "heavy" nodes (passive media, viewers) are
present. The user reports lower FPS during pan/zoom on a 4K@200% display.

What this profiler measures
---------------------------
1. Per pan/zoom step wall-clock cost on the *real* GraphCanvas.qml render path,
   reusing the steady-state benchmark host that ships in
   `ea_node_editor.ui.perf.performance_harness`.
2. Per-component breakdown via Python monkey-patches on the hot path:
     * `ViewportBridge.set_view_state`
     * `ViewportBridge._refresh_visible_scene_rect_cache`
     * `EmbeddedViewerOverlayManager._sync_impl` (run as a separate
       micro-benchmark over a synthetic scene tree)
3. cProfile capture over the steady-state pan/zoom loop to surface the top
   Python functions by cumulative time.
4. A device-pixel-ratio (DPR) ablation: same scenario rendered with the user's
   native DPR vs `QT_SCALE_FACTOR=1.0`. The delta isolates the cost imposed by
   high-DPI compositing.

Output
------
- `artifacts/canvas_lag_profiling/profile_<timestamp>/profile_results.json`
- A markdown summary, plus matplotlib PNG charts for visual inspection.

The profiler runs each scenario in a fresh subprocess so DPR overrides and Qt
state stay isolated. Sub-runs use the `windows` Qt platform plugin so the
display's actual scale factor is honoured.

Usage
-----
    venv\\Scripts\\python scripts/profile_canvas_lag.py
    venv\\Scripts\\python scripts/profile_canvas_lag.py --samples 30
    venv\\Scripts\\python scripts/profile_canvas_lag.py --skip-dpr-ablation

This script is intentionally side-effect free with respect to the repo: it only
writes into `artifacts/canvas_lag_profiling/`.
"""
from __future__ import annotations

import argparse
import cProfile
import json
import os
import pstats
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Subprocess entry-point: runs a single profiling scenario and writes JSON.
# ---------------------------------------------------------------------------


def _run_subprocess_scenario(args: argparse.Namespace) -> int:
    # Force the Qt platform BEFORE any Qt imports.
    os.environ["QT_QPA_PLATFORM"] = args.qt_platform
    if args.scale_factor:
        # On Windows, the OS display scaling cannot be overridden via
        # QT_SCALE_FACTOR alone — the per-screen devicePixelRatio still
        # reflects the OS setting. To force a true DPR=1 we need a
        # combination of env overrides AND a Floor rounding policy applied
        # before QApplication is constructed (handled below).
        os.environ["QT_SCALE_FACTOR"] = args.scale_factor
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
        os.environ["QT_SCREEN_SCALE_FACTORS"] = args.scale_factor
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
    else:
        os.environ.pop("QT_SCALE_FACTOR", None)
        os.environ.pop("QT_AUTO_SCREEN_SCALE_FACTOR", None)
        os.environ.pop("QT_SCREEN_SCALE_FACTORS", None)
        os.environ.pop("QT_ENABLE_HIGHDPI_SCALING", None)

    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QGuiApplication
    from PyQt6.QtWidgets import QApplication

    if args.scale_factor:
        # MUST be set before any QApplication is constructed.
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.Floor
        )

    # Import the existing harness pieces lazily so the env vars above take
    # effect first.
    from ea_node_editor.persistence.serializer import JsonProjectSerializer
    from ea_node_editor.nodes.bootstrap import build_default_registry
    from ea_node_editor.ui.perf.performance_harness import (
        BenchmarkConfig,
        SyntheticGraphConfig,
        _build_scenario_project,
        _GraphCanvasBenchmarkHost,
        _measure_pan_zoom_step,
        _pan_zoom_target,
    )
    from ea_node_editor.ui_qml.viewport_bridge import ViewportBridge
    from ea_node_editor.ui_qml.embedded_viewer_overlay_manager import (
        EmbeddedViewerOverlayManager,
    )

    # The harness's per-sample loop calls wait_for_viewport_interaction_idle
    # with a 1000 ms default timeout. With GraphCanvas.qml's
    # interactionIdleDelayMs raised to 5000, that wait would always time out
    # (RuntimeError) AND it would force a layer-cache teardown between every
    # sample, defeating the purpose of measuring the post-fix steady state.
    # Patch the wait to be a no-op so interactionActive stays true across the
    # whole sample loop — modelling the continuous flick-and-drag behaviour
    # that the new debounce is meant to optimise.
    def _noop_wait_for_viewport_interaction_idle(
        self: "_GraphCanvasBenchmarkHost", *_args: object, **_kwargs: object
    ) -> None:
        return None

    _GraphCanvasBenchmarkHost.wait_for_viewport_interaction_idle = (  # type: ignore[method-assign]
        _noop_wait_for_viewport_interaction_idle
    )

    app = QApplication.instance() or QApplication(sys.argv)

    # ---- Instrument the hot Python path -------------------------------
    instrumentation = _Instrumentation()
    instrumentation.install(ViewportBridge, "set_view_state", classmethod_like=False)
    instrumentation.install(
        ViewportBridge,
        "_refresh_visible_scene_rect_cache",
        classmethod_like=False,
    )
    instrumentation.install(ViewportBridge, "adjust_zoom", classmethod_like=False)
    instrumentation.install(
        ViewportBridge, "adjust_zoom_at_viewport_point", classmethod_like=False
    )
    instrumentation.install(ViewportBridge, "centerOn", classmethod_like=False)
    instrumentation.install(ViewportBridge, "pan_by", classmethod_like=False)

    # Build scenario through existing code paths.
    scenario = args.scenario
    cfg = BenchmarkConfig(
        synthetic_graph=SyntheticGraphConfig(
            node_count=args.nodes,
            edge_count=args.edges,
            seed=1337,
        ),
        load_iterations=1,
        interaction_samples=args.samples,
        interaction_warmup_samples=args.warmup,
        performance_mode=args.performance_mode,
        scenario=scenario,
    )

    serializer = JsonProjectSerializer(build_default_registry())
    with _build_scenario_project(cfg) as scenario_project:
        project = scenario_project.project
        doc = serializer.to_document(project)
        workspace_id = project.active_workspace_id
        expected_media = int(
            scenario_project.scenario_details["expected_media_surface_count"]
        )

        host: _GraphCanvasBenchmarkHost | None = None
        try:
            t_setup = time.perf_counter()
            host = _GraphCanvasBenchmarkHost(
                app=app,
                doc=doc,
                workspace_id=workspace_id,
                performance_mode=args.performance_mode,
            )
            if expected_media > 0:
                host.prepare_media_ready_view()
            host.wait_for_media_surfaces_ready(expected_count=expected_media)
            setup_ms = (time.perf_counter() - t_setup) * 1000.0

            # ---- Wire frame-time hook ---------------------------------
            frame_times: list[float] = []

            def _record_frame_time() -> None:
                frame_times.append(time.perf_counter())

            host.window.afterRendering.connect(
                _record_frame_time, Qt.ConnectionType.DirectConnection
            )

            # Resolve scene bounds for sampling targets.
            workspace = host.model.project.workspaces[workspace_id]
            xs = [float(node.x) for node in workspace.nodes.values()] or [0.0]
            ys = [float(node.y) for node in workspace.nodes.values()] or [0.0]
            margin_x = 800.0
            margin_y = 500.0
            left = min(xs) - margin_x
            right = max(xs) + margin_x
            top = min(ys) - margin_y
            bottom = max(ys) + margin_y

            current_center_x = float(host.view.center_x)
            current_center_y = float(host.view.center_y)
            current_zoom = float(host.view.zoom)

            import random
            rng = random.Random(args.seed)

            # Warmup loop (untimed)
            for warmup_index in range(args.warmup):
                pan_x, pan_y, zoom = _pan_zoom_target(
                    current_center_x=current_center_x,
                    current_center_y=current_center_y,
                    current_zoom=current_zoom,
                    left=left,
                    right=right,
                    top=top,
                    bottom=bottom,
                    random_gen=rng,
                    index=warmup_index,
                    zoom_min=args.zoom_min,
                    zoom_max=args.zoom_max,
                )
                _measure_pan_zoom_step(
                    host, pan_to_x=pan_x, pan_to_y=pan_y, zoom_to=zoom
                )
                current_center_x, current_center_y, current_zoom = pan_x, pan_y, zoom

            # Reset frame and Python instrumentation counters now that warmup
            # is done.
            frame_times.clear()
            instrumentation.reset()

            # cProfile the steady-state loop.
            pan_samples_ms: list[float] = []
            zoom_samples_ms: list[float] = []
            profiler = cProfile.Profile()
            profiler.enable()

            for index in range(args.samples):
                pan_x, pan_y, zoom = _pan_zoom_target(
                    current_center_x=current_center_x,
                    current_center_y=current_center_y,
                    current_zoom=current_zoom,
                    left=left,
                    right=right,
                    top=top,
                    bottom=bottom,
                    random_gen=rng,
                    index=args.warmup + index,
                    zoom_min=args.zoom_min,
                    zoom_max=args.zoom_max,
                )
                pan_ms, zoom_ms = _measure_pan_zoom_step(
                    host, pan_to_x=pan_x, pan_to_y=pan_y, zoom_to=zoom
                )
                pan_samples_ms.append(pan_ms)
                zoom_samples_ms.append(zoom_ms)
                current_center_x, current_center_y, current_zoom = pan_x, pan_y, zoom

            profiler.disable()

            # ---- Capture screen DPR ----------------------------------
            primary_screen = QGuiApplication.primaryScreen()
            screen_dpr = float(primary_screen.devicePixelRatio()) if primary_screen else 1.0
            window_dpr = float(host.window.effectiveDevicePixelRatio()) if host.window else 1.0

            # ---- Build cProfile top-N payload -------------------------
            stats = pstats.Stats(profiler)
            stats.sort_stats("cumulative")
            top_functions = _profile_top_functions(stats, top_n=25)

            # ---- Compute per-frame intervals --------------------------
            frame_intervals_ms: list[float] = []
            for previous, nxt in zip(frame_times, frame_times[1:]):
                frame_intervals_ms.append((nxt - previous) * 1000.0)

            payload = {
                "scenario": scenario,
                "performance_mode": args.performance_mode,
                "qt_platform": args.qt_platform,
                "scale_factor_override": args.scale_factor or "",
                "screen_dpr": screen_dpr,
                "window_effective_dpr": window_dpr,
                "samples": args.samples,
                "warmup": args.warmup,
                "media_surface_count": expected_media,
                "node_count": args.nodes,
                "edge_count": args.edges,
                "setup_ms": setup_ms,
                "pan_ms": pan_samples_ms,
                "zoom_ms": zoom_samples_ms,
                "frame_intervals_ms": frame_intervals_ms,
                "frame_count": len(frame_times),
                "instrumentation": instrumentation.snapshot(),
                "top_functions": top_functions,
            }

        finally:
            if host is not None:
                host.close()

    Path(args.output_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return 0


# ---------------------------------------------------------------------------
# Instrumentation helper
# ---------------------------------------------------------------------------


@dataclass
class _MethodStat:
    call_count: int = 0
    total_ns: int = 0
    samples_ns: list[int] = field(default_factory=list)


class _Instrumentation:
    def __init__(self) -> None:
        self._stats: dict[str, _MethodStat] = {}

    def install(self, owner: type, attr: str, *, classmethod_like: bool) -> None:
        original = getattr(owner, attr)
        key = f"{owner.__name__}.{attr}"
        stat = self._stats.setdefault(key, _MethodStat())

        def _wrapper(self_or_cls, *args, **kwargs):  # noqa: ANN001
            t0 = time.perf_counter_ns()
            try:
                return original(self_or_cls, *args, **kwargs)
            finally:
                elapsed = time.perf_counter_ns() - t0
                stat.call_count += 1
                stat.total_ns += elapsed
                stat.samples_ns.append(elapsed)

        _wrapper.__name__ = original.__name__
        _wrapper.__wrapped__ = original  # type: ignore[attr-defined]
        setattr(owner, attr, _wrapper)

    def reset(self) -> None:
        for stat in self._stats.values():
            stat.call_count = 0
            stat.total_ns = 0
            stat.samples_ns = []

    def snapshot(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for key, stat in self._stats.items():
            samples_ms = [s / 1_000_000.0 for s in stat.samples_ns]
            summary = {
                "call_count": stat.call_count,
                "total_ms": stat.total_ns / 1_000_000.0,
                "mean_ms": (statistics.fmean(samples_ms) if samples_ms else 0.0),
                "median_ms": (statistics.median(samples_ms) if samples_ms else 0.0),
                "max_ms": max(samples_ms, default=0.0),
                "p95_ms": _percentile(samples_ms, 95.0),
            }
            result[key] = summary
        return result


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * (percentile / 100.0)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    return float(ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower))


def _profile_top_functions(stats: pstats.Stats, *, top_n: int) -> list[dict[str, Any]]:
    """Extract top-N functions sorted by cumulative time."""
    func_records: list[tuple[float, float, int, str]] = []
    for func, (call_count, _, total, cumulative, _callers) in stats.stats.items():
        filename, lineno, name = func
        # Skip pstats internals and built-ins
        if filename in {"~", "<built-in>"}:
            continue
        # Only include functions from the project, PyQt6, or Qt-related code.
        loc = f"{filename}:{lineno}"
        func_records.append((cumulative, total, call_count, f"{name}@{loc}"))
    func_records.sort(key=lambda r: r[0], reverse=True)
    return [
        {
            "function": rec[3],
            "call_count": rec[2],
            "total_ms": rec[1] * 1000.0,
            "cumulative_ms": rec[0] * 1000.0,
        }
        for rec in func_records[:top_n]
    ]


# ---------------------------------------------------------------------------
# Overlay-sync micro-benchmark (separate process)
# ---------------------------------------------------------------------------


def _run_overlay_sync_micro(args: argparse.Namespace) -> int:
    """Pure-Python timing of `EmbeddedViewerOverlayManager._sync_impl`.

    The overlay manager is normally driven by `view_state_changed` from a real
    `ViewportBridge`. The cost of `_sync_impl` scales with the number of
    `graphNodeCard` items in the QML tree because of the recursive walk in
    `_walk_items`. This micro-benchmark builds a synthetic GraphCanvas with N
    nodes and an attached widget, then times one full pan/zoom-driven sync per
    sample.
    """
    os.environ["QT_QPA_PLATFORM"] = args.qt_platform
    if args.scale_factor:
        os.environ["QT_SCALE_FACTOR"] = args.scale_factor

    from PyQt6.QtCore import QRectF, QUrl, Qt
    from PyQt6.QtGui import QGuiApplication
    from PyQt6.QtQml import QQmlComponent
    from PyQt6.QtQuickWidgets import QQuickWidget
    from PyQt6.QtWidgets import QApplication, QFrame

    from ea_node_editor.persistence.serializer import JsonProjectSerializer
    from ea_node_editor.nodes.bootstrap import build_default_registry
    from ea_node_editor.ui.perf.performance_harness import (
        BenchmarkConfig,
        SyntheticGraphConfig,
        _BenchmarkMainWindowBridge,
        _build_scenario_project,
        _CANVAS_BENCHMARK_HEIGHT,
        _CANVAS_BENCHMARK_WIDTH,
        _CANVAS_GRAPH_THEME_ID,
        _CANVAS_THEME_ID,
        _bind_scene_for_workspace,
        _graph_canvas_qml_path,
    )
    from ea_node_editor.ui.media_preview_provider import (
        LOCAL_MEDIA_PREVIEW_PROVIDER_ID,
        LocalMediaPreviewImageProvider,
    )
    from ea_node_editor.ui.pdf_preview_provider import (
        LOCAL_PDF_PREVIEW_PROVIDER_ID,
        LocalPdfPreviewImageProvider,
    )
    from ea_node_editor.ui_qml.embedded_viewer_overlay_manager import (
        EmbeddedViewerOverlayManager,
        EmbeddedViewerOverlaySpec,
    )
    from ea_node_editor.ui_qml.graph_canvas_command_bridge import GraphCanvasCommandBridge
    from ea_node_editor.ui_qml.graph_canvas_state_bridge import GraphCanvasStateBridge
    from ea_node_editor.ui_qml.graph_theme_bridge import GraphThemeBridge
    from ea_node_editor.ui_qml.theme_bridge import ThemeBridge

    app = QApplication.instance() or QApplication(sys.argv)

    # Build a heavy-media project so we have many node cards.
    cfg = BenchmarkConfig(
        synthetic_graph=SyntheticGraphConfig(
            node_count=args.nodes,
            edge_count=args.edges,
            seed=1337,
        ),
        load_iterations=1,
        interaction_samples=1,
        interaction_warmup_samples=0,
        performance_mode=args.performance_mode,
        scenario=args.scenario,
    )

    serializer = JsonProjectSerializer(build_default_registry())
    with _build_scenario_project(cfg) as scenario_project:
        project = scenario_project.project
        doc = serializer.to_document(project)
        workspace_id = project.active_workspace_id

        from ea_node_editor.graph.model import GraphModel
        model = GraphModel(serializer.from_document(doc))
        scene_bridge, view_bridge = _bind_scene_for_workspace(
            app=app, model=model, workspace_id=workspace_id
        )
        view_bridge.set_viewport_size(
            float(_CANVAS_BENCHMARK_WIDTH), float(_CANVAS_BENCHMARK_HEIGHT)
        )

        # Create the QQuickWidget instead of QQuickWindow so we can attach
        # an EmbeddedViewerOverlayManager.
        widget = QQuickWidget()
        widget.engine().addImageProvider(
            LOCAL_MEDIA_PREVIEW_PROVIDER_ID, LocalMediaPreviewImageProvider()
        )
        widget.engine().addImageProvider(
            LOCAL_PDF_PREVIEW_PROVIDER_ID, LocalPdfPreviewImageProvider()
        )
        theme_bridge = ThemeBridge(widget.engine(), theme_id=_CANVAS_THEME_ID)
        graph_theme_bridge = GraphThemeBridge(
            widget.engine(), theme_id=_CANVAS_GRAPH_THEME_ID
        )
        main_window_bridge = _BenchmarkMainWindowBridge(performance_mode=args.performance_mode)
        canvas_state_bridge = GraphCanvasStateBridge(
            shell_window=main_window_bridge,
            scene_bridge=scene_bridge,
            view_bridge=view_bridge,
        )
        canvas_command_bridge = GraphCanvasCommandBridge(
            shell_window=main_window_bridge,
            scene_bridge=scene_bridge,
            view_bridge=view_bridge,
        )
        ctx = widget.engine().rootContext()
        ctx.setContextProperty("themeBridge", theme_bridge)
        ctx.setContextProperty("graphThemeBridge", graph_theme_bridge)
        ctx.setContextProperty("canvasStateBridge", canvas_state_bridge)
        ctx.setContextProperty("canvasCommandBridge", canvas_command_bridge)

        widget.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        widget.resize(_CANVAS_BENCHMARK_WIDTH, _CANVAS_BENCHMARK_HEIGHT)
        # Provide initial properties via setContent so canvasStateBridge wires up.
        widget.setSource(QUrl.fromLocalFile(str(_graph_canvas_qml_path())))
        widget.show()
        # Pump events until QML is ready.
        app.processEvents()
        for _ in range(10):
            app.processEvents()

        if widget.status() != QQuickWidget.Status.Ready:
            sys.stderr.write(
                f"GraphCanvas.qml not ready in QQuickWidget: {widget.status()}\n"
            )

        overlay_manager = EmbeddedViewerOverlayManager(
            widget,
            quick_widget=widget,
            scene_bridge=scene_bridge,
            view_bridge=view_bridge,
        )

        # Pick the first available node id (any node will do for the
        # micro-bench because we are timing the *traversal* and the geometry
        # mapping, both of which are independent of node type).
        first_node_id = next(iter(model.project.workspaces[workspace_id].nodes.keys()))
        spec = EmbeddedViewerOverlaySpec(
            workspace_id=workspace_id, node_id=first_node_id, session_id="profile"
        )
        overlay_manager.set_active_overlays([spec])

        # Attach a synthetic heavy widget so the overlay container is real.
        fake_widget = QFrame(widget)
        fake_widget.setFrameShape(QFrame.Shape.Box)
        fake_widget.setStyleSheet("background-color: #2bd576;")
        fake_widget.resize(320, 240)
        overlay_manager.attach_overlay_widget(first_node_id, fake_widget)

        # Pump until the manager has settled and node cards exist.
        for _ in range(20):
            app.processEvents()

        # Time `_sync_impl` directly to isolate Python overhead.
        sync_samples_ms: list[float] = []
        for _ in range(args.samples):
            t0 = time.perf_counter_ns()
            overlay_manager._sync_impl()
            elapsed_ns = time.perf_counter_ns() - t0
            sync_samples_ms.append(elapsed_ns / 1_000_000.0)
            # Move the viewport so the next sync sees a different geometry
            # (forces real `_aligned_rect` work + `mapToItem` re-evaluation).
            view_bridge.pan_by(8.0, 5.0)
            app.processEvents()

        primary_screen = QGuiApplication.primaryScreen()
        screen_dpr = float(primary_screen.devicePixelRatio()) if primary_screen else 1.0

        payload = {
            "scenario": args.scenario,
            "node_count": args.nodes,
            "samples": args.samples,
            "screen_dpr": screen_dpr,
            "scale_factor_override": args.scale_factor or "",
            "sync_impl_ms": sync_samples_ms,
        }

        widget.deleteLater()
        scene_bridge.deleteLater()
        view_bridge.deleteLater()
        main_window_bridge.deleteLater()

    Path(args.output_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return 0


# ---------------------------------------------------------------------------
# Main driver: orchestrates subprocess scenarios + visualization
# ---------------------------------------------------------------------------


_DEFAULT_SCENARIOS = [
    {
        "label": "synthetic_native_dpr",
        "scenario": "synthetic_exec",
        "scale_factor": "",
        "performance_mode": "full_fidelity",
        "nodes": 200,
        "edges": 320,
    },
    {
        "label": "heavy_media_native_dpr",
        "scenario": "heavy_media",
        "scale_factor": "",
        "performance_mode": "full_fidelity",
        "nodes": 18,
        "edges": 30,
    },
    {
        "label": "heavy_media_dpr_1x",
        "scenario": "heavy_media",
        "scale_factor": "1",
        "performance_mode": "full_fidelity",
        "nodes": 18,
        "edges": 30,
    },
    {
        "label": "heavy_media_max_perf",
        "scenario": "heavy_media",
        "scale_factor": "",
        "performance_mode": "max_performance",
        "nodes": 18,
        "edges": 30,
    },
]


def _orchestrate(args: argparse.Namespace) -> int:
    out_root = REPO_ROOT / "artifacts" / "canvas_lag_profiling"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = out_root / f"profile_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    scenarios = _DEFAULT_SCENARIOS
    if args.skip_dpr_ablation:
        scenarios = [s for s in scenarios if s["label"] != "heavy_media_dpr_1x"]
    if args.skip_max_perf:
        scenarios = [s for s in scenarios if s["label"] != "heavy_media_max_perf"]

    results: list[dict[str, Any]] = []
    for scenario_cfg in scenarios:
        label = scenario_cfg["label"]
        out_path = out_dir / f"scenario_{label}.json"
        cmd = [
            sys.executable,
            __file__,
            "--mode",
            "scenario",
            "--scenario",
            scenario_cfg["scenario"],
            "--performance-mode",
            scenario_cfg["performance_mode"],
            "--samples",
            str(args.samples),
            "--warmup",
            str(args.warmup),
            "--nodes",
            str(scenario_cfg["nodes"]),
            "--edges",
            str(scenario_cfg["edges"]),
            "--seed",
            str(args.seed),
            "--zoom-min",
            str(args.zoom_min),
            "--zoom-max",
            str(args.zoom_max),
            "--qt-platform",
            args.qt_platform,
            "--output-path",
            str(out_path),
        ]
        if scenario_cfg["scale_factor"]:
            cmd.extend(["--scale-factor", scenario_cfg["scale_factor"]])
        sys.stdout.write(f"[profile] Running scenario {label} ...\n")
        sys.stdout.flush()
        log_path = out_dir / f"scenario_{label}.log"
        with log_path.open("wb") as log_file:
            completed = subprocess.run(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                timeout=900,
            )
        if completed.returncode != 0:
            sys.stderr.write(
                f"[profile] Scenario {label} failed (rc={completed.returncode}).\n"
                f"See log at: {log_path}\n"
            )
            continue
        try:
            payload = json.loads(out_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"[profile] Failed to read {out_path}: {exc}\n")
            continue
        payload["label"] = label
        results.append(payload)
        sys.stdout.write(f"[profile]   pan p95 {_p95(payload['pan_ms']):.2f} ms / "
                         f"zoom p95 {_p95(payload['zoom_ms']):.2f} ms / "
                         f"frames {payload['frame_count']}\n")

    # Run overlay-sync micro-bench.
    if not args.skip_overlay_micro:
        out_path = out_dir / "overlay_sync_micro.json"
        cmd = [
            sys.executable,
            __file__,
            "--mode",
            "overlay-sync",
            "--scenario",
            "heavy_media",
            "--performance-mode",
            "full_fidelity",
            "--samples",
            str(max(20, args.samples)),
            "--nodes",
            "18",
            "--edges",
            "30",
            "--qt-platform",
            args.qt_platform,
            "--output-path",
            str(out_path),
        ]
        sys.stdout.write("[profile] Running overlay sync micro-benchmark ...\n")
        sys.stdout.flush()
        log_path = out_dir / "overlay_sync_micro.log"
        with log_path.open("wb") as log_file:
            completed = subprocess.run(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                timeout=900,
            )
        if completed.returncode != 0:
            sys.stderr.write(
                "[profile] Overlay sync micro-benchmark failed.\n"
                f"See log at: {log_path}\n"
            )
            overlay_payload = None
        else:
            try:
                overlay_payload = json.loads(out_path.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                sys.stderr.write(f"[profile] Failed to read {out_path}: {exc}\n")
                overlay_payload = None
    else:
        overlay_payload = None

    summary_path = out_dir / "profile_results.json"
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "command_args": vars(args),
        "scenarios": results,
        "overlay_sync_micro": overlay_payload,
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Generate charts + markdown.
    _make_visualizations(out_dir, results, overlay_payload)
    _write_markdown_report(out_dir, results, overlay_payload)

    sys.stdout.write(f"\n[profile] Done. Results in: {out_dir}\n")
    return 0


def _p95(values: list[float]) -> float:
    return _percentile(values, 95.0)


def _make_visualizations(
    out_dir: Path,
    results: list[dict[str, Any]],
    overlay_payload: dict[str, Any] | None,
) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        sys.stderr.write("[profile] matplotlib not available; skipping charts.\n")
        return

    if not results:
        return

    # 1. Pan / zoom timing per scenario (box plot).
    fig, ax = plt.subplots(figsize=(10, 5))
    labels = [r["label"] for r in results]
    pan_data = [r["pan_ms"] for r in results]
    zoom_data = [r["zoom_ms"] for r in results]
    width = 0.35
    positions = list(range(len(labels)))
    bp1 = ax.boxplot(
        pan_data,
        positions=[p - width / 2 for p in positions],
        widths=width,
        patch_artist=True,
        boxprops=dict(facecolor="#4e79a7"),
        medianprops=dict(color="white"),
    )
    bp2 = ax.boxplot(
        zoom_data,
        positions=[p + width / 2 for p in positions],
        widths=width,
        patch_artist=True,
        boxprops=dict(facecolor="#f28e2b"),
        medianprops=dict(color="white"),
    )
    ax.set_xticks(positions)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel("Step time (ms)")
    ax.set_title("Pan / zoom step time by scenario (lower is better)")
    ax.axhline(33.3, color="#e15759", linestyle="--", linewidth=1, label="30 FPS budget (33.3 ms)")
    ax.axhline(16.7, color="#76b7b2", linestyle="--", linewidth=1, label="60 FPS budget (16.7 ms)")
    ax.legend(
        [bp1["boxes"][0], bp2["boxes"][0], plt.Line2D([], [], color="#e15759", linestyle="--"),
         plt.Line2D([], [], color="#76b7b2", linestyle="--")],
        ["pan_ms", "zoom_ms", "30 FPS", "60 FPS"],
        loc="upper left",
    )
    fig.tight_layout()
    fig.savefig(out_dir / "01_pan_zoom_step_times.png", dpi=120)
    plt.close(fig)

    # 2. Frame interval distribution (histogram per scenario).
    fig, axes = plt.subplots(
        nrows=len(results), ncols=1, figsize=(10, max(3, 2.5 * len(results))), sharex=True
    )
    if len(results) == 1:
        axes = [axes]
    for ax, r in zip(axes, results):
        intervals = r["frame_intervals_ms"]
        if not intervals:
            ax.text(0.5, 0.5, "no frames captured", ha="center", va="center")
            ax.set_title(r["label"])
            continue
        ax.hist(intervals, bins=40, color="#59a14f", alpha=0.85)
        ax.axvline(16.7, color="#76b7b2", linestyle="--", linewidth=1)
        ax.axvline(33.3, color="#e15759", linestyle="--", linewidth=1)
        median_iv = statistics.median(intervals)
        p95_iv = _percentile(intervals, 95.0)
        ax.set_title(
            f"{r['label']}  median={median_iv:.1f} ms  p95={p95_iv:.1f} ms  "
            f"(equiv FPS p50={_safe_fps(median_iv):.1f}, p5={_safe_fps(p95_iv):.1f})"
        )
        ax.set_ylabel("Frames")
    axes[-1].set_xlabel("Frame interval (ms)")
    fig.tight_layout()
    fig.savefig(out_dir / "02_frame_interval_histograms.png", dpi=120)
    plt.close(fig)

    # 3. Per-component instrumentation breakdown (stacked bar).
    fig, ax = plt.subplots(figsize=(10, 5))
    component_keys: list[str] = []
    for r in results:
        for k in r["instrumentation"].keys():
            if k not in component_keys:
                component_keys.append(k)
    bottoms = [0.0] * len(results)
    palette = [
        "#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
        "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac",
    ]
    for index, comp in enumerate(component_keys):
        totals = []
        for r in results:
            stat = r["instrumentation"].get(comp, {})
            totals.append(float(stat.get("total_ms", 0.0)))
        ax.bar(
            range(len(results)),
            totals,
            bottom=bottoms,
            color=palette[index % len(palette)],
            label=comp,
        )
        bottoms = [b + t for b, t in zip(bottoms, totals)]
    ax.set_xticks(range(len(results)))
    ax.set_xticklabels([r["label"] for r in results], rotation=20, ha="right")
    ax.set_ylabel("Total Python time during pan/zoom loop (ms)")
    ax.set_title("Python hot path per scenario (instrumented methods)")
    ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0))
    fig.tight_layout()
    fig.savefig(out_dir / "03_python_component_stack.png", dpi=120)
    plt.close(fig)

    # 4. cProfile top-N functions for the heaviest scenario.
    heaviest = max(results, key=lambda r: _p95(r["pan_ms"]))
    top = heaviest["top_functions"][:15]
    fig, ax = plt.subplots(figsize=(11, 6))
    names = [_short_func_name(t["function"]) for t in top]
    cumulative = [t["cumulative_ms"] for t in top]
    y_positions = list(range(len(names)))
    ax.barh(y_positions, cumulative, color="#4e79a7")
    ax.set_yticks(y_positions)
    ax.set_yticklabels(names, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Cumulative time (ms)")
    ax.set_title(
        f"cProfile top functions during pan/zoom loop ({heaviest['label']})"
    )
    fig.tight_layout()
    fig.savefig(out_dir / "04_cprofile_top_functions.png", dpi=120)
    plt.close(fig)

    # 5. DPR ablation summary (only when both heavy_media native and 1x exist).
    by_label = {r["label"]: r for r in results}
    if "heavy_media_native_dpr" in by_label and "heavy_media_dpr_1x" in by_label:
        a = by_label["heavy_media_native_dpr"]
        b = by_label["heavy_media_dpr_1x"]
        metrics = ["pan p50", "pan p95", "zoom p50", "zoom p95"]
        a_vals = [
            _percentile(a["pan_ms"], 50),
            _percentile(a["pan_ms"], 95),
            _percentile(a["zoom_ms"], 50),
            _percentile(a["zoom_ms"], 95),
        ]
        b_vals = [
            _percentile(b["pan_ms"], 50),
            _percentile(b["pan_ms"], 95),
            _percentile(b["zoom_ms"], 50),
            _percentile(b["zoom_ms"], 95),
        ]
        fig, ax = plt.subplots(figsize=(8, 5))
        x = list(range(len(metrics)))
        width = 0.35
        ax.bar(
            [xi - width / 2 for xi in x],
            a_vals,
            width=width,
            color="#e15759",
            label=f"native DPR ({a.get('window_effective_dpr', 'unknown')}x)",
        )
        ax.bar(
            [xi + width / 2 for xi in x],
            b_vals,
            width=width,
            color="#4e79a7",
            label="forced DPR 1x (QT_SCALE_FACTOR=1)",
        )
        ax.set_xticks(x)
        ax.set_xticklabels(metrics)
        ax.set_ylabel("Step time (ms)")
        ax.set_title("DPR ablation: heavy_media scenario")
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_dir / "05_dpr_ablation.png", dpi=120)
        plt.close(fig)

    # 6. Overlay sync micro-benchmark, if available.
    if overlay_payload and overlay_payload.get("sync_impl_ms"):
        samples = overlay_payload["sync_impl_ms"]
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.hist(samples, bins=30, color="#9c755f")
        ax.axvline(statistics.median(samples), color="#fff", linestyle="--", label="median")
        ax.set_xlabel("EmbeddedViewerOverlayManager._sync_impl (ms)")
        ax.set_ylabel("Samples")
        ax.set_title(
            f"Overlay sync micro-benchmark "
            f"(N={overlay_payload['node_count']} nodes; "
            f"DPR={overlay_payload['screen_dpr']}x)"
        )
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_dir / "06_overlay_sync_micro.png", dpi=120)
        plt.close(fig)


def _safe_fps(interval_ms: float) -> float:
    if interval_ms <= 0:
        return 0.0
    return 1000.0 / interval_ms


def _short_func_name(qualified: str) -> str:
    name, _, loc = qualified.partition("@")
    short_loc = loc
    for marker in ("ea_node_editor", "PyQt6", "site-packages"):
        idx = loc.rfind(marker)
        if idx >= 0:
            short_loc = loc[idx:]
            break
    return f"{name}  ({short_loc})"


def _write_markdown_report(
    out_dir: Path,
    results: list[dict[str, Any]],
    overlay_payload: dict[str, Any] | None,
) -> None:
    lines: list[str] = []
    lines.append("# Canvas Lag Profiling Report")
    lines.append("")
    lines.append(f"Generated: `{datetime.now(timezone.utc).isoformat()}`")
    lines.append("")
    lines.append("## Per-Scenario Summary")
    lines.append("")
    lines.append(
        "| Label | Scenario | Mode | DPR | Pan p50 (ms) | Pan p95 (ms) | "
        "Zoom p50 (ms) | Zoom p95 (ms) | Frames | Setup (ms) |"
    )
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for r in results:
        lines.append(
            "| {label} | {scenario} | {mode} | {dpr} | {p50p:.2f} | {p95p:.2f} | "
            "{p50z:.2f} | {p95z:.2f} | {frames} | {setup:.0f} |".format(
                label=r["label"],
                scenario=r["scenario"],
                mode=r["performance_mode"],
                dpr=r.get("window_effective_dpr", "?"),
                p50p=_percentile(r["pan_ms"], 50),
                p95p=_percentile(r["pan_ms"], 95),
                p50z=_percentile(r["zoom_ms"], 50),
                p95z=_percentile(r["zoom_ms"], 95),
                frames=r["frame_count"],
                setup=r["setup_ms"],
            )
        )
    lines.append("")

    lines.append("## Steady-state vs spike frame analysis")
    lines.append("")
    lines.append(
        "Frames are split at 100 ms: anything below is treated as part of the "
        "in-interaction steady state, anything above is a *hitch*. Hitches in "
        "this codebase are dominated by the `interactionIdleTimer` (150 ms "
        "debounce) firing and tearing down the per-node `layer.enabled` "
        "texture cache, which forces a full rasterization on the next frame."
    )
    lines.append("")
    lines.append(
        "| Scenario | DPR | Frames | Steady median (ms) | Steady FPS | "
        "Steady p95 (ms) | Spike count | Spike median (ms) | Spike rate |"
    )
    lines.append(
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    )
    for r in results:
        intervals = r.get("frame_intervals_ms", [])
        steady = [iv for iv in intervals if iv < 100.0]
        spikes = [iv for iv in intervals if iv >= 100.0]
        steady_median = statistics.median(steady) if steady else 0.0
        steady_p95 = _percentile(steady, 95.0)
        spike_median = statistics.median(spikes) if spikes else 0.0
        spike_rate = (len(spikes) / len(intervals) * 100.0) if intervals else 0.0
        steady_fps = (1000.0 / steady_median) if steady_median > 0 else 0.0
        lines.append(
            f"| {r['label']} | {r.get('window_effective_dpr', '?')} | "
            f"{len(intervals)} | {steady_median:.1f} | {steady_fps:.0f} | "
            f"{steady_p95:.1f} | {len(spikes)} | {spike_median:.1f} | "
            f"{spike_rate:.0f}% |"
        )
    lines.append("")

    lines.append("## Python Hot Path (instrumented)")
    lines.append("")
    component_keys: list[str] = []
    for r in results:
        for k in r["instrumentation"].keys():
            if k not in component_keys:
                component_keys.append(k)
    header = ["scenario"] + component_keys
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "---|" * len(header))
    for r in results:
        row = [r["label"]]
        for k in component_keys:
            stat = r["instrumentation"].get(k, {})
            calls = int(stat.get("call_count", 0))
            total = float(stat.get("total_ms", 0.0))
            row.append(f"{calls} calls / {total:.1f} ms")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    lines.append("## cProfile top functions per scenario (top 10)")
    lines.append("")
    for r in results:
        lines.append(f"### {r['label']}")
        lines.append("")
        lines.append("| Function | Calls | Cumulative (ms) | Self total (ms) |")
        lines.append("|---|---:|---:|---:|")
        for entry in r["top_functions"][:10]:
            lines.append(
                f"| `{entry['function']}` | {entry['call_count']} | "
                f"{entry['cumulative_ms']:.2f} | {entry['total_ms']:.2f} |"
            )
        lines.append("")

    if overlay_payload:
        lines.append("## EmbeddedViewerOverlayManager._sync_impl micro-benchmark")
        lines.append("")
        samples = overlay_payload.get("sync_impl_ms", [])
        if samples:
            lines.append(
                f"- Samples: {len(samples)}  "
                f"DPR: {overlay_payload.get('screen_dpr', '?')}x  "
                f"Nodes: {overlay_payload.get('node_count', '?')}"
            )
            lines.append(
                f"- Mean: {statistics.fmean(samples):.3f} ms  "
                f"median: {statistics.median(samples):.3f} ms  "
                f"p95: {_percentile(samples, 95):.3f} ms  "
                f"max: {max(samples):.3f} ms"
            )
        else:
            lines.append("- (no samples recorded)")
        lines.append("")

    lines.append("## Charts")
    lines.append("")
    lines.append("- `01_pan_zoom_step_times.png` – pan/zoom step distribution per scenario")
    lines.append("- `02_frame_interval_histograms.png` – frame interval histogram per scenario")
    lines.append("- `03_python_component_stack.png` – instrumented Python time stack")
    lines.append("- `04_cprofile_top_functions.png` – cProfile top cumulative functions (heaviest scenario)")
    lines.append("- `05_dpr_ablation.png` – heavy_media native DPR vs forced 1x DPR")
    lines.append("- `06_overlay_sync_micro.png` – EmbeddedViewerOverlayManager._sync_impl distribution")
    lines.append("")

    (out_dir / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Canvas pan/zoom lag profiler")
    parser.add_argument(
        "--mode",
        choices=("orchestrate", "scenario", "overlay-sync"),
        default="orchestrate",
    )
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--nodes", type=int, default=200)
    parser.add_argument("--edges", type=int, default=320)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--zoom-min", type=float, default=0.5)
    parser.add_argument("--zoom-max", type=float, default=2.0)
    parser.add_argument("--scenario", choices=("synthetic_exec", "heavy_media"))
    parser.add_argument(
        "--performance-mode", choices=("full_fidelity", "max_performance"), default="full_fidelity"
    )
    parser.add_argument("--qt-platform", default="windows")
    parser.add_argument("--scale-factor", default="")
    parser.add_argument("--output-path", default="")
    parser.add_argument(
        "--skip-dpr-ablation",
        action="store_true",
        help="Skip the forced QT_SCALE_FACTOR=1 sub-run.",
    )
    parser.add_argument(
        "--skip-max-perf",
        action="store_true",
        help="Skip the max_performance scenario.",
    )
    parser.add_argument(
        "--skip-overlay-micro",
        action="store_true",
        help="Skip the overlay sync micro-benchmark.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.mode == "scenario":
        if not args.scenario:
            sys.stderr.write("--scenario required in scenario mode\n")
            return 2
        return _run_subprocess_scenario(args)
    if args.mode == "overlay-sync":
        return _run_overlay_sync_micro(args)
    return _orchestrate(args)


if __name__ == "__main__":
    raise SystemExit(main())
