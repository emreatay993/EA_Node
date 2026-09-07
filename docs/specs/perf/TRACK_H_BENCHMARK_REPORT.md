# Track H Benchmark Report

- Updated: `2026-07-14`
- Evidence Status: `COREX_GRAPH_MUTATION_CHURN_REMEDIATION` closeout adds a fresh current-branch graph-mutation proof under `artifacts/corex_graph_mutation_churn_closeout`, with p50/p95 mutation latency, dirty publication counts, and churn counters for the current checked-in stress fixture. `GRAPH_CANVAS_PERFORMANCE` `P01` added zero-loss baseline diagnostics for renderer/backend/host metadata, no-readback frame intervals, and feature-parity snapshots. `GRAPH_CANVAS_MUTATION_LATENCY_PERFORMANCE` `P08` publishes the final real stress-1200 mutation-latency evidence, baseline comparison, and empirical offscreen/software regression thresholds under `artifacts/graph_canvas_mutation_latency_final`. `GRAPH_CANVAS_STRUCTURAL_EDGE_DELTA_PERFORMANCE` `P05` publishes final structural edge delta real stress-1200 evidence, P07/P01/P04/P05 comparison, conservative same-machine offscreen/software guardrails, and residual bottlenecks under `artifacts/graph_canvas_structural_edge_delta_final`. `GRAPH_CANVAS_UNDO_REDO_DELTA_PUBLICATION_PERFORMANCE` `P02` publishes final undo/redo delta publication evidence, P04/P01/P02 comparison, supported-history targeted publication thresholds, and residual risks under `artifacts/graph_canvas_undo_redo_delta_publication_final`. `GRAPH_CANVAS_STRESS_1200_GPU_PERFORMANCE` `P01` makes the canonical real stress fixture checked-in evidence, requires `--stress-fixture real`, and records prior stress closeout as packet-pass/performance-fail. `GRAPH_CANVAS_STRESS_1200_GPU_PERFORMANCE` `P02` adds explicit `display_diagnostics`, `packet_verification_result`, and `performance_acceptance_result` fields and refuses display acceptance for offscreen/software captures. `GRAPH_CANVAS_STRESS_1200_GPU_PERFORMANCE` `P10` publishes the display-attached Windows/D3D11 real-fixture final proof and keeps the remaining `REQ-PERF-002` failure explicit. `GRAPH_CANVAS_STRESS_1200` `P10` remains historical closeout/default evidence.
- Snapshot Command:
  `.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --scenario graph_mutations --stress-fixture real --load-iterations 1 --interaction-samples 10 --baseline-runs 3 --report-dir artifacts/graph_canvas_undo_redo_delta_publication_final`
- Canonical Artifact Paths: `artifacts/graph_canvas_perf_docs/TRACK_H_BENCHMARK_REPORT.md`, `artifacts/graph_canvas_perf_docs/track_h_benchmark_report.json`
- Structural edge delta harness-isolation artifacts: `artifacts/graph_canvas_structural_edge_delta_harness_isolation/TRACK_H_BENCHMARK_REPORT.md`, `artifacts/graph_canvas_structural_edge_delta_harness_isolation/track_h_benchmark_report.json`
- Windows Desktop Exit Gate: `PASS` on `2026-03-21`; desktop-reference artifacts: `artifacts/graph_canvas_interaction_perf_p09_desktop_reference/TRACK_H_BENCHMARK_REPORT.md`, `artifacts/graph_canvas_interaction_perf_p09_desktop_reference/track_h_benchmark_report.json`
- Current Host Default: Windows display-attached launches default to `qquickwidget` plus Direct3D 11 when no environment override is set. `qquickview_container` plus Direct3D 11 remains available as an explicit A/B override; the composited canvas path remains the default for native viewer overlays.

## 2026-07-14 Node Insertion Latency Contract

The Track H harness now exposes `--scenario node_insertions`. It measures from confirmed insertion dispatch, including synchronous undo capture, until every inserted active-scope primary `graphNodeCard` has visible non-zero bounds and a later `QQuickWindow.afterRendering` callback completes. It does not call `grabWindow()` or capture a screenshot inside the timed interval, does not wait for heavy embedded content, and does not require nested child delegates that are outside the active scope. The group-backdrop input helper is reported as a diagnostic and does not gate completion.

- Fixed profiles: `ordinary_node`, `group_backdrop`, `current_creation_profile` (`core.python_script`), `small_custom_workflow`, and `nested_custom_workflow`.
- Default sampling: `3` unmeasured warmups per profile, then a `40`-sample measured budget balanced round-robin across the five profiles.
- Report schema: top-level `node_insertion_benchmark`, raw `samples`, per-profile `dispatch_to_model_commit_ms` and `all_primary_delegates_presented_ms` sample arrays with p50/p95 summaries, `display_validity`, and `acceptance_result`.
- Acceptance: each profile must have `all_primary_delegates_presented_ms.p95 < 100 ms`. The gate is valid only on display-attached Windows with D3D11 and no software fallback. Offscreen/minimal/software results are marked `INVALID`, not pass or fail evidence. CI checks schema and threshold logic only; it does not apply a wall-clock timing gate.
- Scope limit: node-library drag travel and quick-insert open/filter/selection time remain outside this canvas-side benchmark. The measurement begins at the confirmed dispatch shared by those insertion paths.
- Normal fixture command:
  `.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --scenario node_insertions --nodes 200 --edges 320 --seed 1337 --node-insertion-samples 40 --node-insertion-warmup-samples 3 --baseline-runs 1 --baseline-mode interactive --qt-platform windows --qsg-rhi-backend d3d11 --report-dir artifacts/perf_benchmarks/node_insert_typical`
- Stress fixture command:
  `.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --scenario node_insertions --stress-fixture real --node-insertion-samples 40 --node-insertion-warmup-samples 3 --baseline-runs 1 --baseline-mode interactive --qt-platform windows --qsg-rhi-backend d3d11 --report-dir artifacts/perf_benchmarks/node_insert_stress`

Current-host display evidence was captured with the normal `200`-node / `320`-edge fixture under `artifacts/node_insertion_windows_normal_balanced_40` and the synthetic `1,200`-node / `1,920`-edge fixture under `artifacts/node_insertion_windows_stress_balanced_40`. Both runs used `qquickwidget`, Direct3D 11, three warmups per profile, and a balanced 40-sample measured budget. Both are valid display-attached captures and both miss the strict target:

| Profile | Normal p50 / p95 | 1,200-node p50 / p95 |
|---|---:|---:|
| Ordinary node | `295.1 / 334.6 ms` | `560.4 / 657.5 ms` |
| Group backdrop | `465.0 / 489.7 ms` | `750.7 / 1,121.7 ms` |
| Current creation profile | `270.7 / 371.8 ms` | `545.2 / 768.0 ms` |
| Small custom workflow | `969.2 / 1,133.6 ms` | `5,904.2 / 9,186.8 ms` |
| Nested custom workflow | `230.0 / 470.2 ms` | `616.0 / 719.3 ms` |

The corresponding no-readback frame-interval p95 values were `137.2 ms` and `103.2 ms`, already above the insertion target on this host. A focused profile of the stress small-workflow case attributed most model-commit cost to the required selection notification and Qt/QML publication; history capture was smaller.

A second safe-gains pass now defers insertion selection notification until the new visible rows are published, reuses those rows for selection membership, and applies validated pure additions to endpoint/minimap projections plus the retained QML edge payload overlay. A matched 10-sample Windows/D3D11 diagnostic reduced small-workflow dispatch p95 from `952.0 ms` to `122.9 ms` and presented p95 from `1,259.8 ms` to `359.8 ms`; with only two measured samples per profile, this is directional A/B evidence rather than retained acceptance evidence. The subsequent balanced 40-sample runs overlapped another agent's test workload. The stress run's unrelated graph-load time reached `12,534.2 ms` and its no-readback frame p95 reached `682.6 ms`, so those concurrent-load reports remain diagnostic and do not replace the retained table above. History timing and semantics are unchanged.

## 2026-07-13 Animated Media Baseline

The animated-media harness reuses the real canvas with deterministic static, multi-frame GIF, single-frame GIF, corrupt GIF, and animated WebP fixtures. Both requested three-run offscreen/software captures passed the animation policy: supported visible animators were instantiated lazily, and active playback stayed at zero while every panel was idle. Raw reports are retained locally under `artifacts/gif_animation_baseline_20` and `artifacts/gif_animation_baseline_100`.

- Commands:
  - `.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --scenario animated_media --nodes 20 --edges 0 --baseline-runs 3 --qt-platform offscreen --qsg-rhi-backend software --report-dir artifacts/gif_animation_baseline_20`
  - `.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --scenario animated_media --nodes 100 --edges 0 --baseline-runs 3 --qt-platform offscreen --qsg-rhi-backend software --report-dir artifacts/gif_animation_baseline_100`

| Panels | Run | Process CPU | RSS end (bytes) | Pan + zoom p95 (ms) |
|---:|---|---:|---:|---:|
| 20 | `run_01` | 116.116% | 896,339,968 | 143.596 |
| 20 | `run_02` | 115.877% | 929,476,608 | 150.258 |
| 20 | `run_03` | 115.866% | 567,058,432 | 172.971 |
| 100 | `run_01` | 102.056% | 514,719,744 | 486.040 |
| 100 | `run_02` | 93.019% | 539,447,296 | 426.415 |
| 100 | `run_03` | 97.522% | 478,203,904 | 1,086.144 |

- Median report facts: 20 panels instantiated `3` visible-budget animators and 100 panels instantiated `2`; both reports had `1` visible animated panel, `0` actively playing panels, and `animation_policy_pass=true` while idle.
- `packet_verification_result=PASS` for both sizes. `performance_acceptance_result=FAIL` is expected for this regression-only capture because it is offscreen/software and the measured interaction p95 exceeds the existing `33 ms` display gate. Display-attached Windows QA remains required for release acceptance.

## 2026-07-11 Internal Performance Program Evidence

The canonical retained interpretation is [COREX Internal Performance Improvement QA Matrix](COREX_INTERNAL_PERFORMANCE_IMPROVEMENT_QA_MATRIX.md). Important numeric evidence is embedded there because the raw audit artifacts are ignored build evidence rather than committed spec files.

- Formal display source: same-checksum Windows `qquickwidget` / Direct3D 11, display attached, no software fallback, zero-loss parity.
- Formal single-node full-gesture p95: `52.404 -> 47.811 ms` (`8.8%` better), **FAIL** required `20%`.
- Formal aggregate-frame p95: `93.004 -> 91.327 ms` (`1.8%` better), **FAIL** required `20%`; `REQ-PERF-002` remains failed at `91.327 > 33 ms`.
- Pan/zoom guardrails pass: pan is `102.9%` of baseline, zoom `85.5%`, and combined pan/zoom `90.6%`.
- Selected three-node full gesture `225.326 -> 124.349 ms` and steady offset `37.124 -> 0.156 ms` are supplemental diagnostics only. First offset and selected-frame results still fail and the selected control does not overwrite formal acceptance.
- Harness attribution keeps state-side `visible_node_model_update_ms` as the sole visible-publication source. Forced exact refresh, Qt event drain, render callback, readback, and post-readback drain use separate non-additive phase keys.
- Multi-offset drag reporting uses `12` offsets and reports first offset, steady-offset p95, full-gesture wall, and end/clear separately. The legacy single-offset metric remains continuity evidence only. Baselines without the post-`P06` membership counter report explicit unsupported/null values; supported builds require exactly one freeze.
- The `R05` process-isolated structural proof passes create/remove/delete payload ratios `0.650 / 0.306 / 0.609`, with zero structural fallbacks/reindexes and exact dirty/publication parity.
- The authoritative fixture checksum for this program is `e1aa111b9bfdf88a14e19c24da15e0ea71f04428866a051326d353207118541c`. Older retained hashes are cross-fixture historical context only.

## Benchmark Contract

- `ea_node_editor.ui.perf.performance_harness` is the canonical import and module entry point for Track H. It instantiates `ea_node_editor/ui_qml/components/GraphCanvas.qml` for pan/zoom timings and records the render path, viewport size, Qt version, `QT_QPA_PLATFORM`, `QT_QUICK_BACKEND`, `QSG_RHI_BACKEND`, `QSG_RENDER_LOOP`, active `QSGRendererInterface.GraphicsApi`, QML host kind, screen DPR, effective window DPR, sample counts, active `scenario`, `media_surface_count`, and whether `QQuickWindow.grabWindow()` readback is included in every report.
- Current reports expose a top-level `display_diagnostics` payload with Qt platform, display-attached status, active graphics API, RHI backend, render loop, host kind, DPR, software fallback status, readback inclusion, and `QSG_INFO` capture status. They also split packet structural success into `packet_verification_result` and actual benchmark target success into `performance_acceptance_result`; offscreen/minimal or software-fallback runs cannot report display acceptance.
- Current reports also expose a top-level `mutation_benchmark_contract` payload. It reserves mutation scenarios `rename_node`, `drag_node_commit`, `drag_multi_selection_commit`, `create_edge`, `remove_edge`, `delete_node_with_incident_edges`, and `undo_redo`, and defines schema fields for mutation wall-clock samples, per-phase timings, fixture checksum, graph size, dirty node/edge counts, command/graph-delta/scene payload sizes, and first-frame-after-mutation timing. P08 final evidence adds `mutation_closeout_thresholds` to the final artifact JSON and records empirical offscreen/software regression thresholds for the real stress-1200 fixture.
- `node_insertions` reports are separate from readback-inclusive mutation timing. Their completion callback is `QQuickWindow.afterRendering`, their measured interval excludes screenshots/readback and heavy-content readiness, and their `<100 ms` p95 result is valid only on display-attached Windows/D3D11.
- Structural edge delta harness-isolation reports add setup evidence to every mutation sample: setup wall-clock samples, setup phase timings, setup dirty node/edge counts, and `setup_excluded_from_mutation_timing=true`. Mutation wall-clock, mutation phase timings, mutation dirty counts, payload sizes, and first-frame timing remain the isolated mutation-path evidence.
- Structural edge delta final reports use the same graph-mutation schema as P08/P01 and publish empirical offscreen/software guardrails in this document for `create_edge`, `remove_edge`, `delete_node_with_incident_edges`, and `undo_redo`. Undo/redo delta publication final reports use the same schema and publish supported-history targeted-publication guardrails for the `undo_redo` benchmark path. The JSON artifacts remain measured harness output; threshold interpretation is documented here and enforced by `tests/test_track_h_perf_harness.py`.
- Fixture-backed runs use `--project-path`, `--workspace-id`, or `--stress-fixture real` to load `.cxproj` project data through `JsonProjectSerializer.load()`. Real stress mode targets `examples/stress_1200_nodes.cxproj` and workspace `ws_perf_h` and fails if that canonical fixture is absent.
- Stress fixture reports include project path, workspace id, node count, edge count, node type histogram, scene bounds, renderer/backend/host/DPR facts, readback inclusion, no-readback frame interval, visible delegate/edge counts, edge snapshot and grid timings, frame-scheduler coalescing counters, overlay sync timing when available, and node-drag p95.
- Deterministic pan/zoom and node-drag timings still include `QQuickWindow.grabWindow()` readback. `frame_interval_ms_without_readback` is a separately labeled `QQuickWindow.afterRendering` interval metric used to distinguish render cadence from readback-inclusive wall-clock samples.
- Full-fidelity zero-loss reports include a `Feature Parity Snapshot` for grid, minimap, node shadows (excluding Groups, which have no shadow by design), edge-label simplification, port labels, edge crossing style, embedded media count/preview states, and execution visualization state. The snapshot fails/flags a full-fidelity report when required canvas features are hidden or simplified.
- The canonical heavy-media snapshot uses generated local PNG/PDF fixtures plus built-in image/PDF panels to exercise the real `GraphCanvas.qml` render path and writes to `artifacts/graph_canvas_perf_docs`.
- Historical same-machine offscreen, explicit node-drag control, and Windows desktop-reference metrics remain summarized below; new runs use the single current rendering path.
- The prior P10 host candidate decision used display-attached Windows/D3D11 stress evidence from `docs/specs/work_packets/graph_canvas_stress_1200/P01_P09_integrated_display_d3d11_benchmark.md`: `qquickview_container` was faster than `qquickwidget`, but both still failed the stress closeout targets and the candidate host remains opt-in.
- The current GPU-performance P10 final proof uses `artifacts/graph_canvas_stress_1200_display_final` as the display-attached Windows/D3D11 real-fixture artifact. It passes display eligibility, zero-loss parity, and `REQ-PERF-003` project+graph load, but fails `REQ-PERF-002` because pan, zoom, node-drag, and no-readback frame p95 remain above the `<= 33 ms` target.
- The project+graph load metric still measures serializer/model/bridge setup; it does not wait for a fully rendered `GraphCanvas.qml` frame.
- Use `docs/specs/perf/GRAPH_CANVAS_PERF_QA_MATRIX.md` for the approved rerun commands, the canonical artifact path, and the recorded desktop/manual exit-gate status.

## 2026-06-16 COREX Graph Mutation Churn Remediation Closeout

- Closeout command:
  `.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --scenario graph_mutations --stress-fixture real --load-iterations 1 --interaction-samples 5 --baseline-runs 1 --report-dir artifacts/corex_graph_mutation_churn_closeout`
- Closeout artifact paths:
  - `artifacts/corex_graph_mutation_churn_closeout/TRACK_H_BENCHMARK_REPORT.md`
  - `artifacts/corex_graph_mutation_churn_closeout/track_h_benchmark_report.json`
- Fixture metadata: source kind `real`, project path `examples/stress_1200_nodes.cxproj`, checksum `e1aa111b9bfdf88a14e19c24da15e0ea71f04428866a051326d353207118541c`, workspace `ws_perf_h`, graph `1200` nodes / `1199` edges.
- Result: `packet_verification_result=PASS`; `performance_acceptance_result=FAIL` remains expected because the run is offscreen/software and still fails display-attached `REQ-PERF-002` / `REQ-PERF-003` acceptance. This is same-machine regression and closeout evidence, not desktop release acceptance.
- Comparison policy: the current closeout fixture checksum differs from the older May 2026 Track H mutation baseline checksum (`11ad8f8f79b1621a8cec335a1eee9aa10e94b20b32c16da12c0660e50c3732b7`). The p50 table below is therefore current-checksum closeout proof plus historical context, not a strict same-checksum before/after acceptance table. The older P08/P05/P02 p95 guardrails remain the published historical regression thresholds for their packet sets.

| Scenario | Historical baseline p50 (ms) | Current closeout p50 (ms) | Current closeout p95 (ms) | Current scene publish dirty p50 |
|---|---:|---:|---:|---|
| `rename_node` | 8055.632 | 773.901 | 787.172 | 1 node / 2 edges |
| `drag_node_commit` | 8279.000 | 844.972 | 886.137 | 1 node / 2 edges |
| `drag_multi_selection_commit` | 8255.978 | 697.683 | 950.273 | 3 nodes / 6 edges |
| `create_edge` | 25047.657 | 680.160 | 698.837 | 2 nodes / 1 edge |
| `remove_edge` | 32379.604 | 495.584 | 517.589 | 2 nodes / 1 edge |
| `delete_node_with_incident_edges` | 35037.098 | 965.445 | 1124.152 | 2 nodes / 1 edge |
| `undo_redo` | 23532.072 | 914.707 | 1062.632 | 1 node / 0 edges |

| Scenario | Publication paths in current closeout |
|---|---|
| `rename_node` | `title_payload_delta` |
| `drag_node_commit` | `node_position_delta` |
| `drag_multi_selection_commit` | `node_position_delta` |
| `create_edge` | `edge_topology_delta` |
| `remove_edge` | `edge_topology_delta` |
| `delete_node_with_incident_edges` | `edge_topology_delta` |
| `undo_redo` | `history_title_payload_delta` |

- Churn-counter proof: the current closeout artifact reports `payload_cache_edge_only_reindexes=5` for rename, drag, structural edge, and delete scenarios, with no full-rebuild fallback reason buckets in the covered benchmark samples.
- Residual risks: Group-backdrop/Group-Peek work is intentionally gated at no-membership-change normal-node moves; expanded-backdrop membership flips, collapsed backdrop boundaries, backdrop geometry edits, and active Group Peek cases remain full rebuild unless a later packet proves the spatial diff. History optimization remains Phase 1 only; unsupported replay entries can still use full-rebuild fallback. Autosave, registry pruning, and plot-title reuse have focused correctness coverage, but they are not separately accepted by this Track H display-performance gate.

## 2026-05-09 Mutation Latency P01 Contract

- Contract proof command:
  `.\venv\Scripts\python.exe -m pytest tests/test_track_h_perf_harness.py --ignore=venv -q`
- Report payload: top-level `mutation_benchmark_contract` with `kind=graph_canvas_mutation_latency`, `status=contract_only`, and `threshold_policy=baseline_evidence_only_no_pass_fail_thresholds`.
- Mutation scenarios: `rename_node`, `drag_node_commit`, `drag_multi_selection_commit`, `create_edge`, `remove_edge`, `delete_node_with_incident_edges`, and `undo_redo`.
- Required mutation report field groups:
  - Identity: `scenario`, `operation_iteration`
  - Wall-clock samples: `mutation_wall_clock_samples_ms`
  - Phase timings: `phase_timings_ms`
  - Fixture metadata: `fixture_checksum_sha256`, `graph_size`
  - Dirty counts: `dirty_node_count`, `dirty_edge_count`
  - Payload sizes: `command_payload_bytes`, `graph_delta_payload_bytes`, `scene_payload_bytes`
  - First frame after mutation: `first_frame_after_mutation_ms`
- Acceptance policy: baseline data remains evidence only in P01. The P08 closeout section below populates the fields from real mutation runs and publishes empirical regression thresholds.

## 2026-05-10 Structural Edge Delta P01 Harness Setup Isolation

- Proof command:
  `.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --scenario graph_mutations --stress-fixture real --load-iterations 1 --interaction-samples 5 --baseline-runs 1 --report-dir artifacts/graph_canvas_structural_edge_delta_harness_isolation`
- Artifact paths:
  - `artifacts/graph_canvas_structural_edge_delta_harness_isolation/TRACK_H_BENCHMARK_REPORT.md`
  - `artifacts/graph_canvas_structural_edge_delta_harness_isolation/track_h_benchmark_report.json`
- Harness rule: `create_edge`, `remove_edge`, `delete_node_with_incident_edges`, and `undo_redo` perform their temporary node/edge/history setup before the timed mutation scope. The markdown and JSON reports display setup dirty counts separately from mutation dirty counts so remaining broad mutation dirties stay visible for P02-P04.

## 2026-05-10 Structural Edge Delta P05 Final Thresholds

- Final command:
  `.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --scenario graph_mutations --stress-fixture real --load-iterations 1 --interaction-samples 10 --baseline-runs 3 --report-dir artifacts/graph_canvas_structural_edge_delta_final`
- Final artifact paths:
  - `artifacts/graph_canvas_structural_edge_delta_final/TRACK_H_BENCHMARK_REPORT.md`
  - `artifacts/graph_canvas_structural_edge_delta_final/track_h_benchmark_report.json`
- Comparison sources: P07 pre-structural artifact `artifacts/graph_canvas_mutation_latency_qml_stabilization/track_h_benchmark_report.json`, P01 setup-isolated artifact `artifacts/graph_canvas_structural_edge_delta_harness_isolation/track_h_benchmark_report.json`, and P04 topology artifact `artifacts/graph_canvas_structural_edge_delta_topology/track_h_benchmark_report.json`.
- Fixture metadata: source kind `real`, project path `examples/stress_1200_nodes.cxproj`, checksum `11ad8f8f79b1621a8cec335a1eee9aa10e94b20b32c16da12c0660e50c3732b7`, workspace `ws_perf_h`, graph `1200` nodes / `1199` edges.
- Threshold policy: `p05_structural_edge_delta_empirical_offscreen_guardrails`. These are same-machine offscreen/software regression thresholds for the final structural edge delta artifact, not display-attached release acceptance thresholds. `performance_acceptance_result=FAIL` remains expected because the run is offscreen/software and `REQ-PERF-002` is still above target.

| Scenario | P07 wall p95 (ms) | P01 wall p95 (ms) | P04 wall p95 (ms) | P05 final wall p95 (ms) | P05 vs P07 | P05 vs P04 |
|---|---:|---:|---:|---:|---:|---:|
| `create_edge` | 19293.663 | 4306.293 | 6188.322 | 5270.063 | +72.7% | +14.8% |
| `remove_edge` | 22967.099 | 3116.638 | 4265.277 | 7602.023 | +66.9% | -78.2% |
| `delete_node_with_incident_edges` | 24415.908 | 4723.726 | 5753.606 | 12520.669 | +48.7% | -117.6% |
| `undo_redo` | 18622.137 | 14976.198 | 22761.554 | 32280.323 | -73.3% | -41.8% |

| Scenario | P05 wall p95 (ms) | Threshold max p95 (ms) | Dirty node/edge p95 | Result |
|---|---:|---:|---|---|
| `create_edge` | 5270.063 | 7000 | 2.00 / 1.00 | PASS |
| `remove_edge` | 7602.023 | 8000 | 2.00 / 1.00 | PASS |
| `delete_node_with_incident_edges` | 12520.669 | 13000 | 2.00 / 1.00 | PASS |
| `undo_redo` | 32280.323 | 34000 | 1247.75 / 1208.55 | PASS |

| Scenario | Top residual phases by p95 |
|---|---|
| `create_edge` | `first_frame_after_mutation_ms` 5270.063 ms, `command_dispatch_ms` 4601.392 ms, `scene_publish_ms` 3968.859 ms |
| `remove_edge` | `first_frame_after_mutation_ms` 7602.023 ms, `command_dispatch_ms` 5723.603 ms, `scene_publish_ms` 5542.242 ms |
| `delete_node_with_incident_edges` | `first_frame_after_mutation_ms` 12520.669 ms, `command_dispatch_ms` 8599.060 ms, `scene_publish_ms` 7794.576 ms |
| `undo_redo` | `first_frame_after_mutation_ms` 32280.323 ms, `payload_rebuild_ms` 17016.326 ms, `scene_publish_ms` 11119.208 ms |

- Final classification: ordinary structural edge create/remove/delete paths preserve narrow mutation dirty counts at p95 `2` nodes / `1` edge, but their wall-clock costs remain multi-second and dominated by command dispatch, scene publish, and first-frame completion. `undo_redo` remains broad in this historical P05 artifact at p95 `1247.75` dirty nodes / `1208.55` dirty edges; the later P02 supported-history replay proof below supersedes that broad dirty-publication state for the targeted `history_targeted_node_payload` path only.
- Residual follow-up: create a new packet set for the remaining command-dispatch, scene-publish, first-frame, and broad undo/redo bottlenecks; do not extend this closeout packet with new optimization work.

## 2026-05-11 Undo/Redo Delta Publication P02 Final Thresholds

- Final command:
  `.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --scenario graph_mutations --stress-fixture real --load-iterations 1 --interaction-samples 10 --baseline-runs 3 --report-dir artifacts/graph_canvas_undo_redo_delta_publication_final`
- Final artifact paths:
  - `artifacts/graph_canvas_undo_redo_delta_publication_final/TRACK_H_BENCHMARK_REPORT.md`
  - `artifacts/graph_canvas_undo_redo_delta_publication_final/track_h_benchmark_report.json`
- Comparison sources: P04 topology blocker `artifacts/graph_canvas_structural_edge_delta_topology/track_h_benchmark_report.json`, P01 replay proof `artifacts/graph_canvas_undo_redo_delta_publication_replay/track_h_benchmark_report.json`, and P02 final proof `artifacts/graph_canvas_undo_redo_delta_publication_final/track_h_benchmark_report.json`.
- Fixture metadata: source kind `real`, project path `examples/stress_1200_nodes.cxproj`, checksum `11ad8f8f79b1621a8cec335a1eee9aa10e94b20b32c16da12c0660e50c3732b7`, workspace `ws_perf_h`, graph `1200` nodes / `1199` edges.
- Threshold policy: `p02_undo_redo_delta_publication_empirical_offscreen_guardrails`. These are same-machine offscreen/software regression thresholds for supported undo/redo replay publication, not display-attached release acceptance thresholds. The supported benchmark replay shape is title-history undo/redo that can be refreshed as a targeted node payload. Unsupported history replay entries remain explicit full-rebuild fallback residual risk.

| Evidence | Samples | `undo_redo` wall p95 (ms) | Payload rebuild p95 (ms) | Scene publish p95 (ms) | First-frame p95 (ms) | Dirty publication p95 | Publication path |
|---|---:|---:|---:|---:|---:|---|---|
| P04 topology blocker | 5 | 22761.554 | 13052.378 | 7521.901 | 22761.554 | 1224.00 nodes / 1203.80 edges | not recorded |
| P01 replay proof | 5 | 6560.921 | 1.285 | 4946.789 | 6560.921 | 1.00 node / 0.00 edges | `history_targeted_node_payload` |
| P02 final proof | 10 | 7904.983 | 1.181 | 5519.461 | 7904.983 | 1.00 node / 0.00 edges | `history_targeted_node_payload` |

| Guardrail | P02 observed | Threshold | Result |
|---|---:|---:|---|
| Model dirty p95 | 1.00 node / 0.00 edges | <= 5 nodes / <= 5 edges | PASS |
| Scene-publication dirty p95 | 1.00 node / 0.00 edges | <= 5 nodes / <= 5 edges | PASS |
| Publication path | `history_targeted_node_payload` | targeted history node payload, no full rebuild | PASS |
| Payload rebuild p95 | 1.181 ms | <= 5 ms | PASS |
| Scene publish p95 | 5519.461 ms | <= 6500 ms | PASS |
| Wall and first-frame p95 | 7904.983 ms | <= 8000 ms | PASS |

| Scenario | P02 model dirty p95 | P02 scene publish dirty p95 | Publication path | Top residual phases by p95 |
|---|---:|---:|---|---|
| `undo_redo` | 1.00 node / 0.00 edges | 1.00 node / 0.00 edges | `history_targeted_node_payload` | `first_frame_after_mutation_ms` 7904.983 ms, `scene_publish_ms` 5519.461 ms, `history_apply_ms` 136.727 ms |
| `create_edge` | 0.00 nodes / 1.00 edge | 2.00 nodes / 1.00 edge | `edge_topology_delta` | `first_frame_after_mutation_ms` 4700.280 ms, `command_dispatch_ms` 3506.930 ms, `scene_publish_ms` 2885.346 ms |
| `remove_edge` | 0.00 nodes / 1.00 edge | 2.00 nodes / 1.00 edge | `edge_topology_delta` | `first_frame_after_mutation_ms` 4135.553 ms, `command_dispatch_ms` 3301.088 ms, `scene_publish_ms` 3195.051 ms |
| `delete_node_with_incident_edges` | 1.00 node / 1.00 edge | 2.00 nodes / 1.00 edge | `edge_topology_delta` | `first_frame_after_mutation_ms` 6294.662 ms, `command_dispatch_ms` 3951.626 ms, `scene_publish_ms` 3556.243 ms |

- Final classification: P02 closes the P04 `undo_redo` dirty-publication blocker for the supported benchmark history replay path. The same-machine offscreen/software final artifact reduces `undo_redo` dirty publication from p95 `1224` nodes / `1203.8` edges to `1` node / `0` edges and keeps payload rebuild p95 at `1.181 ms`, so the remaining `undo_redo` wall cost is no longer caused by full graph payload rebuild publication.
- Phase-attribution handoff: the residual supported replay cost is scene-publish and first-frame dominated (`scene_publish_ms` p95 `5519.461 ms`, `first_frame_after_mutation_ms` p95 `7904.983 ms`) in offscreen/software evidence. P01 adds explicit first-frame attribution fields so later packets can separate graph mutation/history apply, Python scene publication, visible-model sync, render wait, readback/grab, and host-composition residual cost instead of moving time between ambiguous buckets.
- Residual risks: `performance_acceptance_result=FAIL` remains expected because the final run uses `QT_QPA_PLATFORM=offscreen`, Qt Quick software rendering, software RHI, and `qquickwidget`. Scene publish and first-frame/host composition still dominate the measured wall time. Unsupported history replay entries still fall back to full scene rebuild and require a new packet set if they become release-blocking.

## 2026-05-11 Scene Publish Phase Attribution P01

- Final command:
  `.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --scenario graph_mutations --stress-fixture real --load-iterations 1 --interaction-samples 5 --baseline-runs 1 --report-dir artifacts/graph_canvas_scene_publish_phase_attribution`
- Final artifact paths:
  - `artifacts/graph_canvas_scene_publish_phase_attribution/TRACK_H_BENCHMARK_REPORT.md`
  - `artifacts/graph_canvas_scene_publish_phase_attribution/track_h_benchmark_report.json`
- Fixture metadata: source kind `real`, project path `examples/stress_1200_nodes.cxproj`, checksum `11ad8f8f79b1621a8cec335a1eee9aa10e94b20b32c16da12c0660e50c3732b7`, workspace `ws_perf_h`, graph `1200` nodes / `1199` edges.
- Measurement semantics: `first_frame_after_mutation_ms` remains readback-inclusive and now carries explicit first-frame phase attribution buckets for graph mutation/history apply, Python scene payload rebuild, Python scene publish, visible-model sync, render wait, readback/grab, post-readback event drain, and residual unattributed first-frame time.

| Scenario | First-frame p95 (ms) | Scene publish p95 (ms) | Visible sync p95 (ms) | Render wait p95 (ms) | Readback p95 (ms) | Post-readback drain p95 (ms) | Unattributed p95 (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `rename_node` | 2605.138 | 2075.722 | 335.220 | 159.251 | 2.056 | 462.025 | 0.000 |
| `drag_node_commit` | 3881.107 | 2373.825 | 889.068 | 166.393 | 2.184 | 407.805 | 0.000 |
| `drag_multi_selection_commit` | 4137.203 | 2473.580 | 588.513 | 269.646 | 1.379 | 617.885 | 0.000 |
| `create_edge` | 3868.648 | 2546.055 | 307.464 | 22.558 | 1.364 | 502.518 | 0.000 |
| `remove_edge` | 3188.039 | 2532.662 | 287.822 | 27.611 | 1.193 | 518.752 | 0.000 |
| `delete_node_with_incident_edges` | 4709.554 | 2664.362 | 881.196 | 302.340 | 1.483 | 521.973 | 0.000 |
| `undo_redo` | 5539.551 | 4043.821 | 780.853 | 309.188 | 3.081 | 965.749 | 39.821 |

- Final classification: P01 publishes phase attribution before optimization. The run confirms readback itself is small in this offscreen/software sample (`undo_redo` readback p95 `3.081 ms`) while Python scene publish and host-side visible-sync/event-drain phases explain most of the measured first-frame cost.
- Residual risks: this is a single-baseline, same-machine offscreen/software attribution proof, not display-attached acceptance. Later packets must reduce the targeted scene-publish/QML-update phases without treating readback-inclusive first-frame time as a direct GPU performance claim.

## 2026-05-10 Mutation Latency P08 Closeout Thresholds

- Final command:
  `.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --scenario graph_mutations --stress-fixture real --load-iterations 1 --interaction-samples 10 --baseline-runs 3 --report-dir artifacts/graph_canvas_mutation_latency_final`
- Final artifact paths:
  - `artifacts/graph_canvas_mutation_latency_final/TRACK_H_BENCHMARK_REPORT.md`
  - `artifacts/graph_canvas_mutation_latency_final/track_h_benchmark_report.json`
- Baseline comparison source: `artifacts/graph_canvas_mutation_latency_baseline/track_h_benchmark_report.json`.
- Fixture metadata: source kind `real`, project path `examples/stress_1200_nodes.cxproj`, checksum `11ad8f8f79b1621a8cec335a1eee9aa10e94b20b32c16da12c0660e50c3732b7`, workspace `ws_perf_h`, graph `1200` nodes / `1199` edges.
- Threshold policy: `p08_empirical_offscreen_regression_guardrails`. These are same-machine offscreen/software regression thresholds for the final artifact, not display-attached release acceptance thresholds.

| Scenario | Baseline wall p95 (ms) | Final wall p95 (ms) | Threshold max p95 (ms) | Improvement vs P03 | Result |
|---|---:|---:|---:|---:|---|
| `rename_node` | 9350.770 | 3809.505 | 4500 | 59.3% | PASS |
| `drag_node_commit` | 8415.772 | 5590.535 | 6000 | 33.6% | PASS |
| `drag_multi_selection_commit` | 8683.242 | 5296.380 | 5500 | 39.0% | PASS |
| `create_edge` | 25351.172 | 23421.623 | 25000 | 7.6% | PASS |
| `remove_edge` | 34474.409 | 29652.571 | 31000 | 14.0% | PASS |
| `delete_node_with_incident_edges` | 36337.181 | 31814.525 | 34000 | 12.4% | PASS |
| `undo_redo` | 23658.702 | 20627.377 | 22000 | 12.8% | PASS |

| Scenario | Top residual phases by p95 |
|---|---|
| `rename_node` | `first_frame_after_mutation_ms` 3809.505 ms, `command_dispatch_ms` 2668.462 ms, `scene_publish_ms` 2570.661 ms |
| `drag_node_commit` | `first_frame_after_mutation_ms` 5590.535 ms, `command_dispatch_ms` 3522.749 ms, `scene_publish_ms` 3010.135 ms |
| `drag_multi_selection_commit` | `first_frame_after_mutation_ms` 5296.380 ms, `command_dispatch_ms` 3808.325 ms, `scene_publish_ms` 3266.552 ms |
| `create_edge` | `first_frame_after_mutation_ms` 23421.623 ms, `command_dispatch_ms` 20508.472 ms, `scene_publish_ms` 10288.122 ms |
| `remove_edge` | `first_frame_after_mutation_ms` 29652.571 ms, `command_dispatch_ms` 24185.279 ms, `scene_publish_ms` 13736.110 ms |
| `delete_node_with_incident_edges` | `first_frame_after_mutation_ms` 31814.525 ms, `command_dispatch_ms` 24433.432 ms, `scene_publish_ms` 13849.937 ms |
| `undo_redo` | `first_frame_after_mutation_ms` 20627.377 ms, `scene_publish_ms` 9269.066 ms, `payload_rebuild_ms` 8811.573 ms |

- Final classification: the P08 threshold payload passes for all covered mutation scenarios. The artifact still records `performance_acceptance_result=FAIL` because the run is offscreen/software and `REQ-PERF-002` remains above target.
- Residual follow-up: edge create/remove, delete-with-incident-edges, and undo/redo remain dominated by scene publish and payload rebuild paths; P08 closes proof and thresholds only and does not add new optimization work.

## 2026-05-09 GPU Performance P01 Real Fixture Truth

- Real stress fixture command:
  `.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --stress-fixture real --load-iterations 1 --interaction-samples 5 --baseline-runs 1 --report-dir artifacts/graph_canvas_stress_1200_real_baseline`
- Real stress artifact paths:
  - `artifacts/graph_canvas_stress_1200_real_baseline/TRACK_H_BENCHMARK_REPORT.md`
  - `artifacts/graph_canvas_stress_1200_real_baseline/track_h_benchmark_report.json`
- Fixture metadata: source kind `real`, project path `examples/stress_1200_nodes.cxproj`, checksum `11ad8f8f79b1621a8cec335a1eee9aa10e94b20b32c16da12c0660e50c3732b7`, workspace `ws_perf_h`, path exists=`True`, fixture strategy `serializer_project_load`, graph `1200` nodes / `1199` edges, node type histogram `{'core.end': 1, 'core.logger': 1198, 'core.start': 1}`, scene bounds width=`8760.0`, height=`4180.0`.
- Current real-fixture baseline results: load p95=`4162.438 ms`, pan p95=`163.454 ms`, zoom p95=`890.817 ms`, pan+zoom p95=`1036.649 ms`, node-drag control p95=`826.728 ms`, no-readback frame p95=`502.543 ms`.
- Current classification: `GRAPH-CANVAS-ZERO-LOSS`, `REQ-PERF-001`, and `GRAPH-CANVAS-DISPLAY-ACCEPTANCE-SOURCE` pass. `REQ-PERF-002` and `REQ-PERF-003` fail and remain the measured bottleneck baseline for later packets. Prior stress `P10` remains packet-pass/performance-fail history and does not override this real-fixture baseline.

## 2026-05-09 GPU Performance P02 Display Diagnostics

- Display diagnostics command:
  `.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --stress-fixture real --load-iterations 1 --interaction-samples 5 --baseline-runs 1 --capture-qsg-info --report-dir artifacts/graph_canvas_stress_1200_display_diagnostics`
- Display diagnostics artifact paths:
  - `artifacts/graph_canvas_stress_1200_display_diagnostics/TRACK_H_BENCHMARK_REPORT.md`
  - `artifacts/graph_canvas_stress_1200_display_diagnostics/track_h_benchmark_report.json`
- Report contract additions: `display_diagnostics`, `packet_verification_result`, and `performance_acceptance_result` are top-level fields in `track_h_benchmark_report.json` and explicit sections in `TRACK_H_BENCHMARK_REPORT.md`.
- Display acceptance semantics: `packet_verification_result` can pass when required diagnostics are present, but `performance_acceptance_result` remains `FAIL` unless the run is display-attached, avoids Qt Quick software fallback, preserves zero-loss parity, uses an accepted fixture source, meets target scale, and satisfies `REQ-PERF-002` and `REQ-PERF-003`.
- Offscreen/software policy: `QT_QPA_PLATFORM=offscreen` or a software RHI/backend is regression evidence only and must produce a `GRAPH-CANVAS-DISPLAY-ATTACHED` failure instead of claiming desktop/GPU acceptance.
- P02 artifact result: `packet_verification_result=PASS`, `performance_acceptance_result=FAIL`, Qt platform `offscreen`, graphics API `Software`, RHI backend `software`, host `qquickwidget`, `QSG_INFO` capture enabled=`True`, load p95=`4501.470 ms`, pan p95=`331.955 ms`, zoom p95=`312.208 ms`, node-drag p95=`920.167 ms`, no-readback frame p95=`528.022 ms`.

## 2026-05-09 GPU Performance P10 Display Final Proof

- Display-final command:
  `$env:QSG_INFO='1'; .\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --stress-fixture real --qml-host qquickview_container --qsg-rhi-backend d3d11 --qt-platform windows --baseline-mode interactive --load-iterations 1 --interaction-samples 20 --baseline-runs 3 --report-dir artifacts/graph_canvas_stress_1200_display_final; Remove-Item Env:QSG_INFO -ErrorAction SilentlyContinue`
- Display-final artifact paths:
  - `artifacts/graph_canvas_stress_1200_display_final/TRACK_H_BENCHMARK_REPORT.md`
  - `artifacts/graph_canvas_stress_1200_display_final/track_h_benchmark_report.json`
- Display diagnostics: `display_attached=True`, Qt platform `windows`, active graphics API `Direct3D11Rhi` / `Direct3D 11`, RHI backend `d3d11`, host `qquickview_container`, screen DPR=`2.000`, effective window DPR=`2.000`, software fallback active=`False`, `QSG_INFO` capture enabled=`True`.
- Renderer and fixture proof: active edge renderer `retained_qml`, Canvas fallback active=`False`, fixture source `real`, project path `examples/stress_1200_nodes.cxproj`, checksum `11ad8f8f79b1621a8cec335a1eee9aa10e94b20b32c16da12c0660e50c3732b7`, workspace `ws_perf_h`, graph `1200` nodes / `1199` edges, scene bounds width=`8760.0`, height=`4180.0`.
- Final display metrics: load p95=`164.320 ms`, pan p95=`99.602 ms`, zoom p95=`80.825 ms`, pan+zoom p95=`144.564 ms`, node-drag control p95=`315.023 ms`, no-readback frame p95=`322.075 ms`.
- Final requirement classification: `packet_verification_result=PASS`; `GRAPH-CANVAS-DISPLAY-ACCEPTANCE-SOURCE`, `GRAPH-CANVAS-DISPLAY-ATTACHED`, `GRAPH-CANVAS-ZERO-LOSS`, `REQ-PERF-001`, and `REQ-PERF-003` pass; `REQ-PERF-002` fails, so `performance_acceptance_result=FAIL` with blocker `REQ-PERF-002`.

## 2026-05-06 P01 Zero-Loss Baseline Diagnostics

- Full-fidelity target-scale command:
  `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.ui.perf.performance_harness --nodes 1000 --edges 5000 --load-iterations 1 --interaction-samples 10 --baseline-runs 1 --scenario synthetic_exec --report-dir artifacts/graph_canvas_zero_loss_target_scale`
- Full-fidelity heavy-media command:
  `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.ui.perf.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 1 --scenario heavy_media --report-dir artifacts/graph_canvas_zero_loss_heavy_media`
- P01 artifact paths:
  - `artifacts/graph_canvas_zero_loss_target_scale/TRACK_H_BENCHMARK_REPORT.md`
  - `artifacts/graph_canvas_zero_loss_target_scale/track_h_benchmark_report.json`
  - `artifacts/graph_canvas_zero_loss_heavy_media/TRACK_H_BENCHMARK_REPORT.md`
  - `artifacts/graph_canvas_zero_loss_heavy_media/track_h_benchmark_report.json`
- Diagnostic labels now expected in every P01 report: `Renderer Diagnostics`, `Feature Parity Snapshot`, `grabWindow readback included`, `No-readback frame metric`, `frame_interval_ms_without_readback`, `QT_QUICK_BACKEND`, `QSG_RHI_BACKEND`, `QSG_RENDER_LOOP`, `Graphics API`, `QML host kind`, `Screen DPR`, and `Effective window DPR`.
- Current P01 baseline classification: `GRAPH-CANVAS-ZERO-LOSS` passes, while existing `REQ-PERF-002` timing targets remain above threshold and are preserved as baseline risk for later optimization packets.

## 2026-05-07 Stress 1200 Fixture Baseline

- Stress fixture command:
  `.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --stress-fixture real --load-iterations 1 --interaction-samples 20 --baseline-runs 3 --report-dir artifacts/graph_canvas_stress_1200_baseline`
- Stress fixture artifact paths:
  - `artifacts/graph_canvas_stress_1200_baseline/TRACK_H_BENCHMARK_REPORT.md`
  - `artifacts/graph_canvas_stress_1200_baseline/track_h_benchmark_report.json`
- Fixture metadata: source kind `real`, project path `examples/stress_1200_nodes.cxproj`, workspace `ws_perf_h`, path exists=`True`, fixture strategy `serializer_project_load`, graph `1200` nodes / `1199` edges, node type histogram `{'core.end': 1, 'core.logger': 1198, 'core.start': 1}`, scene bounds width=`8760.0`, height=`4180.0`.
- Baseline results: load p95=`4957.117 ms`, pan p95=`2433.845 ms`, zoom p95=`3162.731 ms`, pan+zoom p95=`5465.543 ms`, node-drag control p95=`7073.377 ms`, no-readback frame p95=`3222.286 ms`.
- Current stress baseline classification: `GRAPH-CANVAS-ZERO-LOSS` and `REQ-PERF-001` pass; `REQ-PERF-002` and `REQ-PERF-003` fail and remain the measured bottleneck baseline for later packets. P01 records the existing stress-fixture bottleneck and fixture metadata without optimizing rendering, host/backend defaults, or canvas behavior. Display-attached desktop/GPU validation remains required before final acceptance.

## 2026-05-08 P10 Stress 1200 Closeout

- Final stress fixture command:
  `.\venv\Scripts\python.exe -m ea_node_editor.ui.perf.performance_harness --stress-fixture real --load-iterations 1 --interaction-samples 20 --baseline-runs 3 --report-dir artifacts/graph_canvas_stress_1200_final`
- Final stress artifact paths:
  - `artifacts/graph_canvas_stress_1200_final/TRACK_H_BENCHMARK_REPORT.md`
  - `artifacts/graph_canvas_stress_1200_final/track_h_benchmark_report.json`
- Prior P10 fixture metadata: project path `examples/stress_1200_nodes.cxproj`, workspace `ws_perf_h`, path exists=`False`, fixture strategy `generated_missing_default_stress_fixture`, graph `1200` nodes / `1199` edges, node type histogram `{'core.end': 1, 'core.logger': 1198, 'core.start': 1}`, scene bounds width=`8760.0`, height=`4180.0`. That prior packet remains packet-pass/performance-fail and does not satisfy the current real-fixture acceptance contract.
- Final offscreen/software results: load p95=`4363.226 ms`, pan p95=`330.429 ms`, zoom p95=`348.836 ms`, pan+zoom p95=`647.973 ms`, node-drag control p95=`1121.054 ms`, no-readback frame p95=`547.234 ms`.
- Final zero-loss parity checklist: grid visible=`True`, minimap visible=`True`, node shadows enabled=`True` (Groups have no shadow by design), port labels visible=`True`, edge crossing style=`none`, embedded media surfaces=`0 / 0`, execution visualization active=`False`, simplification flags for grid/minimap/shadows/edge labels all `False`.
- Display-attached host comparison evidence: integrated P01-P09 Windows/D3D11 runs show `qquickview_container` faster than `qquickwidget` with zero-loss parity preserved: pan p95 `206.475 ms` vs `271.380 ms`, zoom p95 `160.113 ms` vs `229.396 ms`, node-drag p95 `537.482 ms` vs `588.314 ms`, no-readback frame p95 `500.265 ms` vs `521.347 ms`, load p95 `7257.051 ms` vs `7682.528 ms`.
- Current stress closeout classification: `GRAPH-CANVAS-ZERO-LOSS` and `REQ-PERF-001` pass; `REQ-PERF-002` and `REQ-PERF-003` fail in both final offscreen proof and display-attached A/B evidence. P10 records the faster qquickview candidate, but current app launches keep `qquickwidget` as the default host for native viewer overlay parity.
- Follow-up renderer direction: native grid work is `NOT NEEDED` based on final grid paint/update timings, but an edge/frame-cadence follow-up is justified by edge snapshot p95 around `43 ms`, edge redraw request p95 above `158`, and no-readback frame p95 still above `500 ms`.

## 2026-03-21 Offscreen Snapshot

- Current reproduction command:
  `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m ea_node_editor.ui.perf.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 3 --scenario heavy_media --report-dir artifacts/graph_canvas_perf_docs`
- The numeric snapshot below is retained from the 2026-03-21 same-machine run; rerun the current command before treating it as current performance.
- Generated (UTC): `2026-03-21T08:21:32.521494+00:00`
- Platform: `Windows-10-10.0.26200-SP0`
- Python: `3.10.0`
- Qt platform: `offscreen`
- Qt Quick backend: `software`
- QSG RHI backend: `software`

### Config

- Synthetic graph: `120` nodes / `320` edges
- Seed: `1337`
- Load iterations: `1`
- Warmup samples: `3`
- Pan/zoom samples: `10`
- Baseline runs: `3`
- Scenario: `heavy_media`
- Node mix: `114` execution / `3` image panels / `3` PDF panels
- Generated fixtures: `3` images / `1` PDFs

### Interaction Benchmark

- Kind: `graph_canvas_qml`
- Render path: `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- Driver: `Single warmed GraphCanvas host using begin/note/finish viewport interaction + ViewportBridge.centerOn/set_zoom and GraphNodeHost.dragOffsetChanged with QQuickWindow.grabWindow()`
- Viewport: `1280` x `720`
- Theme pair: `stitch_dark` / `graph_stitch_dark`
- Scenario: `heavy_media`
- Media surface count: `6`
- Real canvas path: `True`
- Reused steady-state host: `True`

### Metrics (ms)

| Metric | p50 | p95 | Mean | Min | Max |
|---|---:|---:|---:|---:|---:|
| Project + graph load | 67.842 | 67.842 | 67.842 | 67.842 | 67.842 |
| Pan interaction | 80.335 | 97.890 | 81.644 | 70.279 | 103.589 |
| Zoom interaction | 14.530 | 16.657 | 14.771 | 13.503 | 16.728 |
| Pan + zoom (combined) | 94.454 | 112.350 | 96.414 | 84.430 | 118.474 |
| Node-drag control | 30.960 | 48.352 | 36.818 | 28.899 | 48.524 |

### Requirement Check

| Requirement | Result | Details |
|---|---|---|
| REQ-PERF-001 | FAIL | Generated graph size `120` nodes / `320` edges, so this docs-refresh snapshot is below target-scale acceptance coverage |
| REQ-PERF-002 | FAIL | Real GraphCanvas pan p95=`97.890 ms`, zoom p95=`16.657 ms`, node-drag control p95=`48.352 ms` (target `<= 33 ms`) |
| REQ-PERF-003 | PASS | Project+graph load p95=`67.842 ms` (target `< 3000 ms`) |

## Baseline Series

- Mode: `offscreen`
- Tag: `local`
- Scenario: `heavy_media`
- Run count: `3`

| Run | Mode | Load p95 (ms) | Pan p95 (ms) | Zoom p95 (ms) | Pan+Zoom p95 (ms) | Drag p95 (ms) | Qt Platform | Machine |
|---|---|---:|---:|---:|---:|---:|---|---|
| run_01 | offscreen | 76.941 | 97.164 | 15.557 | 111.300 | 47.783 | offscreen | AMD64 |
| run_02 | offscreen | 64.792 | 96.687 | 16.063 | 111.519 | 46.515 | offscreen | AMD64 |
| run_03 | offscreen | 67.842 | 97.890 | 16.657 | 112.350 | 48.352 | offscreen | AMD64 |

### Variance Policy

| Metric | CV Threshold | Range Threshold (ms) | Observed CV | Observed Range (ms) | Result |
|---|---:|---:|---:|---:|---|
| load_p95_ms | 0.25 | 500.0 | 0.0739 | 12.148 | PASS |
| pan_p95_ms | 0.20 | 8.0 | 0.0051 | 1.203 | PASS |
| zoom_p95_ms | 0.20 | 8.0 | 0.0279 | 1.100 | PASS |
| pan_zoom_p95_ms | 0.20 | 8.0 | 0.0040 | 1.049 | PASS |
| node_drag_control_p95_ms | 0.20 | 8.0 | 0.0161 | 1.837 | PASS |

### Triage

- If variance check fails, first rerun `3x` on the same machine with no background workloads.
- If variance remains high, classify by hardware tier (CPU/GPU/RAM/display) and keep separate baselines.
- Investigate regressions only when thresholds fail on at least two consecutive runs in the same hardware tier.

## Windows Desktop Exit Gate

- Status: `PASS`
- Desktop command:
  `./venv/Scripts/python.exe -m ea_node_editor.ui.perf.performance_harness --nodes 120 --edges 320 --load-iterations 1 --interaction-samples 10 --baseline-runs 3 --baseline-mode interactive --baseline-tag desktop_reference --scenario heavy_media --qt-platform windows --report-dir artifacts/graph_canvas_interaction_perf_p09_desktop_reference`
- Desktop reference facts:
  - Generated (UTC): `2026-03-21T08:45:38.255600+00:00`
  - Qt platform: `windows`
  - Pan p95=`191.553 ms`, zoom p95=`276.627 ms`, node-drag control p95=`413.152 ms`
  - Manual checklist accepted in-thread to proceed after the desktop run; the packet wrap-up records the accepted smoothness, visual-fidelity, and minimap/edge-label outcomes explicitly.

## Limitations

- Pan/zoom timings instantiate `GraphCanvas.qml` in a `QQuickWindow` and include `QQuickWindow.grabWindow()` readback overhead so frame completion is deterministic.
- P01 separates `frame_interval_ms_without_readback` from readback-inclusive interaction samples, but the offscreen/software backend still does not represent desktop compositor cost.
- Project+graph load timing still measures serializer/model/bridge setup and does not instantiate `GraphCanvas.qml`.
- The checked-in canonical snapshot still uses the Qt offscreen/software path for determinism, while the packet-owned desktop-reference artifact records the completed Windows exit gate separately.
- The historical `GRAPH_CANVAS_STRESS_1200` P10 final stress artifact is deterministic offscreen/software proof; the current GPU-performance P10 display-final proof is the display-attached real-fixture closeout artifact.
- The current GPU-performance P10 display-final run uses the checked-in real `examples/stress_1200_nodes.cxproj`; generated/offscreen evidence remains regression-only and does not satisfy display acceptance.
- The undo/redo delta publication P02 final run is offscreen/software regression proof for supported title-history replay only. It does not claim unsupported history entries avoid full rebuild fallback, and it does not prove display-attached GPU performance.
- Absolute timings are machine- and load-dependent; compare trends on the same hardware tier for regressions.
