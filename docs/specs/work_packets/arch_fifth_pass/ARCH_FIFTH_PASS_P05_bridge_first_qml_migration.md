# ARCH_FIFTH_PASS P05: Bridge-First QML Migration

## Objective
- Migrate packet-owned QML surfaces to the focused bridge contracts, remove raw compatibility globals and fallback logic, and preserve exact shell/canvas behavior and performance.

## Preconditions
- `P04` is marked `PASS` in [ARCH_FIFTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_STATUS.md).
- No later `ARCH_FIFTH_PASS` packet is in progress.

## Execution Dependencies
- `P04`

## Target Subsystems
- `MainShell.qml` and `GraphCanvas.qml` bridge binding
- shell/canvas compatibility-global removal
- graph-surface interaction regression coverage
- canvas performance regression coverage

## Conservative Write Scope
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/shell/WorkspaceCenterPane.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasMinimapOverlay.qml`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `tests/test_main_window_shell.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_graph_surface_input_controls.py`
- `tests/test_graph_surface_input_inline.py`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_track_h_perf_harness.py`
- `docs/specs/work_packets/arch_fifth_pass/P05_bridge_first_qml_migration_WRAPUP.md`

## Required Behavior
- Migrate packet-owned QML references from `mainWindow`, `sceneBridge`, and `viewBridge` compatibility globals to the focused bridge context properties introduced in `P04`.
- Remove the raw compatibility globals from `shell_context_bootstrap.py` once packet-owned QML no longer depends on them.
- Remove fallback logic in `MainShell.qml` and `GraphCanvas.qml` that prefers raw compatibility globals over focused bridges.
- Preserve exact object names, public methods, layout, interaction timing, pointer routing, and minimap behavior.
- Preserve canvas/render-path performance by avoiding new per-frame bridge churn or extra scene rebuild paths.

## Non-Goals
- No shell-controller splitting in this packet; `P03` already owns that.
- No mutation-boundary or persistence/runtime changes in this packet.
- No user-visible shell/canvas redesign.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_window_shell.py tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_controls.py tests/test_graph_surface_input_inline.py tests/test_passive_graph_surface_host.py tests/test_track_h_perf_harness.py -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_main_window_shell.py -q -k "GraphCanvasBridgeTests or MainWindowShellContextBootstrapTests"`

## Expected Artifacts
- `docs/specs/work_packets/arch_fifth_pass/P05_bridge_first_qml_migration_WRAPUP.md`

## Acceptance Criteria
- Packet-owned QML no longer depends on raw `mainWindow`, `sceneBridge`, or `viewBridge` context properties.
- Focused bridge contracts fully cover the migrated QML call sites.
- Shell/canvas behavior and performance remain unchanged, and packet verification passes under offscreen Qt.

## Handoff Notes
- `P06` starts the graph mutation-boundary work; do not blend that logic into this QML packet.
- If any compatibility shim must remain temporarily, document the exact remaining consumer and justify why it is outside the packet write scope.
