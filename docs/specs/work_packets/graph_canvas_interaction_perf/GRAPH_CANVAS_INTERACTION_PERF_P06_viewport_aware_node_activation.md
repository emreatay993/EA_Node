# GRAPH_CANVAS_INTERACTION_PERF P06: Viewport-Aware Node Activation

## Objective
- Keep the full node delegate world instantiated while deactivating offscreen heavy node subtrees so pan/zoom no longer pays full node-surface cost outside the padded visible viewport.

## Preconditions
- `P05` is marked `PASS` in `docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_STATUS.md`.
- No later `GRAPH_CANVAS_INTERACTION_PERF` packet is in progress.

## Execution Dependencies
- `P05`

## Target Subsystems
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeResizeHandle.qml`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_passive_graph_surface_host.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeResizeHandle.qml`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_passive_graph_surface_host.py`
- `docs/specs/work_packets/graph_canvas_interaction_perf/P06_viewport_aware_node_activation_WRAPUP.md`

## Required Behavior
- Introduce a padded visible-scene-rect driven `renderActive` seam so heavy node subtrees can deactivate when a node is far offscreen.
- Keep all node delegates instantiated; this packet may gate heavy rendering work, not remove node presence from the scene model.
- Force nodes to remain active when they are selected, hovered, previewed, pending-connection, context-targeted, dragged, or resized.
- Preserve current object names, graph-surface contracts, and visible behavior.
- Update focused graph-surface input and passive-host regressions to prove offscreen deactivation plus active-node exceptions.

## Non-Goals
- No visible node placeholder mode, proxy surface, or user-facing quality change.
- No node chrome/shadow caching yet. `P07` owns that.
- No grid, minimap, or docs work.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_contract.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/graph_canvas_interaction_perf/P06_viewport_aware_node_activation_WRAPUP.md`

## Acceptance Criteria
- Offscreen heavy node subtrees deactivate from a padded visible-scene-rect gate while node delegates remain instantiated.
- Interaction-critical nodes stay active in all required exception states.
- Focused graph-surface and passive-host regressions pass.

## Handoff Notes
- Record the exact force-active conditions and any padding heuristic in the wrap-up so later packets preserve behavior.
