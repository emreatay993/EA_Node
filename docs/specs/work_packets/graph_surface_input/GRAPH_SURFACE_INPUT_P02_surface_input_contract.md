# GRAPH_SURFACE_INPUT P02: Surface Input Contract

## Objective
- Introduce the explicit host/surface input contract for local embedded controls so host body behavior yields only where a surface publishes interactive ownership.

## Preconditions
- `P01` is marked `PASS` in [GRAPH_SURFACE_INPUT_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_STATUS.md).
- No later `GRAPH_SURFACE_INPUT` packet is in progress.

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphInlinePropertiesLayer.qml` only as needed for initial rect publication
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelSurface.qml` only as needed for initial rect publication
- `tests/test_passive_graph_surface_host.py`
- `tests/test_graph_surface_input_contract.py` (new if needed)

## Required Behavior
- Add `readonly property var embeddedInteractiveRects` to `GraphNodeSurfaceLoader.qml`, forwarding it from the loaded surface with an empty-list fallback.
- Add host-local hit-testing helpers in `GraphNodeHost.qml` that check `embeddedInteractiveRects`.
- Split the input model clearly:
  - `embeddedInteractiveRects` blocks host body drag/select/open/context only within published local regions.
  - `blocksHostInteraction` continues to disable host drag/resize/ports for whole-surface modal tools.
- Publish initial interactive rects from current surface content where needed to prove the contract works before the shared-control refactor lands.
- Keep `hoverActionHitRect` and the host hover proxy working as a compatibility layer through this packet.
- Add regressions that prove points inside published interactive rects do not trigger host body interactions while adjacent body points still do.

## Non-Goals
- No node-specific commit/browse bridge changes yet.
- No shared control-kit extraction yet.
- No media hover-proxy removal yet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_passive_graph_surface_host tests.test_graph_surface_input_contract -v`

## Acceptance Criteria
- The host can distinguish local interactive-control regions from ordinary body regions.
- Whole-surface locks continue to work independently of local interactive rects.
- Compatibility behavior remains intact for current surfaces.

## Handoff Notes
- `P03` consumes this contract to decouple inline commits and browse actions from selected-node state.
