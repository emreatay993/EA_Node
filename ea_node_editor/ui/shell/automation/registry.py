# Purpose: Merge the explicit per-domain HANDLERS tables and assert they cover exactly the op catalog.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
from __future__ import annotations

import importlib

from ea_node_editor.automation.op_catalog import op_names
from ea_node_editor.ui.shell.automation.dispatch import Handler

HANDLER_MODULES: tuple[str, ...] = (
    "app",
    "catalog",
    "graph_read",
    "nodes",
    "edges",
    "structure",
    "annotations",
    "workspaces",
    "project",
    "run",
    "capture",
    "apply",
)


def build_handler_table() -> dict[str, Handler]:
    """Import every handler module by name and merge its ``HANDLERS`` dict.

    No decorators or import-time registration: each module publishes an
    explicit table, duplicates are rejected, and the merged key set must equal
    the op catalog so a missing or misspelled handler fails at startup.
    """
    table: dict[str, Handler] = {}
    for module_name in HANDLER_MODULES:
        module = importlib.import_module(f"ea_node_editor.ui.shell.automation.handlers.{module_name}")
        handlers = module.HANDLERS
        if not isinstance(handlers, dict):
            raise TypeError(f"handlers.{module_name}.HANDLERS must be a dict")
        for op_name, handler in handlers.items():
            if op_name in table:
                raise ValueError(f"duplicate automation handler for {op_name!r} in handlers.{module_name}")
            if not callable(handler):
                raise TypeError(f"handler for {op_name!r} in handlers.{module_name} is not callable")
            table[op_name] = handler
    catalog = set(op_names())
    missing = sorted(catalog - set(table))
    extra = sorted(set(table) - catalog)
    if missing or extra:
        raise RuntimeError(f"automation handler table drift: missing={missing} extra={extra}")
    return table


__all__ = ["HANDLER_MODULES", "build_handler_table"]
