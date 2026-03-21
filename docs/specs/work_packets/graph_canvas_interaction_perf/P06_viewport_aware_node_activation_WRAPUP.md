# P06 Viewport-Aware Node Activation Wrap-Up

## Implementation Summary

- Packet: `P06`
- Branch Label: `codex/graph-canvas-interaction-perf/p06-viewport-aware-node-activation`
- Commit Owner: `worker`
- Commit SHA: `851dc6d94ef58c0a264abe2858d0e86ebc0f8d1f`
- Changed Files: `ea_node_editor/ui_qml/components/GraphCanvas.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`, `tests/test_graph_surface_input_contract.py`, `tests/test_passive_graph_surface_host.py`, `docs/specs/work_packets/graph_canvas_interaction_perf/P06_viewport_aware_node_activation_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/graph_canvas_interaction_perf/P06_viewport_aware_node_activation_WRAPUP.md`, `ea_node_editor/ui_qml/components/GraphCanvas.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`, `tests/test_graph_surface_input_contract.py`, `tests/test_passive_graph_surface_host.py`
- Behavior Notes: `renderActive` now uses a padded visible-scene-rect gate that inflates the viewport by `240` viewport pixels converted into scene units at the current zoom.
- Force-Active Conditions: node surfaces stay active when the node is selected, hovered, previewed, pending-connection, context-targeted, drag-source/pending wire source, live-dragged, or resized.
- Scope Notes: node delegates remain instantiated; only the heavy surface loader subtree deactivates offscreen.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_contract.py --ignore=venv -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

1. Open a graph with nodes spread beyond the current viewport and pan toward a node that starts just outside the visible edge.
Expected result: the node surface is already active as it approaches the viewport because the activation seam uses a padded visible-scene-rect, with no placeholder or visible quality drop.
2. Keep a node offscreen, then select it or target it with a pending wire/preview/context action.
Expected result: the node surface stays active while the selected, previewed, pending-connection, or context-targeted state is present.
3. Drag or resize a node near the viewport boundary.
Expected result: the surface remains active throughout the interaction and the node keeps its existing drag, resize, and surface-control behavior.

## Residual Risks

- The padding heuristic is fixed at `240` viewport pixels per side, so extremely zoomed-out views may keep more nearby offscreen surfaces active than the minimum possible in exchange for avoiding edge-thrash when panning.
- Future packets that add new node interaction states must preserve the force-active seam so offscreen deactivation does not interrupt interaction-critical surfaces.

## Ready for Integration

- Yes: the packet stays inside the allowed scope, preserves node delegate presence, records the force-active seam in the wrap-up, and passes both required verification commands plus the review gate.
