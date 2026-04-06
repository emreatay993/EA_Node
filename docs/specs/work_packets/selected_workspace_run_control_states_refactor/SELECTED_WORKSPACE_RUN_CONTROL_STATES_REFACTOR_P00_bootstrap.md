# SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR P00: Bootstrap

## Objective

- Establish the `SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR` packet set, initialize the status ledger, register the packet set in the spec index, and ensure the packet docs and future wrap-ups are trackable from the existing selected-workspace run-control plan baseline.

## Preconditions

- The canonical spec index exists at [docs/specs/INDEX.md](../../INDEX.md).
- No `selected_workspace_run_control_states_refactor` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies

- `none`

## Target Subsystems

- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/selected_workspace_run_control_states_refactor/*`

## Conservative Write Scope

- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/selected_workspace_run_control_states_refactor/**`

## Required Behavior

- Add `SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_MANIFEST.md` and `SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P04` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR` manifest and status ledger.
- Update `.gitignore` so the new packet docs and future packet wrap-ups are trackable.
- Mark `P00` as `PASS` in `SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_STATUS.md` and leave `P01` through `P04` as `PENDING`.
- Keep packet order, branch labels, locked defaults, execution waves, review-gate structure, and wrap-up expectations aligned with the repo's tracked work-packet conventions.
- Treat [docs/PLANS/Selected_Workspace_Run_Control_States.md](../../../PLANS/Selected_Workspace_Run_Control_States.md) as the stable scope baseline instead of creating a duplicate requirements document.
- Make no runtime, product-source, or regression-suite changes outside the documentation bootstrap scope.

## Non-Goals

- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes under `scripts/**`.
- No changes to `ARCHITECTURE.md`, `README.md`, or `docs/specs/requirements/**` in this packet.

## Verification Commands

1. File and tracking gate:

```powershell
@'
from pathlib import Path
import subprocess

required = [
    "docs/specs/work_packets/selected_workspace_run_control_states_refactor/SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_MANIFEST.md",
    "docs/specs/work_packets/selected_workspace_run_control_states_refactor/SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_STATUS.md",
]
slugs = [
    "P00_bootstrap",
    "P01_run_flow_selected_workspace_projection",
    "P02_qaction_refresh_and_workspace_switch_sync",
    "P03_presenter_bridge_run_control_projection",
    "P04_qml_toolbar_workspace_run_states",
]
for slug in slugs:
    required.append(
        f"docs/specs/work_packets/selected_workspace_run_control_states_refactor/SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_{slug}.md"
    )
    required.append(
        f"docs/specs/work_packets/selected_workspace_run_control_states_refactor/SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_{slug}_PROMPT.md"
    )
missing = [path for path in required if not Path(path).exists()]
if missing:
    print("MISSING: " + ", ".join(missing))
    raise SystemExit(1)
for tracked_path in (
    "docs/specs/work_packets/selected_workspace_run_control_states_refactor/SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_MANIFEST.md",
    "docs/specs/work_packets/selected_workspace_run_control_states_refactor/P04_qml_toolbar_workspace_run_states_WRAPUP.md",
):
    check = subprocess.run(
        ["git", "check-ignore", tracked_path],
        capture_output=True,
        text=True,
        check=False,
    )
    if check.returncode == 0:
        print("IGNORED: " + tracked_path)
        raise SystemExit(1)
index_text = Path("docs/specs/INDEX.md").read_text(encoding="utf-8")
for needle in (
    "SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR Work Packet Manifest",
    "SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR Status Ledger",
):
    if needle not in index_text:
        print("INDEX_MISSING: " + needle)
        raise SystemExit(1)
print("SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_P00_FILE_GATE_PASS")
'@ | .\venv\Scripts\python.exe -
```

## Review Gate

```powershell
@'
from pathlib import Path
text = Path(
    "docs/specs/work_packets/selected_workspace_run_control_states_refactor/SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_STATUS.md"
).read_text(encoding="utf-8")
if "| P00 Bootstrap | `codex/selected-workspace-run-control-states-refactor/p00-bootstrap` | PASS |" not in text:
    raise SystemExit(1)
print("SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_P00_STATUS_PASS")
'@ | .\venv\Scripts\python.exe -
```

## Expected Artifacts

- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/selected_workspace_run_control_states_refactor/SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_MANIFEST.md`
- `docs/specs/work_packets/selected_workspace_run_control_states_refactor/SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_STATUS.md`
- `docs/specs/work_packets/selected_workspace_run_control_states_refactor/SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_P*.md`
- `docs/specs/work_packets/selected_workspace_run_control_states_refactor/SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_P*_PROMPT.md`

## Acceptance Criteria

- The verification command returns `SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_P00_FILE_GATE_PASS`.
- The review gate returns `SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_P00_STATUS_PASS`.
- `SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `.gitignore`, `docs/specs/INDEX.md`, and the new `selected_workspace_run_control_states_refactor` packet docs.

## Handoff Notes

- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next execution thread begins with `P01`.
