# GRAPH_CANVAS_INTERACTION_PERF P03: Frame-Coalesced View Redraw Scheduling

## Objective
- Coalesce viewport-driven redraw work so each committed viewport change schedules at most one grid/edge flush.

## Preconditions
- `P02` is marked `PASS` in `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_STATUS.md`.
- No later `GRAPH_CANVAS_INTERACTION_PERF` packet is in progress.

## Execution Dependencies
- `P02`

## Target Subsystems
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasBackground.qml`
- `tests/graph_track_b/viewport.py`
- `tests/graph_track_b/qml_preference_bindings.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasBackground.qml`
- `tests/graph_track_b/viewport.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `docs/specs/work_packets/graph_canvas_interaction_perf/P03_view_state_redraw_flush_WRAPUP.md`

## Required Behavior
- Replace immediate view-driven redraw requests with dirty flags plus a single-shot flush so one committed viewport change leads to one grid/edge redraw cycle.
- Ensure grid and edge redraws happen at most once per committed viewport tick, including anchored wheel zoom flows that commit both zoom and center updates together.
- Preserve current visuals and public behavior while reducing duplicate redraw scheduling.
- Add or update deterministic redraw-counter tests proving one wheel commit causes one grid/edge flush, not separate zoom and pan redraws.

## Non-Goals
- No raw viewport-state or cached visible-scene-rect hot-path binding work here. `P02` owns that.
- No edge scene-space paint refactor yet. `P04` owns that.
- No node activation, node chrome caching, minimap, or docs work.
- No visible degradation or new settings.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/graph_track_b/viewport.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py --ignore=venv -k "coalesces_view_state_redraw_requests_per_commit" -q`

## Expected Artifacts
- `docs/specs/work_packets/graph_canvas_interaction_perf/P03_view_state_redraw_flush_WRAPUP.md`

## Acceptance Criteria
- Viewport-driven redraw requests are coalesced to one grid/edge flush per committed viewport change.
- One wheel commit produces one grid/edge flush rather than separate redraws for zoom and pan components.
- Focused viewport and QML regression coverage passes.
- Scene-space edge refactor remains deferred to `P04`.

## Handoff Notes
- Document the final dirty-flag and single-shot flush ownership so later packets reuse the same redraw boundary instead of bypassing it.
- If any redraw counters or diagnostics are added for tests, note whether they are packet-private or safe for later reuse.
