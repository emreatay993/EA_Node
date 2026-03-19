# ARCH_FOURTH_PASS P05: Shell Presenter Boundary

## Objective
- Shrink `ShellWindow` by moving packet-owned QML-facing state and command ownership into focused presenters/models while keeping the shell host as composition root and native dialog host.

## Preconditions
- `P04` is marked `PASS` in [ARCH_FOURTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_STATUS.md).
- `P03` remains `PASS`.

## Execution Dependencies
- `P04`

## Target Subsystems
- `ea_node_editor/ui/shell/window.py`
- shell presenters/models under `ea_node_editor/ui/shell/`
- `ea_node_editor/ui_qml/shell_library_bridge.py`
- `ea_node_editor/ui_qml/shell_workspace_bridge.py`
- `ea_node_editor/ui_qml/shell_inspector_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`

## Conservative Write Scope
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/*.py`
- `ea_node_editor/ui_qml/shell_library_bridge.py`
- `ea_node_editor/ui_qml/shell_workspace_bridge.py`
- `ea_node_editor/ui_qml/shell_inspector_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `tests/test_main_bootstrap.py`
- `tests/test_main_window_shell.py`
- `tests/test_shell_run_controller.py`
- `tests/test_shell_project_session_controller.py`
- `docs/specs/work_packets/arch_fourth_pass/P05_shell_presenter_boundary_WRAPUP.md`

## Required Behavior
- Keep `ShellWindow` as composition root and native dialog host, but move packet-owned state/command ownership into focused presenters or state models.
- Reduce direct bridge dependence on lambdas over `shell_window` for packet-owned flows.
- Preserve public `ShellWindow`, bridge, and QML-facing slot/property/signal names relied on by tests and non-packet-owned consumers.
- Keep current shell startup, menu/action, run, workspace, and inspector workflows stable.

## Non-Goals
- No packet-owned removal of raw compatibility context properties yet; `P06` owns that.
- No verification/docs manifest consolidation yet; `P07` owns that.
- No intentional workflow changes.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_bootstrap tests.test_main_window_shell tests.test_shell_run_controller tests.test_shell_project_session_controller -v`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_bootstrap -v`

## Expected Artifacts
- `docs/specs/work_packets/arch_fourth_pass/P05_shell_presenter_boundary_WRAPUP.md`

## Acceptance Criteria
- Packet-owned QML-facing shell state/commands have focused ownership outside `ShellWindow`.
- Public shell/QML contracts remain stable for existing tests.
- Packet verification passes through the project venv.

## Handoff Notes
- `P06` will clean up packet-owned compatibility usage in QML roots; keep presenter contracts explicit so that migration can bind to them cleanly.
- Avoid reopening worker/runtime internals in this packet even if shell presenters expose run-state data.
