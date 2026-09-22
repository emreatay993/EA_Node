# Purpose: Workspace and view op specs: list/create/update/close workspaces, create/update/close views, set camera.
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
from ea_node_editor.automation.ops.common import CHANGED_FIELDS, NODE_ID, VIEW_ID, WORKSPACE_ID

DOMAIN = "workspace"

VIEW_ROW = object_schema(
    {"view_id": VIEW_ID, "name": string_schema(), "active": boolean_schema(), "zoom": number_schema()},
    additional=True,
)
WORKSPACE_ROW = object_schema(
    {
        "workspace_id": WORKSPACE_ID,
        "name": string_schema(),
        "dirty": boolean_schema(),
        "active": boolean_schema(),
        "node_count": number_schema(integer=True),
        "views": array_schema(VIEW_ROW),
    },
    additional=True,
)

LIST = OpSpec(
    name="workspace.list",
    domain=DOMAIN,
    summary="List workspaces (tabs) with their views, dirty flags, and which one is active.",
    params=object_schema({}),
    result=object_schema({"workspaces": array_schema(WORKSPACE_ROW), "active_workspace_id": WORKSPACE_ID}, additional=True),
    mcp_tool="workspace_list",
)

CREATE = OpSpec(
    name="workspace.create",
    domain=DOMAIN,
    summary="Create a new workspace tab (optionally duplicating an existing one) and activate it by default.",
    params=object_schema(
        {
            "name": string_schema("Tab name; defaults to Workspace N"),
            "duplicate_of": string_schema("Workspace id to duplicate"),
            "activate": boolean_schema(default=True),
        },
    ),
    result=object_schema({"workspace_id": WORKSPACE_ID, "name": string_schema()}, additional=True),
    mcp_tool="workspace_create",
)

UPDATE = OpSpec(
    name="workspace.update",
    domain=DOMAIN,
    summary="Rename a workspace and/or make it the active tab.",
    params=object_schema(
        {"workspace_id": WORKSPACE_ID, "name": string_schema(), "activate": boolean_schema()},
        required=("workspace_id",),
    ),
    result=object_schema({"workspace_id": WORKSPACE_ID, "changed": CHANGED_FIELDS}, additional=True),
    mcp_tool="workspace_update",
)

CLOSE = OpSpec(
    name="workspace.close",
    domain=DOMAIN,
    summary="Close a workspace tab (PROJECT_DIRTY unless discard_unsaved=true; LAST_WORKSPACE if it is the only one).",
    params=object_schema(
        {"workspace_id": WORKSPACE_ID, "discard_unsaved": boolean_schema(default=False)},
        required=("workspace_id",),
    ),
    result=object_schema({"closed": boolean_schema(), "active_workspace_id": WORKSPACE_ID}, additional=True),
    mcp_tool="workspace_close",
)

VIEW_CREATE = OpSpec(
    name="view.create",
    domain=DOMAIN,
    summary="Create a new camera view in the active workspace (copies the current camera) and activate it.",
    params=object_schema({"name": string_schema(), "activate": boolean_schema(default=True)}),
    result=object_schema({"view_id": VIEW_ID, "name": string_schema()}, additional=True),
    mcp_tool="view_create",
)

VIEW_UPDATE = OpSpec(
    name="view.update",
    domain=DOMAIN,
    summary="Rename a view and/or switch to it.",
    params=object_schema({"view_id": VIEW_ID, "name": string_schema(), "activate": boolean_schema()}, required=("view_id",)),
    result=object_schema({"view_id": VIEW_ID, "changed": CHANGED_FIELDS}, additional=True),
    mcp_tool="view_update",
)

VIEW_CLOSE = OpSpec(
    name="view.close",
    domain=DOMAIN,
    summary="Close a view (LAST_VIEW when it is the only one).",
    params=object_schema({"view_id": VIEW_ID}, required=("view_id",)),
    result=object_schema({"closed": boolean_schema(), "active_view_id": VIEW_ID}, additional=True),
    mcp_tool="view_close",
)

VIEW_SET_CAMERA = OpSpec(
    name="view.set_camera",
    domain=DOMAIN,
    summary="Set zoom/center explicitly or frame all nodes, the selection, or specific nodes.",
    params=object_schema(
        {
            "zoom": number_schema("0.1 to 5.0", minimum=0.1, maximum=5.0),
            "center_x": number_schema(),
            "center_y": number_schema(),
            "frame": string_schema(enum=("all", "selection", "nodes")),
            "node_ids": array_schema(NODE_ID, "Nodes to frame when frame=nodes"),
        },
    ),
    result=object_schema({"zoom": number_schema(), "center_x": number_schema(), "center_y": number_schema()}, additional=True),
    mcp_tool="view_set_camera",
)

OPS: tuple[OpSpec, ...] = (LIST, CREATE, UPDATE, CLOSE, VIEW_CREATE, VIEW_UPDATE, VIEW_CLOSE, VIEW_SET_CAMERA)

__all__ = [
    "CLOSE",
    "CREATE",
    "DOMAIN",
    "LIST",
    "OPS",
    "UPDATE",
    "VIEW_CLOSE",
    "VIEW_CREATE",
    "VIEW_SET_CAMERA",
    "VIEW_UPDATE",
]
