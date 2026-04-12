# DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR P02: DPF Operator Metadata Normalization

## Objective

- Normalize DPF operator and pin metadata into stable node, port, and type descriptors so later operator generation can be mechanical instead of policy-heavy.

## Preconditions

- `P01` is marked `PASS` in [DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_STATUS.md](./DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR_STATUS.md).
- No later `DPF_OPERATOR_PLUGIN_BACKEND_REFACTOR` packet is in progress.

## Execution Dependencies

- `P00`
- `P01`

## Target Subsystems

- `ea_node_editor/nodes/node_specs.py`
- `ea_node_editor/nodes/registry.py`
- `ea_node_editor/nodes/types.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_catalog.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_common.py`
- `tests/test_dpf_node_catalog.py`
- `tests/test_registry_validation.py`
- `tests/test_registry_filters.py`

## Conservative Write Scope

- `ea_node_editor/nodes/node_specs.py`
- `ea_node_editor/nodes/registry.py`
- `ea_node_editor/nodes/types.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_catalog.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_common.py`
- `tests/test_dpf_node_catalog.py`
- `tests/test_registry_validation.py`
- `tests/test_registry_filters.py`
- `docs/specs/work_packets/dpf_operator_plugin_backend_refactor/P02_dpf_operator_metadata_normalization_WRAPUP.md`

## Required Behavior

- Add a stable normalization contract that maps DPF operators and pins into node IDs, port specs, and internal data types.
- Carry enough metadata to distinguish required inputs, optional inputs, omitted operator defaults, explicit literals, and mutually exclusive input groups.
- Keep the mapping operators-first; do not broaden into non-operator `ansys.dpf.core` reflection.
- Keep the descriptor contract compatible with the existing registry validation rules rather than bypassing them.
- Update inherited DPF catalog and registry regression anchors in place.

## Non-Goals

- No runtime operator invocation changes yet; that belongs to `P03`.
- No missing-plugin placeholder projection yet; that belongs to `P04`.
- No large generated node rollout yet.

## Verification Commands

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_dpf_node_catalog.py tests/test_registry_validation.py tests/test_registry_filters.py --ignore=venv -q
```

## Review Gate

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_dpf_node_catalog.py tests/test_registry_validation.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/dpf_operator_plugin_backend_refactor/P02_dpf_operator_metadata_normalization_WRAPUP.md`

## Acceptance Criteria

- The DPF descriptor layer exposes stable source metadata for operator and pin identity.
- Optional/default/exclusive input semantics are explicit in the descriptor contract.
- Registry validation still owns compatibility enforcement for the normalized descriptors.
- The inherited DPF catalog and registry regression anchors pass.

## Handoff Notes

- `P03` consumes the normalized input and output contract and should not reinvent pin-binding policy.
