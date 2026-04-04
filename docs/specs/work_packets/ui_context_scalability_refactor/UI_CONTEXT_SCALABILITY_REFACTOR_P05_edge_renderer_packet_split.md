# UI_CONTEXT_SCALABILITY_REFACTOR P05: Edge Renderer Packet Split

## Objective

- Split `EdgeLayer.qml` into focused helpers for rendering, labels, cache or cull logic, and hit testing so edge work stops forcing one oversized QML surface into scope.

## Preconditions

- `P00` is marked `PASS` in [UI_CONTEXT_SCALABILITY_REFACTOR_STATUS.md](./UI_CONTEXT_SCALABILITY_REFACTOR_STATUS.md).
- No later `UI_CONTEXT_SCALABILITY_REFACTOR` packet is in progress.

## Execution Dependencies

- `P04`

## Target Subsystems

- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeCanvasLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeFlowLabelLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeHitTestOverlay.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeViewportMath.js`
- `ea_node_editor/ui_qml/components/graph/EdgeSnapshotCache.js`
- `ea_node_editor/ui_qml/components/graph/EdgeMath.js`
- `ea_node_editor/ui_qml/edge_routing.py`
- `ea_node_editor/ui_qml/graph_surface_metrics.py`
- `tests/test_flow_edge_labels.py`
- `tests/test_flowchart_visual_polish.py`
- `tests/test_graphics_settings_preferences.py`
- `tests/test_graph_track_b.py`

## Conservative Write Scope

- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeCanvasLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeFlowLabelLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeHitTestOverlay.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeViewportMath.js`
- `ea_node_editor/ui_qml/components/graph/EdgeSnapshotCache.js`
- `ea_node_editor/ui_qml/components/graph/EdgeMath.js`
- `ea_node_editor/ui_qml/edge_routing.py`
- `ea_node_editor/ui_qml/graph_surface_metrics.py`
- `tests/test_flow_edge_labels.py`
- `tests/test_flowchart_visual_polish.py`
- `tests/test_graphics_settings_preferences.py`
- `tests/test_graph_track_b.py`
- `docs/specs/work_packets/ui_context_scalability_refactor/P05_edge_renderer_packet_split_WRAPUP.md`

## Required Behavior

- Move the canvas paint path into `EdgeCanvasLayer.qml`.
- Move flow-label repeater behavior into `EdgeFlowLabelLayer.qml`.
- Move pointer hit testing into `EdgeHitTestOverlay.qml`.
- Move viewport-transform helpers into `EdgeViewportMath.js` and snapshot-cache helpers into `EdgeSnapshotCache.js`.
- Keep `EdgeLayer.qml` responsible for composition, root property contract, and packet-owned signal glue only.
- End `EdgeLayer.qml` at or below `700` lines and keep each extracted helper at or below `450` lines.
- Preserve selected, previewed, drag-preview, and flow-label simplification behavior.

## Non-Goals

- No viewer packet isolation yet.
- No graph theme editor or performance harness cleanup beyond packet-owned edge helper extraction.
- No change to edge-crossing style semantics.

## Verification Commands

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_flow_edge_labels.py tests/test_flowchart_visual_polish.py tests/test_graphics_settings_preferences.py tests/test_graph_track_b.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_flow_edge_labels.py tests/test_graphics_settings_preferences.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/ui_context_scalability_refactor/P05_edge_renderer_packet_split_WRAPUP.md`
- `ea_node_editor/ui_qml/components/graph/EdgeCanvasLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeFlowLabelLayer.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeHitTestOverlay.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeViewportMath.js`
- `ea_node_editor/ui_qml/components/graph/EdgeSnapshotCache.js`

## Acceptance Criteria

- `EdgeLayer.qml` is no longer the packet-owned home for rendering, labels, cache, and hit testing all at once.
- `EdgeLayer.qml` stays at or below `700` lines and each extracted helper stays at or below `450` lines.
- The inherited flow-edge, graphics-preference, and track-b anchors pass.

## Handoff Notes

- `P06` should isolate viewer-specific surface context without re-expanding the generic edge or canvas packets.
