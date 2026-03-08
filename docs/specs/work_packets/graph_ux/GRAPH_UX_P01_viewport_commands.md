# GRAPH_UX P01: Viewport Commands and Camera Framing

## Objective
- Add reusable viewport helpers and shell commands for framing and centering graph content.

## Preconditions
- `P00` is marked `PASS` in [GRAPH_UX_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_ux/GRAPH_UX_STATUS.md).
- No later Graph UX packet is in progress.

## Target Subsystems
- `ea_node_editor/ui_qml/viewport_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `tests/test_graph_track_b.py`
- `tests/test_main_window_shell.py`

## Required Behavior
- Add reusable viewport helpers for:
  - visible scene rect
  - current workspace scene bounds
  - selection bounds
  - `frame_all`
  - `frame_selection`
  - `center_on_node`
  - `center_on_selection`
- Use `80 px` viewport padding when framing content.
- Keep the existing zoom clamp unchanged at `[0.1, 3.0]`.
- Empty-graph or empty-selection commands must be safe no-ops.
- Add shell actions and shortcuts:
  - `A` -> frame all
  - `F` -> frame selection
  - `Shift+F` -> center on selection without recomputing a fit zoom
- Route all camera math through the shared helpers so later packets can reuse it.

## Non-Goals
- No minimap UI.
- No search palette.
- No history/undo behavior.

## Verification Commands
1. `venv\Scripts\python -m unittest tests.test_graph_track_b tests.test_main_window_shell -v`

## Acceptance Criteria
- Framing a single node centers it with padding and respects zoom limits.
- Framing multiple nodes fits their union bounds.
- `frame_selection` operates on the selected nodes only.
- Empty graph and empty selection commands do not raise and do not corrupt camera state.
- Shortcuts `A`, `F`, and `Shift+F` are wired and covered by tests.

## Handoff Notes
- `P02`, `P04`, and `P05` must reuse these helpers instead of duplicating viewport calculations.
- Keep helper names and behavior stable enough that later packets can call them directly.
