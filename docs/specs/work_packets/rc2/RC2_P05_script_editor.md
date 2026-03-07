# RC2 P05: Python Script Editor Dock

## Objective
- Add a dockable/floating Python script editor surface bound to `core.python_script` node content with syntax highlighting and modified-state UX.

## Inputs
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/gui/3_stitch_engineering_node_editor_workspace (2).zip`

## Allowed Files
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/script_editor_model.py`
- `ea_node_editor/ui/editor/code_editor.py`
- `tests/test_script_editor_dock_rc2.py`
- `tests/test_main_window_shell.py`

## Do Not Touch
- `ea_node_editor/execution/*`
- `ea_node_editor/persistence/serializer.py` (except fields required to persist dock state)

## Verification
1. `venv\Scripts\python -m unittest tests.test_script_editor_dock_rc2 tests.test_main_window_shell -v`

## Output Artifacts
- `docs/specs/perf/rc2/script_editor.png`

## Merge Gate
- Editor binding and persistence tests pass.
- Existing shell tests remain green.
