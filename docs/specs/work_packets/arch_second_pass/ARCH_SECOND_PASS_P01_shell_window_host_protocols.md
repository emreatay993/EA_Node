# ARCH_SECOND_PASS P01: ShellWindow Host Protocols

## Objective
- Reduce `ShellWindow` state-bag behavior and controller/private-field coupling by introducing explicit shell-owned state/services or host protocols for the packet-owned concerns that still mutate or read host internals directly.

## Preconditions
- `P00` is marked `PASS` in [ARCH_SECOND_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_second_pass/ARCH_SECOND_PASS_STATUS.md).
- No later `ARCH_SECOND_PASS` packet is in progress.

## Execution Dependencies
- none

## Target Subsystems
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/state.py`
- `ea_node_editor/ui/shell/window_search_scope_state.py`
- packet-owned controller/helper modules under `ea_node_editor/ui/shell/controllers/`
- packet-owned shell/controller regression tests

## Conservative Write Scope
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/state.py`
- `ea_node_editor/ui/shell/window_search_scope_state.py`
- `ea_node_editor/ui/shell/controllers/run_controller.py`
- `ea_node_editor/ui/shell/controllers/project_session_controller.py`
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `ea_node_editor/ui/shell/controllers/workspace_edit_ops.py`
- `tests/test_main_window_shell.py`
- `tests/test_shell_run_controller.py`
- `tests/test_shell_project_session_controller.py`
- `tests/test_workspace_library_controller_unit.py`

## Required Behavior
- Introduce explicit shell-owned state holder(s), service object(s), or narrow host protocol(s) for packet-owned concerns such as graph search, quick insert, graph hint, and runtime scope-camera coordination where they still live as loose `ShellWindow` fields or helper mutations.
- Reduce or remove packet-owned direct controller access to `ShellWindow` private attributes when a dedicated service/protocol can own that concern instead.
- Replace the current `window_search_scope_state.py` private-field mutation pattern with a clearer ownership seam, or delete it if superseded by dedicated objects.
- Keep existing public `ShellWindow` slots, properties, and emitted signals stable for current QML consumers and tests.
- Preserve current search, quick-insert, graph-hint, and camera behavior from the user’s perspective.

## Non-Goals
- No QML bridge contract changes yet; `P02` owns that.
- No `GraphCanvas.qml`, `GraphNodeHost.qml`, or `GraphSceneBridge` refactors yet.
- No persistence/schema/version changes.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell tests.test_shell_run_controller tests.test_shell_project_session_controller tests.test_workspace_library_controller_unit -v`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_shell_run_controller tests.test_shell_project_session_controller -v`

## Expected Artifacts
- `docs/specs/work_packets/arch_second_pass/P01_shell_window_host_protocols_WRAPUP.md`

## Acceptance Criteria
- Packet-owned controller code no longer depends on packet-owned `ShellWindow` private state where an explicit protocol/service can own that access.
- `window_search_scope_state.py` no longer exists merely as a file-size reduction shim over `ShellWindow` private fields.
- Current shell/controller regression coverage passes without QML contract changes.

## Handoff Notes
- `P02` converts the QML bridge side of these boundaries; do not mix reflective-bridge cleanup into this packet.
- Keep the public shell host surface stable even if the internal owner objects change.
