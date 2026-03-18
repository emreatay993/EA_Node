# Graph Canvas Perf QA Matrix

- Updated: `2026-03-18`
- Packet set: `GRAPH_CANVAS_PERF` (`P01` through `P05`)
- Scope: approved regression and proof-audit workflow for the real `GraphCanvas.qml` pan/zoom path after the redraw-coalescing, viewport-culling, and interaction-cache packets landed.

## Locked Benchmark Contract

- `ea_node_editor.telemetry.performance_harness` is the canonical automated benchmark because it instantiates `GraphCanvas.qml` in a `QQuickWindow` and drives `ViewportBridge.centerOn()` / `ViewportBridge.set_zoom()` directly.
- Bridge-only timing is historical context only and is not accepted as `REQ-PERF` sign-off evidence.
- Offscreen runs use `QQuickWindow.grabWindow()` plus software Qt Quick / RHI backends for deterministic frame completion. Treat them as regression evidence, not desktop sign-off.

## Approved Regression Commands

| Coverage | Command | Expected Evidence | Environment Notes |
|---|---|---|---|
| Harness seam + proof-audit regression | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_track_h_perf_harness.py tests/test_traceability_checker.py -q` | Confirms the harness still reports the actual `GraphCanvas.qml` render path and that the traceability checker still enforces the report/matrix links | Use the project venv from repo root; this is the smallest automated regression slice for the packet-owned proof layer |
| Offscreen regression snapshot | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 1 --report-dir artifacts/graph_canvas_perf_docs` | Writes `artifacts/graph_canvas_perf_docs/TRACK_H_BENCHMARK_REPORT.md` and `artifacts/graph_canvas_perf_docs/track_h_benchmark_report.json` using the real `GraphCanvas.qml` path | This doc-refresh snapshot is intentionally smaller than target-scale acceptance and stays on the offscreen/software path |
| Proof audit / review gate | `./venv/Scripts/python.exe scripts/check_traceability.py` | Verifies `TRACK_H_BENCHMARK_REPORT.md`, this matrix, `80_PERFORMANCE.md`, `90_QA_ACCEPTANCE.md`, and `TRACEABILITY_MATRIX.md` stay aligned | Run after editing perf docs or requirement traceability text |

## 2026-03-18 Execution Results

| Command | Result | Notes |
|---|---|---|
| `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_track_h_perf_harness.py tests/test_traceability_checker.py -q` | PASS | Harness/report/traceability regression slice passed in the project venv |
| `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 1 --report-dir artifacts/graph_canvas_perf_docs` | PASS | Generated a real-`GraphCanvas.qml` offscreen snapshot: load p95=`27.851 ms`, pan p95=`127.646 ms`, zoom p95=`209.871 ms`, combined p95=`323.747 ms` |
| `./venv/Scripts/python.exe scripts/check_traceability.py` | PASS | Proof audit passed after the packet-owned perf docs, requirement docs, and traceability links were refreshed |

## Desktop/Manual Follow-Up

- Prerequisites: run on a display-attached Windows desktop with the same branch, no `QT_QPA_PLATFORM=offscreen`, and no remote/offscreen session that forces the software scene graph path.
- Interactive command:
  `QT_QPA_PLATFORM=windows ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 3 --baseline-mode interactive --baseline-tag desktop_reference --report-dir artifacts/graph_canvas_perf_desktop`
- Manual spot-check: open the app on the same branch, load a representative graph, then pan and wheel-zoom for a few seconds. Expected result: there is no new user-visible mode or stuck cache state, and the idle appearance returns after interaction settles.
- Exit criteria: archive the interactive report path and update this matrix plus `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md` before claiming desktop/GPU sign-off.

## Environment Limits

- The approved automated regression snapshot uses `120` nodes / `320` edges, `1` load iteration, `10` interaction samples, and `1` baseline run. It is a regression seam for the real canvas path, not target-scale acceptance evidence.
- `REQ-PERF-001` target-scale acceptance still requires a dedicated `1000` / `5000` run on reference hardware.
- `REQ-PERF-002` currently remains above target in the refreshed offscreen capture, so this packet documents the residual risk instead of hiding it.

## Residual Risks

- Offscreen numbers include software-backend rendering plus readback overhead and therefore do not predict interactive desktop compositor cost directly.
- The desktop/manual follow-up is still outstanding; until it is archived, the current checked-in evidence is limited to offscreen regression proof rather than full sign-off.
