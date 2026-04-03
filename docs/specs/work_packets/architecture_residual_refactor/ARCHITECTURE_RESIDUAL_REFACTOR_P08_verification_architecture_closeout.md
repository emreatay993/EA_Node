# ARCHITECTURE_RESIDUAL_REFACTOR P08: Verification Architecture Closeout

## Objective

- Replace brittle text-driven architecture proof and manual shell-backed coverage gaps with semantic packet-owned enforcement, then publish final residual-refactor QA evidence.

## Preconditions

- `P07` is marked `PASS` in [ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md](./ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_RESIDUAL_REFACTOR` packet is in progress.

## Execution Dependencies

- `P07`

## Target Subsystems

- `scripts/verification_manifest.py`
- `scripts/check_traceability.py`
- `tests/test_architecture_boundaries.py`
- `tests/test_shell_isolation_phase.py`
- `tests/shell_isolation_main_window_targets.py`
- `tests/shell_isolation_controller_targets.py`
- `tests/test_traceability_checker.py`
- `tests/test_markdown_hygiene.py`
- `docs/specs/INDEX.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/perf/ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX.md`
- `docs/specs/work_packets/architecture_residual_refactor/P08_verification_architecture_closeout_WRAPUP.md`

## Conservative Write Scope

- `scripts/verification_manifest.py`
- `scripts/check_traceability.py`
- `tests/test_architecture_boundaries.py`
- `tests/test_shell_isolation_phase.py`
- `tests/shell_isolation_main_window_targets.py`
- `tests/shell_isolation_controller_targets.py`
- `tests/test_traceability_checker.py`
- `tests/test_markdown_hygiene.py`
- `docs/specs/INDEX.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/perf/ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX.md`
- `docs/specs/work_packets/architecture_residual_refactor/P08_verification_architecture_closeout_WRAPUP.md`

## Required Behavior

- Replace packet-owned architecture-boundary proof with semantic checks where possible, keeping only narrow text smoke assertions that still carry architectural signal.
- Add a reverse shell-catalog ownership check or equivalent manifest-owned guard so new shell-backed tests cannot be omitted silently from packet-owned shell-isolation coverage.
- Collapse packet-owned traceability token ownership onto one manifest-owned schema or another single source of truth shared by the checker and tests.
- Publish `docs/specs/perf/ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX.md` and register the residual packet set closeout in the canonical docs surfaces.

## Non-Goals

- No new product behavior.
- No new architecture refactor packets after this closeout.
- Do not widen packet proof into unrelated repo-wide verification when the packet-owned architecture and docs commands already prove the change.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_architecture_boundaries.py tests/test_shell_isolation_phase.py tests/test_traceability_checker.py tests/test_markdown_hygiene.py --ignore=venv -q
.\venv\Scripts\python.exe scripts/check_traceability.py
.\venv\Scripts\python.exe scripts/check_markdown_links.py
```

## Review Gate

```powershell
.\venv\Scripts\python.exe scripts/check_traceability.py
```

## Expected Artifacts

- `docs/specs/work_packets/architecture_residual_refactor/P08_verification_architecture_closeout_WRAPUP.md`
- `docs/specs/perf/ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX.md`

## Acceptance Criteria

- Packet-owned architecture verification is semantic-first rather than string-snippet-driven wherever the changed seams allow it.
- Shell-backed catalog omissions are gated by packet-owned proof instead of manual discipline alone.
- `docs/specs/perf/ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX.md` is published and linked from canonical docs surfaces.
- The packet-owned verification and docs closeout commands pass.

## Handoff Notes

- This packet closes the residual architecture refactor program.
