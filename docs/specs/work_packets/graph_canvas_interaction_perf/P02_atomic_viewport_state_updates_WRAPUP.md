# P02 Atomic Viewport State Updates Wrap-Up

## Implementation Summary

- Packet: `P02`
- Branch Label: `codex/graph-canvas-interaction-perf/p02-atomic-viewport-state-updates`
- Commit Owner: `worker`
- Commit SHA: `68fd586af03a4a64fcc123ba3c18e623b09524c5`
- Changed Files: `ea_node_editor/ui_qml/components/GraphCanvas.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeResizeHandle.qml`, `ea_node_editor/ui_qml/graph_canvas_bridge.py`, `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`, `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`, `ea_node_editor/ui_qml/viewport_bridge.py`, `tests/graph_track_b/qml_preference_bindings.py`, `tests/graph_track_b/viewport.py`, `docs/specs/work_packets/graph_canvas_interaction_perf/P02_atomic_viewport_state_updates_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/graph_canvas_interaction_perf/P02_atomic_viewport_state_updates_WRAPUP.md`

Implemented an additive `ViewportBridge.set_view_state(...)` seam plus anchored wheel zoom support so one wheel step now commits one logical `view_state_changed` update while preserving the existing zoom/pan helper slots for compatibility callers. The bridge layer now exposes the raw `ViewportBridge` object to QML, `ViewportBridge` caches its visible-scene-rect payload, and `GraphCanvas.qml` binds the hot canvas path to that raw viewport state instead of the coarse `GraphCanvasStateBridge` wrapper while keeping the wrapper surface available for non-hot callers.

`GraphCanvas.qml` now routes wheel zoom through `adjust_zoom_at_viewport_point(...)` when available, falling back to the legacy two-step path only for older command surfaces. Normal node delegates no longer receive per-node zoom fan-out; resize math reads the viewport zoom only where the resize handle actually needs it.

## Verification

- PASS: `./venv/Scripts/python.exe -m pytest tests/graph_track_b/viewport.py --ignore=venv -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py --ignore=venv -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_contract.py --ignore=venv -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -k "wheel_zoom" -q`
- PASS: `./venv/Scripts/python.exe -m pytest tests/main_window_shell/bridge_contracts.py -k "GraphCanvasBridgeTests or MainWindowGraphCanvasBridgeTests" --ignore=venv -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

1. Open a graph with several visible nodes and edges.
2. Hover an off-center point on the canvas, then zoom in and out with the mouse wheel.
3. Confirm the scene point under the cursor stays anchored and the canvas no longer performs an extra visible pan after each wheel step.
4. Hover a node to reveal resize handles, resize the node after zooming, and confirm the handle tracks the cursor correctly.
5. Confirm the grid, minimap viewport, and edge visuals still update with the same full-fidelity appearance during normal wheel zoom.

## Residual Risks

- `P03` still owns redraw-flush coalescing, so grid and edge repaint scheduling can still do more work than necessary even though the viewport mutation itself is now atomic.
- Split-bridge callers that do not expose the new raw `viewport_bridge` property will keep using the compatibility wrapper path for reads.
- The cached visible-scene-rect seam reduces repeated recomputation and wrapper copies, but it does not yet address downstream redraw batching or edge paint hot-loop costs.

## Ready for Integration

- Yes: Required packet verification passed, the wheel path now commits one anchored viewport update, and the remaining redraw-coalescing work is explicitly deferred to `P03`.
