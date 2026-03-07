# RC3 P02: Script Editor Ergonomics

## Objective
- Improve the docked script editor with line-number gutter, caret diagnostics, and reliable keyboard focus behavior.

## Non-Objectives
- No replacement of the existing editor widget technology.
- No workflow execution semantic changes.

## Inputs
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/10_ARCHITECTURE.md`

## Allowed Files
- `ea_node_editor/ui/editor/code_editor.py`
- `ea_node_editor/ui/panels/script_editor_dock.py`
- `ea_node_editor/ui/main_window.py`
- `tests/test_script_editor_dock_rc2.py`
- `tests/test_main_window_shell.py`

## Do Not Touch
- `ea_node_editor/execution/**`
- `ea_node_editor/persistence/**`

## Verification
1. `venv\Scripts\python -m unittest tests.test_script_editor_dock_rc2 tests.test_main_window_shell -v`

## Output Artifacts
- `docs/specs/perf/rc3/script_editor_ergonomics.png`
- `docs/specs/perf/rc3/script_editor_ergonomics_notes.md`

## Merge Gate (Requirement IDs)
- `REQ-ARCH-009`
- `REQ-UI-013`
- `REQ-QA-007`
