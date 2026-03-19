# P01 Startup And Preferences Boundary Wrap-Up

## Implementation Summary

- Packet: `P01`
- Branch Label: `codex/arch-fifth-pass/p01-startup-preferences-boundary`
- Commit Owner: `worker`
- Commit SHA: `n/a`
- Changed Files: `main.py`, `pyproject.toml`, `ea_node_editor/bootstrap.py`, `ea_node_editor/app.py`, `ea_node_editor/app_preferences.py`, `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`, `ea_node_editor/ui/perf/__init__.py`, `ea_node_editor/ui/perf/performance_harness.py`, `ea_node_editor/telemetry/performance_harness.py`, `tests/test_main_bootstrap.py`, `tests/test_graphics_settings_preferences.py`, `tests/test_track_h_perf_harness.py`, `docs/specs/work_packets/arch_fifth_pass/P01_startup_preferences_boundary_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/arch_fifth_pass/P01_startup_preferences_boundary_WRAPUP.md`, `ea_node_editor/bootstrap.py`, `ea_node_editor/app_preferences.py`, `ea_node_editor/ui/perf/__init__.py`, `ea_node_editor/ui/perf/performance_harness.py`

Startup now flows through `ea_node_editor.bootstrap.main` for both `main.py` source launch and the installed `ea-node-editor` console script target. App-preferences normalization/persistence and startup theme resolution were extracted into `ea_node_editor.app_preferences`, while `AppPreferencesController` remains the host-facing adapter and preserves its existing patch surface for shell tests. The QML performance harness implementation now lives under `ea_node_editor.ui.perf`, and `ea_node_editor.telemetry.performance_harness` remains a compatibility shim that preserves the public import path.

## Verification

- PASS: `./venv/Scripts/python.exe -m pytest tests/test_main_bootstrap.py tests/test_graphics_settings_preferences.py tests/test_graph_theme_preferences.py tests/test_track_h_perf_harness.py -q`
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_main_bootstrap.py -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

1. Prerequisite: use the project venv interpreter at `/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/venv/Scripts/python.exe` until this dedicated worktree has its own local `venv/`.
2. Action: launch the app from source with `/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/venv/Scripts/python.exe main.py`, then relaunch it from the installed console entrypoint `ea-node-editor` in the same environment. Expected result: both entrypoints open the same application flow and apply the same persisted shell theme on startup.
3. Action: open Graphics Settings, switch the shell theme, close the app, and relaunch it. Expected result: the selected theme persists and is already applied when the shell first appears.
4. Action: run `/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 80 --edges 220 --load-iterations 1 --interaction-samples 8 --baseline-runs 1`. Expected result: the benchmark completes through the compatibility import path and writes the Track H report artifacts under `docs/specs/perf`.

## Residual Risks

- The dedicated packet worktree does not currently contain its own `./venv/`, so exact packet verification was executed through a temporary Windows junction that pointed `./venv` at the repository venv.
- Broader shell integration suites were not rerun in this packet; verification stayed scoped to the packet-owned bootstrap, preferences, and Track H regression tests.

## Ready for Integration

- Yes: startup/bootstrap, startup theme resolution, and performance-harness ownership all meet the packet acceptance criteria and the packet verification plus review gate passed.
