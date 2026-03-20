# ARCH_SIXTH_PASS P08: Execution Boundary Hardening

## Objective
- Make `RuntimeSnapshot` the single packet-owned run payload contract so runtime transport no longer carries duplicated `project_doc` fallback logic across UI, protocol, and worker layers.

## Preconditions
- `P00` through `P07` are marked `PASS` in [ARCH_SIXTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_STATUS.md).
- No later `ARCH_SIXTH_PASS` packet is in progress.

## Execution Dependencies
- `P07`

## Target Subsystems
- runtime snapshot transport
- execution client and worker boundary
- run-controller trigger construction

## Conservative Write Scope
- `ea_node_editor/execution/runtime_snapshot.py`
- `ea_node_editor/execution/client.py`
- `ea_node_editor/execution/protocol.py`
- `ea_node_editor/execution/worker.py`
- `ea_node_editor/execution/compiler.py`
- `ea_node_editor/ui/shell/controllers/run_controller.py`
- `tests/test_execution_client.py`
- `tests/test_execution_worker.py`
- `tests/test_process_run_node.py`
- `tests/test_run_controller_unit.py`
- `tests/test_passive_runtime_wiring.py`
- `docs/specs/work_packets/arch_sixth_pass/P08_execution_boundary_hardening_WRAPUP.md`

## Required Behavior
- Remove packet-owned duplicate `project_doc` fallback reconstruction across the UI, protocol, and worker path.
- Keep at most one explicit compatibility adapter if packet-external callers still need a transition path.
- Preserve current manual-run trigger behavior that workflow nodes observe, even if the internal transport is snapshot-only.
- Keep worker, compiler, and execution-client behavior stable.

## Non-Goals
- No session/autosave persistence redesign in this packet.
- No plugin/package or docs-only work in this packet.
- No shell verification contract changes in this packet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_execution_client.py tests/test_execution_worker.py tests/test_process_run_node.py tests/test_run_controller_unit.py tests/test_passive_runtime_wiring.py -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_execution_client.py tests/test_execution_worker.py -q`

## Expected Artifacts
- `docs/specs/work_packets/arch_sixth_pass/P08_execution_boundary_hardening_WRAPUP.md`

## Acceptance Criteria
- Packet-owned run transport uses one authoritative runtime snapshot boundary.
- Duplicate `project_doc` fallback logic is removed or collapsed into one explicit compatibility layer.
- Execution regressions pass with unchanged runtime behavior.

## Handoff Notes
- `P09` owns persistence overlay and autosave/session boundary cleanup after runtime transport is narrowed.
- Preserve user-visible trigger behavior even if the internal payload contract changes.
