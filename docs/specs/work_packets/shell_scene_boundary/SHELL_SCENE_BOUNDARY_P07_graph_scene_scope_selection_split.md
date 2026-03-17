# SHELL_SCENE_BOUNDARY P07: GraphScene Scope Selection Split

## Objective
- Extract workspace binding, scope-path, selection, and bounds/navigation state from `GraphSceneBridge` into dedicated helper modules while keeping the bridge’s public QML contract stable.

## Preconditions
- `P06` is marked `PASS` in [SHELL_SCENE_BOUNDARY_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/shell_scene_boundary/SHELL_SCENE_BOUNDARY_STATUS.md).
- No later `SHELL_SCENE_BOUNDARY` packet is in progress.

## Execution Dependencies
- `P06`

## Target Subsystems
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_scope_selection.py` (new)
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_graph_track_b.py`
- `tests/test_inspector_reflection.py`
- `tests/test_main_window_shell.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_scope_selection.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_graph_track_b.py`
- `tests/test_inspector_reflection.py`
- `tests/test_main_window_shell.py`

## Required Behavior
- Extract workspace/model binding, scope-path normalization/persistence, selected-node bookkeeping, scope navigation, bounds helpers, and related signal-emission decisions into `graph_scene_scope_selection.py` or equivalent helpers.
- Keep `GraphSceneBridge` public `@pyqtProperty`, `@pyqtSlot`, and signal names stable.
- Preserve scope persistence, selection behavior, and bridge bindings used by shell and QML.
- Avoid changing mutation/history or payload-building behavior beyond the minimal integration required by this extraction.

## Non-Goals
- No node/edge mutation extraction yet.
- No payload/theme/minimap/media normalization extraction yet.
- No public bridge contract changes.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_scene_bridge_bind_regression tests.test_graph_track_b tests.test_inspector_reflection tests.test_main_window_shell -v`

## Acceptance Criteria
- `GraphSceneBridge` no longer owns all scope/selection state inline.
- Scope/selection/navigation regressions pass.
- No public bridge-slot/property regressions are introduced.

## Handoff Notes
- `P08` assumes this packet has already stabilized the state/binding layer and only extracts mutation/history concerns next.
