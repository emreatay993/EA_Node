# Purpose: Prove generic Plot source preparation, provenance, diagnostics, and request composition.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_generic_plot_preparation.py
from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from ea_node_editor.addons.property_edit_adapters import PropertyEditAdapterContext
from ea_node_editor.addons.tabular_data import loader_cache_service as loaders
from ea_node_editor.addons.tabular_data.input_node import (
    TABULAR_DATA_ARRAY_OUTPUT_KEY, TABULAR_DATA_TABLE_OUTPUT_KEY,
    TABULAR_SELECTED_COLUMNS_PROPERTY, execute_tabular_input,
)
from ea_node_editor.addons.tabular_data.extraction_nodes import (
    TABULAR_ARRAY_SLICE_2D_OUTPUT_KEY, TABULAR_WINDOW_OUTPUT_KEY,
    execute_array_slice_2d, execute_table_filter,
)
from ea_node_editor.execution import plot_backend
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.nodes.builtins.plot import generic, specs
from ea_node_editor.nodes.builtins.plot.generic import build_generic_plot_render_request
from ea_node_editor.nodes.builtins.plot.property_edit_adapter import PlotPropertyEditAdapter
from ea_node_editor.runtime_contracts import TabularWindowRef
from tests.generic_plot_fixtures import _execution_context, _generic_render_request, _tabular_input_context


def _core_series(render_request) -> tuple[dict, ...]:
    """Series payloads minus the decimation/source bookkeeping keys."""
    stripped = []
    for item in render_request.series:
        clean = {key: value for key, value in item.items() if key not in {"decimation", "source_ref"}}
        stripped.append(clean)
    return tuple(stripped)



def test_generic_plot_request_builder_handles_dict_of_arrays_without_numpy_dependency() -> None:
    registry = build_default_registry()
    plugin = registry.create("plot.bar")
    properties = registry.normalize_properties(
        "plot.bar",
        {
            "title": "Packet Line",
            "x_label": "time",
            "y_label": "value",
            "grid": False,
            "legend": True,
        },
    )

    result = plugin.execute(
        _execution_context(
            inputs={"series": {"label": "sample", "x": [0, 1, 2], "y": [1.0, 2.5, 4.0]}},
            properties=properties,
        )
    )

    assert result.outputs == {}
    render_request, warnings = build_generic_plot_render_request(
        node_type_id="plot.bar",
        properties=properties,
        series_input={"label": "sample", "x": [0, 1, 2], "y": [1.0, 2.5, 4.0]},
    )
    assert warnings == ()
    assert render_request.plot_type == "bar"
    assert render_request.title == "Packet Line"
    assert render_request.x_label == "time"
    assert render_request.y_label == "value"
    assert render_request.series == ({"label": "sample", "x": [0, 1, 2], "y": [1.0, 2.5, 4.0]},)
    assert render_request.options["grid"] is False
    assert "import numpy" not in inspect.getsource(plot_backend)



def test_generic_plot_request_preserves_live_investigation_options_when_present() -> None:
    render_request = _generic_render_request(
        series_input={"label": "sample", "x": [0, 1], "y": [1.0, 2.0]},
        properties={
            "plot_options": {
                "plot_theme": "dark",
                "hover_readout": True,
                "vertical_guide": True,
                "crosshair": False,
            }
        },
    )

    assert render_request.options["plot_theme"] == "dark"
    assert render_request.options["hover_readout"] is True
    assert render_request.options["vertical_guide"] is True
    assert render_request.options["crosshair"] is False

    legacy_request = _generic_render_request(
        series_input={"label": "sample", "x": [0, 1], "y": [1.0, 2.0]},
    )
    for option_key in ("plot_theme", "hover_readout", "vertical_guide", "crosshair"):
        assert option_key not in legacy_request.options



def test_generic_bar_plot_materializes_selected_tabular_columns(tmp_path: Path) -> None:
    source = tmp_path / "weather.csv"
    source.write_text("time,temp,pressure\n0,21.5,100.0\n1,22.0,101.5\n", encoding="utf-8")
    tabular_result = execute_tabular_input(
        _tabular_input_context(source, **{TABULAR_SELECTED_COLUMNS_PROPERTY: ["time", "temp"]})
    )
    ref = tabular_result.outputs[TABULAR_DATA_TABLE_OUTPUT_KEY]

    render_request = _generic_render_request(
        series_input=ref, properties={"tabular_mapping": {"x": "time", "y": ["temp"]}}
    )
    assert _core_series(render_request) == (
        {
            "label": "temp",
            "x": [0, 1],
            "y": [21.5, 22],
            "x_column": "time",
            "y_column": "temp",
        },
    )
    decimation = render_request.series[0]["decimation"]
    assert decimation == {"method": "none", "original_rows": 2, "points": 2}
    assert render_request.series[0]["source_ref"]["ref"]["ref_id"] == ref.ref_id



def test_generic_bar_plot_materializes_table_window_ref(tmp_path: Path) -> None:
    source = tmp_path / "weather.csv"
    source.write_text(
        "Time_s,Accel_g,Pressure\n0,-2.0,100\n0.01,-1.4,101\n0.02,-1.8,102\n",
        encoding="utf-8",
    )
    table_ref = execute_tabular_input(
        _tabular_input_context(source)
    ).outputs[TABULAR_DATA_TABLE_OUTPUT_KEY]
    window_ref = execute_table_filter(
        _execution_context(
            inputs={"table_data": table_ref},
            properties={"row_offset": 1, "row_limit": 2, "columns": "Time_s, Accel_g"},
        )
    ).outputs[TABULAR_WINDOW_OUTPUT_KEY]

    render_request = _generic_render_request(
        series_input=window_ref,
        properties={"tabular_mapping": {"x": "Time_s", "y": ["Accel_g"]}},
    )

    assert _core_series(render_request) == (
        {
            "label": "Accel_g",
            "x": [0.01, 0.02],
            "y": [-1.4, -1.8],
            "x_column": "Time_s",
            "y_column": "Accel_g",
        },
    )



def test_generic_histogram_plot_auto_ignores_text_columns(tmp_path: Path) -> None:
    source = tmp_path / "weather.csv"
    source.write_text("station,temp,pressure\nA,21.5,100.0\nB,22.0,101.5\n", encoding="utf-8")
    ref = execute_tabular_input(_tabular_input_context(source)).outputs[TABULAR_DATA_TABLE_OUTPUT_KEY]

    render_request = _generic_render_request(type_id="plot.histogram", series_input=ref)
    assert _core_series(render_request) == (
        {"label": "temp", "values": [21.5, 22], "value_column": "temp"},
        {"label": "pressure", "values": [100, 101.5], "value_column": "pressure"},
    )



def test_generic_bar_plot_reports_unknown_tabular_mapping_column(tmp_path: Path) -> None:
    source = tmp_path / "weather.csv"
    source.write_text("time,temp\n0,21.5\n1,22.0\n", encoding="utf-8")
    ref = execute_tabular_input(_tabular_input_context(source)).outputs[TABULAR_DATA_TABLE_OUTPUT_KEY]
    registry = build_default_registry()
    plugin = registry.create("plot.bar")
    properties = registry.normalize_properties(
        "plot.bar",
        {"tabular_mapping": {"x": "time", "y": ["temperature"]}},
    )

    with pytest.raises(ValueError) as excinfo:
        plugin.execute(_execution_context(inputs={"series": ref}, properties=properties))

    message = str(excinfo.value)
    assert "tabular_mapping.y" in message
    assert "'temperature'" in message
    assert "Loaded columns: 'time', 'temp'." in message
    assert "Header Row" in message



def test_generic_bar_plot_reports_generated_headers_when_header_row_is_disabled(
    tmp_path: Path,
) -> None:
    source = tmp_path / "weather.csv"
    source.write_text("time,temp\n0,21.5\n1,22.0\n", encoding="utf-8")
    ref = execute_tabular_input(
        _tabular_input_context(source, header_row=None)
    ).outputs[TABULAR_DATA_TABLE_OUTPUT_KEY]
    registry = build_default_registry()
    plugin = registry.create("plot.bar")

    with pytest.raises(ValueError) as excinfo:
        plugin.execute(_execution_context(inputs={"series": ref}))

    message = str(excinfo.value)
    assert "needs numeric columns" in message
    assert "Loaded columns: 'column_1', 'column_2'." in message
    assert "Header Row" in message



def test_generic_bar_plot_reports_empty_tabular_input(tmp_path: Path) -> None:
    source = tmp_path / "weather.csv"
    source.write_text("time,temp\n", encoding="utf-8")
    ref = execute_tabular_input(_tabular_input_context(source)).outputs[TABULAR_DATA_TABLE_OUTPUT_KEY]
    registry = build_default_registry()
    plugin = registry.create("plot.bar")

    with pytest.raises(ValueError) as excinfo:
        plugin.execute(_execution_context(inputs={"series": ref}))

    message = str(excinfo.value)
    assert "has no data rows after parsing" in message
    assert "Loaded columns: 'time', 'temp'." in message
    assert "Skip Rows" in message



def test_generic_heatmap_plot_materializes_numeric_tabular_grid(tmp_path: Path) -> None:
    source = tmp_path / "grid.csv"
    source.write_text("a,b,c\n1,2,3\n4,5,6\n", encoding="utf-8")
    ref = execute_tabular_input(
        _tabular_input_context(source, **{TABULAR_SELECTED_COLUMNS_PROPERTY: ["a", "b", "c"]})
    ).outputs[TABULAR_DATA_TABLE_OUTPUT_KEY]

    render_request = _generic_render_request(type_id="plot.heatmap", series_input=ref)
    assert _core_series(render_request) == (
        {"label": "tabular grid", "values": [[1, 2, 3], [4, 5, 6]], "columns": ["a", "b", "c"]},
    )



def test_generic_point_cloud_plot_infers_named_xyz_tabular_columns(tmp_path: Path) -> None:
    source = tmp_path / "points.csv"
    source.write_text("name,x,y,z\np1,1,2,3\np2,4,5,6\n", encoding="utf-8")
    ref = execute_tabular_input(_tabular_input_context(source)).outputs[TABULAR_DATA_TABLE_OUTPUT_KEY]

    render_request = _generic_render_request(type_id="plot.point_cloud", series_input=ref)
    assert _core_series(render_request) == (
        {"label": "tabular point cloud", "points": [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], "columns": ["x", "y", "z"]},
    )



def test_generic_streamlines_plot_reports_missing_xyz_mapping(tmp_path: Path) -> None:
    source = tmp_path / "points.csv"
    source.write_text("x,y\n1,2\n3,4\n", encoding="utf-8")
    ref = execute_tabular_input(_tabular_input_context(source)).outputs[TABULAR_DATA_TABLE_OUTPUT_KEY]
    registry = build_default_registry()
    plugin = registry.create("plot.streamlines")

    with pytest.raises(ValueError, match="Streamline auto tabular plotting requires"):
        plugin.execute(_execution_context(inputs={"series": ref}))



def test_generic_bar_plot_materializes_array_ref_slice(tmp_path: Path) -> None:
    numpy = pytest.importorskip("numpy")
    source = tmp_path / "points.npy"
    numpy.save(source, numpy.array([[1.0, 2.0], [3.0, 4.0]]))
    ref = execute_tabular_input(_tabular_input_context(source)).outputs[TABULAR_DATA_ARRAY_OUTPUT_KEY]

    render_request = _generic_render_request(type_id="plot.bar", series_input=ref)
    assert _core_series(render_request) == (
        {"label": "column_1", "values": [1.0, 3.0]},
        {"label": "column_2", "values": [2.0, 4.0]},
    )
    assert render_request.series[0]["decimation"] == {"method": "none", "original_rows": 2, "points": 2}
    assert render_request.series[0]["source_ref"]["kind"] == "array_ref"
    assert render_request.series[0]["source_ref"]["ref"]["ref_id"] == ref.ref_id



def test_generic_bar_plot_materializes_array_slice_ref(tmp_path: Path) -> None:
    numpy = pytest.importorskip("numpy")
    source = tmp_path / "points.npy"
    numpy.save(source, numpy.array([[1.0, 2.0, 5.0], [3.0, 4.0, 6.0], [7.0, 8.0, 9.0]]))
    array_ref = execute_tabular_input(
        _tabular_input_context(source)
    ).outputs[TABULAR_DATA_ARRAY_OUTPUT_KEY]
    slice_ref = execute_array_slice_2d(
        _execution_context(
            inputs={"array_data": array_ref},
            properties={"row_limit": 2, "column_limit": 2},
        )
    ).outputs[TABULAR_ARRAY_SLICE_2D_OUTPUT_KEY]

    render_request = _generic_render_request(type_id="plot.bar", series_input=slice_ref)

    assert _core_series(render_request) == (
        {"label": "column_1", "values": [1.0, 3.0]},
        {"label": "column_2", "values": [2.0, 4.0]},
    )
    assert render_request.series[0]["decimation"] == {"method": "none", "original_rows": 2, "points": 2}
    assert render_request.series[0]["source_ref"]["kind"] == "array_slice_2d_ref"
    assert render_request.series[0]["source_ref"]["ref"]["ref_id"] == slice_ref.ref_id



@pytest.fixture
def table(tmp_path, monkeypatch):
    service = loaders.TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    monkeypatch.setattr(loaders, "_shared_service", service)
    path = tmp_path / "data.csv"
    path.write_text("time,signal,other\n0,10,100\n1,11,101\n2,12,102\n3,13,103\n", encoding="utf-8")
    return service.open_source(path)


def _request(value, mapping):
    return build_generic_plot_render_request(node_type_id="plot.bar", series_input=value,
                                             properties={"tabular_mapping": mapping})[0]


def test_direct_table_mapping_does_not_restrict_full_source_export_provenance(table):
    request = _request(table, {"columns": ["time", "signal"], "x": "time", "y": ["signal"], "row_limit": 2})
    assert request.series[0]["x"] == [0, 1]
    assert request.series[0]["y"] == [10, 11]
    assert request.series[0]["source_ref"] == {"ref": table.to_payload(), "row_offset": 0, "row_limit": 2}


@pytest.mark.parametrize("mapping_limit,expected_limit", [(1, 1), (3, 2), (0, 2)])
def test_window_provenance_keeps_original_columns_and_minimum_positive_limit(table, mapping_limit, expected_limit):
    window = TabularWindowRef("window", table, row_offset=1, row_limit=2, columns=("time", "signal", "other"))
    request = _request(window, {"columns": ["time", "signal"], "x": "time", "y": ["signal"], "row_limit": mapping_limit})
    assert request.series[0]["x"] == [1, 2][:expected_limit]
    assert request.series[0]["source_ref"] == {
        "ref": table.to_payload(), "row_offset": 1, "row_limit": expected_limit,
        "columns": ["time", "signal", "other"],
    }
    restricted = TabularWindowRef("restricted", table, columns=("time", "signal"))
    with pytest.raises(ValueError, match="other"):
        _request(restricted, {"columns": ["other"]})


def test_runtime_literal_columns_and_inspector_split_columns_are_distinct_policies(table):
    with pytest.raises(ValueError, match="time;signal"):
        _request(table, {"columns": "time;signal"})
    adapter = PlotPropertyEditAdapter()
    context = PropertyEditAdapterContext(node=SimpleNamespace(type_id="plot.bar", properties={}))
    rewrite = adapter.rewrite_property_edit(context, key="tabular_mapping_columns", value="time;signal,TIME")
    assert rewrite.key == "tabular_mapping"
    assert rewrite.value == {"columns": ["time", "signal"]}
    request = _request(table, rewrite.value)
    assert request.series[0]["x"] == [0, 1, 2, 3]
    # Inspector fractional/zero limits and runtime limits deliberately differ.
    limit = adapter.rewrite_property_edit(context, key="tabular_mapping_row_limit", value="0")
    assert limit.value == {"row_limit": 1}
    assert len(_request(table, {"row_limit": 0}).series[0]["x"]) == 4


@pytest.mark.parametrize("windowed", [False, True])
def test_table_preparation_reads_once_and_shares_complete_source_provenance(table, monkeypatch, windowed):
    service = loaders.shared_tabular_loader_cache_service()
    read = Mock(wraps=service.column_arrays)
    monkeypatch.setattr(service, "column_arrays", read)
    value = TabularWindowRef("view", table, row_offset=1, row_limit=2) if windowed else table

    request = _request(value, {"x": "time", "y": ["signal", "other"]})

    assert read.call_count == 1
    assert read.call_args.args == (table,)
    assert read.call_args.kwargs == {
        "columns": ("time", "signal", "other"),
        "row_offset": 1 if windowed else 0,
        "row_limit": 2 if windowed else None,
    }
    first, second = request.series
    assert first["y"] == ([11, 12] if windowed else [10, 11, 12, 13])
    assert second["y"] == ([101, 102] if windowed else [100, 101, 102, 103])
    assert first["source_ref"] == second["source_ref"]
    assert ("columns" in first["source_ref"]) is windowed


@pytest.mark.parametrize("windowed", [False, True])
def test_column_selection_validation_precedes_reads_but_role_validation_follows_empty_rows(
    table, tmp_path, monkeypatch, windowed,
):
    service = loaders.shared_tabular_loader_cache_service()
    read = Mock(wraps=service.column_arrays)
    monkeypatch.setattr(service, "column_arrays", read)
    value = TabularWindowRef("view", table, columns=("time", "signal")) if windowed else table

    with pytest.raises(ValueError, match="tabular_mapping.columns.*'missing'"):
        _request(value, {"columns": ["missing"], "y": ["also_missing"]})
    read.assert_not_called()

    empty_path = tmp_path / "empty.csv"
    empty_path.write_text("time,signal\n", encoding="utf-8")
    empty = service.open_source(empty_path)
    value = TabularWindowRef("empty_view", empty) if windowed else empty
    with pytest.raises(ValueError, match="has no data rows after parsing"):
        _request(value, {"y": ["missing"]})
    assert read.call_count == 1


def test_execution_uses_preview_request_builder_once_with_fresh_defaults(monkeypatch):
    plugin = generic.GenericPlotNodePlugin(specs.PLOT_NODE_DEFINITION_BY_TYPE_ID["plot.bar"])
    value = {"x": [0, 1], "y": [2, 3]}
    properties = {"title": "Overlay", "plot_options": {"hover_readout": True}}
    expected_properties = specs.plot_property_defaults(plugin.spec())
    expected_properties.update(properties)
    expected, warnings = generic.build_generic_plot_render_request(
        node_type_id="plot.bar", properties=expected_properties, series_input=value,
    )
    captured = []
    original_builder = generic.build_generic_plot_render_request

    def record_request(**kwargs):
        result = original_builder(**kwargs)
        captured.append((kwargs, result))
        return result

    builder = Mock(side_effect=record_request)
    defaults = Mock(wraps=specs.plot_property_defaults)
    prepare = Mock(wraps=generic.data_series.prepare_plot_series)
    monkeypatch.setattr(generic, "build_generic_plot_render_request", builder)
    monkeypatch.setattr(specs, "plot_property_defaults", defaults)
    monkeypatch.setattr(generic.data_series, "prepare_plot_series", prepare)
    context = _execution_context(inputs={"series": value}, properties=properties)

    result = plugin.execute(context)

    assert builder.call_count == defaults.call_count == prepare.call_count == 1
    assert result.outputs == {}
    assert result.warnings == warnings
    assert captured[0][1] == (expected, warnings)
    captured[0][0]["properties"]["axis_limits"]["x"][0] = 99
    captured[0][1][0].options["plot_options"] = {"probe": True}

    plugin.execute(context)

    assert builder.call_count == defaults.call_count == prepare.call_count == 2
    assert captured[1][1] == (expected, warnings)
    assert captured[1][0]["properties"]["axis_limits"]["x"] == [None, None]
    assert properties == {"title": "Overlay", "plot_options": {"hover_readout": True}}


def test_value_preparation_imports_no_scientific_or_tabular_runtime():
    code = """
import sys
from ea_node_editor.nodes.builtins.plot.generic import build_generic_plot_render_request
request, warnings = build_generic_plot_render_request(
    node_type_id='plot.bar', properties={}, series_input={'x': [0, 1], 'y': [2, 3]},
)
assert request.series == ({'x': [0, 1], 'y': [2, 3]},)
assert warnings == ()
for prefix in ('numpy', 'matplotlib', 'pyarrow', 'pyvista', 'pyqtgraph',
               'ea_node_editor.addons.tabular_data.loader_cache_service'):
    assert not any(name == prefix or name.startswith(prefix + '.') for name in sys.modules), prefix
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


def test_nd_source_is_rejected_before_array_sampling(tmp_path, monkeypatch):
    np = pytest.importorskip("numpy")
    service = loaders.TabularLoaderCacheService(cache_dir=tmp_path / "cache")
    monkeypatch.setattr(loaders, "_shared_service", service)
    source = tmp_path / "nd.npy"
    np.save(source, np.arange(24).reshape(2, 3, 4))
    ref = service.open_source(source)
    sample = Mock(wraps=service.sample_array)
    monkeypatch.setattr(service, "sample_array", sample)

    with pytest.raises(ValueError, match="Build a table with explicit axes before plotting an ND array"):
        _request(ref, {})
    sample.assert_not_called()


@pytest.mark.parametrize("properties", [{}, {"tabular_mapping": {}, "plot_options": {}}], ids=["missing", "supplied_empty"])
def test_preview_requests_avoid_empty_copy_work_and_own_their_default_state(monkeypatch, properties):
    copied = []
    original_copy = generic.copy.deepcopy

    def record_copy(value):
        copied.append(value)
        return original_copy(value)

    prepare = Mock(wraps=generic.data_series.prepare_plot_series)
    monkeypatch.setattr(generic.copy, "deepcopy", record_copy)
    monkeypatch.setattr(generic.data_series, "prepare_plot_series", prepare)
    requests = [build_generic_plot_render_request(
        node_type_id="plot.bar", properties=properties, series_input={"x": [0, 1], "y": [2, 3]},
    )[0] for _ in range(2)]

    assert len(copied) == 4  # Independent axis and log defaults for each request.
    assert all(value for value in copied)
    first_mapping, second_mapping = [call.kwargs["mapping"] for call in prepare.call_args_list]
    assert first_mapping == second_mapping == {}
    assert first_mapping is not second_mapping
    assert first_mapping is not properties.get("tabular_mapping")
    first_mapping["columns"] = ["edited"]
    requests[0].options["axis_limits"]["x"][0] = 99
    requests[0].options["log_scales"]["y"] = True
    assert second_mapping == {}
    assert requests[1].options["axis_limits"]["x"] == [None, None]
    assert requests[1].options["log_scales"]["y"] is False
    assert not properties.get("tabular_mapping")
    assert not properties.get("plot_options")


def test_preview_requests_copy_nested_supplied_mappings_before_preparation(monkeypatch):
    properties = {
        "tabular_mapping": {"y": ["signal"]},
        "plot_options": {"annotation": {"labels": ["original"]}},
        "axis_limits": {"x": [1, 2]},
        "log_scales": {"x": True},
    }
    prepare = Mock(wraps=generic.data_series.prepare_plot_series)
    monkeypatch.setattr(generic.data_series, "prepare_plot_series", prepare)
    request, warnings = build_generic_plot_render_request(
        node_type_id="plot.bar", properties=properties, series_input={"x": [0, 1], "y": [2, 3]},
    )

    assert warnings == ()
    prepare.call_args.kwargs["mapping"]["y"].append("edited")
    request.options["annotation"]["labels"].append("edited")
    request.options["axis_limits"]["x"][0] = 99
    request.options["log_scales"]["x"] = False
    assert properties == {
        "tabular_mapping": {"y": ["signal"]},
        "plot_options": {"annotation": {"labels": ["original"]}},
        "axis_limits": {"x": [1, 2]},
        "log_scales": {"x": True},
    }


@pytest.mark.parametrize("property_key", ["tabular_mapping", "plot_options", "axis_limits", "log_scales", "default_axis_limits"])
def test_preview_request_preserves_nested_copy_failure_identity(monkeypatch, property_key):
    failure = RuntimeError("nested copy failed")

    class CopyFailure:
        def __deepcopy__(self, memo):
            raise failure

    if property_key == "default_axis_limits":
        properties = {}
        monkeypatch.setattr(specs, "PLOT_AXIS_LIMITS_DEFAULT", {"x": CopyFailure()})
    else:
        properties = {property_key: {"nested": CopyFailure()}}
    with pytest.raises(RuntimeError) as excinfo:
        build_generic_plot_render_request(
            node_type_id="plot.bar", properties=properties, series_input={"x": [0, 1], "y": [2, 3]},
        )
    assert excinfo.value is failure
