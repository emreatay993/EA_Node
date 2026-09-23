# Purpose: Per-user instance discovery files (<instances_dir>/<instance_id>.json) with port, token, pid, mode; liveness-filtered listing.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_discovery.py
"""Instance discovery.

Discovery must stay Qt-free and must not import ``ea_node_editor.settings``
(which pulls the UI package). The directory is
``%LOCALAPPDATA%/COREX_Node_Editor/automation/instances`` on Windows (falls
back to ``%APPDATA%`` then ``~/.config``). ``COREX_AUTOMATION_DISCOVERY_DIR``
overrides it for tests and private launches. Files are written atomically
(temp + replace) with owner-only permissions where the platform supports it.

Liveness: a record is live only when its ``pid`` exists (``psutil.pid_exists``;
the pid check is skipped when psutil is unavailable) *and* a TCP connect to
``127.0.0.1:port`` succeeds. A recycled pid therefore never keeps a dead
instance's record alive, and ``find_instance`` never returns a record whose
server is gone. ``list_instances(live_only=True)`` deletes the files of dead
instances (dead pid or closed port) so a crashed COREX never leaves a stale
token behind; malformed or unreadable files are skipped but left in place.
"""

from __future__ import annotations

import json
import logging
import os
import re
import socket
import tempfile
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

ENV_DISCOVERY_DIR = "COREX_AUTOMATION_DISCOVERY_DIR"
INSTANCE_FILE_SUFFIX = ".json"

_LOGGER = logging.getLogger(__name__)
_INSTANCE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_PROBE_TIMEOUT_S = 0.25
_PREFERRED_MODE = "visible"

try:
    import psutil as _psutil
except ImportError:  # pragma: no cover - the project venv ships psutil; stdlib fallback below
    _psutil = None


@dataclass(frozen=True, slots=True)
class InstanceRecord:
    instance_id: str
    pid: int
    port: int
    token: str = field(repr=False)  # shared secret: kept out of repr, still written by to_dict()
    mode: str
    app_version: str
    started_at: float
    project_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def instances_dir() -> Path:
    override = os.environ.get(ENV_DISCOVERY_DIR, "").strip()
    if override:
        return Path(override)
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    root = Path(base) if base else Path.home() / ".config"
    return root / "COREX_Node_Editor" / "automation" / "instances"


def instance_file_path(instance_id: str) -> Path:
    return instances_dir() / f"{instance_id}{INSTANCE_FILE_SUFFIX}"


def write_instance_file(record: InstanceRecord) -> Path:
    """Atomically publish ``record`` as ``<instances_dir>/<instance_id>.json`` and return the path."""
    instance_id = _validated_instance_id(record.instance_id)
    path = instance_file_path(instance_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(record.to_dict(), indent=2, sort_keys=True)
    fd, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{instance_id}.", suffix=".tmp")
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if os.name != "nt":
            os.chmod(temp_path, 0o600)
        os.replace(temp_path, path)
    except BaseException:
        try:
            temp_path.unlink()
        except OSError:
            pass
        raise
    return path


def remove_instance_file(instance_id: str) -> bool:
    """Delete the discovery file; ``False`` when it did not exist."""
    path = instance_file_path(_validated_instance_id(instance_id))
    try:
        path.unlink()
    except FileNotFoundError:
        return False
    return True


def list_instances(*, live_only: bool = True) -> list[InstanceRecord]:
    """Return known instances, newest ``started_at`` first.

    With ``live_only`` (default) dead instances are dropped and their files
    deleted. Unreadable or malformed files are skipped and left untouched.
    """
    directory = instances_dir()
    try:
        candidates = sorted(directory.glob(f"*{INSTANCE_FILE_SUFFIX}"))
    except OSError:
        return []
    records: list[InstanceRecord] = []
    for path in candidates:
        if not path.is_file():
            continue
        record = _read_record(path)
        if record is None:
            continue
        if live_only and not _instance_alive(record):
            _delete_stale(path)
            continue
        records.append(record)
    records.sort(key=lambda item: item.started_at, reverse=True)
    return records


def find_instance(instance_id: str | None = None, *, mode: str | None = None) -> InstanceRecord | None:
    """Locate one live instance.

    - ``instance_id`` given: the exact match (``mode`` is ignored) or ``None``.
    - otherwise: the newest live instance whose mode equals ``mode``; when
      ``mode`` is ``None`` a ``visible`` instance is preferred, falling back to
      the newest live instance of any mode.
    """
    records = list_instances(live_only=True)
    if instance_id:
        wanted = str(instance_id).strip()
        for record in records:
            if record.instance_id == wanted:
                return record
        return None
    if mode is not None:
        wanted_mode = str(mode).strip().lower()
        for record in records:
            if record.mode == wanted_mode:
                return record
        return None
    for record in records:
        if record.mode == _PREFERRED_MODE:
            return record
    return records[0] if records else None


# --------------------------------------------------------------------- helpers


def _validated_instance_id(instance_id: str) -> str:
    value = str(instance_id or "").strip()
    if not _INSTANCE_ID_RE.match(value):
        raise ValueError(f"invalid automation instance id {instance_id!r}")
    return value


def _read_record(path: Path) -> InstanceRecord | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    if not isinstance(payload, Mapping):
        return None
    try:
        instance_id = str(payload.get("instance_id") or path.stem).strip()
        pid = int(payload["pid"])
        port = int(payload["port"])
        token = str(payload["token"])
        mode = str(payload.get("mode") or _PREFERRED_MODE).strip().lower()
        app_version = str(payload.get("app_version") or "")
        started_at = float(payload.get("started_at") or 0.0)
        project_path = str(payload.get("project_path") or "")
    except (KeyError, TypeError, ValueError):
        return None
    if not instance_id or pid <= 0 or not (0 < port <= 65535) or not token:
        return None
    return InstanceRecord(
        instance_id=instance_id,
        pid=pid,
        port=port,
        token=token,
        mode=mode,
        app_version=app_version,
        started_at=started_at,
        project_path=project_path,
    )


def _delete_stale(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        _LOGGER.debug("could not delete stale automation instance file %s", path, exc_info=True)


def _instance_alive(record: InstanceRecord) -> bool:
    """Liveness probe: the pid exists (when psutil is available) and the loopback port accepts a connect."""
    if _psutil is not None and not _pid_exists(record.pid):
        return False
    return _port_open(record.port)


def _pid_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    if _psutil is None:
        return False
    try:
        return bool(_psutil.pid_exists(pid))
    except Exception:  # pragma: no cover - psutil should not raise here
        return False


def _port_open(port: int, *, timeout_s: float = _PROBE_TIMEOUT_S) -> bool:
    if not (0 < port <= 65535):
        return False
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout_s):
            return True
    except OSError:
        return False


__all__ = [
    "ENV_DISCOVERY_DIR",
    "INSTANCE_FILE_SUFFIX",
    "InstanceRecord",
    "find_instance",
    "instance_file_path",
    "instances_dir",
    "list_instances",
    "remove_instance_file",
    "write_instance_file",
]
