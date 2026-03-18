# ARCH_SECOND_PASS P03: GraphCanvas Interaction State

## Objective
- Extract stateful interaction policy from `GraphCanvas.qml` so the root remains a stable integration surface while wire-drag, drop-preview, context-menu, and related interaction state live behind focused helpers/components.

## Preconditions
- `P00` through `P02` are marked `PASS` in [ARCH_SECOND_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_second_pass/ARCH_SECOND_PASS_STATUS.md).
- No later `ARCH_SECOND_PASS` packet is in progress.

## Execution Dependencies
- `P02`

## Target Subsystems
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasLogic.js`
- `ea_node_editor/ui_qml/components/graph_canvas/*`
- packet-owned canvas boundary tests

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/**`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `tests/test_main_window_shell.py`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_workspace_library_controller_unit.py`

## Required Behavior
- Move packet-owned wire-drag, drop-target, drop-preview, context-menu, and interaction-idle state/policy out of the `GraphCanvas.qml` root into focused helpers/components or a clearly bounded local state layer.
- Keep the `GraphCanvas.qml` root contract stable for shell/drop workflows and current tests.
- Preserve current canvas interaction behavior, including quick insert, drop preview, minimap toggles, and bridge-driven selection/drag flows.
- Avoid widening raw bridge fallback usage while extracting the local interaction state.

## Non-Goals
- No `GraphNodeHost.qml` decomposition yet; `P04` owns that.
- No metrics unification or heavy-pane decomposition yet; `P05` owns that.
- No graph-scene core refactor yet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell tests.test_passive_graph_surface_host tests.test_workspace_library_controller_unit -v`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell.MainWindowShellGraphCanvasHostTests -v`

## Expected Artifacts
- `docs/specs/work_packets/arch_second_pass/P03_graph_canvas_interaction_state_WRAPUP.md`

## Acceptance Criteria
- `GraphCanvas.qml` delegates materially more interaction state/policy than the current baseline while preserving its root contract.
- Current canvas/shell regression coverage passes without behavior regressions.
- Packet-owned interaction policy is easier to reason about than the previous in-root state cluster.

## Handoff Notes
- `P04` can assume the `GraphCanvas.qml` root is a thinner interaction host after this packet.
- Keep any new helper names local to the canvas layer; do not leak them into shell contracts.
