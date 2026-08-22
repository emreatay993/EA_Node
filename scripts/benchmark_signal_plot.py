from __future__ import annotations

import argparse
import gc
import json
import math
import os
import statistics
import tempfile
import threading
import time
from pathlib import Path

import psutil

from ea_node_editor.execution.plot_backend import PlotRenderRequest, PlotStaticExportRequest
from ea_node_editor.execution.plot_backend_matplotlib import MatplotlibPlotBackend
from ea_node_editor.execution.signal_plot_renderer import render_signal_plot
from ea_node_editor.runtime_contracts import DataTree


def _p95(values: list[float]) -> float:
    return statistics.quantiles(values, n=20, method="inclusive")[18]


def _measure(render, *, warmups: int, measurements: int) -> tuple[list[float], int]:
    process = psutil.Process(os.getpid())
    for _ in range(warmups):
        render()
    times: list[float] = []
    peaks: list[int] = []
    for _ in range(measurements):
        gc.collect()
        samples: list[int] = []
        stop = threading.Event()

        def sample() -> None:
            while not stop.is_set():
                samples.append(process.memory_info().rss)
                stop.wait(0.001)

        sampler = threading.Thread(target=sample, daemon=True)
        sampler.start()
        started = time.perf_counter()
        render()
        times.append(time.perf_counter() - started)
        stop.set()
        sampler.join()
        samples.append(process.memory_info().rss)
        peaks.append(max(samples))
    return times, max(peaks)


def benchmark(renderer: str, points: int, *, warmups: int, measurements: int) -> dict[str, object]:
    x = list(range(points))
    branches = (
        tuple(math.sin(index * 0.001) for index in x),
        tuple(math.cos(index * 0.001) for index in x),
    )
    if renderer == "xy":
        tree = DataTree((((0,), branches[0]), ((1,), branches[1])))

        def render() -> None:
            render_signal_plot({"values": tree, "marker_shapes": [0]})

    else:
        request = PlotRenderRequest(
            plot_type="line",
            series=(
                {"label": "signal-a", "x": x, "y": branches[0]},
                {"label": "signal-b", "x": x, "y": branches[1]},
            ),
        )
        temporary = tempfile.TemporaryDirectory()
        output = Path(temporary.name) / "baseline.png"

        def render() -> None:
            MatplotlibPlotBackend().export_static(
                PlotStaticExportRequest(
                    render_request=request,
                    output_path=output,
                    width_inches=6.0,
                    height_inches=4.0,
                    dpi=100,
                )
            )

    times, peak = _measure(render, warmups=warmups, measurements=measurements)
    return {
        "renderer": renderer,
        "branches": 2,
        "point_count_per_branch": points,
        "width": 600,
        "height": 400,
        "warmups": warmups,
        "measurements": measurements,
        "times_seconds": times,
        "mean_seconds": statistics.mean(times),
        "p95_seconds": _p95(times),
        "peak_rss_bytes": peak,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--renderer", choices=("matplotlib", "xy", "both"), default="both")
    parser.add_argument("--points", type=int, nargs="+", default=(10_000, 1_000_000))
    parser.add_argument("--warmups", type=int, default=3)
    parser.add_argument("--measurements", type=int, default=10)
    args = parser.parse_args()
    renderers = ("matplotlib", "xy") if args.renderer == "both" else (args.renderer,)
    for renderer in renderers:
        for points in args.points:
            print(json.dumps(benchmark(renderer, points, warmups=args.warmups, measurements=args.measurements), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
