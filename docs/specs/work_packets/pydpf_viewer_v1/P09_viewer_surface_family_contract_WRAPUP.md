# P09 Viewer Surface Family Contract Wrap-Up
## Implementation Summary
- Packet: `P09`
- Branch Label: `codex/pydpf-viewer-v1/p09-viewer-surface-family-contract`
- Commit Owner: `worker`
- Commit SHA: `92e497759810106c7c9b067939c016effb3dccb0`
- Changed Files: `ea_node_editor/nodes/types.py`, `ea_node_editor/nodes/registry.py`, `ea_node_editor/ui_qml/graph_scene_payload_builder.py`, `ea_node_editor/ui_qml/graph_surface_metrics.py`, `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`, `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurface.qml`, `tests/test_viewer_surface_contract.py`, `tests/test_graph_surface_input_contract.py`, `docs/specs/work_packets/pydpf_viewer_v1/P09_viewer_surface_family_contract_WRAPUP.md`
- Artifacts Produced: `ea_node_editor/nodes/types.py`, `ea_node_editor/nodes/registry.py`, `ea_node_editor/ui_qml/graph_scene_payload_builder.py`, `ea_node_editor/ui_qml/graph_surface_metrics.py`, `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`, `ea_node_editor/ui_qml/components/graph/viewer/GraphViewerSurface.qml`, `tests/test_viewer_surface_contract.py`, `tests/test_graph_surface_input_contract.py`, `docs/specs/work_packets/pydpf_viewer_v1/P09_viewer_surface_family_contract_WRAPUP.md`
- Viewer payload fields: `viewer_surface.body_rect`, `viewer_surface.proxy_rect`, `viewer_surface.live_rect`, `viewer_surface.overlay_target`, `viewer_surface.proxy_surface_supported`, `viewer_surface.live_surface_supported`
- Geometry assumptions: `body_rect` starts at `surface_metrics.body_left_margin` / `surface_metrics.body_top`, uses node width minus body margins, and uses `surface_metrics.body_height`; `proxy_rect` and `live_rect` match the full body rect in `P09`

## Verification
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_viewer_surface_contract.py tests/test_graph_surface_input_contract.py --ignore=venv -q` (`24 passed in 29.02s`)
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_viewer_surface_contract.py --ignore=venv -q` (`4 passed in 1.42s`)
- PASS: `git diff --check` (no whitespace or merge-marker issues)
- Final Verification Verdict: PASS

## Manual Test Directives
Too soon for manual testing
- Blocker: `P09` adds only the viewer surface family contract; there is still no shipped `dpf.viewer` node or `viewerSessionBridge` path that a user can exercise from the graph UI.
- Blocker: native overlay ownership and live-session orchestration are deferred to `P10` through `P12`, so manual viewer interaction would not represent the intended end-to-end behavior yet.
- Next condition: once a later packet exposes a real viewer-family node in the shell, place it on the graph and confirm the host loads `GraphViewerSurface.qml`, keeps the proxy/live rect on the node body, and routes reduced-quality mode to the proxy surface contract.

## Residual Risks
- `GraphNodeSurfaceMetrics.js` still treats `viewer` as a fallback-to-standard family, so the QML host currently depends on scene payloads providing the viewer-specific metrics and rect contract that `P09` now publishes.
- The packet reserves the node body and publishes proxy/live rect metadata, but actual live widget parenting, overlay geometry sync, and viewer-session state remain deferred to later packets.
- No production node uses `surface_family="viewer"` yet, so automated packet-owned tests are the only active regression coverage until the later viewer packets land.

## Ready for Integration
- Yes: the `viewer` family is accepted by the SDK and registry, routed through the existing loader and payload seams, backed by a base `GraphViewerSurface.qml`, and covered by the packet verification and review gate.
