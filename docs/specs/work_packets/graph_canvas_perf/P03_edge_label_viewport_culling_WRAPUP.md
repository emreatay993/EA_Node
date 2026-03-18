# P03 Edge/Label Viewport Culling Wrap-Up

## Implementation Summary

- Packet: `P03`
- Branch Label: `codex/graph-canvas-perf/p03-edge-label-viewport-culling`
- Commit Owner: `worker`
- Commit SHA: `00cd2e5`
- Changed Files: `ea_node_editor/ui_qml/components/GraphCanvas.qml`, `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`, `tests/test_flow_edge_labels.py`, `tests/test_graph_track_b.py`
- Artifacts Produced: `docs/specs/work_packets/graph_canvas_perf/P03_edge_label_viewport_culling_WRAPUP.md`, `artifacts/graph_canvas_perf_p03/TRACK_H_BENCHMARK_REPORT.md`, `artifacts/graph_canvas_perf_p03/track_h_benchmark_report.json`

Edge paint and flow-label evaluation now reuse the existing visible-scene payload from `ViewportBridge` and cull fully offscreen routed geometry against a `96px` screen-space safety margin converted to scene-space at the current zoom. Drag-preview rendering stays unculled so connection feedback remains visible while interactive edge strokes, flow labels, and edge hit-testing skip work for edges whose routed bounds cannot reach the current frame.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flow_edge_labels.py -k "graph_canvas_flow_edge_labels_render_and_reduce_at_low_zoom" -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_track_b.py -k "viewport_applies_zoom_and_center_updates" -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 80 --edges 220 --load-iterations 1 --interaction-samples 8 --baseline-runs 1 --report-dir artifacts/graph_canvas_perf_p03`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flow_edge_labels.py -k "graph_canvas_flow_edge_labels_render_and_reduce_at_low_zoom" -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: open a graph with visible flow edges and another cluster of connected nodes several screens away.
- Action: pan across the canvas until the first cluster leaves the viewport and the distant cluster enters it.
- Expected result: only the in-viewport cluster shows flow labels and edge strokes; offscreen labels disappear without changing visible edge styling.
- Action: keep a visible flow edge on screen and zoom from about `1.0` down through `0.7` and `0.5`.
- Expected result: the label stays as a pill at higher zoom, simplifies to text near the mid threshold, and hides at low zoom exactly as before.
- Action: start a drag connection or select a visible edge, then pan and zoom while that interaction remains active.
- Expected result: drag-preview feedback, selected-edge styling, and visible edge hit behavior remain unchanged.

## Residual Risks

- Culling relies on control-point and polyline bounds expanded by a `96px` screen-space margin, so future routing changes that place visible stroke outside those conservative bounds would need the margin or bounds logic revisited.
- Offscreen edges are skipped during edge hit-testing as well as paint and label work; that matches viewport-local pointer interaction today, but any future non-pointer edge query path should stay aligned with the same culling rules.

## Ready for Integration

- Yes: the packet keeps visible canvas behavior intact while skipping fully offscreen edge and flow-label work through the existing viewport payload path.
