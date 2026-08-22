# Purpose: Provide ordered Interval 1D construction and decomposition built-ins.
# Map: docs/agent_maps/subsystems/nodes_registry_builtins.md
# Tests: tests/test_interval_nodes.py

from __future__ import annotations

from ea_node_editor.nodes.builtins.icon_catalog import builtin_node_type
from ea_node_editor.nodes.decorators import out_port, plugin_descriptor, prop_float
from ea_node_editor.nodes.execution_context import ExecutionContext, NodeResult
from ea_node_editor.nodes.node_specs import PortSpec
from ea_node_editor.runtime_contracts import (
    Interval1D,
    coerce_interval_1d,
)


CONSTRUCT_INTERVAL_TYPE_ID = "math.construct_interval"
DECONSTRUCT_INTERVAL_TYPE_ID = "math.deconstruct_interval"


@builtin_node_type(
    type_id=CONSTRUCT_INTERVAL_TYPE_ID,
    display_name="Construct Interval",
    category_path=("Math", "Interval"),
    description="Constructs an ordered Interval 1D from Start and End values.",
    keywords=("interval", "construct", "range", "start", "end"),
    ports=(
        PortSpec(
            "start",
            "in",
            "data",
            'COREX.DataTypes.Double',
            label="Start",
            required=False,
            uses_property_default=True,
            accepted_data_types=('COREX.DataTypes.Double', 'COREX.DataTypes.Int'),
            description="Interval start value; overrides the configured Start property when connected.",
        ),
        PortSpec(
            "end",
            "in",
            "data",
            'COREX.DataTypes.Double',
            label="End",
            required=False,
            uses_property_default=True,
            accepted_data_types=('COREX.DataTypes.Double', 'COREX.DataTypes.Int'),
            description="Interval end value; overrides the configured End property when connected.",
        ),
        out_port(
            "interval",
            data_type='COREX.DataTypes.Interval1D',
            description="Ordered Interval 1D containing the original Start and End endpoints.",
        ),
    ),
    properties=(
        prop_float("start", 0.0, "Start", inline_editor="number"),
        prop_float("end", 1.0, "End", inline_editor="number"),
    ),
)
class ConstructIntervalNodePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        start = ctx.inputs.get("start", ctx.properties.get("start", 0.0))
        end = ctx.inputs.get("end", ctx.properties.get("end", 1.0))
        return NodeResult(outputs={"interval": Interval1D(start, end)})


@builtin_node_type(
    type_id=DECONSTRUCT_INTERVAL_TYPE_ID,
    display_name="Deconstruct Interval",
    category_path=("Math", "Interval"),
    description="Extracts the original ordered Start and End endpoints from an Interval 1D.",
    keywords=("interval", "deconstruct", "range", "start", "end"),
    ports=(
        PortSpec(
            "interval",
            "in",
            "data",
            'COREX.DataTypes.Interval1D',
            label="Interval",
            required=True,
            description="Interval 1D whose original endpoints will be extracted.",
        ),
        out_port(
            "start",
            data_type='COREX.DataTypes.Double',
            description="Original Interval 1D Start endpoint.",
        ),
        out_port(
            "end",
            data_type='COREX.DataTypes.Double',
            description="Original Interval 1D End endpoint.",
        ),
    ),
    properties=(),
)
class DeconstructIntervalNodePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        interval = coerce_interval_1d(ctx.inputs["interval"])
        return NodeResult(outputs={"start": interval.start, "end": interval.end})


MATH_INTERVAL_NODE_DESCRIPTORS = (
    plugin_descriptor(ConstructIntervalNodePlugin),
    plugin_descriptor(DeconstructIntervalNodePlugin),
)


__all__ = [
    "CONSTRUCT_INTERVAL_TYPE_ID",
    "DECONSTRUCT_INTERVAL_TYPE_ID",
    "ConstructIntervalNodePlugin",
    "DeconstructIntervalNodePlugin",
    "MATH_INTERVAL_NODE_DESCRIPTORS",
]
