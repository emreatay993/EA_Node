# COREX_CLEAN_ARCHITECTURE_RESTRUCTURE P01: Runtime Contracts

## Objective

Make `runtime_contracts` the passive, process-neutral runtime boundary and remove contract-layer dependencies back into execution behavior.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and only source files needed for this packet

## Preconditions

- `P00_bootstrap` is `PASS`.
- No sibling packet branch has been used as this packet's base.

## Execution Dependencies

none

## Target Subsystems

- Runtime contract DTOs and serialization helpers
- Execution protocol DTOs and worker/viewer command-event payloads
- Architecture boundary tests for contract import direction

## Conservative Write Scope

- `ea_node_editor/runtime_contracts/**`
- `ea_node_editor/execution/runtime_value_codec.py`
- `ea_node_editor/execution/runtime_dto.py`
- `ea_node_editor/execution/runtime_snapshot.py`
- `ea_node_editor/execution/protocol.py`
- `tests/test_execution_viewer_protocol.py`
- `tests/test_architecture_boundaries.py`
- `tests/test_dead_code_hygiene.py`
- `docs/specs/work_packets/corex_clean_architecture_restructure/P01_runtime_contracts_WRAPUP.md`

## Required Behavior

- Move or re-home neutral runtime value codec behavior so `runtime_contracts` does not import execution implementation.
- Clarify which DTOs are contracts and which modules own assembly, compilation, process execution, cancellation, and viewer state machines.
- Preserve runtime snapshot wire shape, worker protocol behavior, viewer command/event round trips, and public runtime ref helpers.
- Add or update architecture guards that make the new import direction enforceable.

## Non-Goals

- Do not rewrite the worker runtime, compiler, or viewer session service behavior.
- Do not change `.sfe` persistence shape.
- Do not alter QML bridge call sites except where a contract import path must be updated.

## Verification Commands

- `.\venv\Scripts\python.exe -m pytest tests/test_execution_viewer_protocol.py tests/test_architecture_boundaries.py --ignore=venv`
- `.\venv\Scripts\python.exe -m pytest tests/test_dead_code_hygiene.py --ignore=venv`

## Review Gate

- `.\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py --ignore=venv`

## Expected Artifacts

- `docs/specs/work_packets/corex_clean_architecture_restructure/P01_runtime_contracts_WRAPUP.md`

## Acceptance Criteria

- Contract modules are passive and do not depend on execution implementation modules.
- Runtime refs, viewer event payloads, and worker/viewer command DTOs remain compatible.
- Verification commands pass or the wrap-up records a terminal failure with residual risk.

## Handoff Notes

If implementation discovers that moving protocol DTOs would cascade into UI or worker behavior, keep DTO location changes minimal and prioritize import-direction guardrails over broad file moves.
