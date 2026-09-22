# Purpose: Per-user instance discovery files (<instances_dir>/<instance_id>.json) with port, token, pid, mode; liveness-filtered listing.
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_automation_boundaries.py
"""Instance discovery (T01 owner: implement; T00 fixes the shape).

Discovery must stay Qt-free and must not import ``ea_node_editor.settings``
(which pulls the UI package). The directory is
``%LOCALAPPDATA%/COREX_Node_Editor/automation/instances`` on Windows (falls
back to ``%APPDATA%`` then ``~/.config``). ``COREX_AUTOMATION_DISCOVERY_DIR``
overrides it for tests and private launches. Files are written atomically
(temp + replace) with owner-only permissions where the platform supports it.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ENV_DISCOVERY_DIR = "COREX_AUTOMATION_DISCOVERY_DIR"
INSTANCE_FILE_SUFFIX = ".json"


@dataclass(frozen=True, slots=True)
class InstanceRecord:
    instance_id: str
    pid: int
    port: int
    token: str
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
    raise NotImplementedError("write_instance_file is implemented in T01")


def remove_instance_file(instance_id: str) -> bool:
    raise NotImplementedError("remove_instance_file is implemented in T01")


def list_instances(*, live_only: bool = True) -> list[InstanceRecord]:
    raise NotImplementedError("list_instances is implemented in T01")


def find_instance(instance_id: str | None = None, *, mode: str | None = None) -> InstanceRecord | None:
    raise NotImplementedError("find_instance is implemented in T01")


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
