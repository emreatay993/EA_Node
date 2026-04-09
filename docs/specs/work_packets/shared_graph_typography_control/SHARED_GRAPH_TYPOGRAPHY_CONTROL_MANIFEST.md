# SHARED_GRAPH_TYPOGRAPHY_CONTROL Work Packet Manifest

- Date: `2026-04-09`
- Integration base: `main`
- Published packet window: `P00` through `P07`
- Scope baseline: convert [PLANS_TO_IMPLEMENT/in_progress/typography.md](../../../../PLANS_TO_IMPLEMENT/in_progress/typography.md) into an execution-ready, strictly sequential packet set that adds the persisted app-wide `graphics.typography.graph_label_pixel_size` preference; threads it through app-preference, shell, window, bridge, and graph-canvas bindings; derives shared graph chrome typography size and weight roles from one base token; updates standard graph chrome consumers while preserving passive-style font authority where it already exists; keeps geometry and scene-payload text metrics aligned with the new typography contract; adds the Graphics Settings `Theme` > `Typography` control; and closes with retained QA-matrix and traceability evidence.
- Review baseline: [PLANS_TO_IMPLEMENT/in_progress/typography.md](../../../../PLANS_TO_IMPLEMENT/in_progress/typography.md)

## Requirement Anchors

- [docs/specs/INDEX.md](../../INDEX.md)
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/work_packets/global_gap_break_edge_crossing_variant/GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_MANIFEST.md`
- `docs/specs/work_packets/persistent_node_elapsed_times/PERSISTENT_NODE_ELAPSED_TIMES_MANIFEST.md`

## Retained Packet Order

1. `SHARED_GRAPH_TYPOGRAPHY_CONTROL_P00_bootstrap.md`
2. `SHARED_GRAPH_TYPOGRAPHY_CONTROL_P01_preferences_typography_schema_normalization.md`
3. `SHARED_GRAPH_TYPOGRAPHY_CONTROL_P02_shell_typography_projection.md`
4. `SHARED_GRAPH_TYPOGRAPHY_CONTROL_P03_canvas_typography_contract_and_metrics.md`
5. `SHARED_GRAPH_TYPOGRAPHY_CONTROL_P04_standard_node_chrome_typography_adoption.md`
6. `SHARED_GRAPH_TYPOGRAPHY_CONTROL_P05_inline_and_edge_typography_adoption.md`
7. `SHARED_GRAPH_TYPOGRAPHY_CONTROL_P06_graphics_settings_typography_control.md`
8. `SHARED_GRAPH_TYPOGRAPHY_CONTROL_P07_verification_docs_traceability_closeout.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/shared-graph-typography-control/p00-bootstrap` | Establish the packet docs, status ledger, and spec-index registration for the shared graph typography control follow-up set |
| P01 Preferences Typography Schema Normalization | `codex/shared-graph-typography-control/p01-preferences-typography-schema-normalization` | Add the `graphics.typography.graph_label_pixel_size` default and normalization contract without widening into shell, QML, or dialog work |
| P02 Shell Typography Projection | `codex/shared-graph-typography-control/p02-shell-typography-projection` | Project the normalized typography base size through workspace state, presenter snapshots, `ShellWindow`, and the graph-canvas bridge-owned property seam |
| P03 Canvas Typography Contract and Metrics | `codex/shared-graph-typography-control/p03-canvas-typography-contract-and-metrics` | Expose the canvas-facing `graphLabelPixelSize` binding, define the shared graph typography role contract, and align geometry/payload text metrics before chrome consumers adopt it |
| P04 Standard Node Chrome Typography Adoption | `codex/shared-graph-typography-control/p04-standard-node-chrome-typography-adoption` | Move standard node headers, ports, and elapsed footer typography onto the shared role contract while preserving passive-authoritative font paths |
| P05 Inline and Edge Typography Adoption | `codex/shared-graph-typography-control/p05-inline-and-edge-typography-adoption` | Move inline property labels, status chips, and flow-edge labels/pills onto the shared role contract and inherit any earlier typography regression anchors that change |
| P06 Graphics Settings Typography Control | `codex/shared-graph-typography-control/p06-graphics-settings-typography-control` | Add the user-facing Graphics Settings `Theme` > `Typography` control and prove end-user preference round-trip on the retained shell/dialog seam |
| P07 Verification Docs Traceability Closeout | `codex/shared-graph-typography-control/p07-verification-docs-traceability-closeout` | Publish retained QA evidence, requirement updates, and traceability closeout for the shipped shared graph typography control |

## Locked Defaults

- `graphics.typography.graph_label_pixel_size` is an app-global graphics preference normalized to an integer in the inclusive `8..18` range with default `10`.
- This packet set adds one shared base-size token only. It does not add a font-family picker, per-theme typography schema, per-node typography persistence, or `.sfe` payload changes.
- The Python-side graphics-preference pipeline remains the source of truth. Later packets project one normalized base size into QML, and QML derives role sizes from that bound base value instead of keeping independent hardcoded literals.
- The retained derived role hierarchy from `typography.md` is authoritative unless a packet explicitly documents a compatibility-safe refinement:
  - standard node title: `base + 2`
  - port labels: `base`
  - elapsed footer: `base`
  - inline property labels: `base`
  - badge text: `max(9, base - 1)`
  - flow edge label text: `base + 1`
  - flow edge pill text: `base + 2`
  - exec arrow port label: `base + 8`
- The shared typography source must centralize role font weights as well as role pixel sizes for graph chrome that still hardcodes boldness or weight today. Initial shared weights must preserve the current visual hierarchy instead of leaving bold, demi-bold, or heavy choices scattered across consumers.
- Existing passive `visual_style.font_size` and `visual_style.font_weight` paths remain authoritative where they already control passive title/body text. The global token must not replace those packet-external overrides.
- Geometry and payload-width estimation must stay aligned with the shared typography contract. If a packet changes text pixel sizes that affect standard node or edge layout expectations, that packet must update the relevant deterministic metrics instead of leaving stale width math behind.
- Typography updates must reuse existing graph-canvas payload refresh or revision seams. Do not introduce a second typography-only scene invalidation channel.
- The graph typography adoption scope is limited to the surfaces named in [PLANS_TO_IMPLEMENT/in_progress/typography.md](../../../../PLANS_TO_IMPLEMENT/in_progress/typography.md): `GraphNodeHeaderLayer.qml`, `GraphNodePortsLayer.qml`, `GraphInlinePropertiesLayer.qml`, `GraphNodeHost.qml`, and `EdgeFlowLabelLayer.qml`.
- The persistent elapsed footer surface retained from [PLANS_TO_IMPLEMENT/completed/Persistent_Node_Elapsed_Times.md](../../../../PLANS_TO_IMPLEMENT/completed/Persistent_Node_Elapsed_Times.md) remains in scope as a dependent consumer only; this packet set must not reopen the timing-cache, invalidation, or worker-event contracts owned by `PERSISTENT_NODE_ELAPSED_TIMES`.
- Later packets run strictly sequentially; no non-bootstrap packet shares a wave.
- When a later packet changes a seam already asserted by an earlier typography packet's test, that later packet inherits and updates the earlier test file inside its own write scope.

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

## Retained Handoff Artifacts

- Review baseline: `PLANS_TO_IMPLEMENT/in_progress/typography.md`
- Planning precedent: `PLANS_TO_IMPLEMENT/completed/Persistent_Node_Elapsed_Times.md`
- Spec contract: `SHARED_GRAPH_TYPOGRAPHY_CONTROL_P00_bootstrap.md` through `SHARED_GRAPH_TYPOGRAPHY_CONTROL_P07_verification_docs_traceability_closeout.md`
- Implementation prompts: matching `*_PROMPT.md` files for `P00` through `P07`
- Packet wrap-ups: `P00_bootstrap_WRAPUP.md` through `P07_verification_docs_traceability_closeout_WRAPUP.md`
- Final QA matrix: `docs/specs/perf/SHARED_GRAPH_TYPOGRAPHY_CONTROL_QA_MATRIX.md`
- Status ledger: [SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md](./SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md)

## Standard Thread Prompt Shell

`Implement SHARED_GRAPH_TYPOGRAPHY_CONTROL_PXX_<name>.md exactly. Before editing, read SHARED_GRAPH_TYPOGRAPHY_CONTROL_MANIFEST.md, SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md, and SHARED_GRAPH_TYPOGRAPHY_CONTROL_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update SHARED_GRAPH_TYPOGRAPHY_CONTROL_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every retained `*_PROMPT.md` file in this packet set begins with that shell except for packet number, slug, and packet-local substitutions.
