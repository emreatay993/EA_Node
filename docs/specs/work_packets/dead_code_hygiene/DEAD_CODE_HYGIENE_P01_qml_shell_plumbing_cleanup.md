# DEAD_CODE_HYGIENE P01: QML Shell Plumbing Cleanup

## Objective
- Remove provably unread shell-surface property plumbing rooted at `MainShell.qml` and the owned shell components under `ea_node_editor/ui_qml/components/shell/`, while preserving all live bridge/context contracts and current runtime behavior.

## Preconditions
- `P00` is marked `PASS` in [DEAD_CODE_HYGIENE_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/dead_code_hygiene/DEAD_CODE_HYGIENE_STATUS.md).
- No later `DEAD_CODE_HYGIENE` packet is in progress.

## Execution Dependencies
- none

## Target Subsystems
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/shell/NodeLibraryPane.qml`
- `ea_node_editor/ui_qml/components/shell/GraphSearchOverlay.qml`
- `ea_node_editor/ui_qml/components/shell/ConnectionQuickInsertOverlay.qml`
- `ea_node_editor/ui_qml/components/shell/GraphHintOverlay.qml`
- `ea_node_editor/ui_qml/components/shell/LibraryWorkflowContextPopup.qml`
- `ea_node_editor/ui_qml/components/shell/ScriptEditorOverlay.qml`
- `ea_node_editor/ui_qml/components/shell/ShellRunToolbar.qml`
- `ea_node_editor/ui_qml/components/shell/ShellTitleBar.qml`
- `ea_node_editor/ui_qml/components/shell/InspectorPane.qml`
- `ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml`
- `tests/test_main_window_shell.py` only if a packet-owned boundary assertion must move to keep the slice green

## Conservative Write Scope
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/shell/NodeLibraryPane.qml`
- `ea_node_editor/ui_qml/components/shell/GraphSearchOverlay.qml`
- `ea_node_editor/ui_qml/components/shell/ConnectionQuickInsertOverlay.qml`
- `ea_node_editor/ui_qml/components/shell/GraphHintOverlay.qml`
- `ea_node_editor/ui_qml/components/shell/LibraryWorkflowContextPopup.qml`
- `ea_node_editor/ui_qml/components/shell/ScriptEditorOverlay.qml`
- `ea_node_editor/ui_qml/components/shell/ShellRunToolbar.qml`
- `ea_node_editor/ui_qml/components/shell/ShellTitleBar.qml`
- `ea_node_editor/ui_qml/components/shell/InspectorPane.qml`
- `ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml` only if `overlayHostItem` removal is conclusively proven safe and requires deleting the final handoff
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml` only if `overlayHostItem` removal is conclusively proven safe and requires deleting the final runtime read
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml` only if `overlayHostItem` removal is conclusively proven safe and requires deleting the final runtime read
- `tests/test_main_window_shell.py`
- `docs/specs/work_packets/dead_code_hygiene/P01_qml_shell_plumbing_cleanup_WRAPUP.md`

## Required Behavior
- Remove the unread `mainWindowRef` property declarations from:
  - `NodeLibraryPane.qml`
  - `GraphSearchOverlay.qml`
  - `ConnectionQuickInsertOverlay.qml`
  - `GraphHintOverlay.qml`
  - `LibraryWorkflowContextPopup.qml`
  - `ScriptEditorOverlay.qml`
  - `ShellRunToolbar.qml`
  - `ShellTitleBar.qml`
  - `InspectorPane.qml`
- Remove the corresponding `mainWindowRef: mainWindow` call-site assignments from `MainShell.qml`.
- Remove the unread `workspaceTabsBridgeRef` and `consoleBridgeRef` property declarations from `WorkspaceCenterPane.qml` and the corresponding assignments from `MainShell.qml`.
- Keep `sceneBridgeRef`, `viewBridgeRef`, all registered global context-property names, and all focused bridge object names stable.
- Check `overlayHostItem` after the unused caller plumbing is removed:
  - if no runtime read remains, remove it cleanly and keep behavior stable
  - if runtime reads still exist, retain it and record that retention explicitly in the packet wrap-up and status ledger
- Do not change visual layout, focus behavior, overlay stacking, console behavior, graph-canvas behavior, or bridge ownership.
- Keep any test edits narrowly limited to packet-owned QML boundary expectations if the current assertions need to move with the cleanup.

## Non-Goals
- No renaming or removal of global context properties.
- No renaming or removal of `sceneBridgeRef` or `viewBridgeRef`.
- No removal of inspector selected-node APIs or `shellInspectorBridge` behavior.
- No `GraphCanvas` behavioral refactor beyond a provably dead `overlayHostItem` handoff if it is truly unused.
- No Python helper cleanup. `P02` owns that.
- No broad regression-test expansion. `P03` owns that.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell.ShellLibraryBridgeQmlBoundaryTests tests.test_main_window_shell.ShellInspectorBridgeQmlBoundaryTests tests.test_main_window_shell.ShellWorkspaceBridgeQmlBoundaryTests tests.test_main_window_shell.GraphCanvasQmlBoundaryTests tests.test_main_window_shell.MainWindowShellContextBootstrapTests -v`

## Review Gate
- `git diff --check -- ea_node_editor/ui_qml/MainShell.qml ea_node_editor/ui_qml/components/shell tests/test_main_window_shell.py`

## Expected Artifacts
- `docs/specs/work_packets/dead_code_hygiene/P01_qml_shell_plumbing_cleanup_WRAPUP.md`

## Acceptance Criteria
- The verification command passes.
- The requested unread `mainWindowRef`, `workspaceTabsBridgeRef`, and `consoleBridgeRef` plumbing is removed from the owned shell surface without breaking the existing QML boundary suites.
- `sceneBridgeRef`, `viewBridgeRef`, global context-property names, bridge object names, and current graph-canvas integration methods remain stable.
- `overlayHostItem` is removed only if the packet proves it has no remaining runtime reads; otherwise it remains in place and the wrap-up/status ledger explains why.
- No user-facing shell behavior or visuals intentionally change.

## Handoff Notes
- `P03` should freeze the final QML boundary by asserting the removed property declarations and `MainShell.qml` call-site assignments do not return.
- If `overlayHostItem` remains, record the exact surviving read locations so later cleanup does not rediscover the same boundary from scratch.
