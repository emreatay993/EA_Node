# SHARED_GRAPH_TYPOGRAPHY_CONTROL P02: Shell Typography Projection

## Objective
- Project the normalized graph typography base size through workspace state, presenter snapshots, `ShellWindow`, and the graph-canvas bridge-owned Python property seam before any QML consumer adopts the value.

## Preconditions
- `P01` is marked `PASS` in [SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md](./SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md).
- No later `SHARED_GRAPH_TYPOGRAPHY_CONTROL` packet is in progress.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ea_node_editor/ui/shell/presenters/state.py`
- `ea_node_editor/ui/shell/presenters/workspace_presenter.py`
- `ea_node_editor/ui/shell/presenters/graph_canvas_presenter.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_state/context_properties.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `tests/main_window_shell/bridge_contracts_graph_canvas.py`
- `tests/test_main_window_shell.py`

## Conservative Write Scope
- `ea_node_editor/ui/shell/presenters/state.py`
- `ea_node_editor/ui/shell/presenters/workspace_presenter.py`
- `ea_node_editor/ui/shell/presenters/graph_canvas_presenter.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_state/context_properties.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `tests/main_window_shell/bridge_contracts_graph_canvas.py`
- `tests/test_main_window_shell.py`
- `docs/specs/work_packets/shared_graph_typography_control/SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md`
- `docs/specs/work_packets/shared_graph_typography_control/P02_shell_typography_projection_WRAPUP.md`

## Required Behavior
- Add the packet-owned typography base-size field to `ShellWorkspaceUiState` and seed it from the normalized graphics preferences snapshot.
- Extend the workspace-presenter graphics apply/snapshot path so the returned resolved snapshot includes `graphics.typography.graph_label_pixel_size`.
- Expose one stable Python-side graph-canvas bridge property named `graphics_graph_label_pixel_size`.
- Route that property through the existing `ShellWindow` and `GraphCanvasStateBridge` graphics-preference notification path instead of creating a second signal or revision channel.
- If the legacy composite graph-canvas bridge still mirrors graphics preferences anywhere in the active path, keep its typography property naming aligned with the packet-owned bridge property instead of inventing a second name.
- Add packet-owned regression tests whose names include `graph_typography_bridge` so the targeted verification commands below remain stable.

## Non-Goals
- No `GraphCanvasRootBindings.qml` change yet.
- No shared QML typography-role source yet.
- No geometry/text-width metric changes yet.
- No Graphics Settings dialog control yet.

## Verification Commands
1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_contracts_graph_canvas.py tests/test_main_window_shell.py -k graph_typography_bridge --ignore=venv -q`

## Review Gate
- `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_contracts_graph_canvas.py -k graph_typography_bridge --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/shared_graph_typography_control/P02_shell_typography_projection_WRAPUP.md`

## Acceptance Criteria
- The normalized typography base size is part of `ShellWorkspaceUiState` and the workspace-presenter graphics snapshot contract.
- `ShellWindow` and `GraphCanvasStateBridge` expose the stable Python-side `graphics_graph_label_pixel_size` property through the existing graphics-preference update path.
- The packet-owned `graph_typography_bridge` bridge regressions pass.

## Handoff Notes
- `P03` consumes the packet-owned `graphics_graph_label_pixel_size` property in QML as `graphLabelPixelSize` and defines the derived role contract from that base value.
- Any later packet that renames the Python-side property or changes how it propagates must inherit and update `tests/main_window_shell/bridge_contracts_graph_canvas.py` and `tests/test_main_window_shell.py`.
