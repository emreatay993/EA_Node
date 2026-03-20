# ARCH_SIXTH_PASS P03: Shell Contract Hardening

## Objective
- Replace soft shell bridge and omnibus controller fallback dispatch with explicit shell-facing contracts so new packet-owned shell behavior stops routing through one compatibility-heavy hub.

## Preconditions
- `P00` through `P02` are marked `PASS` in [ARCH_SIXTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_STATUS.md).
- No later `ARCH_SIXTH_PASS` packet is in progress.

## Execution Dependencies
- `P02`

## Target Subsystems
- shell bridge facades
- workspace library controller surface
- shell-facing protocol ownership

## Conservative Write Scope
- `ea_node_editor/ui_qml/shell_library_bridge.py`
- `ea_node_editor/ui_qml/shell_workspace_bridge.py`
- `ea_node_editor/ui_qml/shell_inspector_bridge.py`
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `ea_node_editor/ui/shell/controllers/*.py`
- `tests/test_main_window_shell.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/test_window_library_inspector.py`
- `docs/specs/work_packets/arch_sixth_pass/P03_shell_contract_hardening_WRAPUP.md`

## Required Behavior
- Replace packet-owned `getattr`, `_invoke`, or other soft bridge dispatch with explicit protocols or focused facade objects.
- Reduce the broad pass-through surface of `WorkspaceLibraryController` for packet-owned flows.
- Preserve current QML contracts while moving packet-owned call sites onto clearer shell bridge and controller ownership.
- Keep bridge breakage detectable by focused tests instead of relying on wide runtime fallback behavior.

## Non-Goals
- No `GraphCanvas.qml` bridge removal in this packet.
- No graph transaction or runtime execution boundary work in this packet.
- No documentation closeout in this packet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_workspace_library_controller_unit.py tests/test_window_library_inspector.py tests/test_main_window_shell.py -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_workspace_library_controller_unit.py -q`

## Expected Artifacts
- `docs/specs/work_packets/arch_sixth_pass/P03_shell_contract_hardening_WRAPUP.md`

## Acceptance Criteria
- Packet-owned shell bridges use explicit, reviewable contracts instead of broad fallback dispatch.
- Packet-owned controller flows no longer depend on one compatibility-heavy omnibus controller surface.
- Focused shell contract tests pass with no behavior changes.

## Handoff Notes
- `P04` owns the canvas contract completion after the shell-side bridge surfaces are narrower.
- Keep compatibility-preserving adapters only where packet-owned call sites have not yet migrated.
