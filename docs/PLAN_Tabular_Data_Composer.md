# Tabular Data Composer and UI Redesign

## Summary

Redesign Tabular Data Input around one persisted, reusable data view. Users will browse a file's contents, combine arrays or tables, assign coordinates and labels, and configure output filters, sorting, rows and columns in COREX's existing fullscreen workspace.

Each node reads **one file and produces one configured table or array**. Multiple nodes referencing the same file share source caches.

The implementation covers the existing supported formats: CSV/TSV/text, Excel, Parquet, NPY/NPZ and HDF5. The primary acceptance example is the gearbox archive: `temperature_history_C` + `time_s` + `node_ids` must produce a labeled **3,001-row x 36-column table**.

**Execution agreement**

- The primary agent is the sole implementation worker and owns verification and progress tracking.
- Subagents may perform bounded, read-only exploration only. No implementation or review agents.
- This document contains the complete approved plan and one task-progress table.
- Track task, status, evidence, unresolved findings and next action. All implementation tasks initially remain **Not started**.
- **After every compaction or resumption, reread this entire plan and entire progress table before editing or assigning exploration.** Then reload current instructions, inspect Git state and relevant diffs, and identify the next incomplete task.
- Preserve existing unrelated changes. The 2026-09-14 follow-up authorizes restyling and committing/pushing the tabular changes to main. Installer creation remains outside scope.

### Task progress

Implementation baseline: `3a5648d678c5fd4b9ad63432e3a0908ea2f08213` on `main`, 2026-09-14. Initial unrelated changes: `AGENTS.md`, `docs/specs/INDEX.md`, `tests/fixtures/graph_canvas_surface_snapshot.json`; untracked physical-simulation plan and strain-gage CSV. Preserve all of these; the specs index may receive only this plan's own registration. Owner of all tasks: primary agent.

| Task | Status | Evidence / unresolved findings | Next action |
| --- | --- | --- | --- |
| T01 | Complete | Baseline: 52 contract/input/preview/loader tests passed | none |
| T02 | Complete | Immutable 48 KiB recipe, load options, authored property declarations; 39 contract/ref/loader checks passed. Old live properties removed in T06 | none |
| T03 | Complete | Header-only NPZ catalogue, unsupported-member reporting, atomic selected-member mmap cache sharing the tabular disk budget; 46 focused tests passed. UI cancellation binding completed in T07 | none |
| T04 | Complete | Real archive returns 3001 x 36; 34 composition/retention tests passed; earlier 35 composition/cache/input tests passed. Windows/column reads, batches, ND projection, append types, raw slices and fresh retained reopen covered | none |
| T05 | Complete | Separate query subprocess, cached typed Parquet, complete filters/sort/range, nullable-integer precision; 48 saved-query/composition/Signal Plot/native-guard tests passed | none |
| T06 | Complete | Input and plot consumers use data_view; old live properties removed; project/fragment convert-and-flag; 62 input/plot/provider tests and 12 migration/function tests passed. Input inspector now metadata-only summary | none |
| T07 | Complete | TabularComposerSession/catalogue model/fullscreen delegation; cancellation context; source draft and unique managed stage callbacks; 7 session tests passed, including real GraphSceneBridge one-step undo/redo | none |
| T08 | Complete | Fullscreen and inline composer, explicit ND preview planes, suggestions, one-based labels/units; 5 real QML interaction/light/narrow tests, 12 session/QML checks and 9 graph-host tests passed. Cold inline data IO is now entirely worker-owned | none |
| T09 | Complete | Atomic visible/selection/output exports; bounded ND NPY writer; isolated managed staging and cleanup callback; synthetic three-view example plus maintained examples regenerated. 21 export/extraction/session tests and 6 example/Save As checks passed | none |
| T10 | Complete; broad gates not green | 253 owning-route checks; 155 inventory/architecture/inspector checks + 1305 subtests; 22 targeted fullscreen/probe checks passed. Real gearbox proof: 3001x36, 3001x47, 3001x82; exact filtered/sorted fresh-loader values and 3001-row CSV equality; source SHA unchanged. Fast: 5636 passed / 1 failed; fast serial: 220 passed; Qt Quick passed; GUI: 601 passed / 2 failed; GUI serial: 39 passed / 3 failed. Three transient failures passed isolated; three unchanged Constant/viewer sizing assertions still fail. Maps/traceability/links and diff whitespace checks passed. See final acceptance below | No remaining tabular implementation work; unrelated sizing failures require separate diagnosis |
| T11 | Implementation and verification complete; publication authorized | Composer-local controls reuse shared dialog theme/contrast behavior; source sidebar, compact navigation, mapping card with optional advanced fields, preview/status footer and source onboarding. 416 checks + 90 subtests passed, including 13 real QML checks for keyboard member/axis input, light/dark/empty rendering and non-overlap at 1480x820, 1100x780 and 760x1024. Documentation/map checks passed. User explicitly requested commit/push of the tabular work to main | No remaining UI work; the task response and Git remote identify the published revision |

The T11 visual follow-up supersedes the original plain-control layout. It preserves all data-view, Apply/Cancel, source-integrity and export semantics. No global Qt style or unrelated Constant/viewer geometry was changed. The earlier broad-suite failures remain disclosed above; T11's affected-surface verification is green. Source/test inventories were regenerated. The physical-simulation plan/index row, AGENTS changes, graph-canvas snapshot and strain-gage CSV are excluded from the tabular publication.

### T12 — Configure action in the floating toolbar

The user requested moving Configure data out of the node body, adding an appropriate icon, and committing/pushing to main. Implementation and verification are complete: the action now leads the existing floating toolbar, with a tintable table-and-sliders SVG registered in the shared icon system. It reuses the fullscreen action ID and surface-action dispatch to open the same draft session. The inline button and reserved row are removed; migration-review text is retained and empty-state guidance points to the toolbar. **181 checks and 35 subtests passed**, including real toolbar mouse/Enter dispatch in empty, selection-required, ready and error states, no configuration mutations, recovered preview space, and tinted icon rendering at 15/20/24 pixels. Agent-map, traceability, Markdown-link and whitespace checks passed. Unrelated dirty paths are excluded from publication; the task response and Git remote identify the published revision. The preceding T11 implementation was published as `36c9ea6b` on main.

### Initial implementation acceptance — 2026-09-14 (before T11)

**Outcome:** Implementation complete; tabular acceptance passed; repository-wide acceptance is not green. The primary agent performed all implementation and verification. No implementation/review subagents, commits, staging, push, installer or publication were used.

- The local private gearbox archive passed exact NumPy equality checks for full temperature, heat-flow and combined outputs, a filtered/sorted/ranged result reopened with a fresh loader, and a full 3,001-row temperature CSV. Its original SHA-256 remained unchanged. Only synthetic fixtures/examples were added to the repository.
- Deterministic checks cover metadata-only NPZ discovery, one-time selected-member decompression, bounded preview/selected-column reads, complete saved queries, retained-source content binding and HDF5 containment. Actual QML interactions cover mapping, validation, output-range entry, Apply, preview reset, light/dark and narrow layouts.
- Offscreen/software QML measurement on the real 1,328-member archive: cold preview ready in 444.91 ms (dispatch 7.51 ms); warm in 123.09 ms (dispatch 3.83 ms). Preview stayed at 50 x 36 cells. Maximum 10-ms UI-timer gaps were 88.14 ms cold / 69.98 ms warm. These are local responsiveness observations, not display-attached release or frame-rate acceptance.
- Broad phase logs: `artifacts/verification_logs/20260914_230514/01_fast.pytest.log`; `artifacts/verification_logs/20260914_231636/`; `artifacts/verification_logs/20260914_composer_serial/`. Serial phases were executed using the verification runner's unchanged manifest-built commands after its normal fail-fast behavior stopped the preceding broad phase.
- Persistent, isolated failures outside the tabular owners: `GraphModelTrackBTests.test_hide_optional_ports_shrinks_custom_height_by_removed_rows`, `ViewerSurfaceContractTests.test_viewer_host_heals_stale_default_height_without_explicit_node_height`, and `ViewerSurfaceContractTests.test_viewer_port_rows_stay_inside_shell_for_large_graph_labels`. Relevant Constant/viewer geometry, QML host and test files are unchanged. These were not repaired under T10's explicit non-goal of unrelated failing-test repairs; no baseline-green claim is made for them.
- The broad-run external-runtime identity handshake failure, desktop datetime-probe activation failure, and flow-edge hit-test timeout all passed in the final focused rerun. Their broad-run failures remain recorded, not counted as successful broad gates.
- Agent-map, traceability and Markdown-link checks passed. The protected initial dirty paths remain preserved; only this plan's row was added alongside the user's existing specs-index changes. COREX was not restarted or packaged as part of this task.

## Key Changes

### Composition and output behavior

- Preserve the compact graph node with filename, view name, output dimensions and bounded preview. Per T12, **Configure data** lives in its floating toolbar rather than the node body.
- Use the approved interactive mockup as the layout reference. The fullscreen editor contains a searchable source browser, composition controls and the resulting preview.
- Simple single-table files open directly. Archives with multiple members require an explicit source choice.
- **Build table:** choose values, an optional row coordinate, and optional column labels. A row coordinate becomes an ordinary first column; otherwise the table has presentation-only row numbers.
- **Array axes:** support vectors, matrices, transpose and higher-dimensional arrays. For higher-dimensional table views, explicitly select row/column axes and fixed indices for every remaining dimension.
- **Add columns:** append value blocks horizontally, matching rows by position. Require equal row counts; do not broadcast, truncate or align by inferred keys.
- **Append rows:** combine ordered segments vertically. Match unique column names exactly, regardless of source column order. Reject missing/extra columns and incompatible types. Permit only conversions that preserve all values.
- Require unique, nonblank output column names. Offer explicit renaming and block prefixes to resolve collisions.
- Preserve types and supplied units. Units can be entered explicitly; no unit conversion or interpretation of units solely from filenames.
- Raw-array mode preserves an array output. Preview plane selection remains separate from any explicitly authored output slice. Table filters and sorting require table mode.

### Saved output rules

Use this fixed operation order:

**Map and combine -> filter rows -> sort rows -> select output row range -> select/reorder output columns.**

- Provide a condition builder with **Match all / Match any** for one group of conditions.
- Support typed comparisons, text matching, and missing/present checks. Exclude nested expression trees, arbitrary formulas, Python and user-authored SQL.
- Provide ordered sort keys with ascending/descending choices. Preserve original assembled row order for ties; place missing values last.
- Keep integers, floating-point values, booleans, text and datetimes typed. Parse filter literals in Python rather than through JavaScript numbers, preserving large integer precision.
- Retain the established missing-value behavior for nulls, non-finite values and blank text, with explicit missing/present operators.
- Filters and sorting evaluate the complete configured dataset. The existing bounded preview scan must never become an output-data limit.
- Default output is all rows and columns. UI ranges use one-based inclusive labels; stored ranges use canonical offsets and limits.

### Preview and editing behavior

- QML edits a draft. **Apply** commits the complete validated configuration in one undoable operation; **Cancel** discards it.
- Preview scrolling, cell/header selection, column widths and "Find in preview" do not change downstream output.
- Display saved filters and sorting under **Output rules**, clearly separated from preview inspection.
- Show preview dimensions separately from output dimensions. Unknown counts display as pending until computed.
- Immediately clear obsolete values when the source or mapping changes. Ignore late responses from older draft generations.
- Preserve drafts across unrelated graph updates. If the same node's configuration changes elsewhere, block overwriting and offer **Reload current configuration**.
- Dirty close or retarget offers Apply, Discard or Keep editing. Node deletion retires the draft safely.
- Source selection records a path and storage intent in the draft. Managed copying occurs on Apply into a new artifact; cancellation never replaces the currently used source.

### Existing-project conversion

Apply the agreed **Convert and flag** policy:

- Preserve the source, parsing options and selected member.
- Default converted input nodes to full output.
- Move old input column/slice hints into a persistent review notice, including former 50-row defaults.
- Offer **Use previous selection** to populate explicit draft output limits, followed by normal Apply.
- Leave existing Table Filter and Array Slice nodes unchanged.
- Dismissed notices stay dismissed; new nodes receive no migration notice.
- Apply conversion consistently to project documents, clipboard fragments and library/custom-workflow imports.

## Public Interface Changes

- Retain `TabularDataRef`, `ArrayDataRef` and the existing **Table Data / Array Data** port identities. No new collection-valued output type.
- Add a versioned `DataViewDefinition` representing ordered members/blocks/segments, axes, coordinates, labels, output conditions, sorting and selection.
- Persist that definition as the node's canonical `data_view` property. Store the display name, migration notice and presentation state separately.
- Extend normalized load options and reference identity with the complete definition, allowing a fresh loader process to reconstruct the view without an existing cache.
- Store member references and transformations, not source arrays, expanded preview rows or large label lists. Enforce the existing reference-metadata limit; never silently discard required mapping information.
- Keep the outer project format unchanged. Perform the property migration before registry normalization discards retired properties.
- Extend the fullscreen bridge through one tabular-specific draft session and a virtualized catalogue model. Reuse the existing bulk graph-property mutation API.

## Execution Tasks

All tasks are performed sequentially by the primary agent. Each task includes its focused tests and affected documentation updates. Packetization notes for every task: **none; direct single-worker execution**.

### T01 - Record the baseline and recovery state

- **Goal / Preconditions:** Establish the implementation baseline after plan approval.
- **Conservative write scope:** Plan/progress document, relevant specification registration and focused fixture helpers.
- **Deliverables:** Complete saved plan, progress table, recorded Git baseline, protected dirty paths and focused baseline results.
- **Verification:** Confirm checkout root and current instructions; run the existing contract/input/preview tests needed to distinguish pre-existing failures.
- **Non-goals:** Production changes, unrelated cleanup or a separate tracking framework.

### T02 - Define the canonical data-view contract

- **Goal / Preconditions:** After T01, make composition and output rules explicit and serializable.
- **Conservative write scope:** Runtime contracts, tabular load options, node declarations and contract tests.
- **Deliverables:** Validated versioned definition, canonical identities, stable column references, structural validation and full-output defaults.
- **Verification:** Round trips, malformed definitions, axis/index errors, duplicate labels, oversized descriptors, identity changes and presentation-only invariance.
- **Non-goals:** UI authoring and new runtime carrier types.

### T03 - Implement metadata discovery and member caching

- **Goal / Preconditions:** After T02, browse large archives without loading all their values.
- **Conservative write scope:** Tabular source backends, shared cache lifecycle, catalogue metadata and async discovery.
- **Deliverables:** NPZ header inspection; HDF5 hierarchy metadata; searchable catalogue records with type, shape and size; reusable selected-member reads.
- **Verification:** Enumerate the gearbox archive without reading its 159 MB manifest body; cover malformed/object-array members, case-sensitive names, cancellation and cache invalidation.
- **Non-goals:** Domain-specific manifest interpretation or weakening `allow_pickle=False`.

### T04 - Implement lazy table and array views

- **Goal / Preconditions:** After T03, resolve composition through existing table/array service methods.
- **Conservative write scope:** Tabular records, composition evaluator, schema/window/batch readers and retained-source validation.
- **Deliverables:** Axis mapping, labeled tables, positional column assembly, strict row append, explicit array slicing and fresh-process reopening.
- **Verification:** Compare windows, column arrays, streaming batches and materializations; test append boundaries, transpose, higher dimensions, type preservation and incompatible shapes.
- **Non-goals:** Joins, broadcasting or silent data truncation.

Preserve whole-file content binding for retained results. Validate every contributing HDF5 member against existing containment rules. Source changes, including equal-size/equal-timestamp replacements, must invalidate affected retained results and derived caches.

### T05 - Implement complete saved filtering and sorting

- **Goal / Preconditions:** After T04, execute saved rules consistently for all consumers.
- **Conservative write scope:** Typed tabular query contract/evaluator, derived caches and a dedicated query subprocess.
- **Deliverables:** Complete filtering, stable sorting, post-query output selection and exact resulting row counts.
- **Verification:** Compare against independently computed expectations; cover large integers, datetimes, missing values, multiple sort keys, empty results, cancellation and datasets beyond the old preview scan cap.
- **Non-goals:** Arbitrary SQL, nested expressions or approximate output.

Use the already-declared DuckDB dependency **only in a separate process**, preserving the repository's prohibition on GUI-process imports. Stream required composed columns into managed Parquet and write queried results to a derived cache. DuckDB supports sorting with disk spill for larger-than-memory workloads: [workload guidance](https://duckdb.org/docs/current/guides/performance/how_to_tune_workloads).

Launch through COREX's active/add-on runtime resolution. Start with a 512 MiB engine memory setting, two query threads and temporary storage inside the existing managed-cache budget. Treat these as engine settings, not a guaranteed process-memory ceiling. Errors or cancellation must not publish partial results.

### T06 - Convert existing nodes and update consumers

- **Goal / Preconditions:** After T05, make every consumer use the configured output.
- **Conservative write scope:** Tabular input execution, shared property migration, project/fragment boundaries, plot-source descriptors and affected consumers.
- **Deliverables:** Convert-and-flag migration; removal of live input preview hints; preserved extraction nodes; correct direct and one-hop plotting.
- **Verification:** Old/new project and fragment round trips, repeated conversion, notice dismissal, restoring prior selections, and preview/plot/export agreement.
- **Non-goals:** Rewriting unrelated plot behavior or preserving retired internal APIs.

### T07 - Add the fullscreen draft session

- **Goal / Preconditions:** After T06, provide a reliable editing lifecycle.
- **Conservative write scope:** Tabular session/provider, fullscreen bridge, async request routing and source-staging callbacks.
- **Deliverables:** Draft creation/update/validation, atomic Apply, Cancel, conflict detection, safe managed-copy application and generation-based async rejection.
- **Verification:** One undo/redo step; unchanged Apply; dirty close; unrelated node updates; source replacement; failed staging; node deletion; workspace changes.
- **Non-goals:** A new shell-wide session framework.

### T08 - Build the shared composer UI

- **Goal / Preconditions:** After T07, implement the approved mockup with the additional agreed operations.
- **Conservative write scope:** Tabular QML, catalogue/table models, input-node inspector presentation and shared surface controls only where necessary.
- **Deliverables:** Persistent Configure entry; virtualized searchable browser; block/segment editing; axes and labels; condition/sort builders; explicit output selection; responsive preview.
- **Verification:** Actual QML interaction and rendering in light/dark themes, keyboard navigation, narrow fullscreen widths, large catalogues and validation/loading/error states.
- **Non-goals:** Rebuilding unrelated node controls or creating one port per view.

### T09 - Complete export, portability and examples

- **Goal / Preconditions:** After T08, make the new view usable throughout normal workflows.
- **Conservative write scope:** Tabular export services, managed-source persistence, maintained examples and integration tests.
- **Deliverables:** Clearly labeled **Export visible preview**, **Export selection** and **Export configured output**; cancellation-safe writes; portable saved configurations.
- **Verification:** Export values, ordering and headers match the chosen scope; Save As/internalized sources reopen; multiple nodes share source caches; large exports stream.
- **Non-goals:** New export formats or publishing the user's private archive.

Configuration exports identify when they use an unapplied draft. Invalid drafts cannot export. Selection export uses the explicitly selected displayed cells/columns; configured-output export uses the complete saved-rule result.

### T10 - Integration acceptance and closeout

- **Goal / Preconditions:** After T09, verify the complete workflow and record the final outcome.
- **Conservative write scope:** Remaining task-related fixes, tests, route maps, specification links and the single progress/evidence record.
- **Deliverables:** Completed acceptance evidence, clean task diff, documented behavior changes and no unfinished task findings.
- **Verification:** Owning tabular suites, relevant retention/plot/project tests, fullscreen and mutation isolation tests, followed by repository `fast` and `gui` lanes. Run applicable documentation/map checks and native-runtime import guards.
- **Non-goals:** Unrelated failing-test repairs, reviewer agents, publishing or installer work.

## Work Packet Conversion Map

None. This plan uses direct execution by one implementation owner. The numbered tasks and embedded progress table provide the recovery structure; no packet manifests or per-attempt ledgers are created.

## Test Plan

Acceptance requires these end-to-end outcomes:

1. **Gearbox temperatures:** A 3,001 x 36 table with correct node labels and time values, identical across preview, downstream reads and full export.
2. **Gearbox heat flow:** A separate node produces 3,001 x 47, including correct missing-data handling.
3. **Combined view:** Add temperature and heat-flow blocks to produce 3,001 x 82 without duplicating the time column.
4. **Saved rules:** Filter Housing temperature above 40 degrees C, sort it, then select a range and columns; every consumer receives the same ordered result.
5. **Append:** Reordered matching columns succeed; missing columns, incompatible types and label collisions produce precise errors.
6. **Higher dimensions:** Explicit axis/fixed-index choices reproduce independently sliced source arrays.
7. **Persistence:** Save/reopen, fragments, library import and managed Save As retain the complete configuration and migration decisions.
8. **Lifecycle:** Apply is one undo step; Cancel preserves committed output; obsolete async results never replace the current preview.
9. **Scale:** Discovery performs metadata reads only; previews remain bounded; NPZ members are not decompressed repeatedly per column; complete output queries never inherit preview truncation.
10. **Integrity:** Source mutation, derived-cache invalidation, retained reads and HDF5 containment remain enforced.

Use the real archive locally and generated neutral fixtures for committed tests. Performance acceptance combines deterministic I/O/allocation guards with measured cold/warm UI responsiveness; do not declare success from screenshots or timings alone.

## Assumptions

### Implementation notes for recovery

- New owners so far: `runtime_contracts/data_view.py` (48 KiB canonical immutable JSON recipe), `addons/tabular_data/npz_members.py` (header catalogue and disk mmap cache), `addons/tabular_data/composition.py` (compiled block/segment/table views).
- `TableRecord.view` holds the compiled view. Shared loader dispatches composed open/window/column arrays/batches/preview/row-stream methods; retained rebuild binds source SHA to physical records. `TabularLoadOptions.data_view` survives wire reopening. Raw array slices apply in `_open_array` and determine effective reference shape.
- Composed recipes support mode `source` (single-source passthrough or implicit table when rules exist), `table` (segments), and `array` (explicit per-dimension slices). Each table segment has ordered blocks and an optional coordinate. Block fields: id/member/axes(row,column,fixed)/columns/labels_member/labels_column/names/prefix/unit. Query has match(all/any), typed-literal-text filters, sort; output has row_offset/row_limit(0=all)/columns.
- T06 canonical properties now feed `input_node.py`; old live selected_object/array_slice_2d/tabular_selected_columns properties were removed from the declaration, and their hints no longer affect Signal Plot. Shared common/node_property_migrations.py converts old saved nodes at project and fragment boundaries; old hints survive only in the persistent review notice. Inspector input selection editor was removed in favor of a metadata-only summary. Fullscreen/inline selection UI was replaced in T07/T08. Current repo-owned catalogue snapshot was regenerated for the tabular.input row only; the unrelated graph_canvas_surface_snapshot.json remains untouched.
- T05 is integrated: `_table_record` prepares complete saved rules through `saved_queries.py`/isolated `query_worker.py`; `CompiledView.query_path` redirects all composed readers to the result. Query parameters use named placeholders (DuckDB COPY positional placeholders bind destination first). No DuckDB import in the parent. Cancellation Event hooks are bound to the UI session. Query cache schema uses internal cN field names to protect case-sensitive/user column identities.
- Local acceptance cache is under the task `work/composer-cache`; the private Downloads NPZ has not been copied into the repository. Publication was first authorized by the T11 follow-up.
- T07 UI owner: `ui/tabular_composer_session.py`, owned by `ContentFullscreenBridge.tabular_composer`. It has state/catalogue/members, draft editing/apply/discard/close/conflict/notice/preview slots. The fullscreen bridge opens empty tabular nodes without synchronous data IO. Stage callbacks use a new artifact (empty previous path) on Apply. Session cancellation is propagated by `addons/tabular_data/operations.py`.
- T08 QML consumes that session: TabularFullscreenSurface.qml, TabularComposerMapping.qml, TabularComposerRules.qml. Source browser only selects an item; Use as values changes the primary block and Inspect explicitly selects the single-source view. Models are virtualized and selectors use an unfiltered member model. Row labels/summaries are one-based and column units appear in shared headers. Test screenshots live in task work/qml-composer-check-04; use Qt font registration in render tests because the Windows offscreen plugin otherwise draws missing glyph boxes. Raw ND preview is separate in ui/tabular_composer_preview.py and never silently chooses a plane.
- T09 export slots are wired through ui/tabular_composer_export.py and addons/tabular_data/exporting.py. Full ND NPY exports tile to an 8 MiB buffer. write_table_rows_to_path/write_array_rows_to_path now publish atomically; Excel uses streaming write-only workbooks. The new portable example is examples/tabular_composer.cxproj plus its .data sidecar, generated by scripts/generate_tabular_composer_example.py. The maintained showcase generator also authors data_view now and has regenerated its project/source assets. No commits/staging were performed during T09.
- T10 integration fixes: QML integral doubles are normalized at the UI boundary (contract remains strict); generic plots/schema choices no longer use old hints and full-array exports stream; query subprocess uses Python isolated mode to ignore foreign Python environment variables; retained physical compilation bypasses stat-only metadata; timezone/nanosecond query columns use integer ticks to avoid native SQL precision loss; query input only reads required value members; query scratch and NPZ members share the cache budget. Real acceptance script/results are local in task work/verify_gearbox_composer.py and work/gearbox-temperature-acceptance.csv, outside the repo.

- Target checkout: `C:\Users\emre_\PycharmProjects\EA_Node_Editor`; revalidate it before implementation.
- The mockup establishes the visual direction. Add-columns, append-segments, higher-dimensional axes and saved output rules extend that same interface.
- One file and one view per node; separate nodes may reuse the same source.
- Joins, cross-file composition, multiple named outputs, domain-specific importers, computed columns, aggregation and unit conversion are deferred.
- Existing format dependency gating and resource protections remain in force.
- No source implementation was performed during planning.
