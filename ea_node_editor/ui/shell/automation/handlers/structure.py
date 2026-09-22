# Purpose: Structure automation handlers: groups, subnodes, scope, selection, layout (T06).
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ea_node_editor.automation.errors import not_implemented
from ea_node_editor.automation.op_model import Deferred
from ea_node_editor.ui.shell.automation.context import AutomationContext


def wrap_group(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('group.wrap')


def create_subnode(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('subnode.create')


def ungroup_subnode(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('subnode.ungroup')


def add_subnode_pin(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('subnode.add_pin')


def navigate_scope(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('scope.navigate')


def set_selection(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('selection.set')


def arrange_layout(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('layout.arrange')


HANDLERS = {
    'group.wrap': wrap_group,
    'subnode.create': create_subnode,
    'subnode.ungroup': ungroup_subnode,
    'subnode.add_pin': add_subnode_pin,
    'scope.navigate': navigate_scope,
    'selection.set': set_selection,
    'layout.arrange': arrange_layout,
}

__all__ = ["HANDLERS"]
