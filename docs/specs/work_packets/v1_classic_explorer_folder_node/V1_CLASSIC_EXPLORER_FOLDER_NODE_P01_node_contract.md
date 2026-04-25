# V1_CLASSIC_EXPLORER_FOLDER_NODE P01: Node Contract

## Objective
- Add the passive built-in `io.folder_explorer` node contract under the existing file-I/O integration family, with a folder `current_path` property, a `current: Path` output, registry exposure, and focused persistence/runtime regressions.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and only source/test files needed for the node contract

## Preconditions
- `P00` is marked `PASS` in [V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md](./V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md).
- No later `V1_CLASSIC_EXPLORER_FOLDER_NODE` packet is in progress.

## Execution Dependencies
- none

## Target Subsystems
- `ea_node_editor/nodes/builtins/integrations_file_io.py`
- `ea_node_editor/nodes/builtins/integrations_common.py`
- `tests/test_integrations_track_f.py`
- `tests/test_passive_runtime_wiring.py`
- `tests/test_serializer.py`
- `tests/serializer/round_trip_cases.py`

## Conservative Write Scope
- `ea_node_editor/nodes/builtins/integrations_file_io.py`
- `ea_node_editor/nodes/builtins/integrations_common.py`
- `tests/test_integrations_track_f.py`
- `tests/test_passive_runtime_wiring.py`
- `tests/test_serializer.py`
- `tests/serializer/round_trip_cases.py`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/V1_CLASSIC_EXPLORER_FOLDER_NODE_STATUS.md`
- `docs/specs/work_packets/v1_classic_explorer_folder_node/P01_node_contract_WRAPUP.md`

## Source Public Entry Points
- Built-in descriptor export through `FILE_IO_NODE_DESCRIPTORS`.
- Registry-visible type id `io.folder_explorer`.
- Node property key `current_path`.
- Output port key `current` with semantic type `Path`.

## Regression Public Entry Points
- File-I/O integration tests for builtin descriptor shape and runtime value behavior.
- Passive runtime wiring tests proving the folder explorer remains outside flattened execution flow.
- Serializer round-trip tests proving `current_path` persists as project-semantic node data.

## State Owner
- The node spec owns persistent semantic state: `current_path`.
- Transient Explorer UI state remains out of this packet and out of project persistence.

## Allowed Dependencies
- Existing node spec, registry, and built-in integration helper APIs.
- Standard-library filesystem validation only when needed for `current_path` runtime validation.

## Required Behavior
- Define `io.folder_explorer` as a passive built-in file-I/O integration node.
- Add a folder-path property named `current_path`.
- Add an output port named `current` with semantic type `Path`.
- Register the descriptor through the existing file-I/O built-in descriptor chain.
- Preserve the authored `current_path` string through project serialization.

## Required Invariants
- `io.folder_explorer` is `runtime_behavior="passive"`.
- The node belongs to the existing file-I/O integration family and does not add graph-layer imports from UI or persistence.
- `current_path` accepts folder paths and preserves the authored string in project documents.
- Missing or invalid folders report validation/runtime errors consistently with existing path-pointer helpers rather than mutating the filesystem.
- `current` yields the current folder path when the passive value is queried through existing node plugin behavior.

## Non-Goals
- No Explorer QML surface.
- No filesystem listing service or mutation service.
- No shell/library/inspector exposure beyond descriptor availability.

## Forbidden Shortcuts
- Do not implement the Explorer UI in this packet.
- Do not add filesystem mutations in this packet.
- Do not add public graph raw-write helpers.
- Do not persist navigation history, search text, sort settings, selection, or maximized state.

## Required Tests
- Add or extend file-I/O integration tests for descriptor id, properties, output port, folder-only semantics, and current-path value behavior.
- Add or extend passive runtime tests proving the node is excluded from runtime execution edges.
- Add serializer round-trip coverage for a graph containing `io.folder_explorer` with `current_path`.

## Verification Anchor Handoff
- Later packets that rename `io.folder_explorer`, `current_path`, or `current` must inherit and update `tests/test_integrations_track_f.py`, `tests/test_passive_runtime_wiring.py`, and serializer round-trip coverage.
- Later packets may add UI tests without changing these domain assertions when the node contract stays stable.

## Verification Commands
1. `.\venv\Scripts\python.exe -m pytest tests/test_integrations_track_f.py tests/test_passive_runtime_wiring.py tests/test_serializer.py --ignore=venv -q`

## Review Gate
- `.\venv\Scripts\python.exe -m pytest tests/test_integrations_track_f.py -k folder_explorer --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/v1_classic_explorer_folder_node/P01_node_contract_WRAPUP.md`

## Acceptance Criteria
- `io.folder_explorer` appears in the built-in registry through the file-I/O integration family.
- The node has a folder path property named `current_path` and an output port named `current`.
- Passive runtime behavior is preserved and covered by regression tests.
- Serializer round trips preserve `current_path` without adding transient Explorer UI state.

## Handoff Notes
- `P02` may add filesystem listing and mutation services, but must not change the node type id or persistent property names without inheriting and updating this packet's tests.
- Later UI packets consume this node contract through existing registry and bridge payloads.
