# ARCH_FIFTH_PASS P10: Plugin Descriptor And Package Contract

## Objective
- Add descriptor-based plugin loading and semantic package validation while preserving legacy plugin loading behavior as a compatibility fallback.

## Preconditions
- `P09` is marked `PASS` in [ARCH_FIFTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_STATUS.md).
- No later `ARCH_FIFTH_PASS` packet is in progress.

## Execution Dependencies
- `P09`

## Target Subsystems
- plugin discovery and registration contract
- package import/export validation contract
- plugin/package regression coverage

## Conservative Write Scope
- `ea_node_editor/nodes/types.py`
- `ea_node_editor/nodes/registry.py`
- `ea_node_editor/nodes/plugin_loader.py`
- `ea_node_editor/nodes/package_manager.py`
- `tests/test_plugin_loader.py`
- `tests/test_package_manager.py`
- `tests/test_node_package_io_ops.py`
- `tests/test_registry_validation.py`
- `docs/specs/work_packets/arch_fifth_pass/P10_plugin_descriptor_package_contract_WRAPUP.md`

## Required Behavior
- Add a descriptor-based preferred plugin contract via module-level `PLUGIN_DESCRIPTORS`, where each descriptor carries a validated `NodeTypeSpec` plus the zero-arg factory to register, so discovery no longer needs to instantiate candidate classes just to probe them.
- Add direct registry support for registering a `(spec, factory)` descriptor pair without plugin instantiation during discovery.
- Keep legacy constructor/class scanning as a fallback when `PLUGIN_DESCRIPTORS` is absent.
- Change package import/export validation so manifests are checked semantically against a temporary registry load, not only for archive shape.
- Preserve existing user-visible plugin loading and package IO behavior for valid legacy packages/plugins.

## Non-Goals
- No UI changes for plugin/package management in this packet.
- No removal of legacy plugin discovery fallback in this packet.
- No persistence or runtime execution change in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_plugin_loader.py tests/test_package_manager.py tests/test_node_package_io_ops.py tests/test_registry_validation.py -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_plugin_loader.py tests/test_package_manager.py -q`

## Expected Artifacts
- `docs/specs/work_packets/arch_fifth_pass/P10_plugin_descriptor_package_contract_WRAPUP.md`

## Acceptance Criteria
- Descriptor-based plugin loading works without constructor probing when `PLUGIN_DESCRIPTORS` is present.
- Legacy plugin loading still works when descriptors are absent.
- Package validation rejects manifest/type mismatches before install/export publish.
- Packet verification passes in the project venv.

## Handoff Notes
- Keep the compatibility fallback explicit and well documented in the wrap-up so a later plan can decide whether to deprecate it.
- `P11` starts maintainability cleanup for the large regression surfaces that validate these packet-owned contracts.
