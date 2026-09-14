# Tabular Data Add-on And Preview

## Purpose
Use this for the tabular data add-on, canonical data-view composition, full-output query rules, draft/fullscreen UI, bounded previews, tabular-to-plot payloads, retained source integrity and dependency-gated availability.

## Start Here
- `ea_node_editor/runtime_contracts/data_view.py` — immutable versioned single-file composition and output-rule recipes
- `ea_node_editor/addons/tabular_data/composition.py` — compiled block/segment/axis mapping through existing table refs; `tests/test_tabular_composition.py` covers windows, batch reads and retained reopen
- `ea_node_editor/addons/tabular_data/saved_queries.py` and `ea_node_editor/addons/tabular_data/query_worker.py` — complete saved output rules with an isolated DuckDB subprocess and derived Parquet; `tests/test_tabular_saved_queries.py` verifies complete reads, exact integers/datetimes and cancellation
- `ea_node_editor/ui/tabular_composer_session.py` — draft, virtual catalogue, conflict/Apply/Cancel, preview generations and export lifecycle
- `ea_node_editor/ui/tabular_composer_preview.py` — explicit ND preview planes independent of authored output slices
- `ea_node_editor/ui/tabular_composer_export.py` and `ea_node_editor/addons/tabular_data/exporting.py` — explicit export scopes and atomic publication
- `tests/test_tabular_composer_session.py`, `tests/test_tabular_composer_qml.py`, `tests/test_tabular_composer_export.py`, `tests/test_tabular_composer_example.py` — draft/undo, real QML, exports and portable example/Save As proof
- `scripts/generate_tabular_composer_example.py` and `examples/tabular_composer.README.md` — portable synthetic composition and Signal Plot workflow
- `tests/test_data_view_contract.py` — strict recipe validation, identities, axes and ref transport
- `ea_node_editor/addons/tabular_data/npz_members.py` — bounded NPY-header discovery and atomic selected-member mmap cache; `tests/test_tabular_npz_members.py` proves no full-array scan and warm reuse
- `ea_node_editor/addons/tabular_data/retained_sources.py` — fixed source descriptors and guarded retained reads
- `tests/test_retained_resources.py` — content identity, strict streaming, nested refs and HDF5 boundaries
- `ea_node_editor/addons/tabular_data/catalog.py`
- `ea_node_editor/addons/tabular_data/function_nodes.py` — inert declarations for the seven executable shells
- `ea_node_editor/addons/tabular_data/input_node.py`
- `ea_node_editor/addons/tabular_data/`
- `ea_node_editor/addons/tabular_data/loader_cache_service.py` — shared parquet-first loader service (see notes)
- `ea_node_editor/addons/tabular_data/source_backends.py` — format-specific scan/read/array/conversion owner
- `ea_node_editor/addons/tabular_data/preview_query.py` — normalized preview request and Python/Arrow evaluators
- `ea_node_editor/addons/tabular_data/extraction_nodes.py`
- `ea_node_editor/addons/tabular_data/property_edit_adapter.py`
- `ea_node_editor/execution/plugin_worker_runtime.py`
- `ea_node_editor/ui/tabular_preview_provider.py`
- `ea_node_editor/ui/tabular_preview_async.py` — worker pool for cold preview resolution
- `ea_node_editor/ui/shell/inspector_projection.py`
- `ea_node_editor/ui_qml/tabular_preview_table_model.py`
- `ea_node_editor/ui_qml/components/graph/tabular/`
- `ea_node_editor/ui_qml/components/graph/tabular/GraphTabularPreviewSurface.qml`
- `ea_node_editor/ui/icon_registry.py` and `ea_node_editor/ui_qml/components/shell/icons/table-configure.svg` — tintable table-and-sliders icon for the shared floating-toolbar Configure data action
- `ea_node_editor/ui_qml/components/graph/tabular/TabularTableViewport.qml`
- `ea_node_editor/ui_qml/components/graph/tabular/ComposerButton.qml` and `ea_node_editor/ui_qml/components/graph/tabular/ComposerField.qml` — composer-local shared-dialog styling with inherited theme/contrast tokens
- `ea_node_editor/ui_qml/components/graph/tabular/ComposerComboBox.qml`, `ea_node_editor/ui_qml/components/graph/tabular/ComposerSpinBox.qml`, `ea_node_editor/ui_qml/components/graph/tabular/ComposerCheckBox.qml`, `ea_node_editor/ui_qml/components/graph/tabular/ComposerTabButton.qml`, `ea_node_editor/ui_qml/components/graph/tabular/ComposerCard.qml` — archive-aware selectors and focused, compact workspace controls
- `ea_node_editor/ui_qml/content_fullscreen_bridge.py`
- `ea_node_editor/ui/shell/host_presenter.py`
- `scripts/verify_tabular_perf.py` — perf harness (budgets + cold/warm cache runs)
- `scripts/generate_large_tabular_csv.py` — gigabyte fixture + benchmark project synthesis
- `tests/test_tabular_preview_provider.py`
- `tests/test_tabular_function_migration.py`
- `tests/test_tabular_input_node.py`
- `tests/test_tabular_extraction_nodes.py`
- `tests/test_tabular_preview_async.py`
- `tests/test_tabular_perf_guards.py`
- `tests/test_tabular_native_runtime_guards.py`
- `tests/test_content_fullscreen_bridge.py`
- `tests/test_passive_property_editors.py`
- `tests/test_graph_surface_input_controls.py`
- `tests/graph_surface/passive_host_interaction_suite.py`
- `tests/test_tabular_loaders.py`
- `tests/test_tabular_preview_query.py`
- `tests/test_tabular_project_managed_data.py`
- `examples/tabular_plot_showcase.README.md`
- `examples/tabular_plot_showcase_direct.cxproj`

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_tabular_function_migration.py tests/test_tabular_addon_catalog.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_tabular_preview_provider.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_tabular_input_node.py tests/test_tabular_loaders.py tests/test_tabular_preview_query.py tests/test_tabular_project_managed_data.py tests/test_tabular_runtime_refs.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_tabular_extraction_nodes.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_passive_property_editors.py tests/test_graph_surface_input_controls.py tests/graph_surface/passive_host_interaction_suite.py --ignore=venv -q
```

## Breadcrumbs
- [Add-ons](../subsystems/addons.md)
- [Passive, Media, And Tabular Surfaces](../subsystems/passive_media_tabular_surfaces.md)
- [Plotter Nodes](plotter_nodes.md)

## Surface Ownership Notes
- The composer implementation is tracked in `docs/PLAN_Tabular_Data_Composer.md`. `DataViewDefinition` owns data-only authored mapping and output rules, bounded to 48 KiB so parser/provenance metadata fits the existing ref limit. `TabularLoadOptions.data_view` carries its canonical payload; no source values or presentation state are embedded.
- `loader_cache_service.py::column_arrays` is the shared column reader for generic and Signal plots. Source opening caches bounded schema facts; omit that optional field if merged ref metadata exceeds 64 KiB. Input views define the actual output; preview hints no longer change plot inputs. Explicit extraction refs still select from that output. `sample_array` provides guarded rendering samples while array plot exports retain the full configured extent.
- The seven executable Tabular shells are inert `corex` declarations in `function_nodes.py`, statically parsed as one digest-pinned function bundle owned by `ea_node_editor.builtins.tabular_data`. `catalog.py` retains dependency gating, manifest/toolchain facts, zero descriptors, exact function IDs, and lazy source loading. The worker accepts private declaration metadata only because the trusted registry already carries that exact owner contract; public bundles do not inherit this trust.
- Enable, disable, and dependency-unavailable rebuilds add or remove the Tabular manifest, seven entries, and bundle together. Add-on discovery reports declared IDs without loading or executing the function source, and the existing full registry-replacement coordinator remains the hot-apply owner.
- All tabular consumers share one process-wide `shared_tabular_loader_cache_service()` (thread-safe records + scan cache + per-key conversion locks). Format-specific scan/read/array/conversion behavior lives in `source_backends.py`; text/Excel sources convert once into the managed parquet cache (chunked `pyarrow.csv.read_csv` blocks — NEVER `open_csv`, see `tests/test_tabular_native_runtime_guards.py`). Row counts are never computed by rescanning the source; they backfill from cache metadata. `EA_TABULAR_CACHE_DIR` overrides the cache dir.
- Retained reads enforce a content binding before exposing results, including bounded streaming batches and copied array materializations. Binding scopes propagate to internal I/O threads; source-bound record/parquet cache keys include content SHA-256 so equal size/mtime cannot alias old data. Ordinary fresh previews keep their existing reopen behavior. HDF5 retention supports contained datasets reached by hard links; virtual datasets, external storage and non-hard-link paths remain ineligible while ordinary loads stay available.
- Tabular output availability learned from settlement is node-scoped solution state. Exact invalidation/recompute IDs clear only affected observations; graph mutation helpers no longer clear every node in the workspace, and only a store-accepted current settlement may observe a replacement output kind.
- Cold inline previews and composer metadata/data reads run on `TabularPreviewWorkerPool`; the graph presenter caches bounded results keyed by source stamp and semantic options. The composer owns a draft generation and cancellation context, rejects obsolete completions, and uses the existing bulk mutation for one undoable Apply. Source/mapping changes clear obsolete rows immediately. The fullscreen bridge delegates lifecycle to its tabular session; explicit committed-window APIs remain separately available.
- `preview_query.py` normalizes selected columns, filters, search, sort, offset, and limit once. Parquet-backed sources use its Arrow evaluator with exact totals and typed values; `source_direct`/HDF5 use its bounded Python evaluator with the existing 200k cap, truncated totals, and source typing. Missing/null/blank named-column values share the locked operator policy. duckdb must NOT be imported in the GUI process.
- App startup explicitly calls `_preload_native_tabular_runtime()` before QML construction because lazy Arrow DLL loads after Qt Quick has run crash the process. The Tabular package and catalog stay import-light for discovery; extend the explicit preload list when using a new PyArrow submodule.
- `examples/tabular_plot_showcase_direct.cxproj` demonstrates direct `TabularDataRef` / `ArrayDataRef` plotting without Python Script adapter nodes. Regenerate it through `scripts/generate_tabular_plot_showcase_example.py` when selected-column, array-slice, or plot-side mapping contracts change.
- `data_view` is the persisted versioned recipe. Physical `TabularLoadOptions.selected_object` remains a backend detail. NPZ discovery reads bounded NPY headers only; supported selected members are atomically extracted to a shared-budget read-only mmap cache. The virtual source catalogue preserves all exact, case-sensitive member IDs and never truncates search to 50 choices.
- Tabular Input's source path dialog filter is declared on its `PropertySpec.file_filter` using the shared tabular filter constant. The Path property disables its inline editor, so the node shows the Path port without a path box or Browse button; source selection remains in the inspector and surface toolbar. Its graph-surface Source toolbar dropdown routes `path` browse requests through the same generic shell forwarding with `external_link` / `managed_copy` source modes. Keep tabular file-extension changes in the add-on node metadata/shared filter list and let shell browse forwarding stay generic.
- Excel-style table paste creates the same `tabular.input` node with a staged `.tsv` source path. Shared parsing belongs to `clipboard_paste_nodes.py`; `CanvasImportController` creates data immediately in Automatic mode or offers data, Markdown, plain Text, and Panel in the common Ask dialog. Disabled Tabular support is reported without silently substituting a note. Do not add an add-on-specific paste path.
- Shipped `tabular.input` receives exact registry-owned file-content provenance for `path`; the add-on declaration stays unchanged and public/package rows cannot opt into the overlay.
- The input inspector projects a metadata-only configuration summary and migration notice. Authoring lives in the persistent Configure action and fullscreen Mapping/Output rules/Source options tabs. Extraction-node friendly controls remain add-on-owned in `property_edit_adapter.py`.
- The fullscreen composer uses a source sidebar, compact section tabs and separate preview/footer regions. Empty sources show onboarding rather than an unconfigured mapping form. Optional mapping controls expand without changing the draft. `tests/test_tabular_composer_qml.py` exercises light/dark rendering, keyboard member/axis input and non-overlapping short/narrow layouts; composer controls do not change global Qt styling.
- Lazy extraction execution helpers live in `extraction_nodes.py`: `tabular.table_filter` and `tabular.array_slice_2d` produce `TabularWindowRef` / `ArraySlice2DRef`; writer nodes and generic plot nodes consume those refs directly; materializer nodes are explicit memory-loading escape hatches for scripts/debugging.
- Composer exports distinguish visible preview, selected cell/columns and complete configured output, including an explicit draft label. They run on a worker and publish only complete files. Full ND NPY output uses bounded tiles; text/Excel writers stream. Inline visible export and graph writer nodes reuse the tabular writers. Never overwrite the source as an export destination.
- Extraction-node row/column bounds are stored as hidden zero-based canonical properties and projected by the add-on property adapter into one-based row controls, spreadsheet-style column controls, column chips, and summary rows. `0` row/column limits mean all remaining data and should remain visible in help/summary text.
- Configure data is the first tabular floating-toolbar action, using the table-and-sliders icon and the existing fullscreen action ID. It dispatches through the shared surface-action route to the same draft composer for empty, selection-required, ready and error states. No Configure button or reserved button row remains inside the node; the preview uses that space. Migration review notices remain visible. Header selection and widths are presentation state; they do not mutate output recipes.
- Project and fragment boundaries use `common/node_property_migrations.py` to convert old input source choices to full-output views and preserve prior hints only in a dismissible review notice. Restore-prior-selection edits the draft explicitly; extraction nodes are unchanged. Plot descriptors and schema projections consume the new view, never retired preview hints.

## Update Triggers
Update when tabular dependencies, input node ports, source path browse filters, preview model, tabular QML, tabular clipboard paste behavior, or managed data tests change.
Update when selected-column or array-slice hints are persisted for downstream consumers such as plot nodes.
Update when lazy tabular extraction refs, writer/materializer nodes, output path filters, or `0` full-limit semantics change.
Update when Tabular function declarations, dependency-gated bundle registration, worker identity, or hot-apply membership changes.
Update when selector scan payloads, property-pane `selected_object` editors, property edit adapters, tabular-to-plot auto-preview payloads, visible export behavior, Save As routing, or tabular surface selection-required UX changes.

## 2026-07-11 Performance Ownership

- `.txt` delimiter detection consumes at most the first `4096` characters. Shared tabular cache/service internals allocate on first use, but coordinated PyArrow preload remains explicitly before QML construction.
