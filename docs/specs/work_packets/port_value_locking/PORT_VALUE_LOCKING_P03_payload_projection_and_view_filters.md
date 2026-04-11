# PORT_VALUE_LOCKING P03: Payload Projection And View Filters

## Objective

- Project locked-port and optional-port state into the scene payload, add the scene-facing mutations for per-view port filtering, and expose the required command slots before any node-row or canvas gesture QML adopts the feature.

## Preconditions

- `P02` is complete and accepted.
- The packet branch starts from the current accepted packet-set integration base.

## Execution Dependencies

- `PORT_VALUE_LOCKING_P02_mutation_semantics_and_locked_port_invariants.md`

## Target Subsystems

- `ea_node_editor/graph/mutation_service.py`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/ui_qml/graph_scene/command_bridge.py`
- `ea_node_editor/ui_qml/graph_scene/state_support.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/selection_and_scope_ops.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/main_window_shell/view_library_inspector.py`
- `tests/graph_surface/passive_host_boundary_suite.py`

## Conservative Write Scope

- `ea_node_editor/graph/mutation_service.py`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/ui_qml/graph_scene/command_bridge.py`
- `ea_node_editor/ui_qml/graph_scene/state_support.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/selection_and_scope_ops.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/main_window_shell/view_library_inspector.py`
- `tests/graph_surface/passive_host_boundary_suite.py`
- `docs/specs/work_packets/port_value_locking/P03_payload_projection_and_view_filters_WRAPUP.md`
- `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_STATUS.md`

## Required Behavior

- Add mutation methods for `set_view_hide_locked_ports` and `set_view_hide_optional_ports` on the validated and scene-authoring paths.
- Expose `set_port_locked`, `set_hide_locked_ports`, and `set_hide_optional_ports` through the scene command surface and any state-support wrappers that QML already uses.
- Keep the new view filters scoped to the active view only; do not widen them into node or workspace data.
- Extend `GraphScenePayloadBuilder.build_ports_payload()` so each visible port payload includes both `locked` and `optional`.
- Filter locked and optional rows from the emitted payload based on the active view-state toggles while preserving the default visible behavior when both toggles are `False`.
- Update the scene mutation-history binding so the new scene commands participate in undo/redo through the existing authoring boundary.
- Extend payload and bridge regression anchors so missing slot exposure or incorrect payload filtering fails deterministically.

## Non-Goals

- No locked-port row visuals or double-click QML behavior yet.
- No canvas-wide gesture handling yet.
- No changes to lock-trigger semantics or backend connection invariants from `P02`.

## Verification Commands

1. Full packet verification:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_scene_bridge_bind_regression.py tests/main_window_shell/view_library_inspector.py tests/graph_surface/passive_host_boundary_suite.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_scene_bridge_bind_regression.py tests/main_window_shell/view_library_inspector.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/port_value_locking/P03_payload_projection_and_view_filters_WRAPUP.md`
- `ea_node_editor/graph/mutation_service.py`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/ui_qml/graph_scene/command_bridge.py`
- `ea_node_editor/ui_qml/graph_scene/state_support.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/selection_and_scope_ops.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/main_window_shell/view_library_inspector.py`
- `tests/graph_surface/passive_host_boundary_suite.py`

## Acceptance Criteria

- Scene-facing command slots exist for manual port lock mutation and both per-view hide toggles.
- Port payloads expose `locked` and `optional` fields for visible rows.
- Active-view filter state removes locked and optional rows from emitted payload when enabled and leaves defaults unchanged when disabled.
- Undo/redo covers the new view-filter and lock-toggle scene mutations.
- The full packet verification command passes.
- The review gate passes.

## Handoff Notes

- Stop after `P03`. Do not start `P04` in the same thread.
- `P04` consumes these payload and command surfaces to add locked-port chrome, manual double-click toggle routing, and locked drop-candidate suppression in QML.
