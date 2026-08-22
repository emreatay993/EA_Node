from __future__ import annotations

import keyword
import json
import math
import traceback
from collections.abc import Mapping
from typing import Literal

from ea_node_editor.graph.boundary_adapters import register_node_type_size_resolver
from ea_node_editor.nodes.builtins.data_control import NUMBER_SLIDER_PILL_HEIGHT
from ea_node_editor.nodes.builtins.icon_catalog import builtin_node_type, builtin_node_type_spec
from ea_node_editor.nodes.decorators import (
    out_port,
    plugin_descriptor,
    prop_json,
)
from ea_node_editor.nodes.execution_context import ExecutionContext, NodeResult
from ea_node_editor.nodes.node_specs import (
    DynamicPortGroupSpec,
    NodeTypeSpec,
    PortSpec,
    PropertySpec,
)
from ea_node_editor.runtime_contracts import DataTree
from ea_node_editor.runtime_contracts.data_tree import resolve_single_run_inputs


PYTHON_SCRIPT_DEFAULT_SOURCE = "result = payload\n"
PYTHON_SCRIPT_INPUT_NAMES_PROPERTY = "input_names"
PYTHON_SCRIPT_OUTPUT_NAMES_PROPERTY = "output_names"
DEFAULT_PYTHON_SCRIPT_INPUT_NAMES = ("payload",)
DEFAULT_PYTHON_SCRIPT_OUTPUT_NAMES = ("result",)
_PYTHON_SCRIPT_RESERVED_NAMES = {"ctx", "__builtins__"}


@builtin_node_type(
    type_id="core.constant",
    display_name="Constant",
    category_path=("Core",),
    description="Publishes a reusable JSON-compatible value and its text representation.",
    keywords=("constant", "value", "json"),
    ports=(
        out_port(
            "value",
            kind="data",
            data_type='COREX.DataTypes.Any',
            exposed=True,
            description="The configured JSON-compatible value.",
        ),
        out_port(
            "as_text",
            kind="data",
            data_type='COREX.DataTypes.String',
            exposed=True,
            description="The configured value serialized as JSON text.",
        ),
    ),
    properties=(
        prop_json("value", {"value": 0}, "Value"),
    ),
)
class ConstantNodePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        value = ctx.properties.get("value", {"value": 0})
        try:
            as_text = json.dumps(value, sort_keys=True, ensure_ascii=True)
        except TypeError as exc:
            raise ValueError("Constant node value must be JSON serializable.") from exc
        return NodeResult(outputs={"value": value, "as_text": as_text})


class LoggerNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return builtin_node_type_spec(
            type_id="core.logger",
            display_name="Logger",
            category_path=("Core",),
            description="Writes an informational, warning, or error message to the workflow run log.",
            keywords=("log", "message", "diagnostics"),
            ports=(
                PortSpec(
                    "message",
                    "in",
                    "data",
                    'COREX.DataTypes.String',
                    required=False,
                    uses_property_default=True,
                    data_access="tree",
                    description="Message to log; overrides the configured Message property when connected.",
                ),
            ),
            properties=(
                PropertySpec("message", "str", "log message", "Message", inline_editor="text"),
                PropertySpec(
                    "level",
                    "enum",
                    "info",
                    "Level",
                    enum_values=("info", "warning", "error"),
                    inline_editor="enum",
                ),
            ),
        )

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        inputs = resolve_single_run_inputs(ctx.inputs, node_name="Logger")
        message = str(inputs.get("message", ctx.properties.get("message", "")))
        level = str(ctx.properties.get("level", "info")).strip().lower()
        if level not in {"info", "warning", "error"}:
            ctx.log_warning(f"Logger level '{level}' is invalid; using 'info'.")
            level = "info"
        if level == "warning":
            ctx.log_warning(message)
        elif level == "error":
            ctx.log_error(message)
        else:
            ctx.log_info(message)
        return NodeResult()


_PYTHON_SCRIPT_FRAME_FILENAME = "<string>"
_PYTHON_SCRIPT_FRAME_DISPLAY = "<script>"


class PythonScriptError(RuntimeError):
    """Raised when a Python Script node's user code fails.

    Carries a traceback limited to the user's own script frames so host
    internals stay hidden unless developer mode is active.
    """

    def __init__(self, message: str, *, user_traceback: str) -> None:
        super().__init__(message)
        self.user_traceback = user_traceback


def _sanitize_user_script_traceback(exc: BaseException) -> str:
    user_frames = [
        frame
        for frame in traceback.extract_tb(exc.__traceback__)
        if frame.filename == _PYTHON_SCRIPT_FRAME_FILENAME
    ]
    exception_only = traceback.format_exception_only(type(exc), exc)
    if not user_frames:
        return "".join(exception_only).strip()
    relabeled = [
        traceback.FrameSummary(
            _PYTHON_SCRIPT_FRAME_DISPLAY,
            frame.lineno,
            frame.name,
            line=frame.line,
        )
        for frame in user_frames
    ]
    return "".join(
        [
            "Traceback (most recent call last):\n",
            *traceback.format_list(relabeled),
            *exception_only,
        ]
    ).strip()


def _normalize_python_script_names(
    value: object,
    *,
    default: tuple[str, ...],
    blocked: tuple[str, ...] = (),
) -> tuple[str, ...]:
    candidates = value if isinstance(value, list) else default
    names: list[str] = []
    used = set(blocked)
    for item in candidates:
        if not isinstance(item, str):
            continue
        name = item.strip()
        if (
            not name.isidentifier()
            or keyword.iskeyword(name)
            or name in _PYTHON_SCRIPT_RESERVED_NAMES
            or name in used
        ):
            continue
        names.append(name)
        used.add(name)
    return tuple(names)


def normalize_python_script_input_names(properties: Mapping[str, object]) -> tuple[str, ...]:
    return _normalize_python_script_names(
        properties.get(PYTHON_SCRIPT_INPUT_NAMES_PROPERTY),
        default=DEFAULT_PYTHON_SCRIPT_INPUT_NAMES,
    )


def normalize_python_script_output_names(properties: Mapping[str, object]) -> tuple[str, ...]:
    input_names = normalize_python_script_input_names(properties)
    return _normalize_python_script_names(
        properties.get(PYTHON_SCRIPT_OUTPUT_NAMES_PROPERTY),
        default=DEFAULT_PYTHON_SCRIPT_OUTPUT_NAMES,
        blocked=input_names,
    )


def _python_script_ports(
    names: tuple[str, ...],
    *,
    direction: Literal["in", "out"],
) -> tuple[PortSpec, ...]:
    return tuple(
        PortSpec(
            name,
            direction,
            "data",
            'COREX.DataTypes.Any',
            label=name,
            required=False if direction == "in" else None,
            exposed=True,
            data_access="item",
            description=f"Python variable {name}.",
        )
        for name in names
    )


def resolve_python_script_input_ports(
    properties: Mapping[str, object],
) -> tuple[PortSpec, ...]:
    return _python_script_ports(
        normalize_python_script_input_names(properties),
        direction="in",
    )


def resolve_python_script_output_ports(
    properties: Mapping[str, object],
) -> tuple[PortSpec, ...]:
    return _python_script_ports(
        normalize_python_script_output_names(properties),
        direction="out",
    )


def _next_python_script_port_key(
    properties: Mapping[str, object],
    *,
    prefix: str,
) -> str:
    used = set(normalize_python_script_input_names(properties))
    used.update(normalize_python_script_output_names(properties))
    suffix = 1
    while f"{prefix}{suffix}" in used:
        suffix += 1
    return f"{prefix}{suffix}"


def next_python_script_input_key(properties: Mapping[str, object]) -> str:
    return _next_python_script_port_key(properties, prefix="input")


def next_python_script_output_key(properties: Mapping[str, object]) -> str:
    return _next_python_script_port_key(properties, prefix="output")


def rename_python_script_port_key(
    properties: Mapping[str, object],
    current_key: str,
    value: str,
) -> str:
    renamed_key = value.strip()
    if (
        not renamed_key.isidentifier()
        or keyword.iskeyword(renamed_key)
        or renamed_key in _PYTHON_SCRIPT_RESERVED_NAMES
    ):
        raise ValueError(f"Invalid Python port name: {value!r}.")
    used = set(normalize_python_script_input_names(properties))
    used.update(normalize_python_script_output_names(properties))
    used.discard(current_key)
    if renamed_key in used:
        raise ValueError(f"Python port name already exists: {renamed_key}.")
    return renamed_key


class PythonScriptNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return builtin_node_type_spec(
            type_id="core.python_script",
            display_name="Python Script",
            category_path=("Core",),
            description="Runs custom Python logic in trusted local mode.",
            keywords=("python", "script", "code"),
            ports=(),
            properties=(
                PropertySpec(
                    "script",
                    "str",
                    PYTHON_SCRIPT_DEFAULT_SOURCE,
                    "Script",
                ),
                PropertySpec(
                    "timeout_sec",
                    "float",
                    0.0,
                    "Timeout (sec)",
                ),
                PropertySpec(
                    PYTHON_SCRIPT_INPUT_NAMES_PROPERTY,
                    "json",
                    list(DEFAULT_PYTHON_SCRIPT_INPUT_NAMES),
                    "Inputs",
                    inspector_visible=False,
                ),
                PropertySpec(
                    PYTHON_SCRIPT_OUTPUT_NAMES_PROPERTY,
                    "json",
                    list(DEFAULT_PYTHON_SCRIPT_OUTPUT_NAMES),
                    "Outputs",
                    inspector_visible=False,
                ),
            ),
            dynamic_port_groups=(
                DynamicPortGroupSpec(
                    group_id="inputs",
                    property_key=PYTHON_SCRIPT_INPUT_NAMES_PROPERTY,
                    direction="in",
                    ports_resolver=resolve_python_script_input_ports,
                    key_factory=next_python_script_input_key,
                    minimum=0,
                    rename_mode="key",
                    key_renamer=rename_python_script_port_key,
                ),
                DynamicPortGroupSpec(
                    group_id="outputs",
                    property_key=PYTHON_SCRIPT_OUTPUT_NAMES_PROPERTY,
                    direction="out",
                    ports_resolver=resolve_python_script_output_ports,
                    key_factory=next_python_script_output_key,
                    minimum=0,
                    rename_mode="key",
                    key_renamer=rename_python_script_port_key,
                ),
            ),
        )

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        script = str(ctx.properties.get("script", ""))
        if not script.strip():
            return NodeResult()

        input_names = normalize_python_script_input_names(ctx.properties)
        output_names = normalize_python_script_output_names(ctx.properties)
        scope = {
            "ctx": ctx,
            **{name: ctx.inputs.get(name) for name in input_names},
        }
        try:
            exec(
                compile(script, _PYTHON_SCRIPT_FRAME_FILENAME, "exec"),
                scope,
                scope,
            )
        except Exception as exc:  # noqa: BLE001
            user_traceback = _sanitize_user_script_traceback(exc)
            ctx.log_error(traceback.format_exc() if ctx.developer_mode else user_traceback)
            raise PythonScriptError(
                f"Python Script execution failed: {exc}",
                user_traceback=user_traceback,
            ) from exc

        return NodeResult(
            outputs={
                name: scope[name]
                for name in output_names
                if name in scope
            }
        )


TRIGGER_TYPE_ID = "core.trigger"
TRIGGER_SURFACE_VARIANT = "trigger"
# Button-only pill: narrower than the slider/select pills but height-locked to
# the same shared pill height (see _trigger_node_size and standard_metrics).
TRIGGER_DEFAULT_WIDTH = 160.0
TRIGGER_MIN_WIDTH = 120.0


class TriggerNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id=TRIGGER_TYPE_ID,
            display_name="Trigger",
            category_path=("Data", "Control"),
            description="Stop downstream nodes from running until you click the button.",
            icon="",
            keywords=("button", "action", "run", "dam", "gate", "block"),
            ports=(
                PortSpec(
                    "input",
                    "in",
                    "data",
                    'COREX.DataTypes.Any',
                    label="Input",
                    required=False,
                    data_access="tree",
                    description="The data that is blocked until you click the button.",
                ),
                PortSpec(
                    "output",
                    "out",
                    "data",
                    'COREX.DataTypes.Any',
                    label="Output",
                    data_access="tree",
                    description=(
                        "The current output. The output is not updated until you "
                        "click the button."
                    ),
                ),
            ),
            properties=(),
            collapsible=False,
            surface_variant=TRIGGER_SURFACE_VARIANT,
        )

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        value = ctx.inputs["input"] if "input" in ctx.inputs else DataTree.from_item(True)
        return NodeResult(outputs={"output": value})


def _trigger_node_size(node, _spec, *, base_width: float, base_height: float) -> tuple[float, float]:
    del base_height
    width = float(base_width)
    if getattr(node, "custom_width", None) is None:
        width = max(width, TRIGGER_DEFAULT_WIDTH)
    return max(width, TRIGGER_MIN_WIDTH), NUMBER_SLIDER_PILL_HEIGHT


register_node_type_size_resolver(TRIGGER_TYPE_ID, _trigger_node_size)


class IfNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return builtin_node_type_spec(
            type_id="core.if",
            display_name="If",
            category_path=("Core",),
            description="Selects one of two data trees from a Boolean condition.",
            keywords=("if", "condition", "select", "branch"),
            ports=(
                PortSpec(
                    "condition",
                    "in",
                    "data",
                    'COREX.DataTypes.Bool',
                    required=True,
                    description="Boolean item selecting the true or false value.",
                ),
                PortSpec(
                    "true_value",
                    "in",
                    "data",
                    'COREX.DataTypes.Any',
                    required=True,
                    data_access="tree",
                    description="Tree returned when Condition is true.",
                ),
                PortSpec(
                    "false_value",
                    "in",
                    "data",
                    'COREX.DataTypes.Any',
                    required=False,
                    data_access="tree",
                    description="Optional tree returned when Condition is false.",
                ),
                PortSpec(
                    "result",
                    "out",
                    "data",
                    'COREX.DataTypes.Any',
                    data_access="tree",
                    description="Selected tree; empty when the optional false value is absent.",
                ),
            ),
            properties=(),
        )

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        key = "true_value" if bool(ctx.inputs["condition"]) else "false_value"
        if key not in ctx.inputs:
            return NodeResult()
        return NodeResult(outputs={"result": ctx.inputs[key]})


STREAM_GATE_OUTPUT_IDS_PROPERTY = "output_port_ids"
DEFAULT_STREAM_GATE_OUTPUT_IDS = ("output_0", "output_1")


def normalize_stream_gate_output_ids(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return DEFAULT_STREAM_GATE_OUTPUT_IDS
    output_ids: list[str] = []
    for item in value:
        output_id = str(item).strip()
        if output_id and output_id not in {"stream", "gate"} and output_id not in output_ids:
            output_ids.append(output_id)
    return tuple(output_ids) or DEFAULT_STREAM_GATE_OUTPUT_IDS


def resolve_stream_gate_output_ports(
    properties: Mapping[str, object],
) -> tuple[PortSpec, ...]:
    return tuple(
        PortSpec(
            output_id,
            "out",
            "data",
            'COREX.DataTypes.Any',
            label=f"Output {ordinal}",
            data_access="tree",
            description=f"Tree published when Gate selects output {ordinal}.",
        )
        for ordinal, output_id in enumerate(
            normalize_stream_gate_output_ids(
                properties.get(
                    STREAM_GATE_OUTPUT_IDS_PROPERTY,
                    DEFAULT_STREAM_GATE_OUTPUT_IDS,
                )
            )
        )
    )


def next_stream_gate_output_id(properties: Mapping[str, object]) -> str:
    used = set(
        normalize_stream_gate_output_ids(
            properties.get(
                STREAM_GATE_OUTPUT_IDS_PROPERTY,
                DEFAULT_STREAM_GATE_OUTPUT_IDS,
            )
        )
    )
    suffix = 0
    while f"output_{suffix}" in used:
        suffix += 1
    return f"output_{suffix}"


def stream_gate_index(value: object) -> int:
    if isinstance(value, (bool, str, bytes, bytearray)):
        raise ValueError("Stream Gate gate must be numeric.")
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Stream Gate gate must be numeric.") from exc
    if not math.isfinite(numeric):
        raise ValueError("Stream Gate gate must be finite.")
    return math.floor(numeric + 0.5) if numeric >= 0 else math.ceil(numeric - 0.5)


class StreamGateNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return builtin_node_type_spec(
            type_id="core.stream_gate",
            display_name="Stream Gate",
            category_path=("Core",),
            description="Routes a data tree to one selected output.",
            keywords=("stream", "gate", "route", "switch"),
            ports=(
                PortSpec(
                    "stream",
                    "in",
                    "data",
                    'COREX.DataTypes.Any',
                    required=True,
                    data_access="tree",
                    description="Tree to route.",
                ),
                PortSpec(
                    "gate",
                    "in",
                    "data",
                    'COREX.DataTypes.Double',
                    required=False,
                    uses_property_default=True,
                    accepted_data_types=('COREX.DataTypes.Double', 'COREX.DataTypes.Int'),
                    description="Zero-based output index; midpoint values round away from zero.",
                ),
            ),
            properties=(
                PropertySpec("gate", "float", 0.0, "Gate", inline_editor="number"),
                PropertySpec(
                    STREAM_GATE_OUTPUT_IDS_PROPERTY,
                    "json",
                    list(DEFAULT_STREAM_GATE_OUTPUT_IDS),
                    "Outputs",
                    inspector_visible=False,
                ),
            ),
            dynamic_port_groups=(
                DynamicPortGroupSpec(
                    group_id="outputs",
                    property_key=STREAM_GATE_OUTPUT_IDS_PROPERTY,
                    direction="out",
                    ports_resolver=resolve_stream_gate_output_ports,
                    key_factory=next_stream_gate_output_id,
                    minimum=1,
                    rename_mode="label",
                ),
            ),
        )

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        output_ids = normalize_stream_gate_output_ids(
            ctx.properties.get(STREAM_GATE_OUTPUT_IDS_PROPERTY, DEFAULT_STREAM_GATE_OUTPUT_IDS)
        )
        index = stream_gate_index(ctx.inputs.get("gate", ctx.properties.get("gate", 0.0)))
        if index < 0 or index >= len(output_ids):
            raise ValueError(
                f"Stream Gate output index {index} is outside 0..{len(output_ids) - 1}."
            )
        return NodeResult(outputs={output_ids[index]: ctx.inputs["stream"]})


CORE_NODE_DESCRIPTORS = (
    plugin_descriptor(ConstantNodePlugin),
    plugin_descriptor(LoggerNodePlugin),
    plugin_descriptor(PythonScriptNodePlugin),
    plugin_descriptor(TriggerNodePlugin),
    plugin_descriptor(IfNodePlugin),
    plugin_descriptor(StreamGateNodePlugin),
)


__all__ = [
    "CORE_NODE_DESCRIPTORS",
    "DEFAULT_STREAM_GATE_OUTPUT_IDS",
    "STREAM_GATE_OUTPUT_IDS_PROPERTY",
    "IfNodePlugin",
    "StreamGateNodePlugin",
    "TriggerNodePlugin",
    "normalize_stream_gate_output_ids",
    "stream_gate_index",
]
