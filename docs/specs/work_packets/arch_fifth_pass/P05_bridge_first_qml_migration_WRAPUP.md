# P05 Bridge-First QML Migration Wrap-Up

## Implementation Summary

- Packet: `P05`
- Branch Label: `codex/arch-fifth-pass/p05-bridge-first-qml-migration`
- Commit Owner: `worker`
- Commit SHA: `0bb412c0d70a5c5562575a511783b44ec0faefab`
- Changed Files: `ea_node_editor/ui_qml/MainShell.qml`, `ea_node_editor/ui_qml/components/GraphCanvas.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasMinimapOverlay.qml`, `ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml`, `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`, `ea_node_editor/ui_qml/shell_context_bootstrap.py`, `tests/test_main_window_shell.py`, `docs/specs/work_packets/arch_fifth_pass/P05_bridge_first_qml_migration_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/arch_fifth_pass/P05_bridge_first_qml_migration_WRAPUP.md`, `ea_node_editor/ui_qml/MainShell.qml`, `ea_node_editor/ui_qml/components/GraphCanvas.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasMinimapOverlay.qml`, `ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml`, `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`, `ea_node_editor/ui_qml/shell_context_bootstrap.py`, `tests/test_main_window_shell.py`

`MainShell.qml` and `WorkspaceCenterPane.qml` now bind the shell to `graphCanvasStateBridge` and `graphCanvasCommandBridge` directly, and `shell_context_bootstrap.py` no longer exports the raw `mainWindow`, `sceneBridge`, or `viewBridge` globals. `GraphCanvas.qml` and its packet-owned child components now route packet-owned reads through state bridges and mutations through command bridges while preserving the legacy `GraphCanvas` property surface for direct callers and out-of-scope consumers.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_window_shell.py tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_controls.py tests/test_graph_surface_input_inline.py tests/test_passive_graph_surface_host.py tests/test_track_h_perf_harness.py -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_window_shell.py -q -k "GraphCanvasBridgeTests or MainWindowShellContextBootstrapTests"`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

1. Prerequisite: launch this branch with the repository venv available at `./venv/Scripts/python.exe`; if this dedicated worktree is reopened elsewhere, recreate the temporary local `venv` junction before rerunning the packet commands here.
2. Action: start the shell and confirm the main window loads without QML binding errors. Expected result: the shell opens normally, the graph canvas renders, and no missing `mainWindow`/`sceneBridge`/`viewBridge` context-property errors appear.
3. Action: pan with middle-drag, zoom with the wheel, drag a marquee selection, then use `Alt+Left` and `Alt+Home` on the canvas. Expected result: viewport motion, selection, and scope navigation behave exactly as before the bridge-first migration.
4. Action: expand the minimap, click or drag inside it to recenter, then open edge and node context menus and trigger representative actions. Expected result: minimap recentering still works, context menus open and close correctly, and their actions still route through the shell without visible regressions.

## Residual Risks

- The dedicated worktree still required a temporary Windows `./venv` junction to run the exact packet commands because packet worktrees do not carry their own checked-out virtualenv.
- `graphCanvasBridge` remains exported as the public compatibility adapter for direct `GraphCanvas` callers, but packet-owned shell/QML paths now use `graphCanvasStateBridge` and `graphCanvasCommandBridge`.

## Ready for Integration

- Yes: packet-owned shell/canvas QML no longer relies on the raw `mainWindow`/`sceneBridge`/`viewBridge` globals, and both packet verification gates passed under offscreen Qt.
