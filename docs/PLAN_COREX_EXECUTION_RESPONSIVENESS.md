# COREX execution responsiveness and startup improvement

Status: **IN PROGRESS — NO PERFORMANCE ACCEPTANCE CLAIM**

## Recovery and progress

After every context compaction, reread this entire approved plan and this progress table, inspect the current Git diff, and resume the next incomplete task. The main assistant owns implementation and acceptance. Do not delegate implementation or planning synthesis.

| Task | Owner | Status | Evidence / next action |
| --- | --- | --- | --- |
| T01 Establish acceptance baselines | Main | Complete | Exact `b0d4aba0` matched baselines are recorded in `artifacts/execution_responsiveness/final/summary.json`: 50 warm edits after five warm-ups per native/headless plot/scalar cohort and headless 1000-node cohort; ten process-cold runs per cold cohort. Native frame probe revision 5 corrects the earlier observation-loop/extra-frame bias. Historical initial reports remain diagnostic only. |
| T02 Seal registry ownership | Main | Complete | Actual freeze/fork; `PropertySpec` captured defaults with `make_default()`, `with_changes()` and semantic `contract_values()`; frozen artifact metadata; cached catalog snapshot/digest. Tests: 238 + 77 subtests (`t02_final_registry.log`), 137 + 30 subtests (`t02_integration.log`), 98 (`t02_projection.log`); native pipeline smoke passed (`t02/shell_smoke.json`). Node map/index updated and checked. Existing declaration snapshots remain unchanged. |
| T03 Remove redundant protocol work | Main | Complete | RegistryAgreement and validated revisions; pure prepared/output projection and cached commitments/budgets; PreparedRunDispatch with full wire parity; one raw catalog admission. Guard cross-check findings explicitly fixed (generation, active catalog, control text, frozen catalog, backend/tuple aliases). Tests: 90 (`t03_final_focused.log`), 111 + 50 subtests (`t03_transports.log`), 65 + 40 subtests (`t03_guard_regressions.log`), and 54 + 100 subtests (prepared/protocol/record cohort). Five-edit headless probe p50 233.26 ms / p95 247.22 ms; not final acceptance. Profile `artifacts/diagnostics/execution_t03/runtime_profile.txt`: 435769 calls vs baseline 4730665; next hotspots are snapshot/plan/identity work and worker/event wait. Ruff passed. |
| T04 Refactor preparation lifecycle | Main | Complete | Detached request/state capture, `ExecutionPreparationService`, `ExecutionSubmissionService`, one-time dispatch claim, guarded admission outside blocking reservation/retirement, asynchronous cancellation/shutdown and bounded host/worker compilation caches. Worker/store/service tests: 89 + 5 subtests (`t04_services.log`). Runtime/current-result/backend integration: 120 + 46 subtests passed (`t04_integration.log`); two older plugin-fixture freeze failures fixed and all plugin/cancellation/cache tests then passed (22, `t04_final_guards.log`). Ruff and map checker passed. Keep package sources stable during real-worker tests: build identity is independently computed and cached in each process. |
| T05 Integrate responsive shell submission | Main | Functional checks complete; performance open | Preparing state, queued admission, next-turn Auto/snapshot reuse, cancellation/session rules, asynchronous close, cached/coalesced execution projections, stable QML property/group/port identities, property-only invalidation and single settled-output projection. Controller/transition tests: 78 + 15 subtests; later property/invalidation group: 72 + 15 subtests. Worker result/protocol/current-read group: 58 + 105 subtests plus two new guards. Shell targets passed in the isolated run (first 16), focused toolbar retry, and four remaining targets; real blocked-preparation heartbeat/Stop and editor-identity checks passed. Qt Quick controls: 33 passed (`t05_qml_controls_final.txt`). Expanded-settings native probe: warm p50 735 ms / p95 797 ms, handler ~104–109 ms (`t05/native_settlement_projection.json`): targets remain unmet. Final matched native evidence is recorded under T07; the target remains open. |
| T06 Improve cold readiness | Main | Functional checks complete; performance open | Built-in environment memo, exact trusted-declaration reuse, full-agreement generation command/responses, correlated process readiness/retirement, one runtime executor for warm-up/submission, visible-first-frame startup integration, concurrent host/worker initialization for current-generation on-demand runs, and bounded build-hash reads. Readiness/transport lifecycle: 44 + 12 subtests (`t06_lifecycle_guards.log`); on-demand runtime/current-result group: 80 (`t06_ondemand_initial.log`); codec fixture migration: 16 + 60 subtests; identity: 16 (`t06_identity_final.log`). Single process-cold plot probe 2798 ms (`t06/runtime_bounded_reads.json`), versus original runtime baseline median 6130 ms; the final ten-run cohort is recorded under T07 and fails the absolute p95 limit. Pre-warmed expanded native first plot 1186 ms and warm p95 809 ms (`t06/native_ready_probe.json`) remain above target. |
| T07 Validate and document the result | Main | OPEN — performance gates failed; publication approved | Full phase closeout and focused corrections completed; five remaining assertions reproduce at exact baseline. Latest evidence: [QA and gate results](specs/perf/COREX_EXECUTION_RESPONSIVENESS_QA.md). All 50 follow-up cold processes succeeded; all warm cohorts have 50 edits after five warm-ups. Native plot p95 3077.09 -> 675.68 ms; handler 1878.05 -> 114.52 ms; cold native plot 7028.03 -> 3532.88 ms. Post-readiness plot p95 996.05 ms now passes. Warm, heartbeat, native cold absolute, and scalar launch-tail gates remain open. The 1000-node total improves to p95 4864.11 ms with three settlements; invalidation is 631.28 ms versus baseline 619.47 ms. The user explicitly approved publishing these verified improvements with the remaining limits in the commit body. Remaining work concerns native projection/redraw, worker admission/result overhead, and full-snapshot materialization/copying; retain all validation and normal Signal Plot execution. |

Unrelated baseline work to preserve: `docs/specs/INDEX.md`, `tests/fixtures/graph_canvas_surface_snapshot.json`, `docs/PLAN_COREX_Physical_Simulation_Backend.md`, and `scripts/Strain_Gage_Positioning/modular_version/strain_candidate_points.csv`.

Current follow-up: added lazy shared compiled-snapshot commitments, owner-level snapshot/workspace projection validation without discarded child re-parsing (preserving authored numeric representation), in-place variant-valued list editor rows, Windows desktop QQuickWidget zero swap interval before Qt contexts, and safe close of unbootstrapped windows. Focused integration: 236 tests plus 55 subtests passed (`t07_followup_integration.log`); fidelity/dispatch guards: 28 passed (`t07_projection_fidelity.log`); Qt controls: 34 passed. Follow-up full verification completed in `artifacts/verification_logs/execution_followup_full`: fast 5518 passed with one historical inventory guard corrected and all 15 guard tests then passing; fast serial 220 passed; Qt Quick passed; GUI 594 passed with known height failure and two focus-contention failures (all five native XY cases passed isolated); GUI serial 40 passed with two baseline assertions; slow 57 passed; shell isolation 59 passed with two baseline assertions. The initial QA tables remain historical until remeasurement completes. Candidate-only follow-up cohorts completed under `artifacts/execution_responsiveness/followup_final`: all warm cohorts 50 edits plus five warm-ups; all 50 cold processes succeeded. Native plot p95 675.68 ms, plot handler 114.52 ms, headless plot 157.26 ms, large-graph total 4864.11 ms and invalidation 631.28 ms. Post-readiness plot p95 996.05 ms now passes; headless cold plot p95 2760.95 ms is below three seconds. Native cold plot p95 3532.88 ms and warm/heartbeat gates remain open. Scalar launch p95 4552.89 ms exceeds allowance despite stable median. See the latest QA section for full results. Benchmarks are complete; final follow-up hygiene passed 196 tests and 48 subtests, with map/traceability/Markdown/Ruff/whitespace checks passing. The speculative PresentationValue QML cache was fully removed. No renderer/backend replacement was made; the reference stays D3D11.

Publication is explicitly approved: the user requested committing and pushing the verified improvements to main now, with the remaining limits documented in the commit body. T07 and performance acceptance remain open; publication does not imply that the unmet gates passed. Remote default is main; origin HEAD was verified as `e90c33c9`. Preserve the unrelated paths listed above; stage only this task's specs-index line.

Measurement/verification notes: frame probe revision 5 uses cached visual-item references and tags each rendered frame with its synchronized content, checking scalar text or the accepted PNG image URL; revision 1 repeatedly searched the full QML tree and added observer overhead. Heartbeat revision 2 measures preparation/readiness intervals independently of graph setup/expansion. Final native cohorts use expanded plot settings and the corrected probe. The live checkout is `e90c33c9`, a separate XY cursor feature commit directly atop the approved `b0d4aba0` baseline; preserve it. Initial T01 reports did not capture the source HEAD and are historical diagnostics. Exact matched baseline runs use the detached `b0d4aba0` worktree under ignored `artifacts/execution_responsiveness/baseline_checkout`, with only the diagnostic harness copied into it. Revised baseline expanded plot: 50 edits, p95 2999.13 ms (frame revision 3; older global heartbeat, so heartbeat is not matched proof).

One native probe exited with a Windows `d3d11.dll` access violation (host PID 4812, orphan worker 11232 cleaned up); the same-source retry completed. Preserve this failure in closeout evidence. Use the repository's `unittest` shell isolation loader for the full shell-controller module. The matching Qt Quick SDK is verified at `C:\Qt\6.11.1\msvc2022_64`; set process-scoped `QT_ROOT` for the full runner. A structured `-o <report>,txt` invocation produced the 132-test Qt report; the runner's stdout-only Qt invocation produced an empty log. A custom-height graph test fails identically at exact baseline `b0d4aba0` (74 px versus its stale 260 px expectation); retain it as a baseline exception rather than changing unrelated layout behavior.

## Summary

Make ordinary node recalculation responsive by reducing shared execution overhead and removing expensive preparation from the GUI thread. Include both repeated edits and the first execution after application launch. Signal Plot remains on the normal execution path.

The main assistant synthesizes the design and performs all implementation and verification. Subagents may provide bounded, read-only source investigation; implementation tasks will not be delegated.

The current baseline is commit `b0d4aba0`. Existing unrelated changes will be preserved. The earlier reproduction measured approximately **480–650 ms per warm edit**, including **350–400 ms of preparation and dispatch**, while rendering took approximately **4 ms**.

## Key Changes

### 1. Publish genuinely immutable registry generations

Keep one `NodeRegistry` API rather than introduce a competing registry facade.

- Make `freeze()` idempotently seal the entire registry, including declaration and manifest metadata. All registration and configuration mutations must reject frozen registries.
- Add explicit `fork()` for mutable staging. Bootstrap and plugin transactions compose their contributions before freezing and publishing the candidate.
- Preserve declaration syntax such as `default=[...]`, but capture defaults into immutable templates. `PropertySpec.make_default()` produces independent native values while preserving list, tuple, mapping, and supported semantic-value behavior.
- Cache catalog snapshots and fingerprints at freezing. Construct one execution-owned `RegistryAgreement` per complete registry generation.
- Key generation identity on the full registry contract, including node declarations, plugins, and add-on configuration. Physical worker restarts remain a separate identity that invalidates session results and handles.

This is an internal contract migration: update callers explicitly rather than retain post-freeze mutation through compatibility exceptions.

### 2. Validate at boundaries and serialize in one direction

Separate raw admission from operations over validated, immutable execution values.

- Validate raw requests and incoming worker messages completely before use.
- Strengthen prepared-value construction to enforce ownership, size limits, output commitments, and cross-field consistency once.
- Make prepared-value serialization a detached projection. Remove serialization → decoding → serialization cycles used for internal self-validation.
- Reuse cached registry agreement and canonical snapshot/output representations within the same generation.
- Retain the complete existing `StartRun` wire metadata and independent worker attestation. Do not introduce fingerprint-only admission, a `trusted=True` bypass, or validation exemptions.
- Preserve live checks for artifact integrity, result freshness, resource lifetime, and generation changes at consumption.

### 3. Separate preparation computation from state acceptance

Keep `CorexRuntime` as the public facade, with focused execution-owned preparation and submission services. `SolutionStore` remains the sole authority for results and freshness.

Preparation becomes three explicit phases:

1. Capture immutable request, registry-generation, project-binding, and solution-state references under short locks.
2. Perform compilation, hashing, payload construction, and applicable I/O outside lifecycle locks.
3. Revalidate revision/generation commitments and atomically register or discard the prepared result.

Dispatch retains a final guarded acceptance immediately before starting execution. Superseded preparations release pinned results, Trigger reservations, and other reserved resources.

Reuse one captured snapshot across a graph edit’s invalidation and Auto submission. Cache compiled snapshots by their **complete authored fingerprint plus registry identity**, keeping computational revision separate from full snapshot identity. Retain at most two recent entries per runtime/worker, with a 64 MiB encoded-snapshot budget; oversized entries execute without caching. Active preparations retain their own references.

### 4. Introduce asynchronous submission without changing execution ownership

Use one Qt-free preparation executor per runtime. The shell captures UI-owned values before handoff; background work never reads the live graph model or Qt objects.

- Add a submission identity before background work begins.
- Deliver an ordered admission event carrying the run identity before any associated run-scoped events.
- Keep the existing queued event corridor through `RunEventController` and GUI projection through `RunProjectionController`.
- Show **Preparing** while a requested run is being prepared. Stop cancels preparation; Pause becomes available only during execution.
- Schedule idle Auto work on the next event-loop turn, without a time-based debounce.
- Preserve existing viewer invalidation: no viewer reset before worker preflight acceptance.

Lock these interaction rules:

| Situation | Behavior |
| --- | --- |
| Several committed edits before Auto preparation begins | Use the newest snapshot and union the exact affected targets. |
| New execution-affecting edit during Auto preparation | Discard the superseded preparation and prepare the newest request. |
| Edit during an executing run | Let the captured run finish; reject stale output publication and retain existing pending-Auto rules. |
| Explicit Run or Trigger becomes stale before dispatch | Cancel with an inputs-changed explanation; do not silently replay the action. |
| Stop during preparation | Cancel preparation and pending Auto; no subsequent worker start. |
| Switch Auto to Manual | Cancel queued or preparing Auto work; preserve existing behavior for an executing run. |
| Project replacement, close, or registry replacement | Invalidate the relevant submission generation and discard late results. |

Shutdown must cancel submissions before destroying subscribers and complete worker cleanup without blocking the GUI on preparation.

### 5. Improve actual cold initialization and add background warm-up

After the first usable application frame, prepare the configured built-in worker in the background.

- Compute the existing authoritative build/environment identity once, outside the GUI thread.
- Reuse the host registry already constructed during startup.
- Remove duplicate worker reconstruction of trusted declarations when those declarations have already been derived from the same independently verified generation.
- Add a correlated generation-preparation command and readiness/failure response, independent of workflow execution.
- Immediate Run joins the same in-progress initialization; it never creates a second worker.
- Keep node implementation imports lazy. Warm-up must not execute nodes, read workflow inputs, publish Trigger values, create viewers, initialize solver/CAD sessions, or launch external Python environments.
- Preserve the existing pre-Qt PyArrow initialization order.
- Worker death, generation replacement, and shutdown retire readiness correctly. A failed warm-up leaves ordinary on-demand execution available, with failure reported when relevant.

## Public Interface Changes

- `NodeRegistry.is_frozen`, `NodeRegistry.fork()`, and enforced registry freezing.
- `PropertySpec.make_default()` for obtaining independently mutable defaults.
- Execution-owned immutable `RegistryAgreement`.
- A nonblocking runtime submission API returning a submission handle, with cancellation and correlated lifecycle events.
- A built-in generation-readiness API and corresponding worker lifecycle messages.
- Existing synchronous headless execution and prepared-dispatch APIs remain supported through the same underlying services.

Node IDs, port contracts, graph execution semantics, and `.cxproj` format remain unchanged. No persistence migration is required.

## Execution Tasks

All tasks are implemented sequentially by the main assistant. Each task includes its focused checks before the next dependent task begins.

| Task | Dependencies | Goal and conservative write scope | Deliverable and proving check |
| --- | --- | --- | --- |
| **T01 — Establish acceptance baselines** | None | Diagnostic scripts and focused test fixtures only. | Reproducible real-shell and headless warm/cold measurements with phase timing, backend identity, and output correctness. No behavior changes. |
| **T02 — Seal registry ownership** | T01 | Node declarations, registry construction/publication, catalog facts, and affected consumers. | Immutable published registries, explicit mutable forks, independent defaults, cached invariant facts. Prove alias isolation, transaction rollback, and identical declaration semantics. |
| **T03 — Remove redundant protocol work** | T02 | Execution agreement, prepared values, codecs, clients, and worker admission. | Pure serialization and generation-owned metadata. Prove malformed input still fails at the same boundaries and warm internal projection performs no ingress roundtrip. |
| **T04 — Refactor preparation lifecycle** | T03 | Runtime preparation, solution-store capture/registration, bounded compiled-snapshot reuse, and submission service. | Capture/compute/accept phases, cancellation, short locks, and ordered admission. Prove edits can invalidate state while preparation is deliberately blocked. |
| **T05 — Integrate responsive shell submission** | T04 | Run controllers, run state/projection, composition, and affected run controls. | Preparing state, asynchronous submission, snapshot reuse, and the interaction rules above. Prove GUI responsiveness, event ordering, Auto coalescing, and Trigger behavior. |
| **T06 — Improve cold readiness** | T03–T05 | Build identity scheduling, worker registry initialization, generation-readiness protocol, and startup integration. | Single-flight background warm-up plus reduced on-demand initialization work. Prove readiness introduces no workflow or external-service side effects. |
| **T07 — Validate and document the result** | T02–T06 | Focused integration tests, benchmarks, affected agent maps, and registered acceptance documentation. | Correctness and performance evidence against T01, one integration closeout, and documented remaining limitations. |

No task expands into a renderer replacement, parallel node execution, a new result store, or unrelated canvas rendering work.

## Work Packet Conversion Map

None. These are sequential main-assistant implementation tasks; no delegated implementation packets or per-attempt ledgers will be created.

## Test Plan

### Correctness and lifecycle

Cover:

- Frozen-registry mutation rejection, mutable-fork independence, nested-default isolation, and failed candidate publication.
- Plugin-only, node-contract-only, and add-on configuration changes; identical-registry worker restart.
- Malformed metadata, matching-fingerprint malformed revision records, payload limits, altered prepared values, and plugin tampering.
- Process-isolated, trusted, and external-stdio execution paths.
- Cancellation before dispatch, immediate worker events, stale preparation, Stop, project replacement, workspace navigation, and shutdown.
- Dirty-script Apply, Run Selected preview, Trigger publication/capture, disabled edges, current-result reuse, and viewer preflight ordering.
- Repeated edits without unbounded snapshot/cache growth.
- Background readiness without node execution, source-file access, public implementation imports, or solver/viewer initialization.

Use barrier-controlled tests for concurrency. Timing thresholds belong to the benchmark acceptance runs rather than ordinary unit tests.

### Performance acceptance

Use the existing Windows machine and project venv as the reference environment.

| Measurement | Acceptance target |
| --- | --- |
| Warm setting commit to first displayed frame containing the accepted new plot | **p95 ≤100 ms** |
| GUI property-handler duration on the reference three-node graph | **p95 ≤33 ms** |
| GUI heartbeat lateness during preparation/warm-up | **p95 ≤16 ms; no preparation-induced stall >100 ms** |
| First plot after built-in background readiness | **p95 ≤1 second** |
| First plot with a fresh process and warm-up disabled | **p95 ≤3 seconds and median at least 40% below the matched baseline** |
| Launch to usable shell | **No regression exceeding 5% or 50 ms, whichever is larger** |

Measure at least 50 warm edits after five warm-ups and ten independent process-cold runs per cold cohort. Record p50/p95, sample counts, phase timings, worker identity, and combined host/worker memory. Do not flush system caches; label the cold measurements as process-cold.

Use both the 19-row table/plot/media chain and a lightweight non-plot workflow. Add a headless scaling cohort with unrelated nodes to detect unnecessary global work and verify unaffected nodes do not execute.

Native displayed-frame evidence is required for UI acceptance. Offscreen results remain regression evidence. If a target fails, keep the task open and report the remaining measured bottleneck.

Run focused suites during implementation, followed by one full verification closeout for the shared registry/runtime/shell changes. Update affected maps and the route index, register the final evidence from the specs index, and run map, traceability, and Markdown checks.

## Assumptions

- Background warm-up of one built-in worker is approved. External environments remain on demand.
- Complete validation and worker isolation are retained.
- No special Signal Plot execution shortcut is introduced.
- The main assistant owns design synthesis, implementation, and acceptance.
- Existing unrelated changes are preserved. The user explicitly authorized committing and pushing the verified improvements to main with open performance gates and the remaining limits described in the commit body. Packaging remains outside scope.
