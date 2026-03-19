# P06 Bridge-First QML Contract Cleanup Wrap-Up

## Implementation Summary

- Packet: `P06`
- Branch Label: `codex/arch-fourth-pass/p06-bridge-first-qml-contract-cleanup`
- Commit Owner: `worker`
- Commit SHA: `3e1202e27e05c1bd056861b282f69b1bb46a97ce`
- Changed Files: `docs/specs/work_packets/arch_fourth_pass/P06_bridge_first_qml_contract_cleanup_WRAPUP.md`, `ea_node_editor/ui/shell/controllers/workspace_view_nav_ops.py`, `ea_node_editor/ui/shell/window_library_inspector.py`, `ea_node_editor/ui/support/__init__.py`, `ea_node_editor/ui/support/node_presentation.py`, `ea_node_editor/ui_qml/MainShell.qml`, `ea_node_editor/ui_qml/components/GraphCanvas.qml`, `ea_node_editor/ui_qml/graph_canvas_bridge.py`, `ea_node_editor/ui_qml/graph_scene_payload_builder.py`, `ea_node_editor/ui_qml/shell_context_bootstrap.py`, `tests/test_graph_surface_input_contract.py`, `tests/test_main_window_shell.py`
- Artifacts Produced: `docs/specs/work_packets/arch_fourth_pass/P06_bridge_first_qml_contract_cleanup_WRAPUP.md`, `ea_node_editor/ui/support/node_presentation.py`, `ea_node_editor/ui_qml/graph_canvas_bridge.py`

Moved the packet-owned shell root and canvas path onto a bridge-first contract by feeding `MainShell.qml` bridge refs into the workspace center pane, wiring `GraphCanvas.qml` input/context-menu flows against the unified canvas bridge, and expanding `GraphCanvasBridge` so the packet-owned canvas route can satisfy shell, scene, and view responsibilities without falling back to raw `mainWindow`, `sceneBridge`, or `viewBridge` for its primary behavior. The raw compatibility context exports remain in `shell_context_bootstrap.py` only for deferred or non-packet-owned consumers.

Moved shared node presentation helpers out of the shell-specific inspector module into the neutral `ea_node_editor.ui.support.node_presentation` support module, then repointed the shell and QML-side importers so packet-owned helper flow no longer crosses the `ui` / `ui_qml` seam through `ui.shell.window_library_inspector`. The packet tests now lock both the file-level contract cleanup and a live QML probe that exercises surface edits through the unified `canvasBridge` contract.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell tests.test_graph_scene_bridge_bind_regression tests.test_graph_surface_input_contract tests.test_passive_graph_surface_host -v`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell -v`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: launch the app from this branch in a normal desktop session using the packet worktree venv so the QML shell loads through the bridge-first canvas path.
- Shell and canvas smoke: open a workspace with a few nodes, drag-select nodes, pan and zoom the canvas, toggle minimap expansion, and double-click empty canvas space to open quick insert. Expected: selection, viewport movement, minimap state, and quick insert all work normally with no missing actions.
- Surface editing smoke: place a `Logger` or passive/media node with inline surface controls, edit an inline property from the node surface, and use any path-browse or crop entry point exposed by that node type. Expected: the edit commits immediately through the canvas contract and the node stays selected and focused correctly.
- Context menu smoke: right-click a passive node and a flow edge, run rename/remove/style actions, and enter a subnode scope from the node context menu when available. Expected: node and edge actions still resolve correctly and scope navigation still opens the expected view.
- Compatibility smoke: open graph search and the inspector after using the canvas flows above. Expected: packet-owned roots behave through the focused bridges while deferred compatibility consumers still populate and operate normally.

## Residual Risks

- `shell_context_bootstrap.py` still publishes raw `mainWindow`, `sceneBridge`, `viewBridge`, `consoleBridge`, and `workspaceTabsBridge` context properties for deferred or packet-external consumers, so the compatibility surface still exists even though packet-owned roots no longer depend on it for their primary path.
- `GraphCanvasBridge` now carries a wider unified canvas contract to keep packet-owned QML bridge-first without breaking compatibility. A later pass could narrow that contract again once the remaining deferred consumers are removed.

## Ready for Integration

- Yes: packet-owned QML roots and canvas flows now resolve through the focused bridge contract first, the shared helper leak moved into a neutral support module, and both required venv verification commands passed.
