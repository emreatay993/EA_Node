# COREX Internal Performance Improvement QA Matrix

- Updated: `2026-07-14`
- Product head measured by the final audits: `fd7ee0d00d85ba65ae15017731e5b55888163ec6`
- Packet set: `COREX_INTERNAL_PERFORMANCE_IMPROVEMENT` (`P00` through `P15`, remedial `R01` through `R06`, audits `V01` through `V03`)
- Overall status: **PARTIAL / staged performance acceptance FAIL**

## Decision Summary

All implementation packets are complete, and all implemented product/internal owner metrics pass except the explicitly listed comparable shell-create, relative QML `setSource()`, and formal display-attached gates. Staged performance acceptance remains **FAIL** because the formal display-attached single-node drag and aggregate frame improvements are below the required `20%`, `REQ-PERF-002` remains above `33 ms`, the comparable shell-create phase regressed, and the QML `setSource()` relative improvement cannot be established from `P00`.

This classification deliberately separates:

- product/internal performance and correctness gates;
- comparable relative measurements;
- formal display-attached acceptance;
- supplemental diagnostics that do not replace a formal gate.

Deeper `QQuickWidget` rendering, readback, painting, and host changes were deferred by the approved program scope. The program did not switch to `QQuickView`, defer PyArrow until after QML, add viewport virtualization, replace history, or add a generic cache layer.

## Environment And Baseline Authority

| Fact | Recorded value |
|---|---|
| Python | `3.10.0` |
| PyQt / Qt | `6.11.0` |
| Formal Windows host/backend | `qquickwidget` / Direct3D 11 RHI |
| Stress fixture | `examples/stress_1200_nodes.cxproj`, workspace `ws_perf_h`, `1200` nodes / `1199` edges |
| Baseline/final fixture SHA-256 | `e1aa111b9bfdf88a14e19c24da15e0ea71f04428866a051326d353207118541c` |

Older retained Track H matrices contain fixture hashes from earlier fixture revisions, including `11ad8f8f79b1621a8cec335a1eee9aa10e94b20b32c16da12c0660e50c3732b7`. Those results are cross-fixture historical context only and must not be used as strict before/after evidence for this program.

## Packet Closeout

| Packet | Status | Retained outcome |
|---|---|---|
| `P00` | PASS | Recorded exact environment, fixture checksum, startup, load, mutation, runtime-snapshot, and autosave baselines before product edits. |
| `P01` | PASS | One `GraphInvariantKernel` and validation memo per registry/compiler pass; memo invalidation follows edge removal; runtime snapshot and compiler output parity preserved. |
| `P02` | RETIRED | The former optional operator-catalog optimization no longer applies to the current application surface. |
| `P03` | PASS | Invocation-scoped frozen presentation facts reused across node, minimap, backdrop, bounds, icon, and edge endpoint construction without payload-schema changes. |
| `P04` | PASS | Contiguous in-place visible-model replacement, structural fallback, deferred latest-wins reentrancy, and sparse comment/link badge projection. |
| `P05` | PASS | Stable edge payloads replace in place with zero reindex; `R05` extends the cache with safe single-edge structural insert/remove while bulk and invalid cases retain full fallback. |
| `P06` | COMPLETE; display gate FAIL | Sparse badge repeaters, frozen multi-drag membership, scalar offsets, and shared scheduling shipped. Formal display improvement remains below `20%`. |
| `P07` | PASS | Fullscreen and Add-On Manager panes use retained URL-backed loaders while preserving first-created object identity and lifecycle behavior. |
| `P08` | PASS | Stable bridge QObjects retained; tabular, Jupyter, plot, viewer/binder, and disabled folder-explorer internals allocate lazily and safely shut down before first use. |
| `P09` | PARTIAL acceptance | Import hygiene, QML-source timing, and explicit pre-QML PyArrow preload shipped. Import and process-wall gates pass; comparable shell-create relative gate fails; QML relative gain is unverified. |
| `P10` | PASS | Palette plus tooltip/category projections compute once per existing theme/policy revision. |
| `P11` | PASS | Library rows, category paths, and pin/data-type projections compute once per registry/workflow revision. |
| `P12` | PASS | Text delimiter detection is limited to `4096` characters; mail preview uses a bounded stamp-keyed LRU. |
| `P13` | PASS | Empty and fully workspace-scoped artifact stores skip owner lookup and migration scans; mixed legacy stores preserve behavior. |
| `P14` | PASS | Fingerprints are fixed-length lowercase SHA-256; owned document mappings avoid redundant recursive copies and autosave reuses one non-mutating encoding. |
| `P15` | PASS | This retained matrix, spec/traceability registration, owner-map refresh, generated navigation indexes, and focused docs/map checks complete the documentation packet. |

## Remedial Lineage

| Remedial packet | Accepted commit | Result |
|---|---|---|
| `R01` visible publication | `5da1e14e` | Removed false structural visible-model fallbacks and redundant endpoint/minimap/locked projections. |
| `R02` connection payload | `70a91c97` | Specialized connection payload builds and preserved targeted connection-count semantics. |
| `R03` startup/autosave | `4ba1b099`, `7928df80` | Deferred shared tabular cache startup and removed remaining owned-document copies. |
| `R04` harness attribution | `fa39a9b5`, `ddac9cbf` | Split state publication, forced refresh, event drain, render/readback timing; added compatible 12-offset drag metrics. |
| `R05` structural edge cache | `c49a2b8` | Added sorted incremental single-edge insert/remove with exact index parity and retained fallback guards. |
| `R06` selected drag diagnostic | `fd7ee0d0` | Added nonbinding deterministic selected three-node drag/readback diagnostics without changing formal gates. |

## Product And Internal Performance Gates

| Metric | Result | Classification |
|---|---:|---|
| App import | `28.5 ms` median, `97.4%` faster | PASS (`<=1.0 s`, at least `50%` faster) |
| Project + scene load | `6273.124 -> 2214.771 ms` p95 | PASS (`<3000 ms`) |
| Runtime snapshot + compile | `230.101 ms` p95 | PASS (`<=450 ms`, at least `20%` faster) |
| Viewer-service construction | `2.0693 ms` p50 | PASS (`<=225 ms`, at least `40%` faster) |
| Changed autosave | `57.277 ms` p95 | PASS (`<=80%` of baseline) |
| Add-On Manager open | first `77.994 ms`; reopen `14.440 ms` p95 | PASS (`<=500/50 ms`) |
| Content fullscreen open | first `193.342 ms`; reopen `15.534 ms` p95 | PASS (`<=500/50 ms`) |
| QML `setSource()` | `431.7 ms` absolute | PASS absolute (`<=1.8 s`); **relative gain UNVERIFIED** because `P00` lacked a discrete comparable phase |
| Startup process wall | `24.8%` faster | PASS process-wall relative result |
| Comparable shell-create phase | `679.4 -> 825.5 ms` | **FAIL** required `20%` improvement; do not conflate with process wall |

### Targeted Visible Publication

| Scenario | Final / baseline p95 | Result |
|---|---:|---|
| Rename node | `0.217` | PASS (`<=0.70`) |
| Single-node drag commit | `0.163` | PASS (`<=0.70`) |
| Multi-node drag commit | `0.143` | PASS (`<=0.70`) |
| Undo/redo | `0.175` | PASS (`<=0.70`) |

### Targeted Payload Rebuild

| Scenario | Final / baseline p95 | Result |
|---|---:|---|
| Rename node | `0.514` | PASS (`<=0.80`) |
| Single-node drag commit | `0.375` | PASS (`<=0.80`) |
| Multi-node drag commit | `0.700` | PASS (`<=0.80`) |
| Create edge | `0.650` | PASS (`<=0.80`) |
| Remove edge | `0.306` | PASS (`<=0.80`) |
| Delete node with incident edge | `0.609` | PASS (`<=0.80`) |
| Undo/redo | `0.573` | PASS (`<=0.80`) |

The `R05` 30-sample process-isolated structural proof recorded create/remove/delete p95 values `5.443 / 2.454 / 5.032 ms`, zero structural fallbacks or reindexes, `90` incremental structural operations, and exact dirty/publication-path parity.

## Formal Display-Attached Acceptance

Both formal reports are valid display-attached Windows `qquickwidget` / Direct3D 11 runs with no software fallback and passing zero-loss parity.

| Metric | Baseline p95 | Final p95 | Change | Result |
|---|---:|---:|---:|---|
| Single-node full drag gesture | `52.404 ms` | `47.811 ms` | `8.8%` better | **FAIL** required `20%` |
| Aggregate frame interval | `93.004 ms` | `91.327 ms` | `1.8%` better | **FAIL** required `20%`; `REQ-PERF-002` also fails (`91.327 > 33 ms`) |
| Pan | `67.974 ms` | `69.961 ms` | `102.9%` of baseline | PASS `<=105%` guardrail |
| Zoom | `111.721 ms` | `95.539 ms` | `85.5%` of baseline | PASS |
| Combined pan/zoom | `179.555 ms` | `162.761 ms` | `90.6%` of baseline | PASS |

### Node Insertion Latency Gate

Track H now provides a separate `node_insertions` measurement for ordinary nodes, Group backdrops, the current Python creation profile, a small custom workflow, and a nested workflow. Each profile runs `3` warmups, followed by a `40`-sample measured budget balanced round-robin across the profiles, and the report includes dispatch-to-model-commit plus confirmation/dispatch-to-presented-frame p50/p95; synchronous undo capture remains inside the dispatch timing. Completion requires all active-scope primary node delegates followed by a later `QQuickWindow.afterRendering` callback; screenshot/readback, heavy-content readiness, and nested out-of-scope child delegates are excluded.

The acceptance target is strict `p95 < 100 ms` for every profile, valid only on display-attached Windows/D3D11 with no software fallback. Automated tests validate the schema, completion rule, and PASS/FAIL/INVALID threshold logic without enforcing machine wall-clock timings. Current-host normal and synthetic 1,200-node captures are retained under `artifacts/node_insertion_windows_normal_balanced_40` and `artifacts/node_insertion_windows_stress_balanced_40`; both are valid display captures and both report `FAIL`. A later selection/publication A/B shows a large directional workflow gain, but its balanced reruns overlapped another agent's test workload and remain diagnostic; concurrent-load reports do not replace retained evidence. The exact per-profile values, control-metric contamination evidence, and safe-gains-first interpretation are recorded in `TRACK_H_BENCHMARK_REPORT.md`.

### Supplemental Selected Three-Node Diagnostic

This path is diagnostic only and does not overwrite the formal single-node or aggregate-frame gates.

| Metric | Baseline p95 | Final p95 | Change | Diagnostic result |
|---|---:|---:|---:|---|
| First offset | `30.295 ms` | `37.234 ms` | `22.9%` slower | FAIL |
| Steady offset | `37.124 ms` | `0.156 ms` | `99.6%` better | PASS |
| Full gesture | `225.326 ms` | `124.349 ms` | `44.8%` better | PASS |
| End/clear | `114.768 ms` | `92.847 ms` | `19.1%` better | FAIL |
| Aggregate selected frame | `149.529 ms` | `145.489 ms` | `2.7%` better | FAIL |

The final selected path verified membership size `3`, exactly one membership freeze, `12` raw offsets, `6` incident edges, and one or two shared-scheduler flushes per sample. Render/readback evidence still points to `QQuickWidget` readback and painting/host work as the remaining bottleneck.

## Correctness And Architecture

- Packet-focused unit, integration, QML, persistence, packaging, and architecture-boundary checks passed.
- Runtime DTO/compiler output, descriptor IDs/order/metadata, `.cxproj` shape, display parity, bridge QObject types, QML context names, and public user-facing behavior remain unchanged.
- The architecture audit passed: graph remains independent of UI/persistence, execution snapshot assembly remains in `ea_node_editor.execution`, persistence conversion remains in `ea_node_editor.persistence`, and startup authority remains in `ea_node_editor.bootstrap` / `ea_node_editor.app`.
- `V01` composite correctness verification passed: fast recorded `2151` passed and `1` skipped, its dedicated serial phase recorded `20` passed, standalone one-worker GUI recorded `566` passed, slow recorded `34` passed, shell isolation recorded `31` passed, and traceability, Markdown, and map checks passed.
- The raw monolithic full command did **not** pass because three intermittent QML order/resource test nodes failed inside its embedded GUI phase. Each exact serial rerun passed and the standalone one-worker GUI suite passed, so correctness is **PASS** with a runner reproducibility **WARN**, not a product-correctness failure.
- The detailed `V01` logs remain ignored verification evidence under `artifacts/verification_logs/v01_final_correctness/`; they are not committed retained artifacts.

## Audit Status

| Audit | Status | Retained conclusion |
|---|---|---|
| `V01` correctness | PASS / WARN | Composite correctness PASS: fast `2151` passed + `1` skipped, serial `20` passed, standalone one-worker GUI `566` passed, slow `34` passed, shell isolation `31` passed, and docs/maps checks passed. Raw monolithic full has a runner reproducibility WARN after three intermittent embedded-GUI QML failures whose exact serial reruns passed. |
| `V02` performance | FAIL / PARTIAL | Product/internal gates and pan/zoom guardrails pass; formal display, shell-create relative, and QML relative-proof closure do not. |
| `V03` independent final audit | PASS | Independent audit confirmed product-head ancestry, docs-only `P15` lineage through `6578e2b9`, a clean worktree, `V01` composite correctness PASS with raw-full runner WARN, accurate retained metric transcription, explicit unresolved formal display, shell-create, and QML-relative failures, and no committed raw artifacts. The implementation is ready for partial-performance handoff, not staged performance closure. |

## P15 Verification

```powershell
.\venv\Scripts\python.exe .\scripts\generate_source_test_file_index.py --check
.\venv\Scripts\python.exe .\scripts\generate_qml_navigation_index.py --check
.\venv\Scripts\python.exe .\scripts\generate_agent_route_index.py --check
.\venv\Scripts\python.exe .\scripts\check_agent_maps.py
.\venv\Scripts\python.exe .\scripts\check_traceability.py
.\venv\Scripts\python.exe .\scripts\check_markdown_links.py
.\venv\Scripts\python.exe -m pytest tests/test_agent_maps_hygiene.py tests/test_agent_route_index.py tests/test_source_test_file_index.py tests/test_qml_navigation_index.py tests/test_traceability_checker.py tests/test_markdown_hygiene.py tests/test_dead_code_hygiene.py --ignore=venv -q
```

## Remaining Work

1. Treat the formal display failure and comparable shell-create regression as open performance work. Any deeper QQuickWidget render/readback/painting or host change requires a separately approved scope.
