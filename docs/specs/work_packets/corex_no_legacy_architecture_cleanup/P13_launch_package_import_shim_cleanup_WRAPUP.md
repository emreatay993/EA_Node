# P13 Launch Package Import Shim Cleanup Wrap-Up

## Implementation Summary

- Packet: `P13`
- Branch Label: `codex/corex-no-legacy-architecture-cleanup/p13-launch-package-import-shim-cleanup`
- Commit Owner: `worker`
- Commit SHA: `dfd3ab4b746a13628f4eb2d803bd653809092d89`
- Changed Files: `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P13_launch_package_import_shim_cleanup_WRAPUP.md`, `ea_node_editor.spec`, `ea_node_editor/app.py`, `ea_node_editor/app_preferences.py`, `ea_node_editor/bootstrap.py`, `ea_node_editor/persistence/__init__.py`, `ea_node_editor/telemetry/performance_harness.py`, `ea_node_editor/ui/__init__.py`, `ea_node_editor/ui/dialogs/__init__.py`, `ea_node_editor/ui/perf/__init__.py`, `ea_node_editor/ui/shell/__init__.py`, `ea_node_editor/ui/shell/presenters/__init__.py`, `ea_node_editor/ui_qml/__init__.py`, `ea_node_editor/ui_qml/graph_scene/__init__.py`, `main.py`, `scripts/build_windows_installer.ps1`, `scripts/build_windows_package.ps1`, `scripts/run.sh`, `scripts/sign_release_artifacts.ps1`, `tests/test_dead_code_hygiene.py`, `tests/test_graph_theme_shell.py`, `tests/test_graphics_settings_dialog.py`, `tests/test_main_bootstrap.py`, `tests/test_persistence_package_imports.py`, `tests/test_shell_theme.py`, `tests/test_track_h_perf_harness.py`
- Artifacts Produced: `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P13_launch_package_import_shim_cleanup_WRAPUP.md`

P13 collapses app launch onto `ea_node_editor.bootstrap:main`, deletes the root `main.py` launcher and telemetry performance-harness alias module, moves Windows Quick Controls style setup into bootstrap-owned startup, and removes lazy package barrels from packet-owned package roots. The PyInstaller spec now targets the bootstrap module, `scripts/run.sh` invokes `-m ea_node_editor.bootstrap`, packaging scripts derive package profile artifact paths through shared local helpers, and QML type registration no longer happens from `ui/shell/presenters/__init__.py`.

## Verification

- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_bootstrap.py tests/test_track_h_perf_harness.py tests/test_persistence_package_imports.py tests/test_dead_code_hygiene.py tests/test_run_verification.py tests/test_shell_theme.py tests/test_graphics_settings_dialog.py tests/test_graph_theme_shell.py --ignore=venv -q` (`102 passed, 4 warnings, 41 subtests passed`)
- PASS: `.\venv\Scripts\python.exe scripts/run_verification.py --mode full --dry-run` (printed all full-mode dry-run phases and exited `0`)
- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_main_bootstrap.py tests/test_dead_code_hygiene.py tests/test_run_verification.py --ignore=venv -q` (`42 passed, 4 warnings, 13 subtests passed`)
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

1. Prerequisite: use this packet worktree with the project venv available at `.\venv\Scripts\python.exe`.
2. App launch smoke: run `.\venv\Scripts\python.exe -m ea_node_editor.bootstrap`; expected result is that the COREX Node Editor opens without a missing Qt Quick Controls style/plugin error.
3. Shell script smoke: from a Bash-capable shell, run `EA_NODE_EDITOR_PYTHON=./venv/Scripts/python.exe ./scripts/run.sh`; expected result is the same package bootstrap launch path and no attempt to call root `main.py`.
4. Packaging-path dry inspection: run `.\scripts\sign_release_artifacts.ps1 -PackageProfile base -VerifyOnly` only after a package artifact exists; expected result is that signing looks under the profile-specific `artifacts\pyinstaller\dist\base\COREX_Node_Editor\COREX_Node_Editor.exe` layout.

## Residual Risks

- Existing Ansys DPF operator rename warnings appear during verification and are unrelated to P13.
- Two broader, unscoped legacy tests still assert pre-P13 `main.py` and literal packaging-script strings; they were not edited because they are outside the packet write scope.

## Ready for Integration

- Yes: Required P13 verification and review gate passed, and the packet branch contains only packet-scoped launch, package, import-shim, and test updates.
