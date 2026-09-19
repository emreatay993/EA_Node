# Purpose: Prove the backend-neutral Plot render-request transport contract.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_plot_render_request.py
from __future__ import annotations

from ea_node_editor.execution.plot_backend import (
    PlotRenderRequest, plot_render_request_from_payload, plot_render_request_to_payload,
)


def test_plot_render_request_payload_helpers_are_json_safe() -> None:
    request = PlotRenderRequest(
        plot_type="line",
        series=({"label": "tuple", "x": (0, 1), "y": (2.0, 3.0)},),
        title="Tuple Series",
        x_label="x",
        y_label="y",
        options={"axis_limits": {"x": (None, 10)}, "markers": ("a", "b")},
    )

    payload = plot_render_request_to_payload(request)

    assert payload == {
        "plot_type": "line",
        "series": [{"label": "tuple", "x": [0, 1], "y": [2.0, 3.0]}],
        "title": "Tuple Series",
        "x_label": "x",
        "y_label": "y",
        "options": {"axis_limits": {"x": [None, 10]}, "markers": ["a", "b"]},
    }
    restored = plot_render_request_from_payload(payload)
    assert restored.series == ({"label": "tuple", "x": [0, 1], "y": [2.0, 3.0]},)
    assert restored.options["axis_limits"] == {"x": [None, 10]}
