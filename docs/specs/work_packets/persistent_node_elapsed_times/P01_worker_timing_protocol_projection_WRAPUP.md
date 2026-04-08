# P01 Worker Timing Protocol Projection Wrap-Up

## Implementation Summary

- Packet: `P01`
- Branch Label: `codex/persistent-node-elapsed-times/p01-worker-timing-protocol-projection`
- Commit Owner: `worker`
- Commit SHA: `1cf7252bdda8641c560f63a77fa7bb2b1ac0c900`
- Changed Files: `docs/specs/work_packets/persistent_node_elapsed_times/P01_worker_timing_protocol_projection_WRAPUP.md`, `ea_node_editor/execution/protocol.py`, `ea_node_editor/execution/worker_runner.py`, `tests/test_execution_client.py`, `tests/test_execution_worker.py`
- Artifacts Produced: `docs/specs/work_packets/persistent_node_elapsed_times/P01_worker_timing_protocol_projection_WRAPUP.md`

Added additive `started_at_epoch_ms` and `elapsed_ms` protocol fields with zero-default queue deserialization, emitted worker-owned timing around successful plugin execution in `NodeExecutor`, and added packet-owned worker/client regressions that preserve the richer payload while keeping legacy payloads backward compatible.

## Verification

- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_execution_worker.py tests/test_execution_client.py -k persistent_node_elapsed_time_protocol --ignore=venv -q`
- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_execution_worker.py -k persistent_node_elapsed_time_protocol --ignore=venv -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Too soon for manual testing.

- Blocker: This packet stops at the worker/client protocol layer, so there is no shell, bridge, or QML surface yet that exposes the elapsed-time metadata for a user-driven check.
- Next condition: Manual testing becomes worthwhile after later packets project `started_at_epoch_ms` and `elapsed_ms` into shell state and render the persistent elapsed footer in the graph UI.

## Residual Risks

- `started_at_epoch_ms` and `elapsed_ms` are emitted from the worker on successful completion only; later shell-side packets still need to prove their documented fallback timing path when these fields are absent.
- The elapsed duration uses the same wall-clock source as the start timestamp to preserve protocol consistency, so later consumers should continue treating worker timing as additive display metadata rather than as a strict profiling contract.

## Ready for Integration

- Yes: `The additive protocol fields, worker timing emission, packet-owned regressions, and wrap-up are committed on the assigned branch with packet verification and review gate passing.`
