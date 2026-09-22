# Purpose: graph.apply batch handler: static validation, $ref resolution, one undo step, atomic rollback (T11).
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ea_node_editor.automation.errors import not_implemented
from ea_node_editor.automation.op_model import Deferred
from ea_node_editor.ui.shell.automation.context import AutomationContext


def apply_graph_ops(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('graph.apply')


HANDLERS = {
    'graph.apply': apply_graph_ops,
}

__all__ = ["HANDLERS"]
