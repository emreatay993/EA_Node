# VERIFICATION_SPEED P00: Bootstrap

## Objective
- Establish the `VERIFICATION_SPEED` packet set, initialize the status ledger, and register the packet docs in the canonical spec index.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md).
- No `verification_speed` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies
- none

## Target Subsystems
- `.gitignore` only for a narrow exception needed to make the new packet docs trackable
- `docs/specs/work_packets/verification_speed/*`
- `docs/specs/INDEX.md`

## Conservative Write Scope
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/verification_speed/**`

## Required Behavior
- Create `docs/specs/work_packets/verification_speed/`.
- Add `VERIFICATION_SPEED_MANIFEST.md` and `VERIFICATION_SPEED_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P05` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `VERIFICATION_SPEED` manifest and status ledger.
- Add the narrow `.gitignore` exception required so the new packet docs are not ignored by git.
- Mark `P00` as `PASS` in `VERIFICATION_SPEED_STATUS.md` and leave `P01` through `P05` as `PENDING`.
- Keep the packet order, branch labels, execution waves, locked defaults, review-gate structure, and wrap-up expectations aligned with this approved packet roadmap.
- Make no runtime, script, test, or requirement-doc changes outside the documentation bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes under `scripts/**`.
- No changes to `README.md`, `docs/GETTING_STARTED.md`, or requirements/traceability docs in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe - <<'PY'
from pathlib import Path
import subprocess
import sys

required = [
    "docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_MANIFEST.md",
    "docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_STATUS.md",
    "docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P00_bootstrap.md",
    "docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P00_bootstrap_PROMPT.md",
    "docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P01_pytest_selection_classification.md",
    "docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P01_pytest_selection_classification_PROMPT.md",
    "docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P02_shell_wrapper_collection_hygiene.md",
    "docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P02_shell_wrapper_collection_hygiene_PROMPT.md",
    "docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P03_hybrid_verification_runner.md",
    "docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P03_hybrid_verification_runner_PROMPT.md",
    "docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P04_gui_wait_helper_cleanup.md",
    "docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P04_gui_wait_helper_cleanup_PROMPT.md",
    "docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P05_docs_traceability.md",
    "docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P05_docs_traceability_PROMPT.md",
]
missing = [path for path in required if not Path(path).exists()]
if missing:
    print("MISSING: " + ", ".join(missing))
    raise SystemExit(1)
check = subprocess.run(
    ["git", "check-ignore", "docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_MANIFEST.md"],
    capture_output=True,
    text=True,
)
if check.returncode == 0:
    print("VERIFICATION_SPEED_DOCS_IGNORED")
    raise SystemExit(1)
index_text = Path("docs/specs/INDEX.md").read_text(encoding="utf-8")
for needle in (
    "VERIFICATION_SPEED Work Packet Manifest",
    "VERIFICATION_SPEED Status Ledger",
):
    if needle not in index_text:
        print("INDEX_MISSING: " + needle)
        raise SystemExit(1)
print("VERIFICATION_SPEED_P00_FILE_GATE_PASS")
PY`

## Review Gate
- `./venv/Scripts/python.exe - <<'PY'
from pathlib import Path
text = Path("docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_STATUS.md").read_text(encoding="utf-8")
if "| P00 Bootstrap | `codex/verification-speed/p00-bootstrap` | PASS |" not in text:
    raise SystemExit(1)
print("VERIFICATION_SPEED_P00_STATUS_PASS")
PY`

## Expected Artifacts
- `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_MANIFEST.md`
- `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_STATUS.md`
- `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P00_bootstrap.md`
- `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P01_pytest_selection_classification.md`
- `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P01_pytest_selection_classification_PROMPT.md`
- `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P02_shell_wrapper_collection_hygiene.md`
- `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P02_shell_wrapper_collection_hygiene_PROMPT.md`
- `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P03_hybrid_verification_runner.md`
- `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P03_hybrid_verification_runner_PROMPT.md`
- `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P04_gui_wait_helper_cleanup.md`
- `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P04_gui_wait_helper_cleanup_PROMPT.md`
- `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P05_docs_traceability.md`
- `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P05_docs_traceability_PROMPT.md`

## Acceptance Criteria
- The first verification command returns `VERIFICATION_SPEED_P00_FILE_GATE_PASS`.
- The review gate returns `VERIFICATION_SPEED_P00_STATUS_PASS`.
- `VERIFICATION_SPEED_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `.gitignore`, `docs/specs/INDEX.md`, and the new `verification_speed` packet docs.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next thread may start either `P01` or `P02`, because Wave 1 is explicitly parallel-safe.
