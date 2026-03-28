# GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT Work Packet Manifest

- Date: `2026-03-29`
- Integration base: `main`
- Published packet window: `P00` through `P03`
- Scope baseline: convert the global gap-break edge-crossing plan into an execution-ready packet set that adds one canvas-wide `edge_crossing_style` control with `none` and `gap_break`, keeps the default at `none`, applies gap rendering as a visual-only treatment, preserves existing edge interaction geometry and persistence semantics, and closes with verification, QA-matrix, and traceability evidence.
- Review baseline: [docs/PLAN_Global_Gap_Break_Edge_Crossing_Variant.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/PLAN_Global_Gap_Break_Edge_Crossing_Variant.md)

## Requirement Anchors

- [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- `docs/specs/requirements/10_ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`

## Retained Packet Order

1. `GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_P00_bootstrap.md`
2. `GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_P01_edge_crossing_preference_pipeline.md`
3. `GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_P02_gap_break_renderer_adoption.md`
4. `GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_P03_verification_docs_traceability_closeout.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/global-gap-break-edge-crossing-variant/p00-bootstrap` | Establish the packet docs, status ledger, spec-index registration, and git tracking for the new packet set |
| P01 Edge Crossing Preference Pipeline | `codex/global-gap-break-edge-crossing-variant/p01-edge-crossing-preference-pipeline` | Add the global preference, shell/QML plumbing, and graphics-settings control without changing renderer geometry |
| P02 Gap Break Renderer Adoption | `codex/global-gap-break-edge-crossing-variant/p02-gap-break-renderer-adoption` | Apply deterministic gap-break decoration inside `EdgeLayer.qml` while preserving hit testing, labels, and persistence semantics |
| P03 Verification Docs Traceability Closeout | `codex/global-gap-break-edge-crossing-variant/p03-verification-docs-traceability-closeout` | Publish QA evidence, requirement updates, and traceability closeout for the shipped variant |

## Locked Defaults

- `graphics.canvas.edge_crossing_style` is a canvas-global preference normalized to `none` or `gap_break`.
- Default behavior remains `none`.
- No per-edge override, no `.sfe` schema change, and no persistence payload expansion are allowed in this packet set.
- Gap breaks are render-only decoration. Edge hit testing, culling, routing, arrowheads, label anchors, and selection geometry continue to use the original path geometry.
- Crossing order is deterministic: previewed and selected edges render over non-previewed and non-selected edges; remaining ties resolve by existing visible edge payload order.
- Gap sizing is specified in screen space and translated through the current zoom/path sampling logic instead of mutating stored graph coordinates.
- Internal visible-edge snapshots may gain non-persistent crossing-break metadata for renderer and test use only.
- Crossing decoration must be disabled when the canvas is in `max_performance` mode or transient degraded rendering windows.
- When a later packet changes an earlier packet's proof surface, that later packet inherits and updates the earlier regression anchor inside its own write scope.

## Execution Waves

### Wave 1
- `P01`

### Wave 2
- `P02`

### Wave 3
- `P03`

## Retained Handoff Artifacts

- Spec contract: `GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_P00_bootstrap.md` through `GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_P03_verification_docs_traceability_closeout.md`
- Implementation prompts: matching `*_PROMPT.md` files for `P00` through `P03`
- Packet wrap-ups: `P00_bootstrap_WRAPUP.md` through `P03_verification_docs_traceability_closeout_WRAPUP.md`
- Final QA matrix: `docs/specs/perf/GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_QA_MATRIX.md`
- Status ledger: [GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/global_gap_break_edge_crossing_variant/GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_STATUS.md)

## Standard Thread Prompt Shell

`Implement GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_PXX_<name>.md exactly. Before editing, read GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_MANIFEST.md, GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_STATUS.md, and GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every retained `*_PROMPT.md` file in this packet set begins with that shell except for packet number and file substitutions.
