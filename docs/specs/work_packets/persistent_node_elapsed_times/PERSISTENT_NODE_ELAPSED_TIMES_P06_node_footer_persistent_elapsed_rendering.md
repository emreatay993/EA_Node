# PERSISTENT_NODE_ELAPSED_TIMES P06: Node Footer Persistent Elapsed Rendering

## Objective
- Render live and cached elapsed footer text from the packet-owned timing lookups while preserving the existing formatter/object name, failure priority, and end-user expectation that cached elapsed values stay visible until execution-affecting invalidation occurs.

## Preconditions
- `P05` is marked `PASS` in [PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md](./PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md).
- No later `PERSISTENT_NODE_ELAPSED_TIMES` packet is in progress.

## Execution Dependencies
- `P05`

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHostTheme.qml`
- `tests/test_shell_run_controller.py`
- `tests/graph_surface/passive_host_interaction_suite.py`
- `tests/graph_track_b/qml_preference_bindings.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHostTheme.qml`
- `tests/test_shell_run_controller.py`
- `tests/graph_surface/passive_host_interaction_suite.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `docs/specs/work_packets/persistent_node_elapsed_times/P06_node_footer_persistent_elapsed_rendering_WRAPUP.md`

## Required Behavior
- Replace the purely QML-local running-timer start source with the packet-owned canvas timing lookups while keeping the existing `formatExecutionElapsed()` formatter contract and `graphNodeElapsedTimer` object name stable.
- Show live elapsed time while the node is actively running by using `running_node_started_at_ms_lookup`.
- Fall back to the cached elapsed value from `node_elapsed_ms_lookup` after completion, run end, and preserved cosmetic/layout edits when the cache still contains a value for that node.
- Use running/live styling while active and a quieter completed-style footer treatment when rendering cached elapsed values after the node is no longer running.
- Keep cached elapsed footer text visible after `run_completed`, `run_stopped`, or run-failure cleanup when a completed-node cached value exists, but clear it immediately when the packet-owned invalidation path removes the cache.
- Preserve failure-priority behavior so failed-running nodes do not show a misleading live timer after failure handling transitions.
- Add packet-owned regression tests whose names include `persistent_node_elapsed_footer` so the targeted verification commands below remain stable.

## Non-Goals
- No new bridge property names.
- No history taxonomy or invalidation-policy changes.
- No requirement, QA-matrix, or traceability refresh yet.

## Verification Commands
1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_shell_run_controller.py -k persistent_node_elapsed_footer --ignore=venv -q`
2. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_surface/passive_host_interaction_suite.py -k persistent_node_elapsed_footer --ignore=venv -q`
3. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py -k persistent_node_elapsed_footer --ignore=venv -q`

## Review Gate
- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_shell_run_controller.py -k persistent_node_elapsed_footer --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/persistent_node_elapsed_times/P06_node_footer_persistent_elapsed_rendering_WRAPUP.md`

## Acceptance Criteria
- Running nodes show live elapsed time from the packet-owned started-at lookup rather than from an isolated QML-only timer seed.
- Completed nodes continue to show cached elapsed footer text after run terminal events until execution-affecting invalidation clears the cache.
- The `graphNodeElapsedTimer` object name and `formatExecutionElapsed()` contract remain stable for probes.
- The packet-owned `persistent_node_elapsed_footer` shell/QML regressions pass.

## Handoff Notes
- `P07` treats this footer behavior as the shipped end-user surface for the retained node-execution QA matrix.
- Any later packet that changes footer visibility, object names, formatter semantics, or failure-priority behavior must inherit and update `tests/test_shell_run_controller.py`, `tests/graph_surface/passive_host_interaction_suite.py`, and `tests/graph_track_b/qml_preference_bindings.py`.
