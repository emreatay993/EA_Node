# Purpose: Declare the COREX Signal Plot node.
# Map: feature_routes/plotter_nodes
# Tests: tests/test_signal_plot_renderer.py
from __future__ import annotations

from typing import Any

from ea_node_editor.nodes.builtins.icon_catalog import builtin_node_type_spec
from ea_node_editor.nodes.builtins.core_values import COLOR_DATA_TYPE_ID, IMAGE_DATA_TYPE_ID
from ea_node_editor.nodes.execution_context import ExecutionContext, NodeResult
from ea_node_editor.nodes.node_specs import (
    NodeTypeSpec,
    PortSpec,
    PropertySpec,
    SettingsGroupItemSpec,
    SettingsGroupSpec,
)
from ea_node_editor.nodes.plugin_contracts import PluginDescriptor
from ea_node_editor.runtime_contracts import (
    BOOLEAN_DATA_TYPE_ID,
    DOUBLE_DATA_TYPE_ID,
    INTEGER_DATA_TYPE_ID,
    INTERVAL_1D_GRAPH_DATA_TYPE_ID,
    STRING_DATA_TYPE_ID,
)

SIGNAL_PLOT_TYPE_ID = "plot.signal"
LEGEND_LABELS = (
    "Upper left", "Upper center", "Upper right", "Middle left", "Middle center",
    "Middle right", "Lower left", "Lower center", "Lower right",
)
LINE_STYLE_LABELS = ("None", "Solid", "Dash", "Dash Dot", "Dash Dot Dot", "Dot")
MARKER_LABELS = (
    "None",
    "Filled circle",
    "Filled square",
    "Open circle",
    "Open square",
    "Filled diamond",
    "Open diamond",
    "Asterisk",
    "Hashtag",
    "Cross",
    "X",
    "Vertical bar",
    "Tri upwards",
    "Tri downwards",
    "Filled triangle upwards",
    "Filled triangle downwards",
    "Open triangle upwards",
    "Open triangle downwards",
)
PORT_DESCRIPTIONS = {
    "width": "Width of the image.",
    "height": "Height of the image.",
    "title": "Title of the plot.",
    "font_size": "Specify the font size for your plot.",
    "labels": "Label for each dataset of your plot.",
    "show_legend": "Input 'True' to show a legend with the given labels. If no labels are defined, nothing is shown.",
    "legend_alignment": "Define the alignment where the legend should be displayed. Possible values are 0 = Upper left, 1 = Upper center, 2 = Upper right, 3 = Middle left, 4 = Middle center, 5 = Middle right, 6 = Lower left, 7 = Lower center, 8 = Lower right.",
    "values": "Values of your plot.",
    "x_axis_interval": "Define a custom interval for the displayed X-axis value range.",
    "y_axis_interval": "Define a custom interval for the displayed Y-axis value range.",
    "colors": "Input one color per tree branch for your input data. If the number of colors is less than the number of given branches, then the color values are repeated.",
    "line_styles": "Choose the line style for the plot. 0 = None, 1 = Solid, 2 = Dash, 3 = Dash Dot, 4 = Dash Dot Dot, 5 = Dot. Please provide one style for all branches of the input data or one style for each branch. If the number of styles is less than the number of branches, then the styles are repeated.",
    "line_widths": "Specify the line width connecting the data points. Please provide one width for all branches of the input data or one width for each branch. If the number of widths is less than the number of branches, then the widths are repeated.",
    "marker_shapes": "Choose the marker shape for the plot. 0 = None, 1 = Filled circle, 2 = Filled square, 3 = Open circle, 4 = Open square, 5 = Filled diamond, 6 = Open diamond, 7 = Asterisk, 8 = Hashtag, 9 = Cross, 10 = X, 11 = Vertical bar, 12 = Tri upwards, 13 = Tri downwards, 14 = Filled triangle upwards, 15 = Filled triangle downwards, 16 = Open triangle upwards, 17 = Open triangle downwards. Please provide one shape for all branches of the input data or one shape for each branch. If the number of shapes is less than the number of branches, then the shapes are repeated.",
    "marker_sizes": "Specify the size of the markers which point to your given values. Please provide one size for all branches of the input data or one size for each branch. If the number of sizes is less than the number of branches, then the sizes are repeated.",
    "x_axis_label": "Label of the horizontal x-axis.",
    "y_axis_label": "Label of the vertical y-axis.",
    "logarithmic_y_axis": "If set to true, the Y axis will use a logarithmic scale with a base of 10.",
    "image_background_color": "Specify the background color that is used by the whole image. By default, it's set to white.",
    "data_background_color": "Specify the background color that is used by the rectangle that contains the data. By default, it's set to white.",
}


def _port(
    key: str,
    data_type: str,
    label: str,
    *,
    access: str = "item",
    required: bool = False,
    default: bool = True,
    accepted: tuple[str, ...] = (),
) -> PortSpec:
    return PortSpec(
        key,
        "in",
        "data",
        data_type,
        label=label,
        required=required,
        uses_property_default=default,
        data_access=access,  # type: ignore[arg-type]
        accepted_data_types=accepted,
        description=PORT_DESCRIPTIONS[key],
    )


SIGNAL_PLOT_PORTS = (
    _port("width", INTEGER_DATA_TYPE_ID, "Width"),
    _port("height", INTEGER_DATA_TYPE_ID, "Height"),
    _port("title", STRING_DATA_TYPE_ID, "Title"),
    _port("font_size", INTEGER_DATA_TYPE_ID, "Font size"),
    _port("labels", STRING_DATA_TYPE_ID, "Labels", access="list"),
    _port("show_legend", BOOLEAN_DATA_TYPE_ID, "Show legend"),
    _port("legend_alignment", INTEGER_DATA_TYPE_ID, "Legend alignment"),
    _port("values", DOUBLE_DATA_TYPE_ID, "Values", access="tree", required=True, default=False),
    _port("x_axis_interval", INTERVAL_1D_GRAPH_DATA_TYPE_ID, "X axis interval"),
    _port("y_axis_interval", INTERVAL_1D_GRAPH_DATA_TYPE_ID, "Y axis interval"),
    _port("colors", COLOR_DATA_TYPE_ID, "Colors", access="list", accepted=(STRING_DATA_TYPE_ID,)),
    _port("line_styles", INTEGER_DATA_TYPE_ID, "Line styles", access="list"),
    _port("line_widths", INTEGER_DATA_TYPE_ID, "Line widths", access="list"),
    _port("marker_shapes", INTEGER_DATA_TYPE_ID, "Marker shapes", access="list"),
    _port("marker_sizes", INTEGER_DATA_TYPE_ID, "Marker sizes", access="list"),
    _port("x_axis_label", STRING_DATA_TYPE_ID, "X axis label"),
    _port("y_axis_label", STRING_DATA_TYPE_ID, "Y axis label"),
    _port("logarithmic_y_axis", BOOLEAN_DATA_TYPE_ID, "Logarithmic Y axis"),
    _port("image_background_color", COLOR_DATA_TYPE_ID, "Image background color", accepted=(STRING_DATA_TYPE_ID,)),
    _port("data_background_color", COLOR_DATA_TYPE_ID, "Data background color", accepted=(STRING_DATA_TYPE_ID,)),
    PortSpec(
        "image",
        "out",
        "data",
        IMAGE_DATA_TYPE_ID,
        label="Image",
        exposed=True,
        description="Image data from your plot.",
    ),
)

_MARKER_CODES = tuple(range(len(MARKER_LABELS)))
SIGNAL_PLOT_PROPERTIES = (
    PropertySpec("width", "int", 600, "Width", minimum=2, maximum=3840, step=1, inline_editor="slider", group="General options"),
    PropertySpec("height", "int", 400, "Height", minimum=2, maximum=2160, step=1, inline_editor="slider", group="General options"),
    PropertySpec("title", "str", "", "Title", inline_editor="text", group="General options"),
    PropertySpec("font_size", "int", 12, "Font size", minimum=1, maximum=72, step=1, inline_editor="slider", group="General options"),
    PropertySpec("labels", "json", [], "Labels", inline_editor="list", list_item_type="str", group="General options"),
    PropertySpec("show_legend", "bool", False, "Show legend", inline_editor="toggle", group="General options"),
    PropertySpec(
        "legend_alignment",
        "int",
        8,
        "Legend alignment",
        inline_editor="enum",
        enum_values=LEGEND_LABELS,
        enum_codes=tuple(range(9)),
        group="General options",
    ),
    PropertySpec(
        "x_axis_interval",
        "interval_1d",
        None,
        "X axis interval",
        inline_editor="interval_fields",
        nullable=True,
        group="Signal plot options",
    ),
    PropertySpec(
        "y_axis_interval",
        "interval_1d",
        None,
        "Y axis interval",
        inline_editor="interval_fields",
        nullable=True,
        group="Signal plot options",
    ),
    PropertySpec("colors", "json", [], "Colors", inline_editor="list", list_item_type="color", group="Signal plot options"),
    PropertySpec(
        "line_styles",
        "json",
        [1],
        "Line styles",
        inline_editor="list",
        list_item_type="enum",
        list_item_enum_values=LINE_STYLE_LABELS,
        list_item_enum_codes=tuple(range(len(LINE_STYLE_LABELS))),
        group="Signal plot options",
    ),
    PropertySpec(
        "line_widths", "json", [1], "Line widths", inline_editor="list", list_item_type="int",
        list_item_minimum=0, list_item_maximum=5, list_item_step=1, group="Signal plot options",
    ),
    PropertySpec(
        "marker_shapes",
        "json",
        [1],
        "Marker shapes",
        inline_editor="list",
        list_item_type="enum",
        list_item_enum_values=MARKER_LABELS,
        list_item_enum_codes=_MARKER_CODES,
        group="Signal plot options",
    ),
    PropertySpec(
        "marker_sizes", "json", [10], "Marker sizes", inline_editor="list", list_item_type="int",
        list_item_minimum=1, list_item_maximum=72, list_item_step=1, group="Signal plot options",
    ),
    PropertySpec("x_axis_label", "str", "", "X axis label", inline_editor="text", group="Signal plot options"),
    PropertySpec("y_axis_label", "str", "", "Y axis label", inline_editor="text", group="Signal plot options"),
    PropertySpec("logarithmic_y_axis", "bool", False, "Logarithmic Y axis", inline_editor="toggle", group="Signal plot options"),
    PropertySpec("image_background_color", "str", "#ffffff", "Image background color", inline_editor="color", group="General options"),
    PropertySpec("data_background_color", "str", "#ffffff", "Data background color", inline_editor="color", group="General options"),
)


def _group(group_id: str, label: str, keys: tuple[str, ...], *, include_values: bool = False) -> SettingsGroupSpec:
    items = [SettingsGroupItemSpec(port_key="values")] if include_values else []
    items.extend(SettingsGroupItemSpec(port_key=key, property_key=key) for key in keys)
    return SettingsGroupSpec(group_id, label, tuple(items))


SIGNAL_PLOT_SETTINGS_GROUPS = (
    _group(
        "general_options",
        "General options",
        (
            "width", "height", "title", "font_size", "labels", "show_legend",
            "legend_alignment", "image_background_color", "data_background_color",
        ),
    ),
    _group(
        "signal_plot_options",
        "Signal plot options",
        (
            "x_axis_interval", "y_axis_interval", "logarithmic_y_axis", "colors",
            "line_styles", "line_widths", "marker_shapes", "marker_sizes",
            "x_axis_label", "y_axis_label",
        ),
    ),
)

SIGNAL_PLOT_SPEC = builtin_node_type_spec(
    type_id=SIGNAL_PLOT_TYPE_ID,
    display_name="Signal Plot",
    category_path=("Plot",),
    description="Create an evenly spaced Signal plot of your datapoints.",
    keywords=("signal", "line plot", "chart"),
    ports=SIGNAL_PLOT_PORTS,
    properties=SIGNAL_PLOT_PROPERTIES,
    settings_groups=SIGNAL_PLOT_SETTINGS_GROUPS,
)


class SignalPlotNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return SIGNAL_PLOT_SPEC

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        from ea_node_editor.execution.signal_plot_renderer import render_signal_plot

        values: dict[str, Any] = {prop.key: prop.default for prop in SIGNAL_PLOT_PROPERTIES}
        values.update(dict(ctx.properties or {}))
        values.update(dict(ctx.inputs or {}))
        image, warnings = render_signal_plot(values)
        return NodeResult(outputs={"image": image}, warnings=warnings)


SIGNAL_PLOT_NODE_DESCRIPTOR = PluginDescriptor(spec=SIGNAL_PLOT_SPEC, factory=SignalPlotNodePlugin)

__all__ = [
    "LINE_STYLE_LABELS",
    "MARKER_LABELS",
    "SIGNAL_PLOT_NODE_DESCRIPTOR",
    "SIGNAL_PLOT_PORTS",
    "SIGNAL_PLOT_PROPERTIES",
    "SIGNAL_PLOT_SETTINGS_GROUPS",
    "SIGNAL_PLOT_SPEC",
    "SIGNAL_PLOT_TYPE_ID",
    "SignalPlotNodePlugin",
]
