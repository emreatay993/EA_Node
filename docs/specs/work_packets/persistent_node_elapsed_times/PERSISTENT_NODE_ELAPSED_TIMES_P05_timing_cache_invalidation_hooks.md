# PERSISTENT_NODE_ELAPSED_TIMES P05: Timing Cache Invalidation Hooks

## Objective
- Add the centralized elapsed-cache invalidation hook on history commit, undo, and redo so execution-affecting edits clear cached elapsed values while documented cosmetic/layout edits preserve them.

## Preconditions
- `P04` is marked `PASS` in [PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md](./PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md).
- No later `PERSISTENT_NODE_ELAPSED_TIMES` packet is in progress.

## Execution Dependencies
- `P04`

## Target Subsystems
- `ea_node_editor/ui_qml/graph_scene/context.py`
- `ea_node_editor/ui/shell/runtime_history.py`
- `ea_node_editor/ui/shell/window_state/run_and_style_state.py`
- `ea_node_editor/ui/shell/controllers/workspace_edit_ops.py`
- `tests/main_window_shell/bridge_support.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/edit_clipboard_history.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/graph_scene/context.py`
- `ea_node_editor/ui/shell/runtime_history.py`
- `ea_node_editor/ui/shell/window_state/run_and_style_state.py`
- `ea_node_editor/ui/shell/controllers/workspace_edit_ops.py`
- `tests/main_window_shell/bridge_support.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/edit_clipboard_history.py`
- `docs/specs/work_packets/persistent_node_elapsed_times/P05_timing_cache_invalidation_hooks_WRAPUP.md`

## Required Behavior
- Hook elapsed-cache invalidation once at the shared history commit/undo/redo seam rather than at every individual UI mutation entry point.
- Consume the packet-owned action taxonomy from `P04` to clear cached elapsed data only for execution-affecting edits and preserve it for the locked-default cosmetic/layout edits.
- Preserve cached elapsed values across move/resize, collapse/expand, rename/title-only edits, node/edge style edits, edge-label edits, port-label edits, comment-only edits, selection/scope/view changes, workspace switching, and theme/performance changes.
- Clear cached elapsed values after execution-affecting commit/undo/redo flows such as node add/remove, edge add/remove/rewire, executable property changes, duplicate/paste/delete, group/ungroup, exposed-port changes, and subnode-interface changes.
- Reuse the packet-owned bridge/footer contracts from `P03`; invalidation should clear the existing timing lookups rather than inventing a second renderer-side state path.
- Add packet-owned regression tests whose names include `persistent_node_elapsed_invalidation` so the targeted verification commands below remain stable.

## Non-Goals
- No new action-type expansion beyond the taxonomy established in `P04`.
- No project/session replacement changes; those remain owned by `P02`.
- No requirement, QA, or traceability refresh yet.

## Verification Commands
1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/edit_clipboard_history.py tests/test_main_window_shell.py -k persistent_node_elapsed_invalidation --ignore=venv -q`

## Review Gate
- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/edit_clipboard_history.py -k persistent_node_elapsed_invalidation --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/persistent_node_elapsed_times/P05_timing_cache_invalidation_hooks_WRAPUP.md`

## Acceptance Criteria
- Cached elapsed values clear at the centralized history commit/undo/redo seam for execution-affecting edits and preserve across the documented cosmetic/layout edits.
- The bridge/footer timing lookups from `P03` clear and preserve in lockstep with the invalidation policy rather than diverging from shell state.
- The packet-owned `persistent_node_elapsed_invalidation` regressions pass.

## Handoff Notes
- `P06` will render the end-user footer on top of the invalidation policy established here, and `P07` will document the retained proof path.
- Any later packet that changes which edit classes invalidate elapsed timings must inherit and update the packet-owned regression anchors in this packet's scope.
