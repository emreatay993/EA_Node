# Purpose: Edge automation handlers: connect, update, delete (T06).
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ea_node_editor.automation.errors import not_implemented
from ea_node_editor.automation.op_model import Deferred
from ea_node_editor.ui.shell.automation.context import AutomationContext


def connect_edge(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('edge.connect')


def update_edge(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('edge.update')


def delete_edges(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('edge.delete')


HANDLERS = {
    'edge.connect': connect_edge,
    'edge.update': update_edge,
    'edge.delete': delete_edges,
}

__all__ = ["HANDLERS"]
