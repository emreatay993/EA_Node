# Purpose: Own the bounded data-only XY transport and worker-side figures.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_xy_plot_transport.py
from __future__ import annotations

import base64
import json
import math
import threading
from typing import Any

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

from ea_node_editor.runtime_contracts import PlotValue
from ea_node_editor.runtime_contracts.scientific_values import SCIENTIFIC_OPERATION_MAX_BYTES
from ea_node_editor.web_host.xy_probe_contract import normalized_probe_state, probe_metadata, signal_label

MAX_MESSAGE_BYTES = 1024 * 1024
MAX_POLYGON_POINTS = 2048
PREVIEW_ROWS = 8


def normalized_view_state(value: object) -> dict[str, Any]:
    """Allow only bounded ranges and selection geometry across the host boundary."""
    if not isinstance(value, dict):
        raise ValueError("Plot view state must be an object")
    result: dict[str, Any] = {"ranges": {}, "selection": None}
    ranges = value.get("ranges", {})
    if not isinstance(ranges, dict):
        raise ValueError("Plot ranges must be an object")
    for axis, bounds in ranges.items():
        if axis not in {"x", "y"} or not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
            raise ValueError("Invalid plot axis range")
        if any(type(n) not in {int, float} or not math.isfinite(n) for n in bounds) or bounds[0] >= bounds[1]:
            raise ValueError("Plot ranges require finite increasing endpoints")
        result["ranges"][axis] = list(bounds)
    selection = value.get("selection")
    if selection is not None:
        if not isinstance(selection, dict):
            raise ValueError("Invalid plot selection")
        if "polygon" in selection:
            polygon = selection["polygon"]
            if not isinstance(polygon, list) or not 3 <= len(polygon) <= MAX_POLYGON_POINTS:
                raise ValueError("Plot selection exceeds the geometry limit")
            if any(not isinstance(p, (list, tuple)) or len(p) != 2 or
                   any(type(n) not in {int, float} or not math.isfinite(n) for n in p) for p in polygon):
                raise ValueError("Plot selection needs finite coordinate pairs")
            result["selection"] = {"polygon": [list(p) for p in polygon]}
        elif "range" in selection:
            bounds = selection["range"]
            if not isinstance(bounds, dict) or set(bounds) - {"mode"} != {"x0", "x1", "y0", "y1"}:
                raise ValueError("Invalid plot selection range")
            if "mode" in bounds and (type(bounds["mode"]) is not str or bounds["mode"] not in {"x", "y"}):
                raise ValueError("Plot selection mode must be X or Y")
            if any(type(bounds[key]) not in {int, float} or not math.isfinite(bounds[key]) for key in ("x0", "x1", "y0", "y1")):
                raise ValueError("Plot selection range must be finite")
            result["selection"] = {"range": dict(bounds)}
        else:
            raise ValueError("Unsupported plot selection geometry")
    return result


def decode_request(raw: str) -> dict[str, Any]:
    if type(raw) is not str or len(raw) > MAX_MESSAGE_BYTES or len(raw.encode("utf-8")) > MAX_MESSAGE_BYTES:
        raise ValueError("Plot request exceeds the 1 MiB transport limit")
    request = json.loads(raw, parse_constant=lambda text: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))
    if not isinstance(request, dict):
        raise ValueError("Plot request must be an object")
    if request.get("kind") == "flush":
        normalized_view_state(request.get("state", {}))
        normalized_probe_state(request.get("probe_state"))
        for key in ("changed_axes", "automatic"):
            normalized_axes(request.get(key, []))
    message = request.get("message")
    if message is not None:
        if not isinstance(message, dict):
            raise ValueError("Plot message must be an object")
        polygon = message.get("points") if message.get("type") == "select_polygon" else message.get("polygon")
        if polygon is not None:
            normalized_view_state({"selection": {"polygon": polygon}})
        # Bound computational viewport requests before passing to XY.
        for key in ("px", "w", "h"):
            if key in message and (type(message[key]) not in {int, float} or not 1 <= message[key] <= 16384):
                raise ValueError("Plot viewport dimensions are outside transport limits")
    return request


def normalized_axes(value: object) -> set[str]:
    if not isinstance(value, list) or len(value) > 2 or any(type(axis) is not str or axis not in {"x", "y"} for axis in value):
        raise ValueError("Plot changed axes must be a list containing only X/Y axes")
    return set(value)


def pack_buffers(buffers: Any) -> list[str]:
    values = buffers or []
    if sum(memoryview(buffer).nbytes for buffer in values) > SCIENTIFIC_OPERATION_MAX_BYTES:
        raise ValueError("Plot display buffers exceed the scientific transport limit")
    return [base64.b64encode(memoryview(buffer)).decode("ascii") for buffer in values]


def selection_summary(plot: PlotValue, mark_ids: tuple[str, ...], selection: Any) -> dict[str, Any]:
    """Deduplicate canonical sample indices across representations of a signal."""
    import numpy as np

    grouped: dict[str, list[Any]] = {}
    for trace, indices in selection.per_trace.items():
        if 0 <= trace < len(mark_ids):
            grouped.setdefault(mark_ids[trace], []).append(indices)
    rows, summaries = [], []
    total = 0
    for signal_number, signal in enumerate(plot.signals, 1):
        parts = grouped.get(signal.signal_id)
        if not parts:
            continue
        indices = np.unique(np.concatenate(parts))
        indices = indices[(indices >= 0) & (indices < signal.x.shape[0])]
        x, y = signal.x.to_numpy()[indices], signal.y.to_numpy()[indices]
        finite = np.isfinite(x) & np.isfinite(y)
        x, y, indices = x[finite], y[finite], indices[finite]
        count = len(indices)
        if not count:
            continue
        total += count
        label = signal_label(plot, signal_number - 1)
        summaries.append({"signal": signal.signal_id, "label": label, "count": count,
                          "y_mean": float(np.mean(y)), "y_min": float(np.min(y)), "y_max": float(np.max(y))})
        for index, xv, yv in zip(indices[:max(0, PREVIEW_ROWS-len(rows))], x, y):
            rows.append({"signal": signal.signal_id, "label": label, "index": int(index),
                         "x": str(xv) + "Z" if signal.x_kind == "datetime" else float(xv), "y": float(yv)})
    return {"count": total, "signals": summaries, "rows": rows, "preview_limit": PREVIEW_ROWS}


class XYPlotWorker(QObject):
    outbound = pyqtSignal(str)
    processed = pyqtSignal()

    def __init__(self, plot: PlotValue, session_id: str, cancelled: threading.Event) -> None:
        super().__init__()
        self.plot: PlotValue | None = plot
        self.session_id = session_id
        self.cancelled = cancelled
        self.figure = None
        self.mark_ids = ()
        self.probe_metadata = None
        self.hidden_marks: set[int] = set()

    def emit_event(self, kind: str, **values: Any) -> None:
        if not self.cancelled.is_set():
            self.outbound.emit(json.dumps({"session": self.session_id, "kind": kind, **values}, allow_nan=False))

    @pyqtSlot(str)
    def receive(self, raw: str) -> None:
        try:
            if self.cancelled.is_set():
                return
            request = decode_request(raw)
            if request.get("session") != self.session_id:
                return
            kind = request.get("kind")
            if kind == "initialize":
                if self.figure is not None:
                    return
                from ea_node_editor.execution.signal_plot_renderer import build_xy_figure, xy_mark_signal_ids
                self.mark_ids = xy_mark_signal_ids(self.plot)
                self.figure = build_xy_figure(self.plot)
                self.figure.height = "100%"
                spec, buffers = self.figure.build_payload_split()
                spec["interaction"] = {**spec.get("interaction", {}), "_transport_view_change": True}
                self.probe_metadata = probe_metadata(self.plot, self.mark_ids, [trace.kind for trace in self.figure.traces])
                self.emit_event("mount", spec=spec, buffers=pack_buffers(buffers), probe_metadata=self.probe_metadata)
            elif kind == "message" and self.figure is not None:
                from xy.channel import ChannelCallbacks, handle_message

                reply = handle_message(self.figure, request["message"], callbacks=ChannelCallbacks(
                    on_hover=lambda row: self.emit_event("hover", value=self._hover(row)),
                    on_select=lambda selection: self.emit_event("selection", value=selection_summary(self.plot, self.mark_ids, selection)),
                    on_view_change=lambda view: self.emit_event("view", value=view),
                ))
                if reply is not None:
                    message, buffers = reply
                    self.emit_event("reply", message=message, buffers=pack_buffers(buffers))
                message = request["message"]
                if message.get("type") == "legend_toggle" and message.get("category") is None:
                    trace, hidden = message.get("trace"), message.get("hidden")
                    if type(trace) is int and 0 <= trace < len(self.mark_ids) and type(hidden) is bool:
                        if hidden:
                            self.hidden_marks.add(trace)
                        else:
                            self.hidden_marks.discard(trace)
            elif kind == "probe_query" and self.figure is not None:
                from ea_node_editor.web_host.xy_probes import ProbeCancelled, query_probe
                marks = [mark for mark in self.probe_metadata["marks"] if mark["id"] not in self.hidden_marks]
                try:
                    result = query_probe(self.plot, request,
                        visible_lines={mark["signal"] for mark in marks if mark["kind"] == "line"},
                        visible_signals={mark["signal"] for mark in marks}, cancelled=self.cancelled.is_set)
                    self.emit_event("probe_result", value=result)
                except ProbeCancelled:
                    return
                except (ValueError, OverflowError) as error:
                    self.emit_event("probe_error", revision=request.get("revision"), message=str(error))
            elif kind == "flush":
                self.emit_event("flushed", state=normalized_view_state(request.get("state", {})),
                                changed_axes=request.get("changed_axes", []), automatic=request.get("automatic", []),
                                probe_state=normalized_probe_state(request.get("probe_state"),
                                    logarithmic_y=self.plot.settings.logarithmic_y_axis))
        except Exception as error:  # boundary: report failures, never paint a stale figure
            self.emit_event("error", message=f"{type(error).__name__}: {error}")
        finally:
            self.processed.emit()

    def _hover(self, row: dict[str, Any]) -> dict[str, Any]:
        row = dict(row)
        trace = row.get("trace")
        if type(trace) is int and 0 <= trace < len(self.mark_ids):
            row["signal"] = self.mark_ids[trace]
            for number, signal in enumerate(self.plot.signals, 1):
                if signal.signal_id == row["signal"]:
                    row["label"] = signal_label(self.plot, number - 1)
                    if signal.x_kind == "datetime" and type(row.get("index")) is int:
                        row["x"] = str(signal.x.to_numpy()[row["index"]]) + "Z"
                    break
        return row

    @pyqtSlot()
    def stop(self) -> None:
        self.figure = None
        self.plot = None
        QThread.currentThread().quit()
