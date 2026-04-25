# COREX_NO_LEGACY_ARCHITECTURE_CLEANUP P03: Shell Graph Action Facade Retirement

## Objective

- Remove duplicate `ShellWindow` and `window_state` graph-action facade slots now that `GraphActionController` is the canonical PyQt/QML graph-action owner.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and only shell action/controller/tests needed for this packet

## Preconditions

- `P02` is marked `PASS`.
- High-level QML graph actions do not depend on retired graph-canvas compatibility refs.

## Execution Dependencies

- `P02`

## Target Subsystems

- `ea_node_editor/ui/shell/controllers/graph_action_controller.py`
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_actions.py`
- `ea_node_editor/ui/shell/window_state/workspace_graph_actions.py`
- `ea_node_editor/ui/shell/window_state/library_and_overlay_state.py`
- `ea_node_editor/ui/shell/window_state/run_and_style_state.py`
- `ea_node_editor/ui/shell/window_state/context_properties.py`
- `ea_node_editor/ui/shell/presenters/graph_canvas_presenter.py`
- `ea_node_editor/ui/shell/presenters/graph_canvas_host_presenter.py`
- `ea_node_editor/ui/shell/presenters/library_presenter.py`
- `tests/test_graph_action_contracts.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/bridge_contracts_graph_canvas.py`
- `tests/main_window_shell/shell_runtime_contracts.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P03_shell_graph_action_facade_retirement_WRAPUP.md`

## Conservative Write Scope

- `ea_node_editor/ui/shell/controllers/graph_action_controller.py`
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_actions.py`
- `ea_node_editor/ui/shell/window_state/workspace_graph_actions.py`
- `ea_node_editor/ui/shell/window_state/library_and_overlay_state.py`
- `ea_node_editor/ui/shell/window_state/run_and_style_state.py`
- `ea_node_editor/ui/shell/window_state/context_properties.py`
- `ea_node_editor/ui/shell/presenters/graph_canvas_presenter.py`
- `ea_node_editor/ui/shell/presenters/graph_canvas_host_presenter.py`
- `ea_node_editor/ui/shell/presenters/library_presenter.py`
- `tests/test_graph_action_contracts.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/bridge_contracts_graph_canvas.py`
- `tests/main_window_shell/shell_runtime_contracts.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P03_shell_graph_action_facade_retirement_WRAPUP.md`

## Required Behavior

- Inject the focused dependencies that `GraphActionController` needs so it no longer falls back to generic `shell_window` methods for scope navigation, node edit/remove/rename, passive style dialogs, flow-edge style dialogs, publish workflow, add-on-manager open, clipboard, grouping, alignment, or deletion.
- Remove duplicate `window_state` facade functions that now only mirror `GraphActionController.trigger(...)`.
- Remove matching entries from `WINDOW_STATE_FACADE_BINDINGS` and any tests that kept those aliases alive.
- Keep user-facing menu labels and shortcuts intact through the action declaration/factory layer.
- Update shell tests so they assert controller dispatch and absence of retired facade slots rather than parity between old and new routes.

## Non-Goals

- No broad QML context global shrink; that belongs to `P04`.
- No workspace/custom workflow scope rewrite; that belongs to `P05`.
- No removal of feature-presenter APIs that remain the canonical dependency targets.

## Verification Commands

1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py tests/test_main_window_shell.py tests/main_window_shell/bridge_contracts_graph_canvas.py tests/main_window_shell/shell_runtime_contracts.py --ignore=venv -q`

## Review Gate

- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_action_contracts.py tests/test_main_window_shell.py -k "graph_action or duplicate or clipboard or comment_backdrop or group or align or scope" --ignore=venv -q`

## Expected Artifacts

- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P03_shell_graph_action_facade_retirement_WRAPUP.md`

## Acceptance Criteria

- `GraphActionController` no longer needs a generic `shell_window` fallback for packet-owned graph actions.
- Duplicate ShellWindow/window-state graph-action slots are removed or narrowed to one clearly documented public entry when still necessary.
- Menu/shortcut behavior still dispatches through canonical action declarations and controller triggers.

## Handoff Notes

- `P04` can assume shell graph-action routing is no longer a reason to keep broad shell context exports.
