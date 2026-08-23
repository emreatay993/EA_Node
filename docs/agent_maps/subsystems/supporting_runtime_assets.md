# Telemetry, Help, Benchmarks, Custom Workflows, And Runtime Contracts

## Purpose
Use this for support layers that are not owned by graph, persistence, or UI: telemetry, help, benchmarks, runtime contracts, mockups, and custom workflows.

## Start Here
- `ea_node_editor/runtime_contracts/data_types.py`
- `ea_node_editor/telemetry/`
- `ea_node_editor/help/`
- `ea_node_editor/benchmarks/`
- `ea_node_editor/runtime_contracts/`
- `ea_node_editor/custom_workflows/`
- `ea_node_editor/mockups/`
- `examples/`
- `scripts/`

## Runtime Contracts
- `runtime_contracts/data_tree.py` owns immutable path-indexed `DataTree` values and modifier ordering.
- `runtime_contracts/runtime_values.py` owns carrier serialization for native values, `TypedInlineValue`, `RuntimeHandleRef`, `RuntimeArtifactRef`, and `ImageValue`.
- `runtime_contracts/data_types.py` owns catalog registration, parent assignability, carrier compatibility, and catalog fingerprints.
- `runtime_contracts/interval_1d.py` owns immutable ordered `Interval1D` values and strict coercion.

## Boundaries
- Keep support ownership explicit; do not move graph, persistence, or UI behavior here.
- Keep generated benchmark outputs under ignored local roots.
- Publish accepted COREX behavior and current verification only.
- Keep `ea_node_editor/common/` dependency-light and free of graph, UI, execution, persistence, and nodes imports.

## Focused Tests
- `tests/test_typed_runtime_values.py`
- `tests/test_data_type_catalog.py`
- `tests/test_core_value_codecs.py`
- `tests/test_core_value_types.py`
- `tests/test_tree_path_types.py`
- `tests/test_core_media_types.py`
- `tests/test_unit_types.py`

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_typed_runtime_values.py tests/test_data_type_catalog.py tests/test_core_value_codecs.py -q
```
