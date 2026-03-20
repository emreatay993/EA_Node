# Graph Canvas Perf QA Matrix

- Updated: `2026-03-20`
- Packet set: `GRAPHICS_PERFORMANCE_MODES` (`P01` through `P10`)
- Scope: approved regression and proof-audit workflow for the real `GraphCanvas.qml` pan/zoom path after the app-global graphics-performance mode, render-quality seam, and heavy-media benchmark/report packets landed.

## Locked Benchmark Contract

- `ea_node_editor.telemetry.performance_harness` is the canonical automated benchmark because it instantiates `GraphCanvas.qml` in a `QQuickWindow` and drives `ViewportBridge.centerOn()` / `ViewportBridge.set_zoom()` directly.
- The checked-in docs snapshot for this packet set uses `--performance-mode max_performance --scenario heavy_media` so the benchmark records the app-global mode contract and built-in image/PDF proxy path through the same `P09` report seam.
- Bridge-only timing is historical context only and is not accepted as `REQ-PERF` sign-off evidence.
- Offscreen runs use `QQuickWindow.grabWindow()` plus software Qt Quick / RHI backends for deterministic frame completion. Treat them as regression evidence, not desktop sign-off.

## Approved Regression Commands

| Coverage | Command | Expected Evidence | Environment Notes |
|---|---|---|---|
| Proof-audit checker regression | `./venv/Scripts/python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q` | Confirms the checker still enforces the packet-owned requirement, matrix, report, and traceability tokens | Use the project venv from repo root; rerun this first when only docs or checker code changes |
| Offscreen regression snapshot | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 1 --performance-mode max_performance --scenario heavy_media --report-dir artifacts/graphics_performance_modes_docs` | Writes `artifacts/graphics_performance_modes_docs/TRACK_H_BENCHMARK_REPORT.md` and `artifacts/graphics_performance_modes_docs/track_h_benchmark_report.json` using the real `GraphCanvas.qml` path while recording `performance_mode`, `resolved_graphics_performance_mode`, `scenario`, and `media_surface_count` | This canonical docs snapshot is intentionally smaller than target-scale acceptance and stays on the offscreen/software path |
| Proof audit / review gate | `./venv/Scripts/python.exe scripts/check_traceability.py` | Verifies `20_UI_UX.md`, `40_NODE_SDK.md`, `60_PERSISTENCE.md`, `80_PERFORMANCE.md`, `90_QA_ACCEPTANCE.md`, `TRACEABILITY_MATRIX.md`, this matrix, and `TRACK_H_BENCHMARK_REPORT.md` stay aligned | Run after editing graphics-performance docs, perf docs, or checker rules |

## 2026-03-20 Execution Results

| Command | Result | Notes |
|---|---|---|
| `./venv/Scripts/python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q` | PASS | Packet-owned traceability checker regression passed in the project venv |
| `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 1 --performance-mode max_performance --scenario heavy_media --report-dir artifacts/graphics_performance_modes_docs` | PASS | Generated a real-`GraphCanvas.qml` offscreen snapshot: load p95=`82.356 ms`, pan p95=`96.559 ms`, zoom p95=`151.864 ms`, combined p95=`246.495 ms` |
| `./venv/Scripts/python.exe scripts/check_traceability.py` | PASS | Proof audit passed after the packet-owned graphics-performance docs, perf docs, and traceability links were refreshed |

## Desktop/Manual Follow-Up

- Prerequisites: run on a display-attached Windows desktop with the same branch, remove `QT_QPA_PLATFORM=offscreen`, and do not use a remote/offscreen session that forces the software scene graph path.
- Interactive command:
  `QT_QPA_PLATFORM=windows ./venv/Scripts/python.exe -m ea_node_editor.telemetry.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 3 --baseline-mode interactive --baseline-tag desktop_reference --performance-mode max_performance --scenario heavy_media --report-dir artifacts/graphics_performance_modes_docs`
- Manual spot-check: open the app on the same branch, switch the graphics mode to `Max Performance` through Graphics Settings or the status strip, load a heavy-media graph, and pan/wheel-zoom for a few seconds. Expected result: image/PDF proxy surfaces appear only during the degraded window, there is no stuck proxy/cache state, and idle/full-fidelity appearance returns after interaction settles.
- Exit criteria: replace the canonical `artifacts/graphics_performance_modes_docs/*` snapshot and update this matrix plus `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md` before claiming desktop/GPU sign-off.

## Environment Limits

- The approved automated regression snapshot uses `120` nodes / `320` edges, `1` load iteration, `10` interaction samples, `1` baseline run, `performance_mode=max_performance`, `scenario=heavy_media`, and the built-in `3` image / `3` PDF media mix. It is a regression seam for the real canvas path, not target-scale acceptance evidence.
- `REQ-PERF-001` target-scale acceptance still requires a dedicated `1000` / `5000` run on reference hardware.
- `REQ-PERF-002` currently remains above target in the refreshed offscreen capture, so this packet documents the residual risk instead of hiding it.

## Residual Risks

- Offscreen numbers include software-backend rendering plus readback overhead and therefore do not predict interactive desktop compositor cost directly.
- The desktop/manual follow-up is still outstanding; until it replaces the canonical report directory snapshot, the checked-in evidence is limited to offscreen regression proof rather than full sign-off.
