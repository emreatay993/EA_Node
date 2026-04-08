# P05 Timing Cache Invalidation Hooks Wrap-Up

## Implementation Summary

- Packet: `P05`
- Branch Label: `codex/persistent-node-elapsed-times/p05-timing-cache-invalidation-hooks`
- Commit Owner: `worker`
- Commit SHA: `10128f9acd09a72c1ea4079c9d8bcd9ac974bade`
- Changed Files: `ea_node_editor/ui_qml/graph_scene/context.py`, `ea_node_editor/ui/shell/runtime_history.py`, `ea_node_editor/ui/shell/window_state/run_and_style_state.py`, `ea_node_editor/ui/shell/controllers/workspace_edit_ops.py`, `tests/main_window_shell/edit_clipboard_history.py`, `tests/test_main_window_shell.py`, `docs/specs/work_packets/persistent_node_elapsed_times/P05_timing_cache_invalidation_hooks_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/persistent_node_elapsed_times/P05_timing_cache_invalidation_hooks_WRAPUP.md`

## Verification

- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/edit_clipboard_history.py tests/test_main_window_shell.py -k persistent_node_elapsed_invalidation --ignore=venv -q`
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/edit_clipboard_history.py -k persistent_node_elapsed_invalidation --ignore=venv -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: open the packet branch build in the normal shell UI and stay in one workspace that already has cached elapsed footer values from a previous run.
- Action: move a node, rename a node title, or edit a comment backdrop body. Expected result: the elapsed footer values remain visible and unchanged for that workspace.
- Action: change an execution-affecting property, such as a logger message or another runnable node property. Expected result: the cached elapsed footer clears immediately for the active workspace.
- Action: after the execution-affecting edit clears the cache, use Undo and then Redo. Expected result: each history step clears the same timing lookups again instead of restoring stale elapsed values.
- Action: switch to a different workspace that already has cached elapsed values after invalidating the first workspace. Expected result: the untouched workspace keeps its own cached elapsed values.

## Residual Risks

- Annotation-only preservation relies on the `passive.annotation.*` type-family heuristic in the centralized history classifier; later packets that broaden cosmetic-only node families should update the same classifier and packet-owned regressions together.
- The review-gate pytest run still emits the existing non-fatal Windows temp-cleanup `PermissionError` against `pytest-current` after reporting success.

## Ready for Integration

- Yes: the centralized commit/undo/redo invalidation hook is packet-local, reuses the P03 timing lookups, and passed the packet verification plus review-gate commands.
