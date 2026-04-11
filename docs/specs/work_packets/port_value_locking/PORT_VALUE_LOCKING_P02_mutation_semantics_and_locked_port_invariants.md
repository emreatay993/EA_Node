# PORT_VALUE_LOCKING P02: Mutation Semantics And Locked Port Invariants

## Objective

- Make locked-port state meaningful in validated graph mutations by owning creation/property auto-lock, manual lock mutation, locked-target connection rejection, incoming-edge pruning, and fragment preservation before any payload or QML surface adopts the feature.

## Preconditions

- `P01` is complete and accepted.
- The packet branch starts from the current accepted packet-set integration base.

## Execution Dependencies

- `PORT_VALUE_LOCKING_P01_state_contract_and_persistence.md`

## Target Subsystems

- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/graph/mutation_service.py`
- `ea_node_editor/graph/transform_fragment_ops.py`
- `ea_node_editor/ui/graph_interactions.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/selection_and_scope_ops.py`
- `tests/test_port_locking.py`
- `tests/graph_track_b/scene_model_graph_scene_suite.py`

## Conservative Write Scope

- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/graph/mutation_service.py`
- `ea_node_editor/graph/transform_fragment_ops.py`
- `ea_node_editor/ui/graph_interactions.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/selection_and_scope_ops.py`
- `tests/test_port_locking.py`
- `tests/graph_track_b/scene_model_graph_scene_suite.py`
- `docs/specs/work_packets/port_value_locking/P02_mutation_semantics_and_locked_port_invariants_WRAPUP.md`
- `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_STATUS.md`

## Required Behavior

- Thread `locked_ports` through validated `add_node` and low-level record writers so newly created nodes can retain a caller-supplied lock map.
- Compute initial locked ports at node creation from normalized default properties via the packet-owned helper module.
- Add validated `set_locked_port` mutation support for lockable ports and reject non-lockable targets.
- Apply one-way auto-lock during `set_node_property` and `set_node_properties`: meaningful values may lock an unlocked lockable port, but cleared values never auto-unlock.
- Prune incoming edges that become illegal when a target port is manually locked or auto-locked.
- Reject new connection attempts to locked target ports from both validated mutation paths and `GraphInteractions.connect_ports()`, with a user-facing reason aligned to the review baseline.
- Preserve `locked_ports` through graph-fragment serialization and restore paths so duplication/copy flows do not silently drop lock state.
- Add regression coverage for auto-lock semantics, manual overrides, connection rejection, edge pruning, and fragment preservation.

## Non-Goals

- No payload projection or port-row filtering yet.
- No scene command bridge slots yet.
- No QML locked-port visuals or double-click gesture routing yet.
- No canvas-wide hide gestures yet.

## Verification Commands

1. Full packet verification:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_port_locking.py tests/graph_track_b/scene_model_graph_scene_suite.py --ignore=venv -q
```

## Review Gate

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_port_locking.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/port_value_locking/P02_mutation_semantics_and_locked_port_invariants_WRAPUP.md`
- `ea_node_editor/graph/normalization.py`
- `ea_node_editor/graph/mutation_service.py`
- `ea_node_editor/graph/transform_fragment_ops.py`
- `ea_node_editor/ui/graph_interactions.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/selection_and_scope_ops.py`
- `tests/test_port_locking.py`
- `tests/graph_track_b/scene_model_graph_scene_suite.py`

## Acceptance Criteria

- Creation-time default values can seed `locked_ports`.
- Property edits auto-lock only in the lock-triggering direction and never auto-unlock.
- Manual lock mutation rejects non-lockable ports and prunes newly illegal incoming edges.
- Locked target ports are rejected by backend connection entry points with a user-facing failure reason.
- Fragment serialization and restore preserve lock state.
- The full packet verification command passes.
- The review gate passes.

## Handoff Notes

- Stop after `P02`. Do not start `P03` in the same thread.
- `P03` owns scene bridge slots, payload flags, and view-filter state mutations on top of these backend invariants.
