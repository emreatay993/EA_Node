# P03 Shell Host API Retirement Wrap-Up

## Implementation Summary
- Packet: `P03`
- Branch Label: `codex/architecture-maintainability-refactor/p03-shell-host-api-retirement`
- Commit Owner: `worker`
- Commit SHA: `1d00dc5fa2270ee4037323776e6d016b17480a40`
- Changed Files: `ea_node_editor/ui/shell/composition.py`, `ea_node_editor/ui/shell/presenters.py`, `tests/main_window_shell/bridge_contracts.py`, `tests/main_window_shell/shell_runtime_contracts.py`, `tests/test_main_bootstrap.py`, `tests/test_main_window_shell.py`, `docs/specs/work_packets/architecture_maintainability_refactor/P03_shell_host_api_retirement_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/architecture_maintainability_refactor/P03_shell_host_api_retirement_WRAPUP.md`, `ea_node_editor/ui/shell/composition.py`, `ea_node_editor/ui/shell/presenters.py`, `tests/main_window_shell/bridge_contracts.py`, `tests/main_window_shell/shell_runtime_contracts.py`, `tests/test_main_bootstrap.py`, `tests/test_main_window_shell.py`

Added `GraphCanvasHostPresenter` as the explicit `GraphCanvasCommandBridge.host_source` for the bootstrapped shell path so the bridge no longer binds its host-side command contract to `ShellWindow`. `GraphCanvasPresenter` now applies graphics preference updates directly through `AppPreferencesController`, and the packet-owned bootstrap/runtime regression anchors now assert the presenter-backed seam instead of `host_source == ShellWindow`.

## Verification
- PASS: `git diff --check`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_bootstrap.py tests/main_window_shell/bridge_contracts.py tests/main_window_shell/shell_runtime_contracts.py --ignore=venv -q` (`54 passed, 27 subtests passed in 30.01s`)
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_bootstrap.py tests/test_main_window_shell.py tests/main_window_shell/shell_runtime_contracts.py tests/main_window_shell/bridge_contracts.py tests/test_viewer_session_bridge.py --ignore=venv -q` (`227 passed, 347 subtests passed in 88.85s`)
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_bootstrap.py tests/test_main_window_shell.py --ignore=venv -q` (`180 passed, 320 subtests passed in 57.68s`)
- Final Verification Verdict: PASS

## Manual Test Directives
Ready for manual testing

1. Prerequisite: start the branch in a normal desktop Qt session with the project venv interpreter, not `QT_QPA_PLATFORM=offscreen`.
Action: launch the shell and load or create a simple graph.
Expected result: the main shell, graph canvas, and QML overlays load without bridge-binding errors or missing context properties.

2. Action: use the shell status strip or graph-canvas controls to toggle graphics mode and port-label visibility, then pan and zoom the canvas.
Expected result: the canvas updates immediately, the preference persists after reopening the window, and no command-routing errors appear.

3. Action: from the graph canvas, open canvas quick insert or a connection quick insert, then navigate into and back out of a subnode scope if one is available.
Expected result: the quick-insert surface opens at the expected location and scope navigation still works through the command bridge.

4. Action: on a passive node and a flow edge, use one style-related context-menu action and one rename/remove action.
Expected result: the graph updates immediately and the action succeeds without regressions in cursor handling or canvas command routing.

## Residual Risks
- Automated verification ran with `QT_QPA_PLATFORM=offscreen`, so desktop-session smoke coverage is still recommended for cursor-sensitive graph-canvas interactions and context menus.
- `GraphCanvasCommandBridge` still retains shell-window fallback behavior outside this packet scope; this packet only hardens the bootstrapped shell path to use an explicit host presenter.
- Some direct `ShellWindow` command slots remain for out-of-scope callers and inherited regression anchors, so complete host-surface retirement is not finished in this packet.

## Ready for Integration
- Yes: the bootstrapped shell path now routes graph-canvas host commands through an explicit presenter contract, the packet verification command passed, and the review gate passed.
