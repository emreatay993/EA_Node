# QML_SURFACE_MOD P09: GraphCanvas Interaction Overlays and Final Regression Gate

## Objective
- Extract remaining GraphCanvas interaction overlays (minimap, context menus, input layers) into dedicated components and close the packet set with a full regression gate.

## Preconditions
- `P08` is marked `PASS` in [QML_SURFACE_MOD_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/qml_surface_mod/QML_SURFACE_MOD_STATUS.md).

## Target Subsystems
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasMinimapOverlay.qml` (new)
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml` (new)
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml` (new)
- `tests/test_main_window_shell.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/test_script_editor_dock_rc2.py`
- `tests/test_theme_shell_rc2.py`
- `tests/test_shell_run_controller.py`
- `tests/test_shell_project_session_controller.py`
- `tests/test_workspace_manager.py`
- `tests/test_graph_track_b.py`

## Required Behavior
- Extract minimap UI + interactions into `GraphCanvasMinimapOverlay.qml`.
- Extract edge/node context menus into `GraphCanvasContextMenus.qml`.
- Extract input layers (marquee selection, panning, key handlers) into `GraphCanvasInputLayers.qml`.
- Keep `GraphCanvas.qml` public contracts and behavior unchanged.
- Preserve context menu actions, keyboard shortcuts, zoom/pan interactions, and selection behavior.
- Update status ledger with final packet artifacts, test outcomes, and residual risks.

## Non-Goals
- No new runtime features.
- No Python architecture changes.

## Verification Commands
1. `venv\Scripts\python.exe -m unittest tests.test_main_window_shell tests.test_workspace_library_controller_unit tests.test_script_editor_dock_rc2 tests.test_theme_shell_rc2 tests.test_shell_run_controller tests.test_shell_project_session_controller tests.test_workspace_manager tests.test_graph_track_b -v`

## Acceptance Criteria
- GraphCanvas interaction overlays are modularized with no intended behavior regressions.
- Full regression gate passes.
- Status ledger captures final packet closure details.

## Handoff Notes
- Packet set closes at `P09`; no additional packets should be started in this roadmap.
