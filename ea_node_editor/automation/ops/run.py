# Purpose: Run op specs: start a workflow/selected-node run, poll or wait for status, stop/pause/resume.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_catalog.py
from __future__ import annotations

from ea_node_editor.automation.op_model import (
    OpSpec,
    array_schema,
    boolean_schema,
    number_schema,
    object_schema,
    string_schema,
)
from ea_node_editor.automation.ops.common import NODE_ID

DOMAIN = "run"

RUN_STATUS_RESULT = object_schema(
    {
        "idle": boolean_schema(description="No active run/submission and no pending auto-run"),
        "engine_state": string_schema(enum=("ready", "preparing", "running", "paused", "error")),
        "active_run_id": string_schema(),
        "outcome": string_schema(description="completed | failed | stopped | running | idle"),
        "started": boolean_schema(description="run.start only: whether a submission was created"),
        "running_node_ids": array_schema(NODE_ID),
        "completed_node_ids": array_schema(NODE_ID),
        "failed_node_ids": array_schema(NODE_ID),
        "blocked_node_ids": array_schema(NODE_ID),
        "root_errors": array_schema(object_schema({}, additional=True)),
        "log_tail": array_schema(string_schema()),
        "waited_s": number_schema(),
        "timed_out": boolean_schema(),
    },
    additional=True,
)

START = OpSpec(
    name="run.start",
    domain=DOMAIN,
    summary="Run the active workspace or a set of nodes; optionally wait for completion (wait=true).",
    description="RUN_ACTIVE if a run is already in flight. Passive-only graphs complete immediately.",
    params=object_schema(
        {
            "scope": string_schema(enum=("workspace", "nodes"), default="workspace"),
            "node_ids": array_schema(NODE_ID, "Required when scope=nodes"),
            "wait": boolean_schema(default=False),
            "timeout_s": number_schema(minimum=0, maximum=3600, default=120),
            "log_tail": number_schema(minimum=0, maximum=500, default=20, integer=True),
        },
    ),
    result=RUN_STATUS_RESULT,
    deferred=True,
    mcp_tool="run_start",
)

STATUS = OpSpec(
    name="run.status",
    domain=DOMAIN,
    summary="Report run state and per-node outcomes; wait=true blocks until idle or timeout.",
    params=object_schema(
        {
            "wait": boolean_schema(default=False),
            "timeout_s": number_schema(minimum=0, maximum=3600, default=120),
            "log_tail": number_schema(minimum=0, maximum=500, default=20, integer=True),
        },
    ),
    result=RUN_STATUS_RESULT,
    deferred=True,
    mcp_tool="run_status",
)

CONTROL = OpSpec(
    name="run.control",
    domain=DOMAIN,
    summary="Stop, pause, or resume the active run.",
    params=object_schema({"action": string_schema(enum=("stop", "pause", "resume"))}, required=("action",)),
    result=object_schema({"applied": boolean_schema(), "engine_state": string_schema()}, additional=True),
    mcp_tool="run_control",
)

OPS: tuple[OpSpec, ...] = (START, STATUS, CONTROL)

__all__ = ["CONTROL", "DOMAIN", "OPS", "RUN_STATUS_RESULT", "START", "STATUS"]
