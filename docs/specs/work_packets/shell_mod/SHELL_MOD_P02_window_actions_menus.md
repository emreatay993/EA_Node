# SHELL_MOD P02: Window Actions and Menus Extraction

## Objective
- Extract action creation and menu wiring out of `window.py` into dedicated helper module(s).

## Preconditions
- `P01` is marked `PASS` in [SHELL_MOD_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/shell_mod/SHELL_MOD_STATUS.md).

## Target Subsystems
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_actions.py` (new)
- `tests/test_main_window_shell.py`

## Required Behavior
- Move `_create_actions` and `_build_menu_bar` implementation detail into helper module(s).
- Preserve current action attribute names, shortcuts, and menu order/labels.
- Keep application-wide shortcut context behavior unchanged.

## Non-Goals
- No graph-search state extraction.
- No library/inspector extraction.

## Verification Commands
1. `venv\Scripts\python.exe -m unittest tests.test_main_window_shell -v`

## Acceptance Criteria
- Action and menu behavior is unchanged.
- `window.py` action/menu section is slimmer and delegates to helper module(s).

## Handoff Notes
- `P03` will extract library/inspector payload shaping and must not duplicate action/menu logic.
