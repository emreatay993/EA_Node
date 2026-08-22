# EA_Node Stress 1200 Post-Closeout Escalation Plan

## Summary
- This plan supersedes the earlier stress-1200 follow-up plan for next implementation work. It is based on the completed `origin/main` stress closeout at `d84067d8` inspected from `C:\Users\emre_\PycharmProjects\EA_Node_Editor_origin_main_inspect`.
- The prior `P01` through `P10` packet series did real work: bridge-owned visible-node indexing, stable visible models, visible-edge snapshots, frame coalescing, grid/minimap counters, overlay guardrails, and a Windows display default of `qquickview_container` plus Direct3D 11.
- The packet series is `PASS` as packet execution, but not as performance acceptance. Latest final stress evidence still fails `REQ-PERF-002` and `REQ-PERF-003`.
- Final offscreen/software P10 artifact: load p95 `4363.226 ms`, pan p95 `330.429 ms`, zoom p95 `348.836 ms`, node-drag p95 `1121.054 ms`, and no-readback frame interval p95 `547.234 ms`.
- Integrated display D3D11 evidence: `qquickview_container` improves over `qquickwidget`, but still fails with pan p95 `206.475 ms`, zoom p95 `160.113 ms`, node-drag p95 `537.482 ms`, no-readback frame interval p95 `500.265 ms`, and load p95 `7257.051 ms`.
- The next plan must stop redoing already-fixed work. Visible-model query p95 is now about `0.09-0.10 ms`; grid paint is `0 ms`; overlay sync is `0 ms`; grid update is at most about `5 ms`. The remaining hot seams are fixture/evidence correctness, edge spatial index rebuilds, edge redraw/frame flush churn, and project/canvas setup cost.

## Key Changes
- Make the real `stress_1200_nodes.cxproj` fixture available in clean worktrees or make the generated fallback an explicitly named synthetic fixture. Acceptance must not silently fall back when the real fixture is requested.
- Convert benchmark result language so packet closeout can pass while performance acceptance still fails. A `PASS` packet status must not be confused with meeting `REQ-PERF-002` or `REQ-PERF-003`.
- Fix or disprove the edge spatial index timing anomaly: final reports show `pan_edge_spatial_index_build_ms` and `zoom_edge_spatial_index_build_ms` near `972 ms`, and integrated display notes show `880-1332 ms`.
- Reduce edge redraw requests and flushed frames during a single pan/zoom sample. Final reports still show edge redraw request p95 around `158-160` and flushed-frame p95 around `155-157`.
- Split live interaction into a transform-first path and a deferred exact-rebuild path. Pan/zoom should move already-rendered content immediately, then rebuild edge snapshots only after a meaningful viewport/index boundary or idle deadline.
- Optimize node drag separately: immediate selected-node motion stays live, incident edge previews update at frame cadence, and full crossing/label/exact edge work settles after release or idle.
- Treat load/setup as its own performance product. Final offscreen load is `4.36 s`; display load is `7.2-7.7 s`; final offscreen canvas setup is `13.85 s`.
- Keep zero-loss features. The accepted steady state must preserve grid, minimap, labels, shadows, edge crossing style, overlays, context menus, tooltips, drag, pan, zoom, node controls, passive surfaces, fullscreen, search, command routing, persistence, and execution visualization.

## Public Interface Changes
- Add a benchmark fixture mode distinction:
  - `--stress-fixture real` requires the committed or locally supplied `stress_1200_nodes.cxproj` and fails if absent.
  - `--stress-fixture generated` uses the deterministic generated 1200-node fallback and labels reports as generated.
  - Keep `--stress-fixture` as a backward-compatible alias only if it resolves to a documented default and reports the selected strategy clearly.
- Add acceptance fields to benchmark JSON and reports:
  - `packet_verification_result`
  - `performance_acceptance_result`
  - `fixture_source_kind`
  - `fixture_source_path`
  - `fixture_checksum`
  - `display_attached_required`
  - `display_attached_observed`
- Add a display benchmark command that refuses `QT_QPA_PLATFORM=offscreen` for acceptance runs.
- Optional developer-only graphics status may show active host, RHI backend, graphics API, render loop, DPR, and software fallback status.

## Execution Tasks

### T01 Sync And Evidence Baseline
- Goal: Bring the implementation branch to the completed stress closeout state and establish a trustworthy before/after baseline for this escalation.
- Preconditions: Preserve local dirty work first. Do not run `git pull` directly into the current dirty checkout. Use a clean worktree or stash/commit local work intentionally.
- Conservative write scope:
  - `docs/specs/work_packets/graph_canvas_stress_1200/GRAPH_CANVAS_STRESS_1200_STATUS.md`
  - `docs/specs/work_packets/graph_canvas_stress_1200/P10_stress_closeout_defaults_WRAPUP.md`
  - `docs/specs/work_packets/graph_canvas_stress_1200/P01_P09_integrated_display_d3d11_benchmark.md`
  - `artifacts/graph_canvas_stress_1200_final/**`
  - `artifacts/graph_canvas_stress_1200_display_*`
- Deliverables:
  - Confirm the working branch includes `origin/main` through `d84067d8` or a later commit.
  - Preserve current local uncommitted plan/docs work before updating.
  - Record the exact latest metrics listed in this plan as the baseline for escalation.
  - Record that previous `P10` is packet-pass/performance-fail.
- Verification:
  - `git status -sb`
  - `git log --oneline --decorate -n 5`
  - Confirm the latest status ledger contains `P01` through `P10` as terminal.
- Non-goals: No performance code changes.
- Packetization notes: Use as `P00` bootstrap if this becomes a packet set.

### T02 Make Stress Fixture Acceptance Honest
- Goal: Stop acceptance runs from silently using a generated fixture when the user intends the real `examples/stress_1200_nodes.cxproj`.
- Preconditions: `T01` baseline captured.
- Conservative write scope:
  - `.gitignore`
  - `examples/stress_1200_nodes.cxproj` or a new tracked fixture under `tests/fixtures/perf/`
  - `scripts/generate_stress_fixture.py` if a generator is preferred over tracking the `.cxproj`
  - `ea_node_editor/ui/perf/performance_harness.py`
  - `tests/test_track_h_perf_harness.py`
  - `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`
  - `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md`
- Deliverables:
  - Choose one canonical strategy:
    - Track the real stress fixture with a `.gitignore` negation, or
    - Add a deterministic generator and record a fixture checksum, or
    - Require the local fixture path for manual acceptance and keep generated fallback only for CI regression.
  - Make display-attached acceptance fail if `--stress-fixture real` cannot find the real fixture.
  - Report `fixture_source_kind`, `fixture_source_path`, `fixture_path_exists`, `fixture_checksum`, and `fixture_strategy`.
  - Update docs so generated fallback evidence is not described as real fixture proof.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest tests/test_track_h_perf_harness.py --ignore=venv -q`
  - Harness smoke proving `real` mode fails when the file is absent and succeeds when the fixture exists.
- Non-goals: Do not optimize rendering in this task.
- Packetization notes: This is the first required implementation packet because all later benchmark claims depend on it.

### T03 Fix Benchmark Acceptance Semantics
- Goal: Make reports impossible to misread: packet completion can pass while performance requirements fail.
- Preconditions: `T02` fixture source semantics are in place.
- Conservative write scope:
  - `ea_node_editor/ui/perf/performance_harness.py`
  - `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`
  - `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md`
  - `docs/specs/requirements/80_PERFORMANCE.md`
  - `scripts/verification_manifest.py`
  - `tests/test_track_h_perf_harness.py`
  - `tests/test_traceability_checker.py`
- Deliverables:
  - Add separate report fields for verification result and performance acceptance result.
  - Mark `REQ-PERF-002` and `REQ-PERF-003` as blocking acceptance failures when p95 targets are missed.
  - Add an explicit display-attached acceptance section. It must record `QT_QPA_PLATFORM=windows`, `QSG_RHI_BACKEND=d3d11` or selected backend, graphics API, host, DPR, and whether `QSG_INFO=1` was captured.
  - Correct any benchmark limitation text that says offscreen when renderer diagnostics prove `windows` / `d3d11`.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest tests/test_track_h_perf_harness.py tests/test_traceability_checker.py --ignore=venv -q`
  - `.\venv\Scripts\python.exe .\scripts\check_traceability.py`
  - `.\venv\Scripts\python.exe .\scripts\check_markdown_links.py`
- Non-goals: No rendering changes.
- Packetization notes: Can merge with `T02` if the same executor owns the harness/report contract.

### T04 Edge Spatial Index Rebuild Audit And Fix
- Goal: Remove the suspicious edge spatial index rebuild cost or prove it is a measurement bug.
- Preconditions: `T02` and `T03` report fixture and acceptance truthfully.
- Conservative write scope:
  - `ea_node_editor/ui_qml/components/graph/EdgeSnapshotCache.js`
  - `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeCanvasLayer.qml`
  - Optional new helper under `ea_node_editor/ui_qml/` if the index moves out of QML JS
  - `tests/test_edge_snapshot_spatial_index.py`
  - `tests/graph_track_b/qml_preference_performance_suite.py`
- Deliverables:
  - Audit whether `pan_edge_spatial_index_build_ms=972 ms` is stale cumulative state, a real rebuild, or an instrumentation defect.
  - Replace `Date.now()` timing with a monotonic/high-resolution timing source where QML supports it, or measure from Python harness around explicit calls.
  - Ensure the spatial index is built only on edge topology, endpoint geometry, or graph revision changes, not on every viewport pan/zoom.
  - Add dirty-entry updates for dragged incident edges instead of whole-index rebuilds.
  - Add counters for index rebuild count, dirty-entry update count, index query count, and query time.
  - Set a gate: normal pan/zoom must have spatial-index rebuild count `0` after warmup.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest tests/test_edge_snapshot_spatial_index.py --ignore=venv -q`
  - Stress fixture benchmark showing pan/zoom spatial index rebuild count `0` after warmup and no stale `972 ms` metric.
- Non-goals: Do not change edge feature semantics or selection/hit-test behavior.
- Packetization notes: This is the highest-priority hot-path code packet.

### T05 Frame Scheduler Redraw Budget
- Goal: Reduce flushed frames and redraw requests per interaction sample to near one visual update per display frame.
- Preconditions: `T04` prevents index rebuilds from dominating frame metrics.
- Conservative write scope:
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasFrameScheduler.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInputLayers.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasViewportController.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasSceneState.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeDelegate.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
  - `tests/test_graph_canvas_frame_coalescing.py`
  - `tests/test_graph_surface_input_contract.py`
  - `tests/test_graph_surface_input_inline.py`
- Deliverables:
  - Add a scheduler budget model: one pending viewport transform, one pending edge refresh, one pending grid/minimap update, and one pending overlay sync per frame.
  - Coalesce duplicate edge redraw requests by reason and target revision.
  - Prevent edge redraw requests from recursively scheduling additional frame flushes in the same interaction sample.
  - Add an idle or debounce threshold for expensive exact edge refresh after continuous pan/zoom.
  - Add metrics for raw input events, unique scheduled reasons, dropped duplicate redraws, actual flushes, and over-budget frames.
  - Acceptance gate: p95 flushed frames per pan/zoom sample must fall sharply from `155-157`; set the first target to `<10`, then tighten after measurement.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest tests/test_graph_canvas_frame_coalescing.py tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_inline.py --ignore=venv -q`
  - Stress benchmark proving redraw/flush counts fall without losing final viewport position.
- Non-goals: Do not change final pan/zoom behavior, selection, snap, undo, or drag commit semantics.
- Packetization notes: Depends on `T04`; otherwise edge index rebuilds can hide scheduler improvements.

### T06 Transform-First Live Interaction Path
- Goal: Make pan and zoom visually immediate by transforming the current scene while deferring expensive exact snapshot work until idle or a meaningful viewport boundary.
- Preconditions: `T05` budget counters exist.
- Conservative write scope:
  - `ea_node_editor/ui_qml/components/GraphCanvas.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasRootLayers.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasWorldLayer.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasFrameScheduler.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeCanvasLayer.qml`
  - `ea_node_editor/ui_qml/viewport_bridge.py`
  - `tests/test_graph_canvas_frame_coalescing.py`
  - `tests/test_graph_canvas_viewport_virtualization.py`
- Deliverables:
  - During pan/zoom, update world transform immediately and reuse the previous visible edge snapshot set.
  - Recompute visible node and edge snapshots only when crossing a padded viewport tile/bucket or after interaction idle.
  - Preserve full-fidelity steady state after the interaction settles.
  - Keep minimap viewport rectangle live; static minimap graph representation should not rebuild during pan.
  - Keep context menus and hit testing correct by forcing a settle refresh before actions that need exact geometry.
- Verification:
  - Viewport virtualization tests.
  - Frame coalescing tests.
  - Display-attached benchmark comparing pan/zoom p95 before and after.
- Non-goals: Do not hide edges, grid, minimap, labels, or node surfaces. This is a scheduling/data freshness change, not a feature removal.
- Packetization notes: This is the main architecture escalation after P01-P10.

### T07 Node Drag Fast Path
- Goal: Reduce node-drag p95 from the current `537-1121 ms` range while preserving exact final movement and incident-edge feedback.
- Preconditions: `T04` and `T05` are complete.
- Conservative write scope:
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasNodeDelegate.qml`
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasSceneState.qml`
  - `ea_node_editor/ui_qml/components/graph/GraphNodeHostGestureLayer.qml`
  - `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeSnapshotCache.js`
  - `tests/test_graph_canvas_frame_coalescing.py`
  - `tests/test_edge_snapshot_spatial_index.py`
- Deliverables:
  - Keep selected node motion immediate via local transform/drag offset.
  - Update incident visible edge previews at frame cadence only.
  - Defer non-incident edge crossing metadata and label layout until idle/release.
  - Commit final graph coordinates once on release, preserving undo and snap behavior.
  - Add metrics separating local drag visual latency, incident-edge refresh time, and final commit time.
- Verification:
  - Drag final-coordinate tests.
  - Edge incident refresh tests.
  - Stress benchmark for node drag.
- Non-goals: Do not remove live incident-edge feedback or alter final model state.
- Packetization notes: Can run after `T05`; best after `T06` if shared scheduler APIs change.

### T08 Load And Canvas Setup Performance
- Goal: Bring load/setup below the `REQ-PERF-003` target and reduce first usable canvas time.
- Preconditions: Interaction work can proceed independently; this task owns load/setup.
- Conservative write scope:
  - `ea_node_editor/ui/perf/performance_harness.py`
  - `ea_node_editor/persistence/serializer.py`
  - `ea_node_editor/persistence/project_codec.py`
  - `ea_node_editor/ui_qml/graph_scene/state_support.py`
  - `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
  - `ea_node_editor/ui_qml/graph_canvas_visible_model.py`
  - `ea_node_editor/ui_qml/graph_canvas_viewport_index.py`
  - `ea_node_editor/nodes/*` only if registry/node definition loading is measured as a load bottleneck
  - `tests/test_track_h_perf_harness.py`
- Deliverables:
  - Break `project_graph_load_ms` into serializer parse, migration, registry construction, project conversion, scene bridge population, visible-index build, edge-index build, and first-frame setup.
  - Break `canvas_setup_ms` into QML load, root binding, node model attach, edge model attach, initial visible model, initial edge snapshot, grid/minimap setup, and first rendered frame.
  - Batch bridge/model reset signals during initial load.
  - Delay non-visible node surface payload construction until the node becomes visible.
  - Build edge spatial index once during load and reuse it for first interaction.
  - Acceptance gate: real fixture load p95 `<3000 ms`; first usable canvas time must be tracked even if not yet formalized as a requirement.
- Verification:
  - `.\venv\Scripts\python.exe -m pytest tests/test_track_h_perf_harness.py --ignore=venv -q`
  - Stress fixture load benchmark with at least `3` baseline runs.
- Non-goals: Do not weaken `.cxproj` persistence compatibility or graph invariants.
- Packetization notes: Can run in parallel with interaction tasks if write scopes stay separate.

### T09 Display-Attached Proof And GPU Diagnostics
- Goal: Produce accepted desktop evidence after the actual fixes, not just offscreen/software artifacts.
- Preconditions: At least `T04` through `T07` complete; `T08` if claiming load success.
- Conservative write scope:
  - `ea_node_editor/ui/perf/performance_harness.py`
  - `scripts/profile_canvas_lag.py`
  - `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md`
  - `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md`
  - `artifacts/graph_canvas_stress_1200_display_final/**`
- Deliverables:
  - Run display-attached Windows benchmark with `qquickview_container` plus `d3d11`.
  - Capture `QSG_INFO=1`, active graphics API, render loop, DPR, software fallback status, and host kind.
  - Include screenshot or short capture directive for manual proof when practical.
  - Compare against `qquickwidget` only as regression context; do not let `qquickwidget` parity block the accepted Windows default unless product wants both hosts supported.
- Verification:
  - Display-attached benchmark must not use `QT_QPA_PLATFORM=offscreen`.
  - Final report must mark `display_attached_observed=True`.
- Non-goals: Do not use offscreen/software evidence as final performance acceptance.
- Packetization notes: This is the closeout evidence packet for interaction fixes.

### T10 Conditional Native Edge Renderer
- Goal: Escalate to a native or retained scenegraph edge renderer only if `T04` through `T07` still leave edge/frame cadence above target.
- Preconditions: Diagnostics after scheduler and transform-first fixes still show edge rendering as the measured dominant bottleneck.
- Conservative write scope:
  - New module under `ea_node_editor/ui_qml/native_rendering/` or `ea_node_editor/ui/graph_rendering/`
  - `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
  - `ea_node_editor/ui_qml/components/graph/EdgeCanvasLayer.qml`
  - `tests/test_graph_canvas_native_renderer.py`
  - `tests/test_edge_snapshot_spatial_index.py`
- Deliverables:
  - Prototype a retained edge draw path for visible/active edges only.
  - Prefer true Qt Quick scenegraph geometry or a compiled plugin if Python cannot safely expose the required scenegraph primitives.
  - Keep QML fallback for CI/offscreen.
  - Preserve edge labels, selection, hover, preview, crossing gaps, execution styling, hit testing, and theme changes.
- Verification:
  - Native renderer tests.
  - A/B display benchmark proving native edge path wins and preserves parity.
- Non-goals: No full graph-scene rewrite. No native grid work unless new metrics show grid dominance.
- Packetization notes: Conditional escalation only; current metrics point more strongly at frame cadence and index rebuilds.

## Work Packet Conversion Map
1. `P00 Post-Closeout Bootstrap`: `T01`, status/evidence sync and packet window creation.
2. `P01 Fixture And Acceptance Truth`: `T02` plus `T03` if kept together.
3. `P02 Edge Spatial Index Rebuild Fix`: `T04`.
4. `P03 Frame Scheduler Redraw Budget`: `T05`.
5. `P04 Transform-First Pan Zoom`: `T06`.
6. `P05 Node Drag Fast Path`: `T07`.
7. `P06 Load And Canvas Setup`: `T08`.
8. `P07 Display GPU Proof`: `T09`.
9. `P08 Conditional Native Edge Renderer`: `T10` only if measured evidence still requires it.

## Test Plan
- Use the project virtual environment first: `.\venv\Scripts\python.exe`.
- Core focused tests:
  - `.\venv\Scripts\python.exe -m pytest tests/test_track_h_perf_harness.py tests/test_traceability_checker.py --ignore=venv -q`
  - `.\venv\Scripts\python.exe -m pytest tests/test_edge_snapshot_spatial_index.py tests/test_graph_canvas_frame_coalescing.py --ignore=venv -q`
  - `.\venv\Scripts\python.exe -m pytest tests/test_graph_canvas_viewport_virtualization.py --ignore=venv -q`
  - `.\venv\Scripts\python.exe -m pytest tests/test_graph_surface_input_contract.py tests/test_graph_surface_input_inline.py --ignore=venv -q`
- Guardrail tests:
  - `.\venv\Scripts\python.exe .\scripts\run_verification.py --mode fast`
  - `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m unittest tests.test_graph_surface_input_contract tests.test_graph_surface_input_inline tests.test_passive_graph_surface_host tests.test_passive_image_nodes -v; Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue`
  - `.\venv\Scripts\python.exe .\scripts\check_traceability.py`
  - `.\venv\Scripts\python.exe .\scripts\check_markdown_links.py`
- Benchmark gates:
  - Offscreen generated fixture is regression-only.
  - Real fixture display-attached benchmark is required for acceptance.
  - Windows accepted path should use `qquickview_container` plus Direct3D 11 unless a later packet proves a better default.
- Performance targets:
  - `REQ-PERF-002`: pan and zoom p95 `<=33 ms` on the actual `GraphCanvas.qml` path.
  - Node-drag target: use `<=50 ms` p95 as the temporary escalation gate until a formal requirement is added.
  - `REQ-PERF-003`: project+graph load p95 `<3000 ms`.
  - Frame interval without readback: target `<=33 ms` p95 for display-attached acceptance.

## Assumptions
- `origin/main` through `d84067d8` is the completed stress closeout baseline.
- The current local checkout is dirty and behind `origin/main`; do not overwrite or discard local work while adopting this plan.
- The real `examples/stress_1200_nodes.cxproj` exists in the user workspace but is ignored by `*.cxproj`, so clean worktrees do not contain it unless the plan fixes fixture handling.
- Generated fallback evidence is useful for regression but not enough to prove the user's real stress case.
- The prior visible-node optimization worked. Do not spend the next packet reworking visible-model query paths unless new metrics contradict the current `~0.1 ms` p95 evidence.
- The prior grid/minimap work is not the measured limiter. Do not start native grid work unless new metrics show grid dominance.
- The app must remain zero-loss in steady state. Temporary live-interaction deferral is acceptable only when the final settled state is exact and the user-visible workflow remains complete.
