# GRAPH_CANVAS_INTERACTION_PERF P08: Auxiliary Canvas Stabilization

## Objective
- Stabilize the remaining auxiliary canvas hot paths so grid, minimap, and full-canvas input layers stop adding avoidable lag during pan/zoom after the primary viewport, edge, and node fixes land.

## Preconditions
- `P07` is marked `PASS` in `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_STATUS.md`.
- No later `GRAPH_CANVAS_INTERACTION_PERF` packet is in progress.

## Execution Dependencies
- `P07`

## Target Subsystems
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasBackground.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasMinimapOverlay.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/test_passive_graph_surface_host.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasBackground.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasMinimapOverlay.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/test_passive_graph_surface_host.py`
- `docs/specs/work_packets/graph_canvas_interaction_perf/P08_auxiliary_canvas_stabilization_WRAPUP.md`

## Required Behavior
- Fold grid redraw into the shared viewport flush path established by earlier packets.
- Convert the background grid to a cached tile or equivalent layer that translates during pan and only regenerates on theme, viewport-size, show-grid, or zoom-bucket changes.
- Memoize minimap geometry math and keep minimap node content static during pan/zoom so only the viewport rectangle moves.
- Repeated center changes must move only the minimap viewport rectangle and must not rebuild minimap node geometry.
- Remove unused full-canvas input overhead such as unnecessary `hoverEnabled` behavior when it provides no user-visible value.
- Preserve current full-fidelity visuals and avoid broadening any existing max-performance degradation policy into `full_fidelity`.
- Update focused preference and passive-host regressions to cover the auxiliary-layer behavior.

## Non-Goals
- No new visible grid/minimap policy.
- No changes to checked-in perf docs or traceability docs. `P09` owns that.
- No new user-facing settings or controls.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -k "max_performance_degrades_grid_and_minimap" -q`
3. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -k "minimap" -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -k "minimap" -q`

## Expected Artifacts
- `docs/specs/work_packets/graph_canvas_interaction_perf/P08_auxiliary_canvas_stabilization_WRAPUP.md`

## Acceptance Criteria
- Grid redraw is coalesced with the shared viewport flush path.
- Grid and minimap stop rebuilding avoidable content during ordinary pan/zoom.
- Repeated center changes move only the minimap viewport rect and do not rebuild minimap node geometry.
- Full-canvas input overhead is reduced without changing interaction behavior.
- Focused preference and passive-host regressions pass with unchanged full-fidelity visuals.

## Handoff Notes
- Record the grid cache invalidation keys and the minimap memoization boundaries so `P09` can explain the final runtime behavior accurately.
- If any auxiliary-layer work remains intentionally uncached, document why it is still required per frame.
