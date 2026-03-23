# CTRL_CANVAS_INSERT_MENU P00: Bootstrap

## Objective
- Establish the `CTRL_CANVAS_INSERT_MENU` packet set, initialize the status ledger, register the packet docs in the canonical spec index, and ensure the packet directory is not git-ignored.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md).
- No `ctrl_canvas_insert_menu` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies
- none

## Target Subsystems
- `docs/specs/work_packets/ctrl_canvas_insert_menu/*`
- `docs/specs/INDEX.md`
- `.gitignore`

## Conservative Write Scope
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/ctrl_canvas_insert_menu/**`

## Required Behavior
- Create `docs/specs/work_packets/ctrl_canvas_insert_menu/`.
- Add `CTRL_CANVAS_INSERT_MENU_MANIFEST.md` and `CTRL_CANVAS_INSERT_MENU_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P04` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `CTRL_CANVAS_INSERT_MENU` manifest and status ledger.
- Update `.gitignore` so the new `docs/specs/work_packets/ctrl_canvas_insert_menu/` packet directory is tracked like the other shipped packet sets.
- Mark `P00` as `PASS` in `CTRL_CANVAS_INSERT_MENU_STATUS.md` and leave `P01` through `P04` as `PENDING`.
- Keep packet order, branch labels, execution waves, locked defaults, review-gate structure, and wrap-up expectations aligned with the approved Ctrl-canvas-insert-menu plan.
- Make no runtime, script, test, requirement-doc, or fixture changes outside the documentation bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes under `scripts/**`.
- No changes to requirements, QA docs, fixtures, or `README.md` in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe - <<'PY'
from pathlib import Path
import subprocess

required = [
    "docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_MANIFEST.md",
    "docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_STATUS.md",
    "docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P00_bootstrap.md",
    "docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P00_bootstrap_PROMPT.md",
    "docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P01_text_annotation_contract_and_typography.md",
    "docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P01_text_annotation_contract_and_typography_PROMPT.md",
    "docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P02_ctrl_canvas_insert_menu_shell.md",
    "docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P02_ctrl_canvas_insert_menu_shell_PROMPT.md",
    "docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P03_text_inline_editing_workflow.md",
    "docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P03_text_inline_editing_workflow_PROMPT.md",
    "docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P04_regression_docs_traceability.md",
    "docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P04_regression_docs_traceability_PROMPT.md",
]
missing = [path for path in required if not Path(path).exists()]
if missing:
    print("MISSING: " + ", ".join(missing))
    raise SystemExit(1)
check = subprocess.run(
    ["git", "check-ignore", "docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_MANIFEST.md"],
    capture_output=True,
    text=True,
)
if check.returncode == 0:
    print("CTRL_CANVAS_INSERT_MENU_DOCS_IGNORED")
    raise SystemExit(1)
index_text = Path("docs/specs/INDEX.md").read_text(encoding="utf-8")
for needle in (
    "CTRL_CANVAS_INSERT_MENU Work Packet Manifest",
    "CTRL_CANVAS_INSERT_MENU Status Ledger",
):
    if needle not in index_text:
        print("INDEX_MISSING: " + needle)
        raise SystemExit(1)
print("CTRL_CANVAS_INSERT_MENU_P00_FILE_GATE_PASS")
PY`

## Review Gate
- `./venv/Scripts/python.exe - <<'PY'
from pathlib import Path
text = Path("docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_STATUS.md").read_text(encoding="utf-8")
if "| P00 Bootstrap | `codex/ctrl-canvas-insert-menu/p00-bootstrap` | PASS |" not in text:
    raise SystemExit(1)
print("CTRL_CANVAS_INSERT_MENU_P00_STATUS_PASS")
PY`

## Expected Artifacts
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_MANIFEST.md`
- `docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_STATUS.md`
- `docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P00_bootstrap.md`
- `docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P01_text_annotation_contract_and_typography.md`
- `docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P01_text_annotation_contract_and_typography_PROMPT.md`
- `docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P02_ctrl_canvas_insert_menu_shell.md`
- `docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P02_ctrl_canvas_insert_menu_shell_PROMPT.md`
- `docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P03_text_inline_editing_workflow.md`
- `docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P03_text_inline_editing_workflow_PROMPT.md`
- `docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P04_regression_docs_traceability.md`
- `docs/specs/work_packets/ctrl_canvas_insert_menu/CTRL_CANVAS_INSERT_MENU_P04_regression_docs_traceability_PROMPT.md`

## Acceptance Criteria
- The verification command returns `CTRL_CANVAS_INSERT_MENU_P00_FILE_GATE_PASS`.
- The review gate returns `CTRL_CANVAS_INSERT_MENU_P00_STATUS_PASS`.
- `CTRL_CANVAS_INSERT_MENU_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `.gitignore`, `docs/specs/INDEX.md`, and the new `ctrl_canvas_insert_menu` packet docs.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next execution thread begins with `P01`.
