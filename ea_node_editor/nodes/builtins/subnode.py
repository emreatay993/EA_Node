from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

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
SUBNODE_PIN_TYPE_IDS = frozenset({SUBNODE_INPUT_TYPE_ID, SUBNODE_OUTPUT_TYPE_ID})
SUBNODE_AUTHORING_TYPE_IDS = frozenset({SUBNODE_TYPE_ID, *SUBNODE_PIN_TYPE_IDS})
_SUBNODE_FLOW_KINDS = frozenset({"exec", "completed", "failed"})


@dataclass(slots=True, frozen=True)
class SubnodePinDefinition:
    pin_type_id: str
    label: str
    kind: str
    data_type: str
    pin_port_direction: str
    shell_port_direction: str


def is_subnode_shell_type(type_id: object) -> bool:
    return str(type_id).strip() == SUBNODE_TYPE_ID


def is_subnode_input_type(type_id: object) -> bool:
    return str(type_id).strip() == SUBNODE_INPUT_TYPE_ID


def is_subnode_output_type(type_id: object) -> bool:
    return str(type_id).strip() == SUBNODE_OUTPUT_TYPE_ID


def is_subnode_pin_type(type_id: object) -> bool:
    return str(type_id).strip() in SUBNODE_PIN_TYPE_IDS


def is_subnode_authoring_type(type_id: object) -> bool:
    return str(type_id).strip() in SUBNODE_AUTHORING_TYPE_IDS


def default_subnode_pin_label(pin_type_id: object) -> str:
    return "Input" if is_subnode_input_type(pin_type_id) else "Output"


def normalize_subnode_pin_kind(value: object) -> str:
    normalized = str(value or "data").strip().lower()
    if normalized not in set(SUBNODE_PIN_KIND_VALUES):
        return "data"
    return normalized


def normalize_subnode_pin_data_type(kind: object, value: object) -> str:
    normalized_kind = normalize_subnode_pin_kind(kind)
    if normalized_kind in _SUBNODE_FLOW_KINDS:
        return "any"
    normalized = str(value or "any").strip().lower()
    return normalized or "any"


def resolve_subnode_pin_definition(
    pin_type_id: object,
    properties: Mapping[str, object] | None = None,
) -> SubnodePinDefinition:
    normalized_type_id = str(pin_type_id).strip()
    if not is_subnode_pin_type(normalized_type_id):
        raise ValueError(f"Unsupported subnode pin type: {pin_type_id!r}")
    raw_properties = properties if properties is not None else {}
    default_label = default_subnode_pin_label(normalized_type_id)
    label = str(raw_properties.get(SUBNODE_PIN_LABEL_PROPERTY, default_label)).strip() or default_label
    kind = normalize_subnode_pin_kind(raw_properties.get(SUBNODE_PIN_KIND_PROPERTY, "data"))
    data_type = normalize_subnode_pin_data_type(
        kind,
        raw_properties.get(SUBNODE_PIN_DATA_TYPE_PROPERTY, "any"),
    )
    pin_port_direction = "out" if is_subnode_input_type(normalized_type_id) else "in"
    shell_port_direction = "in" if is_subnode_input_type(normalized_type_id) else "out"
    return SubnodePinDefinition(
        pin_type_id=normalized_type_id,
        label=label,
        kind=kind,
        data_type=data_type,
        pin_port_direction=pin_port_direction,
        shell_port_direction=shell_port_direction,
    )


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
    "SUBNODE_AUTHORING_TYPE_IDS",
    "SUBNODE_PIN_DATA_TYPE_PROPERTY",
    "SUBNODE_PIN_TYPE_IDS",
    "SUBNODE_PIN_KIND_PROPERTY",
    "SUBNODE_PIN_KIND_VALUES",
    "SUBNODE_PIN_LABEL_PROPERTY",
    "SUBNODE_PIN_PORT_KEY",
    "SUBNODE_INPUT_TYPE_ID",
    "SUBNODE_OUTPUT_TYPE_ID",
    "SUBNODE_TYPE_ID",
    "SubnodePinDefinition",
    "SubnodeInputNodePlugin",
    "SubnodeNodePlugin",
    "SubnodeOutputNodePlugin",
    "default_subnode_pin_label",
    "is_subnode_authoring_type",
    "is_subnode_input_type",
    "is_subnode_output_type",
    "is_subnode_pin_type",
    "is_subnode_shell_type",
    "normalize_subnode_pin_data_type",
    "normalize_subnode_pin_kind",
    "resolve_subnode_pin_definition",
]
