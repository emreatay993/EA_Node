# GRAPH_CANVAS_INTERACTION_PERF P07: Static Node Chrome/Shadow Cache

## Objective
- Cache stable node chrome and shadow output so viewport motion stops redoing pixel-identical node decoration work.

## Preconditions
- `P06` is marked `PASS` in `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_STATUS.md`.
- No later `GRAPH_CANVAS_INTERACTION_PERF` packet is in progress.

## Execution Dependencies
- `P06`

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph/GraphNodeChromeBackground.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `tests/test_passive_graph_surface_host.py`
- `tests/graph_track_b/qml_preference_bindings.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/graph/GraphNodeChromeBackground.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `tests/test_passive_graph_surface_host.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `docs/specs/work_packets/graph_canvas_interaction_perf/P07_node_chrome_shadow_cache_WRAPUP.md`

## Required Behavior
- Cache pixel-identical node chrome and shadow output whenever geometry and style inputs are stable, and invalidate only on geometry, selection-border, or shadow-preference changes.
- Preserve current full-fidelity shadow visibility and timing through pan/zoom and any existing transient performance-policy windows.
- Keep visible output unchanged; this is an internal caching packet, not a shadow simplification packet.
- Update focused host and QML preference regressions to prove cached behavior without breaking existing policy expectations.

## Non-Goals
- No node activation policy changes beyond what `P06` already introduced.
- No grid, minimap, or docs work.
- No visible simplification or user-facing performance toggle.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -k "shadow or wheel_zoom" -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py --ignore=venv -k "performance_policy" -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -k "shadow or wheel_zoom" -q`

## Expected Artifacts
- `docs/specs/work_packets/graph_canvas_interaction_perf/P07_node_chrome_shadow_cache_WRAPUP.md`

## Acceptance Criteria
- Stable node chrome/shadow work is cached and invalidates only on geometry, selection-border, or shadow-preference changes.
- Full-fidelity visible shadow behavior remains unchanged.
- Focused host and preference regressions pass.
- Auxiliary canvas and docs work remain deferred.

## Handoff Notes
- Document the cache ownership and invalidation triggers so later packets do not accidentally thrash or bypass it.
- If policy-state timing still influences cache invalidation indirectly, record that interaction clearly.
