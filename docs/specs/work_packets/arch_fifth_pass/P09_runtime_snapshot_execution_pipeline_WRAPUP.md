# P09 Runtime Snapshot Execution Pipeline Wrap-Up

## Implementation Summary

- Packet: `P09`
- Branch Label: `codex/arch-fifth-pass/p09-runtime-snapshot-execution-pipeline`
- Commit Owner: `worker`
- Commit SHA: `867f218980e05967dc594891bc581920da5b7dc1`
- Changed Files: `docs/specs/work_packets/arch_fifth_pass/P09_runtime_snapshot_execution_pipeline_WRAPUP.md`, `ea_node_editor/ui/shell/controllers/run_controller.py`, `ea_node_editor/execution/protocol.py`, `ea_node_editor/execution/client.py`, `ea_node_editor/execution/compiler.py`, `ea_node_editor/execution/runtime_dto.py`, `ea_node_editor/execution/runtime_snapshot.py`, `ea_node_editor/execution/worker.py`, `tests/test_execution_client.py`, `tests/test_execution_worker.py`, `tests/test_process_run_node.py`, `tests/test_run_controller_unit.py`, `tests/test_passive_runtime_wiring.py`
- Artifacts Produced: `docs/specs/work_packets/arch_fifth_pass/P09_runtime_snapshot_execution_pipeline_WRAPUP.md`, `ea_node_editor/execution/runtime_snapshot.py`, `ea_node_editor/execution/runtime_dto.py`, `ea_node_editor/execution/compiler.py`, `ea_node_editor/execution/protocol.py`, `ea_node_editor/execution/client.py`, `ea_node_editor/execution/worker.py`, `ea_node_editor/ui/shell/controllers/run_controller.py`, `tests/test_execution_client.py`, `tests/test_execution_worker.py`, `tests/test_process_run_node.py`, `tests/test_run_controller_unit.py`, `tests/test_passive_runtime_wiring.py`

Replaced the packet-owned `StartRunCommand.project_doc` transport with a typed `RuntimeSnapshot` built from a validated live-model snapshot of the current project. The run controller now builds that snapshot for the active workspace, the client strips it out of the trigger before queue transport, and the worker compiles typed workspace snapshots instead of consuming broad document payloads directly.

Added internal compatibility adapters so packet-owned direct callers that still pass legacy `project_doc` payloads continue to hydrate a `RuntimeSnapshot`, and UI manual runs still expose `trigger.project_doc` to workflow nodes without sending raw project documents across the worker boundary. The compiler/runtime DTO tests now cover typed snapshot round-tripping, UI trigger compatibility, and the unchanged worker/client execution behavior.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_execution_client.py tests/test_execution_worker.py tests/test_process_run_node.py tests/test_run_controller_unit.py tests/test_passive_runtime_wiring.py -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_execution_client.py tests/test_execution_worker.py -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: launch the application from `codex/arch-fifth-pass/p09-runtime-snapshot-execution-pipeline` and open or create a project with at least one runnable workflow; include a second workspace if you want to confirm the active-workspace boundary manually.
- Action: run a normal workflow from the active workspace, then pause/resume or stop a long-running node if you have one. Expected result: the run starts, console logs stream as before, and pause/resume/stop state transitions remain unchanged.
- Action: wire a `Start` node `trigger` output into a `Logger` node `message` input, open Workflow Settings, and run manually. Expected result: the logged trigger payload still includes `workflow_settings` and a `project_doc` entry even though the worker transport now uses the typed runtime snapshot.
- Action: switch to a different workspace and run again, or deliberately trigger a node failure. Expected result: only the selected workspace executes, and failure reporting still targets the correct workspace/node in the shell.

## Residual Risks

- Legacy direct callers that still submit raw `project_doc` payloads now rely on an internal compatibility adapter; packet-owned callers should migrate to `runtime_snapshot` to avoid depending on that bridge long term.
- Dedicated worktree verification still required a temporary local `./venv` helper link to the main checkout's Windows virtualenv because the worktree does not carry its own checked-out venv.

## Ready for Integration

- Yes: packet-owned run orchestration now transports typed runtime snapshots, the explicit `project_path` fallback remains for non-UI callers, and both required pytest gates passed.
