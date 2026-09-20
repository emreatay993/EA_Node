# Unused Dynamic Inputs and Execution Identity

## Summary

Implement the approved shared contract so adding or removing unused Model Viewer
scene inputs preserves current computation and viewer state. The recorded bug
changes the viewer's properties, interface and contract identities despite the
executor ignoring empty inputs. Existing presentation and upstream-reuse fixes
remain in place. Baseline: `b7f67fc4991420b10e18238b157c19963b4b9d58`.
The user subsequently explicitly included reuse of imported CAD data across real
populated-scene connection changes in the default process-isolated runtime.

## Key Changes

- Share one execution-owned projection of participating ports and properties
  between graph invalidation and solution identities; preserve full authored
  snapshots for execution, dispatch validation and persistence.
- Enable connected-input semantics for Model Viewer. Python Script source edits
  and Stream Gate output edits remain computational. Custom nodes may opt in.
- Preserve viewer sessions, sources, camera, selections, previews and timings on
  empty-slot edits; reconcile labels as presentation state.

## Public Interface Changes

`DynamicPortGroupSpec.execution_policy` defaults to `all_ports` and permits
`connected_inputs` for optional list-backed data inputs with no conflicting
source-code, readiness, provenance, sensitive or property-default dependencies.
An enabled connection participates even when its current value is unavailable.
Advance solution-key and interface revisions; no project-file migration.
This extends the existing trusted registry metadata surface; it does not export
metadata constructors or a new dynamic-topology decorator through public `corex`.
Native-handle results retain authenticated resources for exact CURRENT reads;
they do not enter general solution-key REUSE indexes. Opaque object identity
does not establish value equality across fresh imports. Full handle/output
digests remain intact, declared `never` lifetimes remain excluded, and
detached-only result reuse/nondeterminism behavior stays unchanged.

## Execution Tasks

| Task | Status | Owner | Accepted evidence / next action |
| --- | --- | --- | --- |
| T01 Shared declaration and computation contract | Accepted | dynamic_execution | 182 tests + 108 subtests; final dedicated suite 39 passed; review_dynamic_execution found no actionable issues |
| T02 Viewer presentation continuity | Accepted | viewer_presentation | Prior 150 + 31, service 18 + 5 and three host checks passed; fresh-shell registry initialization added with two focused passing checks and integration review |
| T03 Real workflow proof | Accepted | dynamic_workflow_proof | Empty-input/inflight proof accepted; populated default-process acceptance completed by T04/T05 below |
| T04 Process-owned solution resource reuse | Accepted | process_cad_reuse | Final 161 tests + 110 subtests; managed-artifact follow-up 43 passed; independent review accepted; process capability-gated and external stdio offers disabled |
| T05 Default-runtime acceptance and closeout | Accepted with recorded broad-gate limits | Coordinator | Final real workflow 1 passed (8.843s); parallel 6088 passed, 4 skipped, 3 failures (two baseline, one isolated recheck passed); serial 220 passed. Docs/maps/lint checks passed |

### T01 Shared declaration and computation contract

- Goal: identity and invalidation agree on unused dynamic inputs.
- Preconditions: approved plan and confirmed baseline checkout.
- Conservative write scope: node declarations/validation/instance resolution,
  execution projection/graph comparison/plan/identity and focused tests.
- Deliverables: shared policy, Model Viewer opt-in, identity revisions, custom
  node and negative-family coverage.
- Verification: declaration, graph-change and solution-identity tests; independent
  diff review against baseline.
- Non-goals: viewer presentation, unrelated node reclassification, compatibility
  shims, persistence migrations.
- Packetization notes: one coherent writer; no external packet set.

### T02 Viewer presentation continuity

- Goal: graph/history label changes reach current sessions without recomputation.
- Preconditions: T01 accepted and its semantics available.
- Conservative write scope: viewer bridge/service/backend/binder/host,
  preview-state cache, mutation aftermath and focused viewer/history tests; no
  execution identity redesign.
- Deliverables: live scene labels and ordinal shifts, preserved source ownership
  and session state on empty-slot edits.
- Verification: viewer bridge/backend/service and mutation tests, independent review.
- Non-goals: new UI controls, native rendering redesign, session lifecycle changes.
- Packetization notes: fresh writer after T01; reuse existing command flow.

### T03 Real workflow and integration closeout

- Goal: prove the reported user workflow and publish accurate implementation evidence.
- Preconditions: T01 and T02 accepted.
- Conservative write scope: shell/worker regression tests, affected docs/maps and
  generated route index; implementation fixes go back to the relevant owner.
- Deliverables: generated CAD fixture regression with exact run counts, unchanged
  facts/session/view state, real populated connection updates, final outcome.
- Verification: focused shell/worker tests, `fast --summarize-output`, documentation
  and map checks; fresh integration review.
- Non-goals: package release and unrelated dirty files.
- Packetization notes: one writer; coordinator alone updates this progress table.

### T04 Process-owned solution resource reuse

- Goal: unchanged CAD imports remain reusable in the default process-isolated
  runtime when populated scene connections change.
- Preconditions: user explicitly authorized this runtime extension; T03 captures
  the existing non-reusable CAD result and has released write ownership.
- Conservative write scope: execution backend/client/worker/protocol/resource
  lifetime owners and focused runtime, protocol and resource tests. Detailed
  scope follows the bounded architecture pass.
- Deliverables: worker-owned retention before run cleanup, verified host reuse
  and release, cleanup on rejection/eviction/retirement, generation-safe reset.
  Stage bounded original-to-leased handle offers before settlement publication;
  keep original wire outputs for stable reused digests. Host validation claims
  offers locally and finalizes nonblocking after callbacks. Do not perform a
  synchronous lease RPC from the sole event-reader thread. Bind offers to the
  physical client generation separately from worker-local handle generation.
- Verification: real process repeated/partial runs, changed source and stale
  generation rejection, bounded lease cleanup, independent source review.
  Connected file paths must carry their captured source provenance through
  native results; changed bytes at the same path must reject both reuse and
  READ_CURRENT boundaries. Disabling all connected-path retention would not
  satisfy the required path-to-CAD workflow.
  Force-recomputing identical property-backed CAD input must publish fresh
  handles without a false nondeterminism warning; subsequent downstream work
  must read the newly selected CURRENT result.
- Non-goals: switching the default backend, weakening provenance or handle
  validation, retaining arbitrary resources indefinitely, CAD-specific bypasses.
- Packetization notes: fresh single writer, followed by independent review.

### T05 Default-runtime acceptance and closeout

- Goal: satisfy the original populated-scene upstream reuse acceptance in the
  default runtime, then document and verify the integrated change.
- Preconditions: T04 resource ownership implementation accepted.
- Conservative write scope: existing T03 shell/runtime tests, affected
  docs/maps and generated route index; source fixes return to their owner.
- Deliverables: exact CAD/viewer/downstream execution counts for populated
  connect/remove in the default backend; final outcome and limitations.
- Verification: real workflow, cross-route fast lane, map/traceability/link
  checks and fresh integration review.
- Non-goals: packaging or unrelated baseline repairs.
- Packetization notes: restore T03 owner for its proof follow-up; coordinator
  alone records closeout.

## Work Packet Conversion Map

None. This task uses the approved plan directly, not external work packets.

## Test Plan

- Empty add/remove at different positions, disabled edges, undo/redo, stable
  solution keys, later reuse, queued and active work.
- Actual connect/disconnect, populated removal, connected ordering and properties
  invalidate as expected; Python Script and Stream Gate remain computational.
- Invalid policy combinations fail closed; a synthetic custom node proves shared
  behavior without a Model Viewer type special case.
- Real shell/worker CAD workflow retains upstream results and viewer state with
  zero additional dispatches on empty-slot edits.

## Assumptions

- Preserve pre-existing changes to AGENTS.md, the Physical Simulation spec-index
  entry and plan, and the strain-candidate CSV.
- Use the project venv; focused tests precede the cross-route fast lane.
- Complete authored structure remains available for validation and runtime use.

## Final Outcome

Implemented and independently reviewed. Empty scene add/remove/history edits
preserve execution counts, retained facts/keys/outputs/timings, non-default camera
and scene transport. On populated connect/remove, the default process runtime
dispatches once and executes only Model Viewer and its downstream Panel; path
and CAD records remain current without a CAD import. The final real test has no
backend override or temporary acceptance gate.

The two integration adapters are fixed as well: fresh shell composition installs
the registry immediately, and viewer settlement decoding consumes canonical
typed results while retaining type, status, singleton and identity validation.

| Verification | Result |
| --- | --- |
| Shared declaration/graph/identity owner suites | 182 passed + 108 subtests; final expanded dynamic-input file 39 passed |
| Viewer service/backend/binder/cache/history/host unit suites | 150 passed + 31 subtests; camera refinement service recheck 18 + 5; three isolated host tests passed |
| Fresh-shell registry and existing replacement guard | Two focused checks passed |
| Final typed-settlement bridge unit suite | 43 passed + 29 subtests |
| Final process resource/CURRENT/store/worker/codec/message suites | 161 passed + 110 subtests |
| Final managed-artifact/resource/identity/catalogue follow-up | 43 passed; actual managed CAD/FE CURRENT reuse and tamper rejection included |
| Final real default-process CAD shell workflow | 1 passed in 8.843s on final source |
| Queued/preparing/active same-viewer transitions | 14 passed |
| Exact shell target IDs and ownership declarations | 2 passed |
| Source/test scoped Ruff and diff checks | Passed |
| Final fast parallel lane | 6088 passed, 4 skipped, 3 failures; limits below |
| Manifest-owned fast serial lane | 220 passed in 73.86s |
| External handshake isolated recheck | 1 passed in 5.23s |
| Agent maps, route index, traceability, Markdown links | Passed |

The principal reproduction is:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\venv\Scripts\python.exe -m unittest tests.test_shell_run_controller.ShellRunControllerTests.test_unused_viewer_inputs_preserve_real_cad_workflow -v
```

The frozen runtime proving suite is:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_process_solution_resources.py tests/test_runtime_retained_sources.py tests/test_solution_store_session.py tests/test_runtime_current_results.py tests/test_execution_worker.py tests/test_protocol_codec.py tests/test_run_messages.py -q -n 0 --tb=short
```

Managed project-file identity uses the same verified authored-path admission as
execution, symmetrically on host and worker. Raw artifact strings remain rejected
by the lower-level resolver. Both ordinary and project-managed CAD/FE results
support authenticated CURRENT reads; changed or tampered bytes cannot be reused.

Process offers are explicitly capability-gated; this change does not enable
external-stdio resource offers. Native results remain session-only CURRENT
resources, not durable or historical-key reuse entries. Unrelated working-tree
changes are preserved outside the requested main-branch publication.

### Broad verification

The first parallel fast run reported 6081 passed and eight failures. The six
task-related failures were corrected: authored managed-path provenance now
uses admitted descriptors, the missing-path assertion checks the actual failed
path, and the generated catalogue includes its two execution-policy fields.
All six passed the 43-test follow-up.

The final parallel run reported 6088 passed, 4 skipped and three failures in
293.85s. Two canvas failures match the untouched baseline, as detailed below.
The other was
`tests/test_viewer_invalidation_lifecycle.py::test_prepared_empty_viewer_run_project_close_and_same_workspace_reopen[external_subprocess]`,
which failed its external Python identity handshake under parallel load and
passed its immediate isolated `-n 0` recheck. The standard runner stops after a
failed parallel phase, so its unchanged manifest-generated serial command was
run separately through `build_commands("fast")` and `run_command_summarized`;
all 220 serial tests passed. This is not a claim that the unmodified broad fast
command is fully green.

### Baseline shell limitations

Both `ViewerSessionBridgeShellIntegrationTests` below exit with code 1 and no
traceback on the changed checkout and on an untouched detached checkout of
`b7f67fc4991420b10e18238b157c19963b4b9d58`:

- `test_new_project_clears_context_bound_viewer_session_state`
- `test_restore_session_keeps_saved_viewer_project_recent_without_reopening`

Each was run alone with `QT_QPA_PLATFORM=offscreen`, the original project venv,
and `python -m unittest tests.test_viewer_session_bridge.<class>.<method>`.
The baseline commands additionally used `-X faulthandler -v`; no fault traceback
was emitted. Baseline package import location and clean Git state were verified.
These are existing non-passing checks, not successful acceptance evidence.

The first fast lane also found two canvas failures reproduced identically on
the clean baseline checkout with `QT_QPA_PLATFORM=offscreen` and `pytest -n 0`:
`tests/test_canvas_export_presenter.py::test_capture_canvas_view_pngs_crops_to_workspace_bounds_by_default`
and `tests/test_graph_canvas_frame_coalescing.py::GraphCanvasFrameCoalescingTests::test_deselected_proxy_pointer_sequence_has_no_latent_inline_request`.
The baseline result was 2 failed in 12.88s; source imports and clean Git state
were verified before that temporary checkout was removed.

Two broader shell-catalog hygiene checks also expose an existing missing
registration for `test_graph_search_close_returns_keyboard_focus_to_canvas`:
`test_shell_isolation_catalogs_cover_manifest_owned_shell_surfaces` and
`test_shell_target_groups_are_complete_and_disjoint` in
`tests/test_shell_isolation_phase.py`. The method exists at baseline HEAD in
`tests/main_window_shell/shell_basics_and_search.py` but has no corresponding
entry in `tests/shell_isolation_main_window_targets.py`; both files are untouched
by this task. The wider hygiene/runner command reported 44 passed, 4 subtests and
these two failures. The new CAD target's exact catalog and ownership checks pass.
