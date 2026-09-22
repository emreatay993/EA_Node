# Purpose: Agent-facing guidance embedded in the MCP server: instructions text, corex:// resources, and prompt templates.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
"""Guidance (T10 owner: implement; T00 fixes the shape).

Resources served by the MCP server:

- ``corex://guide``      -- concise workflow: status -> catalog -> build with
  graph_apply -> style -> group/subnode -> annotate -> save -> screenshot.
- ``corex://ops``        -- generated op reference (from ``op_catalog``).
- ``corex://styles``     -- node/edge/text style keys and enums.
- ``corex://node-types`` -- passive families with port keys and property hints.

``server_instructions()`` is the MCP ``instructions`` string; keep it short and
imperative (agents read it once per session).
"""

from __future__ import annotations

RESOURCE_URIS: tuple[str, ...] = ("corex://guide", "corex://ops", "corex://styles", "corex://node-types")


def server_instructions() -> str:
    raise NotImplementedError("server_instructions is implemented in T10")


def resource_text(uri: str) -> str:
    raise NotImplementedError("resource_text is implemented in T10")


__all__ = ["RESOURCE_URIS", "resource_text", "server_instructions"]
