# Purpose: App-level automation handlers: status, undo/redo, quit (T09).
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ea_node_editor.automation.errors import not_implemented
from ea_node_editor.automation.op_model import Deferred
from ea_node_editor.ui.shell.automation.context import AutomationContext


def status(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('app.status')


def history(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('app.history')


def quit(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('app.quit')


HANDLERS = {
    'app.status': status,
    'app.history': history,
    'app.quit': quit,
}

__all__ = ["HANDLERS"]
