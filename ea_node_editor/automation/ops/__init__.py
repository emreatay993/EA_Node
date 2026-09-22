# Purpose: Declarative per-domain op specs; each module ends with an explicit OPS tuple aggregated by op_catalog.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_catalog.py
"""Automation op declarations, one module per domain.

Every module exposes ``OPS: tuple[OpSpec, ...]``. ``op_catalog.all_ops()``
imports the modules by name (no decorators, no import-time registration) so
the catalog stays a plain data structure that tests can snapshot.
"""

from __future__ import annotations

DOMAIN_MODULES: tuple[str, ...] = (
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

__all__ = ["DOMAIN_MODULES"]
