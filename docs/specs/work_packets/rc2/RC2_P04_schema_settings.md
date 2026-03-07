# RC2 P04: Schema v2 and Workflow Settings Modal

## Objective
- Introduce schema v2 with backward-compatible migration and implement persisted workflow settings modal integrated with run trigger payloads.

## Inputs
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/50_EXECUTION_ENGINE.md`
- `docs/specs/gui/2_stitch_engineering_node_editor_workspace (1).zip`

## Allowed Files
- `ea_node_editor/settings.py`
- `ea_node_editor/persistence/serializer.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/dialogs/workflow_settings_dialog.py`
- `tests/test_serializer.py`
- `tests/test_settings_dialog_rc2.py`

## Do Not Touch
- `ea_node_editor/graph/*`

## Verification
1. `venv\Scripts\python -m unittest tests.test_serializer tests.test_settings_dialog_rc2 -v`

## Output Artifacts
- `docs/specs/perf/rc2/settings_modal.png`

## Merge Gate
- v1->v2 migration tests pass.
- Settings persistence and trigger inclusion tests pass.
