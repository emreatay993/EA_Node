# P02 Shell Elapsed Cache Projection Wrap-Up

## Implementation Summary

- Packet: `P02`
- Branch Label: `codex/persistent-node-elapsed-times/p02-shell-elapsed-cache-projection`
- Commit Owner: `worker`
- Commit SHA: `3b634f5f64944a1f15ea4ec4387bf98839bb5cfa`
- Changed Files: `docs/specs/work_packets/persistent_node_elapsed_times/P02_shell_elapsed_cache_projection_WRAPUP.md`, `ea_node_editor/ui/shell/controllers/project_session_services_support/document_io_service.py`, `ea_node_editor/ui/shell/controllers/run_controller.py`, `ea_node_editor/ui/shell/state.py`, `ea_node_editor/ui/shell/window_state/run_and_style_state.py`, `tests/test_project_session_controller_unit.py`, `tests/test_run_controller_unit.py`
- Artifacts Produced: `docs/specs/work_packets/persistent_node_elapsed_times/P02_shell_elapsed_cache_projection_WRAPUP.md`

Extended `ShellRunState` with transient started-at tracking and workspace-scoped cached elapsed storage, projected worker timing fields through `RunController` with shell-side fallback timing when the protocol supplies `0.0`, cleared only transient live state on terminal run events, and cleared cached elapsed timing during project installs so timing data cannot leak across session replacement flows.

## Verification

- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_run_controller_unit.py -k persistent_node_elapsed_state --ignore=venv -q`
- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_project_session_controller_unit.py -k persistent_node_elapsed_state --ignore=venv -q`
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_run_controller_unit.py -k persistent_node_elapsed_state --ignore=venv -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Too soon for manual testing.

- Blocker: `P02` stops at shell-state, controller, and project-install timing projection, so there is still no bridge or renderer surface that exposes cached elapsed values for a user-driven check.
- Next condition: Manual testing becomes worthwhile after `P03` exposes the active-workspace timing lookup through the bridge and `P06` renders the persistent footer that consumes it.

## Residual Risks

- The fallback path depends on the normal `node_started` then `node_completed` event sequence; if both worker timing and the shell-started timestamp are unavailable, the shell preserves the prior cached value instead of inventing a replacement.
- All packet verification commands exited successfully, but pytest still emitted the existing non-fatal temp-cleanup `PermissionError` against `pytest-current` during atexit on this Windows worktree.

## Ready for Integration

- Yes: `The packet-owned shell timing state, terminal-event cache semantics, project-install clearing, targeted regressions, and wrap-up are committed on the assigned branch with verification and review gate passing.`
