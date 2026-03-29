# CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK P06: Verification Docs Traceability Closeout

## Objective

- Publish the QA matrix and requirement-traceability updates for the cross-process viewer backend framework after the implementation packets complete.

## Preconditions

- `P01` through `P05` are complete and their wrap-ups or status entries record the accepted implementation state.
- The implementation base is current `main`.

## Execution Dependencies

- `P01`
- `P02`
- `P03`
- `P04`
- `P05`

## Target Subsystems

- `docs/specs/INDEX.md`
- `docs/specs/perf/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md`
- `docs/specs/requirements/10_ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`
- `docs/specs/requirements/50_EXECUTION_ENGINE.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/70_INTEGRATIONS.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `tests/test_traceability_checker.py`

## Conservative Write Scope

- `docs/specs/INDEX.md`
- `docs/specs/perf/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md`
- `docs/specs/requirements/10_ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`
- `docs/specs/requirements/50_EXECUTION_ENGINE.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/70_INTEGRATIONS.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `tests/test_traceability_checker.py`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/P06_verification_docs_traceability_closeout_WRAPUP.md`
- `docs/specs/work_packets/cross_process_viewer_backend_framework/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md`

## Required Behavior

- Create `docs/specs/perf/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md` covering automated verification, manual `dene3.sfe` checks, and residual desktop-only validation for run, reopen, rerun, binder cleanup, and transport lifecycle behavior.
- Update `docs/specs/INDEX.md` to include the new QA matrix link.
- Update packet-owned requirement docs to describe the generic execution backend and shell binder framework, session-scoped temp transport contract, explicit run-required reopen behavior, and the rule that live transport data does not persist into `.sfe`.
- Update `docs/specs/requirements/TRACEABILITY_MATRIX.md` so the feature maps to its implementation and verification surfaces.
- Refresh `tests/test_traceability_checker.py` only as needed to reflect the new packet-owned requirement and QA-matrix references.
- Keep the documentation aligned with the locked defaults: worker-side DPF authority, UI-side widget hosting only, registry-driven backend or binder surfaces, internal temp transport for live viewing, and rerun-required live reopen after project load.

## Non-Goals

- No product-code changes under `ea_node_editor/**`.
- No new runtime behavior beyond documenting the already-implemented state from `P01` through `P05`.
- No new packet planning docs outside the explicit QA-matrix and closeout artifacts above.

## Verification Commands

1. Traceability pytest:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q
```

2. Traceability script:

```powershell
.\venv\Scripts\python.exe scripts/check_traceability.py
```

## Review Gate

```powershell
.\venv\Scripts\python.exe scripts/check_traceability.py
```

## Expected Artifacts

- `docs/specs/work_packets/cross_process_viewer_backend_framework/P06_verification_docs_traceability_closeout_WRAPUP.md`
- `docs/specs/INDEX.md`
- `docs/specs/perf/CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_QA_MATRIX.md`
- `docs/specs/requirements/10_ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`
- `docs/specs/requirements/50_EXECUTION_ENGINE.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/70_INTEGRATIONS.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `tests/test_traceability_checker.py`

## Acceptance Criteria

- The QA matrix exists and is linked from `docs/specs/INDEX.md`.
- Requirement and traceability docs reflect the shipped cross-process viewer backend behavior and its locked defaults.
- The traceability pytest command passes.
- The review gate passes with `TRACEABILITY CHECK PASS`.

## Handoff Notes

- Stop after `P06`; this is the packet-set closeout.
- If a future packet changes this behavior, that later packet must inherit and refresh the requirement and QA evidence it invalidates.
