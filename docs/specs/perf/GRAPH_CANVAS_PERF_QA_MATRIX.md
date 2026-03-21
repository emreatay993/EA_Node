# Graph Canvas Perf QA Matrix

- Updated: `2026-03-21`
- Packet lineage: `GRAPHICS_PERFORMANCE_MODES` canonical proof snapshot, refreshed by `GRAPH_CANVAS_INTERACTION_PERF` `P09`
- Scope: approved same-machine heavy-media regression and proof-audit workflow for the real `GraphCanvas.qml` pan/zoom path, plus the completed Windows desktop/manual exit gate recorded by `P09`.

## Locked Benchmark Contract

- `ea_node_editor.telemetry.performance_harness` is the canonical automated benchmark because it instantiates `GraphCanvas.qml` in a `QQuickWindow` and drives `ViewportBridge.centerOn()` / `ViewportBridge.set_zoom()` directly.
- The checked-in canonical docs snapshot is refreshed from the same-machine `P09` `max_performance` offscreen rerun and mirrored into `artifacts/graphics_performance_modes_docs`; packet-owned `full_fidelity`, `node_drag_control`, and Windows desktop-reference captures stay preserved under `artifacts/graph_canvas_interaction_perf_p09_*`.
- Bridge-only timing is historical context only and is not accepted as `REQ-PERF` sign-off evidence.
- Offscreen runs use `QQuickWindow.grabWindow()` plus software Qt Quick / RHI backends for deterministic frame completion. Treat them as regression evidence, not desktop release sign-off.
- The Windows desktop/manual exit gate uses a display-attached Windows session and the accepted `--qt-platform windows` override for this repo venv so the recorded `Qt platform: windows` value stays truthful.

## Approved Regression Commands

| Coverage | Command | Expected Evidence | Environment Notes |
|---|---|---|---|
| Proof-audit checker regression | `./venv/Scripts/python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q` | Confirms the checker still enforces the packet-owned requirement, matrix, report, artifact, and traceability tokens | Use the project venv from repo root; rerun this first when only docs or checker code changes |
| Offscreen full-fidelity evidence | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 3 --performance-mode full_fidelity --scenario heavy_media --report-dir artifacts/graph_canvas_interaction_perf_p09_full_fidelity` | Writes the packet-owned same-machine `full_fidelity` heavy-media report with explicit pan, zoom, and node-drag control timings through the real `GraphCanvas.qml` path | Deterministic offscreen/software capture for regression proof only |
| Offscreen max-performance canonical proof | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 3 --performance-mode max_performance --scenario heavy_media --report-dir artifacts/graph_canvas_interaction_perf_p09_max_performance` | Writes the packet-owned same-machine `max_performance` heavy-media report, then syncs the checked-in canonical snapshot under `artifacts/graphics_performance_modes_docs` | Deterministic offscreen/software capture; canonical docs snapshot remains an offscreen regression seam rather than target-scale sign-off |
| Offscreen node-drag control evidence | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 3 --performance-mode full_fidelity --scenario heavy_media --report-dir artifacts/graph_canvas_interaction_perf_p09_node_drag_control` | Preserves the explicit full-fidelity node-drag control capture and variance series for the final packet-owned evidence set | Same machine and same deterministic offscreen/software path as the other packet-owned reruns |
| Windows desktop/manual exit gate | `./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 3 --baseline-mode interactive --baseline-tag desktop_reference --performance-mode full_fidelity --scenario heavy_media --qt-platform windows --report-dir artifacts/graph_canvas_interaction_perf_p09_desktop_reference` | Writes the packet-owned Windows desktop-reference report with `Qt platform: windows`; the manual checklist outcome is recorded in the `P09` wrap-up | Run only on a display-attached Windows desktop session in this branch; the accepted `--qt-platform windows` override is required for truthful reporting in this repo venv |
| Proof audit / review gate | `./venv/Scripts/python.exe scripts/check_traceability.py` | Verifies `80_PERFORMANCE.md`, `90_QA_ACCEPTANCE.md`, `TRACEABILITY_MATRIX.md`, this matrix, the benchmark report, and the required packet/canonical artifacts stay aligned | Run after editing perf docs, requirements, traceability rows, or checker rules |

## 2026-03-21 Execution Results

| Command | Result | Notes |
|---|---|---|
| `./venv/Scripts/python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q` | PASS | Packet-owned traceability checker regression passed in the project venv |
| `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 3 --performance-mode full_fidelity --scenario heavy_media --report-dir artifacts/graph_canvas_interaction_perf_p09_full_fidelity` | PASS | Real-`GraphCanvas.qml` offscreen `full_fidelity` rerun: load p95=`64.307 ms`, pan p95=`165.068 ms`, zoom p95=`170.104 ms`, node-drag control p95=`366.433 ms`; node-drag variance remains explicit |
| `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 3 --performance-mode max_performance --scenario heavy_media --report-dir artifacts/graph_canvas_interaction_perf_p09_max_performance` | PASS | Real-`GraphCanvas.qml` offscreen `max_performance` rerun: load p95=`67.842 ms`, pan p95=`97.890 ms`, zoom p95=`16.657 ms`, node-drag control p95=`48.352 ms`; the canonical `artifacts/graphics_performance_modes_docs/*` snapshot was refreshed from this same-machine report |
| `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 3 --performance-mode full_fidelity --scenario heavy_media --report-dir artifacts/graph_canvas_interaction_perf_p09_node_drag_control` | PASS | Packet-owned node-drag control capture completed with the real `GraphCanvas.qml` path: load p95=`66.070 ms`, pan p95=`166.143 ms`, zoom p95=`215.842 ms`, node-drag control p95=`361.639 ms`; pan/zoom/drag variance stayed above threshold and remains documented |
| `./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 3 --baseline-mode interactive --baseline-tag desktop_reference --performance-mode full_fidelity --scenario heavy_media --qt-platform windows --report-dir artifacts/graph_canvas_interaction_perf_p09_desktop_reference` | PASS | Windows desktop-reference capture recorded `Qt platform: windows`: load p95=`146.767 ms`, pan p95=`191.553 ms`, zoom p95=`276.627 ms`, node-drag control p95=`413.152 ms`; the manual exit gate was accepted in-thread and recorded in the packet wrap-up |
| `./venv/Scripts/python.exe scripts/check_traceability.py` | PASS | Proof audit passed after the packet-owned perf docs, requirements, traceability rows, and canonical artifact snapshot were refreshed |

## Desktop/Manual Exit Gate

- Status: `PASS`
- Desktop reference artifact: `artifacts/graph_canvas_interaction_perf_p09_desktop_reference/TRACK_H_BENCHMARK_REPORT.md`
- Manual checklist:
  - Heavy-media pan/zoom smoothness: `PASS`; the user reported the desktop run felt "quite smooth right now."
  - Full-fidelity visuals unchanged: `PASS`; the user accepted packet closeout on the completed desktop-reference evidence after the launcher visibility issue prevented another clean rerun.
  - Minimap and edge-label stability: `PASS`; the user accepted packet closeout on the completed desktop-reference evidence after the launcher visibility issue prevented another clean rerun.

## Environment Limits

- The final automated regression captures use `120` nodes / `320` edges, `1` load iteration, `10` interaction samples, `3` baseline runs, `scenario=heavy_media`, and the built-in `3` image / `3` PDF media mix. They are same-machine regression evidence, not target-scale acceptance evidence.
- The checked-in canonical snapshot remains the offscreen `max_performance` report mirrored into `artifacts/graphics_performance_modes_docs`; the Windows desktop/manual exit gate is recorded separately in `artifacts/graph_canvas_interaction_perf_p09_desktop_reference`.
- `REQ-PERF-001` target-scale acceptance still requires a dedicated `1000` / `5000` run on reference hardware.
- `REQ-PERF-002` remains above target in both the refreshed offscreen and desktop-reference captures, so this packet keeps the residual risk explicit instead of hiding it.

## Residual Risks

- Offscreen numbers include software-backend rendering plus readback overhead and therefore do not predict interactive desktop compositor cost directly.
- The Windows desktop-reference capture is still a same-machine qualitative exit gate, not quantitative release sign-off: `full_fidelity` desktop zoom and node-drag control variance remained above threshold and the absolute timings stayed well above the `<= 33 ms` target.
- The manual closeout was accepted in-thread after the smoothness confirmation and user approval to proceed, but no screenshot or video record was captured for the desktop checklist.
