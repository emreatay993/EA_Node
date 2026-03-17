# SHELL_SCENE_BOUNDARY P05: Shell Inspector Bridge

## Objective
- Move inspector QML consumers onto a focused inspector bridge so `InspectorPane.qml` no longer depends directly on raw `ShellWindow` selected-node APIs for its owned concerns.

## Preconditions
- `P02` is marked `PASS` in [SHELL_SCENE_BOUNDARY_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/shell_scene_boundary/SHELL_SCENE_BOUNDARY_STATUS.md).
- No later `SHELL_SCENE_BOUNDARY` packet is in progress.

## Execution Dependencies
- `P02`

## Target Subsystems
- `ea_node_editor/ui_qml/shell_inspector_bridge.py`
- `ea_node_editor/ui_qml/components/shell/InspectorPane.qml`
- `tests/test_inspector_reflection.py`
- `tests/test_passive_property_editors.py`
- `tests/test_main_window_shell.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/shell_inspector_bridge.py`
- `ea_node_editor/ui_qml/components/shell/InspectorPane.qml`
- `tests/test_inspector_reflection.py`
- `tests/test_passive_property_editors.py`
- `tests/test_main_window_shell.py`

## Required Behavior
- Expose selected-node header data, property items, port items, pin actions, collapse/ungroup actions, and property-edit/browse flows through `shell_inspector_bridge.py` or an equivalent focused facade created in `P02`.
- Update `InspectorPane.qml` to consume the dedicated bridge for inspector concerns instead of direct `mainWindowRef` calls/reads.
- Preserve current inspector editing behavior, selected-node reflection, path browsing, and passive property editor flows.
- Keep `ShellWindow` compatibility methods/properties callable for tests or non-migrated code paths outside this packet.

## Non-Goals
- No GraphCanvas inline-property routing changes.
- No library/search/workspace/run bridge migration.
- No `GraphSceneBridge` internal refactor.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_inspector_reflection tests.test_passive_property_editors tests.test_main_window_shell -v`

## Acceptance Criteria
- `InspectorPane.qml` no longer depends directly on `ShellWindow` for its owned inspector state/actions.
- Inspector reflection and property-edit regressions pass unchanged.
- No GraphCanvas inline-control behavior changes are introduced.

## Handoff Notes
- `P06` keeps the inspector bridge intact and should not reopen it unless GraphCanvas boundary work reveals a real integration bug.
