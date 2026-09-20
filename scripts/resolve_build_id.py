# Purpose: Resolve a displayed COREX build code to local Git commit candidates.
# Map: docs/agent_maps/subsystems/packaging_generated_assets.md
# Tests: tests/test_build_info.py
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from ea_node_editor.common.build_info import BuildInfo


def resolve_build_id(root: Path, build_id: str) -> list[str]:
    # Count can differ in shallow history; the derived token is the identity.
    token = build_id.strip().upper().rsplit("-", 1)[-1]
    if not build_id.upper().startswith("CX-") or len(token) != 12 or any(
        char not in "0123456789ABCDEF" for char in token
    ):
        raise ValueError("Expected a COREX build code such as CX-1234-7A92D6E1B830.")
    result = subprocess.run(
        ["git", "-C", str(root), "log", "--all", "--reflog", "--format=%H"],
        check=True, capture_output=True, text=True,
    )
    return sorted({
        commit for commit in result.stdout.splitlines()
        if BuildInfo(commit=commit).build_id == f"CX-{token}"
    })


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve a COREX splash build code in local Git history.")
    parser.add_argument("build_id")
    args = parser.parse_args()
    try:
        matches = resolve_build_id(REPO_ROOT, args.build_id)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        parser.exit(2, f"{exc}\n")
    if not matches:
        print("No local match. Fetch the relevant branch/history, or inspect the package's build_info.json.")
        return 1
    for commit in matches:
        print(commit)
    if len(matches) > 1:
        print("Multiple candidates: use the package's full commit in build_info.json to disambiguate.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
