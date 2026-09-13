# Purpose: Verify full-data worker inspection and bounded plot transport.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_xy_plot_transport.py
from dataclasses import replace
import json
import threading
from types import SimpleNamespace

import numpy as np
import pytest

from ea_node_editor.runtime_contracts import ArrayValue, PlotSignal
from ea_node_editor.web_host.xy_transport import (
    MAX_MESSAGE_BYTES, XYPlotWorker, decode_request, normalized_view_state, selection_summary,
)
from tests.test_plot_value import plot_value


def test_selection_uses_full_canonical_data_and_deduplicates_marks():
    plot = plot_value()
    result = selection_summary(plot, ("signal-0", "signal-0"), SimpleNamespace(per_trace={
        0: np.array([0, 1]), 1: np.array([1, 2]),
    }))
    assert result["count"] == 3
    assert [row["index"] for row in result["rows"]] == [0, 1, 2]
    assert result["signals"][0]["y_mean"] == 1


def test_authored_labels_match_chart_in_hover_statistics_and_rows():
    plot = plot_value()
    plot = replace(plot, signals=(replace(plot.signals[0], label="source column"),),
                   settings=replace(plot.settings, labels=("Stress",)))
    result = selection_summary(plot, ("signal-0",), SimpleNamespace(per_trace={0: np.array([0, 1])}))
    assert result["signals"][0]["label"] == "Stress"
    assert result["rows"][0]["label"] == "Stress"
    worker = XYPlotWorker(plot, "session", threading.Event())
    worker.mark_ids = ("signal-0",)
    assert worker._hover({"trace": 0, "index": 0, "x": 0, "y": 0})["label"] == "Stress"


@pytest.mark.parametrize("state", [None, {"ranges": []}, {"ranges": {"z": [1, 2]}},
    {"ranges": {"x": [2, 1]}}, {"ranges": {"x": [0, float('inf')]}},
    {"selection": {"polygon": [[0, 0]] * 4097}}, {"selection": {"rows": True}}])
def test_view_state_rejects_invalid_or_unbounded_geometry(state):
    with pytest.raises(ValueError):
        normalized_view_state(state)


def test_request_limit_and_finite_dimensions():
    for raw in [' ' * (MAX_MESSAGE_BYTES + 1), '{"message":{"px":999999999}}', '{"value":NaN}']:
        with pytest.raises(ValueError):
            decode_request(raw)
    with pytest.raises(ValueError, match="geometry limit"):
        decode_request(json.dumps({"kind": "message", "message": {
            "type": "select_polygon", "points": [[0, 0]] * 2049,
        }}))
    for axes in (None, [{}], ["z"], ["x", "y", "x"]):
        with pytest.raises(ValueError):
            decode_request(json.dumps({"kind": "flush", "state": {}, "changed_axes": axes}))


@pytest.mark.parametrize("mode", ["x", "y"])
def test_native_axis_selection_geometry_is_preserved(mode):
    state = {"ranges": {}, "selection": {"range": {"x0": 0, "x1": 1, "y0": 0, "y1": 1, "mode": mode}}}
    assert normalized_view_state(state) == state


def test_worker_million_point_query_generation_and_flush_order():
    x = np.arange(1_000_000.)
    plot = replace(plot_value(), signals=(PlotSignal("signal-0", ArrayValue.from_numpy(x), ArrayValue.from_numpy(x)),))
    worker = XYPlotWorker(plot, "session", threading.Event())
    events = []
    worker.outbound.connect(lambda raw: events.append(json.loads(raw)))
    worker.receive(json.dumps({"session": "session", "kind": "initialize"}))
    assert events[-1]["kind"] == "mount"
    assert worker.figure.traces[0].n_points == 1_000_000
    worker.receive(json.dumps({"session": "old", "kind": "message", "message": {"type": "select", "x0": 900000, "x1": 999999, "y0": 900000, "y1": 999999}}))
    assert len(events) == 1
    worker.receive(json.dumps({"session": "session", "kind": "message", "message": {"type": "select", "x0": 900000, "x1": 999999, "y0": 900000, "y1": 999999}}))
    result = next(event["value"] for event in events if event["kind"] == "selection")
    assert result["count"] == 100_000
    assert len(result["rows"]) == 8
    assert result["signals"][0]["y_mean"] == 949999.5
    worker.receive(json.dumps({"session": "session", "kind": "flush", "state": {"ranges": {"x": [1, 2]}}}))
    assert events[-1]["kind"] == "flushed"
    worker.cancelled.set()
    worker.receive(json.dumps({"session": "session", "kind": "initialize"}))
    assert events[-1]["kind"] == "flushed"
