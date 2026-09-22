# Purpose: Workspace/view automation handlers using the dialog-free navigation seams (T09).
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ea_node_editor.automation.errors import not_implemented
from ea_node_editor.automation.op_model import Deferred
from ea_node_editor.ui.shell.automation.context import AutomationContext


def list_workspaces(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('workspace.list')


def create_workspace(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('workspace.create')


def update_workspace(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('workspace.update')


def close_workspace(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('workspace.close')


def create_view(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('view.create')


def update_view(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('view.update')


def close_view(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('view.close')


def set_camera(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('view.set_camera')


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

__all__ = ["HANDLERS"]
