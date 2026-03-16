# GRAPH_SURFACE_INPUT P06: Inline Extended Editors

## Objective
- Add graph-surface inline support for `textarea` and `path` properties using the shared control kit and the node-specific bridge APIs from `P03`.

## Preconditions
- `P05` is marked `PASS` in [GRAPH_SURFACE_INPUT_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_STATUS.md).
- No later `GRAPH_SURFACE_INPUT` packet is in progress.

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph/GraphInlinePropertiesLayer.qml`
- `ea_node_editor/ui_qml/components/graph/surface_controls/*`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_graph_surface_input_inline.py` (new)
- focused shell regressions for inline media-node editing

## Required Behavior
- Add inline `textarea` editor support with:
  - dirty-state tracking
  - explicit Apply/Reset actions
  - `Ctrl+Enter` commit
  - `Esc` reset
  - local interactive-rect publication for the text area and action buttons
- Add inline `path` editor support with:
  - line edit
  - Browse button
  - routing through `browse_node_property_path(nodeId, key, current_path)`
  - local interactive-rect publication for both the field and Browse button
- Keep inspector behavior unchanged; this packet extends graph-surface inline editing only.
- Add targeted regressions for media-node inline `path` behavior and any graph-surface `textarea` usage introduced by current catalog nodes.

## Non-Goals
- No media hover-proxy removal yet.
- No TODO/docs updates yet.
- No new property types beyond the locked inline editor set.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_surface_input_inline -v`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.main_window_shell.passive_image_nodes.MainWindowShellPassiveImageNodesTests.test_image_panel_inline_path_editor_commits_without_node_drag -v`
3. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.main_window_shell.passive_pdf_nodes.MainWindowShellPassivePdfNodesTests.test_pdf_panel_inline_path_editor_commits_without_node_drag -v`

## Acceptance Criteria
- Graph-surface inline editing supports `textarea` and `path`.
- Inline `textarea` and `path` controls claim pointer ownership locally and do not start host drag/open/context behavior.
- Path browsing and commit behavior works by explicit `nodeId`.

## Handoff Notes
- `P07` migrates media-surface action buttons onto the same direct ownership model.
