# GRAPH_CANVAS_PERF Work Packet Manifest

- Date: `2026-03-18`
- Scope baseline: improve graph-canvas pan/zoom FPS without intentionally changing current visuals, interaction contracts, or user-facing workflow behavior.
- Canonical requirements: [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- Primary requirement anchors:
  - [Architecture](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/10_ARCHITECTURE.md)
  - [UI/UX](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/20_UI_UX.md)
  - [Graph Model](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/30_GRAPH_MODEL.md)
  - [Performance](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/80_PERFORMANCE.md)
  - [QA + Acceptance](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/90_QA_ACCEPTANCE.md)
- Runtime baseline:
  - `ea_node_editor/ui_qml/components/GraphCanvas.qml` currently requests pan/zoom redraw work from root-level view-state connections while `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml` also listens to `zoom_changed` and `center_changed`, so one logical viewport update can schedule duplicate edge/background invalidation.
  - `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml` repaints the full edge list and computes flow-label geometry for the full model on view changes; it does not cull by the visible scene rect before label/paint work.
  - `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasBackground.qml` repaints the grid on every view-state update, and `GraphCanvas.qml` only simplifies node shadows during interaction; it does not currently reuse a cached node-world layer during pan/zoom.
  - `ea_node_editor/telemetry/performance_harness.py` currently times `GraphSceneBridge` and `ViewportBridge` event processing without instantiating `GraphCanvas.qml`, so the archived `TRACK_H` numbers do not directly measure the reported low-FPS canvas rendering path.

## Packet Order (Strict)

1. `GRAPH_CANVAS_PERF_P00_bootstrap.md`
2. `GRAPH_CANVAS_PERF_P01_real_canvas_benchmark_baseline.md`
3. `GRAPH_CANVAS_PERF_P02_view_state_redraw_coalescing.md`
4. `GRAPH_CANVAS_PERF_P03_edge_label_viewport_culling.md`
5. `GRAPH_CANVAS_PERF_P04_viewport_interaction_world_cache.md`
6. `GRAPH_CANVAS_PERF_P05_perf_docs_traceability.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/graph-canvas-perf/p00-bootstrap` | Save the packet set into the repo, register it in the spec index, and initialize the status ledger |
| P01 Real Canvas Benchmark Baseline | `codex/graph-canvas-perf/p01-real-canvas-benchmark-baseline` | Establish a real `GraphCanvas.qml` pan/zoom benchmark and regression seam |
| P02 View-State Redraw Coalescing | `codex/graph-canvas-perf/p02-view-state-redraw-coalescing` | Remove duplicate pan/zoom redraw scheduling while preserving current canvas behavior |
| P03 Edge/Label Viewport Culling | `codex/graph-canvas-perf/p03-edge-label-viewport-culling` | Skip offscreen edge and flow-label work that does not contribute to the visible frame |
| P04 Viewport Interaction World Cache | `codex/graph-canvas-perf/p04-viewport-interaction-world-cache` | Reuse a cached node-world presentation during viewport interaction without changing steady-state visuals |
| P05 Perf Docs Traceability | `codex/graph-canvas-perf/p05-perf-docs-traceability` | Publish the updated benchmark workflow, evidence, QA matrix, and traceability links |

## Locked Defaults

- Preserve current canvas visuals and UI/UX features. Any temporary interaction-only optimization must settle back to the current idle appearance without introducing a new user-visible mode or toggle.
- Keep `graphCanvas` discoverability and public methods stable: `toggleMinimapExpanded()`, `clearLibraryDropPreview()`, `updateLibraryDropPreview()`, `isPointInCanvas()`, and `performLibraryDrop()`.
- Keep `ViewportBridge`, `GraphCanvasBridge`, and `GraphNodeHost` public properties/signals/slots stable unless a packet explicitly confines a change to private optimization wiring.
- Prefer redraw coalescing, viewport culling, and cache reuse over permanent feature removal or permanent visual simplification.
- The benchmark accepted by this packet set must instantiate `GraphCanvas.qml` with representative graph payloads; bridge-only timing is insufficient for sign-off on the reported FPS complaint.
- Use the project venv for verification commands (`./venv/Scripts/python.exe`) unless a packet explicitly requires something else.
- This packet set is intentionally sequential. No implementation wave contains more than one packet.

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

## Handoff Artifacts (Mandatory Per Packet)

- Spec contract: `GRAPH_CANVAS_PERF_Pxx_<name>.md`
- Implementation prompt: `GRAPH_CANVAS_PERF_Pxx_<name>_PROMPT.md`
- Status ledger update in [GRAPH_CANVAS_PERF_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_canvas_perf/GRAPH_CANVAS_PERF_STATUS.md):
  - branch label
  - accepted commit sha (or `n/a` when no git metadata is available)
  - command history
  - test summary
  - artifact paths
  - residual risks

## Standard Thread Prompt Shell

`Implement GRAPH_CANVAS_PERF_PXX_<name>.md exactly. Before editing, read GRAPH_CANVAS_PERF_MANIFEST.md, GRAPH_CANVAS_PERF_STATUS.md, and GRAPH_CANVAS_PERF_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve current canvas visuals and UI/UX contracts unless the packet explicitly changes an internal optimization seam, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update GRAPH_CANVAS_PERF_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every `*_PROMPT.md` file in this packet set must begin with that shell verbatim except for packet number and filename substitutions.
- Packet-specific notes may be appended after the shell when a packet has extra locked constraints.

## Packet Template Rules

- Every implementation packet spec must include: objective, preconditions, execution dependencies, target subsystems, conservative write scope, required behavior, non-goals, verification commands, review gate, expected artifacts, acceptance criteria, and handoff notes.
- Every prompt must tell a fresh-thread agent to read the manifest, status ledger, and packet spec before editing.
- Every prompt must use the standard thread prompt shell defined above.
- `P00` is documentation-only. `P01` through `P05` may change source/test/docs files, but each thread must implement exactly one packet.
- Execution waves are authoritative. Do not start a later wave until every packet in the current wave is `PASS` or `FAIL`.
- Keep new performance evidence comparable: record sample size, node/edge counts, Qt platform, and whether the run exercised the actual canvas render path.
- This planning/bootstrap thread ends after `P00` is complete. All later packets must be executed in fresh threads using the generated prompt files or the executor skill.
