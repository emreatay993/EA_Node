# UI_CONTEXT_SCALABILITY_REFACTOR Work Packet Manifest

- Date: `2026-04-04`
- Integration base: `main`
- Published packet window: `P00` through `P09`
- Scope baseline: convert the 2026-04-04 UI context scalability review into an execution-ready, sequential refactor program that shrinks shell and graph umbrella files, packetizes graph-scene, canvas, edge-rendering, and viewer-specific UI seams, and adds machine-enforced context budgets plus subsystem packet contracts without regressing shipped user workflows, `.sfe` persistence semantics, node type IDs, or the documented viewer-family behavior.
- Review baseline: [docs/UI_CONTEXT_SCALABILITY_REVIEW_2026-04-04.md](../../../UI_CONTEXT_SCALABILITY_REVIEW_2026-04-04.md)

## Requirement Anchors

- [docs/specs/INDEX.md](../../INDEX.md)
- `docs/specs/requirements/10_ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/50_EXECUTION_ENGINE.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`

## Retained Packet Order

1. `UI_CONTEXT_SCALABILITY_REFACTOR_P00_bootstrap.md`
2. `UI_CONTEXT_SCALABILITY_REFACTOR_P01_shell_window_facade_collapse.md`
3. `UI_CONTEXT_SCALABILITY_REFACTOR_P02_presenter_family_split.md`
4. `UI_CONTEXT_SCALABILITY_REFACTOR_P03_graph_scene_bridge_packet_split.md`
5. `UI_CONTEXT_SCALABILITY_REFACTOR_P04_graph_canvas_root_packetization.md`
6. `UI_CONTEXT_SCALABILITY_REFACTOR_P05_edge_renderer_packet_split.md`
7. `UI_CONTEXT_SCALABILITY_REFACTOR_P06_viewer_surface_isolation.md`
8. `UI_CONTEXT_SCALABILITY_REFACTOR_P07_context_budget_guardrails.md`
9. `UI_CONTEXT_SCALABILITY_REFACTOR_P08_subsystem_packet_docs.md`
10. `UI_CONTEXT_SCALABILITY_REFACTOR_P09_verification_docs_closeout.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/ui-context-scalability-refactor/p00-bootstrap` | Establish the review baseline, packet docs, status ledger, spec-index registration, and git tracking for the new packet set |
| P01 Shell Window Facade Collapse | `codex/ui-context-scalability-refactor/p01-shell-window-facade-collapse` | Reduce `ShellWindow` to lifecycle, Qt ownership, and final wiring while moving packet-owned helper logic out of `window.py` |
| P02 Presenter Family Split | `codex/ui-context-scalability-refactor/p02-presenter-family-split` | Replace the monolithic presenter module with one presenter per file behind a curated import surface |
| P03 Graph Scene Bridge Packet Split | `codex/ui-context-scalability-refactor/p03-graph-scene-bridge-packet-split` | Move graph-scene support logic into a focused package and leave `graph_scene_bridge.py` as a thin composition surface |
| P04 Graph Canvas Root Packetization | `codex/ui-context-scalability-refactor/p04-graph-canvas-root-packetization` | Reduce `GraphCanvas.qml` to composition and stable root contract while moving root-local wiring into helper components |
| P05 Edge Renderer Packet Split | `codex/ui-context-scalability-refactor/p05-edge-renderer-packet-split` | Split `EdgeLayer.qml` into focused rendering, label, cache, and hit-test helpers without changing edge UX |
| P06 Viewer Surface Isolation | `codex/ui-context-scalability-refactor/p06-viewer-surface-isolation` | Isolate viewer-specific UI and projection seams so ordinary graph editing does not depend on viewer-session internals |
| P07 Context Budget Guardrails | `codex/ui-context-scalability-refactor/p07-context-budget-guardrails` | Add machine-enforced file-size and ownership guardrails for the packet-owned UI hotspots |
| P08 Subsystem Packet Docs | `codex/ui-context-scalability-refactor/p08-subsystem-packet-docs` | Publish reusable subsystem packet contracts and a feature-packet template for future UI work |
| P09 Verification Docs Closeout | `codex/ui-context-scalability-refactor/p09-verification-docs-closeout` | Publish QA evidence, register the packet set closeout, and align verification or traceability docs with the new guardrails |

## Locked Defaults

- This packet set is a cleanup and refactor program, not a feature-expansion program.
- Preserve shipped user-facing behavior, `.sfe` persistence semantics, node type IDs, and documented viewer-family behavior.
- Later packets run strictly sequentially; no non-bootstrap packet shares a wave.
- After `P01`, `window.py` is lifecycle-first and Qt-first, not a packet-owned workflow bucket.
- After `P02`, `ea_node_editor.ui.shell.presenters` is a curated package surface with one presenter per file; no new omnibus presenter file is allowed.
- After `P03`, `graph_scene_bridge.py` is a thin export or composition surface; state support lives under a focused `graph_scene` package.
- After `P04`, `GraphCanvas.qml` owns only composition plus the documented stable root contract methods.
- After `P05`, `EdgeLayer.qml` owns only composition plus packet-owned surface contract glue; rendering, label, cache, and hit testing live in focused helpers.
- After `P06`, viewer-specific bridge or surface state is isolated from ordinary graph-editing packets.
- After `P07`, packet-owned UI hotspots are guarded by machine-checked context budgets instead of prose-only guidance.
- After `P08`, future UI features must name an owning subsystem packet and reuse the packet contract docs before expanding cross-cutting seams.
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

- Review baseline: `docs/UI_CONTEXT_SCALABILITY_REVIEW_2026-04-04.md`
- Spec contract: `UI_CONTEXT_SCALABILITY_REFACTOR_P00_bootstrap.md` through `UI_CONTEXT_SCALABILITY_REFACTOR_P09_verification_docs_closeout.md`
- Implementation prompts: matching `*_PROMPT.md` files for `P00` through `P09`
- Packet wrap-ups: `P01_shell_window_facade_collapse_WRAPUP.md` through `P09_verification_docs_closeout_WRAPUP.md`
- Final QA matrix: `docs/specs/perf/UI_CONTEXT_SCALABILITY_REFACTOR_QA_MATRIX.md`
- Status ledger: [UI_CONTEXT_SCALABILITY_REFACTOR_STATUS.md](./UI_CONTEXT_SCALABILITY_REFACTOR_STATUS.md)

## Standard Thread Prompt Shell

`Implement UI_CONTEXT_SCALABILITY_REFACTOR_PXX_<name>.md exactly. Before editing, read UI_CONTEXT_SCALABILITY_REFACTOR_MANIFEST.md, UI_CONTEXT_SCALABILITY_REFACTOR_STATUS.md, and UI_CONTEXT_SCALABILITY_REFACTOR_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update UI_CONTEXT_SCALABILITY_REFACTOR_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every retained `*_PROMPT.md` file in this packet set begins with that shell except for packet number and file substitutions.
