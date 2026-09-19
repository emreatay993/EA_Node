"""Compare reduced/full Signal Plot PNGs through the production XY renderer.

Usage: python scripts/verify_plot_visual_parity.py --csv data.csv --x time --y value
Use --kind scatter for marker-only plots. This proves PNG parity and unchanged
canonical samples; interactive fullscreen behavior has its own XY integration tests.
"""
# Purpose: Verify Signal Plot reduction through its production XY rendering owner.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_plot_visual_parity_tool.py
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_CSV = "C:/Users/emre_/PycharmProjects/we_load_visualizer/modular_V2/full_data.csv"
PARITY_DIR = REPO_ROOT / "artifacts" / "perf" / "parity"
MEAN_DIFF_THRESHOLD = 2.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", default=DEFAULT_CSV)
    parser.add_argument("--x", default="", help="exact X column; automatic when omitted")
    parser.add_argument("--y", default="", help="exact Y column; automatic when omitted")
    parser.add_argument("--kind", choices=("line", "scatter"), default="line")
    parser.add_argument("--max-points", type=int, default=4000)
    parser.add_argument("--threshold", type=float, default=MEAN_DIFF_THRESHOLD)
    parser.add_argument("--output-dir", type=Path, default=PARITY_DIR)
    args = parser.parse_args(argv)

    import numpy as np
    from matplotlib import image as mpimg
    from ea_node_editor.addons.tabular_data.loader_cache_service import shared_tabular_loader_cache_service
    from ea_node_editor.execution.signal_plot_renderer import create_signal_plot
    from ea_node_editor.runtime_contracts import PlotProvenance

    source = Path(args.csv)
    if not source.is_file():
        sys.stderr.write(f"csv not found: {source}\n")
        return 2
    args.output_dir.mkdir(parents=True, exist_ok=True)
    ref = shared_tabular_loader_cache_service().open_source(source)
    inputs = {
        "values": ref,
        "width": 960,
        "height": 540,
        "line_styles": [0 if args.kind == "scatter" else 1],
        "marker_shapes": [1 if args.kind == "scatter" else 0],
        "x_mode": "column" if args.x else "auto",
        "x_column": args.x,
        "y_columns": [args.y] if args.y else [],
    }
    provenance = PlotProvenance("parity", "signal_plot", "parity_run")
    reduced, warnings = create_signal_plot({**inputs, "max_points": args.max_points}, provenance=provenance)
    full, _ = create_signal_plot({**inputs, "max_points": 0}, provenance=provenance)
    assert reduced.provenance == full.provenance == provenance
    assert len(reduced.signals) == len(full.signals)
    for left, right in zip(reduced.signals, full.signals, strict=True):
        assert (left.signal_id, left.label, left.x_kind) == (right.signal_id, right.label, right.x_kind)
        np.testing.assert_array_equal(left.x.to_numpy(), right.x.to_numpy())
        np.testing.assert_array_equal(left.y.to_numpy(), right.y.to_numpy())

    reduced_path = args.output_dir / "decimated.png"
    full_path = args.output_dir / "full.png"
    reduced_path.write_bytes(reduced.preview.encoded_bytes)
    full_path.write_bytes(full.preview.encoded_bytes)
    reduced_pixels = (mpimg.imread(reduced_path) * 255.0).astype(np.float64)
    full_pixels = (mpimg.imread(full_path) * 255.0).astype(np.float64)
    if reduced_pixels.shape != full_pixels.shape:
        sys.stderr.write(f"shape mismatch: {reduced_pixels.shape} vs {full_pixels.shape}\n")
        return 1
    delta = np.abs(reduced_pixels - full_pixels)
    metrics = {
        "renderer": "Signal Plot / XY",
        "evidence": "PNG parity and complete canonical samples; not fullscreen interaction",
        "kind": args.kind,
        "csv": str(source.resolve()),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "sample_counts": [signal.y.shape[0] for signal in full.signals],
        "canonical_samples_unchanged": True,
        "max_points": args.max_points,
        "warnings": list(warnings),
        "mean_abs_diff": float(delta.mean()),
        "max_abs_diff": float(delta.max()),
        "diff_pixel_fraction": float((delta.max(axis=-1) > 8).mean()),
        "threshold": args.threshold,
    }
    (args.output_dir / "parity_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    if metrics["mean_abs_diff"] > args.threshold:
        sys.stderr.write("PARITY FAIL: mean pixel difference exceeds threshold\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
