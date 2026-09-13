# Purpose: Query full-resolution plot signals for bounded, visible-window cursor results.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_xy_probes.py
from __future__ import annotations

from decimal import Decimal
import math
from typing import Callable

import numpy as np

from ea_node_editor.common.plot_coordinates import plot_x_coordinates
from ea_node_editor.runtime_contracts import PlotValue
from ea_node_editor.web_host.xy_probe_contract import PROBE_PAGE_SIZE, ProbeQuery

PROBE_CHUNK_SIZE = 65_536


class ProbeCancelled(Exception):
    """The owning plot was retired while scanning a large signal."""


def _scaled(values: np.ndarray, logarithmic: bool) -> np.ndarray:
    if not logarithmic:
        return values
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(values > 0, np.log(values), np.nan)


class _Page:
    def __init__(self, page: int) -> None:
        self.offset = page * PROBE_PAGE_SIZE
        self.total = self.overlaps = 0
        self.rows: list[dict] = []

    def add(self, size: int, row_at: Callable[[int], dict], *, overlaps: int = 0) -> None:
        begin = max(0, self.offset - self.total)
        end = min(size, self.offset + PROBE_PAGE_SIZE - self.total)
        for index in range(begin, end):
            self.rows.append(row_at(index))
        self.total += size
        self.overlaps += overlaps


class _SignalQuery:
    def __init__(self, signal, query: ProbeQuery, page: _Page, log_y: bool, cancelled: Callable[[], bool]) -> None:
        self.signal, self.query, self.page, self.log_y, self.cancelled = signal, query, page, log_y, cancelled
        self.raw_x, self.raw_y = signal.x.to_numpy(), signal.y.to_numpy()
        self.coordinate = math.log(query.position) if query.axis == "y" and log_y else query.position
        self.other = "y" if query.axis == "x" else "x"
        self.other_log = self.other == "y" and log_y
        self.lo, self.hi = (tuple(map(math.log, query.ranges[self.other])) if self.other_log else query.ranges[self.other])

    def chunk(self, start: int, stop: int):
        if self.cancelled():
            raise ProbeCancelled()
        x = np.asarray(plot_x_coordinates(self.raw_x[start:stop]), dtype=np.float64)
        y = np.asarray(self.raw_y[start:stop], dtype=np.float64)
        sy = _scaled(y, self.log_y)
        return x, y, sy, np.isfinite(x) & np.isfinite(sy)

    def row(self, kind: str, x: float, y: float, start: int, end: int, **extra) -> dict:
        result = {"signal": self.signal.signal_id, "kind": kind, "x": float(x), "y": float(y),
                  "sample_start": int(start), "sample_end": int(end), **extra}
        if self.signal.x_kind == "datetime":
            if kind in ("exact", "nearest"):
                result["x_text"] = str(self.raw_x[start]) + "Z"
            else:
                result["x_text"] = str(np.datetime64(int(round(x * 1000)), "us")) + "Z"
            if "x_end" in extra:
                result["x_end_text"] = str(np.datetime64(int(round(extra["x_end"] * 1000)), "us")) + "Z"
        return result

    def sample_row(self, index: int, kind: str = "exact") -> dict:
        x, y = float(plot_x_coordinates(self.raw_x[index:index + 1])[0]), float(self.raw_y[index])
        extra = {}
        if kind == "nearest":
            sample = x if self.query.axis == "x" else y
            offset = sample - self.query.position
            extra["offset"] = offset if math.isfinite(offset) else str(Decimal(str(sample)) - Decimal(str(self.query.position)))
        return self.row(kind, x, y, index, index, **extra)

    def nearest(self) -> None:
        best = math.inf
        axis_bounds = self.query.ranges[self.query.axis]
        scale = 1.0 if math.isfinite(axis_bounds[1] - axis_bounds[0]) else .5
        for collect in (False, True):
            for start in range(0, len(self.raw_x), PROBE_CHUNK_SIZE):
                x, y, sy, finite = self.chunk(start, start + PROBE_CHUNK_SIZE)
                visible = finite & (x >= self.query.ranges["x"][0]) & (x <= self.query.ranges["x"][1])
                visible &= (y >= self.query.ranges["y"][0]) & (y <= self.query.ranges["y"][1])
                values = x if self.query.axis == "x" else sy
                distance = np.abs(values * scale - self.coordinate * scale)
                if not collect:
                    best = min(best, float(np.min(distance[visible], initial=np.inf)))
                elif math.isfinite(best):
                    tied = distance == best
                    if self.query.axis == 'y' and self.log_y:
                        # Independently rounded logarithms can differ by a few
                        # ulps at a geometric midpoint (for example 2, 4, 8).
                        tolerance = 4 * np.finfo(float).eps * max(abs(self.coordinate), abs(best), 1.)
                        tied |= np.abs(distance - best) <= tolerance
                    indices = np.flatnonzero(visible & tied) + start
                    self.page.add(len(indices), lambda k: self.sample_row(int(indices[k]), "nearest"))

    def other_value(self, value: float) -> float:
        if not self.other_log:
            return float(value)
        with np.errstate(over="ignore"):
            converted = float(np.exp(value))
        lo, hi = self.query.ranges[self.other]
        return max(lo, min(hi, converted))

    def span_row(self, start: int, end: int, lo: float, hi: float) -> dict:
        lo, hi = self.other_value(lo), self.other_value(hi)
        if self.query.axis == "x":
            return self.row("overlap", self.query.position, lo, start, end, x_end=self.query.position, y_end=hi)
        return self.row("overlap", lo, self.query.position, start, end, x_end=hi, y_end=self.query.position)

    def emit_span(self, span) -> None:
        start, end, lo, hi = span
        lo, hi = max(self.lo, lo), min(self.hi, hi)
        if lo <= hi:
            self.page.add(1, lambda _: self.span_row(start, end, lo, hi), overlaps=1)

    def intersections(self) -> None:
        pending = None
        segments = len(self.raw_x) - 1
        for start in range(0, segments, PROBE_CHUNK_SIZE):
            count = min(PROBE_CHUNK_SIZE, segments - start)
            before = max(0, start - 1)
            offset = start - before
            x, _y, sy, finite = self.chunk(before, min(len(self.raw_x), start + count + 2))
            axis, other = (x, sy) if self.query.axis == "x" else (sy, x)
            a, b = axis[offset:offset + count], axis[offset + 1:offset + count + 1]
            points = other[offset:offset + count + 1]
            valid = finite[offset:offset + count] & finite[offset + 1:offset + count + 1]
            first, last = a == self.coordinate, b == self.coordinate
            overlap = valid & first & last
            edges = np.flatnonzero(np.diff(np.r_[False, overlap, False].astype(np.int8)))
            starts, ends = edges[::2], edges[1::2]
            if len(starts):
                cuts = np.column_stack((starts, ends)).ravel()
                low = np.minimum(np.minimum.reduceat(points, cuts)[::2], points[ends])
                high = np.maximum(np.maximum.reduceat(points, cuts)[::2], points[ends])
            else:
                low = high = np.array([], dtype=float)
            if pending is not None:
                if len(starts) and starts[0] == 0:
                    pending = (pending[0], start + int(ends[0]), min(pending[2], low[0]), max(pending[3], high[0]))
                    leading_end = int(ends[0])
                    starts, ends, low, high = starts[1:], ends[1:], low[1:], high[1:]
                    if leading_end == count and start + count < segments:
                        continue
                self.emit_span(pending)
                pending = None
            if len(starts) and ends[-1] == count and start + count < segments:
                pending = (start + int(starts[-1]), start + int(ends[-1]), float(low[-1]), float(high[-1]))
                starts, ends, low, high = starts[:-1], ends[:-1], low[:-1], high[:-1]

            previous_overlap = np.r_[bool(offset and finite[0] and finite[1] and axis[0] == self.coordinate and axis[1] == self.coordinate), overlap[:-1]]
            next_valid = np.zeros(count, dtype=bool)
            available = min(count, len(finite) - offset - 2)
            next_valid[:available] = finite[offset + 1:offset + available + 1] & finite[offset + 2:offset + available + 2]
            hit = valid & ~overlap & (np.minimum(a, b) <= self.coordinate) & (np.maximum(a, b) >= self.coordinate)
            hit &= ~(first & previous_overlap) & ~(last & next_valid)
            with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
                t = np.divide(self.coordinate - a, b - a, out=np.zeros(count), where=valid & ~overlap)
                repair = hit & (~np.isfinite(t) | ~np.isfinite(b - a))
                t[repair] = (self.coordinate / 2 - a[repair] / 2) / (b[repair] / 2 - a[repair] / 2)
                crossing = (1 - t) * points[:-1] + t * points[1:]
            hit &= np.isfinite(crossing) & (crossing >= self.lo) & (crossing <= self.hi)
            low, high = np.maximum(low, self.lo), np.minimum(high, self.hi)
            inside = low <= high
            starts, ends, low, high = starts[inside], ends[inside], low[inside], high[inside]
            span_at = np.zeros(count, dtype=bool)
            span_at[starts] = True
            indices = np.flatnonzero(hit | span_at)

            def row_at(k):
                index = int(indices[k])
                if span_at[index]:
                    run = int(np.searchsorted(starts, index))
                    return self.span_row(start + index, start + int(ends[run]), float(low[run]), float(high[run]))
                if first[index] or last[index]:
                    return self.sample_row(start + index + int(last[index]))
                opposite = self.other_value(float(crossing[index]))
                xv, yv = (self.query.position, opposite) if self.query.axis == "x" else (opposite, self.query.position)
                return self.row("interpolated", xv, yv, start + index, start + index + 1)

            self.page.add(len(indices), row_at, overlaps=len(starts))
        if pending is not None:
            self.emit_span(pending)


def query_probe(plot: PlotValue, request: dict | ProbeQuery, *, visible_lines: set[str] | None = None,
                visible_signals: set[str] | None = None, cancelled: Callable[[], bool] = lambda: False) -> dict:
    query = request if isinstance(request, ProbeQuery) else ProbeQuery.parse(request, logarithmic_y=plot.settings.logarithmic_y_axis)
    if visible_lines is None:
        visible_lines = {s.signal_id for i, s in enumerate(plot.signals) if plot.settings.line_styles[i % len(plot.settings.line_styles)]
                         and plot.settings.line_widths[i % len(plot.settings.line_widths)]}
    if visible_signals is None:
        visible_signals = visible_lines | {s.signal_id for i, s in enumerate(plot.signals) if plot.settings.marker_shapes[i % len(plot.settings.marker_shapes)]}
    page, counts = _Page(query.page), []
    outside = not query.ranges[query.axis][0] <= query.position <= query.ranges[query.axis][1]
    for signal in plot.signals:
        if signal.signal_id not in visible_signals:
            continue
        before = page.total
        status = "outside_view" if outside else "no_line" if query.method == "intersections" and signal.signal_id not in visible_lines else "ok"
        if status == "ok":
            scan = _SignalQuery(signal, query, page, plot.settings.logarithmic_y_axis, cancelled)
            if query.method == "nearest":
                scan.nearest()
            else:
                scan.intersections()
        counts.append({"signal": signal.signal_id, "count": page.total - before, "status": status})
    return {"axis": query.axis, "position": query.position, "method": query.method, "revision": query.revision,
            "page": query.page, "page_size": PROBE_PAGE_SIZE, "total": page.total, "overlaps": page.overlaps,
            "counts": counts, "rows": page.rows, "outside_view": outside}
