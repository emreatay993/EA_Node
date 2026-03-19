# ARCH_FIFTH_PASS P07: Authoring Mutation Completion And History

## Objective
- Finish the mutation-boundary cleanup by routing transform/payload-normalization writes through the mutation service and expanding undo/redo capture to the full mutable workspace state.

## Preconditions
- `P06` is marked `PASS` in [ARCH_FIFTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_STATUS.md).
- No later `ARCH_FIFTH_PASS` packet is in progress.

## Execution Dependencies
- `P06`

## Target Subsystems
- graph transforms and scope/group operations
- payload-builder normalization behavior
- runtime history capture/restore completeness

## Conservative Write Scope
- `ea_node_editor/graph/model.py`
- `ea_node_editor/graph/mutation_service.py`
- `ea_node_editor/graph/transforms.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui/shell/runtime_history.py`
- `tests/test_graph_track_b.py`
- `tests/test_passive_visual_metadata.py`
- `tests/test_passive_runtime_wiring.py`
- `tests/test_graph_surface_input_contract.py`
- `docs/specs/work_packets/arch_fifth_pass/P07_authoring_mutation_completion_history_WRAPUP.md`

## Required Behavior
- Route group/ungroup and other packet-owned graph transforms through the mutation service instead of raw `GraphModel` calls.
- Remove packet-owned model writes from payload rebuild/normalization paths so payload building becomes read-only with respect to graph state.
- Expand runtime history capture/restore so it covers the full mutable workspace state that still lives in the live model after `P06`.
- Preserve exact graph-edit behavior, graph-surface behavior, and history semantics from the user point of view.

## Non-Goals
- No persistence overlay extraction yet; `P08` owns that.
- No runtime snapshot or worker-boundary changes in this packet.
- No packet-owned UI redesign or graph-surface contract change.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_track_b.py tests/test_passive_visual_metadata.py tests/test_passive_runtime_wiring.py tests/test_graph_surface_input_contract.py -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_track_b.py -q -k "RuntimeGraphHistoryTrackBTests"`

## Expected Artifacts
- `docs/specs/work_packets/arch_fifth_pass/P07_authoring_mutation_completion_history_WRAPUP.md`

## Acceptance Criteria
- Packet-owned transform flows and payload normalization no longer mutate live model state outside the mutation service.
- Undo/redo restores the full mutable workspace state still owned by the live model after this packet.
- Graph, passive-surface, and history regressions remain unchanged from the user/test perspective, and packet verification passes.

## Handoff Notes
- `P08` removes persistence-only overlay state from the live model. Keep this packet scoped to the state that still belongs there today.
- Document any remaining direct raw-mutation call sites that are intentionally left for packet-external compatibility.
