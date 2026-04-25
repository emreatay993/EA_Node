# COREX_CLEAN_ARCHITECTURE_RESTRUCTURE P02: Graph Domain Mutation

## Objective

Make graph domain state and mutation ownership explicit: passive state objects stay passive, `GraphModel` remains the aggregate root/factory, and semantic graph changes flow through one validated mutation boundary.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and graph/test files needed for this packet

## Preconditions

- `P00_bootstrap` is `PASS`.
- `P01_runtime_contracts` is `PASS`.

## Execution Dependencies

- `P01_runtime_contracts`

## Target Subsystems

- Graph model and normalization
- Graph mutation service
- Graph transform/fragment/grouping operations
- Graph regression and architecture boundary tests

## Conservative Write Scope

- `ea_node_editor/graph/**`
- `tests/test_graph*.py`
- `tests/graph_surface/**`
- `tests/graph_track_b/**`
- `tests/test_architecture_boundaries.py`
- `docs/specs/work_packets/corex_clean_architecture_restructure/P02_graph_domain_mutation_WRAPUP.md`

## Required Behavior

- Centralize semantic node/edge/view mutations behind validated mutation services.
- Reduce or retire raw public graph mutation entry points where production code no longer uses them.
- Centralize dirty marking, active-view fallback, and default-view repair.
- Preserve graph document shape, view-local behavior, hierarchy-aware graph operations, and passive-node persistence semantics.

## Non-Goals

- Do not refactor persistence serialization beyond graph-facing API updates.
- Do not change QML graph-canvas behavior.
- Do not rename public graph facade exports without explicit compatibility handling.

## Verification Commands

- `.\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_graph_surface_input_contract.py tests/test_graph_track_b.py --ignore=venv`
- `.\venv\Scripts\python.exe -m pytest tests/test_graph*.py --ignore=venv`

## Review Gate

- `.\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py --ignore=venv`

## Expected Artifacts

- `docs/specs/work_packets/corex_clean_architecture_restructure/P02_graph_domain_mutation_WRAPUP.md`

## Acceptance Criteria

- Graph mutation ownership is enforceable and documented in tests or architecture guards.
- Existing graph behavior remains compatible.
- Verification commands pass or the wrap-up records a terminal failure with residual risk.

## Handoff Notes

If a later packet must update an inherited graph assertion, that packet owns the inherited regression anchor and must include the test file in its write scope.
