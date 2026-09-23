# Purpose: Start/stop the in-app automation server for a ShellWindow (called from app.py after the splash, never from composition).
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_bridge.py
"""Automation service lifecycle.

``start_automation_if_enabled(window)`` reads ``automation_gate()``; when
enabled it builds ``AutomationContext.from_host(window)``, the handler table,
an ``AutomationBridge`` (parented to the window), an ``AutomationServer`` on
``127.0.0.1:<gate.port>`` whose dispatch callback is ``bridge.submit(...).result()``,
and publishes the discovery file. ``AutomationService.stop()`` removes the
discovery file, shuts the bridge down, and stops the server; it is connected to
``QApplication.aboutToQuit`` and registered with ``atexit``.

The bridge is shut down *before* the server so transport reader threads parked
in ``Future.result()`` wake up with ``APP_SHUTTING_DOWN`` (and can still write
it back) instead of stalling ``AutomationServer.stop()`` until its join timeout.
"""

from __future__ import annotations

import atexit
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QApplication

from ea_node_editor import __version__
from ea_node_editor.automation.discovery import InstanceRecord, remove_instance_file, write_instance_file
from ea_node_editor.automation.gate import AutomationGate, automation_gate
from ea_node_editor.automation.protocol import AutomationRequest, AutomationResponse, HelloResponse
from ea_node_editor.automation.transport import AutomationServer
from ea_node_editor.ui.shell.automation.bridge import AutomationBridge
from ea_node_editor.ui.shell.automation.context import AutomationContext
from ea_node_editor.ui.shell.automation.registry import build_handler_table

logger = logging.getLogger(__name__)


# weakref_slot: PyQt6 keeps a weak reference to the receiver of ``aboutToQuit.connect(service.stop)``;
# a plain ``slots=True`` dataclass has no ``__weakref__`` slot and the connect raised inside the
# startup QTimer slot, which PyQt6 turns into a fatal abort (found by the T13 e2e probe).
@dataclass(slots=True, weakref_slot=True)
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
        """Idempotent teardown: discovery file, then bridge, then server (each step isolated)."""
        if self.stopped:
            return
        self.stopped = True
        try:
            remove_instance_file(self.gate.instance_id)
        except Exception:  # noqa: BLE001 - teardown must run to completion (aboutToQuit / atexit)
            logger.exception("automation: could not remove the instance discovery file")
        try:
            self.bridge.shutdown()
        except Exception:  # noqa: BLE001
            logger.exception("automation: bridge shutdown failed")
        try:
            self.server.stop()
        except Exception:  # noqa: BLE001
            logger.exception("automation: server stop failed")


def _bridge_dispatch(bridge: AutomationBridge):
    def dispatch(request: AutomationRequest) -> AutomationResponse:
        return bridge.submit(request).result()

    return dispatch


def _project_path(window: Any) -> str:
    value = getattr(window, "project_path", None)
    return str(value) if value else ""


def start_automation_if_enabled(window: Any, *, gate: AutomationGate | None = None) -> AutomationService | None:
    """Start the automation server for ``window`` when the gate is enabled."""
    resolved_gate = gate if gate is not None else automation_gate()
    if not resolved_gate.enabled:
        return None
    context = AutomationContext.from_host(window, gate=resolved_gate)
    handlers = build_handler_table()
    bridge = AutomationBridge(context, handlers, parent=window if isinstance(window, QObject) else None)
    hello = HelloResponse(
        app_version=__version__,
        instance_id=resolved_gate.instance_id,
        pid=os.getpid(),
        mode=resolved_gate.mode,
    )
    server = AutomationServer(
        token=resolved_gate.token,
        dispatch=_bridge_dispatch(bridge),
        hello=hello,
        port=resolved_gate.port,
    )
    try:
        bound_port = server.start()
        port = int(bound_port or getattr(server, "port", 0) or 0)
        record = InstanceRecord(
            instance_id=resolved_gate.instance_id,
            pid=os.getpid(),
            port=port,
            token=resolved_gate.token,
            mode=resolved_gate.mode,
            app_version=__version__,
            started_at=time.time(),
            project_path=_project_path(window),
        )
        instance_file = write_instance_file(record)
    except Exception:
        bridge.shutdown()
        try:
            server.stop()
        except Exception:  # noqa: BLE001 - best effort while propagating the original failure
            logger.exception("automation: server stop after a failed start raised")
        raise
    service = AutomationService(gate=resolved_gate, bridge=bridge, server=server, instance_file=instance_file)
    app = QApplication.instance()
    if app is not None:
        app.aboutToQuit.connect(service.stop)
    atexit.register(service.stop)
    logger.info(
        "automation server listening on 127.0.0.1:%s (instance %s, mode %s)",
        port,
        resolved_gate.instance_id,
        resolved_gate.mode,
    )
    return service


__all__ = ["AutomationService", "start_automation_if_enabled"]
