# Execution Engine Requirements

## Runtime Structure
- `REQ-EXEC-001`: the execution engine shall run workflows through a UI-side client and a dedicated worker process boundary per run session.
- `REQ-EXEC-002`: the worker boundary shall use typed command/event payloads that round-trip through queue-safe dictionary adapters.
- `REQ-EXEC-003`: the shell shall receive execution events on a Qt-safe queued path that updates UI state without blocking the worker.
- `REQ-EXEC-009`: the typed command/event protocol shall remain the canonical public execution boundary shared by the UI client, runtime snapshot, and worker.

## Scheduling and Failure Handling
- `REQ-EXEC-004`: the worker shall schedule exec-triggered nodes according to authored exec-edge dependencies.
- `REQ-EXEC-005`: the worker shall propagate resolved data-edge inputs to downstream node execution.
- `REQ-EXEC-006`: runtime failures shall emit structured error and traceback payloads that preserve authored node IDs for diagnostics and shell focus.
- `REQ-EXEC-007`: the worker shall emit run/node lifecycle events covering start, state transitions, completion, failure, stop, logs, and protocol errors.
- `REQ-EXEC-008`: stop requests shall cancel active subprocess-backed execution safely instead of leaving orphaned child processes running.

## Managed Output Transport
- `REQ-EXEC-010`: runtime snapshots and queue payloads shall serialize `RuntimeArtifactRef` values as structured `artifact_ref` payloads so stored outputs can cross the execution boundary as `artifact://...` or `artifact-stage://...` handles instead of inline blobs.
- `REQ-EXEC-011`: execution contexts and downstream file-backed integrations shall resolve managed and staged artifact refs against runtime-snapshot and project artifact metadata during the same run.
- `REQ-EXEC-012`: `Process Run` stored mode shall stage stdout/stderr transcript outputs under the managed-output lifecycle, emit staged refs on success, and remove staged transcript files plus metadata on non-zero failure or cancellation.
- `REQ-EXEC-013`: the execution engine shall expose a registry-driven viewer backend contract: `ViewerBackendRegistry` and `ViewerSessionService` publish `backend_id`, typed `transport`, `transport_revision`, and explicit `live_open_status` / `live_open_blocker` fields through queue-safe viewer protocol payloads, while concrete backends such as the DPF implementation materialize session-scoped temp transport bundles from worker-local state instead of pushing raw PyVista or VTK objects across the boundary.

## Acceptance
- `AC-REQ-EXEC-002-01`: protocol regressions confirm typed command/event payloads round-trip through the queue boundary, including runtime snapshot data and runtime artifact refs.
- `AC-REQ-EXEC-006-01`: worker and shell regressions confirm structured failures preserve traceback data and authored node IDs for UI focus.
- `AC-REQ-EXEC-008-01`: `Process Run` regressions confirm `stop_run` cancels the active subprocess instead of leaking it.
- `AC-REQ-EXEC-010-01`: execution client/worker regressions confirm runtime artifact refs round-trip as structured `artifact_ref` payloads rather than raw inline file blobs.
- `AC-REQ-EXEC-011-01`: execution and integration regressions confirm downstream nodes can resolve stored outputs from runtime/project artifact metadata during the same run.
- `AC-REQ-EXEC-012-01`: `Process Run` regressions confirm stored transcript success paths, stored-mode cleanup on failure, and the preserved `memory` versus `stored` contract.
- `AC-REQ-EXEC-013-01`: execution protocol, client, worker-service, materialization, and bridge regressions confirm registry resolution, temp-bundle reuse and cleanup, rerun-required blocker projection, and typed queue-safe viewer payloads.
