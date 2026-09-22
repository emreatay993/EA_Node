# Purpose: Per-domain CorexClient facades (thin sugar over client.call); one module per catalog domain.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
"""Client facades. Each ``*Api`` class holds the ``CorexClient`` and turns
keyword arguments into catalog params; nothing here validates beyond what the
server does, so the facades stay honest to the wire contract."""

from __future__ import annotations

__all__: list[str] = []
