# Implementation Summary

- Packet: P11 Runtime Snapshot Only Protocol
- Branch Label: codex/corex-no-legacy-architecture-cleanup/p11-runtime-snapshot-only-protocol
- Commit Owner: worker
- Commit SHA: f3b2d0c36db28513e054bd84559b9e4f02e7e220
- Changed Files: Final packet-branch file set relative to wave base rev `40e55c72596a694d0cd7d78048b1376caeb2e52f`:
  - `ea_node_editor/execution/client.py`
  - `ea_node_editor/execution/dpf_runtime/viewer_session_backend.py`
  - `ea_node_editor/execution/protocol.py`
  - `ea_node_editor/execution/runtime_dto.py`
  - `ea_node_editor/execution/runtime_snapshot.py`
  - `ea_node_editor/execution/runtime_snapshot_assembly.py`
  - `ea_node_editor/execution/worker_protocol.py`
  - `ea_node_editor/execution/worker_runner.py`
  - `ea_node_editor/execution/worker_runtime.py`
  - `tests/test_architecture_boundaries.py`
  - `tests/test_execution_artifact_refs.py`
  - `tests/test_execution_client.py`
  - `tests/test_execution_worker.py`
  - `tests/test_run_controller_unit.py`
  - `tests/test_shell_run_controller.py`
  - `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P11_runtime_snapshot_only_protocol_WRAPUP.md`
- Artifacts Produced:
  - `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P11_runtime_snapshot_only_protocol_WRAPUP.md`

P11 makes runtime snapshots mandatory at start-run protocol boundaries, removes normal startup fallback rebuilds from project paths, and tightens runtime snapshot/workspace DTO ingestion to canonical fields. `project_path` remains only artifact-resolution context in the worker runtime path.

DPF viewer source handling now normalizes legacy fields-handle aliases before dispatch into the viewer-session service, while the DPF backend itself requires canonical `fields_container` source refs. Pause, resume, and stop behavior remains covered and unchanged.

# Verification

- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_execution_client.py tests/test_execution_worker.py tests/test_execution_artifact_refs.py tests/test_execution_handle_refs.py tests/test_execution_viewer_protocol.py tests/test_run_controller_unit.py tests/test_shell_run_controller.py tests/test_architecture_boundaries.py --ignore=venv -q` completed with `105 passed, 4 warnings, 23 subtests passed`.
- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_execution_client.py tests/test_execution_worker.py tests/test_execution_artifact_refs.py --ignore=venv -q` completed with `44 passed, 32 warnings`.
- PASS: `git diff --check` completed without whitespace errors.
- PASS: Warnings are Ansys DPF deprecation warnings for renamed gasket operators emitted from the installed dependency.
- Final Verification Verdict: PASS

# Manual Test Directives

Ready for manual testing.

- Launch the P11 worktree application, open or create a simple Start -> Logger -> End workflow, and run it. Expected: the run starts from the runtime snapshot, completes normally, and no project-document fallback load is required.
- Run a saved workflow that produces or consumes execution artifacts. Expected: artifact refs still resolve through the retained artifact context, with no worker project-path rebuild during startup.
- If DPF sample data and dependencies are available, run the DPF result-to-viewer path and open the embedded viewer. Expected: viewer materialization uses current `fields_container` source refs; backend materialization does not accept old fields-handle aliases directly.

# Residual Risks

- DPF viewer UI transport rewrite remains out of scope for P11 and belongs to P12.
- The verification environment emits dependency deprecation warnings from Ansys DPF operator aliases; no P11 failures are associated with those warnings.
- `project_path` is intentionally retained as artifact-resolution context, not as a normal runtime rebuild input.

# Ready for Integration

- Yes: P11 is committed, verification passed, and the wrap-up artifact is present in the packet worktree.
