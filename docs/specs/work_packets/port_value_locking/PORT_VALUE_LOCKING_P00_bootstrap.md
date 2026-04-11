# PORT_VALUE_LOCKING P00: Bootstrap

## Objective

- Establish the `PORT_VALUE_LOCKING` packet set, initialize the status ledger, register the packet docs in the canonical spec index, and ensure the new packet directory plus future wrap-ups and QA matrix are trackable.

## Preconditions

- The canonical spec index exists at [docs/specs/INDEX.md](../../INDEX.md).
- The review baseline exists at [PLANS_TO_IMPLEMENT/in_progress/port_value_locking.md](../../../../PLANS_TO_IMPLEMENT/in_progress/port_value_locking.md).
- No `port_value_locking` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies

- none

## Target Subsystems

- `docs/specs/work_packets/port_value_locking/*`
- `docs/specs/INDEX.md`
- `.gitignore`

## Conservative Write Scope

- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/port_value_locking/**`

## Required Behavior

- Create `docs/specs/work_packets/port_value_locking/`.
- Add `PORT_VALUE_LOCKING_MANIFEST.md` and `PORT_VALUE_LOCKING_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P06` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `PORT_VALUE_LOCKING` manifest and status ledger.
- Update `.gitignore` so the new packet docs, future packet wrap-ups, and future `docs/specs/perf/PORT_VALUE_LOCKING_QA_MATRIX.md` file are trackable.
- Mark `P00` as `PASS` in `PORT_VALUE_LOCKING_STATUS.md` and leave `P01` through `P06` as `PENDING`.
- Keep packet order, branch labels, locked defaults, execution waves, review-gate structure, and wrap-up expectations aligned with `PLANS_TO_IMPLEMENT/in_progress/port_value_locking.md`.
- Make no runtime, product-source, test, packaging-script, or requirement-doc changes outside the documentation bootstrap scope.

## Non-Goals

- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes under `scripts/**`.
- No changes to `docs/specs/requirements/**` or `docs/specs/perf/**` in this packet.

## Verification Commands

1. File gate:

```powershell
@'
from pathlib import Path
import subprocess

required = [
    "docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_MANIFEST.md",
    "docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_STATUS.md",
    "docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P00_bootstrap.md",
    "docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P00_bootstrap_PROMPT.md",
    "docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P01_state_contract_and_persistence.md",
    "docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P01_state_contract_and_persistence_PROMPT.md",
    "docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P02_mutation_semantics_and_locked_port_invariants.md",
    "docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P02_mutation_semantics_and_locked_port_invariants_PROMPT.md",
    "docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P03_payload_projection_and_view_filters.md",
    "docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P03_payload_projection_and_view_filters_PROMPT.md",
    "docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P04_locked_port_qml_ux.md",
    "docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P04_locked_port_qml_ux_PROMPT.md",
    "docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P05_canvas_hide_gestures.md",
    "docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P05_canvas_hide_gestures_PROMPT.md",
    "docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P06_verification_docs_traceability_closeout.md",
    "docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P06_verification_docs_traceability_closeout_PROMPT.md",
]
missing = [path for path in required if not Path(path).exists()]
if missing:
    print("MISSING: " + ", ".join(missing))
    raise SystemExit(1)
for tracked_path in (
    "docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_MANIFEST.md",
    "docs/specs/work_packets/port_value_locking/P06_verification_docs_traceability_closeout_WRAPUP.md",
    "docs/specs/perf/PORT_VALUE_LOCKING_QA_MATRIX.md",
):
    check = subprocess.run(
        ["git", "check-ignore", tracked_path],
        capture_output=True,
        text=True,
    )
    if check.returncode == 0:
        print("IGNORED: " + tracked_path)
        raise SystemExit(1)
index_text = Path("docs/specs/INDEX.md").read_text(encoding="utf-8")
for needle in (
    "PORT_VALUE_LOCKING Work Packet Manifest",
    "PORT_VALUE_LOCKING Status Ledger",
):
    if needle not in index_text:
        print("INDEX_MISSING: " + needle)
        raise SystemExit(1)
print("PORT_VALUE_LOCKING_P00_FILE_GATE_PASS")
'@ | .\venv\Scripts\python.exe -
```

## Review Gate

```powershell
@'
from pathlib import Path

text = Path(
    "docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_STATUS.md"
).read_text(encoding="utf-8")
checks = (
    "| P00 Bootstrap | `codex/port-value-locking/p00-bootstrap` | PASS |",
    "| P01 State Contract and Persistence | `codex/port-value-locking/p01-state-contract-and-persistence` | PENDING |",
    "| P02 Mutation Semantics and Locked Port Invariants | `codex/port-value-locking/p02-mutation-semantics-and-locked-port-invariants` | PENDING |",
    "| P03 Payload Projection and View Filters | `codex/port-value-locking/p03-payload-projection-and-view-filters` | PENDING |",
    "| P04 Locked Port QML UX | `codex/port-value-locking/p04-locked-port-qml-ux` | PENDING |",
    "| P05 Canvas Hide Gestures | `codex/port-value-locking/p05-canvas-hide-gestures` | PENDING |",
    "| P06 Verification Docs Traceability Closeout | `codex/port-value-locking/p06-verification-docs-traceability-closeout` | PENDING |",
)
for needle in checks:
    if needle not in text:
        print("STATUS_MISSING: " + needle)
        raise SystemExit(1)
print("PORT_VALUE_LOCKING_P00_STATUS_PASS")
'@ | .\venv\Scripts\python.exe -
```

## Expected Artifacts

- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_MANIFEST.md`
- `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_STATUS.md`
- `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P00_bootstrap.md`
- `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P01_state_contract_and_persistence.md`
- `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P01_state_contract_and_persistence_PROMPT.md`
- `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P02_mutation_semantics_and_locked_port_invariants.md`
- `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P02_mutation_semantics_and_locked_port_invariants_PROMPT.md`
- `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P03_payload_projection_and_view_filters.md`
- `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P03_payload_projection_and_view_filters_PROMPT.md`
- `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P04_locked_port_qml_ux.md`
- `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P04_locked_port_qml_ux_PROMPT.md`
- `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P05_canvas_hide_gestures.md`
- `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P05_canvas_hide_gestures_PROMPT.md`
- `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P06_verification_docs_traceability_closeout.md`
- `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P06_verification_docs_traceability_closeout_PROMPT.md`

## Acceptance Criteria

- The file-gate command returns `PORT_VALUE_LOCKING_P00_FILE_GATE_PASS`.
- The review gate returns `PORT_VALUE_LOCKING_P00_STATUS_PASS`.
- `PORT_VALUE_LOCKING_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `.gitignore`, `docs/specs/INDEX.md`, and the new `port_value_locking` packet docs.

## Handoff Notes

- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next execution thread begins with `P01`.
