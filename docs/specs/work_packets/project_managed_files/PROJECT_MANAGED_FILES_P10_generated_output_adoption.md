# PROJECT_MANAGED_FILES P10: Generated Output Adoption

## Objective
- Add shared managed-output writer helpers and adopt them in the current file/spreadsheet producer path so generated outputs can stage into the artifact store and flow downstream through the new artifact-ref/runtime contract.

## Preconditions
- `P00` is marked `PASS` in [PROJECT_MANAGED_FILES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_STATUS.md).
- No later `PROJECT_MANAGED_FILES` packet is in progress.

## Execution Dependencies
- `P01`
- `P03`
- `P09`

## Target Subsystems
- `ea_node_editor/nodes/output_artifacts.py`
- `ea_node_editor/nodes/builtins/integrations_common.py`
- `ea_node_editor/nodes/builtins/integrations_file_io.py`
- `ea_node_editor/nodes/builtins/integrations_spreadsheet.py`
- `tests/test_integrations_track_f.py`
- `tests/test_execution_artifact_refs.py`
- `tests/test_project_artifact_store.py`

## Conservative Write Scope
- `ea_node_editor/nodes/output_artifacts.py`
- `ea_node_editor/nodes/builtins/integrations_common.py`
- `ea_node_editor/nodes/builtins/integrations_file_io.py`
- `ea_node_editor/nodes/builtins/integrations_spreadsheet.py`
- `tests/test_integrations_track_f.py`
- `tests/test_execution_artifact_refs.py`
- `tests/test_project_artifact_store.py`
- `docs/specs/work_packets/project_managed_files/P10_generated_output_adoption_WRAPUP.md`

## Required Behavior
- Add shared helpers for packet-owned nodes that generate durable files into managed staging slots.
- Update the current file/spreadsheet writer path so it can emit managed staged outputs via the artifact store instead of requiring only raw explicit paths.
- Ensure file-backed execution helpers resolve both raw paths and artifact refs through one packet-owned path so downstream consumers get absolute local files at the boundary.
- Keep explicit raw-path behavior available for current workflows that still want external output files.
- Make managed generated outputs follow the staging-first rules from `P03` and the explicit-save promotion/prune rules from `P04`.
- Add narrow regression coverage proving file/spreadsheet generated outputs can be produced, staged, and consumed through the packet-owned helpers.

## Non-Goals
- No concrete inline quick-toggle/status-chip heavy-output UI yet. `P11` owns that.
- No broad table/array/mesh artifact platform.
- No project-files dialog or import/repair UX changes.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_integrations_track_f.py tests/test_execution_artifact_refs.py tests/test_project_artifact_store.py --ignore=venv -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_integrations_track_f.py --ignore=venv -q`

## Expected Artifacts
- `ea_node_editor/nodes/output_artifacts.py`
- `docs/specs/work_packets/project_managed_files/P10_generated_output_adoption_WRAPUP.md`

## Acceptance Criteria
- File/spreadsheet producer flows can stage managed generated outputs through the artifact store.
- Downstream file-backed execution can consume those outputs through the shared resolver path.
- Raw explicit output-path behavior still works where users choose it.
- The packet does not add a broad artifact platform beyond the current generic/file-backed support.

## Handoff Notes
- `P11` should reuse the output-helper abstractions from this packet when it adds the Process Run stored-output adopter.
- Record the final helper names and node behaviors in the wrap-up so later heavy-output packets use the same storage semantics.
