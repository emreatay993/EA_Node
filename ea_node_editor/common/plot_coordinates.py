# Purpose: Share loss-minimizing plotted coordinates between rendering and inspection.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_signal_plot_renderer.py, tests/test_xy_probes.py
from __future__ import annotations

import numpy as np


def plot_x_coordinates(values: np.ndarray) -> np.ndarray:
    """Numeric X, or UTC milliseconds including representable sub-ms fractions."""
    if values.dtype.kind != "M":
        return values
    milliseconds = values.astype("datetime64[ms]")
    fractional_ms = (values - milliseconds).astype("timedelta64[ns]").astype(np.float64) / 1_000_000
    result = milliseconds.astype(np.float64) + fractional_ms
    result[np.isnat(values)] = np.nan
    return result
