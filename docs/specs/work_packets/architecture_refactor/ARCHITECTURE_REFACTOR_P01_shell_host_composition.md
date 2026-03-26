# ARCHITECTURE_REFACTOR P01: Shell Host Composition

## Objective
- Reduce `ShellWindow` to a narrower Qt host surface and make shell composition/bootstrap authoritative in one place so host attachment, bridge creation, and compatibility exports stop living in duplicate construction paths.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_REFACTOR` packet is in progress.

## Execution Dependencies
- `P00`

## Target Subsystems
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `tests/test_main_bootstrap.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/shell_runtime_contracts.py`
- `tests/main_window_shell/bridge_contracts.py`

## Conservative Write Scope
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui/shell/`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `tests/test_main_bootstrap.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/shell_runtime_contracts.py`
- `tests/main_window_shell/bridge_contracts.py`
- `docs/specs/work_packets/architecture_refactor/P01_shell_host_composition_WRAPUP.md`

## Required Behavior
- Make shell composition produce dependencies before the host is mutated, or otherwise expose one explicit attach point instead of multiple implicit build-time mutations.
- Remove duplicate bridge/context factory responsibility between `composition.py` and `shell_context_bootstrap.py`; one module must become the authority even if compatibility exports remain active for now.
- Move broad non-lifecycle behavior out of `ShellWindow` where practical without breaking menu wiring, dialog entry points, viewer bridge availability, or current shell startup behavior.
- Preserve current compatibility context names in this packet; retirement belongs to `P11`.
- Update inherited bootstrap/runtime-contract tests when composition-side seam names or attachment timing change.

## Non-Goals
- No controller decomposition yet.
- No bridge compatibility retirement yet.
- No runtime/protocol changes.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_bootstrap.py tests/test_main_window_shell.py tests/main_window_shell/shell_runtime_contracts.py tests/main_window_shell/bridge_contracts.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_bootstrap.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/architecture_refactor/P01_shell_host_composition_WRAPUP.md`

## Acceptance Criteria
- Composition/bootstrap has one clear authority for dependency construction and host attachment.
- `ShellWindow` remains the Qt host but no longer acts as the default home for composition-side indirection.
- The packet-owned shell/bootstrap regression command passes.

## Handoff Notes
- `P11` may retire remaining compatibility names, but it should inherit a single authoritative composition/bootstrap path from this packet.
