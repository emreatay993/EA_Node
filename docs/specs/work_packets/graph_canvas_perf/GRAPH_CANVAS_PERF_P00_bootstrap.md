# GRAPH_CANVAS_PERF P00: Bootstrap

## Objective
- Establish the `GRAPH_CANVAS_PERF` packet set, initialize the status ledger, and register the packet docs in the canonical spec index.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md).
- No `graph_canvas_perf` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies
- none

## Target Subsystems
- `.gitignore` only for a narrow exception needed to make the new packet docs trackable
- `docs/specs/work_packets/graph_canvas_perf/*`
- `docs/specs/INDEX.md`

## Conservative Write Scope
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/graph_canvas_perf/**`

## Required Behavior
- Create `docs/specs/work_packets/graph_canvas_perf/`.
- Add `GRAPH_CANVAS_PERF_MANIFEST.md` and `GRAPH_CANVAS_PERF_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P05` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `GRAPH_CANVAS_PERF` manifest and status ledger.
- Add the narrow `.gitignore` exception required so the new packet docs are not ignored by git.
- Mark `P00` as `PASS` in `GRAPH_CANVAS_PERF_STATUS.md` and leave `P01` through `P05` as `PENDING`.
- Keep the packet order, branch labels, sequential execution waves, locked defaults, review-gate structure, and wrap-up expectations aligned with this approved packet roadmap.
- Make no runtime, script, test, or requirement-doc changes outside the documentation bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes under `scripts/**`.
- No changes to requirements, perf evidence docs, traceability docs, or `README.md` in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe - <<'PY'
from pathlib import Path
import subprocess

required = [
    "docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_MANIFEST.md",
    "docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_STATUS.md",
    "docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P00_bootstrap.md",
    "docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P00_bootstrap_PROMPT.md",
    "docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P01_real_canvas_benchmark_baseline.md",
    "docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P01_real_canvas_benchmark_baseline_PROMPT.md",
    "docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P02_view_state_redraw_coalescing.md",
    "docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P02_view_state_redraw_coalescing_PROMPT.md",
    "docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P03_edge_label_viewport_culling.md",
    "docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P03_edge_label_viewport_culling_PROMPT.md",
    "docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P04_viewport_interaction_world_cache.md",
    "docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P04_viewport_interaction_world_cache_PROMPT.md",
    "docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P05_perf_docs_traceability.md",
    "docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P05_perf_docs_traceability_PROMPT.md",
]
missing = [path for path in required if not Path(path).exists()]
if missing:
    print("MISSING: " + ", ".join(missing))
    raise SystemExit(1)
check = subprocess.run(
    ["git", "check-ignore", "docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_MANIFEST.md"],
    capture_output=True,
    text=True,
)
if check.returncode == 0:
    print("GRAPH_CANVAS_PERF_DOCS_IGNORED")
    raise SystemExit(1)
index_text = Path("docs/specs/INDEX.md").read_text(encoding="utf-8")
for needle in (
    "GRAPH_CANVAS_PERF Work Packet Manifest",
    "GRAPH_CANVAS_PERF Status Ledger",
):
    if needle not in index_text:
        print("INDEX_MISSING: " + needle)
        raise SystemExit(1)
print("GRAPH_CANVAS_PERF_P00_FILE_GATE_PASS")
PY`

## Review Gate
- `./venv/Scripts/python.exe - <<'PY'
from pathlib import Path
text = Path("docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_STATUS.md").read_text(encoding="utf-8")
if "| P00 Bootstrap | `codex/graph-canvas-perf/p00-bootstrap` | PASS |" not in text:
    raise SystemExit(1)
print("GRAPH_CANVAS_PERF_P00_STATUS_PASS")
PY`

## Expected Artifacts
- `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_MANIFEST.md`
- `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_STATUS.md`
- `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P00_bootstrap.md`
- `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P01_real_canvas_benchmark_baseline.md`
- `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P01_real_canvas_benchmark_baseline_PROMPT.md`
- `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P02_view_state_redraw_coalescing.md`
- `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P02_view_state_redraw_coalescing_PROMPT.md`
- `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P03_edge_label_viewport_culling.md`
- `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P03_edge_label_viewport_culling_PROMPT.md`
- `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P04_viewport_interaction_world_cache.md`
- `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P04_viewport_interaction_world_cache_PROMPT.md`
- `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P05_perf_docs_traceability.md`
- `docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_P05_perf_docs_traceability_PROMPT.md`

## Acceptance Criteria
- The first verification command returns `GRAPH_CANVAS_PERF_P00_FILE_GATE_PASS`.
- The review gate returns `GRAPH_CANVAS_PERF_P00_STATUS_PASS`.
- `GRAPH_CANVAS_PERF_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `.gitignore`, `docs/specs/INDEX.md`, and the new `graph_canvas_perf` packet docs.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next thread must start `P01`; this packet set is intentionally sequential.
