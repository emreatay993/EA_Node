# Purpose: Spawn/attach COREX instances for automation (modes auto|attach|private) with isolated session-state dirs and discovery matching.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
"""Launcher (T08 owner: implement; T00 fixes the shape).

Modes
-----
- ``attach``  -- connect to a running instance (``instance_id`` or the newest
  live visible one); never spawns.
- ``auto``    -- attach when a live instance exists, else spawn a *visible*
  instance.
- ``private`` -- always spawn an isolated instance. ``headless=True`` (default)
  sets ``QT_QPA_PLATFORM=offscreen``; ``headless=False`` gives full-fidelity
  rendering in a real (optionally invisible) window.

Every spawned instance gets:
``EA_NODE_EDITOR_BOOTSTRAPPED=1`` (skip re-exec; B4), a launcher-generated
``COREX_AUTOMATION_INSTANCE_ID`` used to match the discovery file (Windows
``Popen.pid != COREX pid``), ``COREX_AUTOMATION_TOKEN``, ``COREX_AUTOMATION_MODE``,
``COREX_SESSION_STATE_DIR=<temp>`` so it never touches the user's autosave /
last-session / staging (B2), ``QT_QUICK_CONTROLS_STYLE=Basic`` and
``QT_QPA_FONTDIR=C:\\Windows\\Fonts`` on Windows. The command is
``<venv python> -m ea_node_editor.bootstrap --automation [--automation-port N]
[--automation-instance-id ID]``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ea_node_editor.automation.discovery import InstanceRecord

LAUNCH_MODES: tuple[str, ...] = ("auto", "attach", "private")
DEFAULT_STARTUP_TIMEOUT_S = 90.0


@dataclass(slots=True)
class CorexInstanceHandle:
    record: InstanceRecord
    process: Any = None
    owned: bool = False
    session_state_dir: Path | None = None
    log_path: Path | None = None
    env: dict[str, str] = field(default_factory=dict)

    @property
    def spawned(self) -> bool:
        return self.process is not None

    def terminate(self, *, timeout_s: float = 10.0) -> None:
        raise NotImplementedError("CorexInstanceHandle.terminate is implemented in T08")


def python_executable() -> Path:
    """Return the interpreter to launch COREX with (repo venv when present)."""
    raise NotImplementedError("python_executable is implemented in T08")


def launch_corex(
    mode: str = "auto",
    *,
    headless: bool = True,
    instance_id: str | None = None,
    port: int = 0,
    startup_timeout_s: float = DEFAULT_STARTUP_TIMEOUT_S,
    extra_env: dict[str, str] | None = None,
) -> CorexInstanceHandle:
    raise NotImplementedError("launch_corex is implemented in T08")


__all__ = ["CorexInstanceHandle", "DEFAULT_STARTUP_TIMEOUT_S", "LAUNCH_MODES", "launch_corex", "python_executable"]
