# RC2 P03: Node Library and Inspector UX

## Objective
- Convert node library into categorized tree interaction and refine inspector layout/controls while preserving existing filter semantics and edit behavior.

## Inputs
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/40_NODE_SDK.md`

## Allowed Files
- `ea_node_editor/ui/panels/node_library_panel.py`
- `ea_node_editor/ui/panels/inspector_panel.py`
- `ea_node_editor/ui/main_window.py`
- `tests/test_registry_filters.py`
- `tests/test_inspector_reflection.py`
- `tests/test_main_window_shell.py`

## Do Not Touch
- `ea_node_editor/execution/*`
- `ea_node_editor/persistence/*`

## Verification
1. `venv\Scripts\python -m unittest tests.test_registry_filters tests.test_inspector_reflection tests.test_main_window_shell -v`

## Output Artifacts
- `docs/specs/perf/rc2/library_inspector.png`

## Merge Gate
- Existing filter and inspector tests pass.
- New library tree behavior tests pass.

