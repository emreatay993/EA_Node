# Python Script authoring workspace

Approved implementation baseline: `2df4ed4d25dfbda1ce2bf426598d7d2b9fd6bb37`.

Status: **IMPLEMENTATION COMPLETE AND INDEPENDENTLY REVIEWED**. Integration
exceptions are recorded in the final outcome below; the original broad run is
not claimed green.

## Requirements

- Shared builder, Python editor, and non-executing live node preview for docked and fullscreen editing. Resizable panes; side tabs below 1200 logical pixels and Interface/Code/Preview tabs below 800.
- All ten existing controls plus inputs/outputs, searchable Add, configuration, duplicate/remove/order/sections, advanced options, and short new-script template. Existing source is preserved.
- Explicit user follow-up: provide Add -> Section (name + selection of one or more inputs/controls), visible expandable/collapsible section headers, section assignment/rename/move-out. Section rename/assignment across members is one draft undo operation using existing `section=` decorators. Outputs stay top-level; empty sections are not persisted and the dialog requires at least one eligible member. Preserve authored member order and use actual shared node group collapse behavior.
- Latest live-app bug report: unsectioned decorator controls have excessive vertical spacing compared with built-in grouped controls; turning a control port off moves its UI above the main ports. Fix production shared layout (canvas and preview), with compact controls below main ports regardless of socket option. Also respect explicit blank control labels shown as hidden by the builder.
- One registered-type picker/completion catalog with names, aliases, IDs, descriptions, families, examples and curated synonyms. Explicit type selection for new ports; type and Item/List/Tree remain separate. Controls expose derived types and restricted List item types.
- Source-authoritative editing preserving unrelated bytes; automatic decorator/parameter updates for builder actions; explicit parameter synchronization for typed edits; 300 ms analysis; bidirectional item/source selection and actionable diagnostics.
- Guided, previewed scope-aware variable rename with collision/dynamic-lookup guards. Static returned-dictionary output-key rename only. Preserve saved values and compatible connections through explicit rename intent; never infer manual-source renames.
- Temporary preview interaction, Use as default, distinction between decorator defaults and saved values, immediate Updating/unavailable state, no user-code execution or graph mutation in preview.
- Per-operation editor undo, per-Apply graph undo, session drafts on retarget/reopen, latest-applied Revert, existing automatic/explicit-run rules, and revision-checked Apply impact preparation.
- No decorator API/project-format change, no full IDE, arbitrary custom widgets, test runs, or unrelated Plot redesign.
- Latest user refinement: both initial screenshots and rounded polish were rejected (bland, button-heavy, missing icons, pill-heavy/web-like, not Qt-like). Final acceptance requires a desktop IDE/property-editor idiom: compact real SVG icon toolbars with separators/tooltips, tree/object-inspector outline with distinct kind icons, flat pane headers/thin borders/conventional tabs, compact label-left/editor-right property rows and restrained titled groups, corners 0-3px. No letter badges, repeated rounded cards/pills or oversized text-button strips. Blue is reserved mainly for selection and primary action. Keep readable hierarchy, friendly types, unclipped preview, themed controls and clear errors. Root must inspect an early representative desktop-styled render before final multi-size captures. Normal valid form commits reach draft/preview; pending fields must be flushed or block Apply and explicit Run, never silently ignored/discarded by other actions.

## Ownership constraints

- Nodes own bounded declaration analysis and source editing; UI owns authoring/type-choice presentation.
- `graph/node_port_state.py` remains a pure projection. Reuse `reconcile_script_port_state`; preserve distinct Apply and registry-load policies.
- `ValidatedGraphMutation` owns candidate-first preparation/Apply and explicit rename remapping. Generic dynamic-key rename still prunes wires. Preserve shared commit helpers and pruning order.
- Remap detached old keys, saved properties, port state, forwarding references and edge endpoints before comparison; preserve edge identity/metadata/order. Validate before any write.
- Graph kernel/type resolver remains compatibility authority. Only data-access changes force compatible-wire removal. Preparation is guarded by source/workspace/registry revisions.
- Editor model/controller owns session drafts; shared graph presentation/QML owns preview appearance. App preferences stay outside project persistence.

## Execution and progress

One active writer; coordinator alone updates this table. Review substantial chunks independently before acceptance.

| Task | Owner | Status / evidence | Next action |
| --- | --- | --- | --- |
| T01 Analysis and type guidance | authoring_core / review_authoring | ACCEPTED; 95 focused tests, final snapshot review and two cleanup repros passed | Consume finalized APIs in editor/UI |
| T02 Source edits and rename | authoring_core / review_authoring | ACCEPTED with T01; source/rename review and diff check passed | Consume explicit GuidedRename records in editor |
| T03 Graph preparation and Apply | graph_apply / review_graph | ACCEPTED; 44 reconciliation/normalization tests and final independent review passed; source hash 924DEAAF6290 | Consume prepare/apply API; preserve name-reuse identities |
| T04 Draft and history integration | editor_session / review_editor | ACCEPTED; 34 focused and four retained shell tests, final review passed; model hash 31A88CC9F738 | UI consumes finalized APIs and preview attachment hooks |
| T05 Builder and assistance UI | authoring_ui / review_ui | ACCEPTED; 58 focused +2 fullscreen +2 tooltip hygiene; six layout/three dialog checks at200%DPI; final compact-widget review and real list input regression passed | Final integration only |
| T06 Preview | authoring_ui / review_ui | ACCEPTED; renderer/isolation/lifecycle/real dropdown verified; wide/medium/narrowdesktop direction visually accepted | Complete |
| T06b Script control surface parity | script_surface_layout / review_surface | ACCEPTED; source/scene/registry108+78subtests, catalog/editor23, shared controls/graph106+2subtests, preview5, QuickTest40; independent all10controls4fontsizes parity passed | Final integration only |
| T07 Integration and documentation | coordinator / integration_fixes / review_integration_fixes | COMPLETE; task-connected integration fixes independently accepted, affected70+336subtests and host40 pass; serial220 pass; guide/spec/maps/index updated | Retain documented integration exceptions |

## Verification

Use project `venv/Scripts/python.exe`. Run narrow proving checks first and owning suites once at the group boundary.

- Parser: `tests/test_python_script_declaration.py`; new focused authoring/completion tests.
- Apply/dynamic state: `tests/test_graph_node_reconciliation.py`; reuse `tests/graph_mutation_fixtures.py`.
- Load policy/memo: `tests/test_graph_registry_normalization.py`.
- Scene/history/payload: `tests/test_python_script_scene_integration.py`.
- Serialization/fragments: `tests/test_python_script_persistence.py`.
- Editor: `tests/test_script_editor_dock.py`, fullscreen bridge targets, focused QML component tests.
- Accept typed input/slider/dropdown/output creation, grouping, preview, used-variable rename, Apply and Undo/Redo. Prove preservation of wires/values/exposure/labels/modifiers/Principal, generic-rename pruning, no-op invalid/stale drafts, no execution in preview, add-on type refresh, keyboard and light/dark/narrow/high-DPI behavior.
- Final cross-layer closeout: summarized `fast` lane, focused QML interactions, agent maps, Markdown links and traceability. Update route index if citations change.
- Existing Plot refactor timing/canvas limitations are baseline evidence only; do not restart its benchmark campaign.

## Final outcome

Recorded 2026-09-20.

All requested features and follow-ups are implemented: desktop-style authoring,
all controls, type guidance/completion, guarded rename, sections, shared drafts
and native fields, isolated preview, and compact socket-independent control
layout. The short starter changes only instructional comments: its executable
AST is identical to the previous pass-through script. Existing project source
is not rewritten.

- Every substantial implementation group received independent review; review
  findings were fixed and rechecked. Focused evidence is recorded in the table.
- Initial `fast.pytest`: **5,986 passed, 26 failed, 4 skipped**. Full log:
  `artifacts/verification_logs/20260920_004446/01_fast.pytest.log`.
- All **22 task-connected failures** were corrected and passed focused
  retesting. Corrections preserve the ordinary Apply single-clone budget and
  explicit composition-to-preview theme boundary; stale test doubles and
  inventory/starter/Help expectations were updated to the actual contracts.
  Final affected cohort: **70 passed plus 336 subtests**; shared node host:
  **40 QuickTest cases passed**.
- The previously unrun exact `fast.serial.pytest` command passed **220 tests**
  in 80.23 seconds. Log: `artifacts/python_script_authoring/final_fast_serial.log`.
- Two canvas failures remain pre-existing: viewer demotion and default canvas
  export crop. Their exact assertions match both retained baseline and
  candidate XML under `artifacts/plot_graph_refactor/t05/`.
- Two external viewer-lifecycle tests failed in the parallel run but passed
  isolated retesting (**2 passed**, 19.36 seconds); the identity probe also
  returned valid JSON. The parallel failure cause is not established.
- All five required documentation/verification hygiene modules passed in the
  initial broad phase. No duplicate hygiene run or benchmark campaign was
  started. The parallel phase was not rerun; its original failure status is
  retained rather than presented as an all-green result.
- Final Ruff, agent-map, traceability, Markdown-link and whitespace checks
  passed. Three final render cases refreshed the wide workspace and both
  unsectioned socket states after the theme/layout integration fixes.
- Rendered interaction checks cover both themes, wide/medium/narrow layouts,
  dialogs and 200% DPI. Artifact captures under
  `artifacts/python_script_authoring/` include the final desktop workspace and
  `unsectioned_controls_port_false.png` / `unsectioned_controls_port_true.png`.
  These are offscreen Qt checks, not display-attached performance qualification.
- Scope limits remain deliberate: no full Python IDE or test-run environment;
  dynamic introspection/output construction can require manual rename, and
  completion directly after inline comments is limited.

The user authorized committing this task to `main` and pushing on 2026-09-20.
Unrelated initial changes remain outside this task's publication scope.

## Protected baseline work

Pre-existing modified `AGENTS.md` and `docs/specs/INDEX.md`, untracked `docs/PLAN_COREX_Physical_Simulation_Backend.md` and `scripts/Strain_Gage_Positioning/modular_version/strain_candidate_points.csv`. Preserve all; any index addition must retain its existing changes.

Publication is limited to this task's changes on `main`. No packet files are required.

## Integration contracts

- T01/T02: `analyze_source(source)` and `edit_source(source, operation, key=..., kind=..., fields=..., remove_fields=..., index=..., new_key=...)`; operations add/update/duplicate/remove/move/rename/synchronize_parameters. Result carries source, selected key, changes and explicit `GuidedRename(old_key,new_key,kind)`. Ranges use Python characters; editor converts UTF-16. UI support exposes decorator_choices/field_choices/type_choices/completions. Completion after an inline comment is a minor known limitation.
- T03: `prepare_python_script(node_id, source, renamed_keys=..., source_revision=...)` returns detached preparation; `apply_python_script` accepts the same plus `prepared`, checks revisions, then prepares afresh. Compound remove/rename and rename/add name reuse are supported by explicit identities.
- T04 UI surface: interface_items/selected_key/selected_item, diagnostics/analysis_status/operation_error, can_synchronize/can_undo/can_redo, rename_review/apply_impact, preview_bridge; perform_edit/preview_rename/confirm_rename, select_item/select_source_position/select_diagnostic, fields_for/query_decorators/query_types/query_completions/accept_completion, undo/redo/prepare_apply/apply/revert. Neutral selection_range_requested signal must not steal builder/preview focus.
- T05/T06 use shared editor QML/native forms and an isolated GraphNodeHost preview through a narrow payload builder entry. Theme references are explicitly injected through docked/fullscreen composition into both the preview facade and node host. T07 updates the short default source, its matching catalog fixture, guide/maps/index and verification records.
- Confirmed Qt bridge issue: QJSEngine maps both `1` and `1.0` to Python int. Numeric form UI must retain explicit Whole/Decimal intent at the Python boundary, update only changed fields, and test real QML-to-Python round-trip. Fractional values must not be silently truncated for Whole mode.
- Accepted desktop-style captures replace the initial prototypes under ignored `artifacts/python_script_authoring/authoring_{light,dark}_{1600,1000,650}.png`, with narrow interface/preview and dialog variants. The coordinator inspected representative wide/medium/narrow light/dark renders; 200% DPI checks also passed.
- Icon probes independently matched regular light/dark screenshot crops to the production provider (0/324 pixel differences). No rendering workaround was added; the UI test checks visible icon pixels as well as source readiness.
- Native pending form buffers belong to the shared model across dock/fullscreen and project/workspace/node contexts; only the active owner flushes. `has_unapplied_edits` includes current pending forms for explicit Run and dynamic-port guards, while automatic runs still use applied source.
- T06b replaces the old unsectioned port-grid spans (switch36/slider72/dropdown72) with exact shared settings rows26/66/56. `SettingsGroupSpec.show_header` defaults true; Python Script resolves unsectioned controls into the collision-safe `script.controls` headerless, always-expanded group. Named groups and other nodes retain existing behavior. Explicit empty labels remain empty, and twenty catalog groups record the new default flag.
