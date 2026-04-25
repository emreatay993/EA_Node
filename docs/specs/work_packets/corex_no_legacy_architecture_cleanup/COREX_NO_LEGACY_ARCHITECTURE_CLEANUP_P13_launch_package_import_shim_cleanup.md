# COREX_NO_LEGACY_ARCHITECTURE_CLEANUP P13: Launch Package Import Shim Cleanup

## Objective

- Collapse launch, package, telemetry, lazy import, script-wrapper, and packaging-path shims onto canonical entry points and explicit modules.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and only startup/package/import/script files needed for this packet

## Preconditions

- `P12` is marked `PASS`.

## Execution Dependencies

- `P12`

## Target Subsystems

- `main.py`
- `pyproject.toml`
- `ea_node_editor.spec`
- `ea_node_editor/app.py`
- `ea_node_editor/bootstrap.py`
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/telemetry/performance_harness.py`
- `ea_node_editor/ui/perf/__init__.py`
- `ea_node_editor/ui_qml/__init__.py`
- `ea_node_editor/ui/__init__.py`
- `ea_node_editor/ui/shell/__init__.py`
- `ea_node_editor/persistence/__init__.py`
- `ea_node_editor/ui/dialogs/__init__.py`
- `ea_node_editor/ui/shell/presenters/__init__.py`
- `ea_node_editor/ui_qml/graph_scene/__init__.py`
- `ea_node_editor/ui_qml/graph_geometry/__init__.py`
- `ea_node_editor/ui/graph_theme/__init__.py`
- `ea_node_editor/ui/theme/__init__.py`
- `scripts/run.sh`
- `scripts/run_verification.py`
- `scripts/build_windows_package.ps1`
- `scripts/build_windows_installer.ps1`
- `scripts/sign_release_artifacts.ps1`
- `scripts/work_packet_gui.ps1`
- `scripts/work_packet_gui.py`
- `scripts/run_work_packets.py`
- `scripts/run_work_packet_thread.py`
- `tests/test_main_bootstrap.py`
- `tests/test_track_h_perf_harness.py`
- `tests/test_persistence_package_imports.py`
- `tests/test_dead_code_hygiene.py`
- `tests/test_run_verification.py`
- `tests/test_shell_theme.py`
- `tests/test_graphics_settings_dialog.py`
- `tests/test_graph_theme_shell.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P13_launch_package_import_shim_cleanup_WRAPUP.md`

## Conservative Write Scope

- `main.py`
- `pyproject.toml`
- `ea_node_editor.spec`
- `ea_node_editor/app.py`
- `ea_node_editor/bootstrap.py`
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/telemetry/performance_harness.py`
- `ea_node_editor/ui/perf/__init__.py`
- `ea_node_editor/ui_qml/__init__.py`
- `ea_node_editor/ui/__init__.py`
- `ea_node_editor/ui/shell/__init__.py`
- `ea_node_editor/persistence/__init__.py`
- `ea_node_editor/ui/dialogs/__init__.py`
- `ea_node_editor/ui/shell/presenters/__init__.py`
- `ea_node_editor/ui_qml/graph_scene/__init__.py`
- `ea_node_editor/ui_qml/graph_geometry/__init__.py`
- `ea_node_editor/ui/graph_theme/__init__.py`
- `ea_node_editor/ui/theme/__init__.py`
- `scripts/run.sh`
- `scripts/run_verification.py`
- `scripts/build_windows_package.ps1`
- `scripts/build_windows_installer.ps1`
- `scripts/sign_release_artifacts.ps1`
- `scripts/work_packet_gui.ps1`
- `scripts/work_packet_gui.py`
- `scripts/run_work_packets.py`
- `scripts/run_work_packet_thread.py`
- `tests/test_main_bootstrap.py`
- `tests/test_track_h_perf_harness.py`
- `tests/test_persistence_package_imports.py`
- `tests/test_dead_code_hygiene.py`
- `tests/test_run_verification.py`
- `tests/test_shell_theme.py`
- `tests/test_graphics_settings_dialog.py`
- `tests/test_graph_theme_shell.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P13_launch_package_import_shim_cleanup_WRAPUP.md`

## Required Behavior

- Select one canonical app launch entry point, preferably `ea_node_editor.bootstrap:main` / console script, and remove redundant root `main.py`, PyInstaller file-target, and shell-script aliases when safe.
- Move interpreter/venv selection to one place; delete duplicate worktree-aware re-exec logic across bootstrap and shell scripts if no longer needed.
- Centralize packaging profile dependency checks and packaged executable path constants used by build, installer, and signing scripts.
- Remove telemetry/performance harness alias module and update callers to the canonical performance harness module.
- Move `QT_QUICK_CONTROLS_STYLE` setup out of `ea_node_editor/ui_qml/__init__.py` import side effects into startup/bootstrap.
- Remove lazy package `__getattr__` barrels and private-internal package re-exports where in-repo callers can import concrete modules directly.
- Move import-time QML registration out of `ui/shell/presenters/__init__.py`.
- Update tests to assert canonical imports and absence of retired shims.

## Non-Goals

- No production feature behavior changes.
- No current runtime/viewer transport changes; P12 owns those.
- No docs closeout; P14 owns public documentation.

## Verification Commands

1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_bootstrap.py tests/test_track_h_perf_harness.py tests/test_persistence_package_imports.py tests/test_dead_code_hygiene.py tests/test_run_verification.py tests/test_shell_theme.py tests/test_graphics_settings_dialog.py tests/test_graph_theme_shell.py --ignore=venv -q`
2. `.\venv\Scripts\python.exe scripts/run_verification.py --mode full --dry-run`

## Review Gate

- `.\venv\Scripts\python.exe -m pytest tests/test_main_bootstrap.py tests/test_dead_code_hygiene.py tests/test_run_verification.py --ignore=venv -q`

## Expected Artifacts

- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P13_launch_package_import_shim_cleanup_WRAPUP.md`

## Acceptance Criteria

- App launch and developer scripts have one explicit canonical path.
- In-repo imports do not depend on lazy compatibility barrels or telemetry aliases.
- Packaging scripts share or clearly derive one artifact layout and dependency profile contract.

## Handoff Notes

- `P14` must update README, architecture docs, and traceability to match the canonical launch/import paths selected here.
