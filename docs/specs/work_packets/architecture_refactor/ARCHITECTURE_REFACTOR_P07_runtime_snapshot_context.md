# ARCHITECTURE_REFACTOR P07: Runtime Snapshot Context

## Objective
- Make runtime input versus mutable execution scratch explicit so `RuntimeSnapshot` semantics stop conflicting with packet-owned node behavior, execution-context typing becomes narrower than a service-locator escape hatch, and artifact-output code stops depending on private persistence internals.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_REFACTOR` packet is in progress.

## Execution Dependencies
- `P06`

## Target Subsystems
- `ea_node_editor/execution/runtime_snapshot.py`
- `ea_node_editor/nodes/types.py`
- `ea_node_editor/nodes/output_artifacts.py`
- `ea_node_editor/nodes/builtins/integrations_process.py`
- `ea_node_editor/persistence/artifact_store.py`
- `ea_node_editor/execution/`
- `tests/test_process_run_node.py`
- `tests/test_execution_artifact_refs.py`
- `tests/test_execution_handle_registry.py`
- `tests/test_project_artifact_store.py`
- `tests/test_passive_runtime_wiring.py`

## Conservative Write Scope
- `ea_node_editor/execution/runtime_snapshot.py`
- `ea_node_editor/execution/`
- `ea_node_editor/nodes/types.py`
- `ea_node_editor/nodes/output_artifacts.py`
- `ea_node_editor/nodes/builtins/integrations_process.py`
- `ea_node_editor/persistence/artifact_store.py`
- `tests/test_process_run_node.py`
- `tests/test_execution_artifact_refs.py`
- `tests/test_execution_handle_registry.py`
- `tests/test_project_artifact_store.py`
- `tests/test_passive_runtime_wiring.py`
- `docs/specs/work_packets/architecture_refactor/P07_runtime_snapshot_context_WRAPUP.md`

## Required Behavior
- Separate immutable run input from mutable execution scratch state instead of relying on silent mutation of nominally frozen runtime objects.
- Tighten `ExecutionContext` or adjacent runtime typing so packet-owned node code no longer depends on broad `Any`-style service escape hatches when narrower capability surfaces are sufficient.
- Replace packet-owned `_state` mutation or other private persistence-store reach-ins with supported `ProjectArtifactStore` APIs or explicit execution-side adapters.
- Preserve stored-output staging, artifact-ref resolution, and passive runtime exclusion behavior.
- Update inherited runtime regression anchors when the packet changes how runtime metadata is represented or accessed.

## Non-Goals
- No worker command-loop split yet.
- No DPF runtime modularization yet.
- No QML viewer bridge changes.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_process_run_node.py tests/test_execution_artifact_refs.py tests/test_execution_handle_registry.py tests/test_project_artifact_store.py tests/test_passive_runtime_wiring.py --ignore=venv -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_execution_artifact_refs.py tests/test_project_artifact_store.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/architecture_refactor/P07_runtime_snapshot_context_WRAPUP.md`

## Acceptance Criteria
- Runtime input and mutable execution scratch state are explicit instead of being conflated.
- Execution-context access is narrower and better typed for packet-owned capabilities.
- Artifact-output code uses explicit store APIs instead of packet-owned private persistence-state mutation.
- The packet-owned verification command passes.

## Handoff Notes
- `P08` should collapse protocol compatibility edges and split worker orchestration on top of this clearer runtime-state boundary.
