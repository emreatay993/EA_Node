# P05 Max Performance Canvas Behavior Wrap-Up

## Implementation Summary

- Packet: `P05`
- Branch Label: `codex/graphics-performance-modes/p05-max-performance-canvas-behavior`
- Commit Owner: `worker`
- Commit SHA: `ed37eb8`
- Changed Files: `ea_node_editor/ui_qml/components/GraphCanvas.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasBackground.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasMinimapOverlay.qml`, `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`, `tests/graph_track_b/qml_preference_bindings.py`, `tests/test_passive_graph_surface_host.py`, `tests/test_flow_edge_labels.py`, `docs/specs/work_packets/graphics_performance_modes/P05_max_performance_canvas_behavior_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/graphics_performance_modes/P05_max_performance_canvas_behavior_WRAPUP.md`
- Degraded-Window Canvas Policy: `GraphCanvas.qml` now converts `transientDegradedWindowActive` into active `gridSimplificationActive`, `minimapSimplificationActive`, `edgeLabelSimplificationActive`, `shadowSimplificationActive`, and `snapshotProxyReuseActive` flags only while `max_performance` is inside the shared 150 ms interaction or mutation-burst window.
- Visible Max-Performance Behavior: the background grid drops out, the minimap viewport pauses, flow edge labels hide, node shadows are suppressed, and node hosts reuse their texture-cache path during the degraded window; idle recovery restores the normal visuals automatically after the shared settle timer expires.
- Full-Fidelity Safeguard: `full_fidelity` keeps the earlier invisible `P04` policy wiring but does not opt into the new visual degradations during viewport activity or structural mutation bursts.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py --ignore=venv -k "max_performance" -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -k "max_performance" -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flow_edge_labels.py --ignore=venv -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py --ignore=venv -k "max_performance" -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: launch this branch with a graph that shows the grid, has the minimap enabled, contains at least one node with a visible shadow, and includes a flow edge with a label.
- Leave the mode on `Full Fidelity`, then pan or wheel-zoom and add or remove a node. Expected result: the grid, minimap viewport, flow edge label, and node shadow stay visible throughout the interaction, and the canvas looks unchanged from the pre-`P05` idle presentation.
- Switch to `Max Performance`, then pan or wheel-zoom the canvas. Expected result: while the view is actively moving, flow edge labels hide, node shadows disappear, the grid drops out, the minimap viewport pauses, and the canvas returns to full idle fidelity automatically about 150 ms after motion stops.
- Stay on `Max Performance`, then add or delete nodes or edges quickly. Expected result: the same temporary degraded-window behavior appears during the mutation burst, node surfaces continue to render from the cache-backed host path, and the normal idle visuals restore automatically once the shared settle timer expires.

## Residual Risks

- The `P05` degraded window currently prefers the strongest simplification path: flow labels hide completely and the minimap viewport pauses instead of using a lighter-weight frozen preview. If desktop UX review wants a softer presentation, that tuning remains a packet-local follow-up rather than a contract gap.
- Snapshot reuse in `P05` rides the existing node-host texture layer. That covers standard host chrome today, but later packets still need the dedicated heavy-surface proxy path for richer media nodes that outgrow the generic host cache.

## Ready for Integration

- Yes: `P05` applies the required max-performance degraded-window behavior for pan/zoom and mutation bursts, preserves `full_fidelity`, restores idle visuals automatically, and passes the packet verification suite plus the review gate.
