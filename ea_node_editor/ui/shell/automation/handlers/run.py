# Purpose: Run automation handlers: start, deferred status/wait, control (T09).
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ea_node_editor.automation.errors import not_implemented
from ea_node_editor.automation.op_model import Deferred
from ea_node_editor.ui.shell.automation.context import AutomationContext


def start_run(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('run.start')


def run_status(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('run.status')


def control_run(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('run.control')


HANDLERS = {
    'run.start': start_run,
    'run.status': run_status,
    'run.control': control_run,
}

__all__ = ["HANDLERS"]
