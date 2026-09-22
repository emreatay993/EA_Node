# Purpose: Qt-free loopback NDJSON server (AutomationServer) that authenticates with the instance token and hands requests to a dispatch callback.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
"""Automation transport (T01 owner: implement; T00 fixes the shape).

``AutomationServer`` runs entirely outside Qt: a listening ``socket`` on
``127.0.0.1`` (never ``0.0.0.0``), an accept thread, and one reader thread per
connection. The first frame must be a ``hello`` whose token matches via
``hmac.compare_digest``; anything else closes the socket with ``AUTH_FAILED``.
Each subsequent frame is decoded into ``AutomationRequest`` and passed to
``dispatch(request) -> AutomationResponse``; the callback blocks (the GUI bridge
resolves a ``Future``) and the response is written back on the same connection.
Frames over ``MAX_FRAME_BYTES`` -> ``PROTOCOL_ERROR`` and disconnect.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field

from ea_node_editor.automation.protocol import AutomationRequest, AutomationResponse, HelloResponse

DispatchCallback = Callable[[AutomationRequest], AutomationResponse]

LOOPBACK_HOST = "127.0.0.1"


@dataclass(slots=True)
class AutomationServer:
    token: str
    dispatch: DispatchCallback
    hello: HelloResponse
    port: int = 0
    host: str = LOOPBACK_HOST
    _thread: threading.Thread | None = field(default=None, repr=False)
    _stop_event: threading.Event = field(default_factory=threading.Event, repr=False)

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> int:
        """Bind, start the accept thread, and return the bound port."""
        raise NotImplementedError("AutomationServer.start is implemented in T01")

    def stop(self, *, timeout_s: float = 2.0) -> None:
        self._stop_event.set()


__all__ = ["AutomationServer", "DispatchCallback", "LOOPBACK_HOST"]
