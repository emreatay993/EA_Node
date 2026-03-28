# ARCHITECTURE_MAINTAINABILITY_REFACTOR P08: Node SDK Surface Cleanup

## Objective
- Split the high-fan-in node type surface into focused internal modules, update in-repo imports to those modules, and reduce `ea_node_editor.nodes.types` to the curated documented SDK surface only.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_MAINTAINABILITY_REFACTOR` packet is in progress.

## Execution Dependencies
- `P07`

## Target Subsystems
- `ea_node_editor/nodes/types.py`
- `ea_node_editor/nodes/registry.py`
- `ea_node_editor/nodes/plugin_loader.py`
- `ea_node_editor/nodes/package_manager.py`
- `ea_node_editor/nodes/`
- `tests/test_plugin_loader.py`
- `tests/test_package_manager.py`
- `tests/test_registry_validation.py`
- `tests/test_execution_artifact_refs.py`
- `tests/test_execution_handle_refs.py`
- `tests/test_passive_node_contracts.py`

## Conservative Write Scope
- `ea_node_editor/nodes/types.py`
- `ea_node_editor/nodes/registry.py`
- `ea_node_editor/nodes/plugin_loader.py`
- `ea_node_editor/nodes/package_manager.py`
- `ea_node_editor/nodes/`
- `tests/test_plugin_loader.py`
- `tests/test_package_manager.py`
- `tests/test_registry_validation.py`
- `tests/test_execution_artifact_refs.py`
- `tests/test_execution_handle_refs.py`
- `tests/test_passive_node_contracts.py`
- `docs/specs/work_packets/architecture_maintainability_refactor/P08_node_sdk_surface_cleanup_WRAPUP.md`

## Required Behavior
- Split packet-owned contents of `ea_node_editor.nodes.types` into focused modules for node specs, execution context, runtime references, and plugin descriptors or equivalent focused surfaces.
- Update internal code to import those focused modules directly rather than continuing to treat `nodes.types` as a catch-all.
- Keep `ea_node_editor.nodes.types` only as the curated documented SDK import surface still needed by the README and external node-authoring contract.
- Update inherited registry, loader, handle/runtime-ref, and passive-node regression anchors in place when type import locations move.

## Non-Goals
- No runtime protocol compatibility removal yet; that belongs to `P09`.
- No new node SDK features.
- No doc refresh beyond direct fallout from packet-owned module moves.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_plugin_loader.py tests/test_package_manager.py tests/test_registry_validation.py tests/test_execution_artifact_refs.py tests/test_execution_handle_refs.py tests/test_passive_node_contracts.py --ignore=venv -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_plugin_loader.py tests/test_registry_validation.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/architecture_maintainability_refactor/P08_node_sdk_surface_cleanup_WRAPUP.md`

## Acceptance Criteria
- Internal code no longer relies on `ea_node_editor.nodes.types` as a broad compatibility module.
- The curated documented SDK surface remains stable for the packet-owned external contract.
- The inherited loader/registry/runtime-ref regression anchors pass after the split.

## Handoff Notes
- `P09` should assume the node SDK internals are clearer and remove runtime protocol compatibility debt on top of those focused types.
