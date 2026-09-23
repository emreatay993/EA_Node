# Purpose: Workspace/view automation handlers using the dialog-free navigation seams and the viewport camera (T09).
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_shell.py
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from PyQt6.QtCore import QRectF

from ea_node_editor.automation.errors import (
    LAST_VIEW,
    LAST_WORKSPACE,
    NOT_FOUND,
    PROJECT_DIRTY,
    AutomationOpError,
    invalid_params,
    no_effect,
    not_found,
)
from ea_node_editor.automation.op_model import Deferred
from ea_node_editor.ui.shell.automation.context import AutomationContext
from ea_node_editor.ui_qml.viewport_bridge import FRAME_PADDING_PX, MAX_ZOOM, MIN_ZOOM

_CLOSE_REASON_CODES = {
    "dirty": PROJECT_DIRTY,
    "last_workspace": LAST_WORKSPACE,
    "unknown_workspace": NOT_FOUND,
}
_FRAME_MODES = ("all", "selection", "nodes")


# ----------------------------------------------------------------- helpers


def view_row(workspace: Any, view: Any) -> dict[str, Any]:
    return {
        "view_id": str(view.view_id),
        "name": str(view.name),
        "active": str(view.view_id) == str(workspace.active_view_id),
        "zoom": float(view.zoom),
        "center_x": float(view.pan_x),
        "center_y": float(view.pan_y),
        "scope_path": [str(item) for item in view.scope_path],
    }


def workspace_row(workspace: Any, active_workspace_id: str) -> dict[str, Any]:
    return {
        "workspace_id": str(workspace.workspace_id),
        "name": str(workspace.name),
        "dirty": bool(workspace.dirty),
        "active": str(workspace.workspace_id) == str(active_workspace_id),
        "node_count": len(workspace.nodes),
        "edge_count": len(workspace.edges),
        "active_view_id": str(workspace.active_view_id or ""),
        "views": [view_row(workspace, view) for view in workspace.views.values()],
    }


def _workspaces(context: AutomationContext) -> dict[str, Any]:
    return context.model.project.workspaces


def _require_workspace(context: AutomationContext, workspace_id: Any) -> Any:
    normalized = str(workspace_id or "").strip()
    workspace = _workspaces(context).get(normalized) if normalized else None
    if workspace is None:
        raise not_found("Workspace", normalized, hint="Call workspace.list to see the open workspaces and their ids.")
    return workspace


def _require_view(context: AutomationContext, view_id: Any) -> tuple[Any, Any]:
    workspace = context.active_workspace()
    normalized = str(view_id or "").strip()
    view = workspace.views.get(normalized) if normalized else None
    if view is None:
        raise AutomationOpError(
            NOT_FOUND,
            f"View '{normalized}' does not exist in the active workspace '{workspace.workspace_id}'.",
            hint="Views belong to the active workspace; call workspace.list and activate the owning workspace first.",
            details={"view_id": normalized, "workspace_id": workspace.workspace_id, "available": list(workspace.views)},
        )
    return workspace, view


def _activate_view(context: AutomationContext, view_id: str) -> None:
    # The presenter path is what the UI uses: nav.switch_view plus scope sync and the
    # scope camera bookkeeping; it is a no-op when the view is already active.
    context.workspace_presenter.request_switch_view(view_id)


def _camera(context: AutomationContext) -> dict[str, float]:
    view = context.view
    return {"zoom": float(view.zoom_value), "center_x": float(view.center_x), "center_y": float(view.center_y)}


def _union_bounds(context: AutomationContext, node_ids: list[str]) -> tuple[QRectF | None, list[str]]:
    union: QRectF | None = None
    missing: list[str] = []
    for node_id in node_ids:
        bounds = context.scene.node_bounds(node_id)
        if bounds is None or bounds.width() <= 0.0 or bounds.height() <= 0.0:
            missing.append(node_id)
            continue
        union = QRectF(bounds) if union is None else union.united(bounds)
    return union, missing


def _unique_ids(values: Any) -> list[str]:
    ordered: list[str] = []
    for value in values or ():
        node_id = str(value or "").strip()
        if node_id and node_id not in ordered:
            ordered.append(node_id)
    return ordered


# ------------------------------------------------------------- workspaces


def list_workspaces(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    active_id = context.workspace_id()
    workspaces = _workspaces(context)
    rows = [
        workspace_row(workspaces[ref.workspace_id], active_id)
        for ref in context.workspace_manager.list_workspaces()
        if ref.workspace_id in workspaces
    ]
    return {"workspaces": rows, "active_workspace_id": active_id}


def create_workspace(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    op = "workspace.create"
    context.require_shell(op)
    nav = context.nav
    workspaces = _workspaces(context)
    previous_active = context.workspace_id()
    name = str(params.get("name") or "").strip()
    duplicate_of = str(params.get("duplicate_of") or "").strip()
    activate = bool(params.get("activate", True))
    before = set(workspaces)
    if duplicate_of:
        source = _require_workspace(context, duplicate_of)
        # Mirrors WorkspaceNavigationController.duplicate_active_workspace without the tab lookup.
        workspace_id = str(context.workspace_manager.duplicate_workspace(source.workspace_id) or "").strip()
        context.runtime_history.clear_workspace(workspace_id)
        nav.refresh_workspace_tabs()
        nav.switch_workspace(workspace_id)
        if name and workspace_id in workspaces and workspaces[workspace_id].name != name:
            nav.rename_workspace_to(workspace_id, name)
    else:
        workspace_id = str(nav.create_workspace_named(name or None) or "").strip()
    workspace = workspaces.get(workspace_id)
    if workspace is None or workspace_id in before:
        raise no_effect(op, "the workspace manager did not create a new workspace", details={"duplicate_of": duplicate_of})
    if name and workspace.name != name:
        raise no_effect(op, f"name '{name}' was not applied (workspace name is '{workspace.name}')", details={"workspace_id": workspace_id})
    if not activate and previous_active in workspaces and previous_active != workspace_id:
        nav.switch_workspace(previous_active)
    active_id = context.workspace_id()
    return {
        "workspace_id": workspace_id,
        "name": str(workspace.name),
        "active": active_id == workspace_id,
        "active_workspace_id": active_id,
        "duplicated_from": duplicate_of,
        "workspace": workspace_row(workspace, active_id),
    }


def update_workspace(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    op = "workspace.update"
    context.require_shell(op)
    workspace = _require_workspace(context, params["workspace_id"])
    workspace_id = str(workspace.workspace_id)
    name = params.get("name")
    activate = params.get("activate")
    if name is None and activate is None:
        raise invalid_params(["provide name and/or activate"], op=op)
    changed: list[str] = []
    requested: list[str] = []
    if name is not None:
        requested.append("name")
        normalized = str(name).strip()
        if not normalized:
            raise invalid_params(["name: must not be blank"], op=op)
        if normalized != workspace.name:
            renamed = context.nav.rename_workspace_to(workspace_id, normalized)
            if not renamed or workspace.name != normalized:
                raise no_effect(op, f"rename to '{normalized}' was not applied", details={"workspace_id": workspace_id, "name": workspace.name})
            changed.append("name")
    if activate:
        requested.append("activate")
        if context.workspace_id() != workspace_id:
            context.nav.switch_workspace(workspace_id)
            if context.workspace_id() != workspace_id:
                raise no_effect(op, "the workspace could not be activated", details={"workspace_id": workspace_id})
            changed.append("active")
    if not changed:
        raise no_effect(
            op,
            "every requested value already matched the workspace",
            details={"workspace_id": workspace_id, "requested": requested},
        )
    active_id = context.workspace_id()
    return {"workspace_id": workspace_id, "changed": changed, "workspace": workspace_row(workspace, active_id), "active_workspace_id": active_id}


def close_workspace(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    op = "workspace.close"
    context.require_shell(op)
    workspace = _require_workspace(context, params["workspace_id"])
    workspace_id = str(workspace.workspace_id)
    discard_unsaved = bool(params.get("discard_unsaved", False))
    outcome = context.nav.close_workspace_noninteractive(workspace_id, discard_unsaved=discard_unsaved)
    if not outcome.closed:
        code = _CLOSE_REASON_CODES.get(str(outcome.reason))
        details = {"workspace_id": workspace_id, "reason": str(outcome.reason), "name": str(workspace.name)}
        if code == PROJECT_DIRTY:
            raise AutomationOpError(
                PROJECT_DIRTY,
                f"Workspace '{workspace.name}' has unsaved changes; pass discard_unsaved=true to close it anyway.",
                details=details,
            )
        if code == LAST_WORKSPACE:
            raise AutomationOpError(LAST_WORKSPACE, "The last workspace cannot be closed.", details=details)
        if code == NOT_FOUND:
            raise not_found("Workspace", workspace_id)
        raise no_effect(op, f"the navigation controller refused to close the workspace ({outcome.reason})", details=details)
    if workspace_id in _workspaces(context):
        raise no_effect(op, "the workspace is still open after the close request", details={"workspace_id": workspace_id})
    return {
        "closed": True,
        "workspace_id": workspace_id,
        "active_workspace_id": str(outcome.active_workspace_id or context.workspace_id()),
        "retirement_error": str(outcome.retirement_error or ""),
    }


# ------------------------------------------------------------------ views


def create_view(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    op = "view.create"
    context.require_shell(op)
    workspace = context.active_workspace()
    name = str(params.get("name") or "").strip()
    activate = bool(params.get("activate", True))
    previous_active = str(workspace.active_view_id or "")
    before = set(workspace.views)
    view_id = str(context.nav.create_view_named(name or None) or "").strip()
    view = workspace.views.get(view_id)
    if not view_id or view is None or view_id in before:
        raise no_effect(op, "the navigation controller did not create a new view", details={"workspace_id": workspace.workspace_id})
    if name and str(view.name) != name:
        raise no_effect(op, f"name '{name}' was not applied (view name is '{view.name}')", details={"view_id": view_id})
    if not activate and previous_active in workspace.views and previous_active != view_id:
        _activate_view(context, previous_active)
    return {
        "view_id": view_id,
        "name": str(view.name),
        "active": str(workspace.active_view_id) == view_id,
        "active_view_id": str(workspace.active_view_id or ""),
        "workspace_id": str(workspace.workspace_id),
        "view": view_row(workspace, view),
    }


def update_view(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    op = "view.update"
    context.require_shell(op)
    workspace, view = _require_view(context, params["view_id"])
    view_id = str(view.view_id)
    name = params.get("name")
    activate = params.get("activate")
    if name is None and activate is None:
        raise invalid_params(["provide name and/or activate"], op=op)
    changed: list[str] = []
    requested: list[str] = []
    if name is not None:
        requested.append("name")
        normalized = str(name).strip()
        if not normalized:
            raise invalid_params(["name: must not be blank"], op=op)
        if normalized != str(view.name):
            renamed = context.nav.rename_view_to(view_id, normalized)
            if not renamed or str(view.name) != normalized:
                raise no_effect(op, f"rename to '{normalized}' was not applied", details={"view_id": view_id, "name": str(view.name)})
            changed.append("name")
    if activate:
        requested.append("activate")
        if str(workspace.active_view_id) != view_id:
            _activate_view(context, view_id)
            if str(workspace.active_view_id) != view_id:
                raise no_effect(op, "the view could not be activated", details={"view_id": view_id})
            changed.append("active")
    if not changed:
        raise no_effect(op, "every requested value already matched the view", details={"view_id": view_id, "requested": requested})
    return {"view_id": view_id, "changed": changed, "view": view_row(workspace, view), "active_view_id": str(workspace.active_view_id or "")}


def close_view(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    op = "view.close"
    context.require_shell(op)
    workspace, view = _require_view(context, params["view_id"])
    view_id = str(view.view_id)
    if len(workspace.views) <= 1:
        raise AutomationOpError(
            LAST_VIEW,
            "The last view of a workspace cannot be closed.",
            details={"view_id": view_id, "workspace_id": workspace.workspace_id},
        )
    closed = context.nav.close_view(view_id, show_errors=False)
    if not closed or view_id in workspace.views:
        raise no_effect(op, "the navigation controller kept the view", details={"view_id": view_id})
    return {"closed": True, "view_id": view_id, "active_view_id": str(workspace.active_view_id or ""), "workspace_id": str(workspace.workspace_id)}


def set_camera(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    op = "view.set_camera"
    context.require_shell(op)
    view = context.view
    frame = params.get("frame")
    zoom = params.get("zoom")
    center_x = params.get("center_x")
    center_y = params.get("center_y")
    if frame is None and zoom is None and center_x is None and center_y is None:
        raise invalid_params(["provide frame (all | selection | nodes) or zoom / center_x / center_y"], op=op)
    before = _camera(context)
    framed = ""
    if frame is not None:
        mode = str(frame)
        if mode not in _FRAME_MODES:
            raise invalid_params([f"frame: must be one of {list(_FRAME_MODES)}"], op=op)
        if mode == "all":
            bounds = context.nav.current_workspace_scene_bounds()
            if bounds is None or bounds.width() <= 0.0 or bounds.height() <= 0.0:
                raise no_effect(op, "the workspace has no nodes to frame", details={"frame": mode})
            context.nav.frame_all()
        elif mode == "selection":
            bounds = context.nav.selection_bounds()
            if bounds is None or bounds.width() <= 0.0 or bounds.height() <= 0.0:
                raise no_effect(op, "nothing is selected", details={"frame": mode, "selected_node_ids": context.selected_node_ids()})
            context.nav.frame_selection()
        else:
            node_ids = _unique_ids(params.get("node_ids"))
            if not node_ids:
                raise invalid_params(["node_ids: required and non-empty when frame=nodes"], op=op)
            context.require_nodes(node_ids)
            union, missing = _union_bounds(context, node_ids)
            if union is None:
                raise no_effect(op, "none of the nodes has renderable bounds (are they in the open scope?)", details={"node_ids": node_ids, "missing": missing})
            view.frame_scene_rect(union, padding_px=FRAME_PADDING_PX)
        framed = mode
    if zoom is not None or center_x is not None or center_y is not None:
        # Explicit values override the framed camera; the owner clamps zoom to 0.1..5.0.
        current = _camera(context)
        target_zoom = max(MIN_ZOOM, min(float(zoom), MAX_ZOOM)) if zoom is not None else current["zoom"]
        target_x = float(center_x) if center_x is not None else current["center_x"]
        target_y = float(center_y) if center_y is not None else current["center_y"]
        view.set_view_state(target_zoom, target_x, target_y)
    after = _camera(context)
    return {**after, "framed": framed, "changed": after != before}


HANDLERS = {
    'workspace.list': list_workspaces,
    'workspace.create': create_workspace,
    'workspace.update': update_workspace,
    'workspace.close': close_workspace,
    'view.create': create_view,
    'view.update': update_view,
    'view.close': close_view,
    'view.set_camera': set_camera,
}

__all__ = ["HANDLERS", "view_row", "workspace_row"]
