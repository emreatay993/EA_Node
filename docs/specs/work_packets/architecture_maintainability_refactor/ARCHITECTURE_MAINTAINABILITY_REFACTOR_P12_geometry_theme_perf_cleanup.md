# ARCHITECTURE_MAINTAINABILITY_REFACTOR P12: Geometry Theme Perf Cleanup

## Objective
- Split routing, surface metrics, edge rendering, theme-editor support, and related performance policy into narrower helpers with explicit ownership boundaries and no compatibility helper layers around the old shapes.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_MAINTAINABILITY_REFACTOR` packet is in progress.

## Execution Dependencies
- `P11`

## Target Subsystems
- `ea_node_editor/ui_qml/graph_surface_metrics.py`
- `ea_node_editor/ui_qml/edge_routing.py`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasPerformancePolicy.js`
- `ea_node_editor/ui/dialogs/graph_theme_editor_dialog.py`
- `ea_node_editor/ui/dialogs/graph_theme_editor_support.py`
- `ea_node_editor/ui/perf/performance_harness.py`
- `tests/test_flow_edge_labels.py`
- `tests/test_flowchart_visual_polish.py`
- `tests/test_graph_theme_editor_dialog.py`
- `tests/test_graph_theme_shell.py`
- `tests/test_graphics_settings_preferences.py`
- `tests/test_graphics_settings_dialog.py`
- `tests/test_track_h_perf_harness.py`
- `tests/test_dead_code_hygiene.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/graph_surface_metrics.py`
- `ea_node_editor/ui_qml/edge_routing.py`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasPerformancePolicy.js`
- `ea_node_editor/ui/dialogs/graph_theme_editor_dialog.py`
- `ea_node_editor/ui/dialogs/graph_theme_editor_support.py`
- `ea_node_editor/ui/perf/performance_harness.py`
- `tests/test_flow_edge_labels.py`
- `tests/test_flowchart_visual_polish.py`
- `tests/test_graph_theme_editor_dialog.py`
- `tests/test_graph_theme_shell.py`
- `tests/test_graphics_settings_preferences.py`
- `tests/test_graphics_settings_dialog.py`
- `tests/test_track_h_perf_harness.py`
- `tests/test_dead_code_hygiene.py`
- `docs/specs/work_packets/architecture_maintainability_refactor/P12_geometry_theme_perf_cleanup_WRAPUP.md`

## Required Behavior
- Split geometry, routing, and edge-rendering policy out of large packet-owned modules into narrower helpers with explicit call sites.
- Make theme-editor support and graphics/performance policy code easier to read by separating UI composition from theme-token or performance-policy logic.
- Keep rendering behavior, theme semantics, and packet-owned perf harness expectations stable while removing compatibility helper layers around the old module shapes.
- Update inherited geometry, theme, graphics-settings, perf-harness, and dead-code-hygiene regression anchors in place when helper boundaries change.

## Non-Goals
- No new rendering features or theme capabilities.
- No docs/traceability cleanup yet.
- No reopening of graph-canvas compatibility or scene decomposition work.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flow_edge_labels.py tests/test_flowchart_visual_polish.py tests/test_graph_theme_editor_dialog.py tests/test_graph_theme_shell.py tests/test_graphics_settings_preferences.py tests/test_graphics_settings_dialog.py tests/test_track_h_perf_harness.py --ignore=venv -q`
2. `./venv/Scripts/python.exe -m pytest tests/test_dead_code_hygiene.py --ignore=venv -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flow_edge_labels.py tests/test_graph_theme_editor_dialog.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/architecture_maintainability_refactor/P12_geometry_theme_perf_cleanup_WRAPUP.md`

## Acceptance Criteria
- Geometry, routing, theme, and performance policy hotspots are split into clearer modules or helpers.
- Packet-owned rendering, theme, and perf harness behavior stays stable without retaining compatibility helper layers.
- The inherited geometry/theme/perf regression anchors pass.

## Handoff Notes
- `P13` should assume the code architecture is now in its post-cleanup shape and close out proof, docs, and traceability without hiding remaining drift behind brittle token checks.
