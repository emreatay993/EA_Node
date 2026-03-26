# ARCHITECTURE_REFACTOR P10: DPF Node Viewer Split

## Objective
- Separate DPF node-definition, viewer-adapter, and catalog concerns so node-layer DPF behavior stops being concentrated in two oversized built-in modules, while finishing descriptor-first package-discovery cleanup around the packet-owned DPF and plugin seams.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_REFACTOR` packet is in progress.

## Execution Dependencies
- `P09`

## Target Subsystems
- `ea_node_editor/nodes/builtins/ansys_dpf.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_common.py`
- `ea_node_editor/nodes/package_manager.py`
- `ea_node_editor/nodes/plugin_loader.py`
- `ea_node_editor/nodes/builtins/`
- `tests/test_dpf_node_catalog.py`
- `tests/test_dpf_compute_nodes.py`
- `tests/test_dpf_viewer_node.py`
- `tests/test_execution_viewer_protocol.py`
- `tests/test_package_manager.py`
- `tests/test_plugin_loader.py`
- `tests/test_node_package_io_ops.py`

## Conservative Write Scope
- `ea_node_editor/nodes/builtins/ansys_dpf.py`
- `ea_node_editor/nodes/builtins/ansys_dpf_common.py`
- `ea_node_editor/nodes/package_manager.py`
- `ea_node_editor/nodes/plugin_loader.py`
- `ea_node_editor/nodes/builtins/`
- `tests/test_dpf_node_catalog.py`
- `tests/test_dpf_compute_nodes.py`
- `tests/test_dpf_viewer_node.py`
- `tests/test_execution_viewer_protocol.py`
- `tests/test_package_manager.py`
- `tests/test_plugin_loader.py`
- `tests/test_node_package_io_ops.py`
- `docs/specs/work_packets/architecture_refactor/P10_dpf_node_viewer_split_WRAPUP.md`

## Required Behavior
- Split DPF node-layer concerns into clearer catalog, viewer-adapter, and shared-node helper boundaries.
- Move packet-owned DPF viewer orchestration behind node-layer adapters or runtime-facing helpers so DPF built-in modules no longer import execution protocol command/event types directly unless one explicit thin allowance module owns that edge.
- Finish descriptor-first built-in registration and expose a public package-discovery surface so `package_manager` and packet-owned shell package IO flows stop importing private loader helpers.
- Keep published DPF node type IDs, output-mode semantics, and viewer-session behavior stable.
- Preserve descriptor-first registration or package-manager behavior when DPF internals move.
- Update inherited DPF node, viewer-protocol, and package/plugin regression anchors in place when packet-owned seams move.

## Non-Goals
- No further execution-side DPF runtime refactor beyond `P09`.
- No shell/QML viewer surface redesign.
- No packaging/script cleanup yet.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_dpf_node_catalog.py tests/test_dpf_compute_nodes.py tests/test_dpf_viewer_node.py tests/test_execution_viewer_protocol.py --ignore=venv -q`
2. `./venv/Scripts/python.exe -m pytest tests/test_package_manager.py tests/test_plugin_loader.py tests/test_node_package_io_ops.py --ignore=venv -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_dpf_viewer_node.py tests/test_package_manager.py tests/test_plugin_loader.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/architecture_refactor/P10_dpf_node_viewer_split_WRAPUP.md`

## Acceptance Criteria
- DPF node-layer concerns are split into smaller modules without changing shipped type IDs or viewer behavior.
- Descriptor-first registration and public package-discovery seams remain stable and test-covered.
- The packet-owned verification command passes.

## Handoff Notes
- `P11` can assume the DPF viewer and execution-side bridges are stable enough to finish shell/QML bridge retirement without also refactoring DPF node internals.
