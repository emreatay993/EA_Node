# PLUGIN_PACKAGE_CONTRACT P02: Package Import Layout

## Objective
- Make `.eanp` import/install, listing, and uninstall flows conform to the loader contract from `P01`, and harden archive validation so imported packages are safe and discoverable by construction.

## Preconditions
- `P00` and `P01` are marked `PASS` in [PLUGIN_PACKAGE_CONTRACT_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/plugin_package_contract/PLUGIN_PACKAGE_CONTRACT_STATUS.md).
- No later `PLUGIN_PACKAGE_CONTRACT` packet is in progress.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ea_node_editor/nodes/package_manager.py`
- limited packet-owned helpers under `ea_node_editor/nodes/` if needed
- `tests/test_package_manager.py`
- limited `tests/test_plugin_loader.py` updates if the final loader contract needs aligned fixtures

## Conservative Write Scope
- `ea_node_editor/nodes/package_manager.py`
- `ea_node_editor/nodes/package*.py`
- `tests/test_package_manager.py`
- `tests/test_plugin_loader.py`
- `docs/specs/work_packets/plugin_package_contract/P02_package_import_layout_WRAPUP.md`

## Required Behavior
- Import `.eanp` archives into the exact package-directory shape established by `P01`.
- Validate package archive contents before install, including manifest presence, allowed file set, and path-safety rules for extracted members.
- Replace an existing installed package atomically enough that the plugins root never ends the operation in a partially merged shape.
- Keep `list_installed_packages()` and `uninstall_package()` aligned with the same installed-package shape.
- Preserve backward compatibility for package metadata fields unless a packet-owned addition is required and backward compatible.

## Non-Goals
- No shell/menu/message changes.
- No package export UX changes yet.
- No registry/spec surface changes.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest -n auto tests/test_package_manager.py tests/test_plugin_loader.py -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest -n auto tests/test_package_manager.py -q`

## Expected Artifacts
- `docs/specs/work_packets/plugin_package_contract/P02_package_import_layout_WRAPUP.md`

## Acceptance Criteria
- Focused tests prove that importing a valid `.eanp` package yields an installed directory that `P01` can discover.
- Focused tests prove that malformed or unsafe package archives are rejected.
- Focused tests prove that list/uninstall flows reflect the same installed-package contract.

## Handoff Notes
- `P03` must make export produce archives that satisfy this import contract without relying on shell-layer workarounds.
- Record any backward-compatibility constraints for legacy package layouts as residual risk if they cannot be fully preserved inside this packet.
