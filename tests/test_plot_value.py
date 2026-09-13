# Purpose: Prove immutable full-resolution plot transport, provenance and shared preview conversion.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_plot_value.py
from __future__ import annotations

import base64
import copy
from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from ea_node_editor.execution.signal_plot_renderer import (
    authored_initial_ranges, build_xy_figure, create_signal_plot, xy_mark_signal_ids,
)
from ea_node_editor.execution.solution_identity import canonical_digest
from ea_node_editor.nodes.bootstrap import build_builtin_registry
from ea_node_editor.runtime_contracts import (
    ArrayValue, DataTree, ImageValue, Interval1D, PlotProvenance, PlotSettings, GRAPH_DATA_TYPE_ID,
    PlotSignal, PlotValue, deserialize_runtime_value, serialize_runtime_value,
)
from ea_node_editor.runtime_contracts.durable_values import validate_durable_settled_outputs
from ea_node_editor.runtime_contracts.settled_results import SettledPortResult, settled_outputs_payload_size

ORIGIN = PlotProvenance("workspace", "signal", "run")
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGBgAAAABQABpfZFQAAAAABJRU5ErkJggg==")


@pytest.fixture(scope="module")
def catalog():
    return build_builtin_registry().data_types


def plot_value():
    signal = PlotSignal("signal-0", ArrayValue.from_numpy(np.arange(3.)), ArrayValue.from_numpy(np.arange(3.)))
    return PlotValue(ImageValue.from_png(PNG), (signal,), PlotSettings(), ORIGIN)


def test_plot_codec_catalog_conversion_and_pass_through_identity(catalog):
    plot = plot_value()
    assert catalog.require(plot.data_type_id).persistence == "never"
    assert catalog.compatibility(plot.data_type_id, "COREX.DataTypes.Image").status == "convertible"
    assert catalog.convert_typed_input(plot.data_type_id, "COREX.DataTypes.Image", plot) is plot.preview
    assert catalog.convert_typed_input(plot.data_type_id, GRAPH_DATA_TYPE_ID, plot) is plot
    tree = DataTree.from_item(plot)
    restored = deserialize_runtime_value(serialize_runtime_value(tree, catalog=catalog), catalog=catalog)
    assert restored == tree
    assert canonical_digest(restored) == canonical_digest(tree)
    with pytest.raises(FrozenInstanceError):
        plot.settings.width = 12
    with pytest.raises(ValueError):
        plot.signals[0].x.to_numpy().flags.writeable = True


def test_million_points_retained_and_home_is_independent_of_authored_ranges(monkeypatch):
    import ea_node_editor.execution.signal_plot_renderer as renderer

    source = np.sin(np.arange(1_000_000.) / 100)
    source[1200:1203] = np.nan
    plot, warnings = create_signal_plot({"values": source, "x_axis_interval": Interval1D(20., 30.)}, provenance=ORIGIN)
    assert plot.signals[0].y.shape == (1_000_000,)
    assert np.isnan(plot.signals[0].y.to_numpy()[1200:1203]).all()
    source[0] = 999
    assert plot.signals[0].y.to_numpy()[0] == 0
    assert any("reduced from 1000000" in warning for warning in warnings)
    captured = []
    axes = []
    original_line, original_axis = renderer.xy.line, renderer.xy.x_axis

    def line(x, y, **kwargs):
        captured.append((x, y))
        return original_line(x, y, **kwargs)

    def axis(**kwargs):
        axes.append(kwargs)
        return original_axis(**kwargs)

    monkeypatch.setattr(renderer.xy, "line", line)
    monkeypatch.setattr(renderer.xy, "x_axis", axis)
    figure = build_xy_figure(plot)
    assert figure is not None
    assert len(captured[0][0]) == 1_000_000
    assert axes[0]["bounds"] is None and axes[0]["domain"] is None
    assert authored_initial_ranges(plot) == {"x": (20., 30.), "y": None}
    assert xy_mark_signal_ids(plot) == ("signal-0", "signal-0")
    assert xy_mark_signal_ids(replace(plot, settings=replace(plot.settings, marker_shapes=(0,)))) == ("signal-0",)
    assert xy_mark_signal_ids(replace(plot, settings=replace(plot.settings, line_styles=(0,)))) == ("signal-0",)


def test_datetime_log_gaps_and_signatures_survive_range_only_update(catalog):
    source = pd.DataFrame({"time": pd.date_range("2024-01-01", periods=5000, freq="s", tz="Europe/Istanbul"), "y": np.arange(5000.)})
    plot, _ = create_signal_plot({"values": source, "logarithmic_y_axis": True, "x_datetime_start": "2023-12-31T21:00:10Z"}, provenance=ORIGIN)
    assert plot.signals[0].x_kind == "datetime"
    assert plot.signals[0].x.shape == (5000,)
    assert np.isnan(plot.signals[0].y.to_numpy()[0])
    assert authored_initial_ranges(plot)["x"][0] == 1704056410000.
    restored = deserialize_runtime_value(serialize_runtime_value(plot, catalog=catalog), catalog=catalog)
    assert restored == plot
    changed = replace(plot, settings=replace(plot.settings, x_bounds=None, y_bounds=(1., 10.)), provenance=replace(ORIGIN, run_id="later"))
    assert changed.data_signature == plot.data_signature
    assert changed.render_signature == plot.render_signature
    assert changed.settings_signature != plot.settings_signature
    assert changed.value_signature != plot.value_signature
    external = replace(plot, settings=replace(plot.settings, title="changed"))
    assert external.render_signature != plot.render_signature


@pytest.mark.parametrize("mutation", [
    lambda p: p.update(version=True),
    lambda p: p.update(callback="eval()"),
    lambda p: p["settings"].update(html="<script>"),
    lambda p: p["settings"].update(width="600"),
    lambda p: p["settings"].update(y_bounds=[0., 0.]),
    lambda p: p["signals"][0]["x"]["array"].update(shape=[999]),
    lambda p: p["signals"][0]["y"]["array"].update(dtype="|O"),
    lambda p: p["provenance"].update(node_id=""),
    lambda p: p.update(preview="not an image"),
])
def test_malformed_plot_payloads_are_rejected(catalog, mutation):
    payload = serialize_runtime_value(plot_value(), catalog=catalog)
    mutation(payload)
    with pytest.raises((ValueError, TypeError)):
        deserialize_runtime_value(payload, catalog=catalog)


def test_plot_transport_preflights_shared_scientific_limits(catalog, monkeypatch):
    from ea_node_editor.runtime_contracts import scientific_values
    import ea_node_editor.runtime_contracts.scientific_codec as codec

    plot = plot_value()
    payload = serialize_runtime_value(plot, catalog=catalog)
    monkeypatch.setattr(scientific_values, "SCIENTIFIC_VALUE_MAX_BYTES", plot.nbytes - 1)
    with pytest.raises(ValueError, match="limit"):
        replace(plot)
    monkeypatch.setattr(codec, "_decode", lambda _: pytest.fail("allocated before preflight"))
    with pytest.raises(ValueError, match="limit"):
        deserialize_runtime_value(payload, catalog=catalog)
    monkeypatch.setattr(scientific_values, "SCIENTIFIC_VALUE_MAX_BYTES", plot.nbytes * 2)
    monkeypatch.setattr(scientific_values, "SCIENTIFIC_OPERATION_MAX_BYTES", plot.nbytes * 2 - 1)
    with pytest.raises(ValueError, match="cumulative"):
        deserialize_runtime_value([payload, copy.deepcopy(payload)], catalog=catalog)


@pytest.mark.parametrize("metadata", ["signal_label", "signal_id", "settings", "provenance"])
def test_plot_metadata_counts_toward_native_and_predecode_budgets(catalog, monkeypatch, metadata):
    from ea_node_editor.runtime_contracts import scientific_values
    from ea_node_editor.runtime_contracts.plot_codec import plot_payload_size
    import ea_node_editor.runtime_contracts.scientific_codec as codec

    plot = plot_value()
    text = "\N{LATIN SMALL LETTER E WITH ACUTE}" * 2048
    if metadata == "signal_label":
        plot = replace(plot, signals=(replace(plot.signals[0], label=text),))
    elif metadata == "signal_id":
        plot = replace(plot, signals=(replace(plot.signals[0], signal_id=text),))
    elif metadata == "settings":
        plot = replace(plot, settings=replace(plot.settings, title=text))
    else:
        plot = replace(plot, provenance=replace(plot.provenance, run_id=text))
    payload = serialize_runtime_value(plot, catalog=catalog)
    assert plot.nbytes > 4096
    assert plot_payload_size(payload) == plot.nbytes
    monkeypatch.setattr(scientific_values, "SCIENTIFIC_VALUE_MAX_BYTES", 1024)
    with pytest.raises(ValueError, match="limit"):
        replace(plot)
    with pytest.raises(ValueError, match="limit"):
        serialize_runtime_value(plot, catalog=catalog)
    monkeypatch.setattr(codec, "_decode", lambda _: pytest.fail("allocated before metadata preflight"))
    with pytest.raises(ValueError, match="limit"):
        deserialize_runtime_value(payload, catalog=catalog)
    monkeypatch.setattr(scientific_values, "SCIENTIFIC_VALUE_MAX_BYTES", plot.nbytes)
    monkeypatch.setattr(scientific_values, "SCIENTIFIC_OPERATION_MAX_BYTES", plot.nbytes * 2 - 1)
    with pytest.raises(ValueError, match="cumulative"):
        serialize_runtime_value([plot, plot], catalog=catalog)
    with pytest.raises(ValueError, match="cumulative"):
        deserialize_runtime_value([payload, payload], catalog=catalog)


def test_plot_is_session_transport_eligible_but_durable_ineligible(catalog):
    plot = plot_value()
    outputs = {"image": SettledPortResult("value", DataTree.from_item(plot))}
    assert settled_outputs_payload_size(outputs, catalog=catalog) < 64 * 1024 * 1024
    for declared in (plot.data_type_id, GRAPH_DATA_TYPE_ID):
        descriptor = SimpleNamespace(port_key="image", status="value", data_type_id=declared, concrete_data_type_ids=(plot.data_type_id,))
        validation = validate_durable_settled_outputs(outputs, (descriptor,), catalog, None)
        assert not validation.eligible and validation.reason_code == "durable_value_ineligible"


def test_plot_native_and_tagged_values_cannot_be_saved_as_project_properties(catalog):
    from ea_node_editor.graph.model import GraphModel
    from ea_node_editor.nodes.bootstrap import build_default_registry
    from ea_node_editor.persistence.serializer import JsonProjectSerializer

    serializer = JsonProjectSerializer(build_default_registry())
    plot = plot_value()
    for value in (plot, serialize_runtime_value(plot, catalog=catalog)):
        model = GraphModel()
        model.add_node(model.active_workspace.workspace_id, "plot.signal", "Plot", 0., 0., properties={"inspection_data": value})
        with pytest.raises((TypeError, ValueError)):
            serializer.to_persistent_document(model.project)


def test_signal_plot_process_export_and_session_reuse(tmp_path):
    from ea_node_editor.execution.runtime import CorexRuntime
    from ea_node_editor.execution.runtime_requests import ExecutionRequest
    from ea_node_editor.execution.runtime_snapshot import build_runtime_snapshot
    from ea_node_editor.graph.model import GraphModel
    from ea_node_editor.nodes.bootstrap import build_default_registry
    from scripts.benchmark_signal_plot import settled_item, wait_for_runtime_idle

    registry = build_default_registry(include_public_plugins=False)
    model = GraphModel()
    workspace_id = model.active_workspace.workspace_id
    mutation = model.validated_mutations(workspace_id, registry)
    source = mutation.add_node(type_id="data.panel", title="Samples", x=0, y=0,
                               properties={"mode": 1, "value": "1\n2\n4", "interpretation": "number"})
    plot = mutation.add_node(type_id="plot.signal", title="Plot", x=300, y=0)
    export = mutation.add_node(type_id="io.image_export", title="Export", x=600, y=0,
                               properties={"path": str(tmp_path / "preview.png"), "overwrite": True})
    mutation.add_edge(source_node_id=source.node_id, source_port_key="output", target_node_id=plot.node_id, target_port_key="values")
    mutation.add_edge(source_node_id=plot.node_id, source_port_key="image", target_node_id=export.node_id, target_port_key="image")
    snapshot = build_runtime_snapshot(model.project, workspace_id=workspace_id, registry=registry)
    runtime = CorexRuntime(registry=registry)
    try:
        request = ExecutionRequest(workspace_id=workspace_id, runtime_snapshot=snapshot)
        first = runtime.run(request, timeout=60)
        assert first.status == "completed", (first.error, first.traceback)
        settled = {e["node_id"]: e for e in first.events if e.get("type") == "node_settled"}
        value = settled_item(settled[plot.node_id], "image", registry.data_types)
        assert type(value) is PlotValue
        assert value.provenance.workspace_id == workspace_id and value.provenance.node_id == plot.node_id
        assert (tmp_path / "preview.png").read_bytes() == value.preview.encoded_bytes
        wait_for_runtime_idle(runtime)
        second = runtime.run(request, timeout=60)
        assert second.status == "completed", (second.error, second.traceback)
        settled = {e["node_id"]: e for e in second.events if e.get("type") == "node_settled"}
        assert settled[plot.node_id]["decision_reason"] == "reusable_record_accepted"
        assert settled_item(settled[plot.node_id], "image", registry.data_types) == value
    finally:
        runtime.shutdown()
