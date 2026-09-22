# Purpose: App-level op specs: status, undo/redo history, quit.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_catalog.py
from __future__ import annotations

from ea_node_editor.automation.op_model import (
    OpSpec,
    any_schema,
    array_schema,
    boolean_schema,
    number_schema,
    object_schema,
    string_schema,
)
from ea_node_editor.automation.ops.common import WORKSPACE_ID

DOMAIN = "app"

STATUS = OpSpec(
    name="app.status",
    domain=DOMAIN,
    summary="Report instance identity, project, active workspace/view/scope, selection, run state, and busy flags.",
    description=(
        "Call this first. It never mutates anything and tells you whether the app is busy "
        "(modal dialog, project IO, active run) before you plan a batch."
    ),
    params=object_schema({}),
    result=object_schema(
        {
            "app_version": string_schema(),
            "protocol": number_schema(integer=True),
            "instance_id": string_schema(),
            "pid": number_schema(integer=True),
            "mode": string_schema(enum=("visible", "private")),
            "qt_platform": string_schema(description="offscreen or windows"),
            "project_path": string_schema(),
            "project_dirty": boolean_schema(),
            "active_workspace_id": WORKSPACE_ID,
            "active_workspace_name": string_schema(),
            "active_view_id": string_schema(),
            "scope_path": array_schema(string_schema(), "Subnode shell ids from root to the open scope"),
            "selected_node_ids": array_schema(string_schema()),
            "run": object_schema(
                {
                    "idle": boolean_schema(),
                    "engine_state": string_schema(),
                    "active_run_id": string_schema(),
                },
                additional=True,
            ),
            "busy": object_schema(
                {
                    "modal_dialog": boolean_schema(),
                    "document_io": boolean_schema(),
                    "shutting_down": boolean_schema(),
                },
                additional=True,
            ),
            "node_count": number_schema(integer=True),
            "edge_count": number_schema(integer=True),
        },
        additional=True,
    ),
    mcp_tool="corex_status",
)

HISTORY = OpSpec(
    name="app.history",
    domain=DOMAIN,
    summary="Undo or redo the last automation/user step in the active workspace, or report undo/redo depth.",
    description=(
        "Every mutating automation op is exactly one undo step (graph.apply batches are one step). "
        "action=status only reads."
    ),
    params=object_schema(
        {
            "action": string_schema("undo | redo | status", enum=("undo", "redo", "status"), default="status"),
        },
    ),
    result=object_schema(
        {
            "applied": boolean_schema(description="True when an undo/redo entry was applied"),
            "action_type": string_schema(description="History label of the applied entry"),
            "can_undo": boolean_schema(),
            "can_redo": boolean_schema(),
            "undo_depth": number_schema(integer=True),
            "redo_depth": number_schema(integer=True),
            "workspace_id": WORKSPACE_ID,
        },
        additional=True,
    ),
    mutates_graph=False,
    mcp_tool="corex_history",
)

QUIT = OpSpec(
    name="app.quit",
    domain=DOMAIN,
    summary="Close the COREX instance (refuses with PROJECT_DIRTY unless discard_unsaved=true).",
    description="Use only for private instances you launched. Attached visible instances belong to the user.",
    params=object_schema({"discard_unsaved": boolean_schema(default=False)}),
    result=object_schema({"quitting": boolean_schema(), "project_dirty": boolean_schema()}, additional=True),
    mcp_tool="corex_quit",
)

OPS: tuple[OpSpec, ...] = (STATUS, HISTORY, QUIT)

__all__ = ["DOMAIN", "HISTORY", "OPS", "QUIT", "STATUS", "any_schema"]
