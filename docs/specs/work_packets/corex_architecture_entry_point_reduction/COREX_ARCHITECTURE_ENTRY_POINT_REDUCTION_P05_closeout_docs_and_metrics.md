# COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION P05: Closeout Docs and Metrics

## Packet Metadata

- Packet: `P05`
- Title: `Closeout Docs and Metrics`
- Execution Dependencies: `P04`
- Worker model: `gpt-5.5`
- Worker reasoning effort: `xhigh`

## Objective

- Publish the new graph action ownership path and close the packet set with focused QA evidence and maintainability metrics.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, final packet-state source files needed for documentation, and closeout tests

## Preconditions

- `P04` is `PASS`.
- PyQt and QML high-level graph action routes use `GraphActionController` / `GraphActionBridge`.

## Execution Dependencies

- `P04`

## Target Subsystems

- `ARCHITECTURE.md`
- `docs/specs/INDEX.md`
- `docs/specs/perf/COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_QA_MATRIX.md`
- `docs/specs/work_packets/corex_architecture_entry_point_reduction/`
- `scripts/verification_manifest.py`
- `tests/test_markdown_hygiene.py`
- `tests/test_traceability_checker.py`
- `tests/test_run_verification.py`

## Conservative Write Scope

- `docs/specs/work_packets/corex_architecture_entry_point_reduction/P05_closeout_docs_and_metrics_WRAPUP.md`
- `ARCHITECTURE.md`
- `docs/specs/INDEX.md`
- `docs/specs/perf/COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_QA_MATRIX.md`
- `scripts/verification_manifest.py`
- `tests/test_markdown_hygiene.py`
- `tests/test_traceability_checker.py`
- `tests/test_run_verification.py`

## Required Behavior

- Update `ARCHITECTURE.md` to document the canonical high-level graph action path: `shortcut/menu/QML event -> GraphActionBridge or PyQt action dispatch -> GraphActionController -> existing behavior owner`.
- Document the boundary between high-level graph actions and low-level canvas operations that stay in existing bridges.
- Add a QA matrix at `docs/specs/perf/COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_QA_MATRIX.md` with packet outcomes, verification commands, review gates, and residual risks.
- Register the QA matrix in `docs/specs/INDEX.md`.
- Update traceability or verification manifest constants only if the new QA matrix or closeout evidence is required by existing hygiene checks.
- Record maintainability metrics in the QA matrix using static counts or documented search results, such as:
  - number of high-level graph action QML branches routed through `graphActionBridge`
  - number of high-level `GraphCanvasCommandBridge` slots removed or retained
  - remaining compatibility wrapper count and reason
- Keep this closeout documentation-only except for tests or manifest constants needed to make documentation checks pass.

## Non-Goals

- Do not continue refactoring graph mutation, runtime snapshot, plugin registration, verification runner, or work-packet tooling.
- Do not change behavior after `P04` unless a documentation test exposes a broken reference.
- Do not run broad full-mode verification unless narrow closeout checks expose a need.

## Verification Commands

1. Full packet verification:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_markdown_hygiene.py tests/test_traceability_checker.py tests/test_run_verification.py --ignore=venv -q
.\venv\Scripts\python.exe scripts/check_markdown_links.py
```

## Review Gate

```powershell
.\venv\Scripts\python.exe scripts/check_markdown_links.py
```

## Expected Artifacts

- `docs/specs/work_packets/corex_architecture_entry_point_reduction/P05_closeout_docs_and_metrics_WRAPUP.md`
- `docs/specs/perf/COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_QA_MATRIX.md`
- `ARCHITECTURE.md`
- `docs/specs/INDEX.md`

## Acceptance Criteria

- `ARCHITECTURE.md` names the canonical graph action owner and the remaining low-level canvas bridge boundary.
- The QA matrix records packet verification and residual risks.
- The spec index links the QA matrix.
- Markdown hygiene and traceability tests pass.
- The markdown link checker passes.

## Handoff Notes

- Follow-on cleanup remains out of scope: graph mutation entry points, runtime/plugin registration, and verification/devtools entry points should become separate packet sets.
- If docs closeout identifies a remaining compatibility wrapper, record why it remains and which later packet set should retire it.
