# Nodes, Registry, Built-ins, And Plugin Loading

## Purpose
Use this for node definitions, registry validation, built-in node families, data-type contracts, packages, and plugin loading.

## Lookup Aliases
- `node registry builtins`

## Start Here
- `ea_node_editor/nodes/bootstrap.py`
- `ea_node_editor/nodes/registry.py`
- `ea_node_editor/nodes/python_script_declaration.py`
- `ea_node_editor/nodes/plugin_contracts.py`
- `ea_node_editor/nodes/plugin_loader.py`
- `ea_node_editor/nodes/builtins/`
- `ea_node_editor/runtime_contracts/data_types.py`

## Built-in Contract Families
- Core values and media: `core_values.py`, `core_media.py`, and `core_value_nodes.py`.
- Geometry and spatial values: `geometry_contracts.py`, `geometry_primitives.py`, and `spatial_values.py`.
- Engineering contracts: `mesh_contracts.py`, `fem_contracts.py`, and `voxel_contracts.py`.
- Support values and nodes: `tree_path.py`, `units.py`, `viewer_viewport.py`, `security_contracts.py`, `reporting.py`, and `ai_ml_contracts.py`.
- Signal Plot is owned by `builtins/plot/signal.py` and emits `COREX.DataTypes.Image`.
- Python Script decorators resolve one applied source into ordinary ports,
  properties, and settings groups through the registry's instance-spec path.

## Boundaries
- Register built-ins through `build_builtin_registry()`; do not mutate catalog internals.
- Keep canonical data-type IDs under the `COREX.*` namespace.
- Keep source-product provenance, import adapters, comparison studies, and installed-product evidence outside the tracked repository.
- Add no compatibility alias for removed internal contracts unless an active public format requires it.

## Focused Tests
- `tests/test_registry_validation.py`
- `tests/test_plugin_loader.py`
- `tests/test_corex_contract_catalog.py`
- `tests/test_corex_type_conformance.py`
- `tests/test_core_value_types.py`
- `tests/test_spatial_values.py`
- `tests/test_geometry_contracts.py`
- `tests/test_mesh_contracts.py`
- `tests/test_fem_contracts.py`
- `tests/test_signal_plot_renderer.py`
- `tests/test_python_script_declaration.py`

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_registry_validation.py tests/test_plugin_loader.py tests/test_corex_contract_catalog.py tests/test_corex_type_conformance.py tests/test_python_script_declaration.py -q
```
