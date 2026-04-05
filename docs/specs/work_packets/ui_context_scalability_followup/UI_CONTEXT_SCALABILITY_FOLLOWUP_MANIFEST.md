# UI_CONTEXT_SCALABILITY_FOLLOWUP Work Packet Manifest

- Date: `2026-04-05`
- Integration base: `main`
- Published packet window: `P00` through `P09`
- Scope baseline: convert the 2026-04-05 UI context follow-up review into an execution-ready, sequential refactor program that packetizes the remaining oversized shell helper, graph geometry, graph-scene mutation, and UI regression-suite umbrellas; extends machine-enforced context budgets to those hotspots; and updates the canonical UI packet docs so future UI work names both a source owner and a regression owner without regressing shipped user workflows, `.sfe` persistence semantics, node type IDs, viewer-family behavior, or the stable top-level regression entrypoints already used by the repo.
- Review baseline: [docs/UI_CONTEXT_SCALABILITY_FOLLOWUP_REVIEW_2026-04-05.md](../../../UI_CONTEXT_SCALABILITY_FOLLOWUP_REVIEW_2026-04-05.md)

## Requirement Anchors

- [docs/specs/INDEX.md](../../INDEX.md)
- `docs/specs/requirements/10_ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/50_EXECUTION_ENGINE.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/UI_CONTEXT_SCALABILITY_REFACTOR_MANIFEST.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/SUBSYSTEM_PACKET_INDEX.md`
- `docs/specs/work_packets/ui_context_scalability_refactor/FEATURE_PACKET_TEMPLATE.md`

## Retained Packet Order

1. `UI_CONTEXT_SCALABILITY_FOLLOWUP_P00_bootstrap.md`
2. `UI_CONTEXT_SCALABILITY_FOLLOWUP_P01_guardrail_catalog_expansion.md`
3. `UI_CONTEXT_SCALABILITY_FOLLOWUP_P02_shell_session_surface_split.md`
4. `UI_CONTEXT_SCALABILITY_FOLLOWUP_P03_graph_geometry_facade_split.md`
5. `UI_CONTEXT_SCALABILITY_FOLLOWUP_P04_graph_scene_mutation_packet_split.md`
6. `UI_CONTEXT_SCALABILITY_FOLLOWUP_P05_main_window_bridge_test_packetization.md`
7. `UI_CONTEXT_SCALABILITY_FOLLOWUP_P06_graph_surface_test_packetization.md`
8. `UI_CONTEXT_SCALABILITY_FOLLOWUP_P07_track_b_test_packetization.md`
9. `UI_CONTEXT_SCALABILITY_FOLLOWUP_P08_canonical_ui_test_packet_docs.md`
10. `UI_CONTEXT_SCALABILITY_FOLLOWUP_P09_verification_docs_closeout.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/ui-context-scalability-followup/p00-bootstrap` | Establish the review baseline, packet docs, status ledger, spec-index registration, and git tracking for the follow-up packet set |
| P01 Guardrail Catalog Expansion | `codex/ui-context-scalability-followup/p01-guardrail-catalog-expansion` | Extend the existing UI context budget catalog to the remaining large source and regression hotspots and wire the check into the normal fast verification path |
| P02 Shell Session Surface Split | `codex/ui-context-scalability-followup/p02-shell-session-surface-split` | Split the remaining shell helper and project-session service umbrellas into curated support packages while keeping the legacy entry files as thin facades |
| P03 Graph Geometry Facade Split | `codex/ui-context-scalability-followup/p03-graph-geometry-facade-split` | Split graph surface metrics and edge routing into focused geometry modules behind stable facade files |
| P04 Graph Scene Mutation Packet Split | `codex/ui-context-scalability-followup/p04-graph-scene-mutation-packet-split` | Split graph-scene mutation history into focused policy and operation modules while keeping the legacy mutation-history entry surface stable |
| P05 Main Window Bridge Test Packetization | `codex/ui-context-scalability-followup/p05-main-window-bridge-test-packetization` | Break the main-window bridge regression umbrella into focused bridge suites plus shared support while keeping the top-level regression entrypoint stable |
| P06 Graph Surface Test Packetization | `codex/ui-context-scalability-followup/p06-graph-surface-test-packetization` | Break the graph-surface host and input-contract umbrellas into focused regression suites plus shared support while keeping the top-level regression entrypoints stable |
| P07 Track-B Test Packetization | `codex/ui-context-scalability-followup/p07-track-b-test-packetization` | Break the Track-B QML preference and scene-model umbrellas into focused suites plus shared support while keeping the top-level regression entrypoints stable |
| P08 Canonical UI Test Packet Docs | `codex/ui-context-scalability-followup/p08-canonical-ui-test-packet-docs` | Update the canonical UI packet docs so future work names both a source subsystem owner and a regression owner, and ratchet follow-up guardrail caps to their steady-state thresholds |
| P09 Verification Docs Closeout | `codex/ui-context-scalability-followup/p09-verification-docs-closeout` | Publish QA evidence, register the follow-up packet set, and align traceability and verification docs with the expanded guardrails and packet contracts |

## Locked Defaults

- This packet set is a cleanup and maintainability refactor program, not a feature-expansion program.
- Preserve shipped user-visible behavior, `.sfe` persistence semantics, node type IDs, viewer-family behavior, and the existing top-level regression commands used by the repo.
- Later packets run strictly sequentially; no non-bootstrap packet shares a wave.
- The canonical home for UI packet contracts and context-budget rules remains `docs/specs/work_packets/ui_context_scalability_refactor/`; follow-up docs extend that home rather than creating a competing canonical packet-doc tree.
- The remaining oversized top-level source files end as thin facades or curated import surfaces, not deleted entrypoints.
- The remaining oversized top-level regression files end as thin aggregators or curated regression entry surfaces, not deleted regression entrypoints.
- `scripts/check_context_budgets.py` and `docs/specs/work_packets/ui_context_scalability_refactor/CONTEXT_BUDGET_RULES.json` remain the single machine-enforced source of truth for UI context budgets.
- After `P01`, the context-budget check is part of the normal fast verification entry path rather than a one-off manual command.
- After `P02`, `window_state_helpers.py` and `project_session_services.py` stay import-compatible but are no longer omnibus implementation buckets.
- After `P03`, `graph_surface_metrics.py` and `edge_routing.py` stay import-compatible but are no longer omnibus implementation buckets.
- After `P04`, `graph_scene_mutation_history.py` stays import-compatible but is no longer the omnibus mutation implementation bucket.
- After `P05`, `tests/main_window_shell/bridge_contracts.py` remains the stable regression entrypoint, but focused bridge suites and shared support own the detailed cases.
- After `P06`, `tests/test_passive_graph_surface_host.py` and `tests/test_graph_surface_input_contract.py` remain stable regression entrypoints, but focused suites and shared support own the detailed cases.
- After `P07`, `tests/graph_track_b/qml_preference_bindings.py` and `tests/graph_track_b/scene_and_model.py` remain stable regression entrypoints, but focused suites and shared support own the detailed cases.
- After `P08`, future UI feature packets must name both an owning source subsystem packet and an owning regression packet before expanding a seam.
- When a later packet changes an earlier packet's asserted seam, the later packet inherits and updates that earlier regression anchor inside its own write scope.

## Execution Waves

### Wave 1
- `P01`

### Wave 2
- `P02`

### Wave 3
- `P03`

### Wave 4
- `P04`

### Wave 5
- `P05`

### Wave 6
- `P06`

### Wave 7
- `P07`

### Wave 8
- `P08`

### Wave 9
- `P09`

## Retained Handoff Artifacts

- Review baseline: `docs/UI_CONTEXT_SCALABILITY_FOLLOWUP_REVIEW_2026-04-05.md`
- Spec contract: `UI_CONTEXT_SCALABILITY_FOLLOWUP_P00_bootstrap.md` through `UI_CONTEXT_SCALABILITY_FOLLOWUP_P09_verification_docs_closeout.md`
- Implementation prompts: matching `*_PROMPT.md` files for `P00` through `P09`
- Packet wrap-ups: `P01_guardrail_catalog_expansion_WRAPUP.md` through `P09_verification_docs_closeout_WRAPUP.md`
- Final QA matrix: `docs/specs/perf/UI_CONTEXT_SCALABILITY_FOLLOWUP_QA_MATRIX.md`
- Status ledger: [UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md](./UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md)

## Standard Thread Prompt Shell

`Implement UI_CONTEXT_SCALABILITY_FOLLOWUP_PXX_<name>.md exactly. Before editing, read UI_CONTEXT_SCALABILITY_FOLLOWUP_MANIFEST.md, UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md, and UI_CONTEXT_SCALABILITY_FOLLOWUP_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every retained `*_PROMPT.md` file in this packet set begins with that shell except for packet number, slug, and packet-local substitutions.
