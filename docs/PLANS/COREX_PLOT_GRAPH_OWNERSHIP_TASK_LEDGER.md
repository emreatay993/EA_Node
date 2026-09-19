# COREX Plot and Graph Ownership - Task Ledger

Plan: [Approved implementation plan](../PLAN_COREX_PLOT_GRAPH_OWNERSHIP_REFACTOR.md)

Status: **IMPLEMENTED AND FUNCTIONALLY REVIEWED - both stages complete; performance qualification stopped by user with limitations retained**

## Authority and recovery

**Latest user direction supersedes the intensive testing schedule:** "I don't like that you are going for this much detail, get over your tests already". Extra timing/diagnostic campaigns and broad fast reruns were stopped. T06-T08 were completed as one graph ownership group with focused correctness checks and one independent review. Both stages are functionally accepted; unresolved array-tail timing remains a limitation, not a pass. All earlier performance-gate scheduling below is historical and superseded where it conflicts with this instruction.

- The user authorized implementation of the complete plan on 2026-09-19.
- Both stages are implemented and functionally accepted under the latest user direction; performance qualification is not claimed.
- The coordinator owns this ledger and acceptance; one implementation writer is active at a time.
- Fresh workers own coherent tasks; independent reviewers inspect actual changes and evidence.
- After compaction/resumption, fully read the plan and this entire ledger, then current instructions, Git state, active agents, and the next incomplete task before writing or delegating.
- Implementation initially excluded publication. The user subsequently authorized committing this refactor to `main` and pushing; see Publication below. Dependency upgrades and unrelated cleanup remain excluded.
- Block demonstrated performance regressions. Noisy/uncontrolled evidence is inconclusive; existing responsiveness acceptance failures remain separate.

## Baseline and protected work

- Checkout: `C:\Users\emre_\PycharmProjects\EA_Node_Editor`
- Branch: `main`
- Baseline HEAD: `d36c84a65c02635acdd7ec541be9d8f1dfee0425`
- Interpreter: `C:\Users\emre_\PycharmProjects\EA_Node_Editor\venv\Scripts\python.exe`
- Runtime: CPython 3.11.6, AMD64; PyQt 6.11.0 / Qt 6.11.0.
- Frozen baseline: detached worktree at `artifacts/plot_graph_refactor/baseline_source`, same baseline HEAD. Its production source must remain unchanged.
- Measurement/log root: ignored `artifacts/plot_graph_refactor/` (`.gitignore:29`).

### Current frozen harnesses (T05 provenance correction accepted)

- Plot SHA-256: `21bb7f59bd54e574dc91d8fce14d3415047e9a785152ba1b83a0fee4a7a4c2fe`.
- Graph SHA-256: `d0d8c40f8358a9a66a8e9193ee17c5820635df9aa731211a426d79c8d60a4ac1`.
- These supersede the historical T01 script hashes only for new runs. Independent AST proof confirms only post-measurement `_origins` validation changed; all measured work/fixtures/reset/counters/schema/sample counts remain frozen. T01 stored origins satisfy the stronger guard, so historical evidence is retained unchanged.

| Protected path | Initial state / SHA-256 |
| --- | --- |
| `AGENTS.md` | Modified; `C2D14F278A59340D11887CA85A894AE7F385079B0B923176189233F3677C2DFD` |
| `docs/specs/INDEX.md` | Existing added Physical Simulation registration; preserve exact hunk while adding this task's line |
| `docs/PLAN_COREX_Physical_Simulation_Backend.md` | Untracked; `F1709CD27CDD97141E354AB0644B3602F8EA43EBEFBB294B0C5FA4578C6788F2` |
| `scripts/Strain_Gage_Positioning/modular_version/strain_candidate_points.csv` | Untracked; `468C04C09DF327871ED6CD947EF58E8F26412D632A1E969C3C56303DFC44061B` |

## Task progress

### User steering adopted in T02 (2026-09-19)

Before Plot benchmarking the user requested using Signal Plot for line/scatter work, then explicitly confirmed Signal Plot plus Media Panel or Image Export is sufficient. The approved amendment retires generic Scatter cleanly, keeps Signal plus seven specialized generic nodes, adds no renderer/alias/migration, and preserves existing explicit unresolved-node file-load rejection. Production edits had not started at that decision; the amendment is now implemented and accepted in T02. Stage B remains intended and gated behind Stage A acceptance.

- `/root/signal_plot_consolidation` completed source/history comparison. `09502b9e` already retired `plot.line`; normal project loading rejects unresolved types before normalization. Signal already renders marker-only scatter through XY with `line_styles=[0]` and nonzero `marker_shapes`.
- Retained generic types: bar, histogram, heatmap, contour, surface, point_cloud, streamlines. Generic fixture coverage moves to retained types, normally Bar; Signal-specific cases prove scatter semantics and the selected output pipelines.
- T01 adapted Plot fixtures before freezing/timing baseline; T02 started only after independent T01 acceptance.
- T01 review fixes are complete: graph deepcopy/clone observability, isolated test plugin-generation roots, and repeated Plot fingerprint consistency. Thirteen final focused tests passed.
- Graph instrumented feasibility passed 100/1200-node cohorts, 12 scenarios; `artifacts/plot_graph_refactor/t01_benchmark/graph_baseline_instrumented.json`, fixture hash `1750e4fe3fc6de5797927f583f135e1a31049e8b025ee259ee2df1f1db98aa41`; prescribed initial timing subsequently passed as recorded below.
- Read-only cache audit found no new attributable test plugin generations; no cleanup performed.
- T02 preparation confirmed intended catalogue-count changes (built-ins125 to124, repo-owned143 to142), related classification/hash fixtures, and example generators. Capture expanded affected test IDs before editing; canonical fixture comparison must isolate the intended retirement/Signal metadata change.
- Generic-node-only unreachable line/scatter branches may be removed after exact consumer checks; independently consumed backend/tooling line/scatter contracts remain.
- Subsequent explicit user correction: visual-parity tool line/scatter cases must route through production Signal Plot/XY. Do not keep generic line preparation solely for that tool. Writer and reviewer were notified; plan amended. Specialized tool cases retain generic backends; report raster versus fullscreen evidence accurately. This overrides the interim coordinator message allowing that tool to retain generic preparation.

| Task | Owner | Allowed scope | Prerequisite | Status | Evidence / review | Accepted snapshot or commit | Next action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T01 Baseline | coordinator; t01_plan_record; t01_baseline_checks; t01_benchmark_worker | Plan/index/ledger, benchmarks, characterization, ignored evidence | Implementation authorization | ACCEPTED | Baseline366 plus77 subtests; focused13; full Plot/graph instrumented+timed baselines; t01_review accepts; docs/maps/freshness pass | d36c84a6 production baseline plus frozen harness hashes below; no commit | Complete; stage comparisons remain later |
| T02 Plot consolidation/specs | t02_plot_specs | Approved Scatter retirement/Signal discoverability, inert specs/init, role metadata/direct callers/tests/examples/maps | T01 | ACCEPTED | Full443+126subtests; four stale expectations closed by final10; specs13; real example/runtime and Signal export proofs; t02_review accepts; hygiene pass | 51 verified files in artifacts/plot_graph_refactor/t02/accepted_files plus implementation_snapshot.json; no commit | Complete; performance still T05 |
| T03 Plot preparation | t03_plot_preparation | Data-series owner, request orchestration, moved preparation/request tests/maps | T02 | ACCEPTED | Owning82pass;33oldIDs retained/moved;7new;7 instrumented outputs/counts match; t03_review accepts; hygiene pass | Cumulative56 files in artifacts/plot_graph_refactor/t03/accepted_files + accepted_snapshot.json; no commit | Complete; timing T05 |
| T04 Plot exports/tests | t04_plot_exports | Export owner, publication, scene/preview/export test ownership/maps | T03 | ACCEPTED | Owning101pass zero skips/errors;37oldIDs/markers accounted;7new exportguards; t04_review accepts; hygiene pass | Cumulative58 files in artifacts/plot_graph_refactor/t04/accepted_files + accepted_snapshot.json; no commit | Complete; Stage A gates T05 |
| T05 Stage A acceptance | t05_verification/t05_review | Verification evidence and coordinator docs | T02-T04 | FUNCTIONALLY ACCEPTED; PERFORMANCE UNRESOLVED | Independent review finds no source blocker; user stopped further investigation | Revised67-file accepted request snapshot; no commit | Complete; retain array-tail and baseline test limitations |
| T06 Graph tests | graph_ownership_implementation | Planned test/fixture migration and focused characterization | T05 functional acceptance | ACCEPTED | All132 original IDs/parameters accounted;22 exact-AST moves;5 focused policy cases | graph_group/implementation_snapshot.json; no commit | Complete |
| T07 Port-state owner | graph_ownership_implementation | Pure projection, Script/load adopters, kernel memo lookup/tests/maps | T06 | ACCEPTED | Caller policies and memo boundaries preserved; independent review accepts | Same grouped snapshot | Complete |
| T08 Mutation mechanics | graph_ownership_implementation | Property/dynamic commit suffixes and direct tests/maps | T07 | ACCEPTED | 186 focused +1 retained Script editor integration pass; graph_ownership_review accepts | Same20-file snapshot | Complete |
| T09 Final closeout | coordinator + independent reviewer | Ownership docs, protected-work check and honest final outcome | T06-T08 | COMPLETE | Functional reviews accepted; final links/traceability/whitespace pass;79 accepted file hashes verified; protected work unchanged | final_source_manifest.json; no commit | Finished; no further testing scheduled |

Final stop checkpoint: all performance work is stopped. The already-running counterfactual finished before user steering (9.94s,320 requests/arm); raw files under `t05/array_counterfactual/` remain uninterpreted and are not acceptance evidence. Diagnostic-thread affinity was restored; no active diagnostic PID/session. Fresh grouped graph writer/reviewer completed and stopped. No further performance investigation is authorized by the current direction.

## Final implementation outcome

- Plot declarations, data preparation, request composition and exports have direct owners. Redundant generic Scatter is retired; Signal Plot/XY plus Media Panel/Image Export is the line/scatter route, including visual-parity tooling. Seven specialized generic plots remain.
- Graph port-state projection has two explicit pure policies; shared property/dynamic mutation mechanics retain entry-specific validation, return values, ordering, Script atomicity and read-only compatibility checks. Existing kernel memo reuse avoids new resolution/traversal ownership.
- Tests now follow declaration/preparation/export/scene/cache and graph/parser/normalization/scene/persistence owners. Assertions and parametrization were preserved through recorded migrations; the sole sink duplicate retains the assertion union.
- Graph proof:186 passed in28.26s plus exact ScriptEditorDock integration1 passed in5.24s, zero failures/errors/skips. Reviewer `/root/graph_ownership_review` verified all20 final hashes,132 prior IDs,22 moved ASTs, policies/order/defaults/memo use and evidence; no material findings.
- Final graph evidence: `artifacts/plot_graph_refactor/graph_group/implementation_report.md`, `implementation_snapshot.json`, `test_dispositions.json`, `focused.log/xml`, `shell.log/xml`. Source/test inventory regenerated before route index; owning maps/coverage, Ruff and quick hygiene passed.
- Known limitations: array-tail timing remains unresolved; broader performance qualification and additional broad suites were stopped by user. Two canvas failures reproduce on baseline and candidate. Composed offscreen aggregate measurements have the scope/run-timer limitations recorded below. Do not call all broad tests green or claim complete performance neutrality.
- Unrelated AGENTS, Physical Simulation plan/index entry and strain CSV preserved; their recorded hashes rechecked. No branch change or user-app termination. Publication was authorized only after implementation closeout.
- Final source manifest: `artifacts/plot_graph_refactor/final_source_manifest.json`,79 accepted files verified against cumulative reviewed hashes; removed provisional characterization file remains absent. Final Markdown links, traceability and whitespace checks pass. Implementation was reviewed against `d36c84a65c02635acdd7ec541be9d8f1dfee0425` before the publication request.

## Publication

The user explicitly requested: "Once you're done, commit your changes here to main and push."

- Publish the reviewed refactor, its tests, examples, navigation and plan/ledger to the existing `origin/main` (`https://github.com/emreatay993/EA_Node`).
- Pre-publication local `main` and fetched `origin/main` both resolve to `d36c84a65c02635acdd7ec541be9d8f1dfee0425`; no unrelated local commits precede this change.
- Stage only the accepted manifest paths plus the plan/ledger and this task's specs-index addition. Exclude `AGENTS.md`, the Physical Simulation plan/index entry, the strain CSV and all ignored measurement artifacts.
- Reuse the completed focused checks and independent reviews. The unresolved array-tail timing and baseline canvas failures remain explicit publication limitations; no benchmark or broad-test campaign is restarted.

## Verification evidence

### T01 baseline

- Original collection: 158 exact IDs: Plot contracts27, Python Script declarations46 including parameters, dataflow persistence16, registry validation69. The plan's 20 Script tests are function count, not collected count.
- Inventory: `artifacts/plot_graph_refactor/t01_baseline/original_test_inventory.json` (IDs, parameters, source starts/hashes, markers).
- Plot owning cohort: **151 passed, 77 subtests passed**, 42.40s, serial offscreen. Log: `artifacts/plot_graph_refactor/t01_baseline/plot_baseline.log`.
- Retained Plot isolated shell target: **1 passed**, 6.22s. No baseline failures reported.
- Graph baseline: **214 passed**, 29.98s, serial offscreen. Registry validation's69 cases were already included in the Plot cohort and were not repeated. Log: `artifacts/plot_graph_refactor/t01_baseline/graph_baseline.log`.
- Total baseline executions: **366 passed plus77 subtests**. Exact commands, environment, dependency versions, and log/JUnit paths: `artifacts/plot_graph_refactor/t01_baseline/summary.json`.
- Benchmarks/characterization: **13 focused tests passed**; seven retained Plot scenarios and twelve graph100/1200 scenarios completed both separate instrumented and timed runs at planned counts. T06 will refresh graph evidence against accepted Stage A.
- Benchmark summary and exact command argument vectors: `artifacts/plot_graph_refactor/t01_benchmark/baseline_summary.json` and `baseline_commands.json`. Instrumented/timed fixture hashes and every semantic fingerprint match; independent reviewer verified source roots and clean baseline checkout.
- Frozen Plot harness SHA-256: `63c9c9e5149cf0af4b2b4a112159f98f9944eba5e0db75ae1b100857be5ee660`.
- Frozen graph harness SHA-256: `28d62078d9418113850f186c090e2dbfc973c3cb19304a3e4a0ace7c67d2c637`.
- Separate existing Signal XY line-renderer baseline: two10000-point traces, one warmup/five measurements, mean24.45ms/p95 25.73ms; isolated launcher/source metadata in `signal_baseline_metadata.json`. This is line timing, not marker-only scatter timing.
- T01 independent reviewer `/root/t01_review` accepts after repeated-Plot-fingerprint, graph-copy-counter, and test-cache isolation findings were fixed. No material findings remain. These baselines are not candidate performance acceptance.
- Agent maps, source/test inventory, route-index freshness, traceability, Markdown links, and diff whitespace passed.

## Test migrations

T02 expanded retirement baseline: `artifacts/plot_graph_refactor/t02/expanded_before_ids.json` (387 IDs), module list in `affected_test_modules.json`, canonical before catalogue in `catalogue_before.json`. Accepted dispositions are in `test_dispositions.json` (all387 IDs accounted for, seven justified renames;451 current collected cases including expanded coverage). Visual-parity tool targets production Signal/XY for line and marker-only scatter, with actual reduction/threshold tests plus canonical-sample checks; fullscreen interaction remains separately owned proof.

### T02 accepted evidence

- `implementation_report.md` and `implementation_snapshot.json` under `artifacts/plot_graph_refactor/t02/` record scope, checks, and51 hashes. Coordinator copied and hash-verified those exact files to `accepted_files/` for subsequent uncommitted-task diff review.
- Full affected run:443 passed,126 subtests; four assertion failures (Bar payload strings and one inventory count) were fixed without production changes. Final focused closure10 passed includes all four, two generated-Bar harness-selector cases and four authored-example edge-preservation cases. No repeated broad run was needed.
- Canonical catalogue delta exactly one removal (`plot.scatter`) and Signal description/keywords changes; all other rows preserved.
- Real CorexRuntime smoke: compact Signal/Media example settles3 nodes with two full six-sample signals; Bar archive settles4 nodes and produces both refs. Authored List-access and stale example wiring were corrected; backend algorithms unchanged.
- `tests/test_plot_value.py::test_signal_plot_process_export_and_session_reuse` passed in affected XML: real Signal-to-Image-Export pipeline, exported PNG bytes equal preview, and session reuse.
- `tests/test_signal_plot_renderer.py::test_signal_marker_only_scatter_keeps_full_xy_samples_without_line_marks` passed: scatter-only XY marks and full4500-point arrays.
- Reviewer `/root/t02_review` independently verified canonical delta, retained-function AST changes, all dispositions and51 current hashes; no material findings remain. Ruff/maps/traceability/links/generated freshness/diff checks pass. Frozen harness and protected file hashes unchanged; frozen baseline checkout clean.
- T05 composed-harness acceptance must assert nonempty `plot_node_id` and `fullscreen_plot` metrics; its existing optional-plot behavior must not yield a false pass.

### T03 accepted evidence

- `artifacts/plot_graph_refactor/t03/implementation_report.md` and12-file `implementation_snapshot.json` record the delta. Coordinator hash-verified and copied the cumulative T02+T03 state (56 files) to `accepted_files/`; manifest `accepted_snapshot.json` is the next task's review baseline.
- `data_series.py` owns preparation with one table/window selection/read path, distinct full-array/slice strategies, and a direct source-column normalizer. `generic.py` owns common request composition used once by plugin execution after fresh defaults. Exports remain for T04.
- Owning cohort82 passed in31.71s. All33 old collected IDs retained/moved with identical test AST/parameters; seven meaningful new cases. Thirteen preparation cases plus five Plot characterization cases moved to `test_generic_plot_preparation`; codec case to `test_plot_render_request`; three unchanged shared fixtures to QML-free `generic_plot_fixtures.py`.
- Frozen harness instrumented candidate: all seven semantic fingerprints, loader counts and effective bounds equal baseline. Explicit `row_offset=0` replaces the loader's identical default on direct calls; sole raw call spelling difference is recorded in `instrumented_comparison.json`. No timing acceptance claim.
- Reviewer `/root/t03_review` independently compared37 moved helpers, test bodies/parameters, all12 hashes, executable references and evidence; no material findings. Ruff/maps/links/traceability/generated freshness/diff pass; frozen harness hashes unchanged.
- The provisional characterization module now contains only the graph case, still scheduled to move in T06.

### T04 accepted evidence

- `artifacts/plot_graph_refactor/t04/implementation_report.md`, `implementation_snapshot.json` (13 delta files), `test_dispositions.json`, commands and JUnit/logs record completion. Coordinator verified and copied cumulative58 accepted files to `accepted_files/`, manifest `accepted_snapshot.json`.
- `exports.py` owns exact publication/validated cleanup and one CSV-only uniform-source preflight; generic execution calls its direct owner. Static/data writer bodies retain source selection, batching, cancellation, optional dependencies and fallback order.
- Owning cohort **101 passed**,34.28s, zero failures/errors/skips, including existing QML and headless subprocess cases. Seven new export guards cover window/slice bounds, chunking/cancellation, mixed/missing/non-CSV/PyArrow-absent fallback, one source comparison, and original KeyboardInterrupt despite independent cleanup failures.
- All37 prior IDs/markers accounted; four archive tests moved, five scene/invalidation tests moved, shared cache identity moved, and only the approved sink duplicate merged with the full assertion union.
- Reviewer `/root/t04_review` verified transaction/cleanup AST equivalence, all13 hashes/dispositions/markers, QML class equality, and evidence; no material findings. An in-progress import replacement inside eight QML child scripts was restored exactly before acceptance.
- Ruff/maps/traceability/links/generated freshness/diff pass; frozen harness/protected hashes unchanged; frozen baseline checkout clean. T05 still owns final integration/composed/performance acceptance.

### T05 integration checkpoint and measurement guard correction

- Additional Signal/XY owners70, retained Plot isolated shell1 and native XY QML/shell3 all pass (zero skips/errors). Maps/links/traceability/generated freshness pass. Reviewer independently traced all158 T01 and387 expanded T02 baseline IDs through the migration chain; only the approved sink-test union converges.
- Planned broad fast run: **5842 passed,14 failed,4 skipped**,342s; runner stopped before serial phase. Canonical serial phase subsequently ran using `build_commands('fast')`: **220 passed**,79.03s. Do not describe the complete fast lane as green.
- Seven task-related failures are stale expected catalogue counts and two CL14 navigation corpus expectations. All seven pass frozen d36 baseline (plus27 subtests). Exact IDs/commands: `artifacts/plot_graph_refactor/t05/remaining_fast_commands.json`; baseline proof `baseline_counts_nav.log/xml`.
- Count correction: original T02 writer changed exactly six numeric literals in five tests (four143-to142, builtins125-to124, internal exceptions49-to48). Exact-set/golden assertions unchanged; requested five targets pass with final T15 closure. Evidence `t05/count_correction/tests.log`, `t15_closure.log`, `ruff.log`; reviewer accepts source delta.
- Nav expectation belongs to `tests/fixtures/nav_owner_corpus.json`, CL14. Correct that fixture's focused owner; do not special-case or weaken the two `test_nav_cli` corpus/rank/output-budget tests.
- Four failures were exposed by launcher TEMP under this Git checkout; all pass with normal OS TEMP. Three concern temporary Git repositories/source inventory. The fourth exposed a real provenance-guard enforcement gap, addressed below. Media frame-swap passes serially in both candidate and baseline.
- Viewer-demotion (`graph_canvas_frame_coalescing`) and canvas-crop (`canvas_export_presenter`) failures reproduce identically at frozen d36 and candidate, including error/crop geometry. Preserve as baseline limitations; no unrelated production repair. Evidence `candidate_diagnostics.*` and `baseline_qt_diagnostics.*` under t05.
- Provenance correction independently approved: both benchmark `_origins` guards must require each `ea_node_editor`/`corex` module under its exact selected package directory, not anywhere under the checkout (which could include nested baseline/venv copies). Only the post-measure validation changes; workload, fixtures/reset, sample counts, timed boundaries, counters and output schema remain frozen. Guard tests cover both harnesses/namespaces, valid roots and nested foreign roots.
- Reviewer retrospectively verified every T01 stored origin against the stricter rule: Plot217 instrumented/217 timed modules and graph139/139, all valid. Historical T01 evidence remains valid. Preserve its original hashes; record new accepted harness hashes before any paired timing and revalidate full baseline/candidate instrumentation. No paired timing has started.
- Agent service rejected original benchmark-worker resumption and a fresh worker with `agent thread limit reached`. Reuse the existing T03 worker for the bounded nav/provenance correction group, preserving one writer and independent T05 review. This is an orchestration resource constraint, not a scope/verification relaxation.
- T05 verifier is idle until corrections accepted. Its artifact-only Signal/composed launcher uses the same exact package-root guard; source files unchanged. Existing user COREX/laser-pointer processes are preserved; assess contention before timing.
- Correction group ACCEPTED by `/root/t05_review`: exact five count targets pass; nav fixture-only update passes2 targets+27 subtests; provenance/counter/determinism20 pass (two full benchmark subprocess tests intentionally deselected here). AST proof independently verifies only `_origins` changed in both scripts. Current frozen hashes are recorded above; original T01 hashes/reports remain historical.
- Coordinator hash-verified cumulative67 files and copied them to `artifacts/plot_graph_refactor/t05/accepted_pre_performance_files`, manifest `accepted_pre_performance_snapshot.json`. Review/evidence: `nav_correction/report.md`, `provenance_correction/report.md`, `ast_and_hash_proof.json`, and count-correction logs.
- All writers/checks stopped before performance release. Verifier must revalidate full baseline/candidate instrumentation with current common scripts, retain exact semantic/count parity, then perform five paired runs. No measured-path retuning or second broad-fast run is authorized merely to repeat already-passing cases.

### T05 performance checkpoint - acceptance remains open

- Revised harness full baseline/candidate instrumentation passes: seven Plot semantics/counts/effective bounds and twelve graph results/counters match; strict package roots pass. Only documented direct-table `row_offset=0` spelling differs. `t05/instrumented_comparison.json` and four full reports retain proof.
- All five alternating generic timing pairs completed with prescribed fixtures/sample counts; all source snapshots, dependencies, semantic fingerprints and origins validated. Raw reports and `t05/generic_timing_comparison.json` retained unchanged.
- Initial median changes: memory0.07565 to0.07770ms (all five paired medians slower); full-array0.76665 to0.83095ms (four/five slower); window mixed with one candidate outlier. Table/slice/export medians near baseline. Lower memory/array p95 did not dismiss the median concerns.
- Exactly one confirmation cohort ran for memory/window/array, unchanged200000-row fixtures/five warmups/fifty measurements/five alternating fresh-process pairs. Its omitted prior table scenario changes priming; interpret independently and do not pool with initial samples.
- Confirmation: memory0.07580 to0.07670ms, again all five pairs slower; array0.79115 to0.77060ms with every candidate median faster; window mixed/outlier reversal. Reviewer finds memory a reproducible small regression (+2.05us initial/+0.90us confirmation), which blocks acceptance under the chosen policy. Array concern not reproduced; no stable window regression established.
- `t05/performance_status.md` records the open gate and absolute metrics. All timing is paused before Signal/composed checks. No third unchanged-code acceptance cohort or measurement retuning is authorized.
- Original T03 writer owns **artifact-only narrow attribution**, comparing baseline/current builder/options/preparation with the exact frozen memory fixture. No source edits until an evidence-backed proposal is approved. Mapping/Sequence bindings are both collections.abc; no per-call data-series import or extra property-copy count has been found. Module-qualified lookups are only a hypothesis, not a proven cause. Diagnostic variants must remain separate from acceptance measurements.
- Attribution completed in `t05/request_attribution/report.md`: baseline/current have identical288001 profiled calls/1000 requests. Direct-owner-binding variants did not reliably help; exact instruction-level cause remains unresolved and no import churn is recommended. A real removable cost is two deep copies of freshly empty fallback mappings, already present in baseline.
- Independent reviewer approved a two-line optimization in existing `generic._mapping_property`: after unchanged supplied-Mapping comprehension, return a fresh `{}` for an empty default, otherwise keep existing deepcopy. All four actual callers use plain-dict defaults; nonempty/nested copies and exception order stay intact. Diagnostic14-case semantic checks and22-to20 deepcopy count reduction support the proposal, but are not acceptance evidence.
- Source edit released to original T03 writer for that helper plus focused request/default/error/counter coverage only. Frozen harnesses/workloads remain unchanged. After independent correction review, run a new full five-pair/seven-scenario acceptance cohort against the changed candidate; retain the earlier failing and confirmation reports. No repeated unchanged-code cohort or timing-threshold relaxation.
- Actual correction ACCEPTED by `/root/t05_review`: `generic.py` differs by exactly the approved two lines; three appended public-request test functions add eight cases, with all prior test ASTs unchanged. Affected62 tests and focused8 pass, zero failures/errors/skips; Ruff/diff pass. New tests prove freshness, nested isolation and original copy-exception identity. Actual count profile removes two empty deep copies per request.
- Corrected generic SHA `9e8c66e51ab9857eef17dbec0c9695c7c819de8edd07278ef50e31eb1d14d8db`; preparation-test SHA `ff64c4feba50102c222e7064186f96cb91a8b2200e978d2bd2e56858470ebbed`. Evidence `t05/request_correction/report.md`; no map ownership/path change, no harness change.
- Coordinator captured/hash-verified revised67-file snapshot in `t05/accepted_request_correction_files` with `accepted_request_correction_snapshot.json`. Initial67-file snapshot and failed measurements remain intact. Renewed exclusive verification must use this new candidate snapshot; source remains frozen until results reviewed.
- Corrected full five-pair/seven-scenario batch completed with all hashes/semantics/counts/origins valid. Memory median is now0.07490 to0.07385ms, all five candidate medians lower: prior median regression resolved. Array median0.78455 to0.77535ms. Source stays frozen.
- New tail concern remains open: memory p95 0.13683 to0.16030ms (+23.47us), array1.148345 to1.221855ms (+73.51us), both five/five pairs higher in this corrected cohort. Historical absolute tails vary substantially, so reviewer requires equivalent confirmation before attribution or acceptance. Other corrected-case metrics are retained in `t05/corrected_performance/generic_timing_comparison.json` and must not be selectively omitted.
- A five-preparation-only confirmation was initially launched. Verifier then identified that the frozen harness primes every selected scenario before measuring, so omitting exports changes backend/heap priming. BEFORE any partial tail metrics were provided or used, coordinator corrected the protocol: stop that partial batch after its active owned child, retain raw reports as diagnostic only, and run exactly one full seven-scenario/five-pair confirmation matching all original priming/settings/counts/order. Reviewer agrees this is a setup correction, not result-driven selection. At action the pair4 candidate child was active; only task launcher processes were suspended to prevent further scheduling, with child/user apps left untouched.
- The valid full corrected confirmation is the only remaining unchanged-source generic acceptance confirmation. No further cohort or threshold adjustment is authorized merely to seek favorable timing. Signal/composed checks remain outstanding and cannot erase the tail concern.
- Equivalent full seven-scenario/five-pair confirmation completed: all hashes/samples/semantics/origins valid. Memory p50 0.08160 to0.08235ms has mixed directions; p95 0.16767 to0.153595ms with3/5 candidate tails lower. Its earlier repeatable median issue and subsequent tail concern are closed as nonpersistent after the correction.
- Array remains unresolved: fullconfirmation p95 1.39158 to1.474655ms (~6% higher;4/5pairs), p50 0.77700 to0.78590ms with mixed directions. Across corrected full and equivalent confirmation,9/10 paired array tails/means are slower. Reviewer does not permit a generic performance pass yet. Evidence `t05/corrected_full_confirmation/generic_timing_comparison.json`; no third unchanged-source generic acceptance cohort.
- Remaining-gates verifier finished and stopped all owned processes. Signal five pairs show no consistent slowdown: median23.412 to23.476ms, p95 24.995 to24.547ms, mixed paired directions, unchanged script/strict origins.
- Four valid composed Bar runs (direct/filtered baseline/candidate) have real plot IDs,4 warm fullscreen opens/5 closes, errors empty, actual offscreen/Software/QQuickWidget. Source/cache entrypoint counts are exactly equal across revisions but nonzero. Single-pair aggregate rebuild medians direct30.06 to38.94ms and filtered24.60 to27.17ms, with shifting move tails, are not a no-regression or causal attribution claim.
- Measurement limits: composed full_rebuild wraps rebuild_models AND processEvents; class-wide counters include cache hits, tabular UI and queued/background tasks. They do not prove physical scans or Plot-only I/O. Payload/scene phase arrays have zero samples: unavailable, not zero cost. Its run helper can exit while active_submission exists but active_run_id is empty, so ready-only run_ms is informational without admission/terminal-success evidence. Preserve separate real runtime correctness proofs.
- An initial composed artifact-launcher multiprocessing failure was excluded and fixed only in the artifact launcher with a guarded entry point; owned hung helpers were stopped, user apps preserved. Partial five-preparation confirmation remains diagnostic-only in `corrected_performance/diagnostic_batch_stop.json`; it was never used for acceptance.
- Exact source projection proof: `test_tabular_perf_guards::test_payload_builds_perform_no_source_io_at_all` instruments uncached scan/conversion/text reads; async work is separately proved by `test_async_auto_preview_build_converts_once_and_respects_budget`. Scene metadata/pending separation is covered by the moved surface-integration test. Reviewer confirms every `kinds/plot.py` function body equals d36; only declaration import changed. Guarantee is no added tabular data reads, not zero filesystem stat activity.
- Handoff and limits: `t05/verification_report.md`, `performance_status.md`, `correctness_status.md`, `remaining_gates_comparison.json`. Original T03 owner now has an exclusive diagnostic window for the exact array fixture/all priming: per-function CPU, actual thread-clock granularity, GC request/inspection correlation and wall-versus-thread time. No product/harness edits or acceptance rerun; optional disabled-GC control is diagnostic only. Review any proposal before source edits.

Baseline inventory plus removed/added ID comparison is authoritative; counts alone do not prove coverage.
Every changed ID must map to a destination, preserved scenario/assertions, and proving evidence.
The duplicate Plot sink-mode test may merge, retaining default empty suppression reasons and lightweight-canvas suppression as well as enabled/disabled behavior. The user-approved Scatter retirement additionally allows Scatter-only cases to become retirement/Signal tests; all shared generic behavior migrates to retained fixtures and remains covered.

| Cohort | Required destination / disposition | Status |
| --- | --- | --- |
| Plot declarations/catalog | Retain `test_plot_node_contracts` | pending |
| Plot preparation | `test_generic_plot_preparation` | accepted T03; exact IDs in t03/test_dispositions.json |
| Request codec | `test_plot_render_request` | accepted T03 |
| Plot archive/publication | `test_generic_plot_exports` | accepted T04 |
| Plot scene projection | Existing `test_plot_surface_integration` | accepted T04; sink duplicate assertion union retained |
| Shared cache identity | Existing `test_plot_auto_preview_service` | accepted T04 |
| Script parser/declaration | Retain `test_python_script_declaration` | pending |
| Direct Script/dynamic graph edits | `test_graph_node_reconciliation` | accepted graph group |
| Script scene/history/payload | `test_python_script_scene_integration` | accepted graph group |
| Script fragment/serialization | `test_python_script_persistence` | accepted graph group |
| Registry normalization | `test_graph_registry_normalization` | accepted graph group |
| Real persistence/runtime/fragment tests | Retain in existing owners | accepted graph group |
| Shell/real canvas/headless export | Retain existing selectors and assertions | retained; focused integration accepted |
| T01 provisional characterization | Five Plot collected cases to preparation; graph case to reconciliation; empty provisional file removed | accepted T03 + graph group |

T01 characterization source is `tests/test_plot_graph_ownership_characterization.py`.
Plot IDs: `test_direct_table_mapping_does_not_restrict_full_source_export_provenance`, `test_window_provenance_keeps_original_columns_and_minimum_positive_limit[1-1]`, `[3-2]`, `[0-2]`, and `test_runtime_literal_columns_and_inspector_split_columns_are_distinct_policies`.
Graph ID: `test_script_apply_preserves_instance_order_but_registry_load_canonicalizes_it`.
Retain isolated plugin-generation roots when moving the graph fixture.

## History-to-behavior constraints

| Commit | Preserved behavior | Proof owner |
| --- | --- | --- |
| `36c9ea6b` | Complete table schema; explicit windows; bounded arrays; ND axes; full streaming export | Plot preparation/export and tabular guards |
| `a88bcea3` | Scientific values; separate Signal Plot contract | Existing scientific/Signal rendering/input owners unchanged; T02 declaration discoverability updated |
| `09502b9e` | Clean Line Plot retirement without alias or automatic migration | Scatter absence/load-rejection and Signal-workflow tests |
| `c218649b` | Candidate-first atomic Script Apply | Reconciliation and Script integration |
| `f2fc1818` | Source-backed canvas ports; dirty drafts; Apply/Undo/Redo | Retained Script editor isolated target |
| `9b8bb83f` | Dynamic port order and wire/state identity | Reconciliation plus persistence integration |
| `7235d8ef` | Forwarded types; semantic reset versus forced wire prune | Type forwarding/rewire and reconciliation |
| `2f03ea69` | Independent mutable defaults/readiness; open responsiveness gates | Catalog/default tests; existing performance status unchanged |

## Performance and review decisions

- Same frozen harness, interpreter, dependency set, fixture content, backend, and source-origin verification for each baseline/candidate pair.
- Five process pairs alternate AB/BA. Preparation/graph: five warmups, fifty operations. Export: one warmup, ten operations.
- Count/fingerprint instrumentation runs separately from timed operations; fixtures/reset stay outside measured intervals.
- Known fixture IDs/URIs may be normalized for semantic comparisons only when raw identity and source content hashes are retained; mapping/provenance options must remain exact.
- No concurrent tests/builds/benchmarks during performance timing.
- Structural gates and caller-specific policies in the plan are mandatory. Repeated timing regression returns to the original writer; do not weaken tests or acceptance.
- Independent reviews, findings, fixes, and acceptance evidence will be recorded here once per task.

## Deferred findings

Graph-scene method rebinding, artifact rename/store redesign, worker execution decomposition, Mechanical runtime adapters, fullscreen tabular sessions, new Signal rendering features, and global shell-fixture cleanup remain outside this change. Signal discoverability/documentation and Scatter retirement are now explicitly included.
