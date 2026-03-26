# ARCHITECTURE_REFACTOR P00: Bootstrap

## Objective
- Establish the `ARCHITECTURE_REFACTOR` packet set, initialize the status ledger, register the packet docs in the canonical spec index, and ensure the new packet directory plus future wrap-ups and QA matrix are trackable.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md).
- No `architecture_refactor` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies
- none

## Target Subsystems
- `docs/specs/work_packets/architecture_refactor/*`
- `docs/specs/INDEX.md`
- `.gitignore`

## Conservative Write Scope
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/architecture_refactor/**`

## Required Behavior
- Create `docs/specs/work_packets/architecture_refactor/`.
- Add `ARCHITECTURE_REFACTOR_MANIFEST.md` and `ARCHITECTURE_REFACTOR_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P13` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `ARCHITECTURE_REFACTOR` manifest and status ledger.
- Update `.gitignore` so the new packet docs, future packet wrap-ups, and future `docs/specs/perf/ARCHITECTURE_REFACTOR_QA_MATRIX.md` file are trackable.
- Mark `P00` as `PASS` in `ARCHITECTURE_REFACTOR_STATUS.md` and leave `P01` through `P13` as `PENDING`.
- Keep packet order, branch labels, locked defaults, execution waves, review-gate structure, and wrap-up expectations aligned with the architecture-audit-derived refactor plan.
- Make no runtime, product-source, test, packaging-script, or requirement-doc changes outside the documentation bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes under `scripts/**`.
- No changes to `ARCHITECTURE.md`, `docs/PACKAGING_WINDOWS.md`, `docs/PILOT_RUNBOOK.md`, or `docs/specs/requirements/**` in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe - <<'PY'
from pathlib import Path
import subprocess

slugs = [
    "P00_bootstrap",
    "P01_shell_host_composition",
    "P02_workspace_library_surface",
    "P03_project_session_service",
    "P04_graph_boundary_adapters",
    "P05_graph_invariant_kernel",
    "P06_persistence_invariant_adoption",
    "P07_runtime_snapshot_context",
    "P08_worker_protocol_split",
    "P09_dpf_runtime_package",
    "P10_dpf_node_viewer_split",
    "P11_shell_qml_bridge_retirement",
    "P12_graph_canvas_scene_decomposition",
    "P13_docs_release_traceability",
]
required = [
    "docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_MANIFEST.md",
    "docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_STATUS.md",
]
for slug in slugs:
    required.append(f"docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_{slug}.md")
    required.append(f"docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_{slug}_PROMPT.md")
missing = [path for path in required if not Path(path).exists()]
if missing:
    print("MISSING: " + ", ".join(missing))
    raise SystemExit(1)
for tracked_path in (
    "docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_MANIFEST.md",
    "docs/specs/work_packets/architecture_refactor/P12_graph_canvas_scene_decomposition_WRAPUP.md",
    "docs/specs/perf/ARCHITECTURE_REFACTOR_QA_MATRIX.md",
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
    "ARCHITECTURE_REFACTOR Work Packet Manifest",
    "ARCHITECTURE_REFACTOR Status Ledger",
):
    if needle not in index_text:
        print("INDEX_MISSING: " + needle)
        raise SystemExit(1)
print("ARCHITECTURE_REFACTOR_P00_FILE_GATE_PASS")
PY`

## Review Gate
- `./venv/Scripts/python.exe - <<'PY'
from pathlib import Path
text = Path("docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_STATUS.md").read_text(encoding="utf-8")
if "| P00 Bootstrap | `codex/architecture-refactor/p00-bootstrap` | PASS |" not in text:
    raise SystemExit(1)
print("ARCHITECTURE_REFACTOR_P00_STATUS_PASS")
PY`

## Expected Artifacts
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_MANIFEST.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_STATUS.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P00_bootstrap.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P01_shell_host_composition.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P01_shell_host_composition_PROMPT.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P02_workspace_library_surface.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P02_workspace_library_surface_PROMPT.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P03_project_session_service.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P03_project_session_service_PROMPT.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P04_graph_boundary_adapters.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P04_graph_boundary_adapters_PROMPT.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P05_graph_invariant_kernel.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P05_graph_invariant_kernel_PROMPT.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P06_persistence_invariant_adoption.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P06_persistence_invariant_adoption_PROMPT.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P07_runtime_snapshot_context.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P07_runtime_snapshot_context_PROMPT.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P08_worker_protocol_split.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P08_worker_protocol_split_PROMPT.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P09_dpf_runtime_package.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P09_dpf_runtime_package_PROMPT.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P10_dpf_node_viewer_split.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P10_dpf_node_viewer_split_PROMPT.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P11_shell_qml_bridge_retirement.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P11_shell_qml_bridge_retirement_PROMPT.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P12_graph_canvas_scene_decomposition.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P12_graph_canvas_scene_decomposition_PROMPT.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P13_docs_release_traceability.md`
- `docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_P13_docs_release_traceability_PROMPT.md`

## Acceptance Criteria
- The verification command returns `ARCHITECTURE_REFACTOR_P00_FILE_GATE_PASS`.
- The review gate returns `ARCHITECTURE_REFACTOR_P00_STATUS_PASS`.
- `ARCHITECTURE_REFACTOR_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `.gitignore`, `docs/specs/INDEX.md`, and the new `architecture_refactor` packet docs.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next execution thread begins with `P01`.
