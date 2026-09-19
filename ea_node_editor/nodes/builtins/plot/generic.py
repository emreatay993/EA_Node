# Purpose: Prepare generic Plot requests and orchestrate plugin execution and exports.
# Map: feature_routes/plotter_nodes
# Tests: tests/test_plot_node_contracts.py, tests/test_generic_plot_preparation.py, tests/test_generic_plot_exports.py
from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from ea_node_editor.nodes.builtins.plot import data_series, exports, specs
from ea_node_editor.nodes.execution_context import ExecutionContext, NodeResult
from ea_node_editor.nodes.node_specs import NodeTypeSpec
from ea_node_editor.nodes.plugin_contracts import PluginDescriptor


def _string_property(properties: Mapping[str, Any], key: str) -> str:
    return str(properties.get(key, "") or "").strip()


def _mapping_property(properties: Mapping[str, Any], key: str, default: Mapping[str, Any]) -> dict[str, Any]:
    value = properties.get(key)
    if isinstance(value, Mapping):
        return {str(item_key): copy.deepcopy(item_value) for item_key, item_value in value.items()}
    if not default:
        return {}
    return copy.deepcopy(dict(default))


def _plot_options(definition: specs.PlotNodeDefinition, properties: Mapping[str, Any]) -> dict[str, Any]:
    options = _mapping_property(properties, "plot_options", {})
    options.update(
        {
            "axis_limits": _mapping_property(properties, "axis_limits", specs.PLOT_AXIS_LIMITS_DEFAULT),
            "log_scales": _mapping_property(properties, "log_scales", specs.PLOT_LOG_SCALES_DEFAULT),
            "grid": bool(properties.get("grid", True)),
            "legend": bool(properties.get("legend", True)),
            "render_in_canvas": bool(properties.get("render_in_canvas", False)),
            "z_label": _string_property(properties, "z_label"),
        }
    )
    if definition.supports_colormap:
        options["cmap"] = _string_property(properties, "colormap") or "viridis"
    return options


def build_generic_plot_render_request(
    *,
    node_type_id: str,
    properties: Mapping[str, Any],
    series_input: Any,
) -> tuple[Any, tuple[str, ...]]:
    from ea_node_editor.execution.plot_backend import build_plot_render_request

    definition = specs.PLOT_NODE_DEFINITION_BY_TYPE_ID.get(str(node_type_id or "").strip())
    if definition is None:
        raise ValueError(f"Unknown generic plot node type: {node_type_id!r}.")
    series, warnings = data_series.prepare_plot_series(
        series_input,
        plot_type=definition.plot_type,
        mapping=_mapping_property(properties, specs.PLOT_TABULAR_MAPPING_PROPERTY, {}),
    )
    return (
        build_plot_render_request(
            plot_type=definition.plot_type,
            series=series,
            properties=properties,
            options=_plot_options(definition, properties),
        ),
        warnings,
    )


class GenericPlotNodePlugin:
    def __init__(self, definition: specs.PlotNodeDefinition) -> None:
        self._definition = definition
        self._spec = specs.plot_node_spec(definition)

    def spec(self) -> NodeTypeSpec:
        return self._spec

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        properties = specs.plot_property_defaults(self._spec)
        properties.update(dict(ctx.properties or {}))
        render_request, warnings = build_generic_plot_render_request(
            node_type_id=self._definition.type_id,
            properties=properties,
            series_input=ctx.inputs.get("series"),
        )
        outputs: dict[str, Any] = {}
        if bool(properties.get("archive_export_on_run", False)):
            outputs.update(
                exports.archive_plot_exports(ctx, render_request, properties, definition=self._definition)
            )
        return NodeResult(outputs=outputs, warnings=warnings)


def _plot_descriptor(definition: specs.PlotNodeDefinition) -> PluginDescriptor:
    spec = specs.plot_node_spec(definition)
    return PluginDescriptor(
        spec=spec,
        factory=lambda definition=definition: GenericPlotNodePlugin(definition),
    )


PLOT_NODE_DESCRIPTORS = tuple(_plot_descriptor(definition) for definition in specs.PLOT_NODE_DEFINITIONS)

__all__ = ["GenericPlotNodePlugin", "PLOT_NODE_DESCRIPTORS", "build_generic_plot_render_request"]
