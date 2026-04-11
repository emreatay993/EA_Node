# Persistent Node Elapsed Times

## Summary
- Keep a session-only, workspace-scoped cache of each node’s last completed elapsed time.
- During a run, a node footer shows live elapsed time; after completion, it shows the cached final duration and stays visible until the workflow is changed in an execution-affecting way.
- Rerunning the same unchanged workflow updates timings node-by-node. If a run stops or fails, only nodes that actually reached completion get new timings; untouched nodes keep their previous cached values.

## Interface Changes
- Extend the execution event contract additively:
  - `NodeStartedEvent.started_at_epoch_ms: float = 0.0`
  - `NodeCompletedEvent.elapsed_ms: float = 0.0`
- Keep run-event consumers backward compatible:
  - If `started_at_epoch_ms` is missing, the shell records a local fallback start time.
  - If `elapsed_ms` is missing, the shell computes it from the stored start time.
- Split coarse graph-history action types so invalidation can distinguish execution-affecting edits from cosmetic/layout edits. The important new distinction is between executable property edits and cosmetic edits like rename/style/edge-label/port-label.
- Expose two new bridge lookups for the active workspace:
  - `running_node_started_at_ms_lookup`
  - `node_elapsed_ms_lookup`

## Implementation Changes
- Measure real node execution time in the worker around plugin execution, publish the worker start timestamp on `node_started`, and publish the final elapsed milliseconds on `node_completed`.
- Extend shell run state with:
  - transient running-node start timestamps for the active run
  - persisted per-workspace elapsed-time cache
  - a revision counter for timing/footer updates
- Keep persisted elapsed data separate from `running_node_ids` and `completed_node_ids` so the footer can persist without keeping the completed outline/border state after the run ends.
- Update run handling so:
  - `run_started` clears only transient running/completed visualization, not the cached elapsed footer data
  - `node_started` begins live timing for that node
  - `node_completed` overwrites that node’s cached elapsed time
  - `run_completed`, `run_stopped`, and `run_failed` clear transient live state but keep the cache
- Update the QML node footer to:
  - keep the existing elapsed formatter/object name
  - show live elapsed while running
  - fall back to cached elapsed after completion
  - use live/run styling while active and a quieter completed-style color when showing cached data
- Add a central cache invalidation hook on history commit/undo/redo. Invalidate the workspace timing cache only for execution-affecting edits:
  - invalidate: node add/remove, edge add/remove/rewire, executable node property changes, duplicate/paste/delete, group/ungroup, exposed-port or subnode-interface changes, and undo/redo of those actions
  - preserve: move/resize, collapse/expand, rename/title-only edits, node/edge style edits, edge-label edits, port-label edits, comment-backdrop/annotation-only edits, selection/scope/view changes, workspace switching, theme/performance changes
- Clear all cached timing data on project/session replacement so timings never leak across projects.

## Test Plan
- Worker/protocol tests:
  - `node_started` emits start timing metadata.
  - `node_completed` emits elapsed timing metadata.
- Run-controller tests:
  - cached timings survive `run_completed`
  - stopped/failed runs keep completed-node timings
  - reruns replace a node’s cached time when that node completes again
  - missing timing fields still work via fallback timing
- Invalidation tests:
  - property/connection/structure edits clear cached timings
  - move/resize/collapse/rename/style/label edits do not
  - undo/redo follows the same invalidation policy
- Shell/QML integration tests:
  - footer stays visible after `run_completed`
  - footer survives layout-only edits
  - footer clears after an execution-affecting edit
  - live rerun timing overrides cached timing while the node is running

## Assumptions
- “Persistent” means persistent within the open app session only; there is no project serialization change in this packet.
- The cached value is the node’s last observed completed duration for the current workflow version, not a guaranteed whole-run snapshot.
- Partial interrupted runs update only nodes that completed before interruption and leave untouched nodes as-is.
- Future analyzer work should read the Python-owned timing cache directly rather than QML-local state.
