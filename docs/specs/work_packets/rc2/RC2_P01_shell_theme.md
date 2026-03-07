# RC2 P01: Shell + Theme Fidelity

## Objective
- Implement a generated Stitch-style dark theme and apply high-fidelity shell styling based on GUI mockup 1 without breaking existing shell behavior.

## Inputs
- `docs/specs/requirements/10_ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/adrs/ADR-0001-ui-stack.md`

## Allowed Files
- `ea_node_editor/app.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui_qml/status_model.py`
- `ea_node_editor/ui/theme/*`
- `tests/test_theme_shell_rc2.py`
- `tests/test_main_window_shell.py`

## Do Not Touch
- `ea_node_editor/execution/*`
- `ea_node_editor/persistence/*`

## Verification
1. `venv\Scripts\python -m unittest tests.test_main_window_shell tests.test_theme_shell_rc2 -v`

## Output Artifacts
- `docs/specs/perf/rc2/shell_idle.png`

## Merge Gate
- Existing shell window tests pass.
- New shell/theme tests pass.
