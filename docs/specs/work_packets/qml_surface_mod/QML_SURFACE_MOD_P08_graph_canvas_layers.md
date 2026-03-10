# QML_SURFACE_MOD P08: GraphCanvas Layer Extraction

## Objective
- Extract GraphCanvas background/grid and library drop-preview visual layers into dedicated components.

## Preconditions
- `P07` is marked `PASS` in [QML_SURFACE_MOD_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/qml_surface_mod/QML_SURFACE_MOD_STATUS.md).

## Target Subsystems
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasBackground.qml` (new)
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasDropPreview.qml` (new)
- `tests/test_main_window_shell.py`

## Required Behavior
- Extract background gradient + grid canvas rendering into `GraphCanvasBackground.qml`.
- Extract drag/drop preview node rendering layer into `GraphCanvasDropPreview.qml`.
- Keep existing z-order, sizing math, and redraw behavior unchanged.
- Keep integration with existing GraphCanvas state and helper methods unchanged.

## Non-Goals
- No minimap/context/input extraction in this packet.
- No user-visible behavior changes.

## Verification Commands
1. `venv\Scripts\python.exe -m unittest tests.test_main_window_shell -v`

## Acceptance Criteria
- GraphCanvas visual layers are modularized with behavior-equivalent rendering and interaction continuity.
- Main shell test suite passes.

## Handoff Notes
- `P09` extracts remaining interaction overlays and runs the final full regression gate.
