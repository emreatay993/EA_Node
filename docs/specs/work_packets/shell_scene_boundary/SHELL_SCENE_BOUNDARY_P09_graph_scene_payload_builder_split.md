# SHELL_SCENE_BOUNDARY P09: GraphScene Payload Builder Split

## Objective
- Extract payload/minimap/theme/media normalization rebuilding from `GraphSceneBridge` into dedicated builder helpers so the bridge stops mixing state/mutation concerns with render-model construction.

## Preconditions
- `P08` is marked `PASS` in [SHELL_SCENE_BOUNDARY_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/shell_scene_boundary/SHELL_SCENE_BOUNDARY_STATUS.md).
- No later `SHELL_SCENE_BOUNDARY` packet is in progress.

## Execution Dependencies
- `P08`

## Target Subsystems
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py` (new)
- `tests/test_flow_edge_labels.py`
- `tests/test_flowchart_surfaces.py`
- `tests/test_graph_theme_shell.py`
- `tests/test_passive_visual_metadata.py`
- `tests/test_pdf_preview_provider.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `tests/test_flow_edge_labels.py`
- `tests/test_flowchart_surfaces.py`
- `tests/test_graph_theme_shell.py`
- `tests/test_passive_visual_metadata.py`
- `tests/test_pdf_preview_provider.py`

## Required Behavior
- Extract node/edge/minimap payload shaping, inline-property payload assembly, graph-theme resolution, edge payload rebuilding, and PDF media page normalization into `graph_scene_payload_builder.py` or equivalent helper(s).
- Preserve emitted payload shapes, signal timing, and graph-theme separation required by shell/canvas tests.
- Preserve passive media preview/page behavior and flow-edge label payload correctness.
- Keep the public `GraphSceneBridge` API stable while reducing its inline builder logic.

## Non-Goals
- No further scope/selection or mutation/history extraction.
- No GraphCanvas or shell-bridge rewrites.
- No intentional behavior changes to theme, media preview, or flow-edge payload semantics.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_flow_edge_labels tests.test_flowchart_surfaces tests.test_graph_theme_shell tests.test_passive_visual_metadata tests.test_pdf_preview_provider -v`

## Acceptance Criteria
- `GraphSceneBridge` no longer owns all payload/theme/media builder logic inline.
- Payload/theme/media regressions pass.
- Public payload shapes and bridge signals remain stable.

## Handoff Notes
- `P10` runs the combined boundary regression slice and closes the docs/traceability work; keep this packet code-focused.
