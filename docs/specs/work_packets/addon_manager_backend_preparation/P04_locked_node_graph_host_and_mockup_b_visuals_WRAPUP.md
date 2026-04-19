# P04 Locked Node Graph Host And Mockup B Visuals Wrap-Up

## Implementation Summary

- Packet: `P04`
- Branch Label: `codex/addon-manager-backend-preparation/p04-locked-node-graph-host-and-mockup-b-visuals`
- Commit Owner: `worker`
- Commit SHA: `3f5d11a6da801eba37028ce6ad32f4a6e60d0bd7`
- Changed Files: `docs/specs/work_packets/addon_manager_backend_preparation/P04_locked_node_graph_host_and_mockup_b_visuals_WRAPUP.md`, `ea_node_editor/ui_qml/components/graph/GraphNodeHeaderLayer.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeSurfaceBridge.qml`, `tests/test_graph_surface_input_contract.py`, `tests/test_graph_surface_input_controls.py`, `tests/test_passive_graph_surface_host.py`
- Artifacts Produced: `docs/specs/work_packets/addon_manager_backend_preparation/P04_locked_node_graph_host_and_mockup_b_visuals_WRAPUP.md`, `ea_node_editor/ui_qml/components/graph/GraphNodeHeaderLayer.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodePortsLayer.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeSurfaceBridge.qml`, `tests/test_graph_surface_input_contract.py`, `tests/test_graph_surface_input_controls.py`, `tests/test_passive_graph_surface_host.py`

- Moved locked-node authority into `GraphNodeHost.qml`, so `nodeData.read_only` and `nodeData.unresolved` now gate title editing, surface actions, common actions, destructive actions, drag and resize affordances, and manager-only locked placeholder behavior at the host boundary.
- Added the packet's Mockup B missing-add-on presentation across the host stack: muted locked header treatment, dashed accent stripe, `LOCKED` chip, collapsed `Requires add-on` placeholder ribbon with add-on details, manager affordance, and locked input and output port glyphs while preserving node silhouette and port positions.
- Routed the locked placeholder escape hatch through the existing P02 seam by sending common-action, context-menu, and placeholder-button requests to `addonManagerBridge.requestOpen(focus_addon_id)` when the missing add-on exposes a focus id.
- Hardened the graph canvas surface bridge against read-only mutation attempts so property commits, inline edits, crop edits, color picks, and browse-path requests short-circuit before reaching the scene or shell bridge for locked placeholders.
- Refreshed packet-owned tests to cover the locked placeholder contract, manager-only node context menus, read-only bridge rejection, and passive-host visual probes for the locked chip, stripe, ribbon, locked ports, and blocked host interactions.

## Verification

- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_contract.py --ignore=venv -q`
- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_controls.py --ignore=venv -q`
- PASS: `.\venv\Scripts\python.exe -m pytest tests/test_passive_graph_surface_host.py -k 'test_standard_host_marks_inactive_input_ports_with_muted_label_and_reason_tooltip or LockedPlaceholderGraphHostTests' -q`
- FAIL: `.\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_controls.py tests/test_graph_surface_input_inline.py tests/test_passive_graph_surface_host.py --ignore=venv -q`
  - Failing inherited tests outside P04 write scope:
    - `tests/test_passive_graph_surface_host.py::PassiveGraphSurfaceHostTests::test_graph_canvas_keeps_node_shadow_visible_during_wheel_zoom`
    - `tests/test_passive_graph_surface_host.py::PassiveGraphSurfaceHostTests::test_graph_canvas_max_performance_degrades_grid_and_minimap_but_preserves_shadows_during_wheel_zoom`
    - `tests/test_passive_graph_surface_host.py::PassiveGraphSurfaceHostTests::test_graph_canvas_max_performance_mutation_burst_uses_snapshot_reuse_and_recovers`
    - `tests/test_passive_graph_surface_host.py::PassiveGraphSurfaceHostTests::test_graph_canvas_media_performance_mode_keeps_full_surface_during_wheel_zoom_and_recovers`
    - `tests/test_passive_graph_surface_host.py::PassiveGraphSurfaceHostTests::test_graph_canvas_media_performance_mode_uses_proxy_surface_during_mutation_burst_and_recovers`
    - `tests/test_passive_graph_surface_host.py::PassiveGraphSurfaceHostTests::test_graph_canvas_mutation_burst_performance_policy_tracks_scene_changes_and_recovers`
    - `tests/test_passive_graph_surface_host.py::PassiveGraphSurfaceHostTests::test_graph_canvas_routes_live_resize_geometry_through_edge_layer_and_scene_commit`
- Final Verification Verdict: `FAIL (7 inherited passive-host regressions outside P04 write scope)`

## Manual Test Directives

Too soon for manual testing.

The packet-owned locked placeholder behavior is implemented, but the required full verification command still fails on inherited passive-host regressions outside the packet write scope. Resolve or explicitly waive those failures before using manual QA as the packet release gate.

## Residual Risks

- The required packet verification command remains red because inherited passive-host shadow and performance-recovery assertions are already failing outside the P04 write scope.
- The live-resize geometry regression still expects a `120.0` height while the current scene path commits `132.0`; that routing path is outside the files owned by this packet.
- The locked placeholder Add-On Manager affordance depends on the session exposing `addonManagerBridge`; when that bridge is absent, the packet falls back to a locked, non-destructive placeholder without an escape action.

## Ready for Integration

- No: the packet-owned locked placeholder implementation is landed, but the required full verification command still fails on inherited passive-host regressions outside P04 write scope.
