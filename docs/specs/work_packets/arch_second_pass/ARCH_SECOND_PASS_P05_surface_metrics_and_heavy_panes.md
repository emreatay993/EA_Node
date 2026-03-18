# ARCH_SECOND_PASS P05: Surface Metrics And Heavy Panes

## Objective
- Establish one authoritative surface-metrics contract and use it to decompose `GraphMediaPanelSurface.qml` and `InspectorPane.qml` into smaller, lower-risk UI units.

## Preconditions
- `P00` through `P04` are marked `PASS` in [ARCH_SECOND_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_second_pass/ARCH_SECOND_PASS_STATUS.md).
- No later `ARCH_SECOND_PASS` packet is in progress.

## Execution Dependencies
- `P04`

## Target Subsystems
- `ea_node_editor/ui_qml/graph_surface_metrics.py`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetrics.js`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelSurface.qml`
- `ea_node_editor/ui_qml/components/shell/InspectorPane.qml`
- new packet-owned helper components under `ea_node_editor/ui_qml/components/graph/` or `ea_node_editor/ui_qml/components/shell/`
- packet-owned graph-surface and inspector tests

## Conservative Write Scope
- `ea_node_editor/ui_qml/graph_surface_metrics.py`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceMetrics.js`
- `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelSurface.qml`
- `ea_node_editor/ui_qml/components/shell/InspectorPane.qml`
- `ea_node_editor/ui_qml/components/graph/**`
- `ea_node_editor/ui_qml/components/shell/**`
- `tests/test_graph_surface_input_inline.py`
- `tests/test_passive_image_nodes.py`
- `tests/test_pdf_preview_provider.py`
- `tests/test_inspector_reflection.py`
- `tests/main_window_shell/passive_image_nodes.py`
- `tests/main_window_shell/passive_pdf_nodes.py`

## Required Behavior
- Remove the current dual-source surface-metrics drift risk by making Python and QML/JS consume one authoritative contract or a clearly generated/shared representation.
- Split packet-owned media-surface concerns so crop geometry, media source/preview handling, and inline editor/tool UI are not all interleaved in one file.
- Split packet-owned inspector-pane sections into smaller components and move packet-owned edit-session state closer to the bridge/model layer where it improves maintainability.
- Preserve current user-visible media, inspector, and inline-editor behavior.
- Keep existing object names and contracts used by current tests stable unless packet-owned tests are updated in lockstep.

## Non-Goals
- No new media features, editor types, or theme features.
- No `GraphNodeHost.qml` or `GraphCanvas.qml` API changes beyond narrow fallout.
- No graph-scene core refactor; `P06` owns that.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_surface_input_inline tests.test_passive_image_nodes tests.test_pdf_preview_provider tests.test_inspector_reflection tests.main_window_shell.passive_image_nodes tests.main_window_shell.passive_pdf_nodes -v`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_inspector_reflection tests.test_passive_image_nodes -v`

## Expected Artifacts
- `docs/specs/work_packets/arch_second_pass/P05_surface_metrics_and_heavy_panes_WRAPUP.md`

## Acceptance Criteria
- There is one authoritative packet-owned source of truth for surface metrics/geometry rules.
- `GraphMediaPanelSurface.qml` and `InspectorPane.qml` are materially less monolithic while preserving current behavior.
- Current inspector/media/inline-editor regression coverage passes.

## Handoff Notes
- `P08` updates docs and traceability for any new metrics/test harness rules; keep packet-local notes precise.
- If this packet adds a generated/shared metrics helper, document the ownership rule clearly in the wrap-up.
