# ARCHITECTURE_MAINTAINABILITY_REFACTOR P11: Graph Canvas Scene Decomposition

## Objective
- Perform a second-pass split of graph-canvas scene ownership, mutation/history logic, payload building, and host interaction helpers after compatibility removals are complete.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_MAINTAINABILITY_REFACTOR` packet is in progress.

## Execution Dependencies
- `P10`

## Target Subsystems
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/graph_scene_scope_selection.py`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_graph_output_mode_ui.py`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/test_flowchart_surfaces.py`
- `tests/test_planning_annotation_catalog.py`
- `tests/test_graph_track_b.py`
- `tests/graph_track_b/qml_preference_bindings.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/graph_scene_scope_selection.py`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_graph_output_mode_ui.py`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/test_flowchart_surfaces.py`
- `tests/test_planning_annotation_catalog.py`
- `tests/test_graph_track_b.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `docs/specs/work_packets/architecture_maintainability_refactor/P11_graph_canvas_scene_decomposition_WRAPUP.md`

## Required Behavior
- Keep `GraphCanvas.qml` acting as a composition root rather than the home of broad packet-owned scene, state, and interaction policy.
- Split packet-owned scene mutation/history, payload building, and host interaction helpers into narrower modules with explicit responsibilities.
- Keep `GraphNodeHost.qml` and related graph-host helpers focused on host composition rather than mixed scene, payload, and UI policy.
- Update inherited graph-surface and bridge-boundary regression anchors in place when graph-canvas ownership or helper boundaries move.

## Non-Goals
- No geometry/routing/theme cleanup yet; that belongs to `P12`.
- No new canvas features or interaction modes.
- No further compatibility-bridge cleanup; earlier packets own that already.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_contract.py tests/test_graph_scene_bridge_bind_regression.py tests/test_graph_output_mode_ui.py tests/test_passive_graph_surface_host.py tests/test_main_window_shell.py tests/main_window_shell/bridge_qml_boundaries.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flowchart_surfaces.py tests/test_planning_annotation_catalog.py tests/test_graph_track_b.py tests/graph_track_b/qml_preference_bindings.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_contract.py tests/test_passive_graph_surface_host.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/architecture_maintainability_refactor/P11_graph_canvas_scene_decomposition_WRAPUP.md`

## Acceptance Criteria
- Packet-owned graph-canvas scene responsibilities are decomposed into clearer modules.
- `GraphCanvas.qml` and graph host helpers act as composition layers rather than compatibility-heavy policy buckets.
- The inherited graph-surface and scene regression anchors pass after the decomposition.

## Handoff Notes
- `P12` should keep the graph-canvas contract stable and focus only on geometry, routing, theme, and performance-policy hotspots.
