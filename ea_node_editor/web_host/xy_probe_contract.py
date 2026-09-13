# Purpose: Validate lightweight cursor messages and inspection state without loading NumPy.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_xy_probes.py
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ea_node_editor.runtime_contracts import PlotValue

PROBE_PAGE_SIZE = 50
PROBE_METHODS = ("intersections", "nearest")


def _finite(value: object) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("Probe coordinates must be finite numbers")
    return float(value)


def normalized_probe_state(value: object = None, *, logarithmic_y: bool = False) -> dict:
    if value is None:
        return {"positions": {"x": None, "y": None}, "active": "x", "method": None}
    if type(value) is not dict or set(value) - {"positions", "active", "method"}:
        raise ValueError("Invalid probe state")
    positions = value.get("positions", {})
    if type(positions) is not dict or set(positions) - {"x", "y"}:
        raise ValueError("Probes support one X and one Y coordinate")
    result = {axis: None if positions.get(axis) is None else _finite(positions[axis]) for axis in ("x", "y")}
    if logarithmic_y and result["y"] is not None and result["y"] <= 0:
        raise ValueError("A logarithmic Y probe must be positive")
    active, method = value.get("active", "x"), value.get("method")
    if type(active) is not str or active not in ("x", "y") or method not in (*PROBE_METHODS, None):
        raise ValueError("Invalid probe axis or reading method")
    return {"positions": result, "active": active, "method": method}


@dataclass(frozen=True)
class ProbeQuery:
    axis: str
    position: float
    method: str
    ranges: dict[str, tuple[float, float]]
    page: int
    revision: int

    @classmethod
    def parse(cls, value: dict, *, logarithmic_y: bool = False) -> "ProbeQuery":
        if type(value) is not dict:
            raise ValueError("A probe request must be an object")
        axis, method = value.get("axis"), value.get("method")
        if type(axis) is not str or axis not in ("x", "y") or type(method) is not str or method not in PROBE_METHODS:
            raise ValueError("Invalid probe axis or reading method")
        position = _finite(value.get("position"))
        ranges = value.get("ranges")
        if type(ranges) is not dict or set(ranges) != {"x", "y"}:
            raise ValueError("A probe needs the current X and Y view ranges")
        normalized = {}
        for key, bounds in ranges.items():
            if type(bounds) not in (tuple, list) or len(bounds) != 2:
                raise ValueError("Invalid probe view range")
            lo, hi = map(_finite, bounds)
            if lo >= hi:
                raise ValueError("Probe view ranges must be increasing")
            normalized[key] = (lo, hi)
        if logarithmic_y and (normalized["y"][0] <= 0 or axis == "y" and position <= 0):
            raise ValueError("Logarithmic Y coordinates must be positive")
        page, revision = value.get("page", 0), value.get("revision")
        if type(page) is not int or not 0 <= page <= 2**31 - 1:
            raise ValueError("Invalid probe page")
        if type(revision) is not int or not 0 <= revision <= 2**53 - 1:
            raise ValueError("Invalid probe request revision")
        return cls(axis, position, method, normalized, page, revision)


def signal_label(plot: PlotValue, index: int) -> str:
    label = plot.settings.labels[index] if plot.settings.labels else plot.signals[index].label
    return label or f"Signal {index + 1}"


def probe_metadata(plot: PlotValue, mark_ids: tuple[str, ...], kinds: list[str]) -> dict:
    return {"x_kind": plot.signals[0].x_kind, "y_log": plot.settings.logarithmic_y_axis,
            "signals": [{"id": signal.signal_id, "label": signal_label(plot, i),
                         "color": plot.settings.colors[i % len(plot.settings.colors)]}
                        for i, signal in enumerate(plot.signals)],
            "marks": [{"id": i, "signal": signal_id, "kind": kinds[i]} for i, signal_id in enumerate(mark_ids)]}
