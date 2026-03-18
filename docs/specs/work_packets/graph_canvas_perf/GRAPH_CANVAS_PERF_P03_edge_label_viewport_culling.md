# GRAPH_CANVAS_PERF P03: Edge/Label Viewport Culling

## Objective
- Reduce pan/zoom render cost by skipping offscreen edge and flow-label work that cannot contribute to the visible frame.

## Preconditions
- `P00`, `P01`, and `P02` are marked `PASS` in [GRAPH_CANVAS_PERF_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_STATUS.md).
- No later `GRAPH_CANVAS_PERF` packet is in progress.

## Execution Dependencies
- `P02`

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- existing view-state payloads used to determine the visible scene region
- tracked edge/canvas regression coverage

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/viewport_bridge.py`
- `tests/test_flow_edge_labels.py`
- `tests/test_graph_track_b.py`

## Required Behavior
- Add visible-scene or visible-screen culling so edge stroke and flow-label work is skipped when routed geometry is fully outside the viewport, with a conservative safety margin.
- Avoid computing flow-label anchors, label pills, and related hit-test work for edges that have already been culled as offscreen.
- Preserve selection, preview, drag-connection feedback, and label appearance for visible edges across the supported zoom range.
- Reuse the existing view payload path where practical instead of introducing a second camera-state contract just for culling.
- Keep edge routing semantics, flow-label styling, and multi-input connection behavior unchanged.

## Non-Goals
- No node-world interaction caching yet. `P04` owns that.
- No docs or traceability updates yet. `P05` owns that.
- No reroute or style redesign work.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flow_edge_labels.py -k "graph_canvas_flow_edge_labels_render_and_reduce_at_low_zoom" -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_track_b.py -k "viewport_applies_zoom_and_center_updates" -q`
3. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 80 --edges 220 --load-iterations 1 --interaction-samples 8 --baseline-runs 1 --report-dir artifacts/graph_canvas_perf_p03`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flow_edge_labels.py -k "graph_canvas_flow_edge_labels_render_and_reduce_at_low_zoom" -q`

## Expected Artifacts
- `docs/specs/work_packets/graph_canvas_perf/P03_edge_label_viewport_culling_WRAPUP.md`

## Acceptance Criteria
- Visible flow-label regression coverage still passes after culling is introduced.
- The small-sample benchmark smoke run completes successfully after the culling change.
- Offscreen work is skipped conservatively and documented in the wrap-up, including any viewport margin used.
- No visible edge, label, or connection interaction behavior is intentionally changed.

## Handoff Notes
- Record the culling margin and whether it is scene-space or screen-space so `P04` can keep cache behavior aligned with it.
- If a fallback path is needed for drag-preview or selected-edge visibility, keep it explicit and document it in residual risks.
