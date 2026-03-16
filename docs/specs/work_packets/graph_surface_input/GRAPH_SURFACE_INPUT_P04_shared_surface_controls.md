# GRAPH_SURFACE_INPUT P04: Shared Surface Controls

## Objective
- Add a reusable graph-surface control kit and host-space geometry helpers so future interactive surfaces do not reimplement buttons, fields, hover plumbing, or rect publication ad hoc.

## Preconditions
- `P03` is marked `PASS` in [GRAPH_SURFACE_INPUT_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_STATUS.md).
- No later `GRAPH_SURFACE_INPUT` packet is in progress.

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph/surface_controls/` (new)
- `ea_node_editor/ui_qml/components/graph/GraphInlinePropertiesLayer.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelSurface.qml` only for shared helper adoption if useful
- `tests/test_graph_surface_input_controls.py` (new)

## Required Behavior
- Add reusable graph-surface controls such as:
  - a shared button
  - a shared text field
  - a shared combo box
  - a shared checkbox
  - any minimal support wrapper needed to surface host-space interactive rects and control-start events
- Add a small JS helper for mapping a child item’s rect into host-local coordinates and composing multiple interactive rects.
- Keep the control kit graph-surface-scoped; do not couple it to inspector components or shell layout.
- Make the kit suitable for both standard inline editors and passive media controls.
- Add focused tests for control start, rect publication, and basic styling/contract behavior.

## Non-Goals
- No `textarea` or `path` editor mode yet.
- No media hover-proxy removal yet.
- No broad visual restyling of existing node surfaces.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_surface_input_controls -v`

## Acceptance Criteria
- New graph-surface controls can publish interactive rects and signal control-start behavior consistently.
- The shared control kit is reusable by later packets without reopening host-level input logic.

## Handoff Notes
- `P05` migrates core inline editors onto this shared control kit.
