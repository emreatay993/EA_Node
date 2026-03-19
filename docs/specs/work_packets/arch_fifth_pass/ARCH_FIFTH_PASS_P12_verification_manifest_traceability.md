# ARCH_FIFTH_PASS P12: Verification Manifest And Traceability

## Objective
- Make verification facts declarative, remove duplicated runner/checker knowledge, and simplify packet-owned traceability auditing without changing the current verification outcomes.

## Preconditions
- `P11` is marked `PASS` in [ARCH_FIFTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_STATUS.md).
- No later `ARCH_FIFTH_PASS` packet is in progress.

## Execution Dependencies
- `P11`

## Target Subsystems
- verification fact ownership
- verification runner/checker alignment
- verification/traceability regression coverage

## Conservative Write Scope
- `scripts/verification_manifest.py`
- `scripts/run_verification.py`
- `scripts/check_traceability.py`
- `tests/conftest.py`
- `tests/test_run_verification.py`
- `tests/test_traceability_checker.py`
- `docs/specs/work_packets/arch_fifth_pass/P12_verification_manifest_traceability_WRAPUP.md`

## Required Behavior
- Keep `scripts/verification_manifest.py` as the single packet-owned source of truth for verification facts.
- Remove packet-owned hard-coded duplicate knowledge from `scripts/check_traceability.py` and `scripts/run_verification.py` where those facts can be derived from `verification_manifest.py`.
- Keep packet-owned traceability auditing smaller and less prose-fragile than the current checker design.
- Preserve the current verification command surface and audit outcomes from the user point of view.

## Non-Goals
- No broader docs rewrite in this packet; `P13` owns the closeout docs and relative-link cleanup.
- No runtime/source behavior changes in this packet.
- No repo-wide verification policy redesign beyond packet-owned consolidation.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_run_verification.py tests/test_traceability_checker.py -q`
2. `./venv/Scripts/python.exe scripts/run_verification.py --mode fast --dry-run`
3. `./venv/Scripts/python.exe scripts/check_traceability.py`

## Review Gate
- `./venv/Scripts/python.exe scripts/run_verification.py --mode fast --dry-run`

## Expected Artifacts
- `docs/specs/work_packets/arch_fifth_pass/P12_verification_manifest_traceability_WRAPUP.md`

## Acceptance Criteria
- Packet-owned runner/checker facts are sourced from `verification_manifest.py` rather than duplicated.
- Verification dry run and traceability audit still produce the expected outcomes.
- Packet verification passes in the project venv.

## Handoff Notes
- `P13` updates requirement/docs surfaces to match the final packet-owned verification/tracing contract.
- Keep external command names stable even if internal fact sourcing changes.
