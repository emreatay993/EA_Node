# GRAPHICS_SETTINGS P07: Canvas QML Theme Adoption

## Objective
- Move graph-canvas-facing QML neutral surfaces onto the shared theme palette while preserving semantic graph colors.

## Preconditions
- `P06` is marked `PASS` in [GRAPHICS_SETTINGS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graphics_settings/GRAPHICS_SETTINGS_STATUS.md).
- Shell QML theme palette adoption is already complete.

## Target Subsystems
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/NodeCard.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasBackground.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasMinimapOverlay.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasDropPreview.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `tests/test_graph_track_b.py`
- `tests/test_main_window_shell.py`
- `tests/test_theme_shell_rc2.py`

## Required Behavior
- Replace hardcoded neutral canvas/background/border/text colors with `themeBridge` palette bindings.
- Apply the theme palette to graph-canvas background/grid, minimap chrome, context-menu chrome, drop-preview chrome, neutral `NodeCard` surfaces, and non-semantic canvas overlay chrome.
- Preserve the existing graph canvas public contracts:
  - `objectName: "graphCanvas"`
  - `toggleMinimapExpanded()`
  - `clearLibraryDropPreview()`
  - `updateLibraryDropPreview()`
  - `isPointInCanvas()`
  - `performLibraryDrop()`
- Keep semantic node/port/edge accent colors unchanged, including node accent bars and kind/data-derived port/edge colors.
- If `EdgeLayer.qml` needs edits, limit them to non-semantic preview/selection neutrals and leave routed edge semantic colors untouched.

## Non-Goals
- No new graphics preference keys.
- No theme registry redesign beyond what `P05` introduced.
- No workflow settings changes.

## Verification Commands
1. `venv\Scripts\python.exe -m unittest tests.test_graph_track_b tests.test_main_window_shell tests.test_theme_shell_rc2 -v`

## Acceptance Criteria
- Canvas neutral surfaces respond to the active theme without breaking graph interaction behavior.
- Semantic node/port/edge colors continue to mean the same thing before and after the palette migration.
- Existing graph and shell regression tests continue to pass.

## Handoff Notes
- `P08` updates requirement/traceability docs for the finished feature set and runs the final graphics-settings regression gate.
