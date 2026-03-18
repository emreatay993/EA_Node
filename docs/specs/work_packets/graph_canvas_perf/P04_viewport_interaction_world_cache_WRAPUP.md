# P04 Viewport Interaction World Cache Wrap-Up

## Implementation Summary

- Packet: `P04`
- Branch Label: `codex/graph-canvas-perf/p04-viewport-interaction-world-cache`
- Commit Owner: `worker`
- Commit SHA: `aa10005daacf6908cc1bb4b70da36ce24f37946a`
- Changed Files: `ea_node_editor/ui_qml/components/GraphCanvas.qml`, `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`, `tests/test_passive_graph_surface_host.py`, `tests/test_graph_track_b.py`
- Artifacts Produced: `docs/specs/work_packets/graph_canvas_perf/P04_viewport_interaction_world_cache_WRAPUP.md`, `artifacts/graph_canvas_perf_p04/TRACK_H_BENCHMARK_REPORT.md`, `artifacts/graph_canvas_perf_p04/track_h_benchmark_report.json`

Viewport interaction now reuses a texture-backed node presentation by enabling per-node `layer` caching only while the existing viewport interaction state is active. Panning and wheel zoom share the same activation path and return to the steady-state node presentation through the existing `150 ms` interaction idle timer, while non-viewport gestures keep the current live node world path.

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py -k "graph_canvas_temporarily_simplifies_node_shadow_during_wheel_zoom" -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_track_b.py -k "viewport_applies_zoom_and_center_updates" -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 80 --edges 220 --load-iterations 1 --interaction-samples 8 --baseline-runs 1 --report-dir artifacts/graph_canvas_perf_p04`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_passive_graph_surface_host.py -k "graph_canvas_temporarily_simplifies_node_shadow_during_wheel_zoom" -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: open a graph with multiple visible nodes on this branch and keep the canvas at its default graphics settings.
- Wheel zoom over the populated canvas. Expected result: nodes stay visible while zooming, shadows simplify during motion, and the original idle appearance returns within about `150 ms` after zoom input stops.
- Middle-mouse pan across the same graph. Expected result: the canvas remains interactive during motion and the steady-state node presentation returns after panning settles.
- Start a non-viewport gesture such as dragging from a node output port without panning or zooming. Expected result: port drag behavior stays unchanged and there is no separate cache-mode visual shift outside viewport interaction.

## Residual Risks

- The cache window is intentionally short and tied to the existing `150 ms` viewport-idle timer, but the texture-backed node presentation during that window may still vary slightly by GPU or Qt scene graph backend.
- The optimization is per-node layer caching rather than a whole-world snapshot, so future node-surface changes that increase per-node texture cost could reduce the benefit unless they are profiled against the same interaction path.

## Ready for Integration

- Yes: viewport-only node caching now activates and recovers through the existing interaction lifecycle, the targeted regressions pass, and the smoke benchmark completed successfully.
