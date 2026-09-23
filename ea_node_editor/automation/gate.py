# Purpose: Env-driven automation capability gate; reads COREX_AUTOMATION_* once and pops the token from os.environ.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_transport.py
"""Automation gate.

Mirrors ``developer_mode.py``: the environment is read exactly once at import
time so the gate cannot flip after launch. ``bootstrap.main()`` promotes the
``--automation`` CLI flags into these variables before ``app.run()`` imports
this module:

- ``COREX_AUTOMATION_ENABLED=1`` -- start the in-process server.
- ``COREX_AUTOMATION_PORT`` -- loopback port (``0`` / unset = ephemeral).
- ``COREX_AUTOMATION_INSTANCE_ID`` -- launcher-generated id used to match the
  discovery file (Windows re-exec means ``Popen.pid != COREX pid``).
- ``COREX_AUTOMATION_TOKEN`` -- shared secret. It is *popped* from
  ``os.environ`` here so worker / Jupyter / script subprocesses never inherit
  it. When absent the app generates one and publishes it via discovery.
- ``COREX_AUTOMATION_MODE`` -- ``visible`` (default) or ``private``.
"""

from __future__ import annotations

import os
import secrets
import uuid
from dataclasses import dataclass, field

ENV_ENABLED = "COREX_AUTOMATION_ENABLED"
ENV_PORT = "COREX_AUTOMATION_PORT"
ENV_INSTANCE_ID = "COREX_AUTOMATION_INSTANCE_ID"
ENV_TOKEN = "COREX_AUTOMATION_TOKEN"
ENV_MODE = "COREX_AUTOMATION_MODE"
ENV_SESSION_STATE_DIR = "COREX_SESSION_STATE_DIR"

MODE_VISIBLE = "visible"
MODE_PRIVATE = "private"
AUTOMATION_MODES: tuple[str, ...] = (MODE_VISIBLE, MODE_PRIVATE)


@dataclass(frozen=True, slots=True)
class AutomationGate:
    enabled: bool
    port: int
    instance_id: str
    token: str = field(repr=False)  # shared secret: never shown in repr/logs
    mode: str

    @property
    def private(self) -> bool:
        return self.mode == MODE_PRIVATE


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def generate_instance_id() -> str:
    return uuid.uuid4().hex[:12]


def _parse_port(value: str | None) -> int:
    try:
        port = int(str(value or "0").strip() or "0")
    except ValueError:
        return 0
    if port < 0 or port > 65535:
        return 0
    return port


def _read_gate_from_environment() -> AutomationGate:
    enabled = os.environ.get(ENV_ENABLED, "").strip() == "1"
    # Pop the secret so child processes (execution workers, Jupyter, external
    # Python scripts) never see it, even when automation is disabled.
    token = os.environ.pop(ENV_TOKEN, "").strip()
    mode = os.environ.get(ENV_MODE, MODE_VISIBLE).strip().lower() or MODE_VISIBLE
    if mode not in AUTOMATION_MODES:
        mode = MODE_VISIBLE
    instance_id = os.environ.get(ENV_INSTANCE_ID, "").strip()
    if not enabled:
        # A disabled gate never starts a server; do not keep the secret around.
        token = ""
    if enabled and not token:
        token = generate_token()
    if enabled and not instance_id:
        instance_id = generate_instance_id()
    return AutomationGate(
        enabled=enabled,
        port=_parse_port(os.environ.get(ENV_PORT)),
        instance_id=instance_id,
        token=token,
        mode=mode,
    )


_GATE = _read_gate_from_environment()


def automation_gate() -> AutomationGate:
    """Return the process-wide gate captured at import time."""
    return _GATE


def automation_enabled() -> bool:
    return _GATE.enabled


__all__ = [
    "AUTOMATION_MODES",
    "AutomationGate",
    "ENV_ENABLED",
    "ENV_INSTANCE_ID",
    "ENV_MODE",
    "ENV_PORT",
    "ENV_SESSION_STATE_DIR",
    "ENV_TOKEN",
    "MODE_PRIVATE",
    "MODE_VISIBLE",
    "automation_enabled",
    "automation_gate",
    "generate_instance_id",
    "generate_token",
]
