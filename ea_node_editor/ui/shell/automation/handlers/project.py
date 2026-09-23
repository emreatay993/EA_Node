# Purpose: Project automation handlers (open/new, save/save-as, stage_file) over the non-interactive document IO seams (T09).
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_shell.py
from __future__ import annotations

import base64
import binascii
import mimetypes
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ea_node_editor.automation.errors import (
    APP_BUSY,
    INVALID_PARAMS,
    OPEN_FAILED,
    PROJECT_DIRTY,
    SAVE_FAILED,
    AutomationOpError,
    invalid_params,
    no_effect,
)
from ea_node_editor.automation.op_model import Deferred
from ea_node_editor.settings import PROJECT_NODE_INPUTS_DIRNAME
from ea_node_editor.ui.shell.automation.context import AutomationContext

ARTIFACT_PREFIX = "automation"
ARTIFACT_KIND = "automation_upload"
DEFAULT_SUBDIRECTORY = "automation"
_DEFAULT_MIME = "application/octet-stream"


# ----------------------------------------------------------------- helpers


def _project_snapshot(host: Any) -> dict[str, Any]:
    # Read the host, not context.model / context.workspace_manager: installing a project
    # (open or new) replaces host.model and host.workspace_manager with new objects.
    workspaces = host.model.project.workspaces
    manager = host.workspace_manager
    return {
        "project_path": str(host.project_path or ""),
        "workspace_ids": [ref.workspace_id for ref in manager.list_workspaces() if ref.workspace_id in workspaces],
        "active_workspace_id": str(manager.active_workspace_id() or ""),
    }


def _raise_open_failure(op: str, result: Any, *, path: str) -> None:
    reason = str(result.reason_code)
    details = {"op": op, "reason_code": reason, "message": str(result.message or ""), "path": path}
    if reason == "project_dirty":
        raise AutomationOpError(PROJECT_DIRTY, "The current project has unsaved changes; nothing was opened.", details=details)
    if reason == "open_in_progress":
        raise AutomationOpError(APP_BUSY, "Another project save or open is in progress.", details=details, retryable=True)
    raise AutomationOpError(
        OPEN_FAILED,
        f"COREX could not open the project ({reason}): {result.message or 'no details'}",
        details=details,
    )


def _node_provenance(context: AutomationContext, node_id: str) -> dict[str, str]:
    if not node_id:
        return {"node_id": "", "node_title": "", "node_type": ""}
    node = context.require_node(node_id)
    spec = context.registry.spec_or_none(node.type_id)
    return {
        "node_id": node.node_id,
        "node_title": str(node.title or ""),
        "node_type": str(spec.display_name) if spec is not None else str(node.type_id),
    }


def _staged_path(context: AutomationContext, ref: str) -> str:
    """Absolute staged file path for ``ref`` (temp://...) or "" when the store cannot resolve it."""
    try:
        resolved = context.project_session.project_artifact_store().resolve_staged_path(ref)
    except (OSError, RuntimeError, TypeError, ValueError):
        return ""
    return str(resolved) if resolved is not None else ""


# ---------------------------------------------------------------- handlers


def open_project(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    op = "project.open"
    host = context.require_shell(op)
    session = context.project_session
    path = str(params.get("path") or "").strip()
    new = bool(params.get("new", False))
    discard_unsaved = bool(params.get("discard_unsaved", False))
    if new and path:
        raise invalid_params(["pass either path or new=true, not both"], op=op)
    if new:
        result = session.new_project_noninteractive(discard_unsaved=discard_unsaved)
    else:
        if not path:
            raise invalid_params(["path: required unless new=true"], op=op)
        result = session.open_project_path_noninteractive(path, discard_unsaved=discard_unsaved)
    if not result.ok:
        _raise_open_failure(op, result, path=path)
    if not new and not str(host.project_path or ""):
        raise no_effect(op, "the project path was not adopted after opening", details={"path": path})
    return {
        **_project_snapshot(host),
        "new": new,
        "reason_code": str(result.reason_code),
        "message": str(result.message or ""),
    }


def save_project(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    op = "project.save"
    host = context.require_shell(op)
    session = context.project_session
    path = str(params.get("path") or "").strip() or None
    result = session.save_project_to_path(path)
    status = str(result.status)
    reason = str(result.reason_code)
    target_path = str(result.target_path or "")
    details = {"op": op, "status": status, "reason_code": reason, "target_path": target_path, "requested_path": path or ""}
    if status == "saved":
        return {
            "project_path": str(host.project_path or target_path),
            "status": status,
            "reason_code": reason,
            "target_path": target_path,
            "project_dirty": any(bool(workspace.dirty) for workspace in host.model.project.workspaces.values()),
        }
    if reason == "save_in_progress":
        raise AutomationOpError(APP_BUSY, "Another project save or open is in progress.", details=details, retryable=True)
    if reason == "save_path_required":
        raise AutomationOpError(
            INVALID_PARAMS,
            "The project has never been saved; pass path to Save As.",
            hint="Call project.save with an absolute .cxproj path.",
            details=details,
        )
    if status == "committed_not_adopted":
        raise AutomationOpError(
            SAVE_FAILED,
            f"The project file was written but COREX could not adopt it ({reason}).",
            hint="The file at target_path may be authoritative: reopen it with project.open before continuing.",
            details=details,
        )
    raise AutomationOpError(SAVE_FAILED, f"COREX could not save the project ({reason}).", details=details)


def stage_file(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    op = "project.stage_file"
    context.require_shell(op)
    session = context.project_session
    path = str(params.get("path") or "").strip()
    content = params.get("content_base64")
    if bool(path) == (content is not None):
        raise invalid_params(["provide exactly one of path or content_base64"], op=op)
    subdirectory = str(params.get("subdirectory") or DEFAULT_SUBDIRECTORY).strip() or DEFAULT_SUBDIRECTORY
    provenance = _node_provenance(context, str(params.get("node_id") or "").strip())
    if path:
        source = Path(path).expanduser()
        if not source.is_file():
            raise invalid_params([f"path: '{path}' is not an existing file"], op=op)
        filename = source.name
        size_bytes = source.stat().st_size
        ref = session.stage_node_artifact_file(
            source,
            artifact_prefix=ARTIFACT_PREFIX,
            io_dir=PROJECT_NODE_INPUTS_DIRNAME,
            subdirectory=subdirectory,
            filename=filename,
            **provenance,
        )
    else:
        filename = str(params.get("filename") or "").strip()
        if not filename:
            raise invalid_params(["filename: required with content_base64"], op=op)
        try:
            data = base64.b64decode(str(content), validate=True)
        except (binascii.Error, ValueError) as exc:
            raise invalid_params([f"content_base64: not valid base64 ({exc})"], op=op) from exc
        if not data:
            raise invalid_params(["content_base64: decodes to zero bytes"], op=op)
        size_bytes = len(data)
        ref = session.stage_node_artifact_bytes(
            data,
            filename=filename,
            mime_type=mimetypes.guess_type(filename)[0] or _DEFAULT_MIME,
            artifact_prefix=ARTIFACT_PREFIX,
            subdirectory=subdirectory,
            artifact_kind=ARTIFACT_KIND,
            **provenance,
        )
    ref = str(ref or "").strip()
    if not ref:
        raise no_effect(op, "the project files service did not stage the file", details={"path": path, "filename": filename})
    return {
        "artifact_ref": ref,
        "staged_path": _staged_path(context, ref),
        "filename": filename,
        "size_bytes": int(size_bytes),
        "subdirectory": subdirectory,
        "node_id": provenance["node_id"],
    }


HANDLERS = {
    'project.open': open_project,
    'project.save': save_project,
    'project.stage_file': stage_file,
}

__all__ = ["ARTIFACT_KIND", "ARTIFACT_PREFIX", "DEFAULT_SUBDIRECTORY", "HANDLERS"]
