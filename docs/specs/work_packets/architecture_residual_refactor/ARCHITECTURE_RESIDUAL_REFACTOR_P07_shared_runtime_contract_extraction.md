# ARCHITECTURE_RESIDUAL_REFACTOR P07: Shared Runtime Contract Extraction

## Objective

- Extract shared runtime handle, artifact, and viewer-session contracts into a neutral package consumed by both `nodes` and `execution`.

## Preconditions

- `P06` is marked `PASS` in [ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md](./ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_RESIDUAL_REFACTOR` packet is in progress.

## Execution Dependencies

- `P06`

## Target Subsystems

- `ea_node_editor/runtime_contracts/**`
- `ea_node_editor/nodes/runtime_refs.py`
- `ea_node_editor/nodes/plugin_contracts.py`
- `ea_node_editor/nodes/execution_context.py`
- `ea_node_editor/nodes/types.py`
- `ea_node_editor/execution/runtime_value_codec.py`
- `ea_node_editor/execution/dpf_runtime/base.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_common.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_viewer_adapter.py`
- `tests/test_plugin_loader.py`
- `tests/test_execution_worker.py`
- `tests/test_execution_viewer_service.py`
- `tests/test_dpf_runtime_service.py`
- `tests/test_dpf_viewer_widget_binder.py`

## Conservative Write Scope

- `ea_node_editor/runtime_contracts/**`
- `ea_node_editor/nodes/runtime_refs.py`
- `ea_node_editor/nodes/plugin_contracts.py`
- `ea_node_editor/nodes/execution_context.py`
- `ea_node_editor/nodes/types.py`
- `ea_node_editor/execution/runtime_value_codec.py`
- `ea_node_editor/execution/dpf_runtime/base.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_common.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_viewer_adapter.py`
- `tests/test_plugin_loader.py`
- `tests/test_execution_worker.py`
- `tests/test_execution_viewer_service.py`
- `tests/test_dpf_runtime_service.py`
- `tests/test_dpf_viewer_widget_binder.py`
- `docs/specs/work_packets/architecture_residual_refactor/P07_shared_runtime_contract_extraction_WRAPUP.md`

## Required Behavior

- Extract packet-owned runtime contract types into a neutral package used by both `nodes` and `execution`.
- Keep documented node SDK import surfaces stable by using curated re-exports where packet-owned compatibility is still required.
- Update DPF runtime and viewer consumers to depend on the neutral contracts instead of cross-package internals.
- Preserve plugin loader behavior and existing runtime payload compatibility.

## Non-Goals

- No new DPF or viewer features.
- No docs or QA closeout work yet; that belongs to `P08`.
- No re-expansion of `ea_node_editor.nodes.types` into another catch-all internal dependency bucket.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_plugin_loader.py tests/test_execution_worker.py tests/test_execution_viewer_service.py tests/test_dpf_runtime_service.py tests/test_dpf_viewer_widget_binder.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_plugin_loader.py tests/test_execution_viewer_service.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/architecture_residual_refactor/P07_shared_runtime_contract_extraction_WRAPUP.md`

## Acceptance Criteria

- Packet-owned shared runtime contracts live in a neutral package instead of direct `nodes` versus `execution` cross-dependence.
- Documented node SDK import surfaces remain stable.
- The inherited plugin-loader, worker, viewer-service, and DPF regression anchors pass.

## Handoff Notes

- `P08` updates verification, shell-catalog, and traceability proof against the new residual architecture seams.
