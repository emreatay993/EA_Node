# ARCH_SIXTH_PASS P11: Shell Verification Lifecycle Hardening

## Objective
- Consolidate shell-backed verification around one honest fresh-process lifecycle contract so runner, checker, devtools, and shell-test helpers stop duplicating shell-isolation and fallback policy.

## Preconditions
- `P00` through `P10` are marked `PASS` in [ARCH_SIXTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_STATUS.md).
- No later `ARCH_SIXTH_PASS` packet is in progress.

## Execution Dependencies
- `P10`

## Target Subsystems
- verification runner and manifest facts
- proof-audit and traceability tooling
- shell-backed test harness helpers

## Conservative Write Scope
- `scripts/run_verification.py`
- `scripts/verification_manifest.py`
- `scripts/check_traceability.py`
- `devtools/work_packet_runner.py`
- `devtools/work_packet_monitor.py`
- `devtools/work_packet_thread.py`
- `tests/main_window_shell/base.py`
- `tests/test_run_verification.py`
- `tests/test_traceability_checker.py`
- `tests/test_shell_isolation_phase.py`
- `tests/shell_isolation_runtime.py`
- `tests/shell_isolation_main_window_targets.py`
- `tests/shell_isolation_controller_targets.py`
- `docs/specs/work_packets/arch_sixth_pass/P11_shell_verification_lifecycle_hardening_WRAPUP.md`

## Required Behavior
- Keep fresh-process shell isolation as the explicit packet-owned truth unless the packet can prove a narrower stable lifecycle contract.
- Remove or reduce duplicated shell-isolation and fallback facts across the runner, proof audit, devtools, and shell-test helpers.
- Align `tests/main_window_shell/base.py` packet-owned harness behavior with the same lifecycle contract that `scripts/run_verification.py` and `scripts/check_traceability.py` document.
- Preserve current verification modes, traceability outcomes, and shell-isolation target coverage.

## Non-Goals
- No broad architecture docs rewrite in this packet.
- No claim that repeated in-process `ShellWindow()` construction is safe unless the packet's proof actually establishes that.
- No plugin/package or runtime transport changes in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_run_verification.py tests/test_traceability_checker.py tests/test_shell_isolation_phase.py -q`
2. `./venv/Scripts/python.exe scripts/run_verification.py --mode full --dry-run`

## Review Gate
- `./venv/Scripts/python.exe scripts/run_verification.py --mode full --dry-run`

## Expected Artifacts
- `docs/specs/work_packets/arch_sixth_pass/P11_shell_verification_lifecycle_hardening_WRAPUP.md`

## Acceptance Criteria
- Packet-owned verification tooling and shell-test harnesses describe one consistent shell lifecycle contract.
- `run_verification` dry-run and traceability/regression tooling stay aligned.
- Shell-backed verification policy is clearer and less bespoke than the current scattered baseline.

## Handoff Notes
- `P12` owns the final docs and traceability closeout after the verification contract is coherent.
- Keep this packet focused on lifecycle and tooling coherence, not broad docs cleanup.
