# ARCHITECTURE_REFACTOR P11: Shell QML Bridge Retirement

## Objective
- Finish the shell/QML bridge migration by moving in-repo consumers to the bridge-first contract, making shell-context export authority singular, and retiring compatibility context names or fallback props only after all tracked consumers are updated.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_REFACTOR` packet is in progress.

## Execution Dependencies
- `P10`

## Target Subsystems
- `ea_node_editor/ui/perf/performance_harness.py`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml`
- `ea_node_editor/ui_qml/components/shell/ShellStatusStrip.qml`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_track_h_perf_harness.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_flow_edge_labels.py`
- `tests/test_main_window_shell.py`
- `tests/test_main_bootstrap.py`
- `tests/main_window_shell/shell_runtime_contracts.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`

## Conservative Write Scope
- `ea_node_editor/ui/perf/performance_harness.py`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml`
- `ea_node_editor/ui_qml/components/shell/ShellStatusStrip.qml`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `ea_node_editor/ui/shell/composition.py`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_track_h_perf_harness.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_flow_edge_labels.py`
- `tests/test_main_window_shell.py`
- `tests/test_main_bootstrap.py`
- `tests/main_window_shell/shell_runtime_contracts.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `docs/specs/work_packets/architecture_refactor/P11_shell_qml_bridge_retirement_WRAPUP.md`

## Required Behavior
- Move tracked in-repo consumers, including the performance harness, to the bridge-first graph-canvas contract before compatibility removals happen.
- Make `shell_context_bootstrap.py` the single authority for exported QML context objects and compatibility aliases.
- Remove legacy `GraphCanvas.qml` fallback property paths and compatibility context names only after all tracked in-repo consumers are migrated in the same packet.
- Preserve shell startup, status-strip behavior, workspace-center behavior, and current graph interaction semantics while retiring compatibility baggage.

## Non-Goals
- No scene/history decomposition yet.
- No `GraphNodeHost` or geometry-policy split yet.
- No release/docs cleanup yet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_track_h_perf_harness.py tests/graph_track_b/qml_preference_bindings.py tests/test_graph_surface_input_contract.py tests/test_flow_edge_labels.py tests/test_main_window_shell.py tests/test_main_bootstrap.py tests/main_window_shell/shell_runtime_contracts.py tests/main_window_shell/bridge_qml_boundaries.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_track_h_perf_harness.py tests/test_main_bootstrap.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/architecture_refactor/P11_shell_qml_bridge_retirement_WRAPUP.md`

## Acceptance Criteria
- Bridge-first graph-canvas and shell-context contracts are authoritative and in-repo compatibility consumers are migrated.
- Compatibility aliases or fallback props retired by this packet are not left behind in known tracked consumers.
- The packet-owned verification command passes.

## Handoff Notes
- `P12` should assume bridge-first contracts are stable and focus on scene/host/geometry/theme hotspot decomposition, not on another round of compatibility export cleanup.
