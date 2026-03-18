# Verification Speed QA Matrix

- Updated: `2026-03-18`
- Packet set: `VERIFICATION_SPEED` (`P01` through `P05`)
- Scope: published developer-facing verification workflow after the pytest
  phase split, shell-wrapper collection hygiene, hybrid runner, and GUI
  wait-helper cleanup, plus the P08 proof-layer refresh.

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
- `pytest-xdist` is declared in `pyproject.toml` and `requirements.txt`, and it
  is installed in the project venv as of `2026-03-18`. `fast` mode therefore
  uses `-n auto` on this machine. If the plugin is unavailable in another
  environment, `scripts/run_verification.py` still falls back to serial pytest
  and prints the runner notice.

## Companion Proof Audit

- `./venv/Scripts/python.exe scripts/check_traceability.py` validates the
  packet-owned proof layer in `README.md`, `docs/GETTING_STARTED.md`,
  `docs/specs/requirements/TRACEABILITY_MATRIX.md`, and the packet-owned docs
  under `docs/specs/perf/`.
- Run the checker after editing verification docs, archived QA evidence
  summaries, or packet-owned traceability references.

## Current Baseline Status

- `./venv/Scripts/python.exe -m pytest tests/test_serializer.py -k passive_image_panel_properties_and_size -q`
  passed on `2026-03-18`, so the earlier passive image-panel serializer caveat
  is retired.
- No known out-of-scope verification baseline failures remain in this matrix.
  If a new environment-specific failure appears, record it here before claiming
  the aggregate workflow is fully green.

## 2026-03-18 Verification Results

| Command | Result | Notes |
|---|---|---|
| `./venv/Scripts/python.exe scripts/run_verification.py --mode full --dry-run` | PASS | Enumerated the `fast`, `gui`, `slow`, and isolated shell-wrapper phases; each pytest phase included all four `--ignore=` entries, and the fast phase emitted `-n auto` because `pytest-xdist` is installed in the current project venv |
| `./venv/Scripts/python.exe -m pytest tests/test_serializer.py -k passive_image_panel_properties_and_size -q` | PASS | The previous serializer spot-check caveat no longer reproduces in the current project venv |
