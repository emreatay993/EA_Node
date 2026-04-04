## Implementation Summary
Packet: `P01`
Branch Label: `codex/ui-context-scalability-refactor/p01-shell-window-facade-collapse`
Commit Owner: `worker`
Commit SHA: `1e873e15c2d959a4cc4282945a774a22804e2b68`
Changed Files:
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_actions.py`
- `ea_node_editor/ui/shell/window_state_helpers.py`
- `tests/test_main_bootstrap.py`
- `tests/test_main_window_shell.py`
- `docs/specs/work_packets/ui_context_scalability_refactor/P01_shell_window_facade_collapse_WRAPUP.md`
Artifacts Produced:
- `ea_node_editor/ui/shell/window_state_helpers.py`
- `docs/specs/work_packets/ui_context_scalability_refactor/P01_shell_window_facade_collapse_WRAPUP.md`

Collapsed `ShellWindow` into a lifecycle-first facade by moving packet-owned search, quick-insert, graphics-preference, presenter/controller delegation, and recent-project menu helpers into [`window_state_helpers.py`](/C:/w/ea-node-editor-ui-context-p01/ea_node_editor/ui/shell/window_state_helpers.py) and [`window_actions.py`](/C:/w/ea-node-editor-ui-context-p01/ea_node_editor/ui/shell/window_actions.py). [`window.py`](/C:/w/ea-node-editor-ui-context-p01/ea_node_editor/ui/shell/window.py) now keeps the Qt lifecycle, top-level widget ownership, exported facade bindings, and final signal wiring, and it is reduced to 519 lines.

Updated packet-owned regression anchors so the shell budget is enforced in [`tests/test_main_bootstrap.py`](/C:/w/ea-node-editor-ui-context-p01/tests/test_main_bootstrap.py) and the inherited GraphCanvas static contract in [`tests/test_main_window_shell.py`](/C:/w/ea-node-editor-ui-context-p01/tests/test_main_window_shell.py) matches the current split-bridge QML surface.

## Verification
- Review Gate: `PASS`
  - `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_shell_window_lifecycle.py tests/main_window_shell/shell_runtime_contracts.py --ignore=venv -q`
- Full Verification: `PASS`
  - `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_bootstrap.py tests/test_main_window_shell.py tests/test_shell_window_lifecycle.py tests/main_window_shell/shell_runtime_contracts.py tests/main_window_shell/bridge_contracts.py --ignore=venv -q`

## Manual Test Directives
Ready for manual testing
- Prerequisite: launch the application from `C:\w\ea-node-editor-ui-context-p01` in a normal desktop session with the project venv active.
- Action: start the shell, confirm the main window renders, and open `File > Open Recent`. Expected result: the shell loads without startup errors and the recent-project menu populates or shows the empty-state entry.
- Action: trigger graph search with `Ctrl+K`, search for an existing node title or type, then close it and open canvas or connection quick insert from the graph surface. Expected result: both overlays open, update results, and dismiss exactly as before the refactor.
- Action: toggle `View > Port Labels`, switch the graphics mode from the status strip, close the window, and reopen it. Expected result: port-label visibility and graphics mode still apply and persist across the restart.

## Residual Risks
- `window_state_helpers.py` is intentionally a temporary packet-owned consolidation point; later packets can continue breaking that surface into narrower helpers without re-expanding `window.py`.
- The packet leaves non-shell subsystems untouched, so any future GraphCanvas/QML contract changes still need to be addressed in their owning packets rather than in the shell host.

## Ready for Integration
Yes. The packet-owned code and regression anchors are committed on the assigned branch, the review gate passes, and the full packet verification command passes in the packet worktree.
