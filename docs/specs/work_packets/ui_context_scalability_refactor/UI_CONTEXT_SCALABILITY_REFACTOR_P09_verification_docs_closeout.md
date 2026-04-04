# UI_CONTEXT_SCALABILITY_REFACTOR P09: Verification Docs Closeout

## Objective

- Close the packet set with QA evidence, spec-index updates, and traceability or verification docs that point future work at the new budgets and packet contracts.

## Preconditions

- `P00` is marked `PASS` in [UI_CONTEXT_SCALABILITY_REFACTOR_STATUS.md](./UI_CONTEXT_SCALABILITY_REFACTOR_STATUS.md).
- No later `UI_CONTEXT_SCALABILITY_REFACTOR` packet is in progress.

## Execution Dependencies

- `P08`

## Target Subsystems

- `docs/specs/INDEX.md`
- `docs/specs/perf/UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `scripts/check_traceability.py`
- `tests/test_traceability_checker.py`
- `tests/test_markdown_hygiene.py`
- `tests/test_run_verification.py`

## Conservative Write Scope

- `docs/specs/INDEX.md`
- `docs/specs/perf/UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `scripts/check_traceability.py`
- `tests/test_traceability_checker.py`
- `tests/test_markdown_hygiene.py`
- `tests/test_run_verification.py`
- `docs/specs/work_packets/ui_context_scalability_refactor/P09_verification_docs_closeout_WRAPUP.md`

## Required Behavior

- Publish `docs/specs/perf/UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX.md` as the retained QA evidence for this packet set.
- Update the canonical spec index to include the QA matrix.
- Update QA acceptance and traceability docs so packet-owned context budgets and subsystem packet contracts are part of the documented verification story.
- Extend packet-owned traceability or verification checks only where needed to keep the new closeout evidence structural and non-brittle.
- Keep the proof packet-scoped; do not expand to broad unrelated release or packaging evidence.

## Non-Goals

- No further product refactors.
- No new feature packets beyond the subsystem docs and closeout evidence already defined by earlier packets.
- No repo-wide documentation cleanup outside the packet-owned verification story.

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

- `docs/specs/work_packets/ui_context_scalability_refactor/P09_verification_docs_closeout_WRAPUP.md`
- `docs/specs/perf/UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX.md`

## Acceptance Criteria

- The packet set has a retained QA matrix registered in the canonical spec index.
- QA acceptance and traceability docs point future UI work at the context-budget and packet-contract guardrails.
- The packet-owned traceability and markdown proof passes.

## Handoff Notes

- This packet closes the `UI_CONTEXT_SCALABILITY_REFACTOR` packet set.
