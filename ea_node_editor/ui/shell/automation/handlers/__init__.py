# Purpose: Per-domain automation handler modules; each ends with an explicit HANDLERS table merged by registry.py.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
"""Automation handlers.

Rules every handler module follows (guard-railed by
``tests/automation/test_automation_boundaries.py``):

- signature ``handler(context: AutomationContext, params: Mapping[str, Any]) -> dict | Deferred``
- no decorators, no import-time side effects, no ``__getattr__``/getattr dispatch
- never import ``QMessageBox`` / ``QInputDialog`` / ``QFileDialog``; use the
  dialog-free seams instead
- call existing owners only (``context.scene`` and friends); never
  ``GraphModel._*`` or ``GraphRecordMutation``
- check-before / verify-after: silent no-ops become ``NO_EFFECT``
- never write the string ``execution_event`` + ``.connect(`` (repo pin)
"""

from __future__ import annotations

__all__: list[str] = []
