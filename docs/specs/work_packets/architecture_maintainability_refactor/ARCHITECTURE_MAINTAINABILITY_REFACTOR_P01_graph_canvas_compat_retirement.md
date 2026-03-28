# ARCHITECTURE_MAINTAINABILITY_REFACTOR P01: Graph Canvas Compat Retirement

## Objective
- Remove `graphCanvasBridge` as a compatibility wrapper and delete its packet-owned QML and host aliases in the same packet that migrates all in-repo callers to the focused graph-canvas state and command bridges.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_MAINTAINABILITY_REFACTOR` packet is in progress.

## Execution Dependencies
- `P00`

## Target Subsystems
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui/perf/performance_harness.py`
- `tests/test_main_bootstrap.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/bridge_contracts.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_track_h_perf_harness.py`
- `tests/graph_track_b/qml_preference_bindings.py`

## Conservative Write Scope
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui/perf/performance_harness.py`
- `tests/test_main_bootstrap.py`
- `tests/test_main_window_shell.py`
- `tests/main_window_shell/bridge_contracts.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_track_h_perf_harness.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `docs/specs/work_packets/architecture_maintainability_refactor/P01_graph_canvas_compat_retirement_WRAPUP.md`

## Required Behavior
- Migrate every packet-owned in-repo caller away from `graphCanvasBridge` and onto `graphCanvasStateBridge` plus `graphCanvasCommandBridge`.
- Remove `graphCanvasBridge` from QML context export authority and delete packet-owned host or QML aliases that only preserved the compatibility bridge.
- Delete the `graph_canvas_bridge.py` compatibility wrapper entirely unless one documented external caller still provably requires it; if one remains, narrow that requirement to an explicit edge adapter and document it in the wrap-up.
- Update the inherited bootstrap and bridge-contract regression anchors in place so they assert the bridge-first contract rather than the retired compatibility contract.

## Non-Goals
- No presenter-or-host fallback cleanup yet; that belongs to `P02`.
- No broader `ShellWindow` API retirement yet; that belongs to `P03`.
- No scene/history or geometry decomposition yet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_bootstrap.py tests/test_main_window_shell.py tests/main_window_shell/bridge_contracts.py tests/main_window_shell/bridge_qml_boundaries.py tests/test_graph_surface_input_contract.py tests/test_track_h_perf_harness.py tests/graph_track_b/qml_preference_bindings.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_bootstrap.py tests/main_window_shell/bridge_contracts.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/architecture_maintainability_refactor/P01_graph_canvas_compat_retirement_WRAPUP.md`

## Acceptance Criteria
- `graphCanvasBridge` is no longer an active packet-owned compatibility surface.
- In-repo graph-canvas callers use the focused state and command bridges directly.
- The inherited bridge/bootstrap regression anchors pass without retaining the old compatibility wrapper.

## Handoff Notes
- `P02` inherits the bridge-first contract from this packet and should harden source ownership rather than revisiting graph-canvas compatibility retirement.
