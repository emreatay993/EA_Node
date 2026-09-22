# Purpose: Render the generated op reference (markdown) from the op catalog for docs/AUTOMATION_API_GUIDE.md and corex://ops.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_catalog.py
"""Doc generation (T12 owner: implement; T00 fixes the shape).

``render_op_reference_markdown()`` returns one markdown section per domain with
a table (op, MCP tool, undo step, apply-allowed) and a per-op block listing
params/results. ``scripts``/docs call it so the guide never drifts from the
catalog; ``test_catalog.py`` asserts the committed guide section matches.
"""

from __future__ import annotations


def render_op_reference_markdown() -> str:
    raise NotImplementedError("render_op_reference_markdown is implemented in T12")


__all__ = ["render_op_reference_markdown"]
