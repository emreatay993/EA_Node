# VERIFICATION_SPEED P02: Shell Wrapper Collection Hygiene

## Objective
- Stop pytest from directly collecting internal shell-wrapper helper classes while preserving the repo's existing `unittest`-driven fresh-process isolation flows.

## Preconditions
- `P00` is marked `PASS` in [VERIFICATION_SPEED_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_STATUS.md).
- No later `VERIFICATION_SPEED` packet is in progress.

## Execution Dependencies
- none

## Target Subsystems
- `tests/test_main_window_shell.py`
- `tests/test_script_editor_dock.py`
- `tests/test_shell_run_controller.py`
- `tests/test_shell_project_session_controller.py`

## Conservative Write Scope
- `tests/test_main_window_shell.py`
- `tests/test_script_editor_dock.py`
- `tests/test_shell_run_controller.py`
- `tests/test_shell_project_session_controller.py`

## Required Behavior
- Prevent pytest from collecting `_SubprocessShellWindowTest` as a standalone test in:
  - `tests/test_main_window_shell.py`
  - `tests/test_script_editor_dock.py`
  - `tests/test_shell_run_controller.py`
- Prevent pytest from directly collecting `_ShellProjectSessionControllerScenarios` in `tests/test_shell_project_session_controller.py`.
- Preserve the current `load_tests(...)` behavior and current subprocess or fresh-process `unittest` execution semantics for all four modules.
- Preserve current module-level `unittest` commands used by the repo's QA docs and packet sets.
- Do not change shell test coverage, subprocess targets, or test assertions beyond the collection-hygiene fix itself.

## Non-Goals
- No pytest marker rollout. `P01` owns classification.
- No new verification runner. `P03` owns that.
- No production code changes or shell/QML behavior changes.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest --collect-only -q tests/test_main_window_shell.py tests/test_script_editor_dock.py tests/test_shell_run_controller.py`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest --collect-only -q tests/test_shell_project_session_controller.py`
3. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_script_editor_dock tests.test_shell_run_controller -v`
4. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_shell_project_session_controller -v`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest --collect-only -q tests/test_shell_project_session_controller.py`

## Expected Artifacts
- `docs/specs/work_packets/verification_speed/P02_shell_wrapper_collection_hygiene_WRAPUP.md`

## Acceptance Criteria
- The collect-only output for the three wrapper modules no longer includes `_SubprocessShellWindowTest`.
- The collect-only output for `tests/test_shell_project_session_controller.py` no longer includes `_ShellProjectSessionControllerScenarios`.
- The `unittest` verification commands still pass through the intended shell-isolation wrappers.
- No files outside the four packet-owned test modules are modified.

## Handoff Notes
- Keep the solution local to pytest collection metadata or helper visibility. Do not redesign the shell wrapper pattern here.
- `P03` will explicitly ignore these modules in fast/gui/slow pytest phases, so do not widen this packet into runner orchestration.
