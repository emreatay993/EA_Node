"""Bounded plot-series decimation.

Plot surfaces render at canvas resolution, so line-like series never need more
points than a few thousand to be visually lossless. This module owns the
decimation contract used by the generic plot nodes: a per-bucket min-max
envelope for x/y series (preserves every global extreme and the first/last
points) and stride sampling for point-cloud-like series.

numpy is imported lazily inside the functions: the core plot contracts stay
importable without numpy, and these entry points only run when tabular/array
refs flow into a plot — a path that is dependency-gated on the tabular add-on
(which requires numpy).
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

DECIMATION_METHOD_NONE = "none"
DECIMATION_METHOD_MINMAX = "minmax"
DECIMATION_METHOD_STRIDE = "stride"


def _import_numpy() -> Any:
    import numpy

    return numpy


def decimate_xy(
    x: Sequence[float] | Any,
    y: Sequence[float] | Any,
    max_points: int,
) -> tuple[list[float], list[float], dict[str, Any]]:
    """Bound an x/y series to ``max_points`` via a per-bucket min-max envelope.

    Rows with a non-finite x or y are dropped first (matching the historical
    per-row numeric filtering of tabular plot series). The remaining samples
    are split into buckets along the row axis; each bucket contributes its
    minimum and maximum y sample (original x preserved, row order kept), and
    the first/last samples are always included. Global extremes therefore
    always survive. Returns plain Python lists so results embed directly into
    JSON-safe render-request payloads.
    """

    np = _import_numpy()
    x_values = np.asarray(x, dtype=np.float64)
    y_values = np.asarray(y, dtype=np.float64)
    if x_values.shape != y_values.shape:
        raise ValueError("decimate_xy requires x and y of equal length")
    original_rows = int(y_values.shape[0])
    budget = max(2, int(max_points))

    finite = np.isfinite(x_values) & np.isfinite(y_values)
    if not bool(finite.all()):
        x_values = x_values[finite]
        y_values = y_values[finite]
    count = int(y_values.shape[0])

    if count <= budget:
        return (
            x_values.tolist(),
            y_values.tolist(),
            {
                "method": DECIMATION_METHOD_NONE,
                "original_rows": original_rows,
                "points": count,
            },
        )

    buckets = max(1, (budget - 2) // 2)
    bucket_ids = (np.arange(count, dtype=np.int64) * buckets) // count

    def _first_per_bucket(order: Any) -> Any:
        sorted_ids = bucket_ids[order]
        _unique_ids, first_positions = np.unique(sorted_ids, return_index=True)
        return order[first_positions]

    min_indices = _first_per_bucket(np.lexsort((y_values, bucket_ids)))
    max_indices = _first_per_bucket(np.lexsort((-y_values, bucket_ids)))
    selected = np.union1d(min_indices, max_indices)
    selected = np.union1d(selected, np.array([0, count - 1], dtype=selected.dtype))

    return (
        x_values[selected].tolist(),
        y_values[selected].tolist(),
        {
            "method": DECIMATION_METHOD_MINMAX,
            "original_rows": original_rows,
            "points": int(selected.shape[0]),
        },
    )


def stride_sample_indices(count: int, max_points: int) -> Any:
    """Evenly spaced row indices bounding ``count`` rows to ``max_points``."""

    np = _import_numpy()
    total = max(0, int(count))
    budget = max(1, int(max_points))
    if total <= budget:
        return np.arange(total, dtype=np.int64)
    return np.unique(np.linspace(0, total - 1, budget).round().astype(np.int64))


def stride_sample_rows(
    rows: Sequence[Any],
    max_points: int,
) -> tuple[list[Any], dict[str, Any]]:
    """Bound a row sequence to ``max_points`` by even stride sampling."""

    original_rows = len(rows)
    if original_rows <= max(1, int(max_points)):
        return (
            list(rows),
            {
                "method": DECIMATION_METHOD_NONE,
                "original_rows": original_rows,
                "points": original_rows,
            },
        )
    indices = stride_sample_indices(original_rows, max_points)
    sampled = [rows[int(index)] for index in indices]
    return (
        sampled,
        {
            "method": DECIMATION_METHOD_STRIDE,
            "original_rows": original_rows,
            "points": len(sampled),
        },
    )


__all__ = [
    "DECIMATION_METHOD_MINMAX",
    "DECIMATION_METHOD_NONE",
    "DECIMATION_METHOD_STRIDE",
    "decimate_xy",
    "stride_sample_indices",
    "stride_sample_rows",
]
