# PLUGIN_PACKAGE_CONTRACT P01: Loader Directory Contract

## Objective
- Define and implement the canonical on-disk discovery contract for plugin directories so raw single-file drop-ins and installed package directories both load predictably from the plugins root.

## Preconditions
- `P00` is marked `PASS` in [PLUGIN_PACKAGE_CONTRACT_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/plugin_package_contract/PLUGIN_PACKAGE_CONTRACT_STATUS.md).
- No later `PLUGIN_PACKAGE_CONTRACT` packet is in progress.

## Execution Dependencies
- `none`

## Target Subsystems
- `ea_node_editor/nodes/plugin_loader.py`
- `ea_node_editor/nodes/bootstrap.py`
- packet-owned plugin-loader helpers under `ea_node_editor/nodes/` if needed
- `tests/test_plugin_loader.py`
- limited `tests/test_main_bootstrap.py` coverage if bootstrap call shape changes

## Conservative Write Scope
- `ea_node_editor/nodes/plugin_loader.py`
- `ea_node_editor/nodes/bootstrap.py`
- `ea_node_editor/nodes/plugin*.py`
- `tests/test_plugin_loader.py`
- `tests/test_main_bootstrap.py`
- `docs/specs/work_packets/plugin_package_contract/P01_loader_directory_contract_WRAPUP.md`

## Required Behavior
- Preserve discovery of raw single-file plugins from `plugins/*.py`.
- Add authoritative discovery support for installed package directories under the plugins root so the loader can find modules that `P02` will install.
- Preserve entry-point plugin loading via `ea_node_editor.plugins`.
- Keep plugin registration error handling tolerant: one bad plugin module must not block the rest of discovery.
- Keep `build_default_registry()` behavior stable apart from the widened discovery contract.

## Non-Goals
- No `.eanp` import/export layout changes yet.
- No shell/menu/message changes.
- No `NodeRegistry` or `NodeTypeSpec` surface changes.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest -n auto tests/test_plugin_loader.py tests/test_main_bootstrap.py -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest -n auto tests/test_plugin_loader.py -q`

## Expected Artifacts
- `docs/specs/work_packets/plugin_package_contract/P01_loader_directory_contract_WRAPUP.md`

## Acceptance Criteria
- Focused tests prove that raw single-file plugin drop-ins still load from the plugins root.
- Focused tests prove that a package directory installed beneath the plugins root is discoverable under the new contract.
- Entry-point loading remains intact and bootstrap coverage still passes through the project venv.

## Handoff Notes
- `P02` must install packages into exactly the loader contract established here; do not leave multiple competing directory shapes alive.
- Record the canonical package-directory expectations explicitly in the wrap-up so `P05` can document the same contract without inference.
