# EXECUTION_EDGE_PROGRESS_VISUALIZATION P05: Verification Docs Traceability Closeout

## Objective
- Update the retained node execution QA matrix, requirements, and traceability evidence so the execution-edge progress extension closes on the canonical node execution docs path instead of forking a second closeout surface.

## Preconditions
- `P04` is marked `PASS` in [EXECUTION_EDGE_PROGRESS_VISUALIZATION_STATUS.md](./EXECUTION_EDGE_PROGRESS_VISUALIZATION_STATUS.md).
- No later `EXECUTION_EDGE_PROGRESS_VISUALIZATION` packet is in progress.

## Execution Dependencies
- `P04`

## Target Subsystems
- `docs/specs/perf/NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `tests/test_traceability_checker.py`

## Conservative Write Scope
- `docs/specs/perf/NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `tests/test_traceability_checker.py`
- `docs/specs/work_packets/execution_edge_progress_visualization/P05_verification_docs_traceability_closeout_WRAPUP.md`

## Required Behavior
- Update the retained `NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md` file instead of creating a new QA matrix.
- Extend the retained node execution requirement and QA text to mention authored control-edge progress visualization, dim-before-progress behavior, the `240ms` flash, `node_failed_handled`, active-workspace filtering, and the no-persistence constraint.
- Refresh traceability rows and packet-owned token checks so the execution-edge extension is represented on the canonical node execution closeout path.
- Keep packet-owned commands and evidence aligned with the earlier implementation packets, especially the verification commands from `P01` through `P04`.
- Add or update packet-owned traceability tests so the verification commands below remain stable.

## Non-Goals
- No runtime, bridge, or renderer code changes.
- No new QA matrix file.
- No repo-wide traceability reshuffle outside the packet-owned node execution closeout surface.

## Verification Commands
1. `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q`
2. `.\venv\Scripts\python.exe scripts/check_traceability.py`

## Review Gate
- `.\venv\Scripts\python.exe scripts/check_traceability.py`

## Expected Artifacts
- `docs/specs/work_packets/execution_edge_progress_visualization/P05_verification_docs_traceability_closeout_WRAPUP.md`
- `docs/specs/perf/NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md`

## Acceptance Criteria
- The retained node execution QA matrix and requirement docs describe the execution-edge progress extension without creating a second QA home.
- Traceability rows and packet-owned token tests reference the new execution-edge commands, docs, and evidence coherently.
- `tests/test_traceability_checker.py` and `scripts/check_traceability.py` pass after the docs refresh.

## Handoff Notes
- This is the closeout packet for `EXECUTION_EDGE_PROGRESS_VISUALIZATION`; no later packet depends on it inside this set.
- If a later feature extends the retained node execution QA matrix again, it should reference this packet set rather than creating a parallel execution-edge closeout tree.
