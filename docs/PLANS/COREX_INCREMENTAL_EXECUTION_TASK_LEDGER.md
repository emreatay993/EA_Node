# COREX Incremental Execution Task Ledger

## Purpose

This ledger controls execution of
`docs/PLAN_COREX_INCREMENTAL_EXECUTION_AND_SOLUTION_SNAPSHOTS.md`.
It is an orchestration record, not implementation proof.

No production task may start until the user approves the plan. After approval,
every task requires a read-only exploration sub-agent, a separate implementation
sub-agent, and an independent review sub-agent. The main agent orchestrates task
assignment, scope, evidence, finding resolution, and ledger updates; it does not
own production code implementation.

## Mandatory Resume Protocol

After context compaction, task handoff, thread continuation, or a long pause, the
orchestrator must read, in this order:

1. `docs/PLAN_COREX_INCREMENTAL_EXECUTION_AND_SOLUTION_SNAPSHOTS.md`
2. this ledger
3. the current task's accepted exploration report
4. the current scoped diff and proving-test output

Do not infer task state from chat memory, git status, or an implementation agent's
summary alone. If the ledger and repository disagree, stop and reconcile them
before assigning more work.

## Current Orchestration Baseline

- Branch: `main`
- Base HEAD: `86a5f562e7c5c9d7d52dad97f842a89631508a26`
- Editable root: `C:\Users\emre_\PycharmProjects\EA_Node_Editor`
- Commit/push authorization: `yes`; use multiple scoped `main` commits at safe
  accepted boundaries, but push only after T01-T09 are accepted, followed by
  local/tracking/remote SHA parity verification
- Unrelated dirty paths that must remain untouched:
  - `docs/specs/INDEX.md`
  - `docs/PLAN_COREX_Physical_Simulation_Backend.md`
- `docs/specs/INDEX.md` remains prohibited through T08. Before T09, its current
  owner diff must be reconciled or separately authorized; then update this baseline
  and T09's locked scope before editing it.
- Plan-owned untracked paths:
  - `docs/PLAN_COREX_INCREMENTAL_EXECUTION_AND_SOLUTION_SNAPSHOTS.md`
  - `docs/PLANS/COREX_INCREMENTAL_EXECUTION_TASK_LEDGER.md`
- Parallel implementation worktrees: `forbidden` while the approved plan/ledger
  are uncommitted or no commit-based integration method is authorized. Use the
  shared checkout sequentially.

## Status Vocabulary

- `PLANNED_BLOCKED_PENDING_APPROVAL`: task is defined but user approval is absent.
- `READY_FOR_EXPLORATION`: dependencies and approval are satisfied.
- `EXPLORING`: read-only sub-agent is verifying current insertion points.
- `READY_FOR_IMPLEMENTATION`: exploration is accepted and write scope is locked.
- `CLASSIFICATION_DRAFTING`: T02 inventory is being produced without metadata edits.
- `CLASSIFICATION_READY_FOR_REVIEW`: T02 inventory is frozen for review.
- `CLASSIFICATION_IN_REVIEW`: independent T02 classification review is active.
- `CLASSIFICATION_ACCEPTED`: T02 inventory is accepted and metadata edits may start.
- `IMPLEMENTING`: assigned implementation sub-agent owns the task.
- `READY_FOR_REVIEW`: implementation and focused proving checks are complete.
- `IN_REVIEW`: independent review sub-agent is active.
- `FINDINGS_OPEN`: reviewer findings returned to the implementation owner.
- `ACCEPTED`: implementation, proving checks, and review are accepted.
- `BLOCKED`: a concrete external/user decision or failed prerequisite prevents work.

Only `ACCEPTED` satisfies a dependent task.

## Orchestration Rules

1. Main-thread role: synthesize, assign, monitor, verify scope, and update this
   ledger. Do not implement production code directly.
2. Exploration role: read-only; report exact current owners, call sites, tests,
   drift from plan, and a compact navigation audit. Do not edit or run broad suites.
3. Implementation role: edit only the locked conservative write scope, preserve
   unrelated dirty work, run the smallest proving checks, and return exact changed
   paths plus test evidence.
4. Review role: must be a different sub-agent from the implementer. Review
   correctness, architecture boundaries, trust/data integrity, scope, tests, and
   private-provenance leakage.
5. Finding resolution: return findings to the original implementation owner. Do
   not create a catch-all fixer unless the owner is unavailable and the ledger
   records the reassignment.
6. Shared checkout: run one implementation task at a time. Parallel implementation
   remains forbidden by the current baseline. If later authorized, record the
   integration commit method, source/base SHA, exact worktree root, and verified
   plan/ledger hashes before creating a worktree.
7. Verification: focused first; broad fast verification only at T09 unless a task
   changes shared infrastructure beyond its planned boundary.
8. Publication: never commit while an implementation/review owner is active.
   Because T01-T04 overlap cumulatively without historical commits and T05 was
   already active when commit splitting was requested, use the next safe accepted
   boundary for a cumulative foundation commit; keep planning artifacts separate,
   then commit T06-T09 individually after acceptance. After T09, inspect staged
   content/private provenance and all extra commits ahead of upstream, push all
   scoped commits, and verify local/tracking/remote parity. Preserve unrelated work.
9. Privacy: tracked files, commits, and reviews use neutral COREX terminology only.
10. Plan drift: any material contract/scope change returns the affected task to
    `PLANNED_BLOCKED_PENDING_APPROVAL` until the user approves the revision.

## Plan Approval Gate

- Plan status: `APPROVED`
- Production implementation authorized: `yes`, subject to task gates
- Plan artifact:
  `docs/PLAN_COREX_INCREMENTAL_EXECUTION_AND_SOLUTION_SNAPSHOTS.md`
- Ledger artifact:
  `docs/PLANS/COREX_INCREMENTAL_EXECUTION_TASK_LEDGER.md`
- Locked user decisions:
  - generic incremental execution, not a Model Viewer special case;
  - disconnected Model Viewer is the primary end-to-end acceptance;
  - future expired-node coloring is out of current scope;
  - internal API and artifact metadata breakage is allowed for a cleaner design;
  - architecture boundaries may change when cleaner ownership replaces them and
    callers/tests/maps move atomically;
  - no migration or compatibility reader;
  - detailed task-first plan;
  - sub-agents own exploration, implementation, and review;
  - orchestrator rereads plan and ledger after compaction.

## Task Overview

| Task | Title | Depends on | Status | Pre-explorer | Implementer | Reviewer | Acceptance evidence | Next allowed action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T01 | Solution contracts and shared plan | plan approval plus T01 contract revision approval | `ACCEPTED` | `/root/t01_explorer` | `/root/t01_implementer` | `/root/t01_reviewer` | accepted: no P0-P3; independent suites green | none |
| T02 | Canonical identity and eligibility | T01 | `ACCEPTED` | `/root/t02_explorer` | `/root/t02_implementer` | `/root/t02_reviewer` | accepted: no P0-P3; identity/catalog evidence green | none |
| T03 | Session solution store | T01, T02 plus revised T03 contract review | `ACCEPTED` | `/root/t03_explorer` | `/root/t03_implementer` | `/root/t03_reviewer` | accepted: no P0-P3; adversarial closure green | none |
| T04 | Worker reuse cutover | T01-T03 plus revised T04 contract review | `ACCEPTED` | `/root/t04_explorer` | `/root/t04_implementer` | `/root/t04_reviewer` | accepted: no P0-P3; cross-backend tamper matrix green | none |
| T05 | Shell invalidation and freshness projection | T03, T04 plus revised T05 contract review | `ACCEPTED` | `/root/t05_explorer` | `/root/t05_implementer_recovery` | `/root/t05_reviewer` | accepted: no P0-P3; shell/cache/QML closure green | none |
| T06 | Scoped viewer invalidation | T03-T05 plus revised T06 contract review | `ACCEPTED` | `/root/t06_explorer` | `/root/t06_implementer` | `/root/t06_reviewer` | accepted: no P0-P3; participant-local viewer acceptance and focused/fast evidence green | none |
| T07 | Durable solution repository | T01-T04 | `PLANNED_BLOCKED_PENDING_APPROVAL` | unassigned | unassigned | unassigned | none | wait for T01-T04 |
| T08 | Save and Save-As transactions | T07 | `PLANNED_BLOCKED_PENDING_APPROVAL` | unassigned | unassigned | unassigned | none | wait for T07 |
| T09 | Closeout and acceptance | T01-T08 | `PLANNED_BLOCKED_PENDING_APPROVAL` | unassigned | unassigned | unassigned | none | wait for all tasks |

## Per-Task Resume And Integration Records

Every field below must be filled before the corresponding status transition. Agent
task IDs and inline ledger summaries are acceptable for explorer/reviewer reports;
test output must name the exact command and result or a stable log path.

| Task | Base SHA | Editable root | Dirty-path baseline | Locked scope/hash | Explorer report | Implementer diff/commit | Focused test evidence | Reviewer report | Open findings | Integration method |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T01 | `86a5f562e7c5c9d7d52dad97f842a89631508a26` | `C:\Users\emre_\PycharmProjects\EA_Node_Editor` | `docs/specs/INDEX.md`; `docs/PLAN_COREX_Physical_Simulation_Backend.md`; plan/ledger | revised plan T01; SHA-256 `C481BEDE79BDFF3E83B17147B52BC2F3BFEDBD1820CB172DAE00BC870B05D7AD` | `/root/t01_explorer` accepted: settlement ownership, DTO limits/shapes, plan callers/tests/maps | `/root/t01_implementer`; working-tree diff; no commit | implementer and independent reviewer: contracts/plan/boundaries 16 + 9 subtests; protocol/dataflow 61 + 145 subtests; worker 5 + 5 subtests; maps/diff/adversarial checks pass | `/root/t01_reviewer`: no P0-P3; accept | none | sequential shared checkout |
| T02 | T01 accepted working-tree state; HEAD `86a5f562e7c5c9d7d52dad97f842a89631508a26` | `C:\Users\emre_\PycharmProjects\EA_Node_Editor` | T01 accepted diff plus prohibited plan/spec paths | locked T02 plan SHA-256 `5136C6972A91EE609D73A865F80F36FB548AC1FF319ECCCA6E29BDF53AC5BF08`; classification SHA-256 `D19369093E7A100A518A8B0E939CDEECC61AA1A78E26A1E51FD46543F6AB460A` | `/root/t02_explorer` accepted: 936-row identity/provenance inventory and exact implementation owners | `/root/t02_implementer`; working-tree diff; no commit | focused 102 + 104 subtests plus identity hardening 13; parser/catalog/package 133; boundaries 26 + 42; cross-process 1; packaging 27; migration 20; catalog 3; maps/Ruff/diff pass; baseline fixture mismatch isolated | `/root/t02_reviewer`: no P0-P3; accept | none | sequential shared checkout |
| T03 | T01-T02 accepted working-tree state; HEAD `86a5f562e7c5c9d7d52dad97f842a89631508a26` | `C:\Users\emre_\PycharmProjects\EA_Node_Editor` | accepted T01-T02 diff plus prohibited plan/spec paths | revised T03 plan SHA-256 `6F833C47577289AC041822C99BB4F1E4255A756CE539D57681A6D461D8644381` | `/root/t03_explorer` accepted: lifecycle/generation/revision/cache/closure/lock map and exact project/composition/reader/contract tests/maps | `/root/t03_implementer`; working-tree diff; no commit | central 51; client/contracts 248 + 187 subtests; project 43 + 5; artifact/handle/security 56 + 23; exact closure 5; real process/maps/links/Ruff/diff pass; baseline isolated | `/root/t03_reviewer`: no P0-P3; accept | none | sequential shared checkout |
| T04 | T01-T03 accepted working-tree state; HEAD `86a5f562e7c5c9d7d52dad97f842a89631508a26` | `C:\Users\emre_\PycharmProjects\EA_Node_Editor` | accepted T01-T03 diff plus prohibited plan/spec paths | revised T04 plan SHA-256 `8C8677AD60353B26A37A367B32616A30D52310CFCC8F2B0CC2E0A131918CC3BC` | `/root/t04_explorer` accepted: transport/event/store/headless boundary map, exact reuse validation and scope drift | `/root/t04_implementer`; working-tree diff; no commit | core 66; protocol/client/headless/store 150 + 186 subtests; worker/dataflow 67 + 5; process/selected/start/run/legacy 7; maps/Ruff/diff pass | `/root/t04_reviewer`: no P0-P3; accept | none | sequential shared checkout |
| T05 | T01-T04 accepted working-tree state; HEAD `86a5f562e7c5c9d7d52dad97f842a89631508a26` | `C:\Users\emre_\PycharmProjects\EA_Node_Editor` | accepted T01-T04 diff plus prohibited plan/spec paths | revised T05 plan SHA-256 `2F3626EB5620181CE6790E2F8D80139F12A525858551F6542FE61BC65027F82D` | `/root/t05_explorer` accepted: history/dispatch/cache/projection/availability/media/API-removal consumer map and store start-failure drift | `/root/t05_implementer_recovery`; audited/completed partial working-tree diff; no commit | exact closure 7; expanded store/headless/run/port/media/DPF 168 + 17 subtests; prior locked suites/maps/indexes/Ruff/diff pass; tooltip/Ruff baselines isolated | `/root/t05_reviewer`: no P0-P3; accept | none | sequential shared checkout |
| T06 | HEAD `63e9786f`; accepted T01-T05 foundation | `C:\Users\emre_\PycharmProjects\EA_Node_Editor` | prohibited `docs/specs/INDEX.md` and Physical Simulation plan only | participant-local T06 plan SHA-256 `1AD2CF1FE568683497504B9EC2ED51B6BD269A53DBC53DCD6100D89515F6F58C` | `/root/t06_explorer` accepted: every invalidator/global reset, bridge/client/service epoch, worker filter, request registry, exact APIs, test/map owner | `/root/t06_implementer`; accepted working-tree diff; scoped commit pending | reopened 10 + 23 subtests; expanded focused 404 + 244 subtests; client/service/headless/store 160 + 64; DPF 25 + 3 and generator check; SSH 17; process reuse xdist 2; fast 4092 passed, 2 skipped, exactly 2 approved Model Viewer fixture baselines; maps/Ruff/diff/scope/process-leak pass | `/root/t06_reviewer`: no P0-P3; accept | none | sequential shared checkout; individual T06 commit |
| T07 | pending assignment | pending assignment | pending | plan T07; hash pending | none | none | none | none | none | sequential shared checkout |
| T08 | pending assignment | pending assignment | pending | plan T08; hash pending | none | none | none | none | none | sequential shared checkout |
| T09 | pending assignment | pending assignment | pending | plan T09; hash pending | none | none | none | none | none | sequential shared checkout |

## T02 Classification Approval Gate

T02 is a two-gate task. Producing the inventory is read-only task preparation and
must finish before the implementation sub-agent changes any node metadata.

- Gate status: `CLASSIFICATION_ACCEPTED`
- Inventory artifact:
  `docs/specs/perf/COREX_SOLUTION_REUSE_CLASSIFICATION.md`
- Inventory base SHA: T01 accepted working-tree state; HEAD `86a5f562e7c5c9d7d52dad97f842a89631508a26`
- Inventory content hash: `D19369093E7A100A518A8B0E939CDEECC61AA1A78E26A1E51FD46543F6AB460A`
- Classification explorer/drafter agent: `/root/t02_explorer`
- Independent classification reviewer agent: `/root/t02_classification_reviewer`
- Reviewer report/evidence: `/root/t02_classification_reviewer`; no P0-P3, accept
- Open classification findings: `none`
- Orchestrator acceptance record: accepted SHA
  `D19369093E7A100A518A8B0E939CDEECC61AA1A78E26A1E51FD46543F6AB460A`
- Metadata implementation permitted: `yes`

Allowed sequence after plan approval:

1. `READY_FOR_EXPLORATION`
2. `CLASSIFICATION_DRAFTING`
3. `CLASSIFICATION_READY_FOR_REVIEW`
4. `CLASSIFICATION_IN_REVIEW`
5. resolve all findings through the classification drafter
6. `CLASSIFICATION_ACCEPTED`
7. lock inventory hash and T02 metadata write scope in the per-task resume record
8. `READY_FOR_IMPLEMENTATION`

The drafter and reviewer must be different sub-agents.

## Task Gates And Evidence Slots

### T01 Solution contracts and shared plan

- Required pre-exploration output:
  - current `ExecutionPlan` callers and import move list;
  - runtime-contract dependency audit;
  - exact ordering/Trigger/disabled-edge/hidden-dependency tests;
  - drift report against plan T01.
- Locked implementation scope: plan T01 only.
- Required implementation evidence:
  - changed paths;
  - strict DTO adapter tests;
  - complete frozen dispatch-envelope round-trip;
  - semantic-combination and payload-budget rejection matrix;
  - settlement DTOs defined only in `runtime_contracts/settled_results.py`, with
    no protocol re-export or old-owner imports;
  - shared-plan behavior parity tests;
  - `git diff --check`.
- Required review lenses:
  - graph/execution/persistence import direction;
  - protocol-size and malformed-input limits;
  - no duplicated `ExecutionPlan` remains.
- Acceptance record: `none`.

### T02 Canonical identity and eligibility

- Required pre-exploration output:
  - all executable metadata owners;
  - existing implementation/package/content digests;
  - existing canonical payload/integrity helpers;
  - explicit node-family classification worklist.
- Locked implementation scope: plan T02 only.
- Required implementation evidence:
  - identity inclusion/exclusion matrix;
  - hostile-value callback-free tests;
  - built-in/add-on/public declaration classification inventory;
  - deterministic cross-process key proof.
- Required review lenses:
  - false hit/false miss risk;
  - side-effect and nondeterminism fail-closed defaults;
  - secret/private-path/provenance handling;
  - no UI-only fields in keys.
- Acceptance record: `none`.

### T03 Session solution store

- Required pre-exploration output:
  - all shell/headless client composition paths;
  - worker/runtime generation lifecycle;
  - current late-settlement and graph-revision guards;
  - duplicate-cache audit.
- Locked implementation scope: plan T03 only.
- Required implementation evidence:
  - current/expired/never transition tests;
  - exact closure invalidation tests;
  - preparation single-use/drift rejection tests;
  - late settlement and runtime-generation eviction tests.
- Required review lenses:
  - one scheduler authority;
  - thread safety and generation races;
  - previous-record preservation on failure/cancel;
  - headless and shell parity.
- Acceptance record: `none`.

### T04 Worker reuse cutover

- Required pre-exploration output:
  - command/event adapters and size limits;
  - `NodeExecutor.node_outputs` write/read sites;
  - worker plan construction and registry generation gates;
  - reusable output validation checklist.
- Locked implementation scope: plan T04 only.
- Required implementation evidence:
  - unchanged second run invokes no implementation;
  - selected upstream reuse;
  - reused settlement without `node_started`;
  - accepted-output protocol round-trip for value/EMPTY/reference payloads;
  - malformed/oversized or node/record/key/status/digest/residency/runtime-generation
    mismatched accepted-output payload rejection before installation;
  - durable payloads require no runtime generation; session payloads require the
    exact current generation; reused events preserve residency;
  - malformed/stale/generation-mismatched decision rejection;
  - actual process-worker second run invokes no implementation and emits no
    `node_started` for reuse;
  - selected upstream and diamond reuse preserves ordered fan-in and settles shared
    upstream once;
  - outputless completed and empty reuse;
  - artifact mutation and missing/stale handle rejection;
  - process/external/trusted prepared-field propagation;
  - force-recompute identical retention and divergent nondeterminism;
  - preflight failure, stop, and cancellation preserve earlier records;
  - `CorexRuntime.start()` prepare-plus-executable-dispatch proof, with legacy
    `start_run()` retained only for shell until T05.
  - `CorexRuntime.run()` subscribes before preparation, dispatches prepared reuse,
    captures terminal events, and has no direct-dispatch bypass.
- Required review lenses:
  - process trust boundary;
  - type/catalog/artifact/handle validation;
  - event ordering and output identity;
  - cancellation/failure behavior.
- Acceptance record: `none`.

### T05 Shell invalidation and freshness projection

- Required pre-exploration output:
  - history hook callers and cosmetic/execution classification;
  - all consumers of shell fresh/stale fields;
  - Auto/manual/selected/Trigger targeting map;
  - QML fact insertion point and static boundary tests.
- Locked implementation scope: plan T05 only.
- Required implementation evidence:
  - exact invalidation closure matrix;
  - before/after deleted/passive/edge-root normalization;
  - deleted-fact/pin/index removal plus tombstone and separate removal event IDs;
  - Manual/Selected/Auto/Trigger unified prepared dispatch and pending-target union;
  - terminal/mode/workspace outcome table and explicit Apply duplicate suppression;
  - old shell authority removal audit;
  - retained-record-ID cache selection across port/DPF/Panel/media/fullscreen/deck
    consumers;
  - explicit store acceptance result prevents rejected outputs from receiving an
    old retained record ID;
  - exact node availability clearing and rejected-late-settlement guard;
  - solution-state reset notification to QML;
  - project/revision filtering and separate expired/removed IDs through the exact
    CorexRuntime -> shell -> bridge -> QML signal chain;
  - strict `InvalidationResult`/`solution_state_changed` payload round-trip and
    malformed/unknown-field rejection coverage;
  - failed-start fact restoration versus started-run failure expiration;
  - bounded UI cache plus monotonic run-count proof;
  - runtime-global cross-workspace cache bounds and deterministic eviction;
  - `CorexRuntime.start_run`/`_start_legacy` absence;
  - freshness projection tests;
  - no visual/style diff.
  - existing blanket viewer invalidation behavior unchanged and T06 seams untouched.
- Required review lenses:
  - no duplicate closure/freshness computation;
  - active-run edit coalescing;
  - stale output inspection versus execution use;
  - authoring dirty-state separation.
- Acceptance record: `none`.

### T06 Scoped viewer invalidation

- Required pre-exploration output:
  - every bridge/service invalidator caller;
  - true-global-reset call list;
  - prepared recompute-set handoff path;
  - exact Model Viewer regression fixture/stub map.
- Locked implementation scope: plan T06 only.
- Required implementation evidence:
  - disconnected Model Viewer acceptance;
  - two-viewer filtered invalidation;
  - empty filter versus `None` semantics;
  - empty filter refreshes runtime context without viewer invalidation;
  - legacy empty-preparation viewer run/failure/skip remains workspace-global;
  - failed dispatch performs zero viewer invalidation/reset;
  - all open/update/close/materialize/query protocol round-trips carry exact
    workspace/node epochs;
  - stale command/response and delayed close/query events fail before signals,
    ownership, projection, or service mutation;
  - exact query/invalidate forwarding signatures, string rejection, unresolved
    owner, and unique retired-request count;
  - scoped pending/session/provisional/generation/owner registry cleanup across
    process/external/trusted clients;
  - run-carried selected-concrete/service snapshot plus independently digested high-
    level/Bridge projection snapshot and post-restart capture order;
  - viewer invalidation reservation failed-start rollback, synchronous response
    buffering, participant-local all-or-nothing commit, and concrete-to-projection
    response translation;
  - identity-bound `run_preflight_accepted` first-event ordering, one-shot commit
    event, preflight-failure invisibility, and reservation/buffer terminal cleanup;
  - matching parent commit/cancel acknowledgment, timeout/wrong-digest rejection,
    worker post-ack adoption order, and post-ack failure semantics;
  - project-load old/incoming workspace union and worker reset global epoch advance;
  - worker filter derives only prepared `execute` viewer metadata and preserves
    unaffected transport/leases/owner scope byte-for-byte;
  - same-branch change invalidation;
  - worker-reset global invalidation;
  - real non-stub same-registry dispatch with an active viewer route reaches worker
    preflight; a differing fingerprint remains rejected without partial retirement;
  - per-participant process/trusted/external/high-level stale-state injections reject
    before delivery and leave every participant unchanged; success commits all once;
  - commit-command delivery `False`/exception matrices leave client, Bridge, and
    service state byte-identical and publish no commit event;
  - recycled fresh-service empty-filter baseline adoption versus non-fresh rejection
    matrix;
  - heterogeneous empty-filter matrix across process/trusted/external/high-level
    epochs proves zero participant cleanup, retirement, or projection change; only a
    qualifying selected fresh service may baseline-adopt its selected-client epoch;
  - selected worker and high-level projection views use independent identity-bound
    digests; a following non-empty recomputation retires only the exact viewer and
    preserves/accepts unrelated backend responses;
  - heterogeneous `None` advances each participant's local workspace epoch once and
    remains global;
  - deterministic response-ingress/commit barrier proves child state-before-viewer
    lock order without deadlock, lock reacquisition, or callbacks under locks;
  - post-delivery generation drift and raising-subscriber/buffered-event matrices
    yield exactly one commit adoption or synchronous global retirement, always clear
    the publication gate, and never leak buffered events;
  - trusted fatal-generation cleanup removes session-node indices with session IDs
    and generations;
  - expanded-scope audit from foundation `63e9786f`;
  - DPF operator catalog regeneration/check;
  - 17 SSH synthetic NodeExecutor cases with prepared-decision state;
  - full-fast-xdist-stable real-process second-run and selected/diamond reuse tests.
- Required review lenses:
  - no viewer-specific scheduler branch;
  - transport/owner-scope lifetime;
  - bridge projection and worker state agreement;
  - live handle generation safety.
- Acceptance record: `/root/t06_reviewer`; no P0-P3; accepted.

### T07 Durable solution repository

- Required pre-exploration output:
  - current artifact transaction/integrity/path-safety primitives;
  - runtime-value codec eligibility inventory;
  - project sidecar ownership and architecture boundaries;
  - exact durable schema threat model.
- Locked implementation scope: plan T07 only.
- Required implementation evidence:
  - schema and path-key tests;
  - atomic record/blob/manifest tests;
  - restart/lazy-load tests;
  - corruption/path/reparse/hash failure matrix;
  - secret/handle/temp/private-path exclusion tests;
  - nondeterminism conflict test.
- Required review lenses:
  - data-loss prevention;
  - path traversal/reparse safety;
  - atomicity and previous-record preservation;
  - persistence/execution dependency direction.
- Acceptance record: `none`.

### T08 Save and Save-As transactions

- Required pre-exploration output:
  - current Save/Save As coordinator and failure injection points;
  - artifact promotion/descriptor rewrite order;
  - reopen validation and cleanup ownership;
  - current dirty-worktree test artifacts that must not be overwritten.
- Locked implementation scope: plan T08 only.
- Required implementation evidence:
  - stage-by-stage failure injection;
  - previous project/manifest/artifact preservation;
  - portable Save As reopen;
  - reachability prune correctness;
  - current-schema rejection and regeneration message.
- Required review lenses:
  - transactional ordering;
  - destination/source isolation;
  - cleanup cannot delete committed content;
  - no migration/compatibility residue.
- Acceptance record: `none`.

### T09 Closeout and acceptance

- Required pre-exploration output:
  - obsolete path/reference audit;
  - affected agent-map and generated-index list;
  - exact traceability rows and current proof status;
  - broad verification escalation check.
- Locked implementation scope: plan T09 only.
- Required implementation evidence:
  - zero duplicate freshness/scheduler authorities;
  - zero partial-run blanket viewer invalidators;
  - map/link/traceability checks;
  - summarized fast verification;
  - automated and, when practical, manual disconnected Model Viewer acceptance.
- Required review lenses:
  - independent architecture review;
  - independent security/data-integrity review;
  - independent UX acceptance review;
  - private-provenance and staged-scope audit.
- Acceptance record: `none`.

## Research Completed Before Plan Approval

The following read-only planning research is complete. It is context, not task
acceptance:

- generic COREX stale/current and Auto-targeting ownership;
- blanket UI/worker viewer invalidation root cause;
- execution-owned session/durable reuse architecture;

No production implementation or verification was performed as part of this
planning research.

## Ledger Change Log

| Entry | Change | Evidence |
| --- | --- | --- |
| L001 | Created detailed plan and orchestration ledger. | Draft complete. |
| L002 | Locked no-migration/current-schema cutover. | User decision. |
| L003 | Locked sub-agent exploration, implementation, and independent review workflow. | User decision. |
| L004 | Locked disconnected Model Viewer as primary acceptance. | User decision. |
| L005 | Added per-task resume, scope, evidence, review, and integration fields. | Independent plan review. |
| L006 | Locked sequential shared-checkout implementation until commit-based worktree integration is authorized. | Independent plan review. |
| L007 | Removed private research provenance from tracked planning artifacts. | Independent architecture review. |
| L008 | Added mandatory T02 classification draft/review/acceptance gate before metadata edits. | Independent architecture re-review. |
| L009 | Clarified that the current spec-index diff remains prohibited until T09 reconciliation or authorization. | Independent architecture re-review. |
| L010 | Independent architecture and execution-readiness reviewers report no remaining P0-P2 findings. | `/root/plan_architecture_review`; `/root/plan_execution_readiness_review`. |
| L011 | Markdown-link and traceability validation passed; `git diff --check` passed. | `scripts/check_markdown_links.py`; `scripts/check_traceability.py`. |
| L012 | Approved the detailed implementation plan and unlocked T01 exploration. | User approval. |
| L013 | T01 exploration found material settlement-ownership, DTO-shape, and payload-limit gaps; revised T01 and returned it to approval gate before production edits. | `/root/t01_explorer`. |
| L014 | Independent T01 revision review required a complete frozen dispatch envelope, full semantic-combination rules, aligned reuse budgets, and structural old-owner removal proof; revision updated accordingly. | `/root/plan_architecture_review`. |
| L015 | Authorized architecture-boundary changes when they produce cleaner ownership, with atomic caller/test/map updates and no adapters. | User decision. |
| L016 | Accepted the reviewed T01 contract revision and locked its plan hash for implementation. | User boundary authorization; independent reviewer clean. |
| L017 | T01 implementation completed with focused checks green and moved to independent review. | `/root/t01_implementer`. |
| L018 | T01 review opened six validation findings and returned them to the original implementer. | `/root/t01_reviewer`. |
| L019 | Original implementer resolved all T01 findings and reran focused evidence successfully. | `/root/t01_implementer`. |
| L020 | Accepted T01 after independent closure review found no P0-P3 issues and evidence was sufficient. | `/root/t01_reviewer`. |
| L021 | Accepted T02 exploration, locked the 936-row inventory totals and expanded exact identity/metadata/test/map scope; opened classification drafting only. | `/root/t02_explorer`. |
| L022 | Drafted and validated the complete 936-row T02 classification; froze its hash for independent review. | `/root/t02_explorer`. |
| L023 | Classification review reopened one unsafe durable row plus carrier/provenance/test-owner facts; locked totals revised to 29 durable, 27 session, 842 never, 38 excluded. | `/root/t02_classification_reviewer`. |
| L024 | Classification drafter resolved all findings and froze revised 936-row artifact hash `8331EC1A6E02F79547119F64795F5B356302B8DB8DF32E0FAEFAC16D12765B4A`. | `/root/t02_explorer`. |
| L025 | Classification closure review returned two P2 textual corrections without changing scopes or totals. | `/root/t02_classification_reviewer`. |
| L026 | Applied the two textual corrections and froze classification hash `D19369093E7A100A518A8B0E939CDEECC61AA1A78E26A1E51FD46543F6AB460A`. | `/root/t02_explorer`. |
| L027 | Accepted the T02 classification with no P0-P3 findings; locked plan/classification hashes and allowed metadata implementation. | `/root/t02_classification_reviewer`. |
| L028 | T02 identity/metadata implementation completed with focused evidence green and moved to independent implementation review. | `/root/t02_implementer`. |
| L029 | T02 implementation review opened packaged-build, directory-race, and DataTree-topology identity findings. | `/root/t02_reviewer`. |
| L030 | Original implementer resolved all T02 identity findings and reran focused/package evidence successfully. | `/root/t02_implementer`. |
| L031 | T02 closure review retained one P2 directory replace-scan-restore race missed by the first regression. | `/root/t02_reviewer`. |
| L032 | Added independent entry-snapshot verification; exact replace-scan-restore attack now fails closed. | `/root/t02_implementer`. |
| L033 | Final T02 review found one P2 recursive directory-entry budget overrun after nested recursion. | `/root/t02_reviewer`. |
| L034 | Added per-entry recursive budget enforcement; exact limit-2 reject and limit-3 pass regression is green. | `/root/t02_implementer`. |
| L035 | Accepted T02 after independent closure review found no P0-P3 issues and identity/classification evidence was sufficient. | `/root/t02_reviewer`. |
| L036 | T03 exploration found sequencing and lifecycle gaps; revised T03 with dormant cutover, generation APIs, namespace/provenance/retention/Trigger rules, shared closure, and project reset scope. | `/root/t03_explorer`. |
| L037 | Resolved T03 plan-review findings with atomic run reservation, private registry preparation, global preparation/store bounds, trusted provenance overlay, route-specific generation identity, mixed carrier descriptors, T04 start adoption, and exact lifecycle tests/maps. | `/root/plan_architecture_review`. |
| L038 | Corrected dispatch order to publish registry before generation snapshot/reservation and added explicit T04 headless start cutover proof. | `/root/plan_architecture_review`. |
| L039 | Accepted revised T03 contract/scope after independent review found no P0-P2 issues. | `/root/plan_architecture_review`. |
| L040 | T03 dormant session-store/lifecycle implementation completed with focused and real-process evidence green. | `/root/t03_implementer`. |
| L041 | T03 adversarial review opened generation, carrier, stale-settlement, lock-order, trust, preparation, invalidation, ordering, environment, and boundedness findings. | `/root/t03_reviewer`. |
| L042 | Original implementer resolved all twelve T03 findings and reran expanded lifecycle/security/concurrency evidence successfully. | `/root/t03_implementer`. |
| L043 | T03 closure review opened five remaining artifact/generation/order/lease/identity findings. | `/root/t03_reviewer`. |
| L044 | Original implementer resolved all five T03 closure findings and reran expanded focused evidence successfully. | `/root/t03_implementer`. |
| L045 | Accepted T03 after independent adversarial closure review found no P0-P3 issues. | `/root/t03_reviewer`. |
| L046 | T04 exploration found missing namespace/Trigger/fingerprint/decision transport and reused-settlement/store/headless scope; revised the worker cutover contract and proof. | `/root/t04_explorer`. |
| L047 | Added T04 execution-map ownership/check and explicit headless `run()` prepared-dispatch acceptance proof. | `/root/plan_architecture_review`. |
| L048 | Accepted revised T04 contract/scope after independent review found no P0-P2 issues. | `/root/plan_architecture_review`. |
| L049 | T04 worker reuse/headless cutover implementation completed with explicit cross-backend acceptance matrix green. | `/root/t04_implementer`. |
| L050 | T04 review opened command-generation/environment, decision-semantics, empty-output identity, and legacy-type validation findings. | `/root/t04_reviewer`. |
| L051 | Original implementer resolved all four T04 trust-boundary findings and reran exact tamper/process evidence successfully. | `/root/t04_implementer`. |
| L052 | Accepted T04 after independent closure review found no P0-P3 issues across prepared transports and headless/legacy boundaries. | `/root/t04_reviewer`. |
| L053 | T05 exploration found retained-record projection, runtime state notification, history-root normalization, node availability, failed-start restoration, UI-cache bounding, legacy API removal, and media/map scope gaps; revised the cutover contract. | `/root/t05_explorer`. |
| L054 | Resolved T05 plan-review findings with explicit store acceptance results, deleted-node tombstones/removal IDs, availability owners, event/signal ordering, pending-run outcome table, global UI-cache bounds, exact maps/tests/checks, and locked T06 viewer boundary. | `/root/plan_architecture_review`; `/root/plan_execution_readiness_review`. |
| L055 | Added strict removed-node/event adapter owner/tests, corrected public event signature, and included the port-availability owner map. | `/root/plan_architecture_review`. |
| L056 | Accepted revised T05 contract/scope after independent architecture and readiness reviews found no P0-P2 issues. | `/root/plan_architecture_review`; `/root/plan_execution_readiness_review`. |
| L057 | Authorized one final scoped `main` commit and push after T09 acceptance, including ahead-commit disclosure and remote parity verification. | User decision. |
| L058 | Revised publication to multiple commits: separate planning artifacts, one cumulative accepted T01-T05 foundation at the next safe boundary, then individual T06-T09 commits; push only after the whole plan. | User request; overlapping uncommitted task history constraint. |
| L059 | T05 implementation owner failed from model capacity without handoff; reassigned the shared partial diff to a new xhigh implementation owner for audit/completion. | `/root/t05_implementer` capacity error. |
| L060 | T05 recovery owner audited/completed the partial cutover and returned focused shell/cache/QML evidence green with unrelated baselines isolated. | `/root/t05_implementer_recovery`. |
| L061 | T05 review opened untitled-session, deletion-tombstone, observed-start, generation-event, availability, and metadata-only projection findings. | `/root/t05_reviewer`. |
| L062 | T05 recovery owner resolved all six findings and reran adversarial/runtime/shell/QML evidence successfully. | `/root/t05_implementer_recovery`. |
| L063 | T05 closure review opened adopted-generation event ordering and metadata-only unavailable-state findings. | `/root/t05_reviewer`. |
| L064 | T05 recovery owner fixed pre-start reset event ordering and explicit metadata-only unavailable projection with exact regressions. | `/root/t05_implementer_recovery`. |
| L065 | Accepted T05 after independent closure review found no P0-P3 issues; opened the safe cumulative T01-T05 commit boundary. | `/root/t05_reviewer`. |
| L066 | Created local planning/classification commit `3abfbc4b` and accepted T01-T05 foundation commit `63e9786f`; no push. | Scoped staging/private-provenance checks passed. |
| L067 | T06 exploration removed blanket preflight, locked exact filter semantics and workspace/node epochs across all viewer commands/responses, added worker execute-viewer filtering and full client/service/bridge scope. | `/root/t06_explorer`. |
| L068 | Resolved T06 plan-review findings with legacy global invalidation, close-epoch consistency, exact query/invalidate APIs, and empty-filter context refresh semantics. | `/root/plan_architecture_review`. |
| L069 | Accepted revised T06 contract/scope after independent review found no P0-P2 issues. | `/root/plan_architecture_review`. |
| L070 | T06 scoped invalidation/epoch implementation completed with focused acceptance green; broad fast lane exposed 22 failures requiring independent baseline/plan attribution. | `/root/t06_implementer`. |
| L071 | T06 review attributed 20 fast failures to the plan and reopened epoch synchronization, process capture, runtime-contract scope, unique cleanup counts, DPF asset, SSH fixture, and process-load stability; revised T06 scope accordingly. | `/root/t06_reviewer`. |
| L072 | Added transactional viewer invalidation reservation/commit/cancel and exact Bridge/client/service epoch adoption to preserve failed-dispatch no-op semantics. | `/root/plan_architecture_review`. |
| L073 | Added identity-bound first-event `run_preflight_accepted` commit boundary and one-shot viewer invalidation commit/cleanup semantics. | `/root/plan_architecture_review`. |
| L074 | Added two-phase worker preflight acceptance and parent commit/cancel handshake so service adoption occurs only after ordered client/Bridge commit. | `/root/plan_architecture_review`. |
| L075 | Accepted the revised T06 fix contract after independent review found no P0-P2 issues. | `/root/plan_architecture_review`. |
| L076 | Original T06 implementer resolved the transactional preflight/epoch and fast-lane findings; focused, xdist, DPF, SSH, and summarized fast evidence is ready for independent closure. | `/root/t06_implementer`. |
| L077 | T06 closure review reopened same-registry live-viewer dispatch, atomic multi-backend commit, recycled-worker empty-filter synchronization, failed commit-ack rollback, trusted cleanup, and locked-scope findings. | `/root/t06_reviewer`. |
| L078 | Revised T06 closure contract to make same-fingerprint publication an early no-op, multi-participant commit prevalidated and atomic, fresh-service empty-filter epoch alignment baseline-only, failed commit-command delivery invisible, trusted fatal cleanup complete, and the locked scope exhaustive. | `/root/plan_architecture_review`. |
| L079 | Removed the remaining empty-filter wording conflict: ordinary empty invalidation is unchanged, while only a qualifying state-free recycled service may baseline-adopt the already-committed workspace epoch. | `/root/plan_architecture_review`. |
| L080 | Accepted finding-revised T06 contract/scope after independent review found no remaining P0-P2 contradictions. | `/root/plan_architecture_review`. |
| L081 | Original T06 implementer resolved all reopened live-route, atomicity, recycle, delivery, cleanup, and scope findings; expanded focused and clean-process fast evidence is ready for closure. | `/root/t06_implementer`. |
| L082 | Second T06 closure review reopened lagging-participant empty-filter cleanup, transaction lock inversion, and post-delivery commit-event/gate suppression. | `/root/t06_reviewer`. |
| L083 | Revised T06 to participant-local transport/projection snapshots, child state-before-viewer transaction locking, and an irreversible post-delivery finalizer with mandatory gate cleanup. | `/root/plan_architecture_review`. |
| L084 | Removed residual shared-epoch wording so recycled service alignment uses only the selected concrete baseline and high-level callbacks receive projection-local translated epochs. | `/root/plan_architecture_review`. |
| L085 | Accepted the participant-local T06 contract after independent review found no remaining P0-P2 contradictions. | `/root/plan_architecture_review`. |
| L086 | Original T06 implementer completed participant-local snapshots/translation, state-before-viewer transaction locking, and irreversible commit finalization; focused and clean-process fast evidence is ready for closure. | `/root/t06_implementer`. |
| L087 | Accepted T06 after independent closure review found no P0-P3 issues; opened the individual T06 commit boundary. | `/root/t06_reviewer`. |

## Current Next Action

Create the scoped individual T06 commit without pushing, then open T07 exploration.
