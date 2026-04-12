# DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR P03: Generic DPF Runtime Adapter

## Objective

- Replace handwritten DPF compute-path assumptions with a generic operator invocation adapter that consumes the normalized descriptor contract without yet mass-exposing generated operators.

## Preconditions

- `P02` is marked `PASS` in [DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_STATUS.md](./DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_STATUS.md).
- No later `DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR` packet is in progress.

## Execution Dependencies

- `P00`
- `P01`
- `P02`

## Target Subsystems

- `ea_node_editor/execution/compiler.py`
- `ea_node_editor/execution/dpf_runtime/contracts.py`
- `ea_node_editor/execution/dpf_runtime/base.py`
- `ea_node_editor/execution/dpf_runtime/materialization.py`
- `ea_node_editor/execution/dpf_runtime/operations.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_compute.py`
- `tests/test_dpf_compute_nodes.py`
- `tests/test_dpf_runtime_service.py`
- `tests/test_passive_runtime_wiring.py`
- `tests/test_execution_worker.py`

## Conservative Write Scope

- `ea_node_editor/execution/compiler.py`
- `ea_node_editor/execution/dpf_runtime/contracts.py`
- `ea_node_editor/execution/dpf_runtime/base.py`
- `ea_node_editor/execution/dpf_runtime/materialization.py`
- `ea_node_editor/execution/dpf_runtime/operations.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_compute.py`
- `tests/test_dpf_compute_nodes.py`
- `tests/test_dpf_runtime_service.py`
- `tests/test_passive_runtime_wiring.py`
- `tests/test_execution_worker.py`
- `docs/specs/work_packets/dpf_operator_plugin_backend_refactor/P03_generic_dpf_runtime_adapter_WRAPUP.md`

## Required Behavior

- Add a generic DPF operator invocation path that binds descriptor-driven inputs instead of relying on per-node handwritten helper assumptions.
- Preserve the semantic distinction between omitted optional inputs and explicit values when constructing operator bindings.
- Normalize output extraction and runtime error reporting for operator-backed compute nodes.
- Keep current handwritten DPF compute node behavior working on top of the new adapter.
- Update inherited DPF compute and runtime regression anchors in place when the adapter contract changes.

## Non-Goals

- No mass node generation or node-catalog UI expansion yet.
- No missing-plugin placeholder portability yet; that belongs to `P04`.
- No viewer-backend refactor beyond what current DPF compute-path compatibility requires.

## Verification Commands

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_dpf_compute_nodes.py tests/test_dpf_runtime_service.py tests/test_passive_runtime_wiring.py tests/test_execution_worker.py --ignore=venv -q
```

## Review Gate

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_dpf_compute_nodes.py tests/test_dpf_runtime_service.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/dpf_operator_plugin_backend_refactor/P03_generic_dpf_runtime_adapter_WRAPUP.md`

## Acceptance Criteria

- DPF compute execution no longer depends on packet-owned per-node binding assumptions for the covered operator-backed path.
- Optional/default input handling follows the descriptor contract from `P02`.
- Runtime outputs and errors are normalized through the new adapter layer.
- The inherited DPF compute and runtime regression anchors pass.

## Handoff Notes

- `P04` relies on the availability and runtime contracts from `P01` through `P03` but should stay focused on saved-project portability, not compute-path expansion.
