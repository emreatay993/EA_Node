# ADDON_MANAGER_BACKEND_PREPARATION P05: ANSYS DPF Add-On Package Extraction

## Objective

- Move the shipped ANSYS DPF surface behind a self-contained repo-local add-on package so DPF descriptors, helpers, docs, and viewer glue stop being hard-wired in core bootstrap and builtins.

## Preconditions

- `P00` is marked `PASS`.
- `P01` is marked `PASS`.
- No later `ADDON_MANAGER_BACKEND_PREPARATION` packet is in progress.

## Execution Dependencies

- `P00`
- `P01`

## Target Subsystems

- `ea_node_editor/nodes/bootstrap.py`
- `ea_node_editor/nodes/builtins/ansys_dpf.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_catalog.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_*.py`
- `ea_node_editor/addons/ansys_dpf/**`
- `ea_node_editor/help/dpf_operator_docs.py`
- `scripts/build_dpf_operator_doc_index.py`
- `scripts/generate_dpf_operator_docs.py`
- `tests/test_dpf_node_catalog.py`
- `tests/test_dpf_generated_helper_catalog.py`
- `tests/test_dpf_generated_operator_catalog.py`
- `tests/test_dpf_operator_help_lookup.py`

## Conservative Write Scope

- `ea_node_editor/nodes/bootstrap.py`
- `ea_node_editor/nodes/builtins/ansys_dpf.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_catalog.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_*.py`
- `ea_node_editor/addons/ansys_dpf/**`
- `ea_node_editor/help/dpf_operator_docs.py`
- `scripts/build_dpf_operator_doc_index.py`
- `scripts/generate_dpf_operator_docs.py`
- `tests/test_dpf_node_catalog.py`
- `tests/test_dpf_generated_helper_catalog.py`
- `tests/test_dpf_generated_operator_catalog.py`
- `tests/test_dpf_operator_help_lookup.py`
- `docs/specs/work_packets/addon_manager_backend_preparation/P05_ansys_dpf_addon_package_extraction_WRAPUP.md`

## Required Behavior

- Move DPF-specific descriptors, helper catalogs, operator catalogs, docs/index helpers, and package-owned metadata behind a repo-local add-on package boundary.
- Preserve the shipped DPF node families and helper/operator discovery semantics while removing direct core-bootstrap ownership of the DPF package definition.
- Keep the core plugin loader generic and compatible with the add-on contract from `P01`.
- Update inherited DPF catalog and help regression anchors in place when ownership paths move.

## Non-Goals

- No in-session hot apply or runtime/service rebuild yet; that belongs to `P06`.
- No Add-On Manager UI yet; that belongs to `P07`.
- No locked-node QML enforcement here; that belongs to `P04`.

## Verification Commands

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_dpf_node_catalog.py tests/test_dpf_generated_helper_catalog.py tests/test_dpf_generated_operator_catalog.py tests/test_dpf_operator_help_lookup.py --ignore=venv -q
```

## Review Gate

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_dpf_node_catalog.py tests/test_dpf_generated_operator_catalog.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/addon_manager_backend_preparation/P05_ansys_dpf_addon_package_extraction_WRAPUP.md`

## Acceptance Criteria

- DPF package ownership no longer lives as a hard-coded built-in-only bootstrap contract.
- The DPF add-on package can provide its own descriptors, helpers, docs, and package-owned metadata.
- Existing DPF node families and docs lookup behavior remain available through the new package boundary.
- The inherited DPF catalog/help regression anchors pass.

## Handoff Notes

- `P06` inherits the extracted package boundary and adds hot-apply rebuild semantics on top of it. Do not mix lifecycle rebuild work into this extraction packet.
