# ARCHITECTURE_RESIDUAL_REFACTOR P00: Bootstrap

## Objective

- Establish the `ARCHITECTURE_RESIDUAL_REFACTOR` packet set, write the residual review baseline, initialize the status ledger, register the new packet set in the spec index, and ensure the packet docs, future wrap-ups, and future QA matrix are trackable.

## Preconditions

- The canonical spec index exists at [docs/specs/INDEX.md](../../INDEX.md).
- No `architecture_residual_refactor` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies

- `none`

## Target Subsystems

- `docs/ARCHITECTURE_RESIDUAL_REVIEW_2026-04-03.md`
- `docs/specs/work_packets/architecture_residual_refactor/*`
- `docs/specs/INDEX.md`
- `.gitignore`

## Conservative Write Scope

- `.gitignore`
- `docs/ARCHITECTURE_RESIDUAL_REVIEW_2026-04-03.md`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/architecture_residual_refactor/**`

## Required Behavior

- Create `docs/ARCHITECTURE_RESIDUAL_REVIEW_2026-04-03.md` as the stable review baseline for this packet set.
- Add `ARCHITECTURE_RESIDUAL_REFACTOR_MANIFEST.md` and `ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P08` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `ARCHITECTURE_RESIDUAL_REFACTOR` manifest and status ledger.
- Update `.gitignore` so the new packet docs, future packet wrap-ups, and future `docs/specs/perf/ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX.md` file are trackable.
- Mark `P00` as `PASS` in `ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md` and leave `P01` through `P08` as `PENDING`.
- Keep packet order, branch labels, locked defaults, execution waves, review-gate structure, and wrap-up expectations aligned with the repo's tracked work-packet conventions.
- Make no runtime, product-source, test, packaging-script, or requirement-doc changes outside the documentation bootstrap scope.

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
    "docs/ARCHITECTURE_RESIDUAL_REVIEW_2026-04-03.md",
    "docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_MANIFEST.md",
    "docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md",
]
slugs = [
    "P00_bootstrap",
    "P01_shell_host_surface_retirement",
    "P02_shell_lifecycle_isolation_hardening",
    "P03_graph_scene_bridge_decomposition",
    "P04_viewer_projection_authority_split",
    "P05_runtime_snapshot_boundary_decoupling",
    "P06_graph_mutation_service_decoupling",
    "P07_shared_runtime_contract_extraction",
    "P08_verification_architecture_closeout",
]
for slug in slugs:
    required.append(
        f"docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_{slug}.md"
    )
    required.append(
        f"docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_{slug}_PROMPT.md"
    )
missing = [path for path in required if not Path(path).exists()]
if missing:
    print("MISSING: " + ", ".join(missing))
    raise SystemExit(1)
for tracked_path in (
    "docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_MANIFEST.md",
    "docs/specs/work_packets/architecture_residual_refactor/P08_verification_architecture_closeout_WRAPUP.md",
    "docs/specs/perf/ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX.md",
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
    "ARCHITECTURE_RESIDUAL_REFACTOR Work Packet Manifest",
    "ARCHITECTURE_RESIDUAL_REFACTOR Status Ledger",
):
    if needle not in index_text:
        print("INDEX_MISSING: " + needle)
        raise SystemExit(1)
print("ARCHITECTURE_RESIDUAL_REFACTOR_P00_FILE_GATE_PASS")
'@ | .\venv\Scripts\python.exe -
```

## Review Gate

```powershell
@'
from pathlib import Path
text = Path(
    "docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md"
).read_text(encoding="utf-8")
if "| P00 Bootstrap | `codex/architecture-residual-refactor/p00-bootstrap` | PASS |" not in text:
    raise SystemExit(1)
print("ARCHITECTURE_RESIDUAL_REFACTOR_P00_STATUS_PASS")
'@ | .\venv\Scripts\python.exe -
```

## Expected Artifacts

- `.gitignore`
- `docs/ARCHITECTURE_RESIDUAL_REVIEW_2026-04-03.md`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_MANIFEST.md`
- `docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md`
- `docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_P00_bootstrap.md`
- `docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_P01_shell_host_surface_retirement.md`
- `docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_P01_shell_host_surface_retirement_PROMPT.md`
- `docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_P02_shell_lifecycle_isolation_hardening.md`
- `docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_P02_shell_lifecycle_isolation_hardening_PROMPT.md`
- `docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_P03_graph_scene_bridge_decomposition.md`
- `docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_P03_graph_scene_bridge_decomposition_PROMPT.md`
- `docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_P04_viewer_projection_authority_split.md`
- `docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_P04_viewer_projection_authority_split_PROMPT.md`
- `docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_P05_runtime_snapshot_boundary_decoupling.md`
- `docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_P05_runtime_snapshot_boundary_decoupling_PROMPT.md`
- `docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_P06_graph_mutation_service_decoupling.md`
- `docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_P06_graph_mutation_service_decoupling_PROMPT.md`
- `docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_P07_shared_runtime_contract_extraction.md`
- `docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_P07_shared_runtime_contract_extraction_PROMPT.md`
- `docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_P08_verification_architecture_closeout.md`
- `docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_P08_verification_architecture_closeout_PROMPT.md`

## Acceptance Criteria

- The verification command returns `ARCHITECTURE_RESIDUAL_REFACTOR_P00_FILE_GATE_PASS`.
- The review gate returns `ARCHITECTURE_RESIDUAL_REFACTOR_P00_STATUS_PASS`.
- `ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `.gitignore`, `docs/ARCHITECTURE_RESIDUAL_REVIEW_2026-04-03.md`, `docs/specs/INDEX.md`, and the new `architecture_residual_refactor` packet docs.

## Handoff Notes

- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next execution thread begins with `P01`.
