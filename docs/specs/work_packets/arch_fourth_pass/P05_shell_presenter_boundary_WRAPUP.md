# P05 Shell Presenter Boundary Wrap-Up

## Implementation Summary

- Packet: `P05`
- Branch Label: `codex/arch-fourth-pass/p05-shell-presenter-boundary`
- Commit Owner: `worker`
- Commit SHA: `045c0adb8d56255ee0456b0f38f8cb5144b66071`
- Changed Files: `docs/specs/work_packets/arch_fourth_pass/P05_shell_presenter_boundary_WRAPUP.md`, `ea_node_editor/ui/shell/presenters.py`, `ea_node_editor/ui/shell/window.py`, `ea_node_editor/ui_qml/graph_canvas_bridge.py`, `ea_node_editor/ui_qml/shell_inspector_bridge.py`, `ea_node_editor/ui_qml/shell_library_bridge.py`, `ea_node_editor/ui_qml/shell_workspace_bridge.py`, `tests/test_main_window_shell.py`
- Artifacts Produced: `docs/specs/work_packets/arch_fourth_pass/P05_shell_presenter_boundary_WRAPUP.md`, `ea_node_editor/ui/shell/presenters.py`

Added packet-owned shell presenters plus a small workspace UI state model so `ShellWindow` stays the composition root/native dialog host while presenter-owned QML state and commands move behind explicit library, workspace, inspector, and canvas seams. The QML bridges now prefer those presenter providers instead of capturing direct `shell_window` lambdas, `ShellWindow` keeps the same public slots/properties by delegating to the presenter layer, and the packet test slice gained bridge regression coverage that proves presenter preference without breaking existing shell/QML contracts.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_bootstrap tests.test_main_window_shell tests.test_shell_run_controller tests.test_shell_project_session_controller -v`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_bootstrap -v`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: launch the app from this branch with `QT_QPA_PLATFORM` unset in a normal desktop session so the standard shell/QML window loads through the packet worktree venv.
- Library and search smoke: open the node library, filter it with a query, then open graph search and the connection quick-insert overlay from a port. Expected: library results, graph search state, quick-insert results, and graph hints behave exactly as before with no missing actions or stale overlay state.
- Workspace and run smoke: create a second workspace and a second view, rename or reorder them, then run a simple `Start -> Logger -> End` graph. Expected: title bar/run toolbar actions still work, workspace/view state stays in sync, and run controls/status stay unchanged.
- Inspector smoke: select a node, edit an inline property, rename or hide an exposed port on a subnode pin shell, and collapse/expand the selected node from the inspector. Expected: inspector values stay populated, edits apply immediately to the graph model, and no action path regresses when selection changes.
- Canvas smoke: toggle minimap expansion and snap-to-grid, drag or quick-insert a node from the library, and open a subnode scope from the canvas. Expected: canvas preferences still update the scene, quick-insert placement still works, and scope navigation continues to restore the expected workspace/view state.

## Residual Risks

- `create_shell_context_bridges()` still passes `shell_window` as the compatibility anchor, so the bridge-first cleanup is only partial in this packet; `P06` still owns removing the remaining raw compatibility seams from QML roots and bootstrap plumbing.
- Some packet-external shell actions still route through `ShellWindow` compatibility slots even though the packet-owned bridge flows now prefer presenters, so the shell surface is slimmer but not fully decomposed yet.

## Ready for Integration

- Yes: packet-owned shell/QML state and commands now resolve through focused presenters/models, the public shell/QML contract stayed stable, and both required venv commands passed in the packet worktree.
