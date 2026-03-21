# GRAPH_CANVAS_INTERACTION_PERF P04: Scene-Space Edge Paint Path

## Objective
- Move edge painting onto a cached scene-space transform path so pan/zoom no longer pays per-point screen-space conversion in the hot loop.

## Preconditions
- `P03` is marked `PASS` in `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_STATUS.md`.
- No later `GRAPH_CANVAS_INTERACTION_PERF` packet is in progress.

## Execution Dependencies
- `P03`

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `tests/test_flow_edge_labels.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `tests/test_flow_edge_labels.py`
- `docs/specs/work_packets/graph_canvas_interaction_perf/P04_scene_space_edge_paint_path_WRAPUP.md`

## Required Behavior
- Keep edge geometry cached in scene space and apply the viewport transform once per draw rather than per edge point.
- Convert constant-width stroke, dash, arrowhead, and hit-test thresholds into scene-space equivalents so visible output and interaction behavior remain unchanged.
- Preserve edge selection, preview, and flow rendering behavior.
- Keep hit testing correct after the scene-space refactor.
- Update focused edge/flow regression coverage to prove the refactor without pulling label-model work forward from `P05`.

## Non-Goals
- No visible-edge snapshot or shared label-model work yet. `P05` owns that.
- No node, grid, minimap, or docs work.
- No user-facing visual changes.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flow_edge_labels.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flow_edge_labels.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/graph_canvas_interaction_perf/P04_scene_space_edge_paint_path_WRAPUP.md`

## Acceptance Criteria
- Edge paint no longer performs per-point screen-space conversion in the hot loop.
- Edge selection, preview, flow rendering, and hit testing remain correct.
- Focused flow-edge regressions pass.
- Shared visible-edge snapshot work remains deferred to `P05`.

## Handoff Notes
- Record the final scene-space transform and threshold conversion strategy so `P05` can reuse it instead of re-deriving geometry conventions.
- Document any new cached geometry structures that later packets must treat as authoritative.
