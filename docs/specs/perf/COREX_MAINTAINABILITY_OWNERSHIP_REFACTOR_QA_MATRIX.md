# COREX Maintainability And Ownership Refactor QA Matrix

Status: `IN PROGRESS`

This is the single task, test-migration, performance, and review ledger for
`docs/PLAN_COREX_MAINTAINABILITY_OWNERSHIP_REFACTOR.md`.

## Locked Baseline

| Fact | Value |
| --- | --- |
| Starting branch | `main` |
| Starting commit | `5a4ae4b8` |
| Upstream at start | `origin/main` at `5a4ae4b8` |
| Publication | Local commits only; no push |
| Protected modified path | `docs/specs/INDEX.md` |
| Protected untracked path | `docs/PLAN_COREX_Physical_Simulation_Backend.md` |
| Protected untracked path | `scripts/Strain_Gage_Positioning/modular_version/strain_candidate_points.csv` |
| Performance policy | Advisory matched evidence; no timing-only rollback |

## Compaction Recovery Checklist

Before continuing after compaction, read these in order:

1. `AGENTS.md`
2. `docs/PLAN_COREX_MAINTAINABILITY_OWNERSHIP_REFACTOR.md`
3. this QA matrix
4. `git status --short --branch`
5. `git log -1 --oneline`
6. the next `IN PROGRESS` or `NOT STARTED` task row below

Do not edit until the protected dirty paths and last accepted commit are
reconciled with this ledger.

## Task Ledger

| Task | Status | Writer | Conservative write scope | Focused evidence | Performance evidence | Independent review | Accepted commit |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T00 Plan and baseline | `READY TO COMMIT` | Orchestrator | Plan, this ledger, exact spec-index additions | Full dry-run, traceability, links, diff hygiene, and 582-test affected inventory passed; `qmltestrunner.exe` unavailable | Fast baseline: 4,543 passed, 2 skipped, 18 existing warnings; logs under `artifacts/verification_logs/20260901_042328/` | Two delegated read-only baseline verifiers returned no findings | Pending |
| T01 Package policy | `NOT STARTED` | Pending | Nodes package schema, add-on contracts, direct tests/maps | Pending | Pending | Pending | Pending |
| T02 Runtime contracts | `NOT STARTED` | Pending | Common artifact grammar, runtime values, direct imports/tests/maps | Pending | Pending | Pending | Pending |
| T03 UI projections | `NOT STARTED` | Pending | Library, Inspector, Quick Insert, direct tests/maps | Pending | Pending | Pending | Pending |
| T04 Graph host owner | `NOT STARTED` | Pending | Graph host presenter, shell forwarders, direct tests/maps | Pending | Pending | Pending | Pending |
| T05 Tabular query | `NOT STARTED` | Pending | Tabular service/backends/query, direct tests/maps | Pending | Pending | Pending | Pending |
| T06 Video playback | `NOT STARTED` | Pending | Video QML/state, direct tests/maps | Pending | Pending | Pending | Pending |
| T07 Residual tests | `NOT STARTED` | Pending | Ledger-proven residual tests/catalogs/maps | Pending | None for product runtime | Pending | Pending or accepted no-op |
| T08 Closeout | `NOT STARTED` | Orchestrator | QA status, shared maps/indexes/guards | Pending | Consolidated review pending | Pending | Pending |

## Test Migration Ledger

Allowed dispositions are `retained`, `moved_to_owner`,
`replaced_by_owner_test`, `replaced_by_qml_quicktest`, `merged_equivalent`, and
`deleted_redundant`.

| Task | Old node ID | Behavior | Current owner | Disposition | Replacement node ID | Proving command | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T01 | Pending inventory | Package schema and trust-boundary validation | Mixed loader/manager/generation | Pending | Pending | Pending | `NOT STARTED` |
| T02 | Pending inventory | Runtime carrier and codec contracts | Mixed runtime/persistence | Pending | Pending | Pending | `NOT STARTED` |
| T03 | Pending inventory | Library/Inspector/Quick Insert projection | Mixed projection module | Pending | Pending | Pending | `NOT STARTED` |
| T04 | Pending inventory | Graph cursor/style action routing | Shell forwarding chain | Pending | Pending | Pending | `NOT STARTED` |
| T05 | Pending inventory | Tabular source/query/cache behavior | Mixed loader service | Pending | Pending | Pending | `NOT STARTED` |
| T06 | Pending inventory | Inline/fullscreen video playback | Two QML renderers | Pending | Pending | Pending | `NOT STARTED` |
| T07 | Pending residual audit | Shell versus direct owner behavior | Shell tests | Pending | Pending | Pending | `NOT STARTED` |

## Performance Evidence

| Task | Metric and fixture | Baseline | Candidate | Repeat / attribution | Verdict |
| --- | --- | --- | --- | --- | --- |
| T01 | Package discovery/import/export | Pending | Pending | Pending | Pending |
| T02 | Runtime codec/import/copy behavior | Pending | Pending | Pending | Pending |
| T03 | Library rebuild and Quick Insert | Pending | Pending | Pending | Pending |
| T04 | Shell create and graph action | Pending | Pending | Pending | Pending |
| T05 | 400 MB Tabular cold/warm queries | Pending | Pending | Pending | Pending |
| T06 | Animated media and decoder ownership | Pending | Pending | Pending | Pending |

## T00 Baseline Evidence

| Command / evidence | Result |
| --- | --- |
| `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode full --dry-run` | `PASS`; command graph rendered, with `qmltestrunner.exe` reported unavailable in this environment |
| Affected Python suites, serial `--collect-only` | `PASS`; 582 tests collected across 27 modules, no collection errors |
| `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode fast --summarize-output` | `PASS`; parallel 4,318 passed/2 skipped, serial 225 passed, 18 existing warnings |
| `.\venv\Scripts\python.exe .\scripts\check_traceability.py` | `PASS` |
| `.\venv\Scripts\python.exe .\scripts\check_markdown_links.py` | `PASS` |
| `git diff --check` | `PASS` |
| Protected-path hash audit | `PASS`; all three pre-existing dirty paths retained their starting hashes |

## Review Ledger

| Review | Scope | Reviewer | Findings | Resolution | Verdict |
| --- | --- | --- | --- | --- | --- |
| Per-task reviews | T01-T07 | Pending | Pending | Pending | Pending |
| Architecture/ownership closeout | Whole series | Pending | Pending | Pending | Pending |
| Correctness/security/no-lost-tests closeout | Whole series | Pending | Pending | Pending | Pending |
| Performance-evidence closeout | Whole series | Pending | Pending | Pending | Pending |

## Final Acceptance

| Gate | Command / evidence | Result |
| --- | --- | --- |
| Focused task suites | Recorded per task | Pending |
| Agent maps | `.\venv\Scripts\python.exe .\scripts\check_agent_maps.py` | Pending |
| Traceability | `.\venv\Scripts\python.exe .\scripts\check_traceability.py` | Pending |
| Markdown links | `.\venv\Scripts\python.exe .\scripts\check_markdown_links.py` | Pending |
| Full verification | `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode full --summarize-output` | Pending |
| Diff hygiene | `git diff --check` and cached-diff audit | Pending |
| Publication | Local commit series only | Pending |
