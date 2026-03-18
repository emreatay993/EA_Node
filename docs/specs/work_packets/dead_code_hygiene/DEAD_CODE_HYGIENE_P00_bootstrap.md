# DEAD_CODE_HYGIENE P00: Bootstrap

## Objective
- Establish the `DEAD_CODE_HYGIENE` packet set, initialize the status ledger, and register the packet docs in the canonical spec index.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md).
- No tracked `dead_code_hygiene` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies
- none

## Target Subsystems
- `.gitignore` only for the narrow exception needed to make the new packet docs trackable
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/dead_code_hygiene/*`

## Conservative Write Scope
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/dead_code_hygiene/**`

## Required Behavior
- Create `docs/specs/work_packets/dead_code_hygiene/`.
- Add `DEAD_CODE_HYGIENE_MANIFEST.md` and `DEAD_CODE_HYGIENE_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P03` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `DEAD_CODE_HYGIENE` manifest and status ledger without disturbing the existing in-progress `graph_canvas_perf` index entries.
- Add only the narrow `.gitignore` exception required so the new packet docs are not ignored by git.
- Mark `P00` as `PASS` in `DEAD_CODE_HYGIENE_STATUS.md` and leave `P01` through `P03` as `PENDING`.
- Record that the worktree is already dirty from `graph_canvas_perf` packet docs plus `docs/specs/INDEX.md` and `.gitignore` edits, and that no later packet may revert or restage unrelated changes.
- Keep the packet order, branch labels, locked defaults, sequential execution waves, review-gate structure, and wrap-up expectations aligned with the approved dead-code roadmap.
- Make no runtime, test, script, or requirement-doc changes outside the documentation bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes under `scripts/**`.
- No changes to product docs such as `README.md`, `ARCHITECTURE.md`, or the requirements specs in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe - <<'PY'
from pathlib import Path
import subprocess

required = [
    "docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_MANIFEST.md",
    "docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_STATUS.md",
    "docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_P00_bootstrap.md",
    "docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_P00_bootstrap_PROMPT.md",
    "docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_P01_qml_shell_plumbing_cleanup.md",
    "docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_P01_qml_shell_plumbing_cleanup_PROMPT.md",
    "docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_P02_internal_python_helper_cleanup.md",
    "docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_P02_internal_python_helper_cleanup_PROMPT.md",
    "docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_P03_regression_locks.md",
    "docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_P03_regression_locks_PROMPT.md",
]
missing = [path for path in required if not Path(path).exists()]
if missing:
    print("MISSING: " + ", ".join(missing))
    raise SystemExit(1)
check = subprocess.run(
    ["git", "check-ignore", "docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_MANIFEST.md"],
    capture_output=True,
    text=True,
)
if check.returncode == 0:
    print("DEAD_CODE_HYGIENE_DOCS_IGNORED")
    raise SystemExit(1)
index_text = Path("docs/specs/INDEX.md").read_text(encoding="utf-8")
for needle in (
    "DEAD_CODE_HYGIENE Work Packet Manifest",
    "DEAD_CODE_HYGIENE Status Ledger",
):
    if needle not in index_text:
        print("INDEX_MISSING: " + needle)
        raise SystemExit(1)
print("DEAD_CODE_HYGIENE_P00_FILE_GATE_PASS")
PY`

## Review Gate
- `./venv/Scripts/python.exe - <<'PY'
from pathlib import Path
text = Path("docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_STATUS.md").read_text(encoding="utf-8")
required = [
    "| P00 Bootstrap | `codex/dead-code-hygiene/p00-bootstrap` | PASS |",
    "| P01 QML Shell Plumbing Cleanup | `codex/dead-code-hygiene/p01-qml-shell-plumbing-cleanup` | PENDING |",
    "| P02 Internal Python Helper Cleanup | `codex/dead-code-hygiene/p02-internal-python-helper-cleanup` | PENDING |",
    "| P03 Regression Locks | `codex/dead-code-hygiene/p03-regression-locks` | PENDING |",
]
for needle in required:
    if needle not in text:
        raise SystemExit(1)
print("DEAD_CODE_HYGIENE_P00_STATUS_PASS")
PY`

## Expected Artifacts
- `docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_MANIFEST.md`
- `docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_STATUS.md`
- `docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_P00_bootstrap.md`
- `docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_P01_qml_shell_plumbing_cleanup.md`
- `docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_P01_qml_shell_plumbing_cleanup_PROMPT.md`
- `docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_P02_internal_python_helper_cleanup.md`
- `docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_P02_internal_python_helper_cleanup_PROMPT.md`
- `docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_P03_regression_locks.md`
- `docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_P03_regression_locks_PROMPT.md`

## Acceptance Criteria
- The verification command returns `DEAD_CODE_HYGIENE_P00_FILE_GATE_PASS`.
- The review gate returns `DEAD_CODE_HYGIENE_P00_STATUS_PASS`.
- `DEAD_CODE_HYGIENE_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `.gitignore`, `docs/specs/INDEX.md`, and the new `dead_code_hygiene` packet docs.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- Later packets must preserve the unrelated dirty worktree changes and must not treat them as packet-owned edits.
