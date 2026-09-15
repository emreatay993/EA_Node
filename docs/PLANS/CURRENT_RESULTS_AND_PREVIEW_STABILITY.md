# Reliable incremental execution and stable previews

Status: **IMPLEMENTED AND REVIEWED — TASK REGRESSIONS RESOLVED; BASELINE LINT EXCEPTION**

## Summary

Implement the approved shared fix for unnecessary upstream execution and
presentation-only preview interruption. Baseline is `2f03ea69` on `main`.
Keep one coordinator, one active writer, task-scoped implementation workers,
and independent review of the runtime changes and integrated result.

Planning probes established that changing, disconnecting, or reconnecting a
Panel feeding Signal Plot's title reruns Tabular Input. Graph comparison finds
the correct downstream roots, but table references fail resource retention and
current-result consumption. A real shell probe also established that moving the
Panel leaves execution counts unchanged while repeatedly replacing the preview
URL and disabling/recreating the Media Panel renderer. The user's exact transient
stale-message report remains an integrated regression requirement.

| Task | Owner | Status | Evidence / next action |
| --- | --- | --- | --- |
| T01 Retained-resource validity | retained_resource_contract | Accepted | 108 focused tests pass; independent re-review closed both findings |
| T02 Runtime integration | runtime_integration | Accepted | 250 tests / 110 subtests pass; independent re-review clear |
| T03 Immutable preview stability | immutable_preview | Accepted | 32 owning tests plus permanent real gesture proof pass |
| T04 Integration and documentation | workflow_acceptance / coordinator | Accepted | Real QML/render proof; 19 broad-run failures resolved; 150-test owning recheck and 220-test serial phase pass |

## Key Changes

- Preserve semantic graph comparison, downstream invalidation and `READ_CURRENT`.
  Distinguish current-result consumption, computational reuse and durable
  persistence eligibility through one shared retained-resource validator.
- Support source-backed table/array references and window/slice wrappers with
  exact resolver, canonical source, object, normalized options and content
  fingerprint bindings. Reuse bounded provenance facilities; size/mtime IDs alone
  do not establish content identity.
- Validate source bindings at preparation, worker preflight and actual reads.
  Accepted references must never alias changed data under an old identity.
  Preparation-time rejection recomputes required ancestry. A change after
  preparation follows existing safe failure handling without modifying attested
  decisions or introducing a retry subsystem.
- Make immutable ImageValue preview registration idempotent within the active
  provider. Re-register after cache loss/replacement or changed content. Preserve
  mutable viewer-preview revision semantics.

## Public Interface Changes

- Add typed retained-source bindings to internal accepted-output integrity
  commitments; update host and worker serialization/validation together.
- Keep node declarations, `affects_execution`, `solution_reuse_scope`, execution
  commands, Trigger boundaries and forced-run policies.
- No new user setting, execution action, general resolver-registration API or
  durable-persistence permission.

### Integration refinements established by verification

- Keep output resource bindings separate from inherited source-provenance
  bindings and provenance completeness. Detached materialized results retain the
  source versions that produced them, so reading a current downstream result
  cannot prune a changed or unverified source. All metadata participates in
  accepted-output commitments and existing byte budgets.
- Connected file inputs do not include an effective file hash in the existing
  captured solution key. Their valid results remain CURRENT-consumable, while
  computation reuse is conservatively disabled for those nodes and their
  descendants, including cold-generation adoption. Effective source versions are
  captured before source execution; stale references are never re-blessed.
- Preserve PlotValue's full run provenance and transport digest. Session records
  compare computational plot content separately from run occurrence so a
  same-content recomputation publishes a fresh current record without a false
  nondeterminism error. Different data/settings/preview/producer identity still
  triggers the original guard; old XY-session provenance remains rejected.
- Source hashing occurs outside the runtime lifecycle lock. Acceptance rechecks
  generation, registry, run context and project binding before publishing.
- Eligible detached durable output retains its existing source/dependency key
  protections without redundant session lineage metadata. Session fallback keeps
  lineage, and source references themselves cannot become durable outputs.

## Execution Tasks

### T01 Retained-resource validity

- Goal: Establish authoritative validity checks for retained source-backed data.
- Preconditions: Confirm baseline and preserve unrelated dirty work.
- Conservative write scope: Retained resource/value contracts, tabular loader
  binding/validation and directly owned tests.
- Deliverables: Typed bindings, shared validation, nested-reference support,
  strict reads rejecting changed-content aliasing.
- Verification: Unchanged, changed, missing, unknown-resolver and nested sources;
  content tampering and late changes without full materialization.
- Non-goals: Scheduling and UI changes.
- Packetization notes: One coherent task; P01 if later packetized.

### T02 Runtime integration

- Goal: Consume valid current outputs without invoking their producers.
- Preconditions: T01.
- Conservative write scope: Runtime settlement, solution store, preparation,
  backend resource handling, accepted-output contracts, worker admission/tests.
- Deliverables: Shared resource policy and binding commitments; consumed-port
  validation; currentness, identity, lifetime and attestation enforcement.
- Verification: Real-worker title edit/connect/disconnect with exact node counts,
  unchanged upstream record identities, and negative admission tests.
- Non-goals: Changing force/Trigger/side-effect policy or durable eligibility.
- Packetization notes: P02; independent review before acceptance.

### T03 Immutable preview stability

- Goal: Keep existing content continuously visible during presentation edits.
- Preconditions: Confirmed preview-revision reproduction; independent of T02.
- Conservative write scope: Immutable image adapter and owning preview/QML tests.
- Deliverables: Stable URLs and renderer instances for unchanged content;
  correct refresh after content change or cache loss.
- Verification: Repeated lookup, equivalent images, provider replacement/eviction,
  Panel movement and undo/redo.
- Non-goals: Delaying genuine stale indications or changing mutable previews.
- Packetization notes: P03; retain one active writer.

### T04 Integrated acceptance and documentation

- Goal: Prove the complete user workflow and document corrected ownership.
- Preconditions: T02 and T03.
- Conservative write scope: Owning runtime/shell/QML regressions, agent maps,
  specification index and this acceptance record.
- Deliverables: End-to-end acceptance evidence and updated ownership documents.
- Verification: Focused suites, real QML gestures and rendered inspection,
  independent integration review, one summarized fast run, map/traceability/links.
- Non-goals: Unrelated performance redesign or publication.
- Packetization notes: P04; no packet manifests unless requested.

## Work Packet Conversion Map

No packet set is needed. If requested later, use P00 for bootstrap and map
T01-T04 directly to P01-P04.

## Test Plan

Use Tabular Input -> Signal Plot -> Media Panel plus Panel -> plot title.

| Action after initial settlement | Expected execution | Presentation |
| --- | --- | --- |
| Move/resize/format title Panel | None | Stable plot, grips, URL and renderer |
| Change title text | Panel, plot and affected downstream consumers | Table remains current |
| Connect/disconnect title | Plot and affected downstream consumers | Upstream data remains available |
| Change source or parsing settings | Table and affected downstream consumers | Genuine stale results replaced |
| Force recompute | Existing force policy | Normal execution feedback |

Exercise Enter/OK, unchanged text, canceled drafts, real drag gestures,
connections, undo/redo and edits while legitimate Auto work is queued. Observe
every relevant QML state transition as well as final output: count dispatches,
invalidations, starts and settlements; preserve unaffected record IDs, freshness,
outputs and timings. Verify continuous renderer identity/activity and no false
stale placeholders. Include source-backed nested references, mixed consumed and
unconsumed outputs, changed/missing sources, generation replacement, forged
payloads, late mutation, and explicit forced execution.

## Assumptions

The solution applies across nodes carrying the supported resource types. Plot
titles remain computational. Source freshness and resource protections remain
enforced. Preserve pre-existing changes in AGENTS.md, the specs index, canvas
snapshot fixture, physical simulation plan and strain-candidate CSV. Publication
was outside the initial implementation scope; the user subsequently requested
committing these task-owned changes to `main` and pushing this repository.

## Final Evidence

Implementation, focused verification and independent integration review are
complete. The broad run and its targeted follow-ups are recorded below without
claiming a repeated all-green parallel run.

### Accepted planning and contract evidence

- Actual offscreen QML mouse drags move the title Panel by `(30, 10)` three
  times. The baseline keeps solution state current and execution counts unchanged
  but changes preview revisions `2 -> 4 -> 6 -> 8`, disabling/recreating the
  renderer each time. Keep the title Panel away from the large Tabular node body
  in gesture fixtures so the mouse hits the intended surface.
- T01 focused check: **108 passed, 11 warnings** (26 retained-resource cases
  plus 82 existing tabular loader/cache/ref/extraction/preview cases). Independent
  review identified and the worker corrected pre-yield stream validation and
  incomplete external HDF5 provenance; independent re-review closed both findings.
- Source-bound HDF5 retention is limited to direct hard-link dataset paths whose
  storage is inside the container. VDS, external raw storage and non-hard-link
  paths remain ineligible for retained reuse; ordinary fresh loads still work.
- T03 image, media-source and viewer-preview suites: **32 passed**. Matching
  immutable content now returns its existing URL before decode/publication;
  cache loss, provider replacement and changed content still register normally,
  and mutable viewer previews retain their revision behavior.
- T02 runtime/current-results/store/contracts/protocol/worker/XY/resource suites:
  **250 passed, 110 subtests**. Independent re-review closed lifecycle-lock,
  cold-generation eligibility, detached-source lineage and durable-promotion
  findings. Real-process regressions include title edits, wire reconnects,
  connected file paths, changed source bytes with preserved stat fields,
  materialized intermediates, forced execution and accepted current records.
- T04 existing isolated shell target: **1 passed**; related Panel/Media QML suites:
  **9 passed**. The regression uses actual mouse/key events for three body drags,
  Enter/OK/cancel, Ctrl-drag disconnect and reconnect, plus Fit Width, formatting,
  undo/redo, queued Auto and source replacement. It observes every relevant
  renderer/grip transition and requires genuine computational updates to become
  stale before replacement. No synthetic wire-state update remains.
- The coordinator inspected the legible 1800x1000 offscreen QML render at
  `artifacts/current_results_preview/acceptance.png`: the final connected graph
  shows the queued title and newly descending source data in Media Panel without
  a placeholder. The render and `before-wire.png` are ignored local evidence.
  This is actual QML behavior/rendering proof, not hardware performance acceptance.
- One summarized fast integration run exercised `fast.pytest`: **5,558 passed,
  4 skipped, 19 failed** in 320.52 seconds. The failures identified three precise
  follow-ups: success-path source bookkeeping reached SSH failure reporting;
  the saved-property execution test's minimal constructor bypass needed its new
  spec/state; and an NPY repeat assertion still expected source reuse to fail.
- Failure/blocked reporting now avoids successful-result source capture and I/O;
  completed/empty outcomes retain their source guards. SSH redaction tests also
  prove no validator is called. The artifact fixture now supplies the actual
  contract state, and the NPY test requires reuse, no extra starts, unchanged
  records/outputs and current facts. Independent re-review accepted these fixes.
- The exact failing cohort passed **19/19**. Its complete owning non-slow cohort
  passed **150 tests and 28 subtests**, with one slow case deselected, in 84.46
  seconds. The parallel broad phase was not repeated after these bounded fixes.
- The previously unrun manifest-owned `fast.serial.pytest` phase was continued
  through `build_commands("fast")` and `run_command_summarized`: **220 passed**
  in 81.20 seconds. Both broad phase logs are retained in
  `artifacts/verification_logs/20260914_184028/`.
- Changed-file Ruff, whitespace, agent-map/route-index, traceability and
  Markdown-link checks pass. Final map/traceability/Markdown/verification-runner
  hygiene passed **148 tests and 19 subtests** after index registration.
- Whole-package Ruff has **five pre-existing F821 reports** for `QWidget`
  annotations in `ea_node_editor/execution/plot_backend_pyvista.py`. That file is
  unchanged from baseline `2f03ea69`; linting its exact `git show` baseline content
  reproduces all five reports. This unrelated lint issue is preserved. It does
  not affect the passing task-owned runtime, QML or serial verification.

### Focused reproduction commands

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_retained_resources.py tests/test_runtime_retained_sources.py -q
$env:QT_QPA_PLATFORM = "offscreen"
.\venv\Scripts\python.exe -m pytest tests/test_shell_run_controller.py::ShellRunControllerTests::test_media_toolbar_history_and_bulk_edits_preserve_real_workflow -q
Remove-Item Env:QT_QPA_PLATFORM -ErrorAction SilentlyContinue
.\venv\Scripts\python.exe -m pytest tests/test_execution_artifact_refs.py tests/test_ssh_sftp_runtime.py tests/test_signal_plot_scientific_integration.py tests/test_runtime_retained_sources.py tests/test_execution_worker.py -m "not slow" -q
```

## Follow-up: Keep the last completed plot visible during updates

Status: **IMPLEMENTED AND REVIEWED**.
Baseline: `9e43e6e9`.

The user provided a video changing Signal Plot Width and Font size, then approved
keeping the last completed plot visible with an Updating indicator and requested
commit/push to this repository's `main`. This changes the earlier presentation
policy that deliberately hid previews during genuine computational updates; it
does not change runtime freshness, scheduling, or accepted-output authority.

| Task | Owner | Status | Verification / next action |
| --- | --- | --- | --- |
| F01 Canvas presentation and regressions | plot_update_preview | Accepted | 195 tests / 28 subtests; final projection/source/shell cohort 47 passed; decoder/capture follow-ups pass |
| F02 Review, documentation and publication | Coordinator / independent reviewer | Verified for publication | Final re-review clear; common surface/tooltip 151 tests / 35 subtests and docs/lint checks pass; user-authorized main publication |

- Keep the canonical media source resolver strict. A canvas-only projection may
  publish a clearly labeled previous immutable Plot preview while the retained
  source is stale/running; it must not publish old content as current input,
  exportable output, or an interactive fullscreen plot.
- Use the existing retained output record rather than a second execution cache.
  Updating appears for queued/preparing/running work; idle Manual/Stop shows an
  Out of date state. The user's follow-up selected an icon at the shared node
  warning/error position and size, rather than a text badge over the plot.
  Failure/empty/unavailable output, removed producers,
  disconnected inputs and workspace/project replacement clear the old preview.
- Keep the image renderer alive and swap to the new decoded preview when ready;
  avoid tearing down the old renderer during regeneration or introducing timers
  that merely hide the transition. Preserve other media types' existing behavior.
- Verify Width/Font-size updates, rapid superseding edits, Manual/Stop, failures,
  source removal/rewiring, no initial result, unchanged upstream facts and run
  counts, strict current-result/fullscreen/export boundaries, and actual QML
  rendering. Reuse the existing isolated shell target where practical.
- One active implementation writer; fresh independent review before acceptance.
  Update affected agent maps and this record, then run focused route and document
  checks. Preserve pre-existing dirty files and publish only this follow-up.

### Follow-up evidence

- The canonical media source resolver and execution package are unchanged.
  Canvas presentation carries separate previous-preview metadata and keeps
  fullscreen/export/current-input authority strict. Old-pixel actions are disabled.
- The updating indicator uses the existing reload icon and exactly reuses the
  shared warning badge's position and dimensions. Its tooltip and accessibility
  text identify the update; idle stale state uses a static icon, warning details
  remain available, and actual failure takes precedence.
- Real Width/Font-size gestures and queued/preparing/Manual/Stop states preserve
  renderer identity and the completed plot while runtime facts remain stale.
  The newest authored width/font settings are verified in the final Plot value.
- A controlled asynchronous image provider proves delayed decode continuity,
  supersession, cancellation without revival, and decode-failure cleanup. The
  renderer switches actual image objects only after successful decoding.
- Independent review identified and corrected unrelated-run and completed-work
  status leaks. UI work metadata is scoped to relevant remaining nodes and clears
  through existing notifications. Publication-order guards cover matching new
  current records arriving before visual settlement and the narrower active-work
  fact/cache gap without accepting arbitrary previous history.
- The owning media/source/actions/fullscreen/XY/runtime-CURRENT/run-controller
  and shell route gate passed **195 tests and 28 subtests**. The final scoped
  projection/source/shell recheck passed **47 tests**; decoder/shell follow-ups
  and the final capture run also passed. Changed-file Ruff and whitespace pass.
- The coordinator inspected the upright retained plot and upper-right indicator
  in `artifacts/plot_updating_preview/media-updating-closeup.png`. Additional
  queued, preparing, Manual and ready frames are retained in the same ignored
  artifact directory. These are real offscreen QML render/gesture proofs.
- Final independent re-review accepted the publication-order guards without
  remaining findings. The common graph input contract, inline input, passive
  host, passive image and tooltip-copy gates passed **151 tests and 35 subtests**.
  Agent-map/index, traceability, Markdown-link, changed-Python Ruff and whitespace
  checks pass. Verification stayed on these owning routes; no unrelated runtime
  redesign, broad fast rerun or pre-existing dirty-file cleanup was performed.
