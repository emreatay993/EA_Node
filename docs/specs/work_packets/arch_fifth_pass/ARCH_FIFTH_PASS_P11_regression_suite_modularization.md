# ARCH_FIFTH_PASS P11: Regression Suite Modularization

## Objective
- Split the largest packet-owned regression modules into maintainable subsystem packages while preserving the current top-level test command entrypoints and logical coverage.

## Preconditions
- `P10` is marked `PASS` in [ARCH_FIFTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_STATUS.md).
- No later `ARCH_FIFTH_PASS` packet is in progress.

## Execution Dependencies
- `P10`

## Target Subsystems
- shell regression suite organization
- graph-core regression suite organization
- serializer regression suite organization

## Conservative Write Scope
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/**`
- `tests/test_graph_track_b.py`
- `tests/graph_track_b/**`
- `tests/test_serializer.py`
- `tests/serializer/**`
- `docs/specs/work_packets/arch_fifth_pass/P11_regression_suite_modularization_WRAPUP.md`

## Required Behavior
- Split the oversized packet-owned regression modules into focused submodules under:
  - `tests/main_window_shell/`
  - `tests/graph_track_b/`
  - `tests/serializer/`
- Keep the top-level files `tests/test_main_window_shell.py`, `tests/test_graph_track_b.py`, and `tests/test_serializer.py` as thin collection shims so existing commands and packet-owned verification surfaces continue to work.
- Preserve the current logical test coverage and packet-owned test names where practical; do not introduce a repo-wide testing-framework conversion.
- Keep shell isolation and packet-owned verification commands working without requiring runner-script changes in this packet.

## Non-Goals
- No changes to runtime/source behavior in this packet.
- No changes to verification-runner or traceability-script logic in this packet; `P12` owns that.
- No repo-wide pytest/unittest style conversion.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_window_shell.py tests/test_graph_track_b.py tests/test_serializer.py -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_window_shell.py tests/test_serializer.py -q`

## Expected Artifacts
- `docs/specs/work_packets/arch_fifth_pass/P11_regression_suite_modularization_WRAPUP.md`

## Acceptance Criteria
- The three large packet-owned regression modules are materially split into focused submodules.
- Existing top-level test file commands continue to work via thin collection shims.
- Logical coverage is preserved, and packet verification passes.

## Handoff Notes
- `P12` may assume the regression surface is easier to reason about, but it must not rely on renamed top-level test entrypoints.
- Keep this packet strictly on test organization; runtime/source behavior changes are out of scope.
