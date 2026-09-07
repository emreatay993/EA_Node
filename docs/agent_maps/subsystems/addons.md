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
- `ea_node_editor/addons/mechanical/workbench.py`
- `ea_node_editor/ui/shell/registry_replacement.py`
- `ea_node_editor/ui/shell/presenters/addon_manager_presenter.py`
- `ea_node_editor/ui_qml/shell_addon_manager_bridge.py`

## Common Changes

- `addons/contracts.py` owns `AddOnState` and `AddOnRecord`; `addons/catalog.py` owns dependency-gated construction and lookup.
- `addons/registry_contributions.py` atomically contributes add-on semantic types, descriptors, and static function bundles. Conflicts reject the complete contribution.
- `addons/state_changes.py` only prepares normalized requested state. `RegistryReplacementCoordinator` owns compatibility checks, registry/service publication, persistence, notification, and rollback.
- The repo catalog contains Tabular Data, MARS, and Mechanical. Mechanical currently contributes only dependency-gated, data-only semantic contracts; its runtime nodes arrive through the Mechanical catalogue route.
- Tabular owns seven function declarations, property editing, native preload, compact refs, preview/query behavior, and one shared loader cache service.
- Mechanical property editing resolves immutable accepted Info/Report catalogue tables through each Model locator. It caches detached descriptor choices by catalogue identity/revision and never opens a source or resolves the live handle while projecting selectors.
- MARS owns three function declarations plus managed-package/toolchain/artifact metadata and JSONL subprocess execution.
- Mechanical contracts and run ownership are isolated in `addons/mechanical/`: `contracts.py` owns transient Model handles and bounded inline/table values, while `session.py` and `owner_process.py` own workspace-identified run sessions, source copies, revision admission, and a dedicated bounded subprocess protocol. On Windows the owner is assigned to a kill-on-close Job Object before backend imports, so worker death cannot orphan the owned process tree.
- Mechanical's current file copy is lifecycle staging, not qualified Workbench project copying. Model opening must replace Workbench-family staging with the native project/archive route in T05 and must not extract an internal database. The 1 MiB owner request limit applies only to control envelopes; T05 must provide existing COREX scientific/image transport outside that envelope for catalogue, table, and image payloads.
- The T03 owner launcher uses the active execution Python for source/dev and fails explicitly in a frozen executable. Packaging work must add an owned module-launch route before Mechanical is enabled in packaged acceptance; do not route `-m` back into the application executable implicitly.
- Repo-owned declarations require authored node keywords and descriptions for every declared port; `tests/test_repo_owned_node_documentation.py` covers the exact 139-row catalog.
- Public plugin loading imports no add-on backend types. Add-on package IDs and apply policy remain private registry facts.

## Focused Verification

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_addon_catalog.py tests/test_addon_state_changes.py tests/test_registry_replacement.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_tabular_function_migration.py tests/test_tabular_addon_catalog.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_mars_function_migration.py tests/test_mars_nodes.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/mechanical_catalogue/test_contracts.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/mechanical_catalogue/test_session_lifecycle.py tests/mechanical_catalogue/test_owner_protocol.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_repo_owned_node_documentation.py --ignore=venv -q
```

## Breadcrumbs

- [Add-on Manager](../feature_routes/addon_manager.md)
- [Tabular Data Add-on And Preview](../feature_routes/tabular_data_addon_preview.md)
- [MARS Solver Add-on](../feature_routes/mars_solver_addon.md)

## Update Triggers

Update when add-on discovery, dependencies, semantic-type/function contributions, persisted state, property edit adapters, Mechanical session ownership, Tabular/MARS metadata, or Add-On Manager behavior changes.
