# GRAPH_SURFACE_INPUT P01: Host Drag Layer Foundation

## Objective
- Move host drag/select/open/context handling below surface content so embedded controls are no longer forced to click through a top-level full-card drag overlay.

## Preconditions
- `P00` is marked `PASS` in [GRAPH_SURFACE_INPUT_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_STATUS.md).
- No later `GRAPH_SURFACE_INPUT` packet is in progress.

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `tests/test_passive_graph_surface_host.py`
- `tests/test_main_window_shell.py` only if a narrow regression is required to preserve object discoverability

## Required Behavior
- Move the node body drag/select/open/context pointer path under surface content instead of over it.
- Preserve current body interactions for non-interactive regions:
  - left-click selects
  - left-drag moves
  - double-click opens
  - right-click opens the node context menu
- Preserve current port and resize-handle interactions.
- Preserve current z-order, `graphNodeCard` discoverability, and GraphCanvas public contracts.
- Keep compatibility with the current `hoverActionHitRect` shim and current surface implementations. This packet is structural groundwork only.
- Add focused regressions that prove the host no longer depends on a top overlay to receive ordinary body drag interactions.

## Non-Goals
- No `embeddedInteractiveRects` contract yet.
- No inline editor or media-surface refactor yet.
- No bridge API changes yet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_passive_graph_surface_host -v`

## Acceptance Criteria
- Non-interactive body drag/select behavior still works.
- Surface content is no longer structurally underneath a full-card drag catcher.
- Existing host regressions remain green.

## Handoff Notes
- `P02` adds the explicit local interactive-region contract on top of this structural change.
