# COREX execution responsiveness evidence

Status: **IN PROGRESS — PERFORMANCE ACCEPTANCE NOT MET**

This document records the implementation and verification of the approved
[execution responsiveness plan](../../PLAN_COREX_EXECUTION_RESPONSIVENESS.md).
The main assistant owns design, implementation, and verification. No implementation
or planning synthesis was delegated. The user explicitly authorized committing
and pushing the verified improvements to main with the remaining limits described
in the commit body. Performance acceptance remains open. Packaging is outside scope.

## Implemented ownership

- Published `NodeRegistry` generations are sealed, including declaration defaults,
  catalog facts, plugin manifests, and add-on configuration. Changes are composed
  in explicit mutable forks. `PropertySpec.make_default()` returns independent
  native values; node declarations and project persistence retain their semantics.
- Execution owns the immutable complete `RegistryAgreement`, prepared commitments,
  detached protocol projections, bounded compilation reuse, and submission lifecycle.
  `StartRun` retains full metadata and independent worker attestation. Raw admission,
  payload limits, artifact integrity, result freshness, and resource lifetime checks
  remain enforced.
- `CorexRuntime` captures, computes, and accepts preparation separately.
  `SolutionStore` remains the sole result/freshness authority. A single Qt-free
  executor performs preparation and built-in readiness. Submission identity precedes
  background work; ordered admission precedes associated run events.
- The shell displays Preparing and supports Stop during preparation. Auto work is
  scheduled on the next event turn, coalesces exact targets, and cancels superseded
  preparations. Explicit stale actions cancel without replay. Existing executing-run
  and viewer-preflight semantics are retained.
- Built-in initialization starts after a usable frame, reuses the published registry,
  and joins one physical worker generation. Environment/build identity computation
  stays outside the GUI thread. Node implementations remain lazy; readiness executes
  no nodes, loads no workflow source files, and creates no viewer or external service.
- Ordinary presentation updates retain QML row identities. Editor contract changes,
  including list item types and exact-selector mode, rebuild the affected editors.

## Correctness evidence

Focused proving checks and task-level logs are recorded in the plan's progress
table. The new boundary and lifecycle suites are
[registry immutability](../../../tests/test_registry_immutability.py),
[prepared dispatch](../../../tests/test_prepared_dispatch.py),
[execution submission](../../../tests/test_execution_submission.py),
[shell submission](../../../tests/test_shell_submission.py),
[generation readiness](../../../tests/test_generation_readiness.py), and
[QML identity retention](../../../tests/test_presentation_model_keys.py).
Concurrency checks use explicit barriers rather than timing thresholds.

The full verification closeout used the repository runner's phase commands,
with focused corrections and reruns for migrated fixtures. Fast verification
passed **5515 tests**, with four skips; its serial
cohort passed **220 tests**. Qt Quick passed **132 checks** with the installed
matching SDK and a file-backed text report. GUI verification passed 595 tests;
the native cursor suite passed all three cases
in isolation after a parallel-run failure. Serial GUI originally passed 32 tests;
eight fixture migrations were then proved with the focused flow/hygiene cohort
(194 tests and 48 subtests passed). The slow phase passed 57 tests. Shell isolation
passed 58 targets, including the two new responsiveness targets; the subsequent
workspace-actions correction passed. Five remaining assertions reproduce at the
exact baseline and are listed below. Changed Python files pass Ruff.

Final verification/docs hygiene passed **182 tests and 48 subtests**. Agent-map,
traceability, Markdown-link, Ruff, and diff-whitespace checks passed. The route
index was regenerated. Unrelated local work and the existing HEAD were preserved.

## Measurement protocol

The reference environment is the existing Windows machine and project venv.
The native shell uses Direct3D11Rhi, QQuickWidget, and DPR 2.0. Process-cold means
a fresh host/worker process without flushing system caches. Raw timing, phase,
backend identity, and combined host/worker memory records remain under the ignored
`artifacts/execution_responsiveness` directory.

The diagnostic entry point is
[benchmark_execution_responsiveness.py](../../../scripts/benchmark_execution_responsiveness.py).
Warm cohorts use five warm-ups and 50 measured edits. Cold cohorts use ten
independent processes. The workflows are the 19-row table/plot/media chain and a
lightweight scalar chain, plus a headless scalar cohort with 1000 unrelated nodes.
Each accepted output is checked, and settlements identify the nodes that executed.

Frame probe revision 5 uses the native Qt event loop and cached output-card and
content-item references. Immediately before scene synchronization it records the
ready image URL or scalar text. A direct render-completion callback timestamps
the frame with that content; the earliest frame matching the accepted result is
the endpoint. It does not require another frame after run-idle observation.
This is native render evidence, not an OS-compositor presentation timestamp.
Heartbeat revision 2 separates preparation/readiness intervals from graph setup,
and a setup frame completes before starting readiness or the first run. Plot
cohorts expand the settings controls. Optional final-frame captures happen after
timed edits and are excluded from latency measurements.

The exact baseline is `b0d4aba0`, run from a detached worktree with the same
diagnostic harness. The candidate preserves the separate `e90c33c9` XY cursor
feature commit atop that baseline. Initial T01 reports did not record source HEAD
and used an earlier observation loop; they are diagnostic history, not the final
matched native comparison.

## Initial matched measurements

All latency values below are milliseconds. Every warm row has **50 measured
edits after five warm-ups**. The native plot uses expanded settings. Combined
RSS is the observed peak for each warm host/worker process cohort, in MiB.

| Warm workflow | Baseline p50 / p95 | Candidate p50 / p95 | Combined RSS baseline / candidate |
| --- | ---: | ---: | ---: |
| Headless plot | 573.04 / 620.49 | 150.35 / 179.49 | 504.0 / 504.3 |
| Headless scalar | 414.64 / 452.69 | 62.31 / 74.26 | 436.4 / 436.1 |
| Headless scalar, 1000 unrelated nodes | 8223.26 / 8629.48 | 5873.92 / 6024.66 | 494.4 / 486.8 |
| Native plot, accepted-output frame | 2910.02 / 3077.09 | 786.52 / 830.66 | 1301.2 / 1224.1 |
| Native scalar, accepted-output frame | 772.89 / 1009.44 | 644.56 / 952.35 | 903.7 / 906.1 |

The scaling cohort settled **exactly three nodes on every measured edit** on
both sides. It retained one physical worker generation per warm cohort. Full
worker identities and registry fingerprints are recorded in the raw reports.

Each cold row contains **ten independent process-cold runs**. The complete cold
matrix contains 80 successful processes with checked outputs. RSS is the median
of each process's peak combined RSS. Readiness rows have no baseline counterpart.

| First result | Baseline p50 / p95 | Candidate p50 / p95 | Combined RSS baseline / candidate |
| --- | ---: | ---: | ---: |
| Headless plot, warm-up disabled | 5291.91 / 5375.56 | 2802.29 / 3356.80 | 485.1 / 486.4 |
| Native plot, warm-up disabled | 6907.02 / 7028.03 | 3325.94 / 3471.20 | 1121.9 / 1141.3 |
| Native scalar, warm-up disabled | 5575.04 / 5637.35 | 2463.20 / 2700.52 | 904.1 / 904.2 |
| Native plot, after readiness | — | 957.33 / 1075.89 | — / 1117.5 |
| Native scalar, after readiness | — | 176.73 / 194.15 | — / 902.6 |

Built-in readiness itself took p50/p95 **2314.46 / 2364.17 ms** in the plot
cohort and **2296.84 / 2824.03 ms** in the scalar cohort. Its duration is excluded
from the post-readiness first-result rows. On-demand native plot median latency
fell **51.85%**; headless plot median fell **47.05%**.

The GUI property handler changed as follows:

| Handler | Baseline p50 / p95 | Candidate p50 / p95 |
| --- | ---: | ---: |
| Plot setting commit | 1791.05 / 1878.05 | 106.78 / 123.83 |
| Scalar value commit | 410.95 / 454.35 | 21.76 / 31.99 |

The native plot's preparation-to-`run_started` observation fell from p95
**2019.47 to 517.35 ms**; scalar fell from **885.35 to 526.26 ms**. These include
queued GUI delivery, not just background CPU time. Preparation heartbeat p95
was **164.08 ms** for the candidate plot and **190.35 ms** for scalar; observed
maxima were **346.17 ms** and **278.71 ms**. These summaries include the initial
run and warm-ups as well as measured edits. During explicit readiness, the worst
per-process heartbeat p95 was **22.43 ms** for plot and **15.09 ms** for scalar;
observed maxima were **243.91 ms** and **241.94 ms**. These are phase observations;
they do not attribute every native paint stall to background preparation.

Launch-to-usable-shell p50/p95 in the ten-run plot cohort was **4001.32 / 4147.91 ms**
at baseline and **4045.87 / 4337.79 ms** for the candidate. The scalar cohort was
**4019.11 / 4076.82 ms** and **4006.73 / 4129.92 ms**, respectively. This is the
matched native composition harness with its isolated diagnostic profile/session,
not an installed-package launch measurement.

Raw records and aggregate phase statistics are in
`artifacts/execution_responsiveness/final/summary.json` and its baseline/candidate
report directories. Native final-frame captures are `warm_shell_plot_0.png` in
each directory. Earlier native `frame4_*` reports are retained as conservative
diagnostics and excluded from this comparison.

Example reference commands, run once per cohort and repeated in fresh processes
for each cold sample:

```powershell
.\venv\Scripts\python.exe scripts/benchmark_execution_responsiveness.py --mode runtime --graph scalar --unrelated 1000 --edits 50 --warmups 5 --output artifacts/execution_responsiveness/scaling.json
.\venv\Scripts\python.exe scripts/benchmark_execution_responsiveness.py --mode shell --graph plot --expand-settings --edits 50 --warmups 5 --capture-frame --output artifacts/execution_responsiveness/native_plot.json
.\venv\Scripts\python.exe scripts/benchmark_execution_responsiveness.py --mode shell --graph plot --expand-settings --edits 0 --warmups 0 --warmup-worker --output artifacts/execution_responsiveness/ready_plot_00.json
```

## Acceptance remains open

| Gate | Candidate evidence | Result |
| --- | --- | --- |
| Warm accepted plot frame p95 ≤100 ms | 830.66 ms | FAIL |
| Plot property handler p95 ≤33 ms | 123.83 ms | FAIL |
| Preparation/readiness heartbeat p95 ≤16 ms, no induced stall >100 ms | Phase p95/maxima exceed limits; causal separation of native painting remains incomplete | NOT ACCEPTED |
| First plot after readiness p95 ≤1000 ms | 1075.89 ms | FAIL |
| Process-cold first plot p95 ≤3000 ms and median ≥40% lower | Native 3471.20 ms; median 51.85% lower. Headless 3356.80 ms; median 47.05% lower | FAIL absolute limit; PASS relative reduction |
| Launch regression ≤max(5%, 50 ms) | Plot p95 +189.88 ms, within 207.40 ms allowance; scalar +53.09 ms, within 203.84 ms allowance | PASS in reference harness |

Native event tracing measured **90–250 ms** shell UpdateRequest processing.
Property/projection work, queued run-event delivery, worker admission/result
handling, and native redraw remain the next bottlenecks. The 1000-node case also
retains substantial full-snapshot serialization/materialization and copying:
invalidation p95 **regressed from 619.47 to 951.18 ms**, despite lower total run
latency. Capture p95 was 174.91 ms versus 169.09 ms. Further work must reduce those
costs while preserving complete authored identity and boundary validation.

Subsequent focused work defers the compiled snapshot's canonical fingerprint to
preparation/dispatch consumption and shares it across the cache entry's consumers.
The full authored cache key is unchanged. A three-edit diagnostic measured
invalidation at 688–741 ms and total execution at 5571–5719 ms; this is preliminary
evidence, not a replacement for the 50-edit table above. Canonical identity,
bounded ownership, cancellation, and prepared-dispatch checks passed (26 tests).
The experiment retaining additional QML payload branches was removed because its
measured benefit was inconclusive. Further native tracing found long top-level
window composition updates without QML render phases inside those updates.

The subsequent verified changes also include in-place variant-valued list rows,
Windows desktop QQuickWidget presentation with swap interval zero, and safe close
before controller attachment. Surface format is configured before Qt shared
contexts and QApplication; other platforms, offscreen runs, and the QQuickView
host retain their policy. This uses the existing D3D11 renderer. See the
[Qt surface-format API](https://doc.qt.io/qt-6/qsurfaceformat.html#setSwapInterval).
Snapshot/workspace projections validate their own fields and their owned child
projections without constructing discarded decoder results. Raw ingress still
fully decodes and validates. Authored numeric representation remains unchanged.

Follow-up integration passed **236 tests and 55 subtests**; projection fidelity and
dispatch passed **28 tests**; Qt controls passed **34 checks**. Full follow-up logs
are under `artifacts/verification_logs/execution_followup_full`: 5518 fast tests
passed, and the historical inventory guard was corrected and passed all 15 tests;
220 serial fast tests passed; GUI had 594 passes and two native focus-contention
failures whose five-case isolated rerun passed; serial GUI had 40 passes; slow had
57 passes; shell isolation had 59 passes. The same five baseline assertions remain.
Current-cohort results are recorded separately below. Final follow-up hygiene passed 196 tests and 48 subtests; map, traceability, Markdown-link, Ruff, and diff-whitespace checks passed.

The implementation and measurement closeout do **not** constitute performance
acceptance. The plan remains open until these gates pass.

No renderer replacement, parallel node execution, Signal Plot shortcut, or new
result store was introduced. Session-bound table carriers remain ineligible for
durable result reuse; lifetime validation was not relaxed to improve timings.

## Latest follow-up measurements

The latest candidate reports are under
`artifacts/execution_responsiveness/followup_final/candidate`, with aggregate
`followup_final/summary.json`. These replace the candidate results for current
acceptance assessment; the initial matched baseline above remains unchanged.
Every warm cohort contains 50 edits after five warm-ups. Every cold/readiness
cohort contains ten independent processes; all 50 follow-up cold processes
completed with valid outputs.

| Latest candidate | p50 ms | p95 ms |
| --- | ---: | ---: |
| Headless warm plot | 135.46 | 157.26 |
| Headless warm scalar | 60.94 | 67.89 |
| Headless warm scalar, 1000 unrelated nodes | 4782.12 | 4864.11 |
| Native warm plot frame | 647.96 | 675.68 |
| Native warm scalar frame | 152.49 | 209.45 |
| Plot property handler | 104.12 | 114.52 |
| Scalar property handler | 21.07 | 31.18 |
| Headless process-cold plot | 2738.08 | 2760.95 |
| Native process-cold plot | 3196.95 | 3532.88 |
| Native process-cold scalar | 2460.80 | 2725.78 |
| First native plot after readiness | 856.12 | 996.05 |
| First native scalar after readiness | 164.74 | 179.63 |

The large-graph invalidation p95 is now **631.28 ms**, close to the 619.47 ms
baseline and below the first candidate's 951.18 ms. Each measured edit still
settles only three nodes. Peak combined warm RSS was 504.7 MiB for headless plot,
437.0 MiB for scalar, 491.7 MiB for the large graph, 1220.5 MiB for native plot,
and 904.3 MiB for native scalar. Median process-cold peak RSS was 487.0 MiB for
headless plot, 1127.4 MiB for native plot, and 903.7 MiB for native scalar.

Native plot preparation heartbeat p95/max is **133.59 / 159.12 ms**; scalar is
**47.04 / 66.96 ms**. During readiness the worst per-process p95/max is
**10.33 / 68.13 ms** for plot and **19.38 / 73.01 ms** for scalar.

The post-readiness first-plot gate now **passes**. Headless cold plot is below
three seconds. The warm plot frame, plot handler, overall heartbeat, and native
cold-plot absolute limits **remain unmet**. Native cold-plot median reduction
still exceeds 40%. Launch plot p50/p95 was **3981.96 / 4038.47 ms**, within the
baseline allowance; scalar was **4011.81 / 4552.89 ms**. The scalar median is
stable, but its measured p95 tail exceeds the allowed regression, so the launch
gate is **not accepted** for this latest cohort. No outlier was removed.

The plan stays open. The user explicitly approved publishing the verified
improvements to main now, with these remaining limits documented in the commit
body. This publication does not constitute performance acceptance.

## Known verification limitations

- Five assertions fail at both exact baseline and candidate: graph custom height
  (260 px expected versus 74 px observed), two viewer surface-height assertions,
  PDF fullscreen document-object lookup, and the Inspector interval override's
  visible-editor lookup. In the latter, both Python and QML property presentations
  contain the correct connected interval and disabled-editor state, but the
  expected visible editor is absent. These baseline failures are retained; no
  unrelated layout or fullscreen behavior was changed to make the suite pass.
- One native diagnostic process exited in `d3d11.dll` with an access violation.
  Its verified orphan worker was cleaned up; the same-source retry completed.
  This failure remains part of the evidence rather than being counted as a pass.
- The SDK runner's stdout-only invocation produced an empty capture despite exit
  code zero. The retained file-backed report contains all 132 passing checks.
