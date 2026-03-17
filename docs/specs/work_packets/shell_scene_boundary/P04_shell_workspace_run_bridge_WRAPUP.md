# P04 Shell Workspace Run Bridge Wrap-Up

## Summary
- Implemented `ShellWorkspaceBridge` as the focused workspace/run/title/console facade for QML-owned shell concerns.
- Migrated `ShellTitleBar.qml`, `ShellRunToolbar.qml`, `WorkspaceCenterPane.qml`, and `ScriptEditorOverlay.qml` to consume `shellWorkspaceBridge` for packet-owned concerns.
- Preserved existing `GraphCanvas` wiring and retained component surface properties (`mainWindowRef`, `workspaceTabsBridgeRef`, `consoleBridgeRef`) where needed for compatibility.
- Added bridge behavior and QML boundary coverage in `tests/test_main_window_shell.py`.
- Added subprocess isolation loaders in `tests/test_shell_run_controller.py` and `tests/test_script_editor_dock.py` to avoid known Windows Qt/QML multi-`ShellWindow` access violations during required verification runs.

## Changed Files
- `ea_node_editor/ui_qml/shell_workspace_bridge.py`
- `ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml`
- `ea_node_editor/ui_qml/components/shell/ShellRunToolbar.qml`
- `ea_node_editor/ui_qml/components/shell/ShellTitleBar.qml`
- `ea_node_editor/ui_qml/components/shell/ScriptEditorOverlay.qml`
- `tests/test_main_window_shell.py`
- `tests/test_shell_run_controller.py`
- `tests/test_script_editor_dock.py`

## Verification
- PASS: `./venv/Scripts/python.exe -m py_compile ea_node_editor/ui_qml/shell_workspace_bridge.py tests/test_main_window_shell.py tests/test_shell_run_controller.py tests/test_script_editor_dock.py`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell.ShellWorkspaceBridgeTests tests.test_main_window_shell.ShellWorkspaceBridgeQmlBoundaryTests -v` (`3` tests)
- PASS: `git diff --check -- <P04 target files>`
- PASS (required): `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell tests.test_shell_run_controller tests.test_workspace_manager tests.test_script_editor_dock -v` (`143` tests, `OK`, `195.134s`)

## Residual Risks
- `ShellWorkspaceBridge` remains a forwarding facade over existing `ShellWindow`/workspace-tabs/console contracts; future shell state additions still require explicit bridge expansion.
- Subprocess isolation for shell-window-heavy tests reduces crash risk but increases runtime and may hide cross-test shared-state issues that only appear in single-process execution.

## Ready For Review
- READY
