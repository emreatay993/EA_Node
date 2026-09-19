# Purpose: Own inert generic Plot declarations, defaults, and tabular mapping roles.
# Map: feature_routes/plotter_nodes.md
# Tests: tests/test_plot_specs.py, tests/test_plot_node_contracts.py, tests/test_plot_property_edit_adapter.py
from __future__ import annotations

import copy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from ea_node_editor.nodes.builtins.icon_catalog import builtin_node_type_spec
from ea_node_editor.nodes.node_specs import NodeTypeSpec, PortSpec, PropertySpec
from ea_node_editor.runtime_contracts import (
    ARRAY_DATA_REF_TYPE_ID, ARRAY_SLICE_2D_REF_TYPE_ID, DOUBLE_DATA_TYPE_ID,
    GRAPH_ARRAY_DATA_TYPE_ID, GRAPH_DICTIONARY_DATA_TYPE_ID, INTEGER_DATA_TYPE_ID,
    TABULAR_DATA_REF_TYPE_ID, TABULAR_WINDOW_REF_TYPE_ID,
)

# Keep node registration independent from execution implementation imports.
AUTO_PLOT_BACKEND_ID = "auto"
MATPLOTLIB_PLOT_BACKEND_ID = "matplotlib"
PLOT_SURFACE_STATIC_EXPORT = "static_export"
PLOT_SURFACE_DATA_EXPORT = "data_export"
PLOT_TYPE_BAR = "bar"
PLOT_TYPE_HISTOGRAM = "histogram"
PLOT_TYPE_HEATMAP = "heatmap"
PLOT_TYPE_CONTOUR = "contour"
PLOT_TYPE_SURFACE = "surface"
PLOT_TYPE_POINT_CLOUD = "point_cloud"
PLOT_TYPE_STREAMLINES = "streamlines"
GENERIC_PLOT_SERIES_RUNTIME_SHAPES = (
    "numpy arrays",
    "lists of numbers",
    "dict-of-arrays",
)
PLOT_NODE_CATEGORY_PATH = ("Plot",)
PLOT_AXIS_LIMITS_DEFAULT = {
    "x": [None, None],
    "y": [None, None],
    "z": [None, None],
}
PLOT_LOG_SCALES_DEFAULT = {
    "x": False,
    "y": False,
    "z": False,
}
PLOT_COLORMAP_VALUES = (
    "viridis",
    "plasma",
    "inferno",
    "magma",
    "cividis",
    "turbo",
    "coolwarm",
)
PLOT_STATIC_EXPORT_FORMATS = ("png", "svg", "pdf")
PLOT_DATA_EXPORT_FORMATS = ("csv",)
PLOT_BACKEND_VALUES = (AUTO_PLOT_BACKEND_ID, MATPLOTLIB_PLOT_BACKEND_ID)
PLOT_RUNTIME_SHAPE_TEXT = ", ".join(GENERIC_PLOT_SERIES_RUNTIME_SHAPES)
PLOT_TABULAR_MAPPING_PROPERTY = "tabular_mapping"
# Plot surfaces render at canvas resolution; series read from tabular refs are
# decimated to this budget (min-max envelope / stride sampling — visually
# lossless). An explicit ``tabular_mapping.row_limit`` remains a hard source
# row cap applied before decimation. Data exports stream the full source.
TABULAR_PLOT_MAX_POINTS_PER_SERIES = 4000
TABULAR_PLOT_DIAGNOSTIC_HINT = (
    "Check Header Row, Skip Rows, selected columns, Tabular Mapping, and numeric formatting."
)


@dataclass(frozen=True, slots=True)
class PlotNodeDefinition:
    type_id: str
    display_name: str
    plot_type: str
    supports_colormap: bool = False
    description: str = ""
    keywords: tuple[str, ...] = ()


PLOT_NODE_DEFINITIONS = (
    PlotNodeDefinition("plot.bar", "Bar Plot", PLOT_TYPE_BAR, keywords=("bar", "chart", "categories")),
    PlotNodeDefinition(
        "plot.histogram",
        "Histogram Plot",
        PLOT_TYPE_HISTOGRAM,
        keywords=("histogram", "distribution", "bins"),
    ),
    PlotNodeDefinition(
        "plot.heatmap",
        "Heatmap Plot",
        PLOT_TYPE_HEATMAP,
        supports_colormap=True,
        keywords=("heatmap", "matrix", "colormap"),
    ),
    PlotNodeDefinition(
        "plot.contour",
        "Contour Plot",
        PLOT_TYPE_CONTOUR,
        supports_colormap=True,
        keywords=("contour", "levels", "colormap"),
    ),
    PlotNodeDefinition(
        "plot.surface",
        "Surface Plot",
        PLOT_TYPE_SURFACE,
        supports_colormap=True,
        keywords=("surface", "3d", "colormap"),
    ),
    PlotNodeDefinition(
        "plot.point_cloud",
        "Point Cloud Plot",
        PLOT_TYPE_POINT_CLOUD,
        supports_colormap=True,
        keywords=("point cloud", "3d", "scatter"),
    ),
    PlotNodeDefinition(
        "plot.streamlines",
        "Streamlines Plot",
        PLOT_TYPE_STREAMLINES,
        supports_colormap=True,
        keywords=("streamlines", "vector field", "flow"),
    ),
)
PLOT_NODE_DEFINITION_BY_TYPE_ID = {
    definition.type_id: definition for definition in PLOT_NODE_DEFINITIONS
}
PLOT_NODE_TYPE_IDS = tuple(definition.type_id for definition in PLOT_NODE_DEFINITIONS)


def _standard_plot_ports(plot_type: str) -> tuple[PortSpec, ...]:
    if plot_type in {
        PLOT_TYPE_BAR,
        PLOT_TYPE_HISTOGRAM,
    }:
        series_data_type = DOUBLE_DATA_TYPE_ID
        accepted_series_data_types = (
            INTEGER_DATA_TYPE_ID,
            GRAPH_ARRAY_DATA_TYPE_ID,
            GRAPH_DICTIONARY_DATA_TYPE_ID,
            ARRAY_DATA_REF_TYPE_ID,
            ARRAY_SLICE_2D_REF_TYPE_ID,
            TABULAR_DATA_REF_TYPE_ID,
            TABULAR_WINDOW_REF_TYPE_ID,
        )
    elif plot_type in {PLOT_TYPE_HEATMAP, PLOT_TYPE_CONTOUR, PLOT_TYPE_SURFACE}:
        series_data_type = GRAPH_ARRAY_DATA_TYPE_ID
        accepted_series_data_types = (
            GRAPH_DICTIONARY_DATA_TYPE_ID,
            ARRAY_DATA_REF_TYPE_ID,
            ARRAY_SLICE_2D_REF_TYPE_ID,
            TABULAR_DATA_REF_TYPE_ID,
            TABULAR_WINDOW_REF_TYPE_ID,
        )
    elif plot_type in {PLOT_TYPE_POINT_CLOUD, PLOT_TYPE_STREAMLINES}:
        series_data_type = GRAPH_DICTIONARY_DATA_TYPE_ID
        accepted_series_data_types = (
            ARRAY_DATA_REF_TYPE_ID,
            ARRAY_SLICE_2D_REF_TYPE_ID,
            TABULAR_DATA_REF_TYPE_ID,
            TABULAR_WINDOW_REF_TYPE_ID,
        )
    else:
        raise ValueError(f"Unknown generic plot type: {plot_type!r}.")

    return (
        PortSpec(
            "series",
            "in",
            "data",
            series_data_type,
            label="Series",
            required=True,
            data_access="list",
            accepted_data_types=accepted_series_data_types,
            description="One or more numeric series, array references, or tabular references to plot.",
        ),
        PortSpec(
            "static_export",
            "out",
            "data",
            'COREX.DataTypes.Path',
            label="Image Export",
            exposed=True,
            description="Path to the archived plot image when image export is enabled.",
        ),
        PortSpec(
            "data_export",
            "out",
            "data",
            'COREX.DataTypes.Path',
            label="Data Export",
            exposed=True,
            description="Path to the archived plot data file when data export is enabled.",
        ),
        PortSpec(
            "exports",
            "out",
            "data",
            'COREX.Plot.ExportBundle',
            label="Exports",
            exposed=True,
            description="Metadata describing the image and data artifacts created by this plot.",
        ),
    )


def _standard_plot_properties(*, supports_colormap: bool) -> tuple[PropertySpec, ...]:
    properties: list[PropertySpec] = [
        PropertySpec(
            "backend",
            "enum",
            AUTO_PLOT_BACKEND_ID,
            "Backend",
            enum_values=PLOT_BACKEND_VALUES,
            inspector_editor="enum",
            group="Rendering",
        ),
        PropertySpec("title", "str", "", "Title", inline_editor="text", group="Text"),
        PropertySpec("x_label", "str", "", "X Axis Label", inline_editor="text", group="Text"),
        PropertySpec("y_label", "str", "", "Y Axis Label", inline_editor="text", group="Text"),
        PropertySpec("z_label", "str", "", "Z Axis Label", inline_editor="text", group="Text"),
        PropertySpec(
            "axis_limits",
            "json",
            copy.deepcopy(PLOT_AXIS_LIMITS_DEFAULT),
            "Axis Limits",
            inspector_editor="textarea",
            group="Axes",
        ),
        PropertySpec(
            "log_scales",
            "json",
            copy.deepcopy(PLOT_LOG_SCALES_DEFAULT),
            "Log Scales",
            inspector_editor="textarea",
            group="Axes",
        ),
        PropertySpec("grid", "bool", True, "Grid", inspector_editor="toggle", group="Axes"),
        PropertySpec("legend", "bool", True, "Legend", inspector_editor="toggle", group="Text"),
        PropertySpec(
            PLOT_TABULAR_MAPPING_PROPERTY,
            "json",
            {},
            "Tabular Mapping",
            inspector_editor="textarea",
            group="Data",
        ),
    ]
    if supports_colormap:
        properties.append(
            PropertySpec(
                "colormap",
                "enum",
                "viridis",
                "Colormap",
                enum_values=PLOT_COLORMAP_VALUES,
                inspector_editor="enum",
                group="Rendering",
            )
        )
    properties.extend(
        [
            PropertySpec(
                "render_in_canvas",
                "bool",
                True,
                "Render In Canvas",
                inspector_editor="toggle",
                group="Rendering",
            ),
            PropertySpec(
                "archive_export_on_run",
                "bool",
                False,
                "Archive Export On Run",
                inspector_editor="toggle",
                group="Export",
            ),
            PropertySpec(
                "static_export_format",
                "enum",
                "png",
                "Image Export Format",
                enum_values=PLOT_STATIC_EXPORT_FORMATS,
                inspector_editor="enum",
                group="Export",
            ),
            PropertySpec(
                "data_export_format",
                "enum",
                "csv",
                "Data Export Format",
                enum_values=PLOT_DATA_EXPORT_FORMATS,
                inspector_editor="enum",
                group="Export",
            ),
            PropertySpec(
                "plot_options",
                "json",
                {},
                "Plot Options",
                inspector_editor="textarea",
                group="Rendering",
            ),
        ]
    )
    return tuple(properties)


def _plot_node_description(definition: PlotNodeDefinition) -> str:
    if definition.description:
        return definition.description
    return (
        f"Generic {definition.display_name.lower()} node. The variadic series input accepts "
        f"{PLOT_RUNTIME_SHAPE_TEXT} at runtime without requiring numpy as a core dependency."
    )


def plot_node_spec(definition: PlotNodeDefinition) -> NodeTypeSpec:
    return builtin_node_type_spec(
        type_id=definition.type_id,
        display_name=definition.display_name,
        category_path=PLOT_NODE_CATEGORY_PATH,
        description=_plot_node_description(definition),
        keywords=definition.keywords,
        ports=_standard_plot_ports(definition.plot_type),
        properties=_standard_plot_properties(supports_colormap=definition.supports_colormap),
    )


def plot_property_defaults(spec: NodeTypeSpec) -> dict[str, Any]:
    return {prop.key: prop.make_default() for prop in spec.properties}


# Editor presentation and runtime validation have intentionally different ordering.
PLOT_TABULAR_DEFAULT_EDITOR_ROLES = (("columns", "Available Columns", "multi"),)
PLOT_TABULAR_EDITOR_ROLES = MappingProxyType({
    PLOT_TYPE_BAR: (("x", "X Column", "single"), ("category", "Category Column", "single"),
                    ("y", "Y Columns", "multi"), *PLOT_TABULAR_DEFAULT_EDITOR_ROLES),
    PLOT_TYPE_HISTOGRAM: (("values", "Value Columns", "multi"), *PLOT_TABULAR_DEFAULT_EDITOR_ROLES),
    **{kind: (("z", "Z Column", "single"), ("values", "Value Columns", "multi"),
              *PLOT_TABULAR_DEFAULT_EDITOR_ROLES)
       for kind in (PLOT_TYPE_HEATMAP, PLOT_TYPE_CONTOUR, PLOT_TYPE_SURFACE)},
    **{kind: (("x", "X Column", "single"), ("y", "Y Column", "single"), ("z", "Z Column", "single"),
              *PLOT_TABULAR_DEFAULT_EDITOR_ROLES)
       for kind in (PLOT_TYPE_POINT_CLOUD, PLOT_TYPE_STREAMLINES)},
})
PLOT_TABULAR_VALIDATION_KEYS = MappingProxyType({
    PLOT_TYPE_BAR: ("x", "category", "y"),
    PLOT_TYPE_HISTOGRAM: ("values",),
    **{kind: ("values", "z") for kind in (PLOT_TYPE_HEATMAP, PLOT_TYPE_CONTOUR, PLOT_TYPE_SURFACE)},
    **{kind: ("x", "y", "z") for kind in (PLOT_TYPE_POINT_CLOUD, PLOT_TYPE_STREAMLINES)},
})
