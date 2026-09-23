# Purpose: graph.apply batch op spec: many ops in one undo step with $ref wiring and atomic rollback.
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

DOMAIN = "apply"

MAX_APPLY_OPS = 500
RECOMMENDED_APPLY_OPS = 200
REF_PATTERN = r"^\$(?!\$)([A-Za-z_][A-Za-z0-9_\-]*)(?:\.([A-Za-z0-9_\-\.]+))?$"

BATCH_OP = object_schema(
    {
        "id": string_schema("Name for $ref use by later ops (e.g. 'start' -> $start)"),
        "op": string_schema("Any apply_allowed op name", min_length=1),
        "params": object_schema({}, additional=True),
    },
    required=("op",),
)

APPLY = OpSpec(
    name="graph.apply",
    domain=DOMAIN,
    summary="Apply up to 500 graph ops as ONE undo step; later ops reference earlier results with $id (or $id.field).",
    description=(
        "All ops are validated before anything mutates (unknown op names -> UNKNOWN_OP; every other static "
        "problem -> one INVALID_PARAMS listing ops[i].<path> entries). $ref tokens are only resolved in each op's "
        "declared ref_fields (never inside markdown or titles); $id is the earlier op's primary id, $id.field / "
        "$id.list.0 read nested result fields; write $$ for a literal dollar. atomic=true (default): the first "
        "failing op restores the pre-batch workspace snapshot, scope and selection, no undo entry is recorded, and "
        "the call raises APPLY_FAILED (details: failed_index, failed_op, error, rolled_back=true, results so far). "
        "atomic=false: earlier ops are kept as one undo step and the call returns ok with failed_index >= 0 and the "
        "failing row's error in results; it still raises APPLY_FAILED when the very first op fails. The batch runs "
        "in the active workspace and the open scope; scope.navigate inside a batch changes the scope for later ops. "
        "Staged files and artifact-folder renames do not roll back."
    ),
    params=object_schema(
        {
            "ops": array_schema(BATCH_OP, min_items=1, max_items=MAX_APPLY_OPS),
            "atomic": boolean_schema(default=True),
            "label": string_schema("Undo history label"),
        },
        required=("ops",),
    ),
    result=object_schema(
        {
            "results": array_schema(
                object_schema(
                    {
                        "index": number_schema(integer=True),
                        "id": string_schema(),
                        "op": string_schema(),
                        "ok": boolean_schema(),
                        "result": object_schema({}, additional=True),
                        "error": object_schema({}, additional=True),
                    },
                    additional=True,
                )
            ),
            "applied": number_schema(integer=True),
            "failed_index": number_schema(integer=True, description="-1 when everything applied"),
            "rolled_back": boolean_schema(),
            "ids": object_schema({}, additional=True, description="batch id -> primary result id"),
        },
        additional=True,
    ),
    mutates_graph=True,
    apply_allowed=False,
    mcp_tool="graph_apply",
    examples=(
        {
            "ops": [
                {"id": "start", "op": "node.add", "params": {"type_id": "passive.flowchart.start", "x": 0, "y": 0, "title": "Start"}},
                {"id": "step", "op": "node.add", "params": {"type_id": "passive.flowchart.process", "x": 320, "y": 0, "title": "Mesh"}},
                {"op": "edge.connect", "params": {"source_node_id": "$start", "source_port": "right", "target_node_id": "$step", "target_port": "left"}},
            ],
            "label": "Build flowchart",
        },
    ),
)

OPS: tuple[OpSpec, ...] = (APPLY,)

__all__ = ["APPLY", "DOMAIN", "MAX_APPLY_OPS", "OPS", "RECOMMENDED_APPLY_OPS", "REF_PATTERN"]
