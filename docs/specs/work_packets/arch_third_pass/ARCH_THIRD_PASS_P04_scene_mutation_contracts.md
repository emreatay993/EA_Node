# ARCH_THIRD_PASS P04: Scene Mutation Contracts

## Objective
- Reduce the internal reach-through between `graph_scene_bridge.py` and `graph_scene_mutation_history.py` by introducing explicit scene context/services for mutation, selection, rebuild, and history coordination while keeping the public bridge API stable.

## Preconditions
- `P00` through `P03` are marked `PASS` in [ARCH_THIRD_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_STATUS.md).
- No later `ARCH_THIRD_PASS` packet is in progress.

## Execution Dependencies
- `P03`

## Target Subsystems
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene_scope_selection.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- packet-owned scene helper modules under `ea_node_editor/ui_qml/`
- `tests/test_graph_track_b.py`
- `tests/test_passive_runtime_wiring.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_main_window_shell.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene_scope_selection.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- packet-owned scene helper modules under `ea_node_editor/ui_qml/`
- `tests/test_graph_track_b.py`
- `tests/test_passive_runtime_wiring.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `tests/test_main_window_shell.py`

## Required Behavior
- Introduce explicit scene-owned context or service objects for mutation, rebuild, selection, and history coordination where those responsibilities currently rely on cross-module reach-through.
- Reduce `GraphSceneBridge` knowledge of `graph_scene_mutation_history.py` internals and reduce mutation-history knowledge of bridge-private state.
- Keep the public `GraphSceneBridge` slot/property API stable for current QML consumers and tests.
- Preserve runtime wiring, graph-track, and shell integration behavior while moving internal ownership boundaries.
- Prefer packet-owned helper modules or service objects over expanding bridge/private cross-calls.

## Non-Goals
- No packet-owned QML root cleanup; `P03` already owns that.
- No passive media-surface bridge cleanup; `P05` owns that.
- No execution worker or persistence centralization yet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_track_b tests.test_passive_runtime_wiring tests.test_graph_scene_bridge_bind_regression tests.test_main_window_shell -v`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_track_b -v`

## Expected Artifacts
- `docs/specs/work_packets/arch_third_pass/P04_scene_mutation_contracts_WRAPUP.md`

## Acceptance Criteria
- Packet-owned scene mutation/rebuild/selection/history coordination no longer relies on broad internal reach-through between the public bridge and mutation-history modules.
- Public `GraphSceneBridge` API remains stable.
- The targeted graph-track, runtime-wiring, bridge-bind, and shell regressions pass.

## Handoff Notes
- `P05` will consume the bridge contracts from QML passive media surfaces; keep packet-owned media-facing methods stable unless the packet explicitly replaces them behind new bridge adapters.
- `P06` and `P07` should not need to reopen scene-boundary ownership if this seam stays explicit.
