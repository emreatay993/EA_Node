# ARCH_SIXTH_PASS P04: Canvas Contract Completion

## Objective
- Finish the bridge-first canvas migration by removing the broad `GraphCanvasBridge` compatibility surface and simplifying `GraphCanvas.qml` onto explicit state and command bridges.

## Preconditions
- `P00` through `P03` are marked `PASS` in [ARCH_SIXTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_sixth_pass/ARCH_SIXTH_PASS_STATUS.md).
- No later `ARCH_SIXTH_PASS` packet is in progress.

## Execution Dependencies
- `P03`

## Target Subsystems
- shell QML context bootstrap
- graph canvas bridge exports
- `GraphCanvas.qml` bridge contract

## Conservative Write Scope
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml`
- `tests/test_main_window_shell.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_graph_surface_input_controls.py`
- `tests/test_graph_surface_input_inline.py`
- `tests/test_passive_graph_surface_host.py`
- `docs/specs/work_packets/arch_sixth_pass/P04_canvas_contract_completion_WRAPUP.md`

## Required Behavior
- Remove the broad packet-owned `GraphCanvasBridge` compatibility adapter when the state and command bridge pair can carry the same behavior.
- Simplify `GraphCanvas.qml` to consume explicit state and command bridge ownership instead of layered fallback bridge references.
- Update packet-owned tests and QML context bootstrap expectations to reflect the completed bridge-first contract.
- Preserve current canvas behavior, graph-surface flows, and shell-to-canvas integration methods exactly.

## Non-Goals
- No shell presenter cleanup in this packet.
- No graph transform or mutation-service redesign in this packet.
- No runtime execution or plugin boundary changes in this packet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_window_shell.py tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_controls.py tests/test_graph_surface_input_inline.py tests/test_passive_graph_surface_host.py -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_contract.py -q`

## Expected Artifacts
- `docs/specs/work_packets/arch_sixth_pass/P04_canvas_contract_completion_WRAPUP.md`

## Acceptance Criteria
- Packet-owned QML no longer depends on the broad `GraphCanvasBridge` compatibility adapter.
- The shell context exports and tests describe a state-and-command bridge pair rather than a merged canvas bridge surface.
- Canvas and graph-surface regression tests pass with no behavior changes.

## Handoff Notes
- `P05` owns graph transaction cleanup after the QML bridge contract is narrowed.
- Preserve the public shell-to-canvas behavior while shrinking the internal bridge topology.
