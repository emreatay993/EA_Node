# P01 QML Shell Plumbing Cleanup Wrap-Up

## Implementation Summary

- Packet: `P01`
- Branch Label: `codex/dead-code-hygiene/p01-qml-shell-plumbing-cleanup`
- Commit Owner: `worker`
- Commit SHA: `965390b41f342e813ecdd8328e7e28dae033fca0`
- Changed Files: `ea_node_editor/ui_qml/MainShell.qml`, `ea_node_editor/ui_qml/components/shell/NodeLibraryPane.qml`, `ea_node_editor/ui_qml/components/shell/GraphSearchOverlay.qml`, `ea_node_editor/ui_qml/components/shell/ConnectionQuickInsertOverlay.qml`, `ea_node_editor/ui_qml/components/shell/GraphHintOverlay.qml`, `ea_node_editor/ui_qml/components/shell/LibraryWorkflowContextPopup.qml`, `ea_node_editor/ui_qml/components/shell/ScriptEditorOverlay.qml`, `ea_node_editor/ui_qml/components/shell/ShellRunToolbar.qml`, `ea_node_editor/ui_qml/components/shell/ShellTitleBar.qml`, `ea_node_editor/ui_qml/components/shell/InspectorPane.qml`, `ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml`, `tests/test_main_window_shell.py`, `docs/specs/work_packets/dead_code_hygiene/P01_qml_shell_plumbing_cleanup_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/dead_code_hygiene/P01_qml_shell_plumbing_cleanup_WRAPUP.md`

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell.ShellLibraryBridgeQmlBoundaryTests tests.test_main_window_shell.ShellInspectorBridgeQmlBoundaryTests tests.test_main_window_shell.ShellWorkspaceBridgeQmlBoundaryTests tests.test_main_window_shell.GraphCanvasQmlBoundaryTests tests.test_main_window_shell.MainWindowShellContextBootstrapTests -v`
- PASS: `git diff --check -- ea_node_editor/ui_qml/MainShell.qml ea_node_editor/ui_qml/components/shell tests/test_main_window_shell.py`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: launch the app from this branch in the normal desktop workflow with the shell window available.
- Action: verify the title bar, run toolbar, node library, graph search, quick insert, graph hint, script editor overlay, inspector pane, and workspace center all load and respond normally.
- Expected result: the shell behaves exactly as before, with no missing bindings or QML warnings caused by removed `mainWindowRef`, `workspaceTabsBridgeRef`, or `consoleBridgeRef` plumbing.
- Action: open a graph, right-click a custom workflow in the node library, and confirm the library workflow context popup still opens and its actions work.
- Expected result: rename/scope/delete actions still route through `shellLibraryBridge` without any popup placement or interaction regression.
- Action: interact with the graph canvas paths that use overlays, including library drag preview and connection quick insert.
- Expected result: overlay positioning remains correct because `overlayHostItem` is still retained through the `WorkspaceCenterPane` and `GraphCanvas` handoff.

## Residual Risks

- `overlayHostItem` remains live and was intentionally retained. Surviving runtime reads are in `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml:134` and `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml:658`, with the handoff still flowing through `ea_node_editor/ui_qml/MainShell.qml`, `ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml`, and `ea_node_editor/ui_qml/components/GraphCanvas.qml`.
- The verification slice covers the shell QML boundary and context bootstrap, but it does not exercise every interactive shell path at runtime; manual smoke validation is still useful for popup and overlay behavior.

## Ready for Integration

- Yes: the unread shell plumbing targeted by P01 was removed, the packet verification command passed, the review gate passed, and no integration blocker remains inside packet scope.
