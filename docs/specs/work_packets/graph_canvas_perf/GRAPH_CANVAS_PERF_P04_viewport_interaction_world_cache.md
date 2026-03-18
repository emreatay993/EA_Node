# GRAPH_CANVAS_PERF P04: Viewport Interaction World Cache

## Objective
- Improve live pan/zoom FPS by reusing a cached node-world presentation during viewport interaction while preserving current steady-state visuals and interaction correctness.

## Preconditions
- `P00` through `P03` are marked `PASS` in [GRAPH_CANVAS_PERF_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_STATUS.md).
- No later `GRAPH_CANVAS_PERF` packet is in progress.

## Execution Dependencies
- `P03`

## Target Subsystems
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- tracked canvas interaction regression coverage

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_graph_track_b.py`

## Required Behavior
- Introduce a viewport-interaction-only cache or reuse strategy for the node world so pan/zoom can render from a cheaper representation while interaction is active.
- Limit the cache strategy to viewport interaction. Node drag, marquee selection, inline editing, port dragging, and other non-viewport gestures must keep their current behavior and contracts.
- Preserve the current shadow simplification recovery path and ensure the scene returns to the current idle appearance once viewport interaction settles.
- Keep ports, hit targets, context menus, minimap behavior, and inline surface controls correct before, during, and after cache activation.
- Add or update targeted regression coverage for cache activation/recovery and for at least one unaffected non-viewport interaction.

## Non-Goals
- No new user-facing graphics toggle or mode.
- No permanent rasterized or reduced-detail canvas mode.
- No docs or traceability updates yet. `P05` owns that.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py -k "graph_canvas_temporarily_simplifies_node_shadow_during_wheel_zoom" -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_track_b.py -k "viewport_applies_zoom_and_center_updates" -q`
3. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 80 --edges 220 --load-iterations 1 --interaction-samples 8 --baseline-runs 1 --report-dir artifacts/graph_canvas_perf_p04`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py -k "graph_canvas_temporarily_simplifies_node_shadow_during_wheel_zoom" -q`

## Expected Artifacts
- `docs/specs/work_packets/graph_canvas_perf/P04_viewport_interaction_world_cache_WRAPUP.md`

## Acceptance Criteria
- The targeted viewport-interaction regression tests pass.
- The small-sample benchmark smoke run completes successfully after cache activation is introduced.
- Cache activation is limited to viewport interaction and is documented clearly in the wrap-up.
- Idle-state visuals and current public canvas behavior remain intact after interaction settles.

## Handoff Notes
- If the final cache strategy must treat panning and wheel zoom differently, document that split explicitly so `P05` can describe it accurately.
- Record any residual image-quality tradeoff window in milliseconds and the exact recovery trigger used.
