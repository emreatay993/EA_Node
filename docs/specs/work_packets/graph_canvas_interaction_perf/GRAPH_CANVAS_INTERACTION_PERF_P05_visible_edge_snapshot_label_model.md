# GRAPH_CANVAS_INTERACTION_PERF P05: Visible-Edge Snapshot And Label Model

## Objective
- Reuse one visible-edge snapshot for both painting and flow labels so label placement stops recomputing edge cull and geometry state in a second pass.

## Preconditions
- `P04` is marked `PASS` in `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_STATUS.md`.
- No later `GRAPH_CANVAS_INTERACTION_PERF` packet is in progress.

## Execution Dependencies
- `P04`

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `tests/test_flow_edge_labels.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `tests/test_flow_edge_labels.py`
- `docs/specs/work_packets/graph_canvas_interaction_perf/P05_visible_edge_snapshot_label_model_WRAPUP.md`

## Required Behavior
- Build one visible-edge snapshot per redraw that contains cull result, geometry, selection state, preview state, label mode, and scene-space label anchor data needed by both painting and flow labels.
- Use that snapshot for label delegates so they only do lightweight position arithmetic instead of re-running full cull and geometry work.
- Preserve current label thresholds, selection behavior, preview behavior, and edge hit testing.
- Keep the scene-space paint conventions from `P04` authoritative rather than forking a second geometry model.
- Update focused flow-label regression coverage to prove the shared snapshot behavior and unchanged visible output.

## Non-Goals
- No new visual label policy and no threshold tuning.
- No node activation, grid, minimap, or docs work.
- No further public API changes beyond packet-local internal data reuse.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flow_edge_labels.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flow_edge_labels.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/graph_canvas_interaction_perf/P05_visible_edge_snapshot_label_model_WRAPUP.md`

## Acceptance Criteria
- Painting and flow labels share one visible-edge snapshot model per redraw.
- Label delegates stop recomputing full edge cull/geometry state.
- Flow-label and edge-interaction regressions pass with unchanged visible behavior.
- Node-world and auxiliary-layer work remain deferred.

## Handoff Notes
- Record the snapshot schema and ownership so later packets do not reintroduce duplicate geometry derivations.
- If any label-specific helper remains separate by necessity, document why it cannot reuse the shared snapshot fully.
