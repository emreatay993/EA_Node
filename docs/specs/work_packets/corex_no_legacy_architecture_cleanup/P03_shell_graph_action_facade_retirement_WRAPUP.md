# P03 Shell Graph Action Facade Retirement Wrap-Up

## Implementation Summary

Packet: P03 Shell Graph Action Facade Retirement
Branch Label: `codex/corex-no-legacy-architecture-cleanup/p03-shell-graph-action-facade-retirement`
Commit Owner: worker
Commit SHA: `9b99e92acd4eefccfc526f004774924034fe9170`
Changed Files:
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui/shell/controllers/graph_action_controller.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_state/workspace_graph_actions.py`
- `tests/main_window_shell/bridge_contracts_graph_canvas.py`
- `tests/test_graph_action_contracts.py`
- `tests/test_main_window_shell.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P03_shell_graph_action_facade_retirement_WRAPUP.md`
Artifacts Produced:
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P03_shell_graph_action_facade_retirement_WRAPUP.md`

`GraphActionController` no longer accepts or discovers a generic `shell_window`; packet-owned graph actions now use injected workspace, presenter, scene, help, and add-on-manager sources. The shell composition binds those focused sources before constructing the QML graph action bridge.

Retired graph-action trigger wrappers were removed from `workspace_graph_actions.py` and therefore from `WINDOW_STATE_FACADE_BINDINGS`. Current QML-facing ShellWindow slot names remain as direct ShellWindow entries that delegate to the canonical controller, preserving existing labels, shortcuts, and QML-visible affordances while removing the window-state facade ownership.

## Verification

PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py tests/test_main_window_shell.py tests/main_window_shell/bridge_contracts_graph_canvas.py tests/main_window_shell/shell_runtime_contracts.py --ignore=venv -q` (`243 passed, 382 subtests passed`; 4 Ansys DPF deprecation warnings)
PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py tests/test_main_window_shell.py -k "graph_action or duplicate or clipboard or comment_backdrop or group or align or scope" --ignore=venv -q` (`216 passed, 346 subtests passed`; 4 Ansys DPF deprecation warnings)
PASS: `git diff --check`

Final Verification Verdict: PASS

## Manual Test Directives

Ready for manual testing

Prerequisite: use this packet branch and the project virtual environment.

1. Launch the shell through the normal repository launch path, create or open a small graph, and use the Edit menu or shortcuts for duplicate, copy, cut, paste, group, ungroup, align, and distribute. Expected result: menu labels and shortcuts are unchanged, and each action mutates the graph through the same visible workflow as before.
2. Open a subnode scope, then use the Scope Parent and Scope Root actions. Expected result: scope navigation still works and breadcrumbs update normally.
3. Select nodes and edges, including a comment backdrop when available, then delete the selection. Expected result: selected graph items are removed and undo/redo still restores the graph state.

## Residual Risks

No known packet-owned residual risks. Existing Ansys DPF deprecation warnings appeared during verification and are unrelated to this packet.

## Ready for Integration

Yes: P03 implementation and wrap-up are complete, required verification and review gate passed, and packet-owned changes are committed on the assigned branch.
