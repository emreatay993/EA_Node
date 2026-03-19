# PLUGIN_PACKAGE_CONTRACT P04: Shell Package Workflows

## Objective
- Align the File-menu import/export node-package workflows with the repaired loader/package contract so success/failure UX is truthful and library refresh behavior matches what the lower layers now guarantee.

## Preconditions
- `P00` through `P03` are marked `PASS` in [PLUGIN_PACKAGE_CONTRACT_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/plugin_package_contract/PLUGIN_PACKAGE_CONTRACT_STATUS.md).
- No later `PLUGIN_PACKAGE_CONTRACT` packet is in progress.

## Execution Dependencies
- `P03`

## Target Subsystems
- `ea_node_editor/ui/shell/controllers/workspace_io_ops.py`
- limited `ea_node_editor/ui/shell/controllers/workspace_library_controller.py` integration if needed
- limited `ea_node_editor/ui/shell/window.py` / `ea_node_editor/ui/shell/window_actions.py` integration only if packet-owned shell surfaces need a minimal helper
- `tests/test_node_package_io_ops.py`
- limited `tests/test_workspace_library_controller_unit.py` updates if existing controller-unit seams are the smallest credible proof

## Conservative Write Scope
- `ea_node_editor/ui/shell/controllers/workspace_io_ops.py`
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_actions.py`
- `tests/test_node_package_io_ops.py`
- `tests/test_workspace_library_controller_unit.py`
- `docs/specs/work_packets/plugin_package_contract/P04_shell_package_workflows_WRAPUP.md`

## Required Behavior
- Import Node Package shall report success only when the imported package is installed and the repaired discovery path yields concrete loaded node types or an explicitly approved no-node outcome.
- Export Node Package shall call the explicit export contract from `P03` and must not emit an empty or placeholder archive under a success path.
- Keep `.eawf` custom-workflow actions separate from `.eanp` node-package actions.
- Preserve existing File-menu wiring and controller entry points unless a minimal packet-owned helper is required.
- Add focused shell/controller tests for import and export outcomes rather than relying on a broad shell suite.

## Non-Goals
- No QML changes.
- No plugin-loader/package-manager contract changes except minimal integration glue.
- No broad `tests/test_main_window_shell.py` regression reruns unless packet-local unit proof proves insufficient.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest -n auto tests/test_node_package_io_ops.py tests/test_workspace_library_controller_unit.py -q`

## Review Gate
- `./venv/Scripts/python.exe -m pytest -n auto tests/test_node_package_io_ops.py -q`

## Expected Artifacts
- `docs/specs/work_packets/plugin_package_contract/P04_shell_package_workflows_WRAPUP.md`

## Acceptance Criteria
- Focused tests prove that Import Node Package only claims package availability when the repaired package contract succeeds.
- Focused tests prove that Export Node Package no longer routes through an empty/ambiguous success path.
- Existing File-menu package actions remain separate from custom-workflow `.eawf` actions.

## Handoff Notes
- `P05` must update README and traceability docs to describe the exact shell behavior implemented here, not the pre-refactor overclaim.
- If shell export remains intentionally narrower than the existing README wording, record that supported scope explicitly in the wrap-up.
