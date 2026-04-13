from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


_BOOTSTRAP_SENTINEL = "EA_NODE_EDITOR_BOOTSTRAPPED"


def _path_key(path: Path) -> str:
    return os.path.normcase(str(path.resolve()))


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _find_worktree_python(repo_root: Path) -> Path | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "worktree", "list", "--porcelain"],
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError:
        return None

    repo_root_key = _path_key(repo_root)
    for line in result.stdout.splitlines():
        if not line.startswith("worktree "):
            continue
        worktree_path = Path(line[len("worktree ") :].strip())
        if _path_key(worktree_path) == repo_root_key:
            continue
        candidate = worktree_path / "venv" / "Scripts" / "python.exe"
        if candidate.is_file():
            return candidate
    return None


def _preferred_python(repo_root: Path) -> Path | None:
    local_python = repo_root / "venv" / "Scripts" / "python.exe"
    if local_python.is_file():
        return local_python
    return _find_worktree_python(repo_root)


def _bootstrap_python() -> None:
    if getattr(sys, "frozen", False):
        return

    if os.environ.get(_BOOTSTRAP_SENTINEL) == "1":
        return

    repo_root = _repo_root()
    preferred_python = _preferred_python(repo_root)
    if preferred_python is None:
        return

    if _path_key(Path(sys.executable)) == _path_key(preferred_python):
        return

    env = os.environ.copy()
    env[_BOOTSTRAP_SENTINEL] = "1"
    os.chdir(repo_root)
    os.execvpe(
        str(preferred_python),
        [str(preferred_python), "main.py", *sys.argv[1:]],
        env,
    )


def main() -> int:
    _bootstrap_python()
    from ea_node_editor.app import run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
