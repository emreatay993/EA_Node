# Purpose: Project automation handlers using the non-interactive document IO seams (T09).
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ea_node_editor.automation.errors import not_implemented
from ea_node_editor.automation.op_model import Deferred
from ea_node_editor.ui.shell.automation.context import AutomationContext


def open_project(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('project.open')


def save_project(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('project.save')


def stage_file(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('project.stage_file')


HANDLERS = {
    'project.open': open_project,
    'project.save': save_project,
    'project.stage_file': stage_file,
}

__all__ = ["HANDLERS"]
