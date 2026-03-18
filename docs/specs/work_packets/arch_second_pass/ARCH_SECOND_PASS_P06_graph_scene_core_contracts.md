# ARCH_SECOND_PASS P06: Graph Scene Core Contracts

## Objective
- Pull non-UI graph-command/domain logic out of `GraphSceneMutationHistory` and isolate subnode/composite-node cross-layer behavior behind clearer core contracts so the scene bridge stops coordinating too many internal domains.

## Preconditions
- `P00` through `P02` are marked `PASS` in [ARCH_SECOND_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_second_pass/ARCH_SECOND_PASS_STATUS.md).
- No later `ARCH_SECOND_PASS` packet is in progress.

## Execution Dependencies
- `P02`

## Target Subsystems
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- new packet-owned graph-scene helper modules
- subnode/composite-node seams in graph/execution modules as needed
- packet-owned graph/runtime regression tests

## Conservative Write Scope
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `ea_node_editor/ui_qml/graph_scene_scope_selection.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/graph/transforms.py`
- `ea_node_editor/graph/effective_ports.py`
- `ea_node_editor/execution/compiler.py`
- `ea_node_editor/nodes/builtins/subnode.py`
- `tests/test_graph_track_b.py`
- `tests/test_passive_runtime_wiring.py`
- `tests/test_main_window_shell.py`

## Required Behavior
- Move packet-owned layout, fragment, clipboard, or related graph-command logic out of `GraphSceneMutationHistory` when that logic is fundamentally core/domain behavior rather than bridge orchestration.
- Reduce packet-owned helper dependence on `GraphSceneBridge` private state/method reach-through by passing explicit inputs/results where practical.
- Introduce or tighten a dedicated subnode/composite-node seam so graph, execution, and UI are not all open-coding the same special-case knowledge.
- Keep public `GraphSceneBridge` slots/properties and persisted graph behavior stable from the user’s perspective.
- Preserve current runtime exclusion and graph-authoring behavior for passive/subnode flows.

## Non-Goals
- No `GraphCanvas.qml` or heavy-surface QML refactors.
- No persistence-layer leak cleanup yet; `P07` owns that.
- No verification/docs refresh yet; `P08` owns that.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_track_b tests.test_passive_runtime_wiring tests.test_main_window_shell -v`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_track_b -v`

## Expected Artifacts
- `docs/specs/work_packets/arch_second_pass/P06_graph_scene_core_contracts_WRAPUP.md`

## Acceptance Criteria
- `GraphSceneMutationHistory` owns materially less non-bridge core logic than the current baseline.
- Packet-owned subnode/composite-node behavior is more centralized and less duplicated across graph/execution/UI.
- Current graph/runtime regression coverage passes without changing user-visible graph behavior.

## Handoff Notes
- `P07` handles persistence/workspace boundary ownership separately; do not mix that cleanup into this packet.
- Call out any remaining unavoidable `GraphSceneBridge` reach-through in the wrap-up so later packets can track it explicitly.
