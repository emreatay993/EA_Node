from __future__ import annotations

from ea_node_editor.nodes.decorators import in_port, node_type, out_port, prop_enum, prop_str
from ea_node_editor.nodes.types import ExecutionContext, NodeResult

SUBNODE_TYPE_ID = "core.subnode"
SUBNODE_INPUT_TYPE_ID = "core.subnode_input"
SUBNODE_OUTPUT_TYPE_ID = "core.subnode_output"

SUBNODE_PIN_PORT_KEY = "pin"
SUBNODE_PIN_LABEL_PROPERTY = "label"
SUBNODE_PIN_KIND_PROPERTY = "kind"
SUBNODE_PIN_DATA_TYPE_PROPERTY = "data_type"
SUBNODE_PIN_KIND_VALUES = ("data", "exec", "completed", "failed")


@node_type(
    type_id=SUBNODE_TYPE_ID,
    display_name="Subnode",
    category="Subnode",
    icon="account_tree",
    description="Container shell whose outer ports are derived from direct child pin nodes.",
    ports=(),
    properties=(),
    runtime_behavior="compile_only",
)
class SubnodeNodePlugin:
    def execute(self, _ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={})


@node_type(
    type_id=SUBNODE_INPUT_TYPE_ID,
    display_name="Subnode Input",
    category="Subnode",
    icon="input",
    description="Pin node that exposes one input port on its parent subnode shell.",
    ports=(out_port(SUBNODE_PIN_PORT_KEY, kind="data", data_type="any"),),
    properties=(
        prop_str(SUBNODE_PIN_LABEL_PROPERTY, "Input", "Label"),
        prop_enum(
            SUBNODE_PIN_KIND_PROPERTY,
            "data",
            "Kind",
            values=SUBNODE_PIN_KIND_VALUES,
        ),
        prop_str(SUBNODE_PIN_DATA_TYPE_PROPERTY, "any", "Data Type"),
    ),
    runtime_behavior="compile_only",
)
class SubnodeInputNodePlugin:
    def execute(self, _ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={})


@node_type(
    type_id=SUBNODE_OUTPUT_TYPE_ID,
    display_name="Subnode Output",
    category="Subnode",
    icon="output",
    description="Pin node that exposes one output port on its parent subnode shell.",
    ports=(in_port(SUBNODE_PIN_PORT_KEY, kind="data", data_type="any"),),
    properties=(
        prop_str(SUBNODE_PIN_LABEL_PROPERTY, "Output", "Label"),
        prop_enum(
            SUBNODE_PIN_KIND_PROPERTY,
            "data",
            "Kind",
            values=SUBNODE_PIN_KIND_VALUES,
        ),
        prop_str(SUBNODE_PIN_DATA_TYPE_PROPERTY, "any", "Data Type"),
    ),
    runtime_behavior="compile_only",
)
class SubnodeOutputNodePlugin:
    def execute(self, _ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={})


__all__ = [
    "SUBNODE_PIN_DATA_TYPE_PROPERTY",
    "SUBNODE_PIN_KIND_PROPERTY",
    "SUBNODE_PIN_KIND_VALUES",
    "SUBNODE_PIN_LABEL_PROPERTY",
    "SUBNODE_PIN_PORT_KEY",
    "SUBNODE_INPUT_TYPE_ID",
    "SUBNODE_OUTPUT_TYPE_ID",
    "SUBNODE_TYPE_ID",
    "SubnodeInputNodePlugin",
    "SubnodeNodePlugin",
    "SubnodeOutputNodePlugin",
]
