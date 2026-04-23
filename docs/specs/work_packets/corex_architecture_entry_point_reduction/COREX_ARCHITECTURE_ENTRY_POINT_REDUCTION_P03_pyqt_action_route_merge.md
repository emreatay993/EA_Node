# COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION P03: PyQt Action Route Merge

## Packet Metadata

- Packet: `P03`
- Title: `PyQt Action Route Merge`
- Execution Dependencies: `P02`
- Worker model: `gpt-5.5`
- Worker reasoning effort: `xhigh`

## Objective

- Route graph-related PyQt menu actions and shortcuts through `GraphActionController`, then remove redundant shell wrapper methods when the packet proves they are no longer used by production code.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, inherited action-contract tests, and only source files needed for PyQt action routing

## Preconditions

- `P02` is `PASS`.
- `GraphActionController` and `graphActionBridge` exist, and old PyQt/QML routes still work.

## Execution Dependencies

- `P02`

## Target Subsystems

- `ea_node_editor/ui/shell/graph_action_contracts.py`
- `ea_node_editor/ui/shell/controllers/graph_action_controller.py`
- `ea_node_editor/ui/shell/window_actions.py`
- `ea_node_editor/ui/shell/window_state/workspace_graph_actions.py`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_graph_action_contracts.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/edit_clipboard_history.py`
- `tests/main_window_shell/comment_backdrop_workflows.py`

## Conservative Write Scope

- `docs/specs/work_packets/corex_architecture_entry_point_reduction/P03_pyqt_action_route_merge_WRAPUP.md`
- `ea_node_editor/ui/shell/graph_action_contracts.py`
- `ea_node_editor/ui/shell/controllers/graph_action_controller.py`
- `ea_node_editor/ui/shell/window_actions.py`
- `ea_node_editor/ui/shell/window_state/workspace_graph_actions.py`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_graph_action_contracts.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/edit_clipboard_history.py`
- `tests/main_window_shell/comment_backdrop_workflows.py`

## Required Behavior

- Change graph-related `QAction.triggered` and `QAction.toggled` connections in `window_actions.py` to dispatch through `GraphActionController` using action ids from `graph_action_contracts.py`.
- Preserve all existing user-visible labels, shortcuts, checked states, enablement behavior, and return behavior.
- Convert `workspace_graph_actions.py` high-level request functions to compatibility delegates to `GraphActionController` when those functions remain QML/PyQt-visible.
- Remove a wrapper only when static search and tests prove no app code, QML, or test path still calls it directly.
- Keep low-level non-action methods and property setters out of the new controller.
- Update inherited action-contract tests to assert the PyQt action declarations use contract ids/specs instead of ad hoc literals.
- Update shell regression tests for duplicate/copy/cut/paste/delete, wrap comment backdrop, group/ungroup, align/distribute, and scope navigation when their asserted route changes.

## Non-Goals

- Do not route QML context menus or node delegate actions through `graphActionBridge`; `P04` owns that.
- Do not remove `GraphCanvasCommandBridge` high-level QML slots.
- Do not change graph mutation, scene selection, or clipboard payload semantics.
- Do not broaden verification to the full shell-isolation phase unless a smaller shell rerun cannot prove the packet.

## Verification Commands

1. Full packet verification:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py tests/test_main_window_shell.py tests/main_window_shell/edit_clipboard_history.py tests/main_window_shell/comment_backdrop_workflows.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_window_shell.py -k "duplicate or clipboard or comment_backdrop or group or align or scope" --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/corex_architecture_entry_point_reduction/P03_pyqt_action_route_merge_WRAPUP.md`
- `ea_node_editor/ui/shell/window_actions.py`
- `ea_node_editor/ui/shell/window_state/workspace_graph_actions.py`
- `tests/test_graph_action_contracts.py`
- `tests/test_main_window_shell.py`

## Acceptance Criteria

- PyQt graph menu actions and shortcuts dispatch through the canonical action controller.
- Removed wrappers have no remaining production or test callers.
- Compatibility wrappers that remain are thin delegates to the controller.
- All user-facing labels, shortcuts, and checked-state behavior are unchanged.
- The full packet verification command passes.
- The review gate passes.

## Handoff Notes

- `P04` inherits `tests/test_graph_action_contracts.py` and `tests/test_main_window_shell.py` because QML route changes may alter bridge bootstrap and action-route assertions.
- Do not leave a PyQt-only assumption in the action contract; QML payload routing must be able to reuse the same action ids.
