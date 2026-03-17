# Verification Speed QA Matrix

- Updated: `2026-03-17`
- Packet set: `VERIFICATION_SPEED` (`P01` through `P05`)
- Scope: published developer-facing verification workflow after the pytest
  phase split, shell-wrapper collection hygiene, hybrid runner, and GUI
  wait-helper cleanup.

## Approved Verification Workflow

| Mode | Command | Coverage | Notes |
|---|---|---|---|
| `fast` | `./venv/Scripts/python.exe scripts/run_verification.py --mode fast` | Default day-to-day pytest loop for tests that are not marked `gui` or `slow` | Uses `pytest -m "not gui and not slow"` and ignores the four shell-wrapper files; adds `-n auto` only when `pytest-xdist` is importable in the project venv |
| `gui` | `./venv/Scripts/python.exe scripts/run_verification.py --mode gui` | QML-heavy pytest slice marked `gui and not slow` | Serial by design and still ignores the four shell-wrapper files |
| `slow` | `./venv/Scripts/python.exe scripts/run_verification.py --mode slow` | Slow pytest slice marked `slow` | Serial by design and still ignores the four shell-wrapper files |
| `full` | `./venv/Scripts/python.exe scripts/run_verification.py --mode full` | Runs `fast`, `gui`, and `slow` first, then the isolated shell-wrapper `unittest` phase | Use `--dry-run` to inspect the exact subprocess commands before execution |

## Locked Shell Isolation Rules

- The pytest phases always pass `--ignore=tests/test_main_window_shell.py`,
  `--ignore=tests/test_script_editor_dock.py`,
  `--ignore=tests/test_shell_run_controller.py`, and
  `--ignore=tests/test_shell_project_session_controller.py`.
- The authoritative shell-wrapper commands remain:
  - `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell -v`
  - `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_script_editor_dock -v`
  - `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_shell_run_controller -v`
  - `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_shell_project_session_controller -v`
- `full` runs each shell-wrapper module in its own process after the pytest
  phases. Do not replace that phase with `unittest discover` or a shared
  `ShellWindow()` reuse strategy.

## Baseline Timings From The Packet Manifest

| Baseline Measurement | Recorded Value | Why It Matters |
|---|---|---|
| `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest -q --durations=30` | about `193.88s` for `450` collected tests | Establishes the pre-packet baseline that motivated the split verification workflow |
| `tests/test_main_window_shell.py` | about `100.12s` | Shows why the shell-wrapper modules stay isolated and out of the default pytest phases |
| `tests/test_shell_project_session_controller.py` | about `25.11s` | Confirms that another shell-backed module is still expensive enough to keep out of the default fast loop |
| Fresh `ShellWindow()` construction | about `870ms` | Startup cost is dominated by QML shell loading through `QQuickWidget.setSource(...)`, not registry bootstrap |

## Current Environment Notes

- Run the workflow with the project-local interpreter:
  `./venv/Scripts/python.exe`. The repo uses a Windows-style virtualenv layout
  even when opened from `bash`.
- `scripts/run_verification.py` applies `QT_QPA_PLATFORM=offscreen` to its
  child verification commands, so the top-level runner invocations do not need
  extra environment variables.
- `pytest-xdist` is declared in `pyproject.toml` and `requirements.txt`, but it
  was not installed in the project venv on `2026-03-17`. `fast` mode therefore
  falls back to serial pytest and prints the runner notice instead of adding
  `-n auto`.

## Known Baseline Caveats

- `./venv/Scripts/python.exe -m pytest tests/test_serializer.py -k passive_image_panel_properties_and_size -q`
  still fails because passive image-panel round-trips add default crop fields.
  The `VERIFICATION_SPEED` packet set keeps that persistence failure
  out-of-scope.
- Do not claim that the overall pytest corpus is fully green while that
  serializer baseline remains open. The runner documentation only changes the
  workflow and traceability around the existing baseline.

## 2026-03-17 Verification Result

| Command | Result | Notes |
|---|---|---|
| `./venv/Scripts/python.exe scripts/run_verification.py --mode full --dry-run` | PASS | Enumerated the `fast`, `gui`, `slow`, and isolated shell-wrapper phases; each pytest phase included all four `--ignore=` entries, and the fast phase printed the serial fallback notice because `pytest-xdist` is not installed in the current project venv |
