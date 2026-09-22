# Purpose: GUI-side automation package: AutomationContext, op dispatch, handler registry, bridge (GUI thread), service lifecycle.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
"""GUI-thread half of the automation API.

``ea_node_editor.automation`` (Qt-free) owns the wire contract and the op
catalog. This package owns everything that touches live shell objects:

- ``context`` -- ``AutomationContext`` (facade over the shell's existing owners)
  plus summary/lookup helpers shared by every handler.
- ``handlers/<domain>`` -- one module per catalog domain; each ends with an
  explicit ``HANDLERS`` dict. Handlers call ONLY existing owners (``host.scene``,
  ``WorkspaceManager``, ``WorkspaceViewMutation``, controllers, presenters) and
  never open dialogs.
- ``registry`` -- merges the handler tables and asserts they cover the catalog.
- ``dispatch`` -- validate params, run the handler inside one grouped history
  action, and translate exceptions into the frozen error envelope.
- ``bridge`` -- ``QObject`` that receives requests from the transport thread,
  serialises them onto the GUI thread, applies busy/modal guards, and polls
  ``Deferred`` results.
- ``service`` -- ``start_automation_if_enabled(window)`` / stop hooks used by
  ``app.py`` (never by the composition package).
"""

from __future__ import annotations

__all__: list[str] = []
