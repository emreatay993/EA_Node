#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

find_worktree_python() {
  if ! command -v git >/dev/null 2>&1; then
    return 1
  fi

  local line=""
  local worktree_path=""
  local candidate=""
  while IFS= read -r line; do
    [[ "${line}" == worktree\ * ]] || continue
    worktree_path="${line#worktree }"
    [[ "${worktree_path}" == "${REPO_ROOT}" ]] && continue
    candidate="${worktree_path}/venv/Scripts/python.exe"
    if [[ -f "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done < <(git -C "${REPO_ROOT}" worktree list --porcelain 2>/dev/null || true)

  return 1
}

if [[ -n "${EA_NODE_EDITOR_PYTHON:-}" ]]; then
  PYTHON_BIN="${EA_NODE_EDITOR_PYTHON}"
elif [[ -f "${REPO_ROOT}/venv/Scripts/python.exe" ]]; then
  PYTHON_BIN="${REPO_ROOT}/venv/Scripts/python.exe"
elif WORKTREE_PYTHON="$(find_worktree_python)"; then
  PYTHON_BIN="${WORKTREE_PYTHON}"
else
  PYTHON_BIN="python"
fi

cd "${REPO_ROOT}"
exec "${PYTHON_BIN}" main.py "$@"
