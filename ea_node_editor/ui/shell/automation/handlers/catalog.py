# Purpose: Catalog automation handlers: node type listing/description and style schema (T05).
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ea_node_editor.automation.errors import not_implemented
from ea_node_editor.automation.op_model import Deferred
from ea_node_editor.ui.shell.automation.context import AutomationContext


def list_node_types(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('catalog.list_node_types')


def describe_node_type(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('catalog.describe_node_type')


def style_schema(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('catalog.style_schema')


HANDLERS = {
    'catalog.list_node_types': list_node_types,
    'catalog.describe_node_type': describe_node_type,
    'catalog.style_schema': style_schema,
}

__all__ = ["HANDLERS"]
