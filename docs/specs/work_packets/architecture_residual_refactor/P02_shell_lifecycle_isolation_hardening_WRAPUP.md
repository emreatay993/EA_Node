## Implementation Summary

- Packet: `P02`
- Branch Label: `codex/architecture-residual-refactor/p02-shell-lifecycle-isolation-hardening`
- Commit Owner: `worker`
- Commit SHA: `4c6f20e2dbce5349ee07c10d2a3c72cd6e752fff`
- Changed Files: `docs/specs/work_packets/architecture_residual_refactor/P02_shell_lifecycle_isolation_hardening_WRAPUP.md`, `ea_node_editor/ui/shell/composition.py`, `ea_node_editor/ui/shell/window.py`, `ea_node_editor/ui_qml/viewer_host_service.py`, `scripts/verification_manifest.py`, `tests/main_window_shell/base.py`, `tests/shell_isolation_runtime.py`, `tests/test_shell_isolation_phase.py`, `tests/test_shell_window_lifecycle.py`
- Artifacts Produced: `docs/specs/work_packets/architecture_residual_refactor/P02_shell_lifecycle_isolation_hardening_WRAPUP.md`, `tests/test_shell_window_lifecycle.py`, `ea_node_editor/ui/shell/window.py`, `ea_node_editor/ui/shell/composition.py`, `ea_node_editor/ui_qml/viewer_host_service.py`, `tests/main_window_shell/base.py`, `tests/shell_isolation_runtime.py`, `tests/test_shell_isolation_phase.py`, `scripts/verification_manifest.py`

- Hardened `ShellWindow` teardown so close now stops packet-owned timers, disconnects the application-state signal, unloads the `QQuickWidget` source before deletion, and suppresses deferred autosave recovery once teardown starts.
- Added a `ViewerHostService.shutdown(...)` path and invoked it during window close so overlay bindings and queued sync work are released deterministically before the embedded QML surface is torn down.
- Aligned the composition factory with the direct constructor by wiring the application-state lifecycle signal for factory-created windows too, so both creation paths follow the same close behavior.
- Replaced the test-only manual QML cleanup in `tests/main_window_shell/base.py` with the packet-owned close path, added focused in-process lifecycle regressions, and normalized stale shell-isolation pytest nodeids through the packet-owned runtime helper so the phase catalog still resolves on the current test layout.

## Verification

- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_shell_window_lifecycle.py tests/shell_isolation_runtime.py tests/test_shell_isolation_phase.py --ignore=venv -q` (`32 passed in 60.90s`)
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_shell_window_lifecycle.py tests/shell_isolation_runtime.py --ignore=venv -q` (`4 passed in 2.79s`)
- Final Verification Verdict: PASS

## Manual Test Directives

Ready for manual testing

Prerequisite: launch the packet worktree build from `C:\w\ea_node_ed-p02-shell-lifecycle` with `.\venv\Scripts\python.exe main.py` in a normal desktop session.

1. Repeated startup/close smoke
Action: launch the app, wait for the shell to finish loading, close it normally, and repeat that cycle three times.
Expected result: each launch reaches the main shell, each close exits cleanly without a crash dialog or hung background process, and the next launch starts normally.

2. Focus-loss and close smoke
Action: with the shell open, switch focus away from the app and back once, then close the app and relaunch it.
Expected result: focus changes do not produce visible shell errors, the close still exits cleanly, and the relaunched shell opens without stale viewer-overlay behavior or teardown warnings.

Automated verification remains the primary proof for this packet because the change is mostly internal lifecycle cleanup.

## Residual Risks

- The broader shell verification story still uses fresh child-process target catalogs for many legacy shell-backed suites; this packet proves packet-owned repeated `ShellWindow` teardown, not a full collapse of every shell regression into one long-lived pytest process.
- The runtime helper now normalizes legacy `tests/test_main_window_shell.py` nodeids to the current split test modules, so future shell test moves should update the packet-owned alias map or the underlying catalog together.

## Ready for Integration

- Yes: packet-owned lifecycle teardown is deterministic across repeated in-process windows, the inherited shell-isolation command passes again, and the required packet verification and review gate both passed on the packet branch.
