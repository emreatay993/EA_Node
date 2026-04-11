# PERSISTENT_NODE_ELAPSED_TIMES P07: Verification Docs Traceability Closeout

## Objective
- Update the retained node-execution QA matrix, requirements, and traceability evidence so the persistent elapsed-time extension closes on the canonical node-execution docs path instead of creating a competing closeout surface.

## Preconditions
- `P06` is marked `PASS` in [PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md](./PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md).
- No later `PERSISTENT_NODE_ELAPSED_TIMES` packet is in progress.

## Execution Dependencies
- `P06`

## Target Subsystems
- `docs/specs/perf/NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`
- `docs/specs/requirements/50_EXECUTION_ENGINE.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `tests/test_traceability_checker.py`

## Conservative Write Scope
- `docs/specs/perf/NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`
- `docs/specs/requirements/50_EXECUTION_ENGINE.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `tests/test_traceability_checker.py`
- `docs/specs/work_packets/persistent_node_elapsed_times/P07_verification_docs_traceability_closeout_WRAPUP.md`

## Required Behavior
- Update the retained `NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md` file instead of creating a new elapsed-time QA matrix.
- Refresh requirement and QA text to describe additive worker timing metadata, shell fallback timing, session-only per-workspace elapsed caching, execution-affecting invalidation, persistent cached footer behavior, and the continued no-`.sfe`-persistence constraint.
- Refresh traceability rows and packet-owned token checks so the persistent elapsed-time extension is represented on the canonical node-execution closeout path.
- Keep packet-owned commands and evidence aligned with the implementation packets from `P01` through `P06`, reusing those verification commands verbatim when they remain authoritative.
- Add or update packet-owned traceability tests so the verification commands below remain stable.

## Non-Goals
- No runtime, bridge, history, or QML code changes.
- No new QA matrix file.
- No repo-wide traceability reshuffle outside the packet-owned node-execution closeout surface.

## Verification Commands
1. `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q`
2. `.\venv\Scripts\python.exe scripts/check_traceability.py`

## Review Gate
- `.\venv\Scripts\python.exe scripts/check_traceability.py`

## Expected Artifacts
- `docs/specs/work_packets/persistent_node_elapsed_times/P07_verification_docs_traceability_closeout_WRAPUP.md`
- `docs/specs/perf/NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md`

## Acceptance Criteria
- The retained node-execution QA matrix and requirement docs describe the persistent elapsed-time extension without creating a second QA home.
- Traceability rows and packet-owned token tests reference the new elapsed-time commands, docs, and evidence coherently.
- `tests/test_traceability_checker.py` and `scripts/check_traceability.py` pass after the docs refresh.

## Handoff Notes
- This is the closeout packet for `PERSISTENT_NODE_ELAPSED_TIMES`; no later packet depends on it inside this set.
- If a later feature extends retained node-execution timing/visualization behavior again, it should reference this packet set and the retained QA matrix rather than creating a parallel elapsed-time closeout tree.
