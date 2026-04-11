# PORT_VALUE_LOCKING P06: Verification Docs Traceability Closeout

## Objective

- Publish the retained QA matrix, requirement updates, and traceability closeout for the shipped port value locking feature without reopening product code.

## Preconditions

- `P05` is complete and accepted.
- The packet branch starts from the current accepted packet-set integration base.

## Execution Dependencies

- `PORT_VALUE_LOCKING_P05_canvas_hide_gestures.md`

## Target Subsystems

- `docs/specs/INDEX.md`
- `docs/specs/perf/PORT_VALUE_LOCKING_QA_MATRIX.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `tests/test_traceability_checker.py`

## Conservative Write Scope

- `docs/specs/INDEX.md`
- `docs/specs/perf/PORT_VALUE_LOCKING_QA_MATRIX.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `tests/test_traceability_checker.py`
- `docs/specs/work_packets/port_value_locking/P06_verification_docs_traceability_closeout_WRAPUP.md`
- `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_STATUS.md`

## Required Behavior

- Add `docs/specs/perf/PORT_VALUE_LOCKING_QA_MATRIX.md` with automated and manual evidence aligned to the shipped packet behavior, including one-way auto-lock, locked incoming-edge rejection, manual lock toggle, per-view hide filters, canvas gestures, persistence, and undo/redo.
- Update the tracked-work-packet index with a QA-matrix link for `PORT_VALUE_LOCKING`.
- Update requirement docs so the locked primitive-port behavior, per-view decluttering controls, and persistence/verification expectations are captured in the canonical spec pack.
- Update the traceability matrix entries for the affected requirements.
- Extend `tests/test_traceability_checker.py` only as needed so the retained requirement and matrix changes are enforced.
- Keep this packet documentation-only; it must not reopen any product-source or test-seam changes outside the listed docs and traceability anchor.

## Non-Goals

- No changes under `ea_node_editor/**`.
- No QML or bridge changes.
- No new runtime or persistence behavior beyond the retained documentation evidence.

## Verification Commands

1. Full packet verification:

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

- `docs/specs/work_packets/port_value_locking/P06_verification_docs_traceability_closeout_WRAPUP.md`
- `docs/specs/INDEX.md`
- `docs/specs/perf/PORT_VALUE_LOCKING_QA_MATRIX.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `tests/test_traceability_checker.py`

## Acceptance Criteria

- The QA matrix exists and captures both automated and manual verification evidence for the shipped feature set.
- Requirements and traceability docs mention locked primitive ports, one-way auto-lock, locked incoming-edge rejection, per-view hide toggles, and the empty-canvas gestures.
- The traceability pytest and script both pass.
- No product-source files outside the docs closeout scope are modified.

## Handoff Notes

- Stop after `P06`. Do not start any new packet in the same thread.
- When `P06` passes, the packet set is ready for merge-readiness reporting and user-triggered integration.
