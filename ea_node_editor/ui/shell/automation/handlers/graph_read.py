# Purpose: Read-only graph automation handlers: snapshot, node detail, search (T05).
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ea_node_editor.automation.errors import not_implemented
from ea_node_editor.automation.op_model import Deferred
from ea_node_editor.ui.shell.automation.context import AutomationContext


def get_graph(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('graph.get')


def get_node(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('graph.get_node')


def find_nodes(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('graph.find_nodes')


HANDLERS = {
    'graph.get': get_graph,
    'graph.get_node': get_node,
    'graph.find_nodes': find_nodes,
}

__all__ = ["HANDLERS"]
