# SHELL_MOD P03: Window Library and Inspector Payload Extraction

## Objective
- Extract node library and selected-node inspector payload shaping logic from `window.py` into helper module(s).

## Preconditions
- `P02` is marked `PASS` in [SHELL_MOD_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/shell_mod/SHELL_MOD_STATUS.md).

## Target Subsystems
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_library_inspector.py` (new)
- `tests/test_main_window_shell.py`
- `tests/test_workspace_library_controller_unit.py`

## Required Behavior
- Extract logic behind:
  - registry + combined library payloads
  - library filters/grouped output/options
  - selected-node property/port payload shaping
  - pin data type option shaping
- Keep payload schemas and sort/filter semantics unchanged.
- Keep all related `@pyqtProperty` signatures unchanged in `ShellWindow`.

## Non-Goals
- No search/scope state extraction.
- No controller flow extraction.

## Verification Commands
1. `venv\Scripts\python.exe -m unittest tests.test_main_window_shell tests.test_workspace_library_controller_unit -v`

## Acceptance Criteria
- Helper module owns payload shaping logic while `window.py` remains QML-facing shell facade.
- Tests confirm unchanged behavior.

## Handoff Notes
- `P04` will extract graph-search and scope state logic next.
