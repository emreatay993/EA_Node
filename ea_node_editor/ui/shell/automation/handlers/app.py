# Purpose: App-level automation handlers: status (shell-free safe), undo/redo history, deferred quit (T09).
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_handlers_shell.py
from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from ea_node_editor import __version__
from ea_node_editor.automation.errors import PROJECT_DIRTY, AutomationOpError
from ea_node_editor.automation.gate import MODE_VISIBLE
from ea_node_editor.automation.op_model import Deferred
from ea_node_editor.automation.protocol import PROTOCOL_VERSION
from ea_node_editor.ui.shell.automation.context import AutomationContext
from ea_node_editor.ui.shell.automation.handlers.run import run_summary

QUIT_DELAY_MS = 250
_DEFAULT_QT_PLATFORM = "windows"


# ----------------------------------------------------------------- helpers


def project_dirty(context: AutomationContext) -> bool:
    """Same rule as ProjectDocumentIOService._project_has_unsaved_changes: any workspace dirty."""
    return any(bool(workspace.dirty) for workspace in context.model.project.workspaces.values())


def _busy_flags(context: AutomationContext) -> dict[str, bool]:
    host = context.host
    if host is None:
        return {"modal_dialog": False, "document_io": False, "shutting_down": False}
    session = context.project_session
    return {
        "modal_dialog": QApplication.activeModalWidget() is not None or QApplication.activePopupWidget() is not None,
        "document_io": bool(session.document_io_active()) if session is not None else False,
        "shutting_down": bool(host._shell_teardown_started),
    }


def _history_depths(context: AutomationContext, workspace_id: str) -> dict[str, Any]:
    history = context.runtime_history
    if history is None:
        return {"can_undo": False, "can_redo": False, "undo_depth": 0, "redo_depth": 0}
    return {
        "can_undo": bool(history.can_undo(workspace_id)),
        "can_redo": bool(history.can_redo(workspace_id)),
        "undo_depth": int(history.undo_depth(workspace_id)),
        "redo_depth": int(history.redo_depth(workspace_id)),
    }


# ---------------------------------------------------------------- handlers


def status(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    # Deliberately no require_shell: graph.apply and the MCP server call this first,
    # and the shell-free harness must get empty project fields instead of INTERNAL.
    host = context.host
    gate = context.gate
    workspace = context.active_workspace()
    return {
        "app_version": str(__version__),
        "protocol": int(PROTOCOL_VERSION),
        "instance_id": str(gate.instance_id) if gate is not None else "",
        "pid": os.getpid(),
        "mode": str(gate.mode) if gate is not None else MODE_VISIBLE,
        "qt_platform": str(os.environ.get("QT_QPA_PLATFORM") or _DEFAULT_QT_PLATFORM),
        "project_path": str(host.project_path or "") if host is not None else "",
        "project_dirty": project_dirty(context),
        "active_workspace_id": str(workspace.workspace_id),
        "active_workspace_name": str(workspace.name),
        "active_view_id": str(workspace.active_view_id or ""),
        "scope_path": context.scope_path(),
        "selected_node_ids": context.selected_node_ids(),
        "run": run_summary(context.run_state),
        "busy": _busy_flags(context),
        "node_count": len(workspace.nodes),
        "edge_count": len(workspace.edges),
        "workspace_count": len(context.model.project.workspaces),
        "has_shell": context.has_shell,
    }


def history(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    op = "app.history"
    action = str(params.get("action") or "status")
    workspace_id = context.workspace_id()
    applied = False
    action_type = ""
    if action in ("undo", "redo"):
        edit = context.workspace_edit
        if edit is None:
            context.require_shell(op)
        history_owner = context.runtime_history
        if history_owner is not None:
            # Drop a stale entry so the label below can only come from this call.
            history_owner.consume_last_applied_entry(workspace_id)
        # Nothing to undo/redo is applied=False, not NO_EFFECT: the depth fields say why.
        applied = bool(edit.undo() if action == "undo" else edit.redo())
        if applied and history_owner is not None:
            # The scene refresh triggered by the edit controller normally consumes the
            # entry first (GraphSceneBridge.refresh_workspace_from_model), so this is
            # usually empty in the full shell; the history owner exposes no peek.
            entry = history_owner.consume_last_applied_entry(workspace_id)
            action_type = str(entry.action_type) if entry is not None else ""
    return {
        "action": action,
        "applied": applied,
        "action_type": action_type,
        "workspace_id": workspace_id,
        **_history_depths(context, workspace_id),
    }


def quit(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    op = "app.quit"
    host = context.require_shell(op)
    dirty = project_dirty(context)
    discard = bool(params.get("discard_unsaved", False))
    if dirty and not discard:
        raise AutomationOpError(
            PROJECT_DIRTY,
            "The project has unsaved changes; COREX was not closed.",
            details={"op": op, "project_path": str(host.project_path or "")},
        )
    app = QApplication.instance()

    def _close_and_quit() -> None:
        # ShellWindow.closeEvent never prompts (it tears down and discards the autosave
        # snapshot), so a dirty project closes silently once discard_unsaved is given.
        host.close()
        if app is not None:
            app.quit()

    # Delayed so the transport can write this response before the sockets go away.
    QTimer.singleShot(QUIT_DELAY_MS, _close_and_quit)
    return {"quitting": True, "project_dirty": dirty, "delay_ms": QUIT_DELAY_MS}


HANDLERS = {
    'app.status': status,
    'app.history': history,
    'app.quit': quit,
}

__all__ = ["HANDLERS", "QUIT_DELAY_MS", "project_dirty"]
