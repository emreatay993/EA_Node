# SHARED_GRAPH_TYPOGRAPHY_CONTROL P07: Verification Docs Traceability Closeout

## Objective
- Publish the retained QA matrix and requirement-traceability updates for the shared graph typography control after implementation proof is complete.

## Preconditions
- `P01` through `P06` are complete and their wrap-ups/status entries record the accepted implementation state.
- The implementation base is current `main`.

## Execution Dependencies
- `P01`
- `P02`
- `P03`
- `P04`
- `P05`
- `P06`

## Target Subsystems
- `docs/specs/INDEX.md`
- `docs/specs/perf/SHARED_GRAPH_TYPOGRAPHY_CONTROL_QA_MATRIX.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `tests/test_traceability_checker.py`

## Conservative Write Scope
- `docs/specs/INDEX.md`
- `docs/specs/perf/SHARED_GRAPH_TYPOGRAPHY_CONTROL_QA_MATRIX.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `tests/test_traceability_checker.py`
- `docs/specs/work_packets/shared_graph_typography_control/P07_verification_docs_traceability_closeout_WRAPUP.md`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md`

## Required Behavior
- Create `docs/specs/perf/SHARED_GRAPH_TYPOGRAPHY_CONTROL_QA_MATRIX.md` covering the retained automated verification from `P01` through `P06`, concise manual desktop checks, and residual desktop-only validation for the feature.
- Update `docs/specs/INDEX.md` to include the new QA matrix link.
- Update packet-owned requirement docs to describe the shipped app-global typography preference, the shared graph typography role contract, passive-authoritative override precedence, and the deterministic metric-alignment constraint.
- Update `docs/specs/requirements/TRACEABILITY_MATRIX.md` so the feature maps to its implementation and verification surfaces.
- Refresh `tests/test_traceability_checker.py` only as needed to reflect the new packet-owned requirement and QA-matrix references.
- Keep the documentation aligned with the locked defaults: default `10`, clamp range `8..18`, app-global-only control, no graph-theme typography schema, no `.sfe` persistence expansion, passive-authoritative overrides where already wired, and no second typography-only invalidation channel.
- Explicitly retain the dependent `PERSISTENT_NODE_ELAPSED_TIMES` precedent in the QA matrix notes for the elapsed-footer typography surface so future follow-up work does not reopen worker timing or cache invalidation contracts accidentally.

## Non-Goals
- No product-code changes under `ea_node_editor/**`.
- No new renderer behavior beyond documenting the already-implemented state from `P01` through `P06`.
- No new packet planning docs outside the explicit QA matrix and closeout artifacts above.

## Verification Commands
1. `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q`
2. `.\venv\Scripts\python.exe scripts/check_traceability.py`

## Review Gate
- `.\venv\Scripts\python.exe scripts/check_traceability.py`

## Expected Artifacts
- `docs/specs/work_packets/shared_graph_typography_control/P07_verification_docs_traceability_closeout_WRAPUP.md`
- `docs/specs/INDEX.md`
- `docs/specs/perf/SHARED_GRAPH_TYPOGRAPHY_CONTROL_QA_MATRIX.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `tests/test_traceability_checker.py`

## Acceptance Criteria
- The QA matrix exists and is linked from `docs/specs/INDEX.md`.
- Requirement and traceability docs reflect the shipped shared graph typography behavior and its locked defaults.
- The traceability pytest command passes.
- The review gate passes with `TRACEABILITY CHECK PASS`.

## Handoff Notes
- Stop after `P07`; this is the packet-set closeout.
- If a future packet changes this behavior, that later packet must inherit and refresh the requirement and QA evidence it invalidates.
