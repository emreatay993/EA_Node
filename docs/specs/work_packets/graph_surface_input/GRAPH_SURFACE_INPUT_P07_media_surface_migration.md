# GRAPH_SURFACE_INPUT P07: Media Surface Migration

## Objective
- Migrate media-surface interactive controls to direct surface ownership and remove the private host hover proxy compatibility layer.

## Preconditions
- `P06` is marked `PASS` in [GRAPH_SURFACE_INPUT_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_STATUS.md).
- No later `GRAPH_SURFACE_INPUT` packet is in progress.

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelSurface.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_passive_image_nodes.py`
- `tests/main_window_shell/passive_image_nodes.py`

## Required Behavior
- Migrate the media crop button, Apply/Cancel buttons, and crop handles onto the direct surface-control ownership model backed by `embeddedInteractiveRects`.
- Preserve crop-mode whole-surface locking through `blocksHostInteraction`.
- Remove `hoverActionHitRect` forwarding from `GraphNodeSurfaceLoader.qml`.
- Remove the private host hover proxy button from `GraphNodeHost.qml`.
- Ensure the media surface still supports hover-only visibility for the crop button without reintroducing a click-swallowing overlay.
- Add regressions for direct crop-button, Apply, Cancel, and crop-handle behavior without host-proxy dependence.

## Non-Goals
- No broad audit of every graph surface yet.
- No TODO/docs closure yet.
- No canvas-wide input rewrite.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_passive_graph_surface_host tests.test_passive_image_nodes -v`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.main_window_shell.passive_image_nodes.MainWindowShellPassiveImageNodesTests.test_image_panel_crop_button_click_does_not_start_host_drag -v`
3. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.main_window_shell.passive_image_nodes.MainWindowShellPassiveImageNodesTests.test_image_panel_crop_apply_and_cancel_clicks_bypass_host_drag -v`

## Acceptance Criteria
- Media-surface controls no longer depend on `hoverActionHitRect` or `graphNodeSurfaceHoverActionButton`.
- Crop-mode locking still works.
- Direct media-surface clicks no longer leak to host drag/open/context behavior.

## Handoff Notes
- `P08` performs the broader audit and freezes the no-top-overlay rule across graph surfaces.
