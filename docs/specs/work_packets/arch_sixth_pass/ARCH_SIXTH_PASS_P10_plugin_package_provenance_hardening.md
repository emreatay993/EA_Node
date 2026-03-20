# ARCH_SIXTH_PASS P10: Plugin Package Provenance Hardening

## Objective
- Make plugin and package provenance explicit so discovery, validation, and export no longer depend on registry internals, constructor probing, or import-time side effects more than necessary.

## Preconditions
- `P00` through `P09` are marked `PASS` in [ARCH_SIXTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_STATUS.md).
- No later `ARCH_SIXTH_PASS` packet is in progress.

## Execution Dependencies
- `P09`

## Target Subsystems
- plugin discovery and entry-point loading
- package import and export validation
- registry provenance metadata

## Conservative Write Scope
- `ea_node_editor/nodes/types.py`
- `ea_node_editor/nodes/registry.py`
- `ea_node_editor/nodes/plugin_loader.py`
- `ea_node_editor/nodes/package_manager.py`
- `ea_node_editor/ui/shell/controllers/workspace_io_ops.py`
- `tests/test_plugin_loader.py`
- `tests/test_package_manager.py`
- `tests/test_node_package_io_ops.py`
- `tests/test_registry_validation.py`
- `docs/specs/work_packets/arch_sixth_pass/P10_plugin_package_provenance_hardening_WRAPUP.md`

## Required Behavior
- Make descriptor metadata the authoritative packet-owned discovery surface for new plugin and package flows.
- Add explicit provenance information to the registry so packet-owned export flows stop reading private registry storage or inferring package ownership from `factory.__module__`.
- Reduce packet-owned import-time execution and constructor probing during staged validation when a narrower metadata contract can replace it safely.
- Modernize packet-owned entry-point loading to avoid the deprecated selectable-groups API shape where appropriate.

## Non-Goals
- No workspace lifecycle or runtime snapshot changes in this packet.
- No shell verification or docs closeout work in this packet.
- No breaking removal of legacy compatibility for packet-external plugins without a packet-owned compatibility path.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_plugin_loader.py tests/test_package_manager.py tests/test_node_package_io_ops.py tests/test_registry_validation.py -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest tests/test_plugin_loader.py tests/test_package_manager.py -q`

## Expected Artifacts
- `docs/specs/work_packets/arch_sixth_pass/P10_plugin_package_provenance_hardening_WRAPUP.md`

## Acceptance Criteria
- Packet-owned package export/import flows depend on explicit provenance metadata rather than registry internals.
- Plugin/package validation relies less on import-time side effects and legacy constructor probing.
- Plugin/package tests pass, and the packet removes the observed entry-point deprecation warning when packet-owned paths run.

## Handoff Notes
- `P11` owns shell verification lifecycle cleanup after plugin/package provenance is narrowed.
- Preserve legacy compatibility only where the packet still documents and tests the fallback.
