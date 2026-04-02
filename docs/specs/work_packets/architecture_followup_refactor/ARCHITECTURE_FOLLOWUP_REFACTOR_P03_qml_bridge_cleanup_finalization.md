# ARCHITECTURE_FOLLOWUP_REFACTOR P03: QML Bridge Cleanup Finalization

## Objective

- Finish the packet-owned shell-to-QML cleanup by retiring the remaining graph-canvas compatibility wrapper and making packet-owned QML consume only explicit focused bridge contracts.

## Preconditions

- `P02` is marked `PASS` in [ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md](./ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_FOLLOWUP_REFACTOR` packet is in progress.

## Execution Dependencies

- `P02`

## Target Subsystems

- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui/shell/composition.py`
- `tests/main_window_shell/bridge_contracts.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/test_main_window_shell.py`
- `tests/test_graph_surface_input_contract.py`

## Conservative Write Scope

- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_command_bridge.py`
- `ea_node_editor/ui_qml/shell_context_bootstrap.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui/shell/composition.py`
- `tests/main_window_shell/bridge_contracts.py`
- `tests/main_window_shell/bridge_qml_boundaries.py`
- `tests/test_main_window_shell.py`
- `tests/test_graph_surface_input_contract.py`
- `docs/specs/work_packets/architecture_followup_refactor/P03_qml_bridge_cleanup_finalization_WRAPUP.md`

## Required Behavior

- Retire `GraphCanvasBridge` from packet-owned context export and packet-owned QML contracts.
- Export only focused packet-owned state, command, and view bridge surfaces through shell QML bootstrap.
- Remove packet-owned `GraphCanvas.qml` compatibility aliasing that reconstructs bridge topology from wrapper objects instead of explicit bridge props.
- Update inherited bridge-contract, bridge-boundary, and graph-surface regression anchors in place.

## Non-Goals

- No graph authoring authority collapse yet; that belongs to `P06`.
- No viewer-session ownership cleanup yet; that belongs to `P07`.
- No new QML features or shell chrome changes beyond bridge cleanup.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_contracts.py tests/main_window_shell/bridge_qml_boundaries.py tests/test_graph_surface_input_contract.py tests/test_main_window_shell.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_contracts.py tests/main_window_shell/bridge_qml_boundaries.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/architecture_followup_refactor/P03_qml_bridge_cleanup_finalization_WRAPUP.md`

## Acceptance Criteria

- Packet-owned shell QML bootstrap no longer exports `GraphCanvasBridge`.
- Packet-owned QML consumes explicit focused bridge contracts instead of wrapper reconstruction.
- The inherited bridge and graph-surface regression anchors pass.

## Handoff Notes

- `P06` inherits the graph-surface regression anchors from this packet when graph authoring authority changes invalidate those assertions.
