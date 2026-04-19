# ADDON_MANAGER_BACKEND_PREPARATION P04: Locked Node Graph Host And Mockup B Visuals

## Objective

- Enforce node-level lock behavior in the graph host and land the Mockup B locked-node treatment so missing add-on nodes are clearly visible, non-interactive, and routed toward the Add-On Manager entry point.

## Preconditions

- `P00` is marked `PASS`.
- `P02` is marked `PASS`.
- `P03` is marked `PASS`.
- No later `ADDON_MANAGER_BACKEND_PREPARATION` packet is in progress.

## Execution Dependencies

- `P00`
- `P02`
- `P03`

## Target Subsystems

- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHeaderLayer.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml`
- `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurfaceBody.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeSurfaceBridge.qml`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_graph_surface_input_controls.py`
- `tests/test_graph_surface_input_inline.py`
- `tests/test_passive_graph_surface_host.py`

## Conservative Write Scope

- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHeaderLayer.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml`
- `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurfaceBody.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeSurfaceBridge.qml`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_graph_surface_input_controls.py`
- `tests/test_graph_surface_input_inline.py`
- `tests/test_passive_graph_surface_host.py`
- `docs/specs/work_packets/addon_manager_backend_preparation/P04_locked_node_graph_host_and_mockup_b_visuals_WRAPUP.md`

## Required Behavior

- Make `nodeData.read_only` and `nodeData.unresolved` authoritative at the graph-host level rather than leaving lock behavior to individual child widgets.
- Block drag, resize, port gestures, title edits, property mutation, surface actions, viewer controls, and normal destructive actions for locked placeholder nodes.
- Match Mockup B's intended treatment: muted header, dashed accent stripe, locked chip, collapsed `Requires add-on` body, and locked port affordances while preserving the normal node silhouette.
- Add the missing-add-on summary ribbon / affordance path in graph chrome and route it through the open-manager request seam from `P02`.
- Update inherited graph-surface regression anchors in place when locked-node behavior changes them.

## Non-Goals

- No final Add-On Manager Variant 4 layout yet; that belongs to `P07`.
- No DPF package extraction or hot-apply lifecycle yet; those belong to `P05` and `P06`.

## Verification Commands

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_controls.py tests/test_graph_surface_input_inline.py tests/test_passive_graph_surface_host.py --ignore=venv -q
```

## Review Gate

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_contract.py --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/addon_manager_backend_preparation/P04_locked_node_graph_host_and_mockup_b_visuals_WRAPUP.md`

## Acceptance Criteria

- Locked placeholder nodes cannot run, mutate, or expose normal actions through graph interactions.
- The graph visually reflects Mockup B rather than a generic warning placeholder.
- Locked-node affordances use the open-manager request seam instead of bespoke dialog wiring.
- The inherited graph-surface regression anchors pass.

## Handoff Notes

- `P07` consumes the affordance path introduced here. Keep the request payload centered on add-on identity rather than direct UI object references.
