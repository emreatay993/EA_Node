# ARCH_SECOND_PASS P08: Verification Traceability Hardening

## Objective
- Refresh stale architecture-proof artifacts and add automated validation for the traceability/evidence layer so verification docs reflect the current workflow and current known caveats.

## Preconditions
- `P00` through `P07` are marked `PASS` in [ARCH_SECOND_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_second_pass/ARCH_SECOND_PASS_STATUS.md).
- No later `ARCH_SECOND_PASS` packet is in progress.

## Execution Dependencies
- `P01`
- `P02`
- `P03`
- `P04`
- `P05`
- `P06`
- `P07`

## Target Subsystems
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- packet-owned QA/perf docs under `docs/specs/perf/`
- `docs/GETTING_STARTED.md`
- `README.md` or verification docs only if packet-owned evidence links require it
- a new automated checker under `scripts/`
- packet-owned checker/tests

## Conservative Write Scope
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/perf/**`
- `docs/GETTING_STARTED.md`
- `README.md`
- `scripts/check_traceability.py`
- `tests/test_work_packet_runner.py`
- `tests/**traceability*`

## Required Behavior
- Refresh stale QA gate evidence, stale caveats, and stale traceability references so the architecture-proof layer matches the current verification workflow and current known constraints.
- Codify the current shell/QML subprocess or fresh-process fallback policy honestly when it is still required, and remove obsolete caveats when they no longer reproduce.
- Add an automated checker that validates packet-owned traceability/evidence references and reports stale or missing proof artifacts.
- Add or update tests for the new checker or its packet-owned validation rules.
- Keep the docs explicit about any remaining multi-`ShellWindow` or harness instability if it is still unresolved after the earlier packets.

## Non-Goals
- No product-feature changes.
- No broad test-harness rewrite beyond the packet-owned validation/checker work.
- No reopening of earlier packet implementation scopes except for narrow doc/test fallout.

## Verification Commands
1. `./venv/Scripts/python.exe scripts/check_traceability.py`
2. `./venv/Scripts/python.exe scripts/run_verification.py --mode fast --dry-run`
3. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_work_packet_runner -v`

## Review Gate
- `./venv/Scripts/python.exe scripts/check_traceability.py`

## Expected Artifacts
- `docs/specs/work_packets/arch_second_pass/P08_verification_traceability_hardening_WRAPUP.md`
- `scripts/check_traceability.py`

## Acceptance Criteria
- Packet-owned QA/traceability docs no longer point to stale gate evidence or stale known-caveat claims.
- The new checker exists, runs in the project venv, and validates the packet-owned proof layer.
- Packet-owned verification/doc regression coverage passes.

## Handoff Notes
- This is the final packet in the set. Its wrap-up should clearly note any intentionally deferred proof-layer gaps that remain after the refresh.
- Keep packet-owned doc edits concrete and source-backed; do not generalize beyond what the checker and rerun commands actually prove.
