from __future__ import annotations

import json
import traceback
from typing import Any

from ea_node_editor.nodes.decorators import node_type, in_port, out_port, prop_json, prop_bool
from ea_node_editor.nodes.execution_context import ExecutionContext, NodeResult
from ea_node_editor.nodes.node_specs import NodeTypeSpec, PortSpec, PropertySpec


class StartNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id="core.start",
            display_name="Start",
            category_path=("Core",),
            icon="core/play_arrow.svg",
            description="Entry point for DAG execution.",
            ports=(
                PortSpec("exec_out", "out", "exec", "exec", exposed=True),
                PortSpec("trigger", "out", "data", "dict", exposed=True),
            ),
            properties=(),
        )

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={"trigger": dict(ctx.trigger), "exec_out": True}, completed=True)


class EndNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id="core.end",
            display_name="End",
            category_path=("Core",),
            icon="core/stop.svg",
            description="Terminal node for DAG execution.",
            ports=(
                PortSpec("exec_in", "in", "exec", "exec", required=True),
                PortSpec("done", "out", "completed", "bool", exposed=True),
            ),
            properties=(),
        )

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        return NodeResult(outputs={"done": True}, completed=True)


@node_type(
    type_id="core.constant",
    display_name="Constant",
    category_path=("Core",),
    icon="core/data_object.svg",
    description="Produces a constant JSON value.",
    ports=(
        out_port("value", kind="data", data_type="any", exposed=True),
        out_port("as_text", kind="data", data_type="str", exposed=True),
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
        return NodeTypeSpec(
            type_id="core.logger",
            display_name="Logger",
            category_path=("Core",),
            icon="core/article.svg",
            description="Writes a message into the run log.",
            ports=(
                PortSpec("exec_in", "in", "exec", "exec", required=True),
                PortSpec("message", "in", "data", "str", required=False),
                PortSpec("exec_out", "out", "exec", "exec", exposed=True),
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
        message = str(ctx.inputs.get("message", ctx.properties.get("message", "")))
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
        return NodeResult(outputs={"exec_out": True})


class PythonScriptNodePlugin:
    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id="core.python_script",
            display_name="Python Script",
            category_path=("Core",),
            icon="core/code.svg",
            description="Runs custom Python logic in trusted local mode.",
            ports=(
                PortSpec("exec_in", "in", "exec", "exec", required=True),
                PortSpec("payload", "in", "data", "any", required=False),
                PortSpec("result", "out", "data", "any", exposed=True),
                PortSpec("exec_out", "out", "exec", "exec", exposed=True),
                PortSpec("on_failed", "out", "failed", "any", exposed=True),
            ),
            properties=(
                PropertySpec(
                    "script",
                    "str",
                    (
                        "# input_data is provided by the engine\n"
                        "# Set output_data to publish result\n"
                        "output_data = input_data\n"
                    ),
                    "Script",
                ),
            ),
        )

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        script = str(ctx.properties.get("script", "")).strip()
        if not script:
            return NodeResult(outputs={"result": ctx.inputs.get("payload"), "exec_out": True})

        payload = ctx.inputs.get("payload")
        local_scope: dict[str, Any] = {
            "input_data": payload,
            "output_data": payload,
            "ctx": ctx,
        }
        try:
            exec(script, {}, local_scope)
        except Exception as exc:  # noqa: BLE001
            stack = traceback.format_exc()
            ctx.log_error(stack)
            raise RuntimeError(f"Python Script execution failed: {exc}") from exc

        return NodeResult(outputs={"result": local_scope.get("output_data", payload), "exec_out": True})


class OnFailureNodePlugin:
    """Receives control when an upstream node fails via a 'failed' edge."""

    def spec(self) -> NodeTypeSpec:
        return NodeTypeSpec(
            type_id="core.on_failure",
            display_name="On Failure",
            category_path=("Core",),
            icon="core/error_outline.svg",
            description="Runs when an upstream node fails. Connect the upstream node's 'failed' port to this node.",
            ports=(
                PortSpec("failed_in", "in", "failed", "any", required=True),
                PortSpec("error", "out", "data", "str", exposed=True),
                PortSpec("exec_out", "out", "exec", "exec", exposed=True),
            ),
            properties=(),
        )

    def execute(self, ctx: ExecutionContext) -> NodeResult:
        error = str(ctx.inputs.get("error", "Unknown error"))
        ctx.log_warning(f"Failure handler triggered: {error}")
        return NodeResult(outputs={"error": error, "exec_out": True})


@node_type(
    type_id="core.branch",
    display_name="If / Else Branch",
    category_path=("Core",),
    icon="core/call_split.svg",
    description="Routes execution to 'true' or 'false' output based on a condition.",
    ports=(
        in_port("exec_in", kind="exec", data_type="exec"),
        in_port("condition", data_type="bool"),
        out_port("true_out", kind="exec", data_type="exec"),
        out_port("false_out", kind="exec", data_type="exec"),
    ),
    properties=(
        prop_bool("default_condition", True, "Default Condition", inline_editor="toggle"),
    ),
)
class BranchNodePlugin:
    def execute(self, ctx: ExecutionContext) -> NodeResult:
        condition = ctx.inputs.get("condition", ctx.properties.get("default_condition", True))
        if condition:
            return NodeResult(outputs={"true_out": True})
        return NodeResult(outputs={"false_out": True})
