# UI_CONTEXT_SCALABILITY_FOLLOWUP P09: Verification Docs Closeout

## Objective

- Publish QA evidence, register the follow-up packet set, and align traceability and verification docs with the expanded guardrails and packet contracts.

## Preconditions

- `P00` is marked `PASS` in [UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md](./UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md).
- No later `UI_CONTEXT_SCALABILITY_FOLLOWUP` packet is in progress.

## Execution Dependencies

- `P08`

## Target Subsystems

- `docs/specs/perf/UI_CONTEXT_SCALABILITY_FOLLOWUP_QA_MATRIX.md`
- `docs/specs/INDEX.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `tests/test_traceability_checker.py`
- `tests/test_markdown_hygiene.py`
- `tests/test_run_verification.py`

## Conservative Write Scope

- `docs/specs/perf/UI_CONTEXT_SCALABILITY_FOLLOWUP_QA_MATRIX.md`
- `docs/specs/INDEX.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `tests/test_traceability_checker.py`
- `tests/test_markdown_hygiene.py`
- `tests/test_run_verification.py`
- `docs/specs/work_packets/ui_context_scalability_followup/P09_verification_docs_closeout_WRAPUP.md`

## Required Behavior

- Add `docs/specs/perf/UI_CONTEXT_SCALABILITY_FOLLOWUP_QA_MATRIX.md` as the published closeout audit for this packet set.
- Update `docs/specs/INDEX.md` so the follow-up manifest, status ledger, and QA matrix are registered together.
- Update `docs/specs/requirements/90_QA_ACCEPTANCE.md` and `docs/specs/requirements/TRACEABILITY_MATRIX.md` so the follow-up guardrails, packet docs, and QA matrix are treated as retained proof artifacts.
- Update `tests/test_traceability_checker.py`, `tests/test_markdown_hygiene.py`, and `tests/test_run_verification.py` so the closeout docs and verification facts are asserted automatically.
- Preserve the earlier packet proof commands rather than inventing a new omnibus proof workflow here.

## Non-Goals

- No more source refactors.
- No more regression-suite refactors.
- No new verification modes beyond documenting and asserting the retained proof path.

## Verification Commands

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py tests/test_markdown_hygiene.py tests/test_run_verification.py --ignore=venv -q
.\venv\Scripts\python.exe scripts/check_traceability.py
.\venv\Scripts\python.exe scripts/check_markdown_links.py
```

## Review Gate

```powershell
.\venv\Scripts\python.exe scripts/check_traceability.py
```

## Expected Artifacts

- `docs/specs/work_packets/ui_context_scalability_followup/P09_verification_docs_closeout_WRAPUP.md`
- `docs/specs/perf/UI_CONTEXT_SCALABILITY_FOLLOWUP_QA_MATRIX.md`

## Acceptance Criteria

- The follow-up QA matrix is published and registered in the canonical spec index.
- QA acceptance and traceability docs point at the expanded guardrails and packet docs.
- Packet-owned traceability, markdown, and verification metadata checks pass.

## Handoff Notes

- This packet set is complete when `P09` is `PASS` and the workflow is ready for merge into `main`.
