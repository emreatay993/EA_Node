# GRAPH_SURFACE_INPUT P03: Interaction Bridge

## Objective
- Route inline property commits and path-browse actions through explicit `nodeId` bridge APIs so embedded controls do not depend on selected-node state and can safely claim focus before editing.

## Preconditions
- `P02` is marked `PASS` in [GRAPH_SURFACE_INPUT_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_STATUS.md).
- No later `GRAPH_SURFACE_INPUT` packet is in progress.

## Target Subsystems
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_graph_surface_input_contract.py`
- focused shell or bridge regressions for node-specific inline editing

## Required Behavior
- Make `graph_scene_bridge.py::set_node_property(node_id, key, value)` QML-invokable.
- Add `window.py::browse_node_property_path(node_id, key, current_path)` for graph-surface inline path editors while preserving `browse_selected_node_property_path()` for the inspector.
- Add a host/surface control-start signal or equivalent routing path so GraphCanvas can:
  - select/focus the node
  - close pending menus/connection state
  - avoid starting drag/open/context behavior
- Update inline commit routing in `GraphCanvas.qml` to use explicit `nodeId` instead of selected-node-only APIs.
- Keep current inspector routing and selected-node property behavior unchanged outside the new graph-surface path.

## Non-Goals
- No shared graph-surface control components yet.
- No new inline editor modes yet.
- No hover-proxy removal yet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_surface_input_contract -v`

## Acceptance Criteria
- Graph-surface inline commits work by explicit `nodeId`.
- Graph-surface path browsing has a dedicated API and does not depend on the selected-node inspector code path.
- Selecting a control region prepares the node for editing without starting host drag/open/context behavior.

## Handoff Notes
- `P04` uses these bridge hooks to build reusable graph-surface controls.
