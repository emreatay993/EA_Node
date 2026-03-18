# P01 ShellWindow Host Protocols Wrap-Up

## Implementation Summary

- Packet: `P01`
- Branch Label: `codex/arch-second-pass/p01-shell-window-host-protocols`
- Commit Owner: `worker`
- Commit SHA: `1cbb51c506ded3c480482b4b00401aaeb567cf1e`
- Changed Files: `ea_node_editor/ui/shell/window.py`, `ea_node_editor/ui/shell/state.py`, `ea_node_editor/ui/shell/window_search_scope_state.py`, `ea_node_editor/ui/shell/controllers/run_controller.py`, `ea_node_editor/ui/shell/controllers/project_session_controller.py`, `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`, `ea_node_editor/ui/shell/controllers/workspace_edit_ops.py`, `tests/test_main_window_shell.py`, `tests/test_shell_run_controller.py`, `tests/test_shell_project_session_controller.py`, `tests/test_workspace_library_controller_unit.py`
- Artifacts Produced: `docs/specs/work_packets/arch_second_pass/P01_shell_window_host_protocols_WRAPUP.md`
- Introduced nested shell-owned state holders for project-session state, run state, library filters, graph search, quick insert, graph hint, minimap expansion, snap-to-grid, and scope-camera caches.
- Replaced the `window_search_scope_state.py` loose helper mutation pattern with a dedicated `WindowSearchScopeController` owned by `ShellWindow`.
- Routed packet-owned controllers through explicit host-owned services/state (`run_state`, `project_session_state`, `search_scope_controller`, and `graph_interactions`) while keeping existing `ShellWindow` slots, properties, and signals stable for QML and tests.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_shell_run_controller tests.test_shell_project_session_controller -v`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell tests.test_shell_run_controller tests.test_shell_project_session_controller tests.test_workspace_library_controller_unit -v`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: launch the application from this branch with the project venv so the QML shell uses the updated host protocols.
- Open graph search with `Ctrl+K`, search for nodes across multiple workspaces, and activate a result. Expected: the result jumps to the correct workspace/scope, focuses the node, and the search overlay closes cleanly.
- Open a subnode scope, switch views or workspaces, then close an active view. Expected: the active scope/camera restores without stale camera jumps or lost breadcrumbs.
- Trigger a quick insert from a port and from empty canvas space. Expected: overlay results populate, selection works, and the overlay closes after insertion or after an incompatible-input hint.
- Start a workflow run that emits logs or intentionally fails a node. Expected: run state, pause/stop actions, console output, and failed-node focus all behave the same as before the refactor.

## Residual Risks

- Automated coverage ran with `QT_QPA_PLATFORM=offscreen`; one live desktop smoke pass is still worthwhile for view-close camera restoration and overlay timing.
- The wrap-up records the accepted substantive packet commit SHA; the wrap-up artifact itself is a packet-local follow-up artifact.

## Ready for Integration

- Yes: packet-owned source and test changes stayed inside the P01 write scope, the review gate passed, and the full verification command passed.
