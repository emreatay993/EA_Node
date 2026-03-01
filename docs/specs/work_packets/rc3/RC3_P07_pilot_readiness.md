# RC3 P07: Pilot Readiness and Operator Validation

## Objective
- Refresh pilot runbook and execute packaged smoke/acceptance validation on target pilot hardware classes.

## Non-Objectives
- No new feature development beyond validation hooks.
- No relaxation of existing QA/perf acceptance gates.

## Inputs
- `docs/PILOT_RUNBOOK.md`
- `docs/specs/perf/PILOT_SIGNOFF.md`
- `docs/specs/perf/PILOT_BACKLOG.md`

## Allowed Files
- `docs/PILOT_RUNBOOK.md`
- `docs/specs/perf/PILOT_SIGNOFF.md`
- `docs/specs/perf/PILOT_BACKLOG.md`
- `docs/specs/perf/rc3/*`
- `artifacts/pilot_signoff/*`

## Do Not Touch
- `ea_node_editor/nodes/**`
- `ea_node_editor/execution/**`

## Verification
1. `venv\Scripts\python -m unittest tests.test_main_window_shell tests.test_serializer -v`
2. `venv\Scripts\python -m unittest tests.test_integrations_track_f -v`

## Output Artifacts
- `docs/specs/perf/rc3/pilot_readiness_report.md`
- `artifacts/pilot_signoff/<run_id>/pilot_signoff_results.json`

## Merge Gate (Requirement IDs)
- `AC-REQ-QA-001-03`
- `AC-REQ-QA-005-02`
- `AC-REQ-QA-007-02`
- `AC-REQ-QA-001-06`
