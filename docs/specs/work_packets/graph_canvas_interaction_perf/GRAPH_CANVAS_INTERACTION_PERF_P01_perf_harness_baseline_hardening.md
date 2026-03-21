# GRAPH_CANVAS_INTERACTION_PERF P01: Perf Harness Baseline Hardening

## Objective
- Harden the graph-canvas performance harness so later runtime packets are judged against stable steady-state pan, zoom, and node-drag evidence taken from the real `GraphCanvas.qml` path.

## Preconditions
- `P00` is marked `PASS` in `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_STATUS.md`.
- No later `GRAPH_CANVAS_INTERACTION_PERF` packet is in progress.

## Execution Dependencies
- `P00`

## Target Subsystems
- `ea_node_editor/ui/perf/performance_harness.py`
- `ea_node_editor/telemetry/performance_harness.py`
- `tests/test_track_h_perf_harness.py`

## Conservative Write Scope
- `ea_node_editor/ui/perf/performance_harness.py`
- `ea_node_editor/telemetry/performance_harness.py`
- `tests/test_track_h_perf_harness.py`
- `docs/specs/work_packets/graph_canvas_interaction_perf/P01_perf_harness_baseline_hardening_WRAPUP.md`

## Required Behavior
- Keep the current harness CLI backward-compatible unless an additive flag or field is clearly safer.
- Separate warmup/setup effects from steady-state interaction sampling so pan/zoom measurements do not keep recreating the canvas host between samples.
- Reuse one real canvas host after warmup for steady-state interaction sampling and keep the real `GraphCanvas.qml` render path explicit in the recorded evidence.
- Record phase timing slices that let later packets distinguish load/setup, warmup, pan, zoom, and node-drag control costs.
- Add a node-drag control metric alongside pan/zoom metrics so the regression target remains "pan/zoom should converge toward drag smoothness."
- Store separate pan and zoom variance series instead of only a combined interaction variance, while preserving any existing combined summary that downstream docs/tests still rely on.
- Keep development-time report output under packet-specific `artifacts/` directories. Do not refresh checked-in perf docs or canonical evidence in this packet.
- Update deterministic harness tests to cover the new phase/variance/control fields without broadening the packet beyond the harness seam.

## Non-Goals
- No viewport, edge, node, grid, minimap, or QML runtime optimizations yet.
- No changes to checked-in requirement, perf, or traceability docs.
- No new user-facing settings or performance modes.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_track_h_perf_harness.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 80 --edges 220 --load-iterations 1 --interaction-samples 6 --baseline-runs 1 --performance-mode full_fidelity --scenario synthetic_exec --report-dir artifacts/graph_canvas_interaction_perf_p01`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_track_h_perf_harness.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/graph_canvas_interaction_perf/P01_perf_harness_baseline_hardening_WRAPUP.md`

## Acceptance Criteria
- Steady-state interaction samples reuse a warmed real canvas host instead of paying repeated host recreation cost.
- Harness output records distinct phase timing and distinct pan, zoom, and node-drag control series.
- Focused harness regression tests pass from the project venv.
- No checked-in perf evidence is refreshed in this packet.

## Handoff Notes
- Record the new report fields and any additive CLI flags in the wrap-up so later packets and `P09` can consume the same evidence schema.
- If a legacy field must remain for compatibility, document which new fields supersede it and which downstream readers still depend on it.
