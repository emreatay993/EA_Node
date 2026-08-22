# Purpose: Adopt the two statically proven COREX deconstruction node shapes.
# Map: subsystems/nodes_registry_builtins.md
# Tests: tests/test_core_value_nodes.py

from __future__ import annotations


from ea_node_editor.nodes.builtins.math_interval import (
    DECONSTRUCT_INTERVAL_TYPE_ID,
    MATH_INTERVAL_NODE_DESCRIPTORS,
)
from ea_node_editor.nodes.builtins.core_values import (
    COLOR_DATA_TYPE_ID,
    is_color_payload,
)
from ea_node_editor.nodes.core_data_types import (
    DOUBLE_DATA_TYPE_ID,
)
from ea_node_editor.nodes.decorators import node_type, plugin_descriptor
from ea_node_editor.nodes.execution_context import ExecutionContext, NodeResult
from ea_node_editor.nodes.node_specs import PortSpec
from ea_node_editor.nodes.plugin_contracts import (
    PluginContractManifest,
)
from ea_node_editor.runtime_contracts import TypedInlineValue


COREX_CORE_VALUE_NODE_OWNER_ID = "corex.core_value_nodes"
COREX_CORE_VALUE_NODE_OWNER_VERSION = "1"

DECONSTRUCT_COLOR_TYPE_ID = "data.deconstruct_color"















@node_type(
    type_id=DECONSTRUCT_COLOR_TYPE_ID,
    display_name="Deconstruct Color",
    category_path=("Utilities", "Color"),
    icon="palette",
    description="Extracts the stored channels from a typed Color value.",
    keywords=("color", "deconstruct", "red", "green", "blue", "alpha"),
    ports=(
        PortSpec(
            "color",
            "in",
            "data",
            COLOR_DATA_TYPE_ID,
            label="Color",
            required=True,
        ),
        PortSpec(
            "red",
            "out",
            "data",
            DOUBLE_DATA_TYPE_ID,
            label="Red",
        ),
        PortSpec(
            "green",
            "out",
            "data",
            DOUBLE_DATA_TYPE_ID,
            label="Green",
        ),
        PortSpec(
            "blue",
            "out",
            "data",
            DOUBLE_DATA_TYPE_ID,
            label="Blue",
        ),
        PortSpec(
            "alpha",
            "out",
            "data",
            DOUBLE_DATA_TYPE_ID,
            label="Alpha",
        ),
    ),
    properties=(),
)
class DeconstructColorNodePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        value = ctx.inputs["color"]
        if (
            not isinstance(value, TypedInlineValue)
            or value.data_type_id != COLOR_DATA_TYPE_ID
            or value.schema_version != 1
            or not is_color_payload(value.payload)
        ):
            raise ValueError("Color input is invalid")
        payload = value.payload
        return NodeResult(
            outputs={
                "red": payload["R"],
                "green": payload["G"],
                "blue": payload["B"],
                "alpha": payload["A"],
            }
        )


COREX_CORE_VALUE_NODE_NEW_DESCRIPTORS = (
    plugin_descriptor(DeconstructColorNodePlugin),
)

(_DECONSTRUCT_INTERVAL_DESCRIPTOR,) = (
    descriptor
    for descriptor in MATH_INTERVAL_NODE_DESCRIPTORS
    if descriptor.spec.type_id == DECONSTRUCT_INTERVAL_TYPE_ID
)

COREX_CORE_VALUE_NODE_BUNDLE_DESCRIPTORS = (
    _DECONSTRUCT_INTERVAL_DESCRIPTOR,
    *COREX_CORE_VALUE_NODE_NEW_DESCRIPTORS,
)


COREX_CORE_VALUE_NODE_CONTRACT_MANIFEST = PluginContractManifest(
)


__all__ = [
    "DECONSTRUCT_COLOR_TYPE_ID",
    "DeconstructColorNodePlugin",
    "COREX_CORE_VALUE_NODE_BUNDLE_DESCRIPTORS",
    "COREX_CORE_VALUE_NODE_CONTRACT_MANIFEST",
    "COREX_CORE_VALUE_NODE_NEW_DESCRIPTORS",
    "COREX_CORE_VALUE_NODE_OWNER_ID",
    "COREX_CORE_VALUE_NODE_OWNER_VERSION",
]
