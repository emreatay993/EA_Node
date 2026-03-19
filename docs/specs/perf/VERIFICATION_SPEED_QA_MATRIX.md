# Verification Speed QA Matrix

- Updated: `2026-03-20`
- Packet set: `VERIFICATION_SPEED` (`P01` through `P05`)
- Scope: published developer-facing verification workflow after the dedicated
  shell-isolation phase rollout, explicit max-parallel worker policy, and
  proof-layer refresh.

## Approved Verification Workflow

| Mode | Command | Coverage | Notes |
|---|---|---|---|
| `fast` | `./venv/Scripts/python.exe scripts/run_verification.py --mode fast` | Default day-to-day pytest loop for tests that are not marked `gui` or `slow` | Uses `pytest -m "not gui and not slow"` and ignores the four shell-backed modules plus `tests/test_shell_isolation_phase.py`; when `pytest-xdist` is importable in the project venv, resolves workers as `psutil.cpu_count(logical=True)` else `os.cpu_count()` else `1`, then passes `-n <resolved_count> --dist load`; otherwise prints the serial fallback notice |
| `gui` | `./venv/Scripts/python.exe scripts/run_verification.py --mode gui` | QML-heavy pytest slice marked `gui and not slow` | Resolves workers as `psutil.cpu_count(logical=True)` else `os.cpu_count()` else `1`, then caps that value at `6` and passes `-n <gui_resolved_count> --dist load` when `pytest-xdist` is importable in the project venv; otherwise prints the serial fallback notice. It still ignores the four shell-backed modules plus `tests/test_shell_isolation_phase.py` |
| `slow` | `./venv/Scripts/python.exe scripts/run_verification.py --mode slow` | Slow pytest slice marked `slow` | Serial by design and still ignores the four shell-backed modules plus `tests/test_shell_isolation_phase.py` |
| `full` | `./venv/Scripts/python.exe scripts/run_verification.py --mode full` | Runs `fast`, `gui`, and `slow` first, then the dedicated fresh-process shell-isolation phase | Use `--dry-run` to inspect the exact subprocess commands before execution; with `pytest-xdist`, the shell phase is `./venv/Scripts/python.exe -m pytest tests/test_shell_isolation_phase.py -q -n <resolved_count> --dist load`, else the same phase runs serially |

## Locked Shell Isolation Rules

- The non-shell pytest phases always pass
  `--ignore=tests/test_main_window_shell.py`,
  `--ignore=tests/test_script_editor_dock.py`,
  `--ignore=tests/test_shell_run_controller.py`,
  `--ignore=tests/test_shell_project_session_controller.py`, and
  `--ignore=tests/test_shell_isolation_phase.py`.
- The dedicated shell-isolation phase is
  `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_shell_isolation_phase.py -q -n <resolved_count> --dist load`
  when `pytest-xdist` is available. `<resolved_count>` resolves as
  `psutil.cpu_count(logical=True)` when available, else `os.cpu_count()`,
  else `1`.
- If `pytest-xdist` is unavailable, `scripts/run_verification.py` falls back to
  serial pytest for the dedicated shell-isolation phase and preserves the same
  fresh-process child-command model.
- Each `tests/test_shell_isolation_phase.py` target launches its own child
  process through `tests/shell_isolation_runtime.py`, so QML shell state is
  not shared across catalog entries even when xdist schedules targets in
  parallel.
- The direct module-level shell commands remain supported for focused manual
  reruns, but they are not the documented `full` workflow:
  - `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell -v`
  - `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_script_editor_dock -v`
  - `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_shell_run_controller -v`
  - `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_shell_project_session_controller -v`
- Do not replace the dedicated shell-isolation phase with `unittest discover`,
  shared `ShellWindow()` reuse, or shell coverage folded back into the earlier
  pytest phases.

## Baseline Timings From The Packet Manifest

| Baseline Measurement | Recorded Value | Why It Matters |
|---|---|---|
| `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest -q --durations=30` | about `193.88s` for `450` collected tests | Establishes the pre-packet baseline that motivated the split verification workflow |
| `tests/test_main_window_shell.py` | about `100.12s` | Shows why shell-backed coverage stayed out of the default pytest phases before the dedicated shell-isolation phase was introduced |
| `tests/test_shell_project_session_controller.py` | about `25.11s` | Confirms that another shell-backed module was expensive enough to justify a separate shell-isolation phase |
| Fresh `ShellWindow()` construction | about `870ms` | Startup cost is dominated by QML shell loading through `QQuickWidget.setSource(...)`, not registry bootstrap |

## Published Shell-Tail Benchmark Evidence

| Workflow Shape | Recorded Result | Notes |
|---|---|---|
| Old sequential shell-tail baseline | `77.776s` mean across `3` reps | Historical packet-doc baseline for the prior `full` shell tail |
| Dedicated shell-isolation phase | `26 passed in 57.27s` | Accepted `P04` measurement for `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_shell_isolation_phase.py -q -n 12 --dist load` on this host |

- Compared against the old `3`-rep mean, the accepted dedicated shell-isolation
  run is `20.506s` faster, about `26.4%` lower elapsed time.
- The new result keeps fresh-process shell isolation because each of the `26`
  shell targets still runs in its own child interpreter.

## Current Environment Notes

- Run the workflow with the project-local interpreter:
  `./venv/Scripts/python.exe`. The repo uses a Windows-style virtualenv layout
  even when opened from `bash`.
- `scripts/run_verification.py` applies `QT_QPA_PLATFORM=offscreen` to its
  child verification commands, so the top-level runner invocations do not need
  extra environment variables.
- `pytest-xdist` is declared in `pyproject.toml` and `requirements.txt`, and it
  is installed in the project venv as of `2026-03-18`. On this machine,
  `resolve_max_parallel_workers()` resolves `12` via
  `psutil.cpu_count(logical=True)`, so `fast` and the dedicated
  shell-isolation phase emit `-n 12 --dist load`, while `gui` caps that
  resolved value to `6` workers. If the plugin is unavailable in another
  environment, `scripts/run_verification.py` still falls back to serial pytest
  and prints the runner notice.

## Companion Proof Audit

- `./venv/Scripts/python.exe scripts/check_traceability.py` validates the
  packet-owned proof layer in `README.md`, `docs/GETTING_STARTED.md`,
  `docs/specs/requirements/TRACEABILITY_MATRIX.md`, and the packet-owned docs
  under `docs/specs/perf/`.
- The current closeout evidence for those proof layers is summarized in
  `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_QA_MATRIX.md`.
- Run the checker after editing verification docs, archived QA evidence
  summaries, or packet-owned traceability references.

## Current Baseline Status

- `./venv/Scripts/python.exe -m pytest tests/test_serializer.py -k passive_image_panel_properties_and_size -q`
  passed on `2026-03-18`, so the earlier passive image-panel serializer caveat
  is retired.
- No known out-of-scope verification baseline failures remain in this matrix.
  `docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_QA_MATRIX.md`
  records the current closeout evidence and carried-forward residual risks. If
  a new environment-specific failure appears, record it here before claiming
  the aggregate workflow is fully green.

## 2026-03-18 Verification Results

| Command | Result | Notes |
|---|---|---|
| `./venv/Scripts/python.exe scripts/run_verification.py --mode full --dry-run` | PASS | Enumerated `fast`, `gui`, `slow`, and the dedicated shell-isolation phase; each non-shell pytest phase included all five `--ignore=` entries, `fast` and the shell-isolation phase emitted `-n 12 --dist load`, and `gui` emitted `-n 6 --dist load` in the current project venv |
| `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_shell_isolation_phase.py -q -n 12 --dist load` | PASS | Accepted `P04` shell-isolation benchmark evidence: `26 passed in 57.27s` |
| `./venv/Scripts/python.exe -m pytest tests/test_serializer.py -k passive_image_panel_properties_and_size -q` | PASS | The previous serializer spot-check caveat no longer reproduces in the current project venv |

## 2026-03-20 ARCH_FIFTH_PASS Closeout Results

| Command | Result | Notes |
|---|---|---|
| `./venv/Scripts/python.exe scripts/check_traceability.py` | PASS | The packet-owned proof audit passed after the spec index links, architecture snapshot, traceability matrix anchors, and fifth-pass closeout matrix were refreshed. |
| `./venv/Scripts/python.exe scripts/run_verification.py --mode fast --dry-run` | PASS | The dry-run output kept the manifest-owned `fast` workflow, ignore list, and worker-resolution behavior aligned with the refreshed proof docs. |
