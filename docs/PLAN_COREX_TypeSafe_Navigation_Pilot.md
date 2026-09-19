# COREX TypeSafe Navigation Pilot

## Summary

Implement the user-approved development-only navigation pilot. Keep exact lookup
deterministic and existing navigation available. Use TypeSafe only when ownership
is unclear, through a separate command returning ranked source/test evidence.
Do not enable routine agent use unless all qualification gates pass.

The planning benchmark covered backend and UI code; its corrected prototype
returned complete source-and-test evidence for 8 of 14 implementation requests.
Candidate omissions and weak evidence selection must be treated separately from
model errors. This is not a COREX application-runtime AI feature.

## Key Changes

- Build complete, current source/test/QML associations without executing source.
- Preserve purpose statements, useful symbols and numbered code excerpts.
- Score route and file relevance independently so multiple owners remain eligible.
- Evaluate bounded batches, then inspect fuller evidence for shortlisted candidates.
- Validate paths and excerpt freshness locally; never treat a model score as proof.
- Keep no-match, unresolved, stale and unavailable outcomes explicit.
- Never transmit credentials, unrelated files, ignored/private research or binaries.
- Preserve pre-existing edits to `AGENTS.md`, `docs/specs/INDEX.md`, the Physical
  Simulation plan and the strain-candidate CSV. Publish only the TypeSafe changes
  in the user-requested commit and push; leave pre-existing work uncommitted.

## Public Interface Changes

Add `python -m scripts.nav_assist "<task>"`, with readable output and `--json`.
Return at most three source candidates and three test candidates, symbols,
numbered excerpts, uncertainty and unresolved gaps. Record model version,
latency and token usage. Explicit existing paths and unambiguous symbols bypass
the API. An API failure exposes available local navigation rather than blocking
ordinary investigation. Use `TYPESAFE_API_KEY` and pinned `jev-1.13.0`.

## Execution Tasks

### T01 — Reliable candidate evidence

- **Goal:** Correct candidate omissions and retain useful code evidence.
- **Preconditions:** Freeze the planning benchmark's existing cases and expected groups.
- **Conservative write scope:** Navigation index generator and generated outputs;
  development-only candidate/evidence modules; their focused tests and development corpus.
- **Deliverables:** Complete file associations, reverse source/test references, QML
  ownership, bounded exact path/symbol lookup and freshness-aware excerpts.
- **Verification:** Every development-corpus target is in the inventory; paths and
  numbered excerpts resolve; existing navigation/index tests pass.
- **Non-goals:** API calls, application changes or AI-based syntax parsing.
- **Packetization notes:** One writer; no packet conversion.

### T02 — Semantic selection

- **Goal:** Add the separate TypeSafe command with independent relevance judgments.
- **Preconditions:** T01 accepted after focused tests and independent review.
- **Conservative write scope:** Development-only API transport, semantic selection
  and command modules, plus focused mocked tests.
- **Deliverables:** Pinned model, stable candidate identities, bounded batches,
  fuller shortlist inspection and diagnostics for each candidate-loss stage.
- **Verification:** Typed response validation, missing credentials, timeouts,
  malformed/service responses, no-match handling and exact lookup without API calls.
- **Non-goals:** Editing source, executing recommendations or replacing fuzzy navigation.
- **Packetization notes:** Fresh implementation owner; retain it through review fixes.

### T03 — Evidence packs and guidance

- **Goal:** Make recommendations usable and their limits explicit.
- **Preconditions:** T02 accepted.
- **Conservative write scope:** Formatting and CLI tests, development documentation,
  agent navigation guidance and relevant maps.
- **Deliverables:** Bounded text/JSON evidence packs; stale-result rejection;
  conditional-invocation instructions gated on T04; source/test inspection requirement.
- **Verification:** Text/JSON, size limits, stale files and existing CLI regressions.
- **Non-goals:** Automatic tests or routine agent activation before qualification.
- **Packetization notes:** May share T02's owner because CLI and output form one small seam.

### T04 — Qualification and closeout

- **Goal:** Evaluate against frozen, independently grounded cases and report actual gates.
- **Preconditions:** T01–T03 pass; freeze 20 new cases before final tuning.
- **Conservative write scope:** Evaluation fixture/runner, focused evaluator tests,
  retained results, final guidance, owning maps and spec-index proof link.
- **Deliverables:** Six backend, six UI, four multi-owner, two exact and two no-match
  cases; identical baseline/pilot expectations; full results and an honest closeout.
- **Verification:** The acceptance gates below and independent integration review.
- **Non-goals:** Tuning to evaluation labels, weakening gates or replacing incumbent navigation.
- **Packetization notes:** No packet conversion; coordinator records final acceptance.

## Work Packet Conversion Map

None requested. Use the repository's large-plan workflow with one active writer
and independent review before substantial task acceptance.

## Test Plan

- Preserve correct exact lookups without API calls.
- Validate returned paths and actual excerpt lines; reject both no-match cases.
- On 18 actionable evaluation cases, require complete source-group coverage in
  the three-source shortlist for at least **17/18**, and focused-test-group coverage
  in the three-test shortlist for at least **15/18**.
- A multi-owner case passes only when every expected group is represented.
- Compare both arms with the same deterministic exact-lookup preflight; use
  incumbent navigation for baseline ambiguous requests. Do not handicap the
  baseline by forcing known paths through fuzzy search.
- Keep evaluation labels out of model state. Record corpus/source/prompt identity,
  per-case results, candidate-loss stages and full uncached command latency.
- Retain settings-group expansion, tooltip styling and XY plot control regressions.
- Require uncached evidence-pack **p95 below 10 seconds**; report token usage.
- Run route-owned navigation tests, map checks, traceability and Markdown-link checks.
- If any gate fails, keep the pilot explicitly callable and document the unmet gate;
  do not enable routine conditional agent invocation.

## Assumptions

- The user accepted the numerical thresholds by requesting this plan's implementation.
- Full relevant files may be sent when useful and within request budgets.
- UI code is a navigation target; no UI behavior changes or GUI launches are needed.
- Existing dirty work stays intact; evaluation artifacts contain no API credentials.

## Progress

| Task | Status | Owner | Accepted evidence / next action |
| --- | --- | --- | --- |
| T01 | Accepted | t01_inventory / review_t01 | Four findings fixed and independently accepted; inventory 16 + 41 subtests, generator/nav 44 + 178; index check passed. |
| T02 | Accepted implementation | t02_t03_pilot / review_t02_t03 | Generic development fixes independently accepted; full focused integration 131 tests + 464 subtests passed. |
| T03 | Accepted implementation | t02_t03_pilot / review_t02_t03 | Bounded exact nonblank excerpts and formatter liveness accepted; guide and manual-only agent/map guidance in place. |
| T04 | Closed; failed qualification accepted | Coordinator / review_t04 | Source 10/18, tests 9/18, p95 12.324s; independent audit verified all 109 displayed records and exact gates. Manual-only fallback retained. |

Final implementation verification: 131 tests and 464 subtests passed, together
with map/generated-index, traceability and Markdown-link checks. The live run
completed all 40 commands on the unchanged frozen corpus. See
[qualification evidence and limitations](COREX_TYPESAFE_NAVIGATION.md#qualification).
