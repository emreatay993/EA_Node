# Purpose: Start/stop the in-app automation server for a ShellWindow (called from app.py after the splash, never from composition).
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
"""Automation service lifecycle (T02 owner: implement; T00 fixes the shape).

``start_automation_if_enabled(window)`` reads ``automation_gate()``; when
enabled it builds ``AutomationContext.from_host(window)``, the handler table,
an ``AutomationBridge`` (parented to the window), an ``AutomationServer`` on
``127.0.0.1:<gate.port>`` whose dispatch callback is ``bridge.submit(...).result()``,
and publishes the discovery file. ``AutomationService.stop()`` removes the
discovery file, stops the server, and shuts the bridge down; it is connected to
``QApplication.aboutToQuit`` and registered with ``atexit``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ea_node_editor.automation.gate import AutomationGate, automation_gate


@dataclass(slots=True)
class AutomationService:
    gate: AutomationGate
    bridge: Any
    server: Any
    instance_file: Any = None
    stopped: bool = False

    @property
    def port(self) -> int:
        return int(getattr(self.server, "port", 0) or 0)

    def stop(self) -> None:
        if self.stopped:
            return
        self.stopped = True
        # T02: remove discovery file, stop server, shutdown bridge.


def start_automation_if_enabled(window: Any, *, gate: AutomationGate | None = None) -> AutomationService | None:
    """Start the automation server for ``window`` when the gate is enabled."""
    resolved_gate = gate or automation_gate()
    if not resolved_gate.enabled:
        return None
    # T02: build context/handlers/bridge/server, publish discovery, wire aboutToQuit + atexit.
    return None


__all__ = ["AutomationService", "start_automation_if_enabled"]
