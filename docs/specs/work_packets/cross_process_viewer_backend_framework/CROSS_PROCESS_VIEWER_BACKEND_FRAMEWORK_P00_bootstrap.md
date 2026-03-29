# CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK P00: Bootstrap

## Objective

- Establish the `CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK` packet set, initialize the status ledger, register the packet docs in the canonical spec index, and ensure the new packet directory plus future wrap-ups and QA matrix are trackable.

## Preconditions

- The canonical spec index exists at [docs/specs/INDEX.md](../../INDEX.md).
- The review baseline exists at [docs/Cross-Process Viewer Backend Framework for Embedded DPF Sessions.md](../../../Cross-Process%20Viewer%20Backend%20Framework%20for%20Embedded%20DPF%20Sessions.md).
- No `cross_process_viewer_backend_framework` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies

- none

## Target Subsystems

- `docs/specs/work_packets/cross_process_viewer_backend_framework/*`
- `docs/specs/INDEX.md`
- `.gitignore`

## Conservative Write Scope

- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/**`

## Required Behavior

- Create `docs/specs/work_packets/cross_process_viewer_backend_framework/`.
- Add `CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_MANIFEST.md` and `CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P06` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK` manifest and status ledger.
- Update `.gitignore` so the new packet docs, future packet wrap-ups, and future `docs/specs/perf/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md` file are trackable.
- Mark `P00` as `PASS` in `CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md` and leave `P01` through `P06` as `PENDING`.
- Keep packet order, branch labels, locked defaults, execution waves, review-gate structure, and wrap-up expectations aligned with the cross-process viewer backend framework plan.
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
    "docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_MANIFEST.md",
    "docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md",
    "docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P00_bootstrap.md",
    "docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P00_bootstrap_PROMPT.md",
    "docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P01_execution_viewer_backend_contract.md",
    "docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P01_execution_viewer_backend_contract_PROMPT.md",
    "docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P02_dpf_transport_bundle_materialization.md",
    "docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P02_dpf_transport_bundle_materialization_PROMPT.md",
    "docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P03_shell_viewer_host_framework.md",
    "docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P03_shell_viewer_host_framework_PROMPT.md",
    "docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P04_dpf_widget_binder_transport_adoption.md",
    "docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P04_dpf_widget_binder_transport_adoption_PROMPT.md",
    "docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P05_bridge_projection_run_required_states.md",
    "docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P05_bridge_projection_run_required_states_PROMPT.md",
    "docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P06_verification_docs_traceability_closeout.md",
    "docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P06_verification_docs_traceability_closeout_PROMPT.md",
]
missing = [path for path in required if not Path(path).exists()]
if missing:
    print("MISSING: " + ", ".join(missing))
    raise SystemExit(1)
for tracked_path in (
    "docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_MANIFEST.md",
    "docs/specs/work_packets/cross_process_viewer_backend_framework/P06_verification_docs_traceability_closeout_WRAPUP.md",
    "docs/specs/perf/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md",
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
    "CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK Work Packet Manifest",
    "CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK Status Ledger",
):
    if needle not in index_text:
        print("INDEX_MISSING: " + needle)
        raise SystemExit(1)
print("CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P00_FILE_GATE_PASS")
'@ | .\venv\Scripts\python.exe -
```

## Review Gate

```powershell
@'
from pathlib import Path

text = Path(
    "docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md"
).read_text(encoding="utf-8")
checks = (
    "| P00 Bootstrap | `codex/cross-process-viewer-backend-framework/p00-bootstrap` | PASS |",
    "| P01 Execution Viewer Backend Contract | `codex/cross-process-viewer-backend-framework/p01-execution-viewer-backend-contract` | PENDING |",
    "| P02 DPF Transport Bundle Materialization | `codex/cross-process-viewer-backend-framework/p02-dpf-transport-bundle-materialization` | PENDING |",
    "| P03 Shell Viewer Host Framework | `codex/cross-process-viewer-backend-framework/p03-shell-viewer-host-framework` | PENDING |",
    "| P04 DPF Widget Binder Transport Adoption | `codex/cross-process-viewer-backend-framework/p04-dpf-widget-binder-transport-adoption` | PENDING |",
    "| P05 Bridge Projection Run-Required States | `codex/cross-process-viewer-backend-framework/p05-bridge-projection-run-required-states` | PENDING |",
    "| P06 Verification Docs Traceability Closeout | `codex/cross-process-viewer-backend-framework/p06-verification-docs-traceability-closeout` | PENDING |",
)
for needle in checks:
    if needle not in text:
        print("STATUS_MISSING: " + needle)
        raise SystemExit(1)
print("CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P00_STATUS_PASS")
'@ | .\venv\Scripts\python.exe -
```

## Expected Artifacts

- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_MANIFEST.md`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P00_bootstrap.md`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P01_execution_viewer_backend_contract.md`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P01_execution_viewer_backend_contract_PROMPT.md`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P02_dpf_transport_bundle_materialization.md`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P02_dpf_transport_bundle_materialization_PROMPT.md`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P03_shell_viewer_host_framework.md`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P03_shell_viewer_host_framework_PROMPT.md`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P04_dpf_widget_binder_transport_adoption.md`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P04_dpf_widget_binder_transport_adoption_PROMPT.md`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P05_bridge_projection_run_required_states.md`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P05_bridge_projection_run_required_states_PROMPT.md`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P06_verification_docs_traceability_closeout.md`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P06_verification_docs_traceability_closeout_PROMPT.md`

## Acceptance Criteria

- The file-gate command returns `CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P00_FILE_GATE_PASS`.
- The review gate returns `CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P00_STATUS_PASS`.
- `CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `.gitignore`, `docs/specs/INDEX.md`, and the new `cross_process_viewer_backend_framework` packet docs.

## Handoff Notes

- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next execution thread begins with `P01`.
