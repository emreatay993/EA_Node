# UI_CONTEXT_SCALABILITY_REFACTOR P04: Graph Canvas Root Packetization

## Objective

- Reduce `GraphCanvas.qml` to composition plus the documented stable root contract so ordinary graph UI changes stop paying the cost of one broad QML root file.

## Preconditions

- `P00` is marked `PASS` in [UI_CONTEXT_SCALABILITY_REFACTOR_STATUS.md](./UI_CONTEXT_SCALABILITY_REFACTOR_STATUS.md).
- No later `UI_CONTEXT_SCALABILITY_REFACTOR` packet is in progress.

## Execution Dependencies

- `P03`

## Target Subsystems

- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootLayers.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootApi.js`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_graph_surface_input_controls.py`
- `tests/test_graph_surface_input_inline.py`
- `tests/test_graph_track_b.py`
- `tests/graph_track_b/qml_preference_bindings.py`

## Conservative Write Scope

- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootLayers.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootApi.js`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_graph_surface_input_controls.py`
- `tests/test_graph_surface_input_inline.py`
- `tests/test_graph_track_b.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `docs/specs/work_packets/ui_context_scalability_refactor/P04_graph_canvas_root_packetization_WRAPUP.md`

## Required Behavior

- Extract root-local property binding clusters into `GraphCanvasRootBindings.qml`.
- Extract non-public layer composition into `GraphCanvasRootLayers.qml`.
- Move root-local forwarding helpers into `GraphCanvasRootApi.js`.
- Keep `GraphCanvas.qml` responsible for composition and the stable public root contract only, including `toggleMinimapExpanded()`, `clearLibraryDropPreview()`, `updateLibraryDropPreview()`, `isPointInCanvas()`, and `performLibraryDrop()`.
- End `GraphCanvas.qml` at or below `700` lines.
- Update inherited graph-surface input and track-b regression anchors in place when object names or root helper ownership changes.

## Non-Goals

- No edge-rendering packetization yet; that belongs to `P05`.
- No viewer packet isolation yet.
- No new canvas gestures or menu behavior.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_controls.py tests/test_graph_surface_input_inline.py tests/test_graph_track_b.py tests/graph_track_b/qml_preference_bindings.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_controls.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/ui_context_scalability_refactor/P04_graph_canvas_root_packetization_WRAPUP.md`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootBindings.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootLayers.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootApi.js`

## Acceptance Criteria

- `GraphCanvas.qml` is a composition-first root with only the documented stable public contract methods.
- `GraphCanvas.qml` stays at or below `700` lines.
- The inherited graph-surface input and track-b anchors pass.

## Handoff Notes

- `P05` should split edge rendering without re-expanding the canvas root file.
