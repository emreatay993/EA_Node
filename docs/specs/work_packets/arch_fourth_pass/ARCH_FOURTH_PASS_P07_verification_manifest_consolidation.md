# ARCH_FOURTH_PASS P07: Verification Manifest Consolidation

## Objective
- Consolidate verification phase catalogs, shell-isolation targets, and traceability proof facts into one declarative source so runner, tests, and proof auditing stop drifting independently.

## Preconditions
- `P06` is marked `PASS` in [ARCH_FOURTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_STATUS.md).
- No later `ARCH_FOURTH_PASS` packet is in progress.

## Execution Dependencies
- `P06`

## Target Subsystems
- `scripts/run_verification.py`
- `scripts/check_traceability.py`
- `tests/conftest.py`
- verification/traceability regression tests
- packet-owned verification manifest data/module

## Conservative Write Scope
- `scripts/run_verification.py`
- `scripts/check_traceability.py`
- `scripts/*.py`
- `tests/conftest.py`
- `tests/test_run_verification.py`
- `tests/test_traceability_checker.py`
- `docs/specs/perf/VERIFICATION_SPEED_QA_MATRIX.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/work_packets/arch_fourth_pass/P07_verification_manifest_consolidation_WRAPUP.md`

## Required Behavior
- Introduce one declarative verification manifest or equivalent canonical data source for phase selection, shell-isolation catalogs, and proof-audit anchors.
- Make `scripts/run_verification.py`, `tests/conftest.py`, and traceability checks consume that canonical source instead of hardcoding overlapping facts.
- Replace brittle exact-prose or exact-benchmark-string assertions with structured fact checks wherever packet-owned traceability logic currently depends on text copies.
- Preserve the current developer-facing verification entry points and documented mode names unless a packet-owned compatibility layer keeps them stable.

## Non-Goals
- No broad architecture-doc closeout yet; `P08` owns that.
- No packet-owned shell/UI runtime refactors.
- No requirement-module rewrites beyond the narrow verification/traceability anchors this packet must keep aligned.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_run_verification.py tests/test_traceability_checker.py -q`
2. `./venv/Scripts/python.exe scripts/run_verification.py --mode full --dry-run`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_run_verification.py -q`

## Expected Artifacts
- `docs/specs/work_packets/arch_fourth_pass/P07_verification_manifest_consolidation_WRAPUP.md`

## Acceptance Criteria
- One canonical verification manifest or equivalent source owns the packet-owned phase/catalog/proof facts that were previously duplicated.
- The dry-run workflow and packet-owned verification tests remain green through the project venv.
- Traceability checks no longer depend on fragile exact prose copies for packet-owned facts.

## Handoff Notes
- `P08` will update higher-level docs and traceability around the new manifest contract; keep names and locations stable enough to document there.
- Avoid widening this packet into generic packet-doc archival or backlog cleanup.
