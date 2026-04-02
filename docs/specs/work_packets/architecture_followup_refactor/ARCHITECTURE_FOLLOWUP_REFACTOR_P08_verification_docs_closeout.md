# ARCHITECTURE_FOLLOWUP_REFACTOR P08: Verification Docs Closeout

## Objective

- Publish the final architecture follow-up QA evidence, update requirement or traceability anchors, and close the packet set with focused proof artifacts instead of expanding legacy documentation machinery.

## Preconditions

- `P07` is marked `PASS` in [ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md](./ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_FOLLOWUP_REFACTOR` packet is in progress.

## Execution Dependencies

- `P07`

## Target Subsystems

- `ARCHITECTURE.md`
- `docs/specs/INDEX.md`
- `docs/specs/perf/ARCHITECTURE_FOLLOWUP_REFACTOR_QA_MATRIX.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `scripts/check_traceability.py`
- `tests/test_architecture_boundaries.py`
- `tests/test_markdown_hygiene.py`
- `tests/test_traceability_checker.py`

## Conservative Write Scope

- `ARCHITECTURE.md`
- `docs/specs/INDEX.md`
- `docs/specs/perf/ARCHITECTURE_FOLLOWUP_REFACTOR_QA_MATRIX.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `scripts/check_traceability.py`
- `tests/test_architecture_boundaries.py`
- `tests/test_markdown_hygiene.py`
- `tests/test_traceability_checker.py`
- `docs/specs/work_packets/architecture_followup_refactor/P08_verification_docs_closeout_WRAPUP.md`

## Required Behavior

- Publish `docs/specs/perf/ARCHITECTURE_FOLLOWUP_REFACTOR_QA_MATRIX.md` as the packet-set closeout artifact.
- Update `docs/specs/INDEX.md` to register the QA matrix alongside the manifest and status ledger.
- Update architecture and requirement or traceability docs so the final packet-owned architecture state is discoverable from the canonical spec pack.
- Keep the proof surface focused to this packet set's retained artifacts and avoid introducing new broad token-audit machinery outside packet scope.
- Update inherited architecture-boundary, markdown-hygiene, and traceability regression anchors in place where this packet changes those contracts.

## Non-Goals

- No new feature work.
- No additional packet planning docs outside the wrap-up artifact.
- No repo-wide verification expansion beyond the packet-owned proof required here.

## Verification Commands

1. Targeted regression proof:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_traceability_checker.py tests/test_markdown_hygiene.py --ignore=venv -q
```

2. Traceability proof:

```powershell
.\venv\Scripts\python.exe scripts/check_traceability.py
```

3. Markdown-link proof:

```powershell
.\venv\Scripts\python.exe scripts/check_markdown_links.py
```

## Review Gate

```powershell
.\venv\Scripts\python.exe scripts/check_traceability.py
```

## Expected Artifacts

- `docs/specs/work_packets/architecture_followup_refactor/P08_verification_docs_closeout_WRAPUP.md`
- `docs/specs/perf/ARCHITECTURE_FOLLOWUP_REFACTOR_QA_MATRIX.md`

## Acceptance Criteria

- The QA matrix exists and is registered in the canonical spec index.
- Architecture, QA-acceptance, and traceability anchors reflect the final packet-owned architecture state.
- All packet verification commands pass.
- The review gate passes.

## Handoff Notes

- Stop after `P08`. Do not start any new packet set in the same thread.
- After `P08` passes, the packet set is ready for executor-driven merge-readiness reporting.
