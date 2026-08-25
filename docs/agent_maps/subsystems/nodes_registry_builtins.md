# Nodes, Registry, Built-ins, And Plugin Loading

## Purpose
Use this for node definitions, registry validation, built-in node families, data-type contracts, packages, and plugin loading.

## Lookup Aliases
- `node registry builtins`

## Start Here
- `corex/__init__.py`
- `ea_node_editor/nodes/bootstrap.py`
- `ea_node_editor/nodes/registry.py`
- `ea_node_editor/nodes/declaration_engine.py`
- `ea_node_editor/nodes/function_plugin.py`
- `ea_node_editor/nodes/plugin_declaration.py`
- `ea_node_editor/nodes/plugin_generation.py`
- `ea_node_editor/nodes/python_script_declaration.py`
- `ea_node_editor/nodes/execution_context.py`
- `ea_node_editor/nodes/plugin_contracts.py`
- `ea_node_editor/nodes/plugin_loader.py`
- `ea_node_editor/nodes/package_manager.py`
- `ea_node_editor/nodes/builtins/`
- `ea_node_editor/runtime_contracts/data_types.py`
- `docs/PLAN_COREX_NOVICE_PLUGIN_SDK.md`
- `docs/specs/requirements/COREX_NOVICE_PLUGIN_SDK_MIGRATION_INVENTORY.md`

## Built-in Contract Families
- Core values and media: `core_values.py`, `core_media.py`, and `core_value_nodes.py`.
- Geometry and spatial values: `geometry_contracts.py`, `geometry_primitives.py`, and `spatial_values.py`.
- Engineering contracts: `mesh_contracts.py`, `fem_contracts.py`, and `voxel_contracts.py`.
- Support values and nodes: `tree_path.py`, `units.py`, `viewer_viewport.py`, `security_contracts.py`, `reporting.py`, and `ai_ml_contracts.py`.
- Signal Plot is owned by `builtins/plot/signal.py` and emits `COREX.DataTypes.Image`.
- Public function plugins use the dependency-free top-level `corex` decorators and static `plugin_declaration.py` discovery. Python Script keeps its one-`run` signature while sharing only the bounded literal/control engine.
- `TrustedFactoryEntry` and `PythonFunctionEntry` are the mutually exclusive private registry implementations. Public function entries store only `PythonFunctionRef`; process workers re-hash the immutable generation and use `PythonFunctionAdapter` without exposing a callable to GUI discovery.
- Public loose files and installed schema-2 directories are parsed without import, checked for bundled imports, and copied byte-for-byte into `runtime/plugin_generations/<bundle-digest>/`; registry fingerprints exclude author/install paths. Worker registry construction reparses only the verified generation and never the mutable discovery roots.
- `.cxpkg` import/export accepts schema 2 only. `package_manager.py` applies the shared static directory/declaration checks, exact source/asset hashes, Windows-safe paths and documented size/member limits; the 128-file ceiling includes `node_package.json`, and filesystem members must be singly linked regular files. ZIP exports use canonical manifest JSON, sorted members, fixed timestamps, and stored bytes for deterministic output. Install replacement is staged beside the plugins root and restores the prior directory if activation fails; cleanup failures log only bounded codes.
- Package node icons must name declared `.svg`/`.png`/`.jpg`/`.jpeg` assets. Function entries expose private provenance rooted at the immutable validated generation, so title-icon projection never reopens mutable installed assets. Loose files cannot claim custom assets.
- Python Script decorators resolve one applied source into ordinary ports,
  properties, and settings groups through the registry's instance-spec path.

## Boundaries
- Register built-ins through `build_builtin_registry()`; do not mutate catalog internals.
- Keep `corex/` dependency-free and normalize its static declarations into the existing registry/presentation model; do not import public plugin source in GUI discovery.
- Keep public function entries non-constructible through `NodeRegistry.create()` so trusted in-process execution cannot acquire their callable.
- Keep generation pruning explicit and protect both active and externally referenced digests; never overwrite a mismatched existing digest directory.
- Keep package archives free of compatibility fields, dependency installers, descriptor overrides, nested Python packages, and executable validation hooks. Schema-1 rejection uses the migration pointer in `SCHEMA_1_UNSUPPORTED_MESSAGE`.
- During the novice function-SDK cutover, preserve the normalized 133-node non-DPF baseline in `tests/fixtures/node_catalog/pre_cutover_non_dpf_catalog.json` and follow the migration inventory's exact convert/internal-exception/DPF-exclusion classification.
- Keep canonical data-type IDs under the `COREX.*` namespace.
- Keep source-product provenance, import adapters, comparison studies, and installed-product evidence outside the tracked repository.
- Add no compatibility alias for removed internal contracts unless an active public format requires it.

## Focused Tests
- `tests/test_registry_validation.py`
- `tests/test_plugin_declaration.py`
- `tests/test_function_plugin.py`
- `tests/test_plugin_loader.py`
- `tests/test_plugin_worker_loading.py`
- `tests/test_package_manager.py`
- `tests/test_node_package_io_ops.py`
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
.\venv\Scripts\python.exe -m pytest tests/test_plugin_declaration.py tests/test_function_plugin.py tests/test_registry_validation.py tests/test_plugin_loader.py tests/test_package_manager.py tests/test_corex_contract_catalog.py tests/test_corex_type_conformance.py tests/test_python_script_declaration.py -q
```
