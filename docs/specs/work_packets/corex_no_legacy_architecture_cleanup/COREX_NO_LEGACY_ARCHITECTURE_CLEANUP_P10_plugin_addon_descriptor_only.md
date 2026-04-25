# COREX_NO_LEGACY_ARCHITECTURE_CLEANUP P10: Plugin Add-on Descriptor Only

## Objective

- Require descriptor/add-on records for plugin and add-on loading, retiring plugin class probing, DPF compatibility alias modules, add-on ID aliases, and synthetic namespace package fallback.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and only plugin/add-on files needed for this packet

## Preconditions

- `P09` is marked `PASS`.

## Execution Dependencies

- `P09`

## Target Subsystems

- `ea_node_editor/nodes/plugin_loader.py`
- `ea_node_editor/nodes/plugin_contracts.py`
- `ea_node_editor/nodes/package_manager.py`
- `ea_node_editor/addons/catalog.py`
- `ea_node_editor/addons/hot_apply.py`
- `ea_node_editor/addons/ansys_dpf/__init__.py`
- `ea_node_editor/addons/ansys_dpf/catalog.py`
- `ea_node_editor/nodes/builtins/ansys_dpf.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_catalog.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_common.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_helper_catalog.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_operator_catalog.py`
- `pyproject.toml`
- `tests/test_plugin_loader.py`
- `tests/test_package_manager.py`
- `tests/test_registry_validation.py`
- `tests/test_dpf_runtime_service.py`
- `tests/test_dpf_viewer_node.py`
- `tests/test_execution_viewer_service.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P10_plugin_addon_descriptor_only_WRAPUP.md`

## Conservative Write Scope

- `ea_node_editor/nodes/plugin_loader.py`
- `ea_node_editor/nodes/plugin_contracts.py`
- `ea_node_editor/nodes/package_manager.py`
- `ea_node_editor/addons/catalog.py`
- `ea_node_editor/addons/hot_apply.py`
- `ea_node_editor/addons/ansys_dpf/__init__.py`
- `ea_node_editor/addons/ansys_dpf/catalog.py`
- `ea_node_editor/nodes/builtins/ansys_dpf.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_catalog.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_common.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_helper_catalog.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_operator_catalog.py`
- `pyproject.toml`
- `tests/test_plugin_loader.py`
- `tests/test_package_manager.py`
- `tests/test_registry_validation.py`
- `tests/test_dpf_runtime_service.py`
- `tests/test_dpf_viewer_node.py`
- `tests/test_execution_viewer_service.py`
- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P10_plugin_addon_descriptor_only_WRAPUP.md`

## Required Behavior

- Delete plugin class probing, `_legacy_plugin_spec`, tuple shorthand coercion, synthetic namespace package creation, and entry-point compatibility branches that only exist for unshipped third-party packages.
- Require one descriptor-returning module/package API for plugin descriptors and backend descriptors.
- Require package manifests to include explicit names; remove directory-name fallback for invalid package metadata.
- Replace DPF compatibility alias modules and `__getattr__` forwarding with one canonical DPF descriptor catalog.
- Remove add-on ID aliases such as `ansys.dpf` / `ansys_dpf` when focusing the add-on manager.
- Split add-on enabled-state persistence from runtime rebuild orchestration where practical; document any remaining hot-apply runtime coupling in the wrap-up.

## Non-Goals

- No viewer transport/session state consolidation; that belongs to `P12`.
- No runtime snapshot protocol cleanup; that belongs to `P11`.
- No docs/traceability closeout; that belongs to `P14`.

## Verification Commands

1. `.\venv\Scripts\python.exe -m pytest tests/test_plugin_loader.py tests/test_package_manager.py tests/test_registry_validation.py tests/test_dpf_runtime_service.py tests/test_dpf_viewer_node.py tests/test_execution_viewer_service.py --ignore=venv -q`

## Review Gate

- `.\venv\Scripts\python.exe -m pytest tests/test_plugin_loader.py tests/test_package_manager.py --ignore=venv -q`

## Expected Artifacts

- `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/P10_plugin_addon_descriptor_only_WRAPUP.md`

## Acceptance Criteria

- Plugin/add-on loading is descriptor-only for packet-owned paths.
- DPF compatibility alias imports and add-on ID aliases are gone or isolated with explicit proof.
- Package manager tests reject invalid current metadata instead of accepting legacy fallbacks.

## Handoff Notes

- `P12` can assume DPF descriptors and add-on IDs are canonical when cleaning viewer transport.
