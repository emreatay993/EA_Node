#!/usr/bin/env python3
# Purpose: Install the tracked corex-automation agent skill into the user's Claude Code and/or Codex skill folders (the dot folders are gitignored).
# Map: feature_routes/automation_api_mcp
# Tests: tests/automation/test_docgen.py
"""Copy ``docs/automation/skills/corex-automation`` into user skill folders.

``.claude/`` and ``.codex/skills/*`` are gitignored, so the skill is tracked
under ``docs/`` and installed per user::

    python scripts/install_automation_skill.py --claude --codex
    python scripts/install_automation_skill.py --all --dry-run
    python scripts/install_automation_skill.py --all --force

Destinations (``<home>`` is ``%USERPROFILE%`` on Windows, ``$HOME`` elsewhere,
or ``--home``):

- ``--claude``: ``<home>/.claude/skills/corex-automation``
- ``--codex``:  ``<home>/.codex/skills/corex-automation``

An existing destination is left alone unless ``--force`` replaces it. Exit code
1 when a destination was skipped or nothing was selected. Stdlib only.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "corex-automation"
SKILL_SOURCE = REPO_ROOT / "docs" / "automation" / "skills" / SKILL_NAME
SKILL_FILE = "SKILL.md"
TARGETS: dict[str, tuple[str, ...]] = {
    "claude": (".claude", "skills"),
    "codex": (".codex", "skills"),
}


def destination(target: str, home: Path) -> Path:
    return home.joinpath(*TARGETS[target], SKILL_NAME)


def selected_targets(args: argparse.Namespace) -> list[str]:
    if args.all:
        return list(TARGETS)
    return [name for name in TARGETS if getattr(args, name)]


def install(target: str, home: Path, *, dry_run: bool, force: bool, source: Path = SKILL_SOURCE) -> tuple[bool, str]:
    """Install one target; returns ``(ok, message)``. Never writes when ``dry_run``."""
    dest = destination(target, home)
    exists = dest.exists()
    if exists and not force:
        return False, f"[{target}] skip: {dest} already exists (pass --force to replace it)"
    verb = "replace" if exists else "copy"
    if dry_run:
        return True, f"[{target}] would {verb} {source} -> {dest}"
    if exists:
        if dest.is_dir() and not dest.is_symlink():
            shutil.rmtree(dest)
        else:
            dest.unlink()
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return True, f"[{target}] {'replaced' if exists else 'copied'} {source} -> {dest}"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install the corex-automation skill for Claude Code and/or Codex.")
    parser.add_argument("--claude", action="store_true", help="install into <home>/.claude/skills/corex-automation")
    parser.add_argument("--codex", action="store_true", help="install into <home>/.codex/skills/corex-automation")
    parser.add_argument("--all", action="store_true", help="install for every supported agent")
    parser.add_argument("--dry-run", action="store_true", help="print what would happen without writing anything")
    parser.add_argument("--force", action="store_true", help="replace an existing installed copy")
    parser.add_argument("--home", type=Path, default=None, help="home folder to install under (default: the user's home)")
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    targets = selected_targets(args)
    if not targets:
        print("Choose --claude, --codex, or --all.", file=sys.stderr)
        return 1
    if not (SKILL_SOURCE / SKILL_FILE).is_file():
        print(f"Skill source missing: {SKILL_SOURCE / SKILL_FILE}", file=sys.stderr)
        return 1
    home = (args.home or Path.home()).expanduser()
    ok = True
    for target in targets:
        installed, message = install(target, home, dry_run=args.dry_run, force=args.force)
        print(message)
        ok = ok and installed
    if args.dry_run:
        print("dry run: nothing was written")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
