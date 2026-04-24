# P03 PyQt Action Route Merge Wrap-Up

## Implementation Summary

- Packet: P03
- Branch Label: codex/corex-architecture-entry-point-reduction/p03-pyqt-action-route-merge
- Commit Owner: worker
- Commit SHA: 062c22257bef0dc9ee3b27bf1792bc4605424831
- Changed Files: docs/specs/work_packets/corex_architecture_entry_point_reduction/P03_pyqt_action_route_merge_WRAPUP.md, ea_node_editor/ui/shell/controllers/graph_action_controller.py, ea_node_editor/ui/shell/window_actions.py, ea_node_editor/ui/shell/window_state/workspace_graph_actions.py, tests/test_graph_action_contracts.py, tests/test_main_window_shell.py
- Artifacts Produced: docs/specs/work_packets/corex_architecture_entry_point_reduction/P03_pyqt_action_route_merge_WRAPUP.md, ea_node_editor/ui/shell/controllers/graph_action_controller.py, ea_node_editor/ui/shell/window_actions.py, ea_node_editor/ui/shell/window_state/workspace_graph_actions.py, tests/test_graph_action_contracts.py, tests/test_main_window_shell.py

Routed PyQt graph menu actions and shortcuts through `GraphActionController` using `GraphActionId` contract values and `graph_action_spec` labels/shortcuts. Converted retained shell request slots for duplicate, copy, cut, paste, delete, wrap comment backdrop, group, ungroup, align, distribute, connect, and scope navigation into compatibility delegates to the controller.

Removed redundant private shell graph-action wrappers after static search showed no remaining production or test callers outside contract legacy-name inventory. Kept low-level graphics toggles, viewport actions, property setters, undo/redo, and QML command bridge routes outside this packet's controller routing.

## Verification

- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py --ignore=venv -q` (`10 passed`)
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py -k "PyQtGraphActionRoute" --ignore=venv -q` (`2 passed, 201 deselected, 4 warnings`)
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py tests/test_main_window_shell.py tests/main_window_shell/edit_clipboard_history.py tests/main_window_shell/comment_backdrop_workflows.py --ignore=venv -q` (`247 passed, 4 warnings, 318 subtests passed`)
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py -k "duplicate or clipboard or comment_backdrop or group or align or scope" --ignore=venv -q` (`203 passed, 4 warnings, 318 subtests passed`)
- PASS: `git diff --check`
- Final Verification Verdict: PASS

## Manual Test Directives

- No separate manual test directive is required for P03 handoff. If a human smoke test is requested, use the PyQt Edit/View menu actions and shortcuts for duplicate, copy, cut, paste, wrap comment backdrop, group, ungroup, align, distribute, and scope navigation on a small graph and confirm labels, shortcuts, and graph mutations are unchanged.

## Residual Risks

- The offscreen Qt runs report existing Ansys DPF operator deprecation warnings for gasket operators; no P03 functional failures were observed.
- QML context-menu and node-delegate routes intentionally remain on their existing command paths; P04 owns routing those callers through `graphActionBridge`.

## Ready for Integration

- Yes: P03 routes PyQt graph actions through the canonical controller, retained compatibility slots delegate to the controller, retired private wrappers have no remaining callers by static search, and required verification plus review gate pass.
