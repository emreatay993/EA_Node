# COREX Plot and Graph Ownership Refactor

Status: **IMPLEMENTED AND FUNCTIONALLY REVIEWED. Focused verification accepted; broader performance qualification stopped by user with timing uncertainty recorded.**

Task status, ownership, acceptance evidence, and recovery state are recorded in the [task ledger](PLANS/COREX_PLOT_GRAPH_OWNERSHIP_TASK_LEDGER.md).

## Latest execution direction

The user subsequently instructed: "I don't like that you are going for this much detail, get over your tests already". This supersedes the remaining intensive verification schedule and the requirement to resolve every timing uncertainty before starting Stage B. Stop further benchmark/diagnostic cohorts and broad fast lanes. Stage A is functionally accepted; its unresolved array-tail timing difference remains documented and is not a performance pass. Complete T06-T08 as one coherent graph ownership implementation group, with only focused correctness checks and one independent review. T09 closes documentation/ownership and reports limitations; it does not restart the extensive performance campaign. Preserve behavior and avoid additional graph traversals/copies through the existing focused structural tests.

Implementation closeout: both ownership stages and the Signal Plot/XY amendments are implemented. Independent reviews accepted all functional changes. The final graph group passed186 focused checks plus the retained Script editor integration case. Agent maps and generated navigation were updated, and unrelated user changes were preserved. The user subsequently authorized committing to `main` and pushing; publication scope is recorded in the ledger. The ledger records the unresolved array-tail timing, measurement limitations and pre-existing canvas failures; no overall performance-neutrality claim is made.

## Summary

Refactor two areas sequentially:

1. **Stage A — Plot consolidation and ownership:** make Signal Plot with Media Panel or Image Export the line/scatter workflow, retire generic Scatter Plot, then separate the retained generic family's declarations, preparation, request composition, and exports; reorganize their tests and remove confirmed duplicated coverage.
2. **Stage B — Graph mutation:** consolidate port-state reconciliation and repeated mutation mechanics while preserving each caller’s distinct behavior.

Stage A must pass its acceptance checkpoint before Stage B starts. Plot is the first deliverable; the plan does not require completing both stages in one day.

The read-only audit examined source, tests, ownership maps, and relevant commit history at `d36c84a65c02635acdd7ec541be9d8f1dfee0425`, on `main`. An independent reviewer found no remaining plan-blocking issues after the preservation rules below were incorporated. No files were changed and no tests or benchmarks were run during planning.

### Audit findings and disposition

| Area | Current problem | Decision |
|---|---|---|
| [Generic Plot implementation](../ea_node_editor/nodes/builtins/plot/generic.py) | Declarations, source reads, numeric preparation, execution, and artifact publication share one owner. Table/window preparation and export preflight repeat policy. | Stage A |
| [Validated graph mutation](../ea_node_editor/graph/validated_mutation.py) | Single/bulk property updates repeat their commit sequence. Script Apply, dynamic edits, and registry normalization overlap in port-state handling. | Stage B |
| Plot and Python Script tests | Several modules mix declarations, pure processing, graph mutation, persistence, scene projection, and shell integration. One Plot scene test is demonstrably duplicated. | Reorganize alongside their production owners |
| [Graph-scene mutation assembly](../ea_node_editor/ui_qml/graph_scene_mutation_history.py) | Runtime method assignments obscure ownership and navigation; some tests enforce that assembly technique. | Record as a substantial follow-up |
| Artifact rename orchestration | Scene code discovers shell services, constructs persistence stores, retries filesystem operations, and publishes metadata; workspace rename repeats orchestration. | Defer |
| Worker execution, Mechanical adapters, fullscreen tabular sessions | Additional mixed responsibilities and repeated admission/scheduling policy exist, but require separate lifecycle and performance qualification. | Defer |

Earlier protocol, registry, package-schema, Library, Media Panel, and native viewer/plot handoff refactors are already present. This plan preserves those owners.

## Key Changes

### A. Generic Plot ownership

#### Approved scope amendment: Signal Plot owns line/scatter

On 2026-09-19, before any Plot timing or production refactor, the user confirmed that Signal Plot plus Media Panel or Image Export is sufficient for line/scatter cases. This amendment supersedes the original blanket Signal Plot non-goal and node-ID preservation statement only for the explicitly described consolidation.

- Retire `plot.scatter` from the generic catalogue, icon entry, public node documentation and authoring examples. `plot.line` is already retired by `09502b9e`; do not restore it.
- Retain `plot.signal` and the seven specialized generic types: `plot.bar`, `plot.histogram`, `plot.heatmap`, `plot.contour`, `plot.surface`, `plot.point_cloud`, and `plot.streamlines`.
- Reuse existing XY rendering and style controls: `line_styles=[0]` with nonzero `marker_shapes` is marker-only scatter. Add discoverability keywords and document the Signal Plot to Media Panel/Image Export routes; add no new renderer, mode property, or duplicate style state.
- Follow the prior Line Plot retirement: no alias, compatibility wrapper, or automatic wire/property migration. Registry-backed project loading already rejects an unresolved `plot.scatter` before normalization. Add a regression proving this rejection leaves the source document unchanged, and document the replacement workflow. Preserve the separate read-only registry compatibility guards.
- Generic Scatter's CSV/paired-artifact output contract is deliberately not recreated on Signal Plot. The user selected the PlotValue/media/image-export workflow. Retained generic nodes keep their existing export behavior.
- Change shared generic fixtures to an appropriate retained type (normally Bar) while preserving the behavior under test. Move genuinely scatter-specific rendering assertions to Signal Plot coverage; retain backend-level line/scatter contracts with independent live consumers.
- Remove unreachable generic-node-only line/scatter preparation and adapter branches after checking exact consumers. Live backend/tooling consumers must retain their contract through their actual owner; do not delete independently useful renderer capabilities.
- The user specifically clarified that `scripts/verify_plot_visual_parity.py` must use the existing production Signal Plot/XY path for line/scatter cases, rather than keep generic line preparation alive for the tool. Retained specialized cases continue through generic backends. Reuse production normalization/PlotValue creation, remove the tool's generic line-preparation dependency, and distinguish PNG rendering evidence from actual fullscreen-interaction evidence. This supersedes the earlier provisional option to retain generic line preparation for this tool.
- Repair the stale Signal Plot guide's direct-array/source-selection text to match `36c9ea6b`: full direct source domains; only explicit windows/slices restrict them. Preserve full normalized PlotValue data and full-resolution interaction without source reread.
- Refresh owned catalogue fixtures using their current canonical generation/overlay contract, not a blind snapshot rewrite. Regenerate generated examples. Replace stale line demonstrations with Signal Plot pipelines and keep paired-archive demonstrations on a retained generic type.
- Freeze and measure retained generic fixtures, not retired Scatter. Separately verify the existing Signal Plot line/marker-only pipeline with its existing renderer tests and benchmark; do not compare the two different data-retention strategies as equivalent workloads.

Use four direct owners within `ea_node_editor.nodes.builtins.plot`:

| Owner | Responsibility |
|---|---|
| `specs.py` — new | Inert Plot definitions, constants, fresh-default construction, node specifications, and immutable mapping-role metadata |
| `data_series.py` — new | Input interpretation, table/window selection, numeric series preparation, array sampling, warnings, and source provenance |
| `exports.py` — new | Full-fidelity data export and the existing paired-artifact publication/cleanup sequence |
| `generic.py` — retained | `GenericPlotNodePlugin`, descriptors, render-request composition, and execution orchestration |

The package initializer becomes inert. Registration and other consumers import their actual owner directly; no compatibility re-exports remain.

`generic.py` retains `build_generic_plot_render_request(...)` with its existing signature. Plugin execution uses this same builder after applying fresh defaults and execution-context properties. Preview preparation therefore has one request-construction implementation.

Metadata consumers—including scene projection and the property editor—import `specs.py`. Scientific libraries, tabular services, and execution backends remain lazy at their existing use boundaries. No new dependency is introduced.

#### One table/window preparation path

Introduce a private frozen, slotted `_TablePlotSelection` containing:

- Table reference and schema facts.
- Complete and available columns.
- Effective row offset and limit.
- Source provenance used by later exports.

One resolver constructs this selection; one executor reads columns and invokes the existing numeric-series pipeline.

Preserve these distinctions:

| Behavior | Direct table | Explicit table window |
|---|---|---|
| Mapping validation | Complete source schema | Columns admitted by the window |
| Plot columns | Explicit mapping or complete schema | Explicit mapping or window columns |
| Offset | Zero | Window offset |
| Limit | Positive mapping limit, otherwise unlimited | Minimum positive mapping/window limit |
| Export provenance | Omits a `columns` restriction | Retains original window columns |
| Full-fidelity CSV | All source columns, even if the plot maps fewer | Window columns, offset, and effective limit |

Do not derive export columns from the plotted series. Preserve warning order, error order, existing `source_ref` attachment behavior, and source identity.

#### Shared role metadata, separate coercion policies

`specs.py` stores editor roles and runtime validation order separately:

| Plot family | Editor roles before the final `columns` selector | Runtime validation order |
|---|---|---|
| Bar | Single X, single category, multiple Y | X, category, Y |
| Histogram | Multiple values | Values |
| Heatmap/contour/surface | Single Z, multiple values | Values, Z |
| Point cloud/streamlines | Single X, Y, Z | X, Y, Z |

Preserve current labels and the final multiple-column selector. Unknown plot types retain their current columns-only editor behavior.

The following differences remain intentional boundaries:

- Runtime strings denote one column name and use case-sensitive deduplication.
- Inspector strings support comma/semicolon splitting and case-insensitive deduplication.
- Runtime and inspector row-limit coercion remain separate.
- Point-cloud/streamline Y remains stored as a list despite its single-selector presentation.
- Runtime validation stays at its existing position relative to empty-input handling and numeric preparation.
- The current streamlines mapping behavior is preserved. Any correction belongs in a separate behavioral change.

#### Preserve array strategies and algorithms

Full arrays retain bounded source sampling, existing grid row/column and retained point-cloud width limits, original-size metadata, and explicit rejection of unsupported ND input. Independently consumed backend-level line/scatter capabilities remain outside node retirement.

Explicit slices retain their authored slice read followed by the existing sampler. They must not become the implementation of full-array reads.

The 4,000-point budget, decimation algorithms, numerical conversion rules, and pre-decimation row limits remain unchanged.

#### Export ownership and failure behavior

`archive_plot_exports(ctx, render_request, properties, *, definition)` returns the existing output mapping and preserves this order:

1. Resolve static/data backends before allocating artifacts.
2. Allocate and write the static artifact.
3. Record its attempted ID before registration; register it.
4. Allocate and write the data artifact.
5. Record its attempted ID before registration; register it.
6. Persist the store and return the existing refs/backend metadata.

On `BaseException`, independently attempt validated entry cleanup, validated path cleanup, and store persistence; then re-raise the original exception. Cleanup failures must not replace that exception.

Preserve the existing behavior when registration has already changed the store, including repeated stable IDs and removal of a previously seeded artifact pair. Do not introduce restoration of an earlier pair or raw file deletion around store validation.

Share one small uniform-source preflight. Retain table export, array export, and backend fallback order, optional-PyArrow behavior, 65,536-row table batches, and cancellable atomic array writes in 4,096-row chunks.

### B. Graph mutation ownership

Add `ea_node_editor.graph.node_port_state` as a pure domain owner:

```python
@dataclass(frozen=True, slots=True)
class NodePortState:
    exposed_ports: dict[str, bool]
    port_labels: dict[str, str]
    port_modifiers: dict[str, tuple[str, ...]]
    principal_input_port_id: str | None
```

Expose two named policies:

```python
normalize_node_port_state(node, spec, ports) -> NodePortState

reconcile_script_port_state(
    node,
    ports,
    *,
    semantic_changed_keys,
) -> NodePortState
```

These functions return fresh dictionaries. They perform no writes, registry resolution, source parsing, graph cloning, edge traversal, dirty marking, or I/O.

Use small shared projection primitives internally. Do not introduce a configurable reconciliation framework.

#### Preserve three different state policies

| Concern | Script Apply | Generic dynamic edit | Registry normalization |
|---|---|---|---|
| Exposure | Preserve unchanged ports; reset semantically changed ports to declaration behavior | Remove only the old key’s state | Normalize against effective ports and defaults |
| Labels | Preserve surviving, unchanged, nonblank labels | Key rename does not transfer the old label; label rename preserves identity | Remove invalid labels, including forbidden dynamic labels |
| Modifiers | Preserve surviving unchanged tuples and their order | Clear only the removed key | Canonicalize supported values/order; remove empty or invalid entries |
| Principal input | Preserve an eligible unchanged input | Clear only if it names the removed key | Validate against surviving eligible inputs |
| Expanded settings groups | Preserve surviving instance order | Leave unchanged | Restore declaration order |
| Wires | Compute candidate pruning before writes | Preserve existing incident-removal and subsequent-pruning order | Preserve workspace normalization, pruning, and fan-in ordering |

Settings-group reconciliation remains outside the port-state helper.

Script Apply keeps two separate sets:

- `semantic_changed_keys`: changes to direction, kind, primary type, accepted types, data access, or `type_from_input`.
- `forced_prune_keys`: surviving ports whose data access changed.

Semantic changes reset port state; they do not automatically delete compatible wires. The invariant kernel remains authoritative for compatibility and forwarding-aware pruning.

#### Consolidate mutation mechanics without changing entry contracts

Keep `ValidatedGraphMutation` as the write authority. Introduce:

- `_commit_normalized_property_updates(node, updates)`: contextual normalization, Media Panel source protection, semantic preflight, private writes, and existing downstream pruning.
- `_commit_dynamic_port_keys(node, group, property_value, *, removed_port_key)`: shared application mechanics after operation-specific validation.

Preserve:

- Singular unknown-property rejection and its scalar return value.
- Bulk ignoring of unknown/blank keys and its changed-property mapping.
- Bulk normalization against the original properties before contextual updates.
- Script-only restrictions and routing through atomic Apply.
- Direct dynamic backing-property write rejection.
- No-op behavior without revision changes.
- Dynamic key callbacks’ defensive property copy.
- Collision, limit, resolver, and catalog validation before writes.
- Generic removal ordering: incident edges → backing property → removed-key state → downstream pruning.
- Existing removed-edge return ordering.
- Source-backed dynamic edits calling Apply once and retaining their current return values.

Script Apply retains its candidate-first validation, saved-value checks, independent `make_default()` values, one candidate node clone, and existing history boundary.

Generic property/dynamic mutations retain their current expected-failure preflight followed by writes and pruning. This plan does not add an all-exception rollback guarantee for an unexpected failure during final pruning.

Expose the kernel’s existing memoized port lookup as `effective_ports_for(...)`, updating direct callers. Registry normalization consumes the existing invocation-scoped memo rather than independently materializing effective ports again. Do not add another cache.

Registry compatibility checking remains read-only and does not call normalization or mutation.

### Commit-history preservation

The ledger links these commits to the corresponding tests and acceptance evidence:

| Commit | Behavior to preserve |
|---|---|
| `36c9ea6b` | Full-schema tables, explicit views, bounded full-array sampling, ND-axis requirements, streaming exports |
| `a88bcea3` | Scientific values and the separate Signal Plot contract |
| `09502b9e` | Existing clean generic Line Plot retirement in favor of Signal Plot/XY |
| `c218649b` | Candidate-first atomic Python Script Apply |
| `f2fc1818` | Canvas port handles routed through source editing and Apply; dirty editor drafts and Undo/Redo |
| `9b8bb83f` | Ordered dynamic ports and wire/state behavior |
| `7235d8ef` | Forwarding-derived types, semantic comparison, and downstream compatibility pruning |
| `2f03ea69` | Independent defaults, readiness behavior, and explicitly unresolved responsiveness gates |

Current source and active contracts govern implementation. History supplies intent; it does not justify restoring superseded behavior.

## Public Interface Changes

The approved amendment retires generic `plot.scatter` and makes the existing Signal Plot pipelines the line/scatter authoring route. No automatic persistence migration is introduced; existing unresolved-node rejection remains explicit and source files remain unchanged.

For all retained nodes, preserve IDs, properties, ports, output mappings, runtime carrier formats, render-request payloads, `.cxproj` documents, QML slots, graph action IDs, and the public `corex` SDK. Scatter retirement is the explicit exception; do not silently translate its incompatible input/output wiring.

Internal imports change to the new direct owners. Update all repository callers and patch targets in the same task; leave no forwarding aliases or obsolete test wrappers.

Test module locations change according to the migration rules below. Existing shell target IDs remain intact.

## Execution Tasks

### T01 — Establish the plan, ledger, characterization, and baseline

- **Goal:** Make subsequent changes measurable and recoverable.
- **Preconditions:** Implementation is authorized; repository root and current HEAD are rechecked.
- **Conservative write scope:** New plan/ledger, dedicated benchmark scripts and their focused checks, selected characterization tests, and one task-owned specs-index entry.
- **Deliverables:** Persist this plan as `docs/PLAN_COREX_PLOT_GRAPH_OWNERSHIP_REFACTOR.md` and create `docs/PLANS/COREX_PLOT_GRAPH_OWNERSHIP_TASK_LEDGER.md`. Record protected dirty files, exact collected test IDs, history constraints, baseline results, fixture hashes, environment, and benchmark commands.
- **Verification:** Run the affected baseline cohorts; establish whether any failures predate the refactor. Validate benchmark source provenance and deterministic semantic outputs before timing.
- **Non-goals:** Production refactoring, dependency upgrades, cleanup of unrelated files.
- **Packetization:** Bootstrap plus P01 if later converted into packets; no packet manifests are created now.

Create two focused benchmark scripts: one for generic Plot preparation/export and one for graph reconciliation. They use existing entry points and are frozen before their respective production changes.

Add characterization only where current coverage does not distinguish the policies described above.

### T02 — Retire redundant Scatter and establish inert Plot specifications

- **Goal:** Establish the chosen Signal Plot line/scatter workflow and give retained generic declarations and role metadata one owner.
- **Preconditions:** T01 accepted.
- **Conservative write scope:** Plot specifications/initializer/orchestration/adapter and direct consumers; scatter catalogue/icon retirement; Signal declaration discoverability and guide; visual-parity line/scatter routing through production Signal/XY; affected generic/Signal/serializer/tool tests, canonical catalogue fixture maintenance, generated Plot examples and their generators; associated maps/indexes.
- **Deliverables:** Seven specialized generic definitions; existing Signal marker-only workflow documented/searchable; explicit saved-Scatter rejection proof; `specs.py`; inert initializer; direct metadata imports; distinct editor/runtime role metadata; test fixtures moved to retained types without lost shared coverage.
- **Verification:** Exact seven-type generic catalogue plus Signal and absence of line/scatter IDs; marker-only XY with no line marks; Signal to Media Panel/Image Export; unchanged-document rejection; fresh defaults, role/coercion characterization, registration, tabular guards, fresh-process optional-import checks, affected generated example validation.
- **Non-goals:** New Signal rendering modes, lossy automatic migration, recreation of Scatter CSV outputs, data-read/decimation/backend algorithm changes.
- **Packetization:** P02; independent review before acceptance.

Registration imports descriptors from their actual owner. Metadata imports must not load NumPy, tabular execution machinery, or plotting backends merely to inspect Plot specifications.

### T03 — Consolidate Plot preparation and request construction

- **Goal:** Remove duplicated table/window preparation and duplicated request construction.
- **Preconditions:** T02 accepted.
- **Conservative write scope:** `data_series.py`, generic request/execution orchestration, direct preparation consumers, preparation/request tests, relevant maps.
- **Deliverables:** Explicit table selection, shared table read path, retained array strategies, common request builder used by execution and previews.
- **Verification:** Existing series/decimation cases, table/window provenance and limit cases, array/slice/ND cases, no-NumPy dictionary input, errors/warnings, and read-call counts.
- **Non-goals:** New sampling algorithms, altered retained-node mappings, loader-cache changes, Signal Plot rendering changes beyond the T02 discoverability/documentation amendment.
- **Packetization:** P03; move preparation and request-codec tests with this task.

Redirect private helper consumers, including visual-parity tooling, to their new actual owner.

### T04 — Extract Plot exports and complete test ownership

- **Goal:** Give export publication one owner and align remaining tests with production responsibilities.
- **Preconditions:** T03 accepted.
- **Conservative write scope:** `exports.py`, plugin export orchestration, export/surface/preview tests, small shared test fixtures, maps and import callers.
- **Deliverables:** Shared source preflight, unchanged publication/cleanup behavior, export-owned tests, merged sink-mode coverage, scene and preview tests in existing owners.
- **Verification:** Successful paired export; second-registration failure after store mutation; stable-ID replacement; strict cleanup refusal; unrelated-artifact preservation; original exception identity; full-source table/array exports; headless subprocess exports.
- **Non-goals:** Artifact-store redesign, new transaction machinery, renderer changes.
- **Packetization:** P04; no compatibility method remains for the removed plugin export implementation.

Move monkeypatches to the new export owner. Backend factory patches remain on the real backend owner.

### T05 — Accept Stage A

- **Goal:** Establish a complete, independently reviewed Plot result.
- **Preconditions:** T02–T04 accepted.
- **Conservative write scope:** Task evidence, navigation/docs, and bounded fixes returned to the responsible writer.
- **Deliverables:** Complete test migration accounting; Plot correctness, performance, and independent review results; a frozen Stage A source snapshot for Stage B comparisons.
- **Verification:** Combined Plot cohort, retained inline-editor shell target, matched performance measurements, `fast` verification once, and documentation/navigation checks.
- **Non-goals:** Starting graph changes while Stage A has an unresolved regression.
- **Packetization:** P05 acceptance boundary.

Stage B begins only after this checkpoint is accepted. An inconclusive performance result remains visible and must be resolved before claiming performance acceptance.

### T06 — Establish graph characterization and test ownership

- **Goal:** Make the graph’s differing policies explicit before consolidating them.
- **Preconditions:** T05 accepted.
- **Conservative write scope:** Graph benchmark, graph/declaration/scene/persistence tests, small graph fixture owner, ledger and maps.
- **Deliverables:** Stage B baseline against accepted Stage A; exact test migration mapping; characterization of policy, return-value, no-op, and refusal behavior.
- **Verification:** Moved tests pass before production changes; pure/declaration tests no longer require scene imports; retained integration tests remain collected.
- **Non-goals:** QML command reorganization or changing graph behavior.
- **Packetization:** P06.

Move shared dynamic-registry fixture construction into `tests/graph_mutation_fixtures.py`. Keep assertions in test owners.

### T07 — Introduce pure port-state reconciliation

- **Goal:** Remove duplicated Script/load projection policy while keeping their differences explicit.
- **Preconditions:** T06 accepted.
- **Conservative write scope:** New port-state owner, Script Apply, registry normalization, kernel port lookup, direct tests and maps.
- **Deliverables:** `NodePortState`, two named projection functions, memoized effective-port reuse, removal of superseded projection bodies.
- **Verification:** Input nonmutation, detached result dictionaries, required exposure, label permissions, modifier preservation/canonicalization, Principal eligibility, semantic-versus-forced-pruning behavior, settings-order preservation, normalization idempotency.
- **Non-goals:** Moving settings-group policy into the port helper, adding a resolver/cache, changing compatibility checks.
- **Packetization:** P07; independent review of policy differences and allocation/resolution counts.

### T08 — Consolidate property and dynamic-edit application

- **Goal:** Remove repeated mutation sequences without changing entry-point contracts.
- **Preconditions:** T07 accepted.
- **Conservative write scope:** Private `ValidatedGraphMutation` helpers and callers, focused mutation/contextual-property tests, source banners/maps.
- **Deliverables:** Shared normalized-property commit and dynamic-key application; operation-specific validation remains at entry points.
- **Verification:** Singular/bulk differences; no-ops; Media Panel source restrictions; collisions and limits; source-backed Apply routing; label-versus-key rename; returned edge IDs; forwarding pruning; rejected-operation state/revision/history equality.
- **Non-goals:** A general transaction framework, UI contextual-property cleanup, additional graph copies or pruning passes.
- **Packetization:** P08; independent review before acceptance.

Run affected Mechanical contextual-control/default-port tests because their property changes use this common mutation path.

### T09 — Accept Stage B and close the program

- **Goal:** Prove the complete refactor and leave accurate navigation and evidence.
- **Preconditions:** T07–T08 accepted.
- **Conservative write scope:** Final evidence/docs/navigation and bounded fixes assigned to their original owners.
- **Deliverables:** Final ownership map, complete test dispositions, measured performance results, review closure, explicit deferred findings.
- **Verification:** Graph cohort, retained Script editor/canvas integration, structural counters, matched Stage B benchmarks, one final `fast` integration run, and required documentation/navigation checks.
- **Non-goals:** Worker, graph-scene rebinding, artifact rename, global shell-fixture, or unrelated performance work.
- **Packetization:** P09 closeout.

Do not repeat already valid expensive checks merely to produce a second closeout record. Rerun when subsequent changes invalidate their evidence.

## Work Packet Conversion Map

No packet set is created for this work.

If later requested:

| Packet | Task |
|---|---|
| P00 | Bootstrap, plan registration, ledger initialization |
| P01 | T01 characterization and measurement baseline |
| P02–P04 | T02–T04 Plot implementation |
| P05 | T05 Stage A acceptance |
| P06 | T06 graph baseline/test ownership |
| P07–P08 | T07–T08 graph implementation |
| P09 | T09 final acceptance |

Dependencies remain sequential. Shared-checkout writers do not run concurrently.

## Test Plan

### Test ownership and preservation

T01 records exact collected IDs, including parametrized cases. Migration is accounted for by:

`old ID → retained/moved/merged → new ID → preserved behavior → verification evidence`

Unchanged tests remain covered by the baseline inventory. The confirmed sink-mode duplicate may merge through a documented assertion union. Under the user-approved Scatter retirement amendment, Scatter-only cases may become explicit retirement/Signal-workflow cases; shared generic behavior must move to retained-node fixtures, not disappear. Record every changed expectation and its intent.

| Current owner | Final disposition |
|---|---|
| `test_plot_node_contracts` | Retain declaration/catalog tests |
| Its preparation tests | Move to `test_generic_plot_preparation` |
| Its render-request codec test | Move to `test_plot_render_request` |
| Its archive/publication tests | Move to `test_generic_plot_exports` |
| Its scene projection/invalidation tests | Move to existing `test_plot_surface_integration` |
| Its shared preview-cache identity test | Move to existing `test_plot_auto_preview_service` |
| `test_python_script_declaration` | Retain parser/declaration/diagnostic tests |
| Its direct graph-edit tests | Move to `test_graph_node_reconciliation` |
| Its real scene/history/payload tests | Move to `test_python_script_scene_integration` |
| Its fragment/serialization tests | Move to `test_python_script_persistence` |
| Dynamic edit tests in `test_dataflow_graph_persistence` | Move to graph reconciliation; retain actual persistence/runtime/fragment cases |
| Registry-normalization cases across existing suites | Move to `test_graph_registry_normalization` |

The baseline audit identified 27 tests in the mixed Plot module and 20 in the Python Script declaration module. These counts are inventory aids; exact IDs and parametrizations establish preservation.

The sink-mode merge retains default payload, empty suppression reasons, disabled/enabled behavior, and lightweight-canvas suppression.

Retain headless subprocess exports, both 4,500-row full-fidelity export fixtures, registry compatibility/replacement tests, actual canvas clicks, and every ScriptEditorDock shell target.

### Correctness cohorts

All commands use the repository’s `venv/Scripts/python.exe`. Use serial `-n 0` for focused cohorts and preserve existing shell child isolation.

**Plot cohort:** declaration, preparation, request-codec, export, property-adapter, decimation, headless export, preview-service/cache, surface-integration, tabular-performance guards, passive-runtime wiring, affected registry/serializer/host/overlay tests, and Signal renderer/input/PlotValue/media/image-export coverage affected by retirement. Preserve existing Signal fullscreen/XY contracts.

Retain this exact shell target:

```text
tests/test_shell_isolation_phase.py::test_shell_isolation_target[run_controller__test_plot_property_updates_retain_inline_rows_across_settings_and_ports]
```

**Graph cohort:** declaration, reconciliation, registry normalization, Script scene/persistence, dataflow persistence, graph type enforcement, forwarding, rewire validation, registry validation/compatibility/replacement, data-tree UI, and affected contextual-property tests.

Retain this exact shell target:

```text
tests/test_shell_isolation_phase.py::test_shell_isolation_target[script_editor__test_canvas_port_edits_preserve_dirty_drafts_and_refresh_clean_editor]
```

Retain the existing validation-memo and bounded rewire-preview counter tests. Direct helper tests supplement caller and integration tests; they do not replace them.

### Performance acceptance

The selected policy is **block proven regressions**.

Freeze benchmark fixtures, timed boundaries, output schema, and instrumentation before production changes. Run the same harness against baseline and candidate source snapshots using the same interpreter and dependencies. Each process verifies its imported source path to prevent an editable installation from accidentally benchmarking the other checkout.

Use:

- Five independent baseline/candidate process pairs, alternating execution order.
- Five warmups and 50 measured operations for request preparation and graph mutations.
- One warmup and ten measured operations for full export.
- Fixture construction/reset outside timed intervals.
- Separate instrumented runs for operation counts and semantic fingerprints.
- Raw samples, per-process median/p95, and run-to-run variability retained in ignored artifacts.
- No concurrent tests, builds, or other agent benchmarks during timing.

Retained generic Plot fixtures cover in-memory series, 200,000-row tables, offset/limited windows, 200,000×8 arrays, explicit slices, and 100,000-row full exports, using retained Bar/grid families as appropriate. Existing 4,500-row fixtures continue as correctness proofs. Existing Signal Plot benchmark/semantic checks separately cover the chosen line/scatter pipeline; no timing of retired generic Scatter is acceptance evidence.

Graph fixtures contain 100 and 1,200 nodes with fixed local connectivity and unrelated-node counts. Measure Script Apply, dynamic insert/remove/key rename, ordinary property updates, and registry normalization separately.

Use the existing tabular performance harness for composed application checks on generated absolute-path source projects. Its project-copy behavior omits managed `.data` sidecars, so do not use a sidecar-dependent fixture without explicitly preserving that dependency. Keep its existing metric schema; do not pass unsupported p95 budget keys.

Hard structural gates:

- No added source reads during scene projection.
- No increased Plot read/materialization counts or unbounded sampling.
- Unchanged point limits, exported rows/columns, provenance, and cleanup behavior.
- No additional graph copies, history snapshots, resolver passes, or pruning traversals.
- No resolution or edge traversal inside pure port-state projection.
- One existing registry-validation memo with correct invalidation.
- No new eager optional-library imports.

A suspected timing regression receives one matched confirmation cohort and path attribution. Reproducible degradation attributable to the refactor blocks acceptance and returns to the responsible writer. Uncontrolled or uninterpretable measurements are `INCONCLUSIVE`, not a performance pass.

Report “no measured regression” with the measurement limits; do not claim mathematically zero overhead. Existing execution-responsiveness failures remain separately documented and are not repaired or declared passing by this refactor.

### Navigation and documentation

Each accepted production slice updates its source banners, owning maps, coverage rows, and affected test selectors.

Regenerate source/test inventory before the route index. Regenerate QML navigation only if its inputs change.

Run the repository’s map, Markdown-link, traceability, and generated-index freshness checks. Use `fast --summarize-output` at the two stage acceptance boundaries. A full shell-wide or release lane is not required unless implementation unexpectedly expands into those surfaces.

### Orchestration and recovery

- The primary agent coordinates requirements, scope, dependencies, acceptance, and the ledger.
- Fresh implementation workers own coherent tasks; one writer is active in the checkout at a time.
- Each substantial implementation task receives independent review against its recorded baseline and this plan.
- Review findings return to the original writer; that writer does not approve its own changes.
- Performance verification runs independently and serially.
- The coordinator alone updates task acceptance status.

The ledger contains task, owner, allowed scope, prerequisite, status, evidence, reviewer, accepted source snapshot or commit, and next action. It also contains test migrations, history constraints, and performance conclusions.

After any compaction or resumption, the coordinator **fully rereads the plan and entire task ledger**, then current instructions, Git state, active-agent state, and the next incomplete task before delegating or editing. Raw logs are opened only to resolve an uncertainty.

## Assumptions

- Implementation targets the current checkout after confirming its root and baseline. The later explicit publication request authorizes a scoped commit to existing `main` and push; no branch change is required.
- Preserve the existing changes to `AGENTS.md`, the physical-simulation specs-index entry and plan, and the strain-candidate CSV. Add only the new task-owned index entry.
- Internal architecture may change substantially; user-visible behavior and established data contracts remain stable.
- Cleanup success is measured by fewer independent policy implementations, clear direct owners, navigable tests, preserved coverage, and performance evidence—not a line-count quota.
- New Signal Plot rendering features, worker execution, graph-scene method rebinding, artifact-store/rename redesign, fullscreen tabular sessions, Mechanical adapter restructuring, and global shell-fixture cleanup remain explicit follow-ups. The approved Signal discoverability/documentation and generic Scatter retirement are part of Stage A.
