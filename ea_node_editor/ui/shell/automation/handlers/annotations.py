# Purpose: Annotation automation handlers: node comments and links (T07).
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ea_node_editor.automation.errors import not_implemented
from ea_node_editor.automation.op_model import Deferred
from ea_node_editor.ui.shell.automation.context import AutomationContext


def upsert_comment(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('comment.upsert')


def remove_comment(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('comment.remove')


def upsert_link(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('link.upsert')


def remove_link(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('link.remove')


HANDLERS = {
    'comment.upsert': upsert_comment,
    'comment.remove': remove_comment,
    'link.upsert': upsert_link,
    'link.remove': remove_link,
}

__all__ = ["HANDLERS"]
