# SHELL_SCENE_BOUNDARY P06: GraphCanvas Boundary Bridge

## Objective
- Replace direct raw app-bridge dependency inside `GraphCanvas.qml` with dedicated canvas-boundary adapters while preserving the public `GraphCanvas` root contract used by the shell and tests.

## Preconditions
- `P03`, `P04`, and `P05` are marked `PASS` in [SHELL_SCENE_BOUNDARY_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/shell_scene_boundary/SHELL_SCENE_BOUNDARY_STATUS.md).
- No later `SHELL_SCENE_BOUNDARY` packet is in progress.

## Execution Dependencies
- `P03`
- `P04`
- `P05`

## Target Subsystems
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `tests/test_main_window_shell.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_passive_graph_surface_host.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `tests/test_main_window_shell.py`
- `tests/test_workspace_library_controller_unit.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_passive_graph_surface_host.py`

## Required Behavior
- Route GraphCanvas-owned preferences, viewport read/write state, node/edge query/mutation calls, quick-insert/drop/connect actions, scope-open helpers, and node-specific browse hooks through `graph_canvas_bridge.py` or equivalent dedicated adapters instead of direct `mainWindowBridge`, `sceneBridge`, and `viewBridge` reads/calls.
- Preserve `GraphCanvas.qml` root contracts and object discoverability:
  - `objectName: "graphCanvas"`
  - `toggleMinimapExpanded()`
  - `clearLibraryDropPreview()`
  - `updateLibraryDropPreview()`
  - `isPointInCanvas()`
  - `performLibraryDrop()`
- Preserve graph-surface inline control routing introduced by `GRAPH_SURFACE_INPUT`, including explicit `nodeId` property commits and path browsing.
- Keep behavior stable for drop previews, connection workflows, selection, drag/resize flows, minimap, and viewport zoom/pan.

## Non-Goals
- No visual layer extraction or canvas styling changes.
- No `GraphSceneBridge` internal extraction yet.
- No reopening shell component bridge packets unless a GraphCanvas integration bug forces a minimal follow-up.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell tests.test_workspace_library_controller_unit tests.test_graph_surface_input_contract tests.test_passive_graph_surface_host -v`

## Acceptance Criteria
- `GraphCanvas.qml` no longer depends directly on raw app bridges for its owned concerns.
- Public `GraphCanvas` root methods/properties remain stable.
- GraphCanvas/surface/shell regression tests pass.

## Handoff Notes
- `P07` begins the internal `GraphSceneBridge` split; keep the public bridge contract stable for it.
