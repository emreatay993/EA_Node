# Purpose: Identify source launches and freeze Git provenance into packaged builds.
# Map: docs/agent_maps/subsystems/packaging_generated_assets.md
# Tests: tests/test_build_info.py
from __future__ import annotations

import json
import hashlib
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from ea_node_editor import __version__


@dataclass(frozen=True)
class BuildInfo:
    version: str = __version__
    commit: str | None = None
    revision: int | None = None
    dirty: bool | None = None
    built_at: str | None = None
    profile: str | None = None

    @property
    def build_id(self) -> str | None:
        if not self.commit:
            return None
        token = hashlib.sha256(f"COREX:{self.commit}".encode("ascii")).hexdigest()[:12].upper()
        ordinal = f"{self.revision}-" if self.revision is not None else ""
        return f"CX-{ordinal}{token}"

    @property
    def label(self) -> str:
        parts = [f"v{self.version}"]
        if self.commit:
            parts.append(self.build_id)
            if self.dirty:
                parts.append("dirty")
        else:
            parts.append("commit unknown")
        return " · ".join(parts)


def source_build_info(root: Path) -> BuildInfo:
    """Read this checkout, including Git worktrees; never use a parent repository."""
    if not (root / ".git").exists():
        return BuildInfo()

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            check=True, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=3,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        ).stdout.strip()

    try:
        commit = git("rev-parse", "HEAD")
        shallow = git("rev-parse", "--is-shallow-repository") == "true"
        revision = None if shallow else int(git("rev-list", "--count", "HEAD"))
        dirty = bool(git("status", "--porcelain", "--untracked-files=normal"))
    except (OSError, subprocess.SubprocessError, ValueError):
        return BuildInfo()
    return BuildInfo(commit=commit, revision=revision, dirty=dirty)


def write_build_info(root: Path, destination: Path, profile: str) -> Path:
    """Stamp every PyInstaller invocation; missing Git provenance fails the build."""
    info = source_build_info(root)
    if not info.commit:
        raise RuntimeError("Cannot identify COREX build commit. Build from a Git checkout with Git available.")
    payload = asdict(info)
    payload.update(built_at=datetime.now(timezone.utc).isoformat(), profile=profile)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return destination


@lru_cache(maxsize=1)
def get_build_info() -> BuildInfo:
    """Capture source identity once per launch, or read only the frozen build stamp."""
    if getattr(sys, "frozen", False):
        path = Path(__file__).resolve().parents[1] / "build_info.json"
        try:
            return BuildInfo(**json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError):
            return BuildInfo()
    return source_build_info(Path(__file__).resolve().parents[2])
