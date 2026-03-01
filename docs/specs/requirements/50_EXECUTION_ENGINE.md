# Execution Engine Requirements

## Process Model
- `REQ-EXEC-001`: Execution shall run in a worker process separate from UI process.
- `REQ-EXEC-002`: UI/worker communication shall use queue-based command/event protocol.
- `REQ-EXEC-003`: UI thread shall not block during run.

## Workflow Semantics
- `REQ-EXEC-004`: Execution shall support control flow through exec/completed edges.
- `REQ-EXEC-005`: Execution shall pass data outputs to downstream inputs via data edges.
- `REQ-EXEC-006`: On node exception, run shall abort with failure event containing node id and traceback.
- `REQ-EXEC-008`: Stop commands shall support cancellation hooks for active long-running node operations (for example external subprocess calls).

## Events
- `REQ-EXEC-007`: Worker shall emit `run_state`, `node_started`, `node_completed`, `log`, `run_completed`, `run_failed`.

## Acceptance
- `AC-REQ-EXEC-001-01`: Workflow run does not freeze pan/zoom/selection interactions.
- `AC-REQ-EXEC-006-01`: Failed node is identified and surfaced to UI with traceback.
- `AC-REQ-EXEC-007-01`: Event stream can populate console and status bar.
- `AC-REQ-EXEC-008-01`: `stop_run` can terminate an active external process node without forcing worker process termination.
