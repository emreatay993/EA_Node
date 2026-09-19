# Purpose: Prove the parity tool uses Signal/XY and preserves canonical data.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_plot_visual_parity_tool.py
from __future__ import annotations

import json

import pytest

from scripts.verify_plot_visual_parity import main


@pytest.mark.parametrize("kind", ["line", "scatter"])
def test_signal_parity_tool_compares_real_xy_pngs_and_full_samples(tmp_path, kind) -> None:
    source = tmp_path / "source.csv"
    source.write_text("time,value\n" + "".join(f"{index},{index * 2}\n" for index in range(80)))
    output = tmp_path / kind
    assert main(["--csv", str(source), "--x", "time", "--y", "value", "--kind", kind,
                 "--max-points", "100", "--output-dir", str(output)]) == 0
    metrics = json.loads((output / "parity_metrics.json").read_text())
    assert metrics["renderer"] == "Signal Plot / XY"
    assert metrics["sample_counts"] == [80]
    assert metrics["canonical_samples_unchanged"] is True
    assert metrics["mean_abs_diff"] == 0
    assert (output / "decimated.png").read_bytes() == (output / "full.png").read_bytes()


def test_signal_parity_tool_reduces_png_and_fails_a_real_zero_difference_budget(tmp_path) -> None:
    import math

    source = tmp_path / "wave.csv"
    source.write_text("time,value\n" + "".join(f"{index},{math.sin(index / 13)}\n" for index in range(600)))
    output = tmp_path / "reduced"
    assert main(["--csv", str(source), "--x", "time", "--y", "value", "--max-points", "40",
                 "--threshold", "0", "--output-dir", str(output)]) == 1
    metrics = json.loads((output / "parity_metrics.json").read_text())
    assert metrics["sample_counts"] == [600]
    assert metrics["canonical_samples_unchanged"] is True
    assert any("reduced from 600" in warning for warning in metrics["warnings"])
    assert metrics["mean_abs_diff"] > 0
