# PORT_VALUE_LOCKING P05: Canvas Hide Gestures

## Objective

- Add the empty-canvas gesture layer that toggles the retained per-view hide-locked and hide-optional filters, while preserving existing quick-insert, marquee, and panning behavior.

## Preconditions

- `P04` is complete and accepted.
- The packet branch starts from the current accepted packet-set integration base.

## Execution Dependencies

- `PORT_VALUE_LOCKING_P04_locked_port_qml_ux.md`

## Target Subsystems

- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `tests/graph_surface/pointer_and_modal_suite.py`
- `tests/graph_track_b/qml_preference_performance_suite.py`

## Conservative Write Scope

- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `tests/graph_surface/pointer_and_modal_suite.py`
- `tests/graph_track_b/qml_preference_performance_suite.py`
- `docs/specs/work_packets/port_value_locking/P05_canvas_hide_gestures_WRAPUP.md`
- `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_STATUS.md`

## Required Behavior

- Project the current active-view `hide_locked_ports` and `hide_optional_ports` state through the graph-canvas bridge/root-binding path so empty-canvas QML input handlers can toggle `!current` without guessing.
- Add `Ctrl + DoubleClick` on empty canvas to toggle `hide_locked_ports`.
- Add `MiddleButton + LeftButton` chord on empty canvas to toggle `hide_locked_ports`.
- Add `MiddleButton + RightButton` chord on empty canvas to toggle `hide_optional_ports`.
- Keep plain empty-canvas double-click quick insert unchanged when `Ctrl` is not held.
- Keep normal marquee selection, box zoom, and panning behavior unchanged outside the new explicit chord cases.
- Extend canvas interaction regression anchors so gesture precedence, object discovery, and unchanged non-modified behavior are proved explicitly.

## Non-Goals

- No changes to locked-port model or payload semantics from earlier packets.
- No new node-row visuals or property-surface changes.
- No requirement-doc or QA-matrix updates in this packet.

## Verification Commands

1. Full packet verification:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_surface/pointer_and_modal_suite.py tests/graph_track_b/qml_preference_performance_suite.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/graph_surface/pointer_and_modal_suite.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/port_value_locking/P05_canvas_hide_gestures_WRAPUP.md`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `tests/graph_surface/pointer_and_modal_suite.py`
- `tests/graph_track_b/qml_preference_performance_suite.py`

## Acceptance Criteria

- The active-view hide flags are readable from the graph-canvas root/input layer without guessing current state.
- `Ctrl + DoubleClick` on empty canvas toggles `hide_locked_ports` while plain double-click still opens quick insert.
- `MiddleButton + LeftButton` toggles `hide_locked_ports`, and `MiddleButton + RightButton` toggles `hide_optional_ports`.
- Existing panning, marquee selection, and box zoom behavior remain unchanged for non-chord interactions.
- The full packet verification command passes.
- The review gate passes.

## Handoff Notes

- Stop after `P05`. Do not start `P06` in the same thread.
- `P06` is docs-only closeout and must not reopen product code.
