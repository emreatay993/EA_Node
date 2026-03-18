# P03 Regression Locks Wrap-Up

## Implementation Summary

- Packet: `P03`
- Branch Label: `codex/dead-code-hygiene/p03-regression-locks`
- Commit Owner: `worker`
- Commit SHA: `2bae738cd81dd34fd4409282138b6168b43c08d9`
- Changed Files: `tests/test_main_window_shell.py`, `tests/test_dead_code_hygiene.py`, `docs/specs/work_packets/dead_code_hygiene/P03_regression_locks_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/dead_code_hygiene/P03_regression_locks_WRAPUP.md`, `tests/test_dead_code_hygiene.py`

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell.ShellLibraryBridgeQmlBoundaryTests tests.test_main_window_shell.ShellInspectorBridgeQmlBoundaryTests tests.test_main_window_shell.ShellWorkspaceBridgeQmlBoundaryTests tests.test_main_window_shell.GraphCanvasQmlBoundaryTests tests.test_main_window_shell.MainWindowShellContextBootstrapTests -v`
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_icon_registry.py tests/test_window_library_inspector.py tests/test_execution_client.py tests/test_execution_worker.py tests/test_graph_track_b.py -q`
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_dead_code_hygiene.py -q`
- PASS: `git diff --check -- tests/test_main_window_shell.py tests/test_dead_code_hygiene.py`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: launch the desktop app from this branch with the main shell window and graph canvas available.
- Action: open the title bar, run toolbar, node library, graph search, quick insert, inspector pane, script editor overlay, workspace tabs, and console surfaces.
- Expected result: the shell behaves normally with no missing bindings or QML warnings caused by restoring removed `mainWindowRef`, `workspaceTabsBridgeRef`, or `consoleBridgeRef` plumbing.
- Action: on the graph canvas, double-click empty space and drag from a port into connection quick insert.
- Expected result: the quick-insert and related overlay paths still position correctly because the retained `overlayHostItem` handoff remains live.

## Residual Risks

- `overlayHostItem` remains intentionally live because `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml:134` and `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml:658` still read it through the `MainShell.qml` -> `WorkspaceCenterPane.qml` -> `GraphCanvas.qml` handoff.
- `WorkspaceCenterPane.qml` intentionally retains `mainWindowRef`, `sceneBridgeRef`, and `viewBridgeRef` because `GraphCanvas` still consumes them via `mainWindowBridge`, `sceneBridge`, and `viewBridge`; P03 locks that seam instead of treating it as dead.
- Broader out-of-scope public/package surfaces remain intentionally untouched: `AsyncNodePlugin`, `icon_names`, `list_installed_packages`, `uninstall_package`, and package `__all__` re-export surfaces.

## Ready for Integration

- Yes: P03 adds the requested static regression locks for the accepted P01 and P02 cleanup boundaries, reruns the required verification slices, and leaves no blocker inside packet scope.
