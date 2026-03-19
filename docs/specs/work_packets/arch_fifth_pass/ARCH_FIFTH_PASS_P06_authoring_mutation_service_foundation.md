# ARCH_FIFTH_PASS P06: Authoring Mutation Service Foundation

## Objective
- Introduce the authoritative authoring mutation service and route the primary graph edit flows through it so graph invariants are enforced from one boundary instead of by scattered call-site discipline.

## Preconditions
- `P05` is marked `PASS` in [ARCH_FIFTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_STATUS.md).
- No later `ARCH_FIFTH_PASS` packet is in progress.

## Execution Dependencies
- `P05`

## Target Subsystems
- graph mutation boundary and validated authoring rules
- shell/controller edit flows
- scene-bridge mutation entrypoints

## Conservative Write Scope
- `ea_node_editor/graph/model.py`
- `ea_node_editor/graph/mutation_service.py`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/ui/graph_interactions.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui/shell/controllers/workspace_edit_ops.py`
- `ea_node_editor/ui/shell/controllers/workspace_drop_connect_ops.py`
- `ea_node_editor/ui/shell/controllers/workspace_view_nav_ops.py`
- `tests/test_graph_track_b.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/test_graph_scene_bridge_bind_regression.py`
- `docs/specs/work_packets/arch_fifth_pass/P06_authoring_mutation_service_foundation_WRAPUP.md`

## Required Behavior
- Add `WorkspaceMutationService` as the packet-owned authoritative write boundary for graph authoring state.
- Route primary node/edge/property/title/collapse/position/view edit flows through the mutation service rather than raw `GraphModel` calls from packet-owned UI/controller entrypoints.
- Keep `GraphModel` raw mutators available as internal compatibility helpers in this packet, but remove direct use of them from the packet-owned edit flows listed above.
- Preserve all current validation, normalization, and user-visible edit behavior exactly.

## Non-Goals
- No transform/ungroup/payload-builder cleanup in this packet; `P07` owns that.
- No persistence overlay or runtime snapshot work in this packet.
- No intentional behavior change to graph-edit leniency or error messaging.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_track_b.py tests/test_workspace_library_controller_unit.py tests/test_graph_scene_bridge_bind_regression.py -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_scene_bridge_bind_regression.py -q`

## Expected Artifacts
- `docs/specs/work_packets/arch_fifth_pass/P06_authoring_mutation_service_foundation_WRAPUP.md`

## Acceptance Criteria
- Packet-owned primary graph edit flows no longer mutate `GraphModel` directly.
- The new mutation service becomes the required entry boundary for the packet-owned edit flows listed above.
- Existing graph behavior and validation outcomes remain unchanged, and packet verification passes.

## Handoff Notes
- `P07` completes transform/payload/history cleanup on top of this service. Keep this packet focused on the foundational edit flows only.
- Preserve compatibility behavior for packet-external callers that still use raw `GraphModel` methods.
