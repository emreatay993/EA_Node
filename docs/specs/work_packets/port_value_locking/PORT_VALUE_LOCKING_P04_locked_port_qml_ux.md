# PORT_VALUE_LOCKING P04: Locked Port QML UX

## Objective

- Adopt Variant A locked-port chrome in the graph surface, route manual double-click lock toggles through the retained scene command surface, and keep locked inputs out of QML drag and drop affordances without widening into canvas-wide gestures yet.

## Preconditions

- `P03` is complete and accepted.
- The packet branch starts from the current accepted packet-set integration base.

## Execution Dependencies

- `PORT_VALUE_LOCKING_P03_payload_projection_and_view_filters.md`

## Target Subsystems

- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeDelegate.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasLogic.js`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_graph_surface_input_controls.py`
- `tests/test_graph_surface_input_inline.py`

## Conservative Write Scope

- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeDelegate.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasLogic.js`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_graph_surface_input_controls.py`
- `tests/test_graph_surface_input_inline.py`
- `docs/specs/work_packets/port_value_locking/P04_locked_port_qml_ux_WRAPUP.md`
- `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_STATUS.md`

## Required Behavior

- Add a host-facing `portDoubleClicked` signal path and route locked-port double-clicks to the retained `set_port_locked` scene command surface.
- In `GraphNodePortsLayer.qml`, derive a locked state from payload, apply the Variant A padlock treatment, dim locked labels, and add the subtle locked-row tint while keeping row height and inline property placement unchanged.
- Prevent locked ports from starting drags, hover previews, or click-to-connect flows, and use a forbidden cursor for locked input dots.
- Keep unlocked ports and non-lockable ports on their existing interaction paths.
- Update node-delegate and graph-canvas interaction logic so locked input ports are not treated as valid drop candidates during wire drag or click-to-connect flows.
- Extend QML regression coverage so double-click lock routing, locked input suppression, and padlock-state object contracts fail deterministically when regressed.

## Non-Goals

- No per-view hide gesture handling yet.
- No changes to payload filtering rules from `P03`.
- No GraphInlinePropertiesLayer structural change or extra inline padlock chip in this packet.

## Verification Commands

1. Full packet verification:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_controls.py tests/test_graph_surface_input_inline.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_controls.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/port_value_locking/P04_locked_port_qml_ux_WRAPUP.md`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeDelegate.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasLogic.js`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_graph_surface_input_controls.py`
- `tests/test_graph_surface_input_inline.py`

## Acceptance Criteria

- Locked input rows render the Variant A locked visual treatment while keeping the inline editor row geometry unchanged.
- Double-clicking a lockable port can route a lock/unlock toggle through the retained scene command surface.
- Locked input ports cannot start drag, hover, or click-to-connect flows in QML.
- Locked inputs are not offered as valid drop candidates during wire drag.
- The full packet verification command passes.
- The review gate passes.

## Handoff Notes

- Stop after `P04`. Do not start `P05` in the same thread.
- `P05` adds the empty-canvas hide gestures and any graph-canvas bridge projection still needed to toggle the retained per-view filters from QML.
