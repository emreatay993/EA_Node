# P03 Payload Projection And View Filters Wrap-Up

## Implementation Summary

- Packet: `P03`
- Branch Label: `codex/port-value-locking/p03-payload-projection-and-view-filters`
- Commit Owner: `worker`
- Commit SHA: `32be122133585ac75acb1630dd4bf320356d68e0`
- Changed Files: `docs/specs/work_packets/port_value_locking/P03_payload_projection_and_view_filters_WRAPUP.md`, `ea_node_editor/graph/mutation_service.py`, `ea_node_editor/graph/normalization.py`, `ea_node_editor/ui_qml/graph_scene/command_bridge.py`, `ea_node_editor/ui_qml/graph_scene/state_support.py`, `ea_node_editor/ui_qml/graph_scene_mutation/selection_and_scope_ops.py`, `ea_node_editor/ui_qml/graph_scene_mutation_history.py`, `ea_node_editor/ui_qml/graph_scene_payload_builder.py`, `tests/test_graph_scene_bridge_bind_regression.py`, `tests/main_window_shell/view_library_inspector.py`, `tests/graph_surface/passive_host_boundary_suite.py`
- Artifacts Produced: `docs/specs/work_packets/port_value_locking/P03_payload_projection_and_view_filters_WRAPUP.md`, `ea_node_editor/graph/mutation_service.py`, `ea_node_editor/graph/normalization.py`, `ea_node_editor/ui_qml/graph_scene/command_bridge.py`, `ea_node_editor/ui_qml/graph_scene/state_support.py`, `ea_node_editor/ui_qml/graph_scene_mutation/selection_and_scope_ops.py`, `ea_node_editor/ui_qml/graph_scene_mutation_history.py`, `ea_node_editor/ui_qml/graph_scene_payload_builder.py`, `tests/test_graph_scene_bridge_bind_regression.py`, `tests/main_window_shell/view_library_inspector.py`, `tests/graph_surface/passive_host_boundary_suite.py`

P03 projects lock and optional-port state through the scene payload instead of leaving the data stranded in the backend model. The mutation layer now owns active-view `hide_locked_ports` and `hide_optional_ports` setters, the scene command surface exposes manual `set_port_locked` plus both hide toggles through the existing authoring boundary, and payload building filters visible rows against the active view while publishing explicit `locked` and `optional` flags for each emitted port. The scene payload cache now also refreshes when a view switch changes only the active view filters, and the packet-owned regressions cover slot exposure, payload metadata, view-local filtering, and undo/redo round-trips.

## Verification

- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_scene_bridge_bind_regression.py tests/main_window_shell/view_library_inspector.py tests/graph_surface/passive_host_boundary_suite.py --ignore=venv -q` (`66 passed, 46 subtests passed`)
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_scene_bridge_bind_regression.py tests/main_window_shell/view_library_inspector.py --ignore=venv -q` (`51 passed, 28 subtests passed`)

- Final Verification Verdict: PASS

## Manual Test Directives

Ready for manual testing

- Prerequisites: launch the application from this branch, open a graph workspace, and use the existing developer invocation surface for `window.scene` slot calls because the dedicated QML gestures land in later packets.
- Test 1: Add a `Logger` node, then call `window.scene.set_hide_locked_ports(True)`. Expected result: the `message` port row disappears while `exec_in` and `exec_out` remain visible because the active view now filters locked rows from the scene payload.
- Test 2: With the same `Logger` node still selected, call `window.scene.set_port_locked(node_id, "message", False)` and then `window.scene.set_hide_locked_ports(False)`. Expected result: the `message` row returns without changing the property value, confirming that manual lock state now flows through the scene command surface and payload projection.
- Test 3: Create a second view, set `window.scene.set_hide_optional_ports(True)` in that view, then switch back and forth between the two views. Expected result: the second view collapses the `Logger` payload to its required `exec_in` row, while the original view keeps its own independent row visibility state.

## Residual Risks

- The hide toggles and manual port-lock mutation are available through the scene command surface, but this packet intentionally does not add dedicated QML gestures or locked-row chrome; that UI work remains deferred to `P04` and `P05`.
- Active-view filter changes now refresh the cached scene payload on access, but the view-switch path still depends on that scene-layer refresh instead of an explicit workspace-view invalidation hook.
- Pytest completed with exit code `0`, but the Windows environment still emitted a non-failing temp-directory cleanup `PermissionError` during shutdown.

## Ready for Integration

- Yes: P03 adds the required scene-facing lock and filter mutations, the payload now projects and filters `locked` and `optional` rows per active view, and both the full packet verification and review gate passed on the packet branch.
