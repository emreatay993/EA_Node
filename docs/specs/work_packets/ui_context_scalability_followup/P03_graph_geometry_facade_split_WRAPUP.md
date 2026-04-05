# P03 Graph Geometry Facade Split Wrap-Up

## Implementation Summary

- Packet: `P03`
- Branch Label: `codex/ui-context-scalability-followup/p03-graph-geometry-facade-split`
- Commit Owner: `worker`
- Commit SHA: `5af6ef7ebf6d797de1d74b9104cb66c1678dcc04`
- Changed Files: `docs/specs/work_packets/ui_context_scalability_followup/P03_graph_geometry_facade_split_WRAPUP.md`, `ea_node_editor/ui_qml/edge_routing.py`, `ea_node_editor/ui_qml/graph_geometry/__init__.py`, `ea_node_editor/ui_qml/graph_geometry/anchors.py`, `ea_node_editor/ui_qml/graph_geometry/flowchart_metrics.py`, `ea_node_editor/ui_qml/graph_geometry/panel_metrics.py`, `ea_node_editor/ui_qml/graph_geometry/route_endpoints.py`, `ea_node_editor/ui_qml/graph_geometry/route_payload.py`, `ea_node_editor/ui_qml/graph_geometry/route_pipe.py`, `ea_node_editor/ui_qml/graph_geometry/route_styles.py`, `ea_node_editor/ui_qml/graph_geometry/standard_metrics.py`, `ea_node_editor/ui_qml/graph_geometry/surface_contract.py`, `ea_node_editor/ui_qml/graph_geometry/viewer_metrics.py`, `ea_node_editor/ui_qml/graph_surface_metrics.py`, `tests/test_flow_edge_labels.py`, `tests/test_viewer_surface_contract.py`
- Artifacts Produced: `docs/specs/work_packets/ui_context_scalability_followup/P03_graph_geometry_facade_split_WRAPUP.md`, `ea_node_editor/ui_qml/graph_geometry/route_payload.py`, `ea_node_editor/ui_qml/graph_geometry/anchors.py`

- Split the graph geometry implementation into a focused `ea_node_editor.ui_qml.graph_geometry` package and kept `graph_surface_metrics.py` as a 251-line import-compatible facade over the extracted surface-contract, flowchart, panel, viewer, and anchor helpers.
- Split edge routing into endpoint, pipe, style, and payload helpers and kept `edge_routing.py` as a 326-line facade that preserves the existing public and compatibility helper names expected by the repo hygiene checks.
- Added packet-owned seam assertions to the routing and viewer-surface regressions so the new facade budgets and helper package boundaries stay locked in place for later UI packets.

## Verification

- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_flow_edge_labels.py tests/test_flowchart_visual_polish.py tests/test_viewer_surface_contract.py --ignore=venv -q`
- FAIL: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_flow_edge_labels.py tests/test_flowchart_visual_polish.py tests/test_graph_surface_input_contract.py tests/test_passive_graph_surface_host.py tests/test_graph_track_b.py tests/graph_track_b/qml_preference_bindings.py tests/test_viewer_surface_contract.py --ignore=venv -q` (`tests/test_graph_surface_input_contract.py::GraphSurfaceInputContractTests::test_graph_canvas_pendingConnectionPort_rejects_same_node_logic_flow_edge` and `tests/test_passive_graph_surface_host.py::PassiveGraphSurfaceHostTests::test_graph_canvas_media_performance_mode_keeps_full_surface_during_wheel_zoom_and_recovers` exited once with Qt probe code `3221226505`)
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_contract.py -k same_node_logic_flow_edge --ignore=venv -q`
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_passive_graph_surface_host.py -k media_performance_mode_keeps_full_surface_during_wheel_zoom_and_recovers --ignore=venv -q`
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_flow_edge_labels.py tests/test_flowchart_visual_polish.py tests/test_graph_surface_input_contract.py tests/test_passive_graph_surface_host.py tests/test_graph_track_b.py tests/graph_track_b/qml_preference_bindings.py tests/test_viewer_surface_contract.py --ignore=venv -q`
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_flow_edge_labels.py tests/test_graph_track_b.py --ignore=venv -q`
- PASS: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_dead_code_hygiene.py --ignore=venv -q`
- Final Verification Verdict: PASS

## Manual Test Directives

1. Open a graph with standard, flowchart, viewer, annotation, and media nodes, then resize and move them once to confirm port anchors, passive chrome, and viewer body overlays still line up with the pre-split visuals.
2. Create forward and backward flow edges with labels, try a same-node `exec_in` to `exec_out` connection, and zoom a media panel in max-performance mode to confirm orthogonal pipe routing, connection rejection, and full-surface recovery still behave as before.

## Residual Risks

- The geometry logic now spans multiple focused modules, so later packets that adjust anchor math or edge payload policy need to update the facade imports and seam assertions together instead of drifting implementation back into the top-level monoliths.
- The first full verification batch hit two transient Qt probe access violations before the isolated reruns and the final full rerun both passed; if nearby UI work changes probe timing again, those two QML cases are the first places to recheck.

## Ready for Integration

- Yes: the geometry facades are under the packet budgets, the required verification and review gate pass, and the final packet diff stays inside the documented P03 write scope.
