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
- `ea_node_editor/nodes/plugin_authoring.py`
- `ea_node_editor/nodes/builtin_functions/`
- `ea_node_editor/nodes/builtins/`
- `ea_node_editor/runtime_contracts/data_types.py`
- `docs/PLAN_COREX_NOVICE_PLUGIN_SDK.md`
- `docs/PLUGIN_AUTHORING_GUIDE.md`
- `docs/PLUGIN_MIGRATION_GUIDE.md`
- `docs/examples/signal_plot_function_plugin.py`
- `docs/examples/strain_conditioner_plugin.py`
- `docs/specs/requirements/COREX_NOVICE_PLUGIN_SDK_MIGRATION_INVENTORY.md`
- `docs/specs/perf/COREX_NOVICE_PLUGIN_SDK_QA_MATRIX.md`

## Built-in Contract Families
- Core values and media contracts: `core_values.py` and `core_media.py`; ordinary converted execution source lives as inert strings under `builtin_functions/`.
- Geometry and spatial contracts/helpers: `geometry_contracts.py`, `geometry_primitives.py`, and `spatial_values.py`; ordinary execution declarations live in `builtin_functions/{spatial.py,engineering_geometry.py}`.
- Engineering contracts/helpers: `mesh_contracts.py`, `fem_contracts.py`, `engineering_imports.py`, `engineering_viewer.py`, and `voxel_contracts.py`; ordinary declarations live in `builtin_functions/{engineering_fem.py,engineering_imports.py,engineering_viewer.py}`.
- Support contracts/helpers: `tree_path.py`, `units.py`, `viewer_viewport.py`, `security_contracts.py`, `reporting.py`, `rich_value_nodes.py`, and `ai_ml_contracts.py`; their converted declarations live in the matching `builtin_functions/` modules.
- Signal Plot declaration/execution is owned by inert `builtin_functions/plot_signal.py`; rendering remains in `execution/signal_plot_renderer.py` and emits `COREX.DataTypes.Image`.
- Public function plugins use the dependency-free top-level `corex` decorators and static `plugin_declaration.py` discovery. Python Script keeps its one-`run` signature while sharing only the bounded literal/control engine.
- `corex.__all__` is the exact 17-name public SDK. `ea_node_editor.nodes` exports
  no authoring helpers, `nodes/types.py` is deleted, and `nodes/decorators.py`,
  `NodePlugin`, `PluginDescriptor`, `node_type`, and `PLUGIN_BACKENDS` remain
  trusted implementation details only. The loader discovers public code only
  from explicitly configured loose/schema-2 paths through static parsing; it has
  no entry-point, class-probe, executable-manifest, or descriptor-discovery path.
- The internal owner `corex:builtin:functions` is the only reserved-ID function bundle. GUI bootstrap aggregates 20 inert source members, materializes the normal content-addressed generation, and registers exactly 68 `PythonFunctionEntry` records; workers independently attest and lazily execute it. The remaining 55 built-ins are the migration inventory's exact trusted exceptions, including Python Script, Trigger, Stream Gate, subnodes, three FEM pool/setup nodes, passive/custom surfaces, and generated private families.
- The complete private boundary is the 55 trusted non-DPF exceptions, 805 DPF
  exclusions, and three shipped add-on catalogs. Public authors never use those
  descriptor/backend records.
- `TrustedFactoryEntry` and `PythonFunctionEntry` are the mutually exclusive private registry implementations. Public function entries store only `PythonFunctionRef`; process workers re-hash the immutable generation and use `PythonFunctionAdapter` without exposing a callable to GUI discovery.
- Public loose files and installed schema-2 directories are parsed without import, checked for bundled imports, and copied byte-for-byte into `runtime/plugin_generations/<bundle-digest>/`; registry fingerprints exclude author/install paths. Worker registry construction reparses only the verified generation and never the mutable discovery roots.
- `build_plugin_candidate_registry(...)` builds fail-closed candidates into a caller-owned disposable generation root; one staged schema-2 package may replace only the installed package with the same exact name. Candidate and canonical registries must have the same full `NodeRegistry.contract_fingerprint()` before publication.
- `.cxpkg` import/export accepts schema 2 only. `package_manager.py` applies the shared static directory/declaration checks, exact source/asset hashes, Windows-safe paths and documented size/member limits; the 128-file ceiling includes `node_package.json`, and filesystem members must be singly linked regular files. ZIP exports use canonical manifest JSON, sorted members, fixed timestamps, and stored bytes for deterministic output. `PackageInstallTransaction` separates stage, reversible activation, commit, and retryable rollback; unresolved cleanup/restore work is exposed only as bounded issue codes.
- Package node icons must name declared `.svg`/`.png`/`.jpg`/`.jpeg` assets. Function entries expose private provenance rooted at the immutable validated generation, so title-icon projection never reopens mutable installed assets. Loose files cannot claim custom assets.
- `plugin_authoring.py` owns one-time readable/random identities, novice templates, non-executing temporary validation, structured summaries, direct-child no-clobber saves, expected-content overwrites, and attested saved-draft reads. It has no watcher, installer, environment selection, or legacy descriptor path.
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
- `tests/test_plugin_authoring.py`
- `tests/test_builtin_function_infrastructure.py`
- `tests/test_builtin_function_migration.py`
- `tests/test_remaining_builtin_function_migration.py`
- `tests/test_corex_contract_catalog.py`
- `tests/test_corex_type_conformance.py`
- `tests/test_core_value_types.py`
- `tests/test_spatial_values.py`
- `tests/test_geometry_contracts.py`
- `tests/test_mesh_contracts.py`
- `tests/test_fem_contracts.py`
- `tests/test_signal_plot_renderer.py`
- `tests/test_python_script_declaration.py`
- `tests/test_dead_code_hygiene.py`
- `tests/test_architecture_boundaries.py`
- `tests/test_packaging_configuration.py`
- `tests/test_novice_plugin_sdk_docs.py`
- `tests/non_dpf_catalog_fixture.py`
- `tests/fixtures/node_catalog/t17_non_dpf_documentation_overlay.json`
- `tests/test_non_dpf_node_documentation.py`

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_plugin_declaration.py tests/test_function_plugin.py tests/test_registry_validation.py tests/test_plugin_loader.py tests/test_package_manager.py tests/test_corex_contract_catalog.py tests/test_corex_type_conformance.py tests/test_python_script_declaration.py -q
.\venv\Scripts\python.exe -m pytest tests/test_plugin_authoring.py tests/test_plugin_authoring_controller.py tests/test_plugin_authoring_dialog.py -q
.\venv\Scripts\python.exe -m pytest tests/test_builtin_function_infrastructure.py tests/test_builtin_function_migration.py tests/test_remaining_builtin_function_migration.py tests/test_corex_contract_catalog.py tests/test_core_unit_nodes.py tests/test_spatial_values.py -q
.\venv\Scripts\python.exe -m pytest tests/test_novice_plugin_sdk_docs.py tests/test_non_dpf_node_documentation.py -q
```
