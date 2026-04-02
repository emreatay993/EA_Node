# ARCHITECTURE_FOLLOWUP_REFACTOR P00: Bootstrap

## Objective

- Establish the `ARCHITECTURE_FOLLOWUP_REFACTOR` packet set, write the follow-up review baseline, initialize the status ledger, register the new packet set in the spec index, and ensure the packet docs, future wrap-ups, and future QA matrix are trackable.

## Preconditions

- The canonical spec index exists at [docs/specs/INDEX.md](../../INDEX.md).
- No `architecture_followup_refactor` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies

- none

## Target Subsystems

- `docs/ARCHITECTURE_FOLLOWUP_REVIEW_2026-04-01.md`
- `docs/specs/work_packets/architecture_followup_refactor/*`
- `docs/specs/INDEX.md`
- `.gitignore`

## Conservative Write Scope

- `.gitignore`
- `docs/ARCHITECTURE_FOLLOWUP_REVIEW_2026-04-01.md`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/architecture_followup_refactor/**`

## Required Behavior

- Create `docs/ARCHITECTURE_FOLLOWUP_REVIEW_2026-04-01.md` as the stable review baseline for this packet set.
- Add `ARCHITECTURE_FOLLOWUP_REFACTOR_MANIFEST.md` and `ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P08` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `ARCHITECTURE_FOLLOWUP_REFACTOR` manifest and status ledger.
- Update `.gitignore` so the new packet docs, future packet wrap-ups, and future `docs/specs/perf/ARCHITECTURE_FOLLOWUP_REFACTOR_QA_MATRIX.md` file are trackable.
- Mark `P00` as `PASS` in `ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md` and leave `P01` through `P08` as `PENDING`.
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
    "docs/ARCHITECTURE_FOLLOWUP_REVIEW_2026-04-01.md",
    "docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_MANIFEST.md",
    "docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md",
]
slugs = [
    "P00_bootstrap",
    "P01_shell_composition_root_collapse",
    "P02_shell_controller_surface_narrowing",
    "P03_qml_bridge_cleanup_finalization",
    "P04_graph_persistence_sidecar_removal",
    "P05_runtime_snapshot_direct_builder",
    "P06_graph_authoring_boundary_collapse",
    "P07_viewer_session_single_authority",
    "P08_verification_docs_closeout",
]
for slug in slugs:
    required.append(
        f"docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_{slug}.md"
    )
    required.append(
        f"docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_{slug}_PROMPT.md"
    )
missing = [path for path in required if not Path(path).exists()]
if missing:
    print("MISSING: " + ", ".join(missing))
    raise SystemExit(1)
for tracked_path in (
    "docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_MANIFEST.md",
    "docs/specs/work_packets/architecture_followup_refactor/P08_verification_docs_closeout_WRAPUP.md",
    "docs/specs/perf/ARCHITECTURE_FOLLOWUP_REFACTOR_QA_MATRIX.md",
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
    "ARCHITECTURE_FOLLOWUP_REFACTOR Work Packet Manifest",
    "ARCHITECTURE_FOLLOWUP_REFACTOR Status Ledger",
):
    if needle not in index_text:
        print("INDEX_MISSING: " + needle)
        raise SystemExit(1)
print("ARCHITECTURE_FOLLOWUP_REFACTOR_P00_FILE_GATE_PASS")
'@ | .\venv\Scripts\python.exe -
```

## Review Gate

```powershell
@'
from pathlib import Path
text = Path(
    "docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md"
).read_text(encoding="utf-8")
if "| P00 Bootstrap | `codex/architecture-followup-refactor/p00-bootstrap` | PASS |" not in text:
    raise SystemExit(1)
print("ARCHITECTURE_FOLLOWUP_REFACTOR_P00_STATUS_PASS")
'@ | .\venv\Scripts\python.exe -
```

## Expected Artifacts

- `.gitignore`
- `docs/ARCHITECTURE_FOLLOWUP_REVIEW_2026-04-01.md`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_MANIFEST.md`
- `docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md`
- `docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_P00_bootstrap.md`
- `docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_P01_shell_composition_root_collapse.md`
- `docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_P01_shell_composition_root_collapse_PROMPT.md`
- `docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_P02_shell_controller_surface_narrowing.md`
- `docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_P02_shell_controller_surface_narrowing_PROMPT.md`
- `docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_P03_qml_bridge_cleanup_finalization.md`
- `docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_P03_qml_bridge_cleanup_finalization_PROMPT.md`
- `docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_P04_graph_persistence_sidecar_removal.md`
- `docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_P04_graph_persistence_sidecar_removal_PROMPT.md`
- `docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_P05_runtime_snapshot_direct_builder.md`
- `docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_P05_runtime_snapshot_direct_builder_PROMPT.md`
- `docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_P06_graph_authoring_boundary_collapse.md`
- `docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_P06_graph_authoring_boundary_collapse_PROMPT.md`
- `docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_P07_viewer_session_single_authority.md`
- `docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_P07_viewer_session_single_authority_PROMPT.md`
- `docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_P08_verification_docs_closeout.md`
- `docs/specs/work_packets/architecture_followup_refactor/ARCHITECTURE_FOLLOWUP_REFACTOR_P08_verification_docs_closeout_PROMPT.md`

## Acceptance Criteria

- The verification command returns `ARCHITECTURE_FOLLOWUP_REFACTOR_P00_FILE_GATE_PASS`.
- The review gate returns `ARCHITECTURE_FOLLOWUP_REFACTOR_P00_STATUS_PASS`.
- `ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `.gitignore`, `docs/ARCHITECTURE_FOLLOWUP_REVIEW_2026-04-01.md`, `docs/specs/INDEX.md`, and the new `architecture_followup_refactor` packet docs.

## Handoff Notes

- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next execution thread begins with `P01`.
