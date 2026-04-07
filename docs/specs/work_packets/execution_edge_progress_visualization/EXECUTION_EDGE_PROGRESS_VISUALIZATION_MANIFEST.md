# EXECUTION_EDGE_PROGRESS_VISUALIZATION Work Packet Manifest

- Date: `2026-04-07`
- Integration base: `main`
- Published packet window: `P00` through `P05`
- Scope baseline: convert the `Execution_Edge_Progress_Visualization.md` follow-up plan into an execution-ready, strictly sequential packet set that extends the shipped node execution visualization from node chrome to authored control edges; keeps edge progress state run-scoped, active-workspace-filtered, and in-memory only; reuses the existing node execution signal/revision path; introduces `node_failed_handled` for handled failure continuations; and closes by updating the retained `NODE_EXECUTION_VISUALIZATION` QA matrix and traceability docs instead of creating a competing QA home.
- Review baseline: [PLANS_TO_IMPLEMENT/in_progress/Execution_Edge_Progress_Visualization.md](../../../../PLANS_TO_IMPLEMENT/in_progress/Execution_Edge_Progress_Visualization.md)

## Requirement Anchors

- [docs/specs/INDEX.md](../../INDEX.md)
- `docs/specs/requirements/10_ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`
- `docs/specs/requirements/50_EXECUTION_ENGINE.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/work_packets/node_execution_visualization/NODE_EXECUTION_VISUALIZATION_MANIFEST.md`
- `docs/specs/perf/NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md`

## Retained Packet Order

1. `EXECUTION_EDGE_PROGRESS_VISUALIZATION_P00_bootstrap.md`
2. `EXECUTION_EDGE_PROGRESS_VISUALIZATION_P01_run_state_edge_progress_projection.md`
3. `EXECUTION_EDGE_PROGRESS_VISUALIZATION_P02_graph_canvas_execution_edge_bindings.md`
4. `EXECUTION_EDGE_PROGRESS_VISUALIZATION_P03_execution_edge_snapshot_metadata.md`
5. `EXECUTION_EDGE_PROGRESS_VISUALIZATION_P04_execution_edge_renderer_highlights.md`
6. `EXECUTION_EDGE_PROGRESS_VISUALIZATION_P05_verification_docs_traceability_closeout.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/execution-edge-progress-visualization/p00-bootstrap` | Establish the packet docs, status ledger, spec-index registration, and git tracking for the follow-up packet set |
| P01 Run State Edge Progress Projection | `codex/execution-edge-progress-visualization/p01-run-state-edge-progress-projection` | Add the handled-failure worker event plus run-scoped authored execution-edge progress projection on the shell/controller path without touching QML edge visuals yet |
| P02 Graph Canvas Execution Edge Bindings | `codex/execution-edge-progress-visualization/p02-graph-canvas-execution-edge-bindings` | Expose progressed execution edge lookups through the bridge-first GraphCanvas contract while preserving the existing node execution revision path |
| P03 Execution Edge Snapshot Metadata | `codex/execution-edge-progress-visualization/p03-execution-edge-snapshot-metadata` | Convert bridge-level progressed edge lookups into packet-owned control-edge snapshot metadata and one-shot flash state bookkeeping without changing paint output yet |
| P04 Execution Edge Renderer Highlights | `codex/execution-edge-progress-visualization/p04-execution-edge-renderer-highlights` | Render dim-before-progress control edges plus the one-shot flash overlay on top of the packet-owned snapshot contract and prove the end-user shell/QML behavior |
| P05 Verification Docs Traceability Closeout | `codex/execution-edge-progress-visualization/p05-verification-docs-traceability-closeout` | Update the retained node execution QA matrix, requirements, and traceability evidence for the shipped execution-edge visualization extension |

## Locked Defaults

- This packet set extends `NODE_EXECUTION_VISUALIZATION`; the retained QA-matrix home remains `docs/specs/perf/NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md` rather than a new matrix file.
- Execution edges mean authored control edges only: source-port kinds `exec`, `completed`, and `failed`.
- Edge progress state is run-scoped, active-workspace-filtered, and in-memory only. Do not add `.sfe` persistence fields, session restore payloads, or project-file schema changes for this feature.
- Reuse the existing `node_execution_state_changed` and `node_execution_revision` invalidation path. Do not introduce a second execution-visualization signal or revision channel for edges.
- The per-run authored-edge index is frozen from the run-start authored workspace snapshot so the UI stays aligned with the run snapshot even if the graph is edited mid-run.
- `node_completed` progresses the authored `exec` and `completed` edges from that source node. `node_failed_handled` progresses the authored `failed` edges from that source node when execution continues through failure handlers.
- `run_started`, `run_completed`, `run_stopped`, fatal `run_failed`, and a fresh project session clear edge progress together with node execution state. Non-fatal handled failures preserve the current run's visualization until the run actually ends.
- Unprogressed control edges render at `0.35` alpha and `1.7px` base width. Progressed control edges return to their normal current stroke/color/width. The first progress transition emits a `240ms` QML-local flash using the edge's current base color, `+1.4px` width, and alpha easing from `0.55` to `0.0`.
- Selection and preview keep their current interaction colors and widths and must not be dimmed, but the flash can still layer on top.
- Data edges and passive flow edges remain unchanged.
- Later packets run strictly sequentially; no non-bootstrap packet shares a wave.
- When a later packet extends or invalidates an earlier packet's regression anchor, that later packet inherits and updates the earlier test file inside its own write scope.

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

## Retained Handoff Artifacts

- Review baseline: `PLANS_TO_IMPLEMENT/in_progress/Execution_Edge_Progress_Visualization.md`
- Spec contract: `EXECUTION_EDGE_PROGRESS_VISUALIZATION_P00_bootstrap.md` through `EXECUTION_EDGE_PROGRESS_VISUALIZATION_P05_verification_docs_traceability_closeout.md`
- Implementation prompts: matching `*_PROMPT.md` files for `P00` through `P05`
- Packet wrap-ups: `P00_bootstrap_WRAPUP.md` through `P05_verification_docs_traceability_closeout_WRAPUP.md`
- Final QA matrix: `docs/specs/perf/NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md`
- Status ledger: [EXECUTION_EDGE_PROGRESS_VISUALIZATION_STATUS.md](./EXECUTION_EDGE_PROGRESS_VISUALIZATION_STATUS.md)

## Standard Thread Prompt Shell

`Implement EXECUTION_EDGE_PROGRESS_VISUALIZATION_PXX_<name>.md exactly. Before editing, read EXECUTION_EDGE_PROGRESS_VISUALIZATION_MANIFEST.md, EXECUTION_EDGE_PROGRESS_VISUALIZATION_STATUS.md, and EXECUTION_EDGE_PROGRESS_VISUALIZATION_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update EXECUTION_EDGE_PROGRESS_VISUALIZATION_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every retained `*_PROMPT.md` file in this packet set begins with that shell except for packet number, slug, and packet-local substitutions.
