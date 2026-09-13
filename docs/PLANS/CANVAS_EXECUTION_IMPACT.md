# Canvas execution impact

Status: **IMPLEMENTED AND REVIEWED — IDENTIFIED VERIFICATION FAILURES RESOLVED**

## Approved objective and baseline

Presentation-only canvas edits update immediately, remain saved and undoable,
and neither invalidate solutions nor dispatch workflows. One declared property
contract feeds execution-change comparison and solution identity. Full runtime
snapshots and transport attestation retain all authored state.

Implementation baseline: `adce5a49` on `main`, following the concurrent Mechanical
CDB save/export commit. Pre-existing changes to the specs index, canvas snapshot
fixture, physical simulation plan, and strain candidate CSV are preserved.
The main Astra xhigh agent is the sole implementation owner; exploration and
independent review are read-only. No external work packets were requested.
Private-main and sanitized-public publication were authorized after implementation.

History: `10128f9a` added action-name cosmetic exceptions; `63e9786f` retained them
in incremental execution; `a72486a4` proved Media Panel chrome rendering without
scheduler assertions; `bac3ec00` fixed downstream current-result reuse separately.

## Progress and acceptance

| Task | Owner | Status | Evidence / next action |
| --- | --- | --- | --- |
| T01 Property contract, declarations, inventory | Main | Accepted | 193 tests + 30 subtests passed across contract/spec/plugin/script declarations; canonical 147-row fixture regenerated with a guard proving only impact metadata changed |
| T02 Execution comparison and identity | Main | Accepted | Fallback roots and resolver shortcut findings fixed; independent follow-up resolved both; identity retains complete-snapshot attestation |
| T03 Catalogue and live presentation adoption | Main | Accepted | Viewer bulk/removal/late-open regressions pass; independent review clear; registry replacement/rollback updates metadata and catalog together |
| T04 Canvas/runtime regressions | Main | Accepted | Real QML table/plot/media regression passed; preserved counters, facts, results and timings; plot edit dispatched once |
| T05 Integration and documentation | Main | Accepted | Focused suites pass; full fast phases exercised once; five pre-existing failure reports were verified, then resolved in the requested follow-up |

## Contract and inventory

`PropertySpec.affects_execution` and public control `affects_execution` default to
`True`. Only an explicit false declaration removes normalized properties from
computational identity. Input, structural, readiness, and provenance dependencies
cannot be presentation-only. Complete properties remain available for initial
runtime setup. Existing Auto-toggle, selected/manual Run, and Trigger policies stay.

| Family / actions | Classification and rationale | Proving ownership |
| --- | --- | --- |
| Media Panel title/frame/content-only, fit/crop/rotation/mirror, PDF page, playback/bookmarks/clip display | All declared properties except `source` are presentation. Execute only validates and publishes `_surface_source`. | `media_panel.py`, media surface/renderer tests |
| Panel formatting and fit | `font_size`, `alignment`, `auto_resize` are presentation; `value`, `mode`, `interpretation` define output. | Data-control execution and Panel surface tests |
| Tabular column widths | `tabular_table_view_state` is presentation. Source, parse/loader policy, selected columns/slices and reference metadata define outputs. | Tabular input tests |
| Model Viewer appearance/bookmarks | Appearance options and `camera_bookmarks` use live session updates. `scene_input_ids` and `saved_selections` define interfaces/outputs. | Viewer control/session and engineering node tests |
| Passive annotation/web/mail/board/planning/flowchart | No executable node state; changes remain presentation unless compiled computation changes. | Passive and graph comparison tests |
| Move/resize/align/distribute/collapse/settings expansion/lock/styles/ordinary labels/comments | Presentation records, independent of history action names. | History and QML action regressions |
| Group/ungroup | Presentation when compiled node interfaces/dependencies remain equivalent. | Compilation/comparison tests |
| Ports/connections/modifiers/Principal/dynamic ports and execution links | Compare effective executable interfaces and old/new dependencies; actual changes affect computation. | Execution-plan/comparison tests |
| Run/Run Selected/Trigger/Auto mode | Explicit execution commands retain existing behavior. | Run-controller tests |
| Plot controls/slider domains/Mechanical and MARS controls | Execution defaults retained: controls define published plots, numeric semantics, exported artifacts or solver operations. | Existing route-owned tests and catalogue assertions |
| Pan/zoom/select/preview/fullscreen/copy/navigation | View/session interaction; no computational mutation by itself. Paste/duplicate/delete compare resulting executable state. | Canvas and history tests |

## Verification strategy

Run focused contract and route checks while implementing. Prove the reported
Tabular Input to Signal Plot to Media Panel path through real QML actions and
runtime counters; cosmetic changes preserve results/revisions/timings and never
queue Auto, including during active execution. Positive controls prove real edits
still invalidate the exact affected region. Cover undo/redo, bulk/mixed changes,
compiled grouping equivalence, invalid/incomplete graphs, and newest appearance
after viewer session creation/restoration. Finish with independent review and one
`run_verification.py --mode fast --summarize-output`, plus affected QML/viewer and
map/traceability/Markdown checks. Record final outcomes here once.

## Final verification and limitations

- Contract/spec/plugin/Python Script declarations: **193 passed, 30 subtests**.
- Final execution/property comparison, identity, current-result reuse, controllers,
  plugin worker loading and agreement: **167 passed, 55 subtests**.
- Real shell/QML/worker regression, existing media renderer test, viewer sessions,
  viewer controls and mutation effects: **58 passed, 22 subtests**. The real graph
  executes Tabular Input → Signal Plot → Media Panel, then proves title/frame/
  content-only, undo/redo, rotation/fit and table widths cause zero new dispatches,
  invalidations or node starts. Facts, outputs and elapsed times remain identical.
  Rendered title/frame properties change; a generated-plot title edit dispatches once.
- Registry replacement and SDK documentation: **33 passed**. Additional exact
  computational-interface checks (modifiers, Principal, exposure): **3 passed**.
- Fast integration ran once. `fast.pytest` initially reported **5,394 passed,
  4 skipped, 23 failure reports**. The new metadata required regenerating the
  canonical catalogue fixture, updating one unit-test host dependency, and
  registering the new isolated shell target in the existing ownership ledger.
  The **19-target focused recheck passed 18**; its remaining failure is the
  pre-existing registry port-count assertion below. No broad rerun was used.
- The remaining manifest-owned `fast.serial.pytest` phase was continued directly
  through `build_commands` / `run_command_summarized`: **220 passed**.
- Source Ruff, agent maps/index, traceability, Markdown links, and shell target
  ownership checks pass. Both independent reviewers closed their scopes without
  remaining correctness findings. All implementation was performed by the main agent.

The initial fast run had five unrelated baseline failure reports. The requested
follow-up resolved all five: current explicit fullscreen dependencies and lazy
Inspector bindings are asserted, catalogue counts are corrected, and the board
retry button declares its inherited general tooltip category. The exact four
test cases now pass with **66 subtests**. The missing-category allowance was not
expanded, and the full broad gate was not repeated merely to obtain a green summary.
The complete owning architecture, QML boundary, registry and tooltip-copy suites
then passed **172 tests and 1,380 subtests** before publication.

| Baseline check | Evidence |
| --- | --- |
| Fullscreen explicit-owner dependency AST expectation | Updated the exact dependency list to include the existing state callbacks/session ID. |
| Inspector node-link option bindings (two subtest failures) | Assertions now cover both cached content bindings and their bridge-owned refresh source. |
| Tooltip missing-category inventory | The board-preview retry button explicitly declares `general`; its inherited label tooltip is preserved. |
| Registry declared data-port count | Corrected declared/resolved counts to **440/445**, preserving the remaining catalogue invariants. |

The first four failure reports were reproduced by running their three test cases
with all tracked text inputs read from `git show adce5a49:<path>` (167 baseline
files, no checkout edits). The port-count mismatch was checked directly against
the same baseline's frozen catalogue. Detailed evidence is retained locally under
`artifacts/verification_logs/20260913_193545/`, including the two phase logs,
`baseline_static_checks.log`, and `baseline_catalog_counts.json`.

The default registry inventory contains 144 node types and 936 declared properties,
with exactly **40** presentation-only properties. The canonical shipped fixture
covers 147 rows, including add-on declarations. No unrelated production behavior,
existing dirty canvas snapshot, or concurrent planning work was changed. QML
acceptance ran offscreen; this is behavior/rendering proof, not a hardware performance claim.
