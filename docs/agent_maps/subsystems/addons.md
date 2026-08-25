# Add-ons

## Purpose
Use this for repo-local add-ons, dependency-gated add-on availability, add-on manager backend payloads, add-on node routing, and add-on-provided viewer/plot backend factories.

## Start Here
- `ea_node_editor/addons/catalog.py`
- `ea_node_editor/addons/hot_apply.py`
- `ea_node_editor/addons/ansys_dpf/`
- `ea_node_editor/nodes/ansys_dpf_data_types.py`
- `ea_node_editor/addons/ansys_dpf/plot_catalog.py`
- `ea_node_editor/addons/tabular_data/`
- `ea_node_editor/addons/mars/`
- `ea_node_editor/ui/shell/controllers/addon_manager_controller.py`
- `ea_node_editor/ui/shell/presenters/addon_manager_presenter.py`
- `ea_node_editor/ui_qml/shell_addon_manager_bridge.py`

## Do Not Start Here
- Built-in node modules when a feature is add-on dependency gated.
- QML add-on UI before checking add-on catalog payloads.

## Common Changes
- Keep dependency-gated availability in add-on catalog and add-on-specific services.
- Live-shell hot apply routes through `RegistryReplacementCoordinator`: accepted add-on state is part of the full registry/worker identity, run and viewer admission is guarded, graph publication is non-normalizing, preferences persist after all reversible consumers, and failures restore registry/services/files without changing open graph data. The standalone service helper remains explicit and also uses non-normalizing scene replacement.
- Add-on backend manifests contribute semantic data-type families/types/conversions before node descriptors. Dependency-unavailable backends contribute nothing; a type conflict or invalid descriptor rejects the complete bundle. The DPF add-on owns the ten `COREX.Ansys.DPF.*` concrete contracts plus the evidence-backed `IMesh`/`IModel` parent relations in `nodes/ansys_dpf_data_types.py`.
- Add-on node descriptors follow the coordinated dataflow SDK: no execution/completed/failed ports, scalar pins use Item, variadic pins use List, and whole-topology or side-effect inputs use Tree. Generated DPF ellipsis pins declare List access in the committed catalog; MARS, Tabular, plot, integration, and SSH/SFTP descriptors must preserve their audited access declarations.
- Repo-owned Tabular and MARS node descriptors follow the shared help contract: authored node `keywords` and an authored `description` for every declared port. `tests/test_non_dpf_node_documentation.py` covers these add-ons together with built-ins; generated Ansys DPF descriptors are intentionally excluded.
- Update add-on manager payload tests for metadata changes.
- Tabular data refs should carry reopen metadata, including load options, selected object, selected columns, and array slice hints, because generic plot nodes can materialize refs directly without adapter nodes.
- The tabular add-on owns one process-wide loader service (`shared_tabular_loader_cache_service()`): parquet-first ingestion with per-key conversion locks, scan caching, ref-record registry, and arrow-compute preview queries. It preloads pyarrow native submodules at import because lazy arrow/duckdb DLL loads after Qt Quick has run access-violate the process on Windows; never import duckdb in GUI-process code (`tests/test_tabular_native_runtime_guards.py`).
- Add-on-owned property edit policy registers through `AddOnRegistration.property_edit_adapter_factory_attr`; the tabular add-on owns inspector `array_slice_2d_*` fields and selected-object property-pane overrides through its property edit adapter, not generic shell inspector/edit branches.
- The direct tabular plot showcase under `examples/tabular_plot_showcase_direct.cxproj` is a consumer-facing proof of that ref metadata; regenerate it with `scripts/generate_tabular_plot_showcase_example.py` when tabular ref metadata changes.
- For add-on nodes, update the add-on route and node registry route together. DPF-typed plot nodes are add-on descriptors loaded from `ansys_dpf/plot_catalog.py`, not always-on built-ins.
- The DPF library is workflow-first: nine curated workflow nodes (registered via `ansys_dpf/curated_catalog.py`) are the default surface; all generated `dpf.op.*` mirrors route under `Ansys DPF/Advanced/Raw API Mirror/<Family>` and the atomic building-block duplicates under `Ansys DPF/Advanced` — see the DPF feature route before re-categorizing.
- For add-on-provided plot backends, keep registration in `AddOnRegistration.plot_backend_factory_attr` and verify through the plotter route tests.
- Managed add-ons declare package IDs on `AddOnRegistration`; the MARS add-on installs asynchronously without a default five-minute ceiling, reports the selected COREX Python, remains disabled until verification succeeds, and never imports solver code into COREX. Source runs install only editable MARS with `--no-deps` into the active interpreter; frozen runs retain the app-managed AppData venv.

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_tabular_input_node.py tests/test_addon_manager_install.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_non_dpf_node_documentation.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_tabular_input_node.py tests/test_tabular_loaders.py tests/test_tabular_runtime_refs.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_plot_backend_registry.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_plot_dpf_node_contracts.py tests/test_dpf_node_catalog.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_core_dataflow_nodes.py tests/test_dpf_generated_operator_catalog.py tests/test_mars_nodes.py tests/test_tabular_extraction_nodes.py --ignore=venv -q
```

## Breadcrumbs
- [Add-on Manager](../feature_routes/addon_manager.md)
- [Plotter Nodes](../feature_routes/plotter_nodes.md)
- [Tabular Data Add-on And Preview](../feature_routes/tabular_data_addon_preview.md)
- [Ansys DPF Operator Nodes, Viewer, And Transport](../feature_routes/ansys_dpf_operator_viewer_transport.md)
- [MARS Solver Add-on](../feature_routes/mars_solver_addon.md)

## Update Triggers
Update when add-on discovery, add-on dependencies, add-on type contributions, add-on node access/control-port audits, add-on metadata, add-on property edit adapters, tabular ref metadata/reopen behavior, add-on-provided backend factories, DPF plot/generated descriptors, or add-on manager behavior changes.

## 2026-07-11 Performance Ownership

- `addons/ansys_dpf/operator_catalog.json` is the deterministic schema-1 package catalog; `operator_catalog.py` owns exact-match deserialization, warn-once supported-patch live fallback, and live-discovery failure omission. No writable user cache is allowed.
- Tabular shared-cache construction remains behind first use; do not move PyArrow import/preload later than the coordinated pre-QML startup seam.
