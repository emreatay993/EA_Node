# GRAPH_SURFACE_INPUT P05: Inline Core Editors

## Objective
- Migrate core inline editors (`toggle`, `enum`, `text`, `number`) onto the shared graph-surface control kit so standard nodes stop relying on ad hoc inline controls behind host-level drag behavior.

## Preconditions
- `P04` is marked `PASS` in [GRAPH_SURFACE_INPUT_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_surface_input/GRAPH_SURFACE_INPUT_STATUS.md).
- No later `GRAPH_SURFACE_INPUT` packet is in progress.

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph/GraphInlinePropertiesLayer.qml`
- `ea_node_editor/ui_qml/components/graph/GraphStandardNodeSurface.qml`
- `tests/test_graph_surface_input_controls.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/main_window_shell/view_library_inspector.py` only if inline payload expectations need extension

## Required Behavior
- Replace the existing ad hoc inline control instances in `GraphInlinePropertiesLayer.qml` with the shared graph-surface controls.
- Publish accurate `embeddedInteractiveRects` for inline toggle, enum, text, and number controls.
- Preserve existing inline property behavior:
  - override-by-input display
  - current value rendering
  - existing commit semantics for `text` and `number`
  - passive and standard host theming hooks
- Keep `GraphStandardNodeSurface.qml` behavior stable outside the control refactor.
- Add regressions that prove clicking the inline controls no longer falls through to host drag/select/open behavior.

## Non-Goals
- No `textarea` or `path` inline support yet.
- No media-surface migration yet.
- No inspector behavior changes.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_surface_input_controls tests.test_graph_surface_input_contract -v`

## Acceptance Criteria
- Standard inline core editors use the shared control kit.
- Their interactive regions are published to the host and block host body behavior locally.
- Existing inline payload and visual semantics remain stable.

## Handoff Notes
- `P06` extends the same layer to `textarea` and `path`.
