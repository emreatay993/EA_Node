# ARCHITECTURE_REFACTOR P08: Worker Protocol Split

## Objective
- Collapse runtime compatibility edges and split `execution/worker.py` into focused orchestration modules so worker behavior stops concentrating protocol parsing, run control, node execution, and event publication in one file.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_REFACTOR` packet is in progress.

## Execution Dependencies
- `P07`

## Target Subsystems
- `ea_node_editor/execution/worker.py`
- `ea_node_editor/execution/protocol.py`
- `ea_node_editor/execution/worker_services.py`
- `ea_node_editor/execution/`
- `ea_node_editor/nodes/types.py`
- `tests/test_execution_artifact_refs.py`
- `tests/test_execution_worker.py`
- `tests/test_execution_client.py`
- `tests/test_run_controller_unit.py`
- `tests/test_shell_run_controller.py`

## Conservative Write Scope
- `ea_node_editor/execution/worker.py`
- `ea_node_editor/execution/protocol.py`
- `ea_node_editor/execution/worker_services.py`
- `ea_node_editor/execution/`
- `ea_node_editor/nodes/types.py`
- `tests/test_execution_artifact_refs.py`
- `tests/test_execution_worker.py`
- `tests/test_execution_client.py`
- `tests/test_run_controller_unit.py`
- `tests/test_shell_run_controller.py`
- `docs/specs/work_packets/architecture_refactor/P08_worker_protocol_split_WRAPUP.md`

## Required Behavior
- Split worker responsibilities into focused modules or helpers for command loop, run control, node execution, and event publication.
- Collapse legacy `project_doc` compatibility to a narrow edge adapter instead of letting it leak through core worker paths.
- Preserve packet-owned command and event semantics at the public boundary while reducing internal coupling.
- Update inherited runtime and run-controller anchors when packet-owned protocol seams change, including `tests/test_execution_artifact_refs.py` when wire-level runtime payload assertions move.

## Non-Goals
- No DPF-specific modularization yet.
- No viewer-surface or QML bridge changes.
- No release/docs cleanup yet.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_execution_worker.py tests/test_execution_client.py tests/test_execution_artifact_refs.py tests/test_run_controller_unit.py tests/test_shell_run_controller.py --ignore=venv -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_execution_client.py tests/test_execution_artifact_refs.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/architecture_refactor/P08_worker_protocol_split_WRAPUP.md`

## Acceptance Criteria
- Worker orchestration is decomposed into focused modules or helpers instead of one oversized file.
- `project_doc` compatibility survives only at a narrow edge adapter.
- The packet-owned verification command passes.

## Handoff Notes
- `P09` and `P10` should build DPF runtime and node-layer cleanup on top of this narrower worker boundary rather than reopening broad worker responsibilities.
