# Add-ons

## Purpose

Use this for repo-local add-on discovery, dependency-gated availability, persisted state, registry contributions, property-edit adapters, and Add-On Manager payloads.

## Start Here

- `ea_node_editor/addons/contracts.py`
- `ea_node_editor/addons/catalog.py`
- `ea_node_editor/addons/registry_contributions.py`
- `ea_node_editor/addons/state_changes.py`
- `ea_node_editor/addons/tabular_data/`
- `ea_node_editor/addons/mars/`
- `ea_node_editor/addons/mechanical/`
- `ea_node_editor/addons/mechanical/session.py`
- `ea_node_editor/addons/mechanical/owner_process.py`
- `ea_node_editor/addons/mechanical/backend.py`
- `ea_node_editor/addons/mechanical/commands.py`
- `ea_node_editor/addons/mechanical/graphics.py`
- `ea_node_editor/addons/mechanical/inspection.py`
- `ea_node_editor/addons/mechanical/runtime.py`
- `ea_node_editor/addons/mechanical/workbench.py`
- `ea_node_editor/ui/shell/registry_replacement.py`
- `ea_node_editor/ui/shell/presenters/addon_manager_presenter.py`
- `ea_node_editor/ui_qml/shell_addon_manager_bridge.py`

## Common Changes

- `addons/contracts.py` owns `AddOnState` and `AddOnRecord`; `addons/catalog.py` owns dependency-gated construction and lookup.
- `addons/registry_contributions.py` atomically contributes add-on semantic types, descriptors, and static function bundles. Conflicts reject the complete contribution.
- `addons/state_changes.py` only prepares normalized requested state. `RegistryReplacementCoordinator` owns compatibility checks, registry/service publication, persistence, notification, and rollback.
- The repo catalog contains Tabular Data, MARS, and Mechanical. Mechanical contributes dependency-gated semantic contracts and the real `mechanical.open_model`, `mechanical.search_tree`, `mechanical.fea_table`, `mechanical.camera_views`, `mechanical.export_image`, `mechanical.run_script`, and `mechanical.apdl_snippet` declarations.
- Tabular owns seven function declarations, property editing, native preload, compact refs, preview/query behavior, and one shared loader cache service.
- Mechanical property editing resolves immutable accepted Info/Report catalogue tables through each Model locator. It caches detached descriptor choices by catalogue identity/revision and never opens a source or resolves the live handle while projecting selectors.
- MARS owns three function declarations plus managed-package/toolchain/artifact metadata and JSONL subprocess execution.
- Mechanical contracts and run ownership are isolated in `addons/mechanical/`: `contracts.py` owns transient Model handles and bounded inline/table values, while `session.py` and `owner_process.py` own workspace-identified run sessions, source copies, revision admission, and a dedicated bounded subprocess protocol. On Windows the owner is assigned to a kill-on-close Job Object before backend imports, so worker death cannot orphan the owned process tree.
- Mechanical working copies use native Open/SaveAs or source-family Archive/Unarchive routes; Workbench projects retain their dependency structure. The 1 MiB owner request limit is control-only, while accepted catalogues use a hashed owner-spool descriptor and the existing bounded scientific codec. Run Script preflights Object/Text analysis selectors, executes in native tree order with cleaned injected context, advances the admitted model revision on every attempt, and returns a fresh Report locator only after every invocation succeeds. APDL Snippet defaults to supported Static Structural analyses, preflights all phases/steps/native setters/ownership collisions, and creates or updates deterministic marker-owned command objects with bounded verified rollback.
- Mechanical Search re-reads the admitted current model through the owner process, applies eleven COREX data predicates without native Outline filter calls or table-cell reads, and transfers typed Object/Property lists plus Details through the hashed `mechanical-search-v1` runtime-value spool. FEA Table separately reads actual Field/Variable values, bolt-pretension step states, native ITable columns, configured-result summaries, qualified PlotData/ForceReaction data, and mesh/layered worksheet rows, then publishes immutable scientific tables and Definitions through the same bounded codec contract. Camera Views reads saved names/original indices from direct exported `ModelView` children and returns typed snapshots. Export Image validates complete object/view selections before capture, preserves exact graphics and accepted result-addressing state, returns object-grouped `ImageValue` trees, and optionally publishes one rollback-protected no-clobber PNG batch. Restoration failures retire the native session.
- The Mechanical owner launcher uses module execution in source/dev and the statically allowlisted `--private-mechanical-owner` bootstrap role when frozen.
- Repo-owned declarations require authored node keywords and descriptions for every declared port; `tests/test_repo_owned_node_documentation.py` covers the exact 146-row catalog.
- Public plugin loading imports no add-on backend types. Add-on package IDs and apply policy remain private registry facts.

## Focused Verification

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_addon_catalog.py tests/test_addon_state_changes.py tests/test_registry_replacement.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_tabular_function_migration.py tests/test_tabular_addon_catalog.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_mars_function_migration.py tests/test_mars_nodes.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/mechanical_catalogue/test_contracts.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/mechanical_catalogue/test_session_lifecycle.py tests/mechanical_catalogue/test_owner_protocol.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/mechanical_catalogue/test_open_model.py tests/mechanical_catalogue/test_catalogue.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/mechanical_catalogue/test_search_tree.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/mechanical_catalogue/test_definition_tables.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/mechanical_catalogue/test_result_tables.py tests/mechanical_catalogue/test_worksheet_tables.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/mechanical_catalogue/test_camera_views.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/mechanical_catalogue/test_image_export.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/mechanical_catalogue/test_scripts.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/mechanical_catalogue/test_snippets.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_repo_owned_node_documentation.py --ignore=venv -q
```

## Breadcrumbs

- [Add-on Manager](../feature_routes/addon_manager.md)
- [Tabular Data Add-on And Preview](../feature_routes/tabular_data_addon_preview.md)
- [MARS Solver Add-on](../feature_routes/mars_solver_addon.md)

## Update Triggers

Update when add-on discovery, dependencies, semantic-type/function contributions, persisted state, property edit adapters, Mechanical session ownership, Tabular/MARS metadata, or Add-On Manager behavior changes.
