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
- `ea_node_editor/ui/shell/registry_replacement.py`
- `ea_node_editor/ui/shell/presenters/addon_manager_presenter.py`
- `ea_node_editor/ui_qml/shell_addon_manager_bridge.py`

## Common Changes

- `addons/contracts.py` owns `AddOnState` and `AddOnRecord`; `addons/catalog.py` owns dependency-gated construction and lookup.
- `addons/registry_contributions.py` atomically contributes add-on semantic types, descriptors, and static function bundles. Conflicts reject the complete contribution.
- `addons/state_changes.py` only prepares normalized requested state. `RegistryReplacementCoordinator` owns compatibility checks, registry/service publication, persistence, notification, and rollback.
- The repo catalog contains Tabular Data, MARS, and Mechanical. Mechanical currently contributes only dependency-gated, data-only semantic contracts; its runtime nodes arrive through the Mechanical catalogue route.
- Tabular owns seven function declarations, property editing, native preload, compact refs, preview/query behavior, and one shared loader cache service.
- MARS owns three function declarations plus managed-package/toolchain/artifact metadata and JSONL subprocess execution.
- Mechanical contract ownership is isolated in `addons/mechanical/contracts.py`: transient Model handles, Object/Property/CameraView inline values, selectors, and fixed catalogue/Definitions tables. Availability inspection does not import or launch Ansys.
- Repo-owned declarations require authored node keywords and descriptions for every declared port; `tests/test_repo_owned_node_documentation.py` covers the exact 139-row catalog.
- Public plugin loading imports no add-on backend types. Add-on package IDs and apply policy remain private registry facts.

## Focused Verification

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_addon_catalog.py tests/test_addon_state_changes.py tests/test_registry_replacement.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_tabular_function_migration.py tests/test_tabular_addon_catalog.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_mars_function_migration.py tests/test_mars_nodes.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/mechanical_catalogue/test_contracts.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_repo_owned_node_documentation.py --ignore=venv -q
```

## Breadcrumbs

- [Add-on Manager](../feature_routes/addon_manager.md)
- [Tabular Data Add-on And Preview](../feature_routes/tabular_data_addon_preview.md)
- [MARS Solver Add-on](../feature_routes/mars_solver_addon.md)

## Update Triggers

Update when add-on discovery, dependencies, semantic-type/function contributions, persisted state, property edit adapters, Tabular/MARS metadata, or Add-On Manager behavior changes.
