# PLUGIN_PACKAGE_CONTRACT P03: Package Export Contract

## Objective
- Repair the lower-level `.eanp` export contract so export APIs only produce packages that the `P01`/`P02` loader+import pipeline can actually round-trip, or fail explicitly when the caller cannot provide a valid exportable source set.

## Preconditions
- `P00` through `P02` are marked `PASS` in [PLUGIN_PACKAGE_CONTRACT_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/plugin_package_contract/PLUGIN_PACKAGE_CONTRACT_STATUS.md).
- No later `PLUGIN_PACKAGE_CONTRACT` packet is in progress.

## Execution Dependencies
- `P02`

## Target Subsystems
- `ea_node_editor/nodes/package_manager.py`
- packet-owned export/source-selection helpers under `ea_node_editor/nodes/` if needed
- `tests/test_package_manager.py`

## Conservative Write Scope
- `ea_node_editor/nodes/package_manager.py`
- `ea_node_editor/nodes/package*.py`
- `tests/test_package_manager.py`
- `docs/specs/work_packets/plugin_package_contract/P03_package_export_contract_WRAPUP.md`

## Required Behavior
- Define one lower-level export API that accepts explicit exportable source inputs and refuses empty or placeholder package definitions.
- Ensure exported `.eanp` archives use the same manifest/content rules that `P02` imports and `P01` discovers.
- Prevent the lower-level export path from claiming success when no actual plugin source files are being packaged.
- Keep `.eanp` extension, manifest filename, and package-manager ownership stable unless a backward-compatible metadata addition is required.
- Add focused round-trip proof showing that a package exported by this API can be re-imported and discovered under the repaired contract.

## Non-Goals
- No File-menu/dialog flow changes yet.
- No shell message or menu wiring changes yet.
- No registry/spec surface changes.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest -n auto tests/test_package_manager.py tests/test_plugin_loader.py -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest -n auto tests/test_package_manager.py -q`

## Expected Artifacts
- `docs/specs/work_packets/plugin_package_contract/P03_package_export_contract_WRAPUP.md`

## Acceptance Criteria
- Focused tests prove that the repaired export API cannot emit an empty or undiscoverable package under the success path.
- Focused tests prove that exported packages round-trip through import and loader discovery.
- The lower-level export contract is explicit enough for `P04` to wire into shell workflows without inference.

## Handoff Notes
- `P04` may only use the explicit export contract from this packet; do not leave a shell-only special case that bypasses it.
- If the repo cannot yet infer exportable source files for every registry entry, record the intentionally supported export scope explicitly instead of silently packaging the full registry.
