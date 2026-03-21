# GRAPH_CANVAS_INTERACTION_PERF P02: Atomic Viewport Mutation Path

## Objective
- Collapse wheel zoom into one anchored viewport mutation, bind hot canvas consumers directly to raw viewport state, and remove dead per-node zoom fan-out from normal node delegates without changing public canvas behavior.

## Preconditions
- `P01` is marked `PASS` in `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_STATUS.md`.
- No later `GRAPH_CANVAS_INTERACTION_PERF` packet is in progress.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ea_node_editor/ui_qml/viewport_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeResizeHandle.qml`
- `tests/graph_track_b/viewport.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_passive_graph_surface_host.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/viewport_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeResizeHandle.qml`
- `tests/graph_track_b/viewport.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_passive_graph_surface_host.py`
- `docs/specs/work_packets/graph_canvas_interaction_perf/P02_atomic_viewport_state_updates_WRAPUP.md`

## Required Behavior
- Add an additive internal viewport mutation seam such as `set_view_state(...)` and anchored zoom support so wheel zoom can commit one logical viewport update.
- Add a cached visible-scene-rect property or signal on `ViewportBridge` and move the hot canvas path off the coarse copy-heavy view-state wrapper onto raw viewport state.
- Preserve the current cursor-anchor semantics, zoom limits, and canvas-facing public behavior.
- Keep compatibility for existing public bridge callers that still use current slots or helpers.
- Route `GraphCanvas.qml` wheel zoom through the new atomic path so the normal interaction no longer performs separate zoom and pan mutations for one wheel step.
- Bind hot canvas consumers directly to raw viewport state instead of the coarse wrapper on the hot path while preserving compatibility for non-hot callers that still depend on the existing bridge surface.
- Remove dead per-node zoom fan-out from normal node delegates and keep zoom reads only where resize math still genuinely depends on them.
- Reduce avoidable duplicate viewport notifications on the wheel path, but leave later redraw coalescing work to `P03`.
- Update focused tests so one wheel interaction proves cursor anchoring and one logical viewport-state commit.

## Non-Goals
- No redraw scheduling or view-state flush changes yet. `P03` owns that.
- No viewport-aware node activation gating yet. `P06` owns that.
- No edge-layer, grid, minimap, or docs work.
- No visible behavior change and no new user-facing settings.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/graph_track_b/viewport.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py --ignore=venv -q`
3. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_contract.py --ignore=venv -q`
4. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -k "wheel_zoom" -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/graph_track_b/viewport.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/graph_canvas_interaction_perf/P02_atomic_viewport_state_updates_WRAPUP.md`

## Acceptance Criteria
- Wheel zoom applies one anchored viewport mutation per logical input step.
- Hot canvas consumers read raw viewport state plus cached visible-scene-rect data instead of paying the coarse wrapper path.
- Dead per-node zoom fan-out is removed from normal node delegates without breaking resize behavior.
- Existing public bridge callers remain compatible.
- Focused viewport and passive host regressions pass.
- Redraw-flush and node-activation follow-up work remain clearly deferred to later packets.

## Handoff Notes
- Record the new internal viewport API shape, cached visible-scene-rect seam, and the compatibility path retained for existing callers.
- Call out any remaining redraw duplication that `P03` is expected to remove so later workers do not rediscover the same seam.
