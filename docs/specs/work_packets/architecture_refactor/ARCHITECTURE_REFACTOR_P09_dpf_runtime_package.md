# ARCHITECTURE_REFACTOR P09: DPF Runtime Package

## Objective
- Break the DPF runtime service into a clearer execution-side package so optional imports, dataset materialization, and viewer-session runtime behavior stop accumulating in one oversized service file.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_REFACTOR` packet is in progress.

## Execution Dependencies
- `P08`

## Target Subsystems
- `ea_node_editor/execution/dpf_runtime_service.py`
- `ea_node_editor/execution/worker_services.py`
- `ea_node_editor/execution/`
- `tests/test_dpf_runtime_service.py`
- `tests/test_dpf_materialization.py`
- `tests/test_execution_viewer_service.py`
- `tests/test_execution_viewer_protocol.py`

## Conservative Write Scope
- `ea_node_editor/execution/dpf_runtime_service.py`
- `ea_node_editor/execution/worker_services.py`
- `ea_node_editor/execution/`
- `tests/test_dpf_runtime_service.py`
- `tests/test_dpf_materialization.py`
- `tests/test_execution_viewer_service.py`
- `tests/test_execution_viewer_protocol.py`
- `docs/specs/work_packets/architecture_refactor/P09_dpf_runtime_package_WRAPUP.md`

## Required Behavior
- Split DPF runtime behavior into clearer execution-side modules for optional import handling, dataset loading/materialization, and viewer-session runtime helpers.
- Keep worker-side viewer-session ownership in execution services rather than pushing live-session state back into graph payloads.
- Preserve packet-owned protocol and handle semantics already stabilized by earlier runtime packets.
- Update inherited DPF runtime and viewer-service regression anchors when the new module boundaries move existing assertions.

## Non-Goals
- No DPF node catalog or node-definition split yet.
- No QML viewer surface or shell bridge cleanup yet.
- No packaging/signing script cleanup yet.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_dpf_runtime_service.py tests/test_dpf_materialization.py tests/test_execution_viewer_service.py tests/test_execution_viewer_protocol.py --ignore=venv -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_dpf_runtime_service.py tests/test_dpf_materialization.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/architecture_refactor/P09_dpf_runtime_package_WRAPUP.md`

## Acceptance Criteria
- DPF runtime behavior is decomposed into smaller execution-side modules instead of one catch-all service file.
- Worker-side viewer-session ownership remains intact.
- The packet-owned verification command passes.

## Handoff Notes
- `P10` should split node-definition and viewer-adapter concerns on top of this runtime package rather than re-expanding execution-side responsibilities.
