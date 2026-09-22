# Purpose: Project op specs: open/new, save/save-as, stage a file into the project.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_catalog.py
from __future__ import annotations

from ea_node_editor.automation.op_model import (
    OpSpec,
    array_schema,
    boolean_schema,
    object_schema,
    string_schema,
)
from ea_node_editor.automation.ops.common import WORKSPACE_ID

DOMAIN = "project"

OPEN = OpSpec(
    name="project.open",
    domain=DOMAIN,
    summary="Open a .cxproj (path) or start a new blank project (new=true); refuses PROJECT_DIRTY unless discard_unsaved.",
    params=object_schema(
        {
            "path": string_schema("Absolute .cxproj path"),
            "new": boolean_schema("Start a blank project instead of opening a file", default=False),
            "discard_unsaved": boolean_schema(default=False),
        },
    ),
    result=object_schema(
        {
            "project_path": string_schema(),
            "workspace_ids": array_schema(WORKSPACE_ID),
            "active_workspace_id": WORKSPACE_ID,
        },
        additional=True,
    ),
    mcp_tool="project_open",
)

SAVE = OpSpec(
    name="project.save",
    domain=DOMAIN,
    summary="Save the project; pass path to Save As. Staged node files are published into the .data folder.",
    params=object_schema({"path": string_schema("Target .cxproj path for Save As; omit to save in place")}),
    result=object_schema(
        {"project_path": string_schema(), "status": string_schema(), "reason_code": string_schema()},
        additional=True,
    ),
    mcp_tool="project_save",
)

STAGE_FILE = OpSpec(
    name="project.stage_file",
    domain=DOMAIN,
    summary="Copy a local file (or write bytes) into the project's staging area and return its artifact ref.",
    description="Use for media/web assets you want the project to own; refs look like temp://... until saved.",
    params=object_schema(
        {
            "path": string_schema("Local file to copy"),
            "content_base64": string_schema("Alternative to path: file bytes"),
            "filename": string_schema("Required with content_base64"),
            "subdirectory": string_schema(default="automation"),
            "node_id": string_schema("Owning node for provenance"),
        },
    ),
    result=object_schema({"artifact_ref": string_schema(), "staged_path": string_schema()}, additional=True),
    mcp_tool="project_stage_file",
)

OPS: tuple[OpSpec, ...] = (OPEN, SAVE, STAGE_FILE)

__all__ = ["DOMAIN", "OPEN", "OPS", "SAVE", "STAGE_FILE"]
