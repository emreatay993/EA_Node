# VERIFICATION_SPEED P03: Hybrid Verification Runner

## Objective
- Add a repo-owned verification runner that exposes `fast`, `gui`, `slow`, and `full` modes, uses pytest for the split developer loops, and preserves the isolated `unittest` shell phase for the known shell-wrapper modules.

## Preconditions
- `P00` is marked `PASS` in [VERIFICATION_SPEED_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_STATUS.md).
- `P01` and `P02` are marked `PASS`.
- No later `VERIFICATION_SPEED` packet is in progress.

## Execution Dependencies
- `P01`
- `P02`

## Target Subsystems
- `scripts/run_verification.py`

## Conservative Write Scope
- `scripts/run_verification.py`

## Required Behavior
- Add a Python CLI at `scripts/run_verification.py`.
- Support `--mode fast`, `--mode gui`, `--mode slow`, and `--mode full`.
- Support `--dry-run` so the script can print its exact commands without executing them.
- `fast` mode must:
  - run pytest with `-m "not gui and not slow"`
  - ignore the four shell-wrapper modules
  - prefer `pytest-xdist` parallel execution when the plugin is importable
  - fall back to serial pytest with an explicit notice when `pytest-xdist` is unavailable
- `gui` mode must:
  - run pytest with `-m "gui and not slow"`
  - ignore the four shell-wrapper modules
  - stay serial
- `slow` mode must:
  - run pytest with `-m slow`
  - ignore the four shell-wrapper modules
  - stay serial
- `full` mode must run:
  - `fast`
  - then `gui`
  - then `slow`
  - then the isolated `unittest` shell phase for:
    - `tests.test_main_window_shell`
    - `tests.test_script_editor_dock`
    - `tests.test_shell_run_controller`
    - `tests.test_shell_project_session_controller`
- Ensure all GUI-bearing phases set `QT_QPA_PLATFORM=offscreen`.
- Print each concrete command before execution and stop on the first failing exit code.
- Keep the script independent of future doc wording; `P05` will publish the final human-facing commands.

## Non-Goals
- No documentation updates yet. `P05` owns that.
- No test-body or marker changes. `P01`, `P02`, and `P04` own those.
- No attempt to repair the known serializer baseline failure in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe -m py_compile scripts/run_verification.py`
2. `./venv/Scripts/python.exe scripts/run_verification.py --mode fast --dry-run`
3. `./venv/Scripts/python.exe scripts/run_verification.py --mode gui --dry-run`
4. `./venv/Scripts/python.exe scripts/run_verification.py --mode slow --dry-run`
5. `./venv/Scripts/python.exe scripts/run_verification.py --mode full --dry-run`

## Review Gate
- `./venv/Scripts/python.exe scripts/run_verification.py --mode full --dry-run`

## Expected Artifacts
- `docs/specs/work_packets/verification_speed/P03_hybrid_verification_runner_WRAPUP.md`

## Acceptance Criteria
- The script compiles with `py_compile`.
- Dry-run output enumerates the expected phase structure for every mode.
- Dry-run output for `full` explicitly includes the isolated `unittest` shell phase after the pytest phases.
- The script has a clear serial fallback when `pytest-xdist` is not importable.
- No production files under `ea_node_editor/**` or test modules under `tests/**` are modified in this packet.

## Handoff Notes
- Keep the public mode names stable once introduced.
- `P05` will reference these exact modes in the docs and QA matrix, so do not invent alternate synonyms or extra default modes here.
