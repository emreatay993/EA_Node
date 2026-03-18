# GRAPH_CANVAS_PERF P02: View-State Redraw Coalescing

## Objective
- Remove duplicate pan/zoom redraw scheduling so one logical viewport update triggers one coordinated background/edge invalidation path instead of several overlapping ones.

## Preconditions
- `P00` and `P01` are marked `PASS` in [GRAPH_CANVAS_PERF_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_STATUS.md).
- No later `GRAPH_CANVAS_PERF` packet is in progress.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasBackground.qml`
- targeted canvas regression coverage in tracked tests

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasBackground.qml`
- `ea_node_editor/ui_qml/viewport_bridge.py`
- `tests/test_graph_track_b.py`
- `tests/test_passive_graph_surface_host.py`

## Required Behavior
- Make one canvas-owned path responsible for pan/zoom-triggered redraw scheduling, or otherwise coalesce the current overlapping listeners so duplicate invalidation requests are removed.
- Preserve `ViewportBridge` public properties/signals for other consumers unless a private batching helper is clearly safer and does not widen the external contract.
- Keep background grid placement, edge geometry, minimap behavior, and wheel zoom interaction visually unchanged.
- Add or update deterministic regression coverage that locks in the new invalidation ownership and keeps future packets from reintroducing duplicate view listeners.
- Keep the canvas responsive to every committed viewport change; do not introduce frame skipping that leaves visible state stale.

## Non-Goals
- No viewport culling yet. `P03` owns that.
- No node-world interaction caching yet. `P04` owns that.
- No docs updates yet. `P05` owns that.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_track_b.py -k "viewport_applies_zoom_and_center_updates" -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py -k "graph_canvas_temporarily_simplifies_node_shadow_during_wheel_zoom" -q`
3. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 80 --edges 220 --load-iterations 1 --interaction-samples 8 --baseline-runs 1 --report-dir artifacts/graph_canvas_perf_p02`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 50 --edges 120 --load-iterations 1 --interaction-samples 4 --baseline-runs 1 --report-dir artifacts/graph_canvas_perf_p02_review`

## Expected Artifacts
- `docs/specs/work_packets/graph_canvas_perf/P02_view_state_redraw_coalescing_WRAPUP.md`

## Acceptance Criteria
- The targeted pan/zoom regression tests pass.
- The small-sample benchmark smoke run completes successfully after the redraw ownership change.
- Duplicate view-driven invalidation wiring is removed or coalesced and documented in the wrap-up with the final owner path.
- No current canvas object names, public methods, or visual behaviors are intentionally changed.

## Handoff Notes
- Record the final redraw-owner decision in the wrap-up so `P03` and `P04` do not reintroduce overlapping listeners.
- If a tiny helper is added to `ViewportBridge`, keep it internal and note the reason in residual risks.
