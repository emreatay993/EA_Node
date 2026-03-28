# Implementation Summary
Packet: `P09`
Branch Label: `codex/architecture-maintainability-refactor/p09-runtime-protocol-compat-removal`
Commit Owner: `worker`
Commit SHA: `29409ebf270674f0ce92650a3e4ebb9628a4dfa1`
Changed Files:
- `ea_node_editor/execution/client.py`
- `ea_node_editor/execution/protocol.py`
- `ea_node_editor/execution/runtime_snapshot.py`
- `ea_node_editor/execution/worker.py`
- `ea_node_editor/execution/worker_protocol.py`
- `ea_node_editor/execution/worker_runner.py`
- `tests/test_execution_artifact_refs.py`
- `tests/test_execution_client.py`
- `tests/test_execution_viewer_protocol.py`
- `tests/test_execution_worker.py`
- `docs/specs/work_packets/architecture_maintainability_refactor/P09_runtime_protocol_compat_removal_WRAPUP.md`
Artifacts Produced:
- `docs/specs/work_packets/architecture_maintainability_refactor/P09_runtime_protocol_compat_removal_WRAPUP.md`
- `ea_node_editor/execution/client.py`
- `ea_node_editor/execution/protocol.py`
- `ea_node_editor/execution/runtime_snapshot.py`
- `ea_node_editor/execution/worker.py`
- `ea_node_editor/execution/worker_protocol.py`
- `ea_node_editor/execution/worker_runner.py`
- `tests/test_execution_artifact_refs.py`
- `tests/test_execution_client.py`
- `tests/test_execution_viewer_protocol.py`
- `tests/test_execution_worker.py`

Removed packet-owned `project_doc` compatibility from start-run payload coercion, client dispatch, and execution trigger shaping so packet-owned normal runs now rely on `RuntimeSnapshot` instead of rehydrating from embedded project documents. Added explicit `request_id` propagation on protocol-error events and switched client-side viewer failure correlation to request-id matching so concurrent viewer commands no longer depend on FIFO-by-command heuristics.

# Verification
PASS: `./venv/Scripts/python.exe -m pytest tests/test_execution_client.py tests/test_execution_worker.py tests/test_execution_artifact_refs.py tests/test_execution_viewer_protocol.py --ignore=venv -q`
PASS: `./venv/Scripts/python.exe -m pytest tests/test_execution_client.py tests/test_execution_worker.py tests/test_execution_artifact_refs.py tests/test_execution_handle_refs.py tests/test_execution_viewer_protocol.py tests/test_run_controller_unit.py tests/test_shell_run_controller.py --ignore=venv -q`
PASS: `./venv/Scripts/python.exe -m pytest tests/test_execution_client.py tests/test_execution_artifact_refs.py --ignore=venv -q`
Final Verification Verdict: PASS

# Manual Test Directives
Ready for manual testing
- Prerequisite: launch the application from this branch and open a workflow where `core.start.trigger` is wired into a `core.logger` node so the manual trigger payload is visible in the run log.
- Action: run the workflow from the shell UI. Expected result: the logged trigger still includes the manual metadata you supplied, such as `kind` and `workflow_settings`, but it does not include a `project_doc` key or an inlined project document payload.
- Optional viewer smoke: use a workflow that opens a viewer-backed session, issue multiple viewer updates in quick succession, then force a stale viewer action by rerunning the workspace or reusing an expired session. Expected result: any viewer failure is reported against the specific request/session that failed, and unrelated pending viewer requests stay intact.

# Residual Risks
- Out-of-scope callers that still send raw `project_doc` start-run payloads will now receive an explicit rejection and must migrate to `runtime_snapshot`.
- Viewer failure synthesis now depends on packet-owned `protocol_error` emitters preserving `request_id`; any out-of-scope producer that fabricates viewer-related protocol errors without a request id will no longer get FIFO-based fallback matching.

# Ready for Integration
Yes: Packet-local code, tests, and wrap-up are prepared on the packet branch, and no executor-owned integration state or shared status ledger was changed.
