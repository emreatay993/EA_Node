# ANSYS_DPF_FULL_PLUGIN_ROLLOUT P03: Family Taxonomy

## Objective

- Introduce the workflow-first DPF library taxonomy and split the catalog seams so operator rollout and helper rollout can proceed on disjoint write scopes in the next wave.

## Preconditions

- `P02` is marked `PASS` in [ANSYS_DPF_FULL_PLUGIN_ROLLOUT_STATUS.md](./ANSYS_DPF_FULL_PLUGIN_ROLLOUT_STATUS.md).
- No later `ANSYS_DPF_FULL_PLUGIN_ROLLOUT` packet is in progress.

## Execution Dependencies

- `P02`

## Target Subsystems

- `ea_node_editor/nodes/builtins/ansys_dpf_taxonomy.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_catalog.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_operator_catalog.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_helper_catalog.py`
- `tests/test_dpf_library_taxonomy.py`
- `tests/test_dpf_node_catalog.py`
- `tests/test_registry_filters.py`

## Conservative Write Scope

- `ea_node_editor/nodes/builtins/ansys_dpf_taxonomy.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_catalog.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_operator_catalog.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_helper_catalog.py`
- `tests/test_dpf_library_taxonomy.py`
- `tests/test_dpf_node_catalog.py`
- `tests/test_registry_filters.py`
- `PLANS_TO_IMPLEMENT/in_progress/ansys_dpf_full_plugin_rollout_packets/P03_family_taxonomy_WRAPUP.md`

## Required Behavior

- Define the first-wave DPF library taxonomy:
  - `Inputs`
  - `Helpers`
  - `Operators`
  - `Workflow`
  - `Viewer`
  - `Advanced`
- Define helper subcategories by workflow role (`Models`, `Scoping`, `Factories`, `Containers`, `Support`) instead of raw module name.
- Define operator-family category mapping rules that keep operator nodes grouped by DPF family.
- Retain original DPF source path, resolved family path, and stability metadata in descriptor source metadata.
- Split the shared catalog seam so later operator and helper packets can land on separate modules without editing the same file family.
- Update inherited node-library discoverability tests in place.

## Non-Goals

- No full operator descriptor generation yet; that belongs to `P04`.
- No helper descriptor generation yet; that belongs to `P05`.
- No runtime, serializer, or missing-plugin portability work yet; that belongs to `P06`.

## Verification Commands

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_dpf_library_taxonomy.py tests/test_dpf_node_catalog.py tests/test_registry_filters.py --ignore=venv -q
```

## Review Gate

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_dpf_library_taxonomy.py --ignore=venv -q
```

## Expected Artifacts

- `PLANS_TO_IMPLEMENT/in_progress/ansys_dpf_full_plugin_rollout_packets/P03_family_taxonomy_WRAPUP.md`
- `ea_node_editor/nodes/builtins/ansys_dpf_taxonomy.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_catalog.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_operator_catalog.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_helper_catalog.py`
- `tests/test_dpf_library_taxonomy.py`
- `tests/test_dpf_node_catalog.py`
- `tests/test_registry_filters.py`

## Acceptance Criteria

- The DPF library taxonomy is defined in code and reflected in the library-facing category paths.
- Descriptor metadata can preserve original source path, resolved family path, and stability level.
- The catalog seam is split so the next-wave operator and helper packets have disjoint write scopes.
- Taxonomy and discoverability regression anchors pass.

## Handoff Notes

- `P04` owns `ansys_dpf_operator_catalog.py` after this packet.
- `P05` owns `ansys_dpf_helper_catalog.py` after this packet.
- Neither `P04` nor `P05` should reopen taxonomy shape unless an inherited test proves it necessary.
