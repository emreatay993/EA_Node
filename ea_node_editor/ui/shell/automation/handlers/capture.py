# Purpose: Capture automation handler: canvas view PNGs (shadows off) and window grabs (T09).
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ea_node_editor.automation.errors import not_implemented
from ea_node_editor.automation.op_model import Deferred
from ea_node_editor.ui.shell.automation.context import AutomationContext


def screenshot(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('capture.screenshot')


HANDLERS = {
    'capture.screenshot': screenshot,
}

__all__ = ["HANDLERS"]
