# Purpose: Hold inert decorated source for ordinary core and value built-ins.
# Map: subsystems/nodes_registry_builtins.md
# Tests: tests/test_builtin_function_infrastructure.py

SOURCE = '''import corex

from ea_node_editor.nodes.builtins.core_values import (
    COLOR_DATA_TYPE_ID,
    is_color_payload,
)
from ea_node_editor.runtime_contracts import TypedInlineValue


@corex.node(
    id="core.if",
    name="If",
    category=("Core",),
    icon="call_split",
    description="Selects one of two data trees from a Boolean condition.",
    keywords=("if", "condition", "select", "branch"),
)
@corex.input(
    "condition",
    value_type="COREX.DataTypes.Bool",
    label="",
    required=True,
    description="Boolean item selecting the true or false value.",
)
@corex.input(
    "true_value",
    value_type="COREX.DataTypes.Any",
    structure="tree",
    label="",
    required=True,
    description="Tree returned when Condition is true.",
)
@corex.input(
    "false_value",
    value_type="COREX.DataTypes.Any",
    structure="tree",
    label="",
    required=False,
    description="Optional tree returned when Condition is false.",
)
@corex.output(
    "result",
    value_type="COREX.DataTypes.Any",
    structure="tree",
    label="",
    description="Selected tree; empty when the optional false value is absent.",
)
def core_if(ctx, condition, true_value, false_value):
    key = "true_value" if bool(condition) else "false_value"
    if key not in ctx.inputs:
        return {}
    return {"result": true_value if key == "true_value" else false_value}


@corex.node(
    id="data.deconstruct_color",
    name="Deconstruct Color",
    category=("Utilities", "Color"),
    icon="palette",
    description="Extracts the stored channels from a typed Color value.",
    keywords=("color", "deconstruct", "red", "green", "blue", "alpha"),
)
@corex.input(
    "color",
    value_type="COREX.DataTypes.Color",
    label="Color",
    required=True,
)
@corex.output("red", value_type="COREX.DataTypes.Double", label="Red")
@corex.output("green", value_type="COREX.DataTypes.Double", label="Green")
@corex.output("blue", value_type="COREX.DataTypes.Double", label="Blue")
@corex.output("alpha", value_type="COREX.DataTypes.Double", label="Alpha")
def deconstruct_color(ctx, color):
    del ctx
    if (
        not isinstance(color, TypedInlineValue)
        or color.data_type_id != COLOR_DATA_TYPE_ID
        or color.schema_version != 1
        or not is_color_payload(color.payload)
    ):
        raise ValueError("Color input is invalid")
    payload = color.payload
    return {
        "red": payload["R"],
        "green": payload["G"],
        "blue": payload["B"],
        "alpha": payload["A"],
    }
'''

__all__ = ["SOURCE"]
