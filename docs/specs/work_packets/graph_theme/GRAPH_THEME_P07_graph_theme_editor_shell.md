# GRAPH_THEME P07: Graph Theme Editor Shell

## Objective
- Add the graph-theme manager/editor dialog shell and library-management UI wiring without enabling token editing yet.

## Preconditions
- `P06` is marked `PASS` in [GRAPH_THEME_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_theme/GRAPH_THEME_STATUS.md).
- Custom-theme CRUD helpers already exist in the graph-theme/app-preferences layer.

## Target Subsystems
- `ea_node_editor/ui/dialogs/graph_theme_editor_dialog.py` (new)
- `ea_node_editor/ui/dialogs/graphics_settings_dialog.py`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_graph_theme_editor_dialog.py` (new)
- `tests/test_graphics_settings_dialog.py`

## Required Behavior
- Add `ea_node_editor/ui/dialogs/graph_theme_editor_dialog.py`.
- Integrate a `Manage Graph Themes...` entry point from graphics settings or the shell flow.
- The dialog must show:
  - built-in themes
  - custom themes
  - `New`
  - `Duplicate`
  - `Rename`
  - `Delete`
  - `Use Selected`
- Built-in themes remain read-only and cannot be renamed or deleted.
- Show grouped token sections in the right pane as a preview/read-only shell in this packet.
- Keep dialog wiring modular rather than expanding `window.py` or `graphics_settings_dialog.py` ad hoc.

## Non-Goals
- No editable token fields yet.
- No live apply of token changes yet.
- No import/export of theme files.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_theme_editor_dialog tests.test_graphics_settings_dialog -v`

## Acceptance Criteria
- Users can open the graph-theme manager, inspect built-in/custom themes, and use the library-management commands.
- Built-ins are visibly read-only.
- The dialog remains a shell for the editor; token editing is deferred to `P08`.

## Handoff Notes
- `P08` enables editing for custom themes only and adds live runtime apply behavior on top of this shell.
