# GRAPHICS_PERFORMANCE_MODES P07: Host Surface Quality Seam

## Objective
- Extend the graph host/surface seam so loaded surfaces can observe the resolved performance tier and, when declared, opt into a proxy-surface strategy without breaking existing node rendering contracts.

## Preconditions
- `P00` through `P06` are marked `PASS` in [GRAPHICS_PERFORMANCE_MODES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graphics_performance_modes/GRAPHICS_PERFORMANCE_MODES_STATUS.md).
- No later `GRAPHICS_PERFORMANCE_MODES` packet is in progress.

## Execution Dependencies
- `P06`

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`
- packet-owned host/surface helper glue only if strictly needed
- targeted graph-surface host/contract regression tests

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`
- `ea_node_editor/ui_qml/components/graph/*.qml`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_passive_graph_surface_host.py`
- `docs/specs/work_packets/graphics_performance_modes/P07_host_surface_quality_seam_WRAPUP.md`

## Required Behavior
- Expose the resolved performance tier from the canvas/host path to loaded node surfaces in a stable host-facing form.
- Expose the node’s normalized `render_quality` metadata from `P06` to the loaded surface.
- Add a proxy-surface seam for nodes whose `max_performance_strategy` declares a proxy path, while keeping the generic fallback available for nodes that do nothing special.
- Preserve existing `graphNodeCard` / `graphCanvas` discoverability and ordinary surface loading for nodes that do not opt into proxy behavior.
- Add or update focused tests that lock the new host/surface contract and proxy-strategy routing seam.

## Non-Goals
- No built-in media-surface adoption yet. `P08` owns that.
- No benchmark/report or docs work yet. `P09` and `P10` own those.
- No dynamic plugin-loader overhaul or new runtime surface-family registry.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_contract.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py --ignore=venv -k "render_quality or proxy_surface or quality_tier" -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_contract.py --ignore=venv -k "render_quality" -q`

## Expected Artifacts
- `docs/specs/work_packets/graphics_performance_modes/P07_host_surface_quality_seam_WRAPUP.md`

## Acceptance Criteria
- Host/surface code can observe both the resolved performance tier and the node’s normalized render-quality metadata.
- Nodes without a proxy strategy keep their current rendering path.
- A documented proxy-surface seam exists for future heavy nodes to adopt.
- Focused graph-surface host regressions pass.

## Handoff Notes
- Record the final host property names and proxy decision point in the wrap-up so `P08` can adopt them directly.
- If a compatibility shim is required for surfaces that do not consume the new fields, note its removal plan explicitly.
