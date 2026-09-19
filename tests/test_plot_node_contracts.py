# Purpose: Prove the retained generic Plot catalogue and declaration contracts.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_plot_node_contracts.py
from __future__ import annotations


from ea_node_editor.execution.plot_backend import (
    AUTO_PLOT_BACKEND_ID,
    GENERIC_PLOT_SERIES_RUNTIME_SHAPES,
)
from ea_node_editor.execution.plot_backend_matplotlib import MATPLOTLIB_PLOT_BACKEND_ID
from ea_node_editor.nodes.bootstrap import build_default_registry
from ea_node_editor.runtime_contracts import (
    ARRAY_DATA_REF_TYPE_ID,
    ARRAY_SLICE_2D_REF_TYPE_ID,
    DOUBLE_DATA_TYPE_ID,
    GRAPH_ARRAY_DATA_TYPE_ID,
    GRAPH_DICTIONARY_DATA_TYPE_ID,
    INTEGER_DATA_TYPE_ID,
    PATH_DATA_TYPE_ID,
    PLOT_EXPORT_BUNDLE_DATA_TYPE_ID,
    TABULAR_DATA_REF_TYPE_ID,
    TABULAR_WINDOW_REF_TYPE_ID,
)
from ea_node_editor.nodes.builtins.plot.specs import PLOT_NODE_CATEGORY_PATH, PLOT_NODE_TYPE_IDS


EXPECTED_PLOT_TYPE_IDS = (
    "plot.bar",
    "plot.histogram",
    "plot.heatmap",
    "plot.contour",
    "plot.surface",
    "plot.point_cloud",
    "plot.streamlines",
)
EXPECTED_DISPLAY_NAMES = {
    "plot.bar": "Bar Plot",
    "plot.histogram": "Histogram Plot",
    "plot.heatmap": "Heatmap Plot",
    "plot.contour": "Contour Plot",
    "plot.surface": "Surface Plot",
    "plot.point_cloud": "Point Cloud Plot",
    "plot.streamlines": "Streamlines Plot",
}
EXPECTED_GENERIC_PLOT_TYPE_IDS = EXPECTED_PLOT_TYPE_IDS
STANDARD_PROPERTY_KEYS = {
    "backend",
    "title",
    "x_label",
    "y_label",
    "z_label",
    "axis_limits",
    "log_scales",
    "grid",
    "legend",
    "render_in_canvas",
    "archive_export_on_run",
    "static_export_format",
    "data_export_format",
    "tabular_mapping",
    "plot_options",
}
COLORMAP_PLOT_TYPES = {
    "plot.heatmap",
    "plot.contour",
    "plot.surface",
    "plot.point_cloud",
    "plot.streamlines",
}


def test_generic_plot_catalog_registers_v1_specs_through_builtin_bootstrap() -> None:
    registry = build_default_registry()
    scalar_series_profile = (
        DOUBLE_DATA_TYPE_ID,
        (
            INTEGER_DATA_TYPE_ID,
            GRAPH_ARRAY_DATA_TYPE_ID,
            GRAPH_DICTIONARY_DATA_TYPE_ID,
            ARRAY_DATA_REF_TYPE_ID,
            ARRAY_SLICE_2D_REF_TYPE_ID,
            TABULAR_DATA_REF_TYPE_ID,
            TABULAR_WINDOW_REF_TYPE_ID,
        ),
    )
    grid_series_profile = (
        GRAPH_ARRAY_DATA_TYPE_ID,
        (
            GRAPH_DICTIONARY_DATA_TYPE_ID,
            ARRAY_DATA_REF_TYPE_ID,
            ARRAY_SLICE_2D_REF_TYPE_ID,
            TABULAR_DATA_REF_TYPE_ID,
            TABULAR_WINDOW_REF_TYPE_ID,
        ),
    )
    point_series_profile = (
        GRAPH_DICTIONARY_DATA_TYPE_ID,
        (
            ARRAY_DATA_REF_TYPE_ID,
            ARRAY_SLICE_2D_REF_TYPE_ID,
            TABULAR_DATA_REF_TYPE_ID,
            TABULAR_WINDOW_REF_TYPE_ID,
        ),
    )
    expected_series_profiles = {
        "plot.bar": scalar_series_profile,
        "plot.histogram": scalar_series_profile,
        "plot.heatmap": grid_series_profile,
        "plot.contour": grid_series_profile,
        "plot.surface": grid_series_profile,
        "plot.point_cloud": point_series_profile,
        "plot.streamlines": point_series_profile,
    }

    assert PLOT_NODE_TYPE_IDS == EXPECTED_PLOT_TYPE_IDS
    for type_id in EXPECTED_GENERIC_PLOT_TYPE_IDS:
        spec = registry.get_spec(type_id)
        assert spec.type_id == type_id
        assert spec.display_name == EXPECTED_DISPLAY_NAMES[type_id]
        assert spec.category_path == PLOT_NODE_CATEGORY_PATH
        assert spec.category_path == ("Plot",)
        assert spec.runtime_behavior == "active"
        assert spec.surface_family == "standard"
        for shape_name in GENERIC_PLOT_SERIES_RUNTIME_SHAPES:
            assert shape_name in spec.description

        series_port = next(port for port in spec.ports if port.key == "series")
        assert series_port.direction == "in"
        assert series_port.kind == "data"
        assert (
            series_port.data_type,
            series_port.accepted_data_types,
        ) == expected_series_profiles[type_id]
        assert series_port.required
        assert series_port.data_access == "list"
        assert not series_port.allow_multiple_connections
        for source_data_type in (
            series_port.data_type,
            *series_port.accepted_data_types,
        ):
            assert registry.data_types.compatibility(
                source_data_type,
                series_port.data_type,
                series_port.accepted_data_types,
            ).is_compatible
        assert not registry.data_types.compatibility(
            PATH_DATA_TYPE_ID,
            series_port.data_type,
            series_port.accepted_data_types,
        ).is_compatible

        ports = {port.key: port for port in spec.ports}
        assert "render_request" not in ports
        assert ports["static_export"].label == "Image Export"
        assert ports["exports"].data_type == PLOT_EXPORT_BUNDLE_DATA_TYPE_ID


def test_generic_plot_standard_properties_are_stable_and_colormap_is_scoped() -> None:
    registry = build_default_registry()

    for type_id in EXPECTED_GENERIC_PLOT_TYPE_IDS:
        spec = registry.get_spec(type_id)
        property_by_key = {prop.key: prop for prop in spec.properties}
        assert STANDARD_PROPERTY_KEYS.issubset(property_by_key)
        assert property_by_key["backend"].make_default() == AUTO_PLOT_BACKEND_ID
        assert property_by_key["backend"].enum_values == (AUTO_PLOT_BACKEND_ID, MATPLOTLIB_PLOT_BACKEND_ID)
        assert property_by_key["axis_limits"].type == "json"
        assert property_by_key["log_scales"].type == "json"
        assert property_by_key["render_in_canvas"].make_default() is True
        assert property_by_key["archive_export_on_run"].make_default() is False
        assert property_by_key["static_export_format"].label == "Image Export Format"
        assert "frame_selector" not in property_by_key
        assert "animate" not in property_by_key
        assert ("colormap" in property_by_key) is (type_id in COLORMAP_PLOT_TYPES)
