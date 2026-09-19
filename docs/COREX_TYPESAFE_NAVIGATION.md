# TypeSafe navigation pilot

This is an explicitly invoked development command for finding source owners and
focused tests. Routine agent invocation remains disabled pending the qualification
gates in the [pilot plan](PLAN_COREX_TypeSafe_Navigation_Pilot.md). It does not run
tests, edit files, or change application behavior.

```powershell
.\venv\Scripts\python.exe -m scripts.nav_assist "Trace mixed-type forwarding and connection recommendations"
.\venv\Scripts\python.exe -m scripts.nav_assist "Inspect tooltip styling and wrapping" --json
.\venv\Scripts\python.exe -m scripts.nav_assist ea_node_editor/graph/type_forwarding.py
```

An existing explicit path or unambiguous declaration bypasses client construction
and needs no credential. Missing or ambiguous exact identifiers stay local and
report unresolved status. Ordinary task prose, including reference strings such as
`saved://`, uses semantic navigation.

For semantic requests, set `TYPESAFE_API_KEY` in the launching process environment.
The command uses the Python standard library and pinned model `jev-1.13.0` at
`https://api.typesafe.ai/v1/systemone`. It has no endpoint override or SDK runtime
dependency. It sends the task and bounded eligible repository evidence. API keys
are used only in the HTTPS authorization header; errors omit raw service bodies.
Recognizable credentials in task/evidence strings are excluded before serialization.

## Read a result

The evidence pack has at most three sources and three tests. Each includes its
relative path, stable identity, content hash, useful declarations, and exact
numbered lines. A source excerpt is intentionally bounded: open the live file to
inspect surrounding implementation before selecting an owner or insertion point.
Check the focused test's actual assertions before treating it as proving a change.

Tests carry relationship labels. `direct` means an explicit source `Tests:` banner
or a static test import links the files; it does not prove the test covers the
requested behavior. `shared_route` only means the files share an advisory map.
`semantic_or_lexical` has neither of those direct association claims.

| Status | Meaning |
| --- | --- |
| `ok` | Exact evidence or semantic owner candidates are available. |
| `no_match` | The model judged the task outside repository navigation or unsupported by supplied candidate areas; this is not an exhaustive absence proof. |
| `unresolved` | An exact identifier is missing/ambiguous, or supplied evidence did not establish an owner. |
| `unavailable` | Missing credentials, service failure, invalid response, or unavailable safe inventory. Local suggestions remain available when safe. |
| `stale` | Input or output evidence, ignore eligibility, or association inputs changed; rerun before using the result. |

Scores rank independent candidates on the same four-category relevance rubric.
Several owners can qualify. Confidence describes concentration of a model answer,
not proof of ownership or permission to act. The useful-owner and exact-owner
probabilities are added into `owner_probability`. A candidate is eligible when
that combined event is more likely than unrelated/context; a split across the two
owner levels cannot by itself discard it. There is no confidence cutoff.

## Selection and boundaries

The inventory includes eligible current Python, QML and JavaScript/TypeScript
sources and tests. It excludes ignored, private, vendor, generated, binary and
reparse-point paths, and requires Git visibility. Source is parsed as data and never
imported. Direct associations and map neighbors are kept separate.

Local retrieval considers the complete inventory using paths, purpose statements,
and local-only declaration, documentation and property-binding terms, including
late methods. Those cheap retrieval hints are not authoritative parsed symbols;
displayed symbols still require source parsing and freshness checks. The first pass
scores every non-QML area route, up to 12 locally relevant QML routes, 30 sources
and 18 tests independently. Its scope question sees the complete compact area
catalogue, rather than inferring absence from the first file batch. A positive owner
judgment overrides a contradictory absence judgment. An incomplete safe catalogue
cannot support an absence verdict.

Every request identifies COREX application ownership and distinguishes standalone
development tools with their own UI. The second
pass reads richer evidence for up to 18 sources and 18 tests, including candidates
rescued in interleaved order from several routes and direct tests for both initial
and rescued sources. Each batch has at most 12 candidate
judgments, with at most four concurrent requests. Inputs are revalidated before
requests and after responses, including files later dropped from the result.

Each request has a four-second transport deadline and bounded request/response
sizes. At most four daemon resolver workers may remain outstanding; a stalled
system DNS call cannot block process exit or cause unbounded resolver threads.
Failed batches cancel queued requests. Failures return a safe local fallback
without automatic retries. End-to-end
latency also includes inventory building, local validation and multiple request
batches; the qualification target is uncached p95 below ten seconds. Passing unit
tests alone does not establish that latency or source/test coverage gate.

Readable output is capped at 16,000 characters; JSON at 24,000. Extra symbols and
excerpt lines may be removed to fit, with `output_truncated` set. Each retained
candidate keeps a small exact excerpt around a declaration or nonblank source
line. If that excerpt cannot fit, the whole candidate is omitted; `output_omitted`
counts and a visible gap explain the removal. Status, uncertainty and existing
gaps remain visible. Numbered source lines are never clipped or invented.
Suggestions can lose candidates at local retrieval, route expansion,
richer evidence selection, rubric interpretation or the final three-result cap.

If unavailable, continue with existing local navigation:

```powershell
.\venv\Scripts\python.exe scripts/nav.py find "tooltip"
.\venv\Scripts\python.exe scripts/nav.py source ea_node_editor/graph/type_forwarding.py
```

## Programmatic evaluation

`scripts.nav_assist.run(query, root=..., inventory=None, client=None,
include_trace=False)` returns a JSON-compatible dictionary. `mode` is `exact`,
`semantic`, or `local_fallback`. `usage` records input/output tokens and successful
requests, plus attempted requests (failed requests may have unknown token usage).
`latency.total_seconds` includes inventory construction unless the caller
explicitly supplies an inventory. `api_request_seconds` sums request durations and
can exceed wall time because requests run concurrently.

An injected test client implements `evaluate(state, questions)` and returns the
same typed HTTP response; the selector still validates its model, question IDs,
answer types, finite numbers, ranges, probability keys and usage. Legitimate API
rounding of probability-weighted scores is tolerated.

`include_trace=True` adds complete inventory paths, per-stage paths and model
answers for local candidate-loss analysis. Trace is never sent to the model or
included in normal CLI JSON. The implementation does not read evaluation fixtures.
Both baseline and pilot should use the same deterministic exact preflight.

Focused offline verification:

```powershell
.\venv\Scripts\python.exe -m unittest tests.test_nav_assist tests.test_nav_assist_inventory -v
.\venv\Scripts\python.exe -m pytest tests/test_nav_assist_evaluation.py -q -n 0
```

## Qualification

**2026-09-19 result: manual pilot only; qualification gates not met.**
Routine agent invocation remains disabled. The implementation and offline checks
passed, but the frozen evaluation missed source coverage, focused-test coverage
and latency targets. No model tuning followed this qualification run.

| Gate | Required | Measured | Result |
| --- | --- | --- | --- |
| Complete actionable source groups | At least 17/18 | 10/18 | FAIL |
| Complete focused-test groups | At least 15/18 | 9/18 | FAIL |
| No-match requests | 2/2 | 2/2 | PASS |
| Exact lookup without attempted API calls | 2/2 | 2/2 | PASS |
| Paths, content hashes and displayed excerpts | All valid | All valid | PASS |
| Full uncached command p95 | Below 10 seconds | 12.324 seconds | FAIL |
| Complete corpus and stable identities | All 20 cases | Complete and stable | PASS |

The shared-exact-preflight baseline achieved 2/18 source and 1/18 test cases,
with p95 5.335 seconds. Pilot UI cases achieved 3/6 source and 4/6 test coverage;
requests spanning owners achieved 2/4 source and 1/4 test coverage. These are
navigation results against frozen expected groups, not GUI behavior tests or
end-to-end coding-success measurements.

All 40 baseline/pilot commands completed. Four pilot cases returned a handled
service-unavailable result and remained failures in the coverage denominators.
The pinned model was `jev-1.13.0`: 241 successful requests from 245 attempts,
3,568,517 reported input tokens and 71,845 output tokens. Failed requests may
have additional unreported token usage.

[Retained per-case qualification evidence](../tests/fixtures/nav_assist_qualification.json)
records predictions, expected groups, validity, candidate-loss stages, identities,
timing and usage. The complete local trace is retained at
`artifacts/verification_logs/typesafe_navigation/qualification.json`; its checksum
is recorded in the retained evidence. Offline integration passed **131 tests and
464 subtests**, together with map/index, traceability and Markdown-link checks.

The frozen [evaluation corpus](../tests/fixtures/nav_assist_evaluation.json) has
20 independently grounded cases: six backend, six UI, four involving multiple
owners, two exact lookups and two no-match requests. It is distinct from the
[development corpus](../tests/fixtures/nav_assist_development.json).

Run from the repository root with a configured process environment and a new
output filename:

```powershell
.\venv\Scripts\python.exe -m scripts.evaluate_nav_assist --corpus tests/fixtures/nav_assist_evaluation.json --output artifacts/verification_logs/typesafe_navigation/qualification.json --include-trace
```

The evaluator launches each baseline/pilot case in a fresh process and measures
full command wall time. Only the parent reads expected paths; model input never
contains the labels. Coverage is graded on the rendered, size-bounded pack, and
every required owner group must appear. Failures stay in the denominators.
Development subsets require `--development` and cannot qualify the pilot.
Reports are screened for recognizable credentials and existing outputs are never
overwritten. Full trace is local evaluation evidence, not normal CLI output.

Required gates are at least 17/18 actionable source cases and 15/18 focused-test
cases, both no-matches, exact lookups with zero attempted API calls, valid paths,
hashes and excerpts, stable source/corpus identities, and uncached command p95
below ten seconds. A missed gate keeps the command explicitly callable only.

If a Windows shell predates a saved user environment variable, a new shell can
inherit it; the current shell can load the existing value without displaying it:

```powershell
$env:TYPESAFE_API_KEY = [Environment]::GetEnvironmentVariable('TYPESAFE_API_KEY', 'User')
```

The integration follows the live [HTTP API](https://docs.typesafe.ai/api),
[Score](https://docs.typesafe.ai/primitives/score),
[state](https://docs.typesafe.ai/concepts/state), and
[skill-suggestion pattern](https://docs.typesafe.ai/cookbooks/skill_suggestion).
Its independent scores and multi-owner shortlist are specific to this pilot;
the cookbook's example thresholds are not imported.
