# QML_SURFACE_MOD P07: GraphCanvas Utility Extraction

## Objective
- Extract pure helper logic from `GraphCanvas.qml` into reusable JS helper module(s) while preserving root method/property contracts.

## Preconditions
- `P06` is marked `PASS` in [QML_SURFACE_MOD_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/qml_surface_mod/QML_SURFACE_MOD_STATUS.md).

## Target Subsystems
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasLogic.js` (new)
- `tests/test_main_window_shell.py`
- `tests/test_workspace_library_controller_unit.py`

## Required Behavior
- Extract pure helper functions from `GraphCanvas.qml` into `GraphCanvasLogic.js` (for example coordinate transforms, drop candidate compatibility checks, preview sizing helpers, and normalization helpers).
- Keep `GraphCanvas.qml` root method/property names and call contracts stable, including:
  - `toggleMinimapExpanded()`
  - `clearLibraryDropPreview()`
  - `updateLibraryDropPreview()`
  - `isPointInCanvas()`
  - `performLibraryDrop()`
- Keep `objectName: "graphCanvas"` and `minimapExpanded` contract unchanged.
- Preserve runtime behavior and interaction outcomes.

## Non-Goals
- No layer/component extraction in this packet.
- No context-menu/minimap/input-layer extraction in this packet.

## Verification Commands
1. `venv\Scripts\python.exe -m unittest tests.test_main_window_shell tests.test_workspace_library_controller_unit -v`

## Acceptance Criteria
- GraphCanvas utility logic is modularized without behavior changes.
- Relevant shell and controller tests pass.

## Handoff Notes
- `P08` extracts visual layers (background/grid + drop preview).
