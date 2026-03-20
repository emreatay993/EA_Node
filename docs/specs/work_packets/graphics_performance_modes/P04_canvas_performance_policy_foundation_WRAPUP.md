# P04 Canvas Performance Policy Foundation Wrap-Up

## Implementation Summary

- Packet: `P04`
- Branch Label: `codex/graphics-performance-modes/p04-canvas-performance-policy-foundation`
- Commit Owner: `worker`
- Commit SHA: `e504e0d94abd4207faa8d2cbc18fafb08057a6fd`
- Changed Files: `ea_node_editor/ui_qml/components/GraphCanvas.qml`, `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasPerformancePolicy.js`, `tests/graph_track_b/qml_preference_bindings.py`, `tests/test_passive_graph_surface_host.py`, `docs/specs/work_packets/graphics_performance_modes/P04_canvas_performance_policy_foundation_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/graphics_performance_modes/P04_canvas_performance_policy_foundation_WRAPUP.md`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasPerformancePolicy.js`
- Policy Helper: `graphCanvasPerformancePolicy` in `ea_node_editor/ui_qml/components/GraphCanvas.qml`, backed by `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasPerformancePolicy.js`
- Exported Inputs: resolved `graphics_performance_mode` from `root._canvasStateBridgeRef`, viewport activity from `interactionState.interactionActive`, structural mutation notifications from `scene_nodes_changed` / `scene_edges_changed`, and the shared `150 ms` settle window from `interactionIdleDelayMs`
- Exported Outputs: `resolvedGraphicsPerformanceMode`, `mutationBurstActive`, `transientPerformanceActivityActive`, `transientDegradedWindowActive`, `viewportInteractionWorldCacheActive`, `highQualityRendering`, `gridSimplificationActive`, `minimapSimplificationActive`, `edgeLabelSimplificationActive`, `shadowSimplificationActive`, and `snapshotProxyReuseActive`
- Edge-Layer Cleanup: flow-label delegates stop calling `edgeAtScreen(...)` for the internal `hitTestMatches` probe and now treat visibility as the only needed signal, removing unused per-label hit-test work without changing rendered output

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flow_edge_labels.py --ignore=venv -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py --ignore=venv -k "performance_policy or mutation_burst" -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -k "performance_policy or mutation_burst" -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flow_edge_labels.py --ignore=venv -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: launch the application from this branch with a graph that has at least one edge label and at least one node with a visible shadow.
- Leave the mode on `Full Fidelity`, then pan/zoom the canvas and add or delete a node or edge. Expected result: the canvas still looks the same as before this packet, node shadows stay visible, and the view settles back to the normal idle state after a brief delay.
- Switch to `Max Performance` using the existing status-strip or Graphics Settings control, then add and remove a few nodes or edges quickly. Expected result: there is still no whole-canvas simplification in this packet, but the canvas remains responsive and returns to the same idle fidelity after the short settle window.
- Click a visible flow edge label and open its context menu if applicable. Expected result: edge selection and label visibility still behave normally even though the label delegate no longer performs the old internal hit-test probe.

## Residual Risks

- `P04` centralizes the policy state and mutation-burst timing, but it intentionally leaves the future-facing simplification outputs inactive. `P05` still needs to consume `transientDegradedWindowActive` for actual max-performance canvas behavior.
- Structural mutation bursts are keyed off the scene bridge node/edge change signals. If a later mutation path bypasses those signals, it will also bypass the centralized burst timer until that path is routed through the same scene notifications.
- The `hitTestMatches` property is now only a visibility-aligned internal probe for tests. Any later packet that tries to reuse it as a real geometric hit-test signal will need to introduce a separate explicit contract instead of relying on the old incidental behavior.

## Ready for Integration

- Yes: `P04` adds one centralized canvas policy owner, reuses the existing 150 ms settle window for structural mutation bursts, keeps `Full Fidelity` visually unchanged, and passes the packet verification suite plus the review gate.
