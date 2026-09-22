# Purpose: Public automation API package (Qt-free): wire protocol, op catalog, transport, client, launcher, MCP server.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
"""COREX automation API.

This package is the *public* programmatic control surface for COREX. It is a
local, opt-in developer automation surface (not permissioned agent
orchestration): the app must be started with ``--automation`` (or spawned by
``ea_node_editor.automation.launcher``), it listens on loopback only, and every
connection authenticates with a per-instance token.

Layering (see ``docs/agent_maps/feature_routes/automation_api_mcp.md``):

- ``protocol`` / ``errors`` / ``op_model`` / ``ops`` / ``op_catalog`` -- the
  frozen wire contract and the declarative operation catalog.
- ``transport`` / ``discovery`` / ``gate`` -- the in-process loopback server,
  instance discovery files, and the env-driven capability gate.
- ``client`` / ``client_api`` / ``launcher`` -- the stdlib-only Python client.
- ``mcp_server`` / ``guidance`` -- the MCP adapter (optional ``[mcp]`` extra).

Nothing in this package may import PyQt6 or ``ea_node_editor.ui``; the GUI-side
handlers live in ``ea_node_editor.ui.shell.automation``.
"""

from __future__ import annotations

__all__: list[str] = []
