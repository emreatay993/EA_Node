# PORT_VALUE_LOCKING P01: State Contract And Persistence

## Objective

- Add durable graph-model state for locked ports and per-view hidden-port toggles, plus the shared lockability helpers and persistence-safe round-trip coverage, without changing mutation semantics or QML behavior yet.

## Preconditions

- `P00` is complete and the packet set is registered in `.gitignore` and `docs/specs/INDEX.md`.
- The implementation base is current `main`.

## Execution Dependencies

- `PORT_VALUE_LOCKING_P00_bootstrap.md`

## Target Subsystems

- `ea_node_editor/graph/model.py`
- `ea_node_editor/graph/effective_ports.py`
- `ea_node_editor/graph/port_locking.py`
- `ea_node_editor/persistence/project_codec.py`
- `tests/test_port_locking.py`
- `tests/test_serializer.py`

## Conservative Write Scope

- `ea_node_editor/graph/model.py`
- `ea_node_editor/graph/effective_ports.py`
- `ea_node_editor/graph/port_locking.py`
- `ea_node_editor/persistence/project_codec.py`
- `tests/test_port_locking.py`
- `tests/test_serializer.py`
- `docs/specs/work_packets/port_value_locking/P01_state_contract_and_persistence_WRAPUP.md`
- `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_STATUS.md`

## Required Behavior

- Add `NodeInstance.locked_ports: dict[str, bool]` with mapping helpers that preserve authored keys during runtime and persistent document round trips.
- Add `ViewState.hide_locked_ports` and `ViewState.hide_optional_ports` with backward-compatible defaults of `False`.
- Keep snapshot, clone, and workspace/view restore flows compatible with the new node and view fields.
- Add `EffectivePort.locked` so later packets can project lock state through the resolved port surface without re-reading raw node maps in multiple places.
- Create `ea_node_editor/graph/port_locking.py` with the packet-owned shared helpers for lockability checks, trigger evaluation, and initial lock-map computation.
- Extend project codec view decode/encode behavior so the two new per-view toggles survive `.sfe` save/load without schema breakage for older documents.
- Add regression coverage that proves the new node/view state survives serializer round trip and model snapshot/restore.

## Non-Goals

- No creation-time auto-lock or property-edit auto-lock behavior yet.
- No connection rejection or edge pruning for locked ports yet.
- No scene command bridge, payload, or QML changes yet.
- No canvas gestures or view-filter payload suppression yet.

## Verification Commands

1. Full packet verification:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_port_locking.py tests/test_serializer.py --ignore=venv -q
```

## Review Gate

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_port_locking.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/port_value_locking/P01_state_contract_and_persistence_WRAPUP.md`
- `ea_node_editor/graph/model.py`
- `ea_node_editor/graph/effective_ports.py`
- `ea_node_editor/graph/port_locking.py`
- `ea_node_editor/persistence/project_codec.py`
- `tests/test_port_locking.py`
- `tests/test_serializer.py`

## Acceptance Criteria

- Node mappings and persistent documents preserve `locked_ports` without breaking older documents that omit the field.
- View mappings and persistent documents preserve `hide_locked_ports` and `hide_optional_ports`, defaulting missing values to `False`.
- `EffectivePort.locked` is available on the resolved port surface.
- The shared helper module exists and covers lockability plus initial-lock evaluation.
- The full packet verification command passes.
- The review gate passes.

## Handoff Notes

- Stop after `P01`. Do not start `P02` in the same thread.
- `P02` owns mutation semantics, creation/property auto-lock, backend connection rejection, and fragment preservation on top of this durable state.
