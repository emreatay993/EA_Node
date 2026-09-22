# Purpose: Node automation handlers: add/text/media/web, update, style, delete, duplicate (T05).
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ea_node_editor.automation.errors import not_implemented
from ea_node_editor.automation.op_model import Deferred
from ea_node_editor.ui.shell.automation.context import AutomationContext


def add_node(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('node.add')


def add_text_node(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('node.add_text')


def add_media_node(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('node.add_media')


def add_web_panel_node(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('node.add_web_panel')


def update_node(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('node.update')


def set_node_style(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('node.set_style')


def delete_nodes(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('node.delete')


def duplicate_nodes(context: AutomationContext, params: Mapping[str, Any]) -> dict[str, Any] | Deferred:
    raise not_implemented('node.duplicate')


HANDLERS = {
    'node.add': add_node,
    'node.add_text': add_text_node,
    'node.add_media': add_media_node,
    'node.add_web_panel': add_web_panel_node,
    'node.update': update_node,
    'node.set_style': set_node_style,
    'node.delete': delete_nodes,
    'node.duplicate': duplicate_nodes,
}

__all__ = ["HANDLERS"]
