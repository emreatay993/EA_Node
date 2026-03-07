# RC3 Script Editor Ergonomics Notes

- Packet: `RC3-P02`
- Date: `2026-03-01`
- Branch label: `rc3/p02-script-editor-ergonomics`

## Implemented Changes

- Added line-number gutter rendering to `PythonCodeEditor` using a dedicated line-number area widget and viewport margins.
- Added caret diagnostics signal (`line`, `column`, `position`, `selection`) and synchronized diagnostics updates on cursor/selection changes.
- Updated script editor dock diagnostics label to include line/column, selected character count, and absolute position.
- Added deterministic editor focus behavior when:
  - script editor dock becomes visible,
  - a script node is selected while dock is visible,
  - apply/revert actions complete.

## Verification Command

- `venv\Scripts\python -m unittest tests.test_script_editor_dock_rc2 tests.test_main_window_shell -v`

## Test Summary

- Result: **PASS**
- Total: `21`
- Passed: `21`
- Failed: `0`
- Duration: `5.599s`

## Evidence

- UI capture: `docs/specs/perf/rc3/script_editor_ergonomics.png`
- Added assertions:
  - `tests/test_script_editor_dock_rc2.py::test_script_editor_shows_gutter_and_caret_diagnostics`
  - `tests/test_script_editor_dock_rc2.py::test_toggle_script_editor_focuses_editor_for_script_node`
  - `tests/test_main_window_shell.py::test_script_editor_action_focuses_editor_when_script_node_selected`
