# ADDON_MANAGER_BACKEND_PREPARATION P00: Bootstrap

## Objective

- Establish the `ADDON_MANAGER_BACKEND_PREPARATION` packet set, initialize the status ledger, register the packet docs in the canonical spec index, and ensure the future QA matrix path is trackable.

## Preconditions

- The canonical spec index exists at [docs/specs/INDEX.md](../../INDEX.md).
- No `addon_manager_backend_preparation` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies

- none

## Target Subsystems

- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/addon_manager_backend_preparation/*`

## Conservative Write Scope

- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/addon_manager_backend_preparation/**`

## Required Behavior

- Create `docs/specs/work_packets/addon_manager_backend_preparation/`.
- Add `ADDON_MANAGER_BACKEND_PREPARATION_MANIFEST.md` and `ADDON_MANAGER_BACKEND_PREPARATION_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P08`.
- Update `docs/specs/INDEX.md` with links to the `ADDON_MANAGER_BACKEND_PREPARATION` manifest and status ledger.
- Update `.gitignore` so the packet directory and future `docs/specs/perf/ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md` file are trackable.
- Mark `P00` as `PASS` in `ADDON_MANAGER_BACKEND_PREPARATION_STATUS.md` and leave `P01` through `P08` as `PENDING`.
- Keep packet order, branch labels, locked defaults, execution waves, review-gate structure, and wrap-up expectations aligned with the approved scope.
- Make no runtime, product-source, test, or requirement-doc changes outside the documentation bootstrap scope.

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
    ".gitignore",
    "docs/specs/INDEX.md",
    "docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_MANIFEST.md",
    "docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_STATUS.md",
    "docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P00_bootstrap.md",
    "docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P00_bootstrap_PROMPT.md",
    "docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P01_addon_contracts_and_state_model.md",
    "docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P01_addon_contracts_and_state_model_PROMPT.md",
    "docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P02_addon_manager_entry_and_open_request_plumbing.md",
    "docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P02_addon_manager_entry_and_open_request_plumbing_PROMPT.md",
    "docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P03_generic_missing_addon_placeholder_projection.md",
    "docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P03_generic_missing_addon_placeholder_projection_PROMPT.md",
    "docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P04_locked_node_graph_host_and_mockup_b_visuals.md",
    "docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P04_locked_node_graph_host_and_mockup_b_visuals_PROMPT.md",
    "docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P05_ansys_dpf_addon_package_extraction.md",
    "docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P05_ansys_dpf_addon_package_extraction_PROMPT.md",
    "docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P06_dpf_hot_apply_registry_and_runtime_rebuild.md",
    "docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P06_dpf_hot_apply_registry_and_runtime_rebuild_PROMPT.md",
    "docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P07_addon_manager_variant4_surface.md",
    "docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P07_addon_manager_variant4_surface_PROMPT.md",
    "docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P08_verification_docs_traceability_closeout.md",
    "docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P08_verification_docs_traceability_closeout_PROMPT.md",
]
missing = [path for path in required if not Path(path).exists()]
if missing:
    print("MISSING: " + ", ".join(missing))
    raise SystemExit(1)
for tracked_path in (
    "docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_MANIFEST.md",
    "docs/specs/work_packets/addon_manager_backend_preparation/P08_verification_docs_traceability_closeout_WRAPUP.md",
    "docs/specs/perf/ADDON_MANAGER_BACKEND_PREPARATION_QA_MATRIX.md",
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
    "ADDON_MANAGER_BACKEND_PREPARATION Work Packet Manifest",
    "ADDON_MANAGER_BACKEND_PREPARATION Status Ledger",
):
    if needle not in index_text:
        print("INDEX_MISSING: " + needle)
        raise SystemExit(1)
print("ADDON_MANAGER_BACKEND_PREPARATION_P00_FILE_GATE_PASS")
'@ | .\venv\Scripts\python.exe -
```

## Review Gate

```powershell
@'
from pathlib import Path

text = Path(
    "docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_STATUS.md"
).read_text(encoding="utf-8")
checks = (
    "| P00 Bootstrap | `codex/addon-manager-backend-preparation/p00-bootstrap` | PASS |",
    "| P01 Add-on Contracts And State Model | `codex/addon-manager-backend-preparation/p01-addon-contracts-and-state-model` | PENDING |",
    "| P02 Add-On Manager Entry And Open-Request Plumbing | `codex/addon-manager-backend-preparation/p02-addon-manager-entry-and-open-request-plumbing` | PENDING |",
    "| P03 Generic Missing-Add-On Placeholder Projection | `codex/addon-manager-backend-preparation/p03-generic-missing-addon-placeholder-projection` | PENDING |",
    "| P04 Locked Node Graph Host And Mockup B Visuals | `codex/addon-manager-backend-preparation/p04-locked-node-graph-host-and-mockup-b-visuals` | PENDING |",
    "| P05 ANSYS DPF Add-On Package Extraction | `codex/addon-manager-backend-preparation/p05-ansys-dpf-addon-package-extraction` | PENDING |",
    "| P06 DPF Hot Apply Registry And Runtime Rebuild | `codex/addon-manager-backend-preparation/p06-dpf-hot-apply-registry-and-runtime-rebuild` | PENDING |",
    "| P07 Add-On Manager Variant 4 Surface | `codex/addon-manager-backend-preparation/p07-addon-manager-variant4-surface` | PENDING |",
    "| P08 Verification Docs Traceability Closeout | `codex/addon-manager-backend-preparation/p08-verification-docs-traceability-closeout` | PENDING |",
)
for needle in checks:
    if needle not in text:
        print("STATUS_MISSING: " + needle)
        raise SystemExit(1)
print("ADDON_MANAGER_BACKEND_PREPARATION_P00_STATUS_PASS")
'@ | .\venv\Scripts\python.exe -
```

## Expected Artifacts

- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_MANIFEST.md`
- `docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_STATUS.md`
- `docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P00_bootstrap.md`
- `docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P01_addon_contracts_and_state_model.md`
- `docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P01_addon_contracts_and_state_model_PROMPT.md`
- `docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P02_addon_manager_entry_and_open_request_plumbing.md`
- `docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P02_addon_manager_entry_and_open_request_plumbing_PROMPT.md`
- `docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P03_generic_missing_addon_placeholder_projection.md`
- `docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P03_generic_missing_addon_placeholder_projection_PROMPT.md`
- `docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P04_locked_node_graph_host_and_mockup_b_visuals.md`
- `docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P04_locked_node_graph_host_and_mockup_b_visuals_PROMPT.md`
- `docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P05_ansys_dpf_addon_package_extraction.md`
- `docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P05_ansys_dpf_addon_package_extraction_PROMPT.md`
- `docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P06_dpf_hot_apply_registry_and_runtime_rebuild.md`
- `docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P06_dpf_hot_apply_registry_and_runtime_rebuild_PROMPT.md`
- `docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P07_addon_manager_variant4_surface.md`
- `docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P07_addon_manager_variant4_surface_PROMPT.md`
- `docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P08_verification_docs_traceability_closeout.md`
- `docs/specs/work_packets/addon_manager_backend_preparation/ADDON_MANAGER_BACKEND_PREPARATION_P08_verification_docs_traceability_closeout_PROMPT.md`

## Acceptance Criteria

- The file-gate command returns `ADDON_MANAGER_BACKEND_PREPARATION_P00_FILE_GATE_PASS`.
- The review gate returns `ADDON_MANAGER_BACKEND_PREPARATION_P00_STATUS_PASS`.
- `ADDON_MANAGER_BACKEND_PREPARATION_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `.gitignore`, `docs/specs/INDEX.md`, and the new `addon_manager_backend_preparation` packet docs.

## Handoff Notes

- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- Before executor-driven packet work begins, commit or merge the bootstrap docs so worker worktrees inherit them from the target merge branch.
