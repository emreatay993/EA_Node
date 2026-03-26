# ARCHITECTURE_REFACTOR P12: Graph Canvas Scene Decomposition

## Objective
- Break up `GraphCanvas`, scene, host, geometry, and theme hotspots without reopening the public graph-surface contract.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_REFACTOR` packet is in progress.

## Execution Dependencies
- `P11`

## Target Subsystems
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene_scope_selection.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/`
- `ea_node_editor/ui_qml/graph_surface_metrics.py`
- `ea_node_editor/ui_qml/edge_routing.py`
- `ea_node_editor/ui/dialogs/graph_theme_editor_dialog.py`
- `ea_node_editor/ui/dialogs/`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_graph_track_b.py`
- `tests/test_main_window_shell.py`
- `tests/test_graph_output_mode_ui.py`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_pdf_preview_provider.py`
- `tests/test_viewer_surface_contract.py`
- `tests/test_flowchart_surfaces.py`
- `tests/test_flowchart_visual_polish.py`
- `tests/test_flow_edge_labels.py`
- `tests/test_planning_annotation_catalog.py`
- `tests/test_graph_theme_editor_dialog.py`
- `tests/test_graph_theme_shell.py`
- `tests/test_graphics_settings_preferences.py`
- `tests/test_graphics_settings_dialog.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/test_dead_code_hygiene.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene_scope_selection.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/`
- `ea_node_editor/ui_qml/graph_surface_metrics.py`
- `ea_node_editor/ui_qml/edge_routing.py`
- `ea_node_editor/ui/dialogs/graph_theme_editor_dialog.py`
- `ea_node_editor/ui/dialogs/`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_graph_track_b.py`
- `tests/test_main_window_shell.py`
- `tests/test_graph_output_mode_ui.py`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_pdf_preview_provider.py`
- `tests/test_viewer_surface_contract.py`
- `tests/test_flowchart_surfaces.py`
- `tests/test_flowchart_visual_polish.py`
- `tests/test_flow_edge_labels.py`
- `tests/test_planning_annotation_catalog.py`
- `tests/test_graph_theme_editor_dialog.py`
- `tests/test_graph_theme_shell.py`
- `tests/test_graphics_settings_preferences.py`
- `tests/test_graphics_settings_dialog.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/test_dead_code_hygiene.py`
- `docs/specs/work_packets/architecture_refactor/P12_graph_canvas_scene_decomposition_WRAPUP.md`

## Required Behavior
- Shrink `GraphCanvas.qml` into a composition root on top of the bridge-first contract from `P11`, pushing packet-owned interaction, state, and input-layer helpers into focused QML components.
- Split scene mutation, clipboard, history, and scope-selection logic out of `graph_scene_bridge.py` into smaller helpers without regressing scene payload contracts.
- Break `GraphNodeHost.qml` into smaller host or surface helpers while preserving the shared graph-node contract.
- Extract geometry policy from `graph_surface_metrics.py` and `edge_routing.py` into narrower helpers and keep geometry call sites explicit.
- Make `graph_theme_editor_dialog.py` comply with theme-token architecture while preserving live preview and persisted settings behavior.
- Update inherited `GraphCanvas`, scene, host, geometry, and theme regression anchors in place when packet-owned seams change.

## Non-Goals
- No new passive-node or theme features.
- No further shell-context or graph-canvas compatibility cleanup beyond fallout from packet-owned decompositions.
- No packaging/docs cleanup yet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_contract.py tests/test_graph_scene_bridge_bind_regression.py tests/test_graph_output_mode_ui.py tests/test_passive_graph_surface_host.py tests/test_pdf_preview_provider.py tests/test_viewer_surface_contract.py tests/test_main_window_shell.py tests/main_window_shell/bridge_qml_boundaries.py tests/test_graph_theme_editor_dialog.py tests/test_graph_theme_shell.py tests/test_graphics_settings_preferences.py tests/test_graphics_settings_dialog.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py tests/test_flowchart_surfaces.py tests/test_flowchart_visual_polish.py tests/test_flow_edge_labels.py tests/test_planning_annotation_catalog.py tests/test_graph_track_b.py tests/test_dead_code_hygiene.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_contract.py tests/test_passive_graph_surface_host.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/architecture_refactor/P12_graph_canvas_scene_decomposition_WRAPUP.md`

## Acceptance Criteria
- `GraphCanvas.qml`, scene/history/clipboard, node-host composition, geometry policy, and graph-theme dialog behavior are decomposed into smaller modules or helpers.
- Public graph-surface behavior remains stable and packet-owned host/scene/theme regressions pass.
- The packet-owned verification commands pass.

## Handoff Notes
- `P13` should document and prove the final state rather than discovering stale scene/theme/release assertions left behind by this packet.
