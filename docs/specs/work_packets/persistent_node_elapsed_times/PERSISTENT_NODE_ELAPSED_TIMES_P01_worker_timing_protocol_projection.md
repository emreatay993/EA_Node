# PERSISTENT_NODE_ELAPSED_TIMES P01: Worker Timing Protocol Projection

## Objective
- Add additive worker timing metadata on `node_started` and `node_completed` so later shell/QML packets can consume real execution start and elapsed timing without guessing from QML-only state.

## Preconditions
- `P00` is marked `PASS` in [PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md](./PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md).
- No later `PERSISTENT_NODE_ELAPSED_TIMES` packet is in progress.

## Execution Dependencies
- `P00`

## Target Subsystems
- `ea_node_editor/execution/protocol.py`
- `ea_node_editor/execution/worker_runner.py`
- `tests/test_execution_worker.py`
- `tests/test_execution_client.py`

## Conservative Write Scope
- `ea_node_editor/execution/protocol.py`
- `ea_node_editor/execution/worker_runner.py`
- `tests/test_execution_worker.py`
- `tests/test_execution_client.py`
- `docs/specs/work_packets/persistent_node_elapsed_times/P01_worker_timing_protocol_projection_WRAPUP.md`

## Required Behavior
- Extend `NodeStartedEvent` additively with `started_at_epoch_ms: float = 0.0`.
- Extend `NodeCompletedEvent` additively with `elapsed_ms: float = 0.0` while preserving the existing `outputs` payload.
- Emit the packet-owned `started_at_epoch_ms` value immediately before real plugin execution begins in `worker_runner.py`.
- Emit the packet-owned `elapsed_ms` value after plugin execution succeeds and normalized outputs are ready, using the same worker-owned clock source as the start timestamp.
- Keep `node_completed` timing additive and avoid emitting a false elapsed payload for nodes that never actually complete successfully.
- Keep queue-boundary compatibility intact so older shell consumers still accept the richer payload without requiring matching rollout timing.
- Add packet-owned regression tests whose names include `persistent_node_elapsed_time_protocol` so the targeted verification commands below remain stable.

## Non-Goals
- No shell, bridge, history, or QML changes yet.
- No timing-cache invalidation behavior yet.
- No `.sfe` persistence or project-session behavior changes.

## Verification Commands
1. `.\venv\Scripts\python.exe -m pytest tests/test_execution_worker.py tests/test_execution_client.py -k persistent_node_elapsed_time_protocol --ignore=venv -q`

## Review Gate
- `.\venv\Scripts\python.exe -m pytest tests/test_execution_worker.py -k persistent_node_elapsed_time_protocol --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/persistent_node_elapsed_times/P01_worker_timing_protocol_projection_WRAPUP.md`

## Acceptance Criteria
- `NodeStartedEvent` and `NodeCompletedEvent` expose additive timing fields with zero-default backward compatibility.
- Worker execution publishes a real start timestamp and a real elapsed duration for successful node completions.
- The packet-owned `persistent_node_elapsed_time_protocol` worker/client regressions pass without regressing existing event payload consumers.

## Handoff Notes
- `P02` consumes `started_at_epoch_ms` and `elapsed_ms` on the shell/controller path but must still keep the documented fallback behavior when the fields are absent.
- Any later packet that renames these protocol fields or changes when they are emitted must inherit and update `tests/test_execution_worker.py` and `tests/test_execution_client.py`.
