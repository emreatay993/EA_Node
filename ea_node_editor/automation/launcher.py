# Purpose: Spawn/attach COREX instances for automation (modes auto|attach|private) with isolated session-state dirs and discovery matching.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_launcher.py
"""Launcher for automation-enabled COREX instances.

Modes
-----
- ``attach``  -- connect to a running instance (``instance_id`` or the newest
  live visible one); never spawns. Raises ``NOT_FOUND`` when none is live.
- ``auto``    -- attach to a live *visible* instance (``instance_id``, else the
  newest COREX started with ``--automation``); private/offscreen instances
  belong to whoever spawned them and are never adopted. Otherwise spawn a
  *visible* instance (``headless`` is ignored; a visible instance is never
  forced offscreen).
- ``private`` -- always spawn an isolated instance. ``headless=True`` (default)
  sets ``QT_QPA_PLATFORM=offscreen``; ``headless=False`` gives full-fidelity
  rendering in a real window.

Every spawned instance gets:
``EA_NODE_EDITOR_BOOTSTRAPPED=1`` (skip re-exec; B4), a launcher-generated
``COREX_AUTOMATION_INSTANCE_ID`` used to match the discovery file (Windows
``Popen.pid != COREX pid``), a launcher-generated ``COREX_AUTOMATION_TOKEN``,
``COREX_AUTOMATION_MODE`` (``private`` | ``visible``), ``COREX_AUTOMATION_PORT``,
``COREX_SESSION_STATE_DIR=<fresh temp dir>`` for *every* spawn -- private and
auto-visible alike -- so a spawned COREX never restores, overwrites, or deletes
the user's autosave / last-session / staging (B2),
``QT_QUICK_CONTROLS_STYLE=Basic`` (Windows, when unset) and
``QT_QPA_FONTDIR=C:\\Windows\\Fonts`` (Windows, headless). The command is
``<venv python> -m ea_node_editor.bootstrap --automation --automation-port N
--automation-instance-id ID`` run from the repo root with stdout/stderr
redirected to ``<session dir>/corex-automation.log`` (Windows spawns use
``CREATE_NEW_PROCESS_GROUP``).

Startup polls discovery every ``_POLL_INTERVAL_S`` until the instance file
exists with a port that accepts a TCP connection. Process exit raises
``INTERNAL`` and ``startup_timeout_s`` raises ``TIMEOUT``; both terminate the
child and carry the log tail in ``details``.

``CorexInstanceHandle.terminate()`` only stops instances the launcher spawned
(``owned``): it terminates/kills the process and, once the process has exited,
removes the discovery file and deletes the session-state directory (log
included). A directory is never deleted while its process is still alive. For
attached instances ``terminate()`` is a no-op, so a client never unregisters a
COREX it did not start. ``CorexClient.close()`` owns the quit-or-detach policy:
an owned visible instance with unsaved work is *detached* (``detached=True``)
and left running for the user together with its session directory.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ea_node_editor.automation import discovery, gate
from ea_node_editor.automation.discovery import InstanceRecord
from ea_node_editor.automation.errors import INTERNAL, NOT_FOUND, TIMEOUT, AutomationOpError

LAUNCH_MODES: tuple[str, ...] = ("auto", "attach", "private")
MODE_AUTO, MODE_ATTACH, MODE_PRIVATE = LAUNCH_MODES
DEFAULT_STARTUP_TIMEOUT_S = 90.0
BOOTSTRAP_MODULE = "ea_node_editor.bootstrap"
BOOTSTRAP_SENTINEL = "EA_NODE_EDITOR_BOOTSTRAPPED"
LOG_FILE_NAME = "corex-automation.log"
LOOPBACK_HOST = "127.0.0.1"
QT_OFFSCREEN_PLATFORM = "offscreen"
QT_QUICK_CONTROLS_STYLE = "Basic"
WINDOWS_FONT_DIR = "C:\\Windows\\Fonts"
_TEMP_PREFIX = "corex-automation-"
_POLL_INTERVAL_S = 0.25
_PROBE_TIMEOUT_S = 1.0
_LOG_TAIL_CHARS = 4000
_ATTACH_HINT = "Start COREX with --automation, or use mode='private' to spawn an isolated instance, then retry."
_LOG_HINT = "Inspect the startup log (details.log_path / details.log_tail), fix the failure, then relaunch."


@dataclass(slots=True)
class CorexInstanceHandle:
    record: InstanceRecord
    process: Any = None
    owned: bool = False
    session_state_dir: Path | None = None
    log_path: Path | None = None
    env: dict[str, str] = field(default_factory=dict, repr=False)
    # Set by CorexClient.close() when an owned visible instance was left running for the user.
    detached: bool = field(default=False, compare=False)
    _terminated: bool = field(default=False, init=False, repr=False, compare=False)

    @property
    def spawned(self) -> bool:
        return self.process is not None

    @property
    def private(self) -> bool:
        mode = self.env.get(gate.ENV_MODE) or self.record.mode
        return str(mode).strip().lower() == gate.MODE_PRIVATE

    @property
    def terminated(self) -> bool:
        return self._terminated

    @property
    def alive(self) -> bool:
        """``True`` while the spawned process is running; ``False`` when not spawned or exited."""
        process = self.process
        return process is not None and process.poll() is None

    def poll(self) -> int | None:
        """Exit code of the spawned process, ``None`` while running or when not spawned."""
        process = self.process
        if process is None:
            return None
        return process.poll()

    def wait(self, *, timeout_s: float = 10.0) -> int | None:
        """Wait up to ``timeout_s`` for the spawned process; returns its exit code or ``None``."""
        process = self.process
        if process is None:
            return None
        try:
            return process.wait(timeout=max(0.0, float(timeout_s)))
        except subprocess.TimeoutExpired:
            return None

    def terminate(self, *, timeout_s: float = 10.0) -> None:
        """Stop an owned instance and clean up after it; idempotent, no-op for attached instances.

        Cleanup (discovery file, session-state directory) only happens once the
        process has exited; a process that survives terminate + kill keeps both.
        """
        if self._terminated:
            return
        self._terminated = True
        if not self.owned:
            return
        _stop_process(self.process, timeout_s)
        if self.alive:
            return
        try:
            discovery.remove_instance_file(self.record.instance_id)
        except (OSError, ValueError):
            pass
        if self.session_state_dir is not None:
            shutil.rmtree(self.session_state_dir, ignore_errors=True)


def python_executable() -> Path:
    """Return the interpreter to launch COREX with (repo venv when present, else this interpreter)."""
    candidate = _venv_python(_repo_root())
    if candidate.is_file():
        return candidate
    return Path(sys.executable)


def launch_corex(
    mode: str = "auto",
    *,
    headless: bool = True,
    instance_id: str | None = None,
    port: int = 0,
    startup_timeout_s: float = DEFAULT_STARTUP_TIMEOUT_S,
    extra_env: dict[str, str] | None = None,
) -> CorexInstanceHandle:
    """Attach to or spawn a COREX instance according to ``mode`` (see module docstring)."""
    if mode not in LAUNCH_MODES:
        raise ValueError(f"mode must be one of {LAUNCH_MODES}, got {mode!r}")
    port_number = _validated_port(port)
    if mode == MODE_ATTACH:
        record = discovery.find_instance(instance_id)
        if record is None:
            raise _no_instance_error(instance_id)
        return CorexInstanceHandle(record=record, owned=False)
    if mode == MODE_AUTO:
        # Only visible instances are adopted; an explicit instance_id still wins over the mode filter.
        record = discovery.find_instance(instance_id, mode=gate.MODE_VISIBLE)
        if record is not None:
            return CorexInstanceHandle(record=record, owned=False)
        return _spawn(
            automation_mode=gate.MODE_VISIBLE,
            headless=False,
            instance_id=instance_id,
            port=port_number,
            startup_timeout_s=startup_timeout_s,
            extra_env=extra_env,
        )
    return _spawn(
        automation_mode=gate.MODE_PRIVATE,
        headless=headless,
        instance_id=instance_id,
        port=port_number,
        startup_timeout_s=startup_timeout_s,
        extra_env=extra_env,
    )


# ------------------------------------------------------------------ spawning


def _spawn(
    *,
    automation_mode: str,
    headless: bool,
    instance_id: str | None,
    port: int,
    startup_timeout_s: float,
    extra_env: dict[str, str] | None,
) -> CorexInstanceHandle:
    requested_id = str(instance_id or "").strip()
    resolved_id = requested_id or gate.generate_instance_id()
    # Every spawn gets its own session-state dir (B2); the startup log lives inside it.
    session_state_dir = Path(tempfile.mkdtemp(prefix=_TEMP_PREFIX))
    env = _spawn_environment(
        automation_mode=automation_mode,
        headless=headless,
        instance_id=resolved_id,
        port=port,
        session_state_dir=session_state_dir,
        extra_env=extra_env,
    )
    log_path = session_state_dir / LOG_FILE_NAME
    command = [
        str(python_executable()),
        "-m",
        BOOTSTRAP_MODULE,
        "--automation",
        "--automation-port",
        str(port),
        "--automation-instance-id",
        resolved_id,
    ]
    popen_kwargs: dict[str, Any] = {}
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    try:
        with open(log_path, "ab") as log_file:
            process = subprocess.Popen(
                command,
                cwd=str(_repo_root()),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                **popen_kwargs,
            )
    except OSError as exc:
        shutil.rmtree(session_state_dir, ignore_errors=True)
        raise AutomationOpError(
            INTERNAL,
            f"Could not start COREX: {exc}",
            hint="Check the interpreter path and the repository checkout, then retry.",
            details={"command": command, "log_path": str(log_path)},
            retryable=False,
        ) from exc
    provisional = CorexInstanceHandle(
        record=_placeholder_record(resolved_id, process, automation_mode),
        process=process,
        owned=True,
        session_state_dir=session_state_dir,
        log_path=log_path,
        env=env,
    )
    record = _wait_for_instance(provisional, startup_timeout_s)
    return CorexInstanceHandle(
        record=record,
        process=process,
        owned=True,
        session_state_dir=session_state_dir,
        log_path=log_path,
        env=env,
    )


def _spawn_environment(
    *,
    automation_mode: str,
    headless: bool,
    instance_id: str,
    port: int,
    session_state_dir: Path,
    extra_env: dict[str, str] | None,
) -> dict[str, str]:
    env = os.environ.copy()
    env[BOOTSTRAP_SENTINEL] = "1"
    env[gate.ENV_ENABLED] = "1"
    env[gate.ENV_PORT] = str(int(port))
    env[gate.ENV_INSTANCE_ID] = instance_id
    env[gate.ENV_TOKEN] = gate.generate_token()
    env[gate.ENV_MODE] = automation_mode
    env[gate.ENV_SESSION_STATE_DIR] = str(session_state_dir)
    if headless:
        env["QT_QPA_PLATFORM"] = QT_OFFSCREEN_PLATFORM
        if sys.platform == "win32":
            env["QT_QPA_FONTDIR"] = WINDOWS_FONT_DIR
    if sys.platform == "win32":
        env.setdefault("QT_QUICK_CONTROLS_STYLE", QT_QUICK_CONTROLS_STYLE)
    if extra_env:
        env.update({str(key): str(value) for key, value in extra_env.items()})
    return env


def _wait_for_instance(handle: CorexInstanceHandle, startup_timeout_s: float) -> InstanceRecord:
    """Poll discovery until the spawned instance publishes a reachable port; clean up and raise otherwise."""
    process = handle.process
    instance_id = handle.record.instance_id
    timeout = max(0.0, float(startup_timeout_s))
    deadline = time.monotonic() + timeout
    while True:
        exit_code = process.poll()
        if exit_code is not None:
            details = _failure_details(handle, exit_code=exit_code)
            handle.terminate()
            raise AutomationOpError(
                INTERNAL,
                f"COREX exited with code {exit_code} before its automation server came up.",
                hint=_LOG_HINT,
                details=details,
                retryable=False,
            )
        record = discovery.find_instance(instance_id)
        if record is not None and record.port > 0 and _probe_port(record.port):
            return record
        if time.monotonic() >= deadline:
            details = _failure_details(handle, timeout_s=timeout)
            handle.terminate()
            raise AutomationOpError(
                TIMEOUT,
                f"COREX did not publish a reachable automation port within {timeout:g} s.",
                hint="Increase startup_timeout_s, or inspect the startup log (details.log_path / details.log_tail).",
                details=details,
                retryable=False,
            )
        time.sleep(_POLL_INTERVAL_S)


def _failure_details(handle: CorexInstanceHandle, **extra: Any) -> dict[str, Any]:
    return {
        "instance_id": handle.record.instance_id,
        "pid": handle.record.pid,
        "log_path": str(handle.log_path) if handle.log_path is not None else "",
        "log_tail": _read_log_tail(handle.log_path),
        **extra,
    }


def _stop_process(process: Any, timeout_s: float) -> None:
    if process is None or process.poll() is not None:
        return
    try:
        process.terminate()
    except OSError:
        return
    try:
        process.wait(timeout=max(0.0, float(timeout_s)))
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        process.kill()
        process.wait(timeout=max(0.0, float(timeout_s)))
    except (OSError, subprocess.TimeoutExpired):
        pass


def _probe_port(port: int, *, timeout_s: float = _PROBE_TIMEOUT_S) -> bool:
    try:
        with socket.create_connection((LOOPBACK_HOST, int(port)), timeout=timeout_s):
            return True
    except OSError:
        return False


def _read_log_tail(path: Path | None, *, limit: int = _LOG_TAIL_CHARS) -> str:
    if path is None:
        return ""
    try:
        data = Path(path).read_bytes()
    except OSError:
        return ""
    return data.decode("utf-8", errors="replace")[-limit:]


def _placeholder_record(instance_id: str, process: Any, automation_mode: str) -> InstanceRecord:
    return InstanceRecord(
        instance_id=instance_id,
        pid=int(getattr(process, "pid", 0) or 0),
        port=0,
        token="",
        mode=automation_mode,
        app_version="",
        started_at=time.time(),
    )


def _no_instance_error(instance_id: str | None) -> AutomationOpError:
    wanted = f" '{instance_id}'" if instance_id else ""
    return AutomationOpError(
        NOT_FOUND,
        f"No live COREX automation instance{wanted} was found to attach to.",
        hint=_ATTACH_HINT,
        details={"instance_id": str(instance_id or "")},
        retryable=False,
    )


def _validated_port(port: int) -> int:
    try:
        number = int(port)
    except (TypeError, ValueError):
        raise ValueError(f"port must be an integer in 0..65535, got {port!r}") from None
    if number < 0 or number > 65535:
        raise ValueError(f"port must be an integer in 0..65535, got {port!r}")
    return number


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _venv_python(repo_root: Path) -> Path:
    if sys.platform == "win32":
        return repo_root / "venv" / "Scripts" / "python.exe"
    return repo_root / "venv" / "bin" / "python"


__all__ = [
    "BOOTSTRAP_MODULE",
    "BOOTSTRAP_SENTINEL",
    "CorexInstanceHandle",
    "DEFAULT_STARTUP_TIMEOUT_S",
    "LAUNCH_MODES",
    "LOG_FILE_NAME",
    "MODE_ATTACH",
    "MODE_AUTO",
    "MODE_PRIVATE",
    "launch_corex",
    "python_executable",
]
