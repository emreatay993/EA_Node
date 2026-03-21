# GRAPH_CANVAS_INTERACTION_PERF P00: Bootstrap

## Objective
- Establish the `GRAPH_CANVAS_INTERACTION_PERF` packet set, initialize the status ledger, and register the packet docs in the canonical spec index.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md).
- No `graph_canvas_interaction_perf` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies
- none

## Target Subsystems
- `.gitignore` only for the narrow exception needed to make the new packet docs trackable
- `docs/specs/work_packets/graph_canvas_interaction_perf/*`
- `docs/specs/INDEX.md`

## Conservative Write Scope
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/graph_canvas_interaction_perf/**`

## Required Behavior
- Create `docs/specs/work_packets/graph_canvas_interaction_perf/`.
- Add `GRAPH_CANVAS_INTERACTION_PERF_MANIFEST.md` and `GRAPH_CANVAS_INTERACTION_PERF_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P09` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `GRAPH_CANVAS_INTERACTION_PERF` manifest and status ledger.
- Add the narrow `.gitignore` exception required so the new packet docs are not ignored by git.
- Mark `P00` as `PASS` in `GRAPH_CANVAS_INTERACTION_PERF_STATUS.md` and leave `P01` through `P09` as `PENDING`.
- Keep the packet order, branch labels, sequential execution waves, locked defaults, review-gate structure, wrap-up expectations, and executor-ready worker split aligned with this approved packet roadmap.
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

root = Path(".")
packet_dir = root / "docs/specs/work_packets/graph_canvas_interaction_perf"
packets = [
    ("P00", "bootstrap"),
    ("P01", "perf_harness_baseline_hardening"),
    ("P02", "atomic_viewport_state_updates"),
    ("P03", "view_state_redraw_flush"),
    ("P04", "scene_space_edge_paint_path"),
    ("P05", "visible_edge_snapshot_label_model"),
    ("P06", "viewport_aware_node_activation"),
    ("P07", "node_chrome_shadow_cache"),
    ("P08", "auxiliary_canvas_stabilization"),
    ("P09", "evidence_refresh_traceability"),
]
required = [
    packet_dir / "GRAPH_CANVAS_INTERACTION_PERF_MANIFEST.md",
    packet_dir / "GRAPH_CANVAS_INTERACTION_PERF_STATUS.md",
]
required += [packet_dir / f"GRAPH_CANVAS_INTERACTION_PERF_{code}_{slug}.md" for code, slug in packets]
required += [packet_dir / f"GRAPH_CANVAS_INTERACTION_PERF_{code}_{slug}_PROMPT.md" for code, slug in packets]
missing = [str(path) for path in required if not path.exists()]
status_text = (packet_dir / "GRAPH_CANVAS_INTERACTION_PERF_STATUS.md").read_text(encoding="utf-8")
expectations = [
    ("P00 Bootstrap", "PASS"),
    ("P01 Perf Harness Baseline Hardening", "PENDING"),
    ("P02 Atomic Viewport State Updates", "PENDING"),
    ("P03 View-State Redraw Flush", "PENDING"),
    ("P04 Scene-Space Edge Paint Path", "PENDING"),
    ("P05 Visible-Edge Snapshot And Label Model", "PENDING"),
    ("P06 Viewport-Aware Node Activation", "PENDING"),
    ("P07 Node Chrome And Shadow Cache", "PENDING"),
    ("P08 Auxiliary Canvas Stabilization", "PENDING"),
    ("P09 Evidence Refresh And Traceability", "PENDING"),
]
bad_status = [
    f"{label}:{expected}"
    for label, expected in expectations
    if f"| {label} |" not in status_text
    or f"| {expected} |" not in next((line for line in status_text.splitlines() if f"| {label} |" in line), "")
]
index_text = (root / "docs/specs/INDEX.md").read_text(encoding="utf-8")
missing_refs = [
    ref
    for ref in (
        "GRAPH_CANVAS_INTERACTION_PERF Work Packet Manifest",
        "GRAPH_CANVAS_INTERACTION_PERF Status Ledger",
    )
    if ref not in index_text
]
ignored = subprocess.run(
    ["git", "check-ignore", str(packet_dir / "GRAPH_CANVAS_INTERACTION_PERF_MANIFEST.md")],
    capture_output=True,
    text=True,
)
if missing:
    print("MISSING: " + ", ".join(missing))
    raise SystemExit(1)
if bad_status:
    print("STATUS_MISMATCH: " + ", ".join(bad_status))
    raise SystemExit(1)
if missing_refs:
    print("INDEX_MISSING: " + ", ".join(missing_refs))
    raise SystemExit(1)
if ignored.returncode == 0:
    print("GRAPH_CANVAS_INTERACTION_PERF_DOCS_IGNORED")
    raise SystemExit(1)
print("GRAPH_CANVAS_INTERACTION_PERF_P00_FILE_GATE_PASS")
PY`

## Review Gate
- `./venv/Scripts/python.exe - <<'PY'
from pathlib import Path
text = Path("docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_STATUS.md").read_text(encoding="utf-8")
if "| P00 Bootstrap | `codex/graph-canvas-interaction-perf/p00-bootstrap` | PASS |" not in text:
    raise SystemExit(1)
print("GRAPH_CANVAS_INTERACTION_PERF_P00_STATUS_PASS")
PY`

## Expected Artifacts
- `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_MANIFEST.md`
- `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_STATUS.md`
- `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P00_bootstrap.md`
- `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P00_bootstrap_PROMPT.md`
- `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P01_perf_harness_baseline_hardening.md`
- `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P01_perf_harness_baseline_hardening_PROMPT.md`
- `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P02_atomic_viewport_state_updates.md`
- `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P02_atomic_viewport_state_updates_PROMPT.md`
- `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P03_view_state_redraw_flush.md`
- `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P03_view_state_redraw_flush_PROMPT.md`
- `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P04_scene_space_edge_paint_path.md`
- `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P04_scene_space_edge_paint_path_PROMPT.md`
- `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P05_visible_edge_snapshot_label_model.md`
- `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P05_visible_edge_snapshot_label_model_PROMPT.md`
- `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P06_viewport_aware_node_activation.md`
- `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P06_viewport_aware_node_activation_PROMPT.md`
- `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P07_node_chrome_shadow_cache.md`
- `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P07_node_chrome_shadow_cache_PROMPT.md`
- `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P08_auxiliary_canvas_stabilization.md`
- `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P08_auxiliary_canvas_stabilization_PROMPT.md`
- `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P09_evidence_refresh_traceability.md`
- `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_P09_evidence_refresh_traceability_PROMPT.md`

## Acceptance Criteria
- The verification command returns `GRAPH_CANVAS_INTERACTION_PERF_P00_FILE_GATE_PASS`.
- The review gate returns `GRAPH_CANVAS_INTERACTION_PERF_P00_STATUS_PASS`.
- `GRAPH_CANVAS_INTERACTION_PERF_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `.gitignore`, `docs/specs/INDEX.md`, and the new `graph_canvas_interaction_perf` packet docs.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next thread must start `P01`; this packet set is intentionally sequential and each implementation packet is intended for a separate worker subagent.
