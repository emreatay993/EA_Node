# GRAPH_CANVAS_INTERACTION_PERF Work Packet Manifest

- Date: `2026-03-21`
- Scope baseline: remove the remaining graph-canvas pan/zoom interaction lag relative to single-node dragging through invisible structural optimizations only, while preserving current visuals, public canvas contracts, and user-facing workflow behavior.
- Canonical requirements: [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- Primary requirement anchors:
  - [Architecture](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/10_ARCHITECTURE.md)
  - [UI/UX](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/20_UI_UX.md)
  - [Graph Model](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/30_GRAPH_MODEL.md)
  - [Performance](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/80_PERFORMANCE.md)
  - [QA + Acceptance](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/90_QA_ACCEPTANCE.md)
  - [Traceability Matrix](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/TRACEABILITY_MATRIX.md)
- Runtime baseline:
  - `ea_node_editor/ui_qml/components/GraphCanvas.qml` still routes wheel zoom through separate `adjust_zoom()` and `pan_by()` calls, and it still requests background and edge redraw work from `view_state_changed`.
  - `ea_node_editor/ui_qml/viewport_bridge.py` still emits coarse view updates that the hot canvas path consumes through `GraphCanvasStateBridge`, including a copied `visible_scene_rect_payload`.
  - `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml` still does per-edge screen-space conversion in the hot paint loop and evaluates flow-label geometry in a second per-edge pass.
  - `ea_node_editor/ui_qml/components/GraphCanvas.qml`, `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`, and `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml` still keep the full node world active during pan/zoom without viewport-aware heavy-surface activation.
  - `ea_node_editor/ui_qml/components/graph/GraphNodeChromeBackground.qml` still renders `RectangularShadow` with `cached: false`.
  - The checked-in offscreen heavy-media regression evidence in `docs/specs/perf/TRACK_H_BENCHMARK_REPORT.md` still fails `REQ-PERF-002` by a wide margin, so this packet set targets the remaining structural gap rather than a settings-only tweak.

## Packet Order (Strict)

1. `GRAPH_CANVAS_INTERACTION_PERF_P00_bootstrap.md`
2. `GRAPH_CANVAS_INTERACTION_PERF_P01_perf_harness_baseline_hardening.md`
3. `GRAPH_CANVAS_INTERACTION_PERF_P02_atomic_viewport_state_updates.md`
4. `GRAPH_CANVAS_INTERACTION_PERF_P03_view_state_redraw_flush.md`
5. `GRAPH_CANVAS_INTERACTION_PERF_P04_scene_space_edge_paint_path.md`
6. `GRAPH_CANVAS_INTERACTION_PERF_P05_visible_edge_snapshot_label_model.md`
7. `GRAPH_CANVAS_INTERACTION_PERF_P06_viewport_aware_node_activation.md`
8. `GRAPH_CANVAS_INTERACTION_PERF_P07_node_chrome_shadow_cache.md`
9. `GRAPH_CANVAS_INTERACTION_PERF_P08_auxiliary_canvas_stabilization.md`
10. `GRAPH_CANVAS_INTERACTION_PERF_P09_evidence_refresh_traceability.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/graph-canvas-interaction-perf/p00-bootstrap` | Save the packet set into the repo, register it in the spec index, and initialize the status ledger |
| P01 Perf Harness Baseline Hardening | `codex/graph-canvas-interaction-perf/p01-perf-harness-baseline-hardening` | Harden the real-canvas measurement seam so later optimization packets can be judged against stable phase and drag-control evidence |
| P02 Atomic Viewport State Updates | `codex/graph-canvas-interaction-perf/p02-atomic-viewport-state-updates` | Collapse wheel zoom into one anchored viewport mutation, bind hot canvas consumers directly to raw viewport state, and remove dead per-node zoom fan-out while keeping additive bridge compatibility |
| P03 View-State Redraw Flush | `codex/graph-canvas-interaction-perf/p03-view-state-redraw-flush` | Coalesce viewport-driven grid and edge redraw scheduling so one committed view tick produces one redraw flush |
| P04 Scene-Space Edge Paint Path | `codex/graph-canvas-interaction-perf/p04-scene-space-edge-paint-path` | Move edge paint math onto a scene-space transform path instead of per-point screen conversion |
| P05 Visible-Edge Snapshot And Label Model | `codex/graph-canvas-interaction-perf/p05-visible-edge-snapshot-label-model` | Reuse one visible-edge snapshot for painting and flow labels |
| P06 Viewport-Aware Node Activation | `codex/graph-canvas-interaction-perf/p06-viewport-aware-node-activation` | Deactivate offscreen heavy node subtrees while preserving active-node behavior and current interaction semantics |
| P07 Node Chrome And Shadow Cache | `codex/graph-canvas-interaction-perf/p07-node-chrome-shadow-cache` | Cache stable node chrome/shadow work with explicit geometry/selection-border/shadow-preference invalidation and no visible output change |
| P08 Auxiliary Canvas Stabilization | `codex/graph-canvas-interaction-perf/p08-auxiliary-canvas-stabilization` | Stabilize grid, minimap, and full-canvas input hot paths so auxiliary layers stop dominating viewport motion |
| P09 Evidence Refresh And Traceability | `codex/graph-canvas-interaction-perf/p09-evidence-refresh-traceability` | Re-run offscreen full-fidelity, max-performance, and node-drag control evidence on the same machine, complete the Windows desktop/manual exit gate, and only then refresh checked-in evidence plus any required truthfulness docs |

## Locked Defaults

- `full_fidelity` remains the primary acceptance mode for this packet set. Every packet must keep `full_fidelity` visually identical from the user’s point of view.
- No temporary hiding, proxy surfaces, label suppression, or appearance changes are allowed to satisfy this packet set in `full_fidelity`.
- No packet may introduce a new user-facing mode, toggle, setting, or persistent schema change.
- Preserve `graphCanvas` discoverability and public methods: `toggleMinimapExpanded()`, `clearLibraryDropPreview()`, `updateLibraryDropPreview()`, `isPointInCanvas()`, and `performLibraryDrop()`.
- Preserve the existing public `ViewportBridge`, `GraphCanvasCommandBridge`, `GraphCanvasBridge`, `GraphCanvasStateBridge`, and `GraphNodeHost` contracts unless a packet explicitly adds an additive private optimization seam while keeping current public callers working.
- Intermediate benchmark runs must write to packet-specific artifact directories under `artifacts/`; only `P09` may refresh checked-in performance docs or the canonical `artifacts/graphics_performance_modes_docs` snapshot.
- This packet set is intentionally sequential. Each implementation packet runs in its own dedicated worker branch/worktree and no wave contains more than one packet.
- Use the project venv for packet verification commands (`./venv/Scripts/python.exe`) unless a packet explicitly requires something else.

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

## Handoff Artifacts (Mandatory Per Packet)

- Spec contract: `GRAPH_CANVAS_INTERACTION_PERF_Pxx_<name>.md`
- Implementation prompt: `GRAPH_CANVAS_INTERACTION_PERF_Pxx_<name>_PROMPT.md`
- Status ledger update in [GRAPH_CANVAS_INTERACTION_PERF_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_canvas_interaction_perf/GRAPH_CANVAS_INTERACTION_PERF_STATUS.md):
  - branch label
  - accepted commit sha (or `n/a` when no git metadata is available)
  - command history
  - test summary
  - artifact paths
  - residual risks

## Standard Thread Prompt Shell

`Implement GRAPH_CANVAS_INTERACTION_PERF_PXX_<name>.md exactly. Before editing, read GRAPH_CANVAS_INTERACTION_PERF_MANIFEST.md, GRAPH_CANVAS_INTERACTION_PERF_STATUS.md, and GRAPH_CANVAS_INTERACTION_PERF_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve locked defaults and current full-fidelity visuals unless the packet explicitly changes an internal optimization seam, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update GRAPH_CANVAS_INTERACTION_PERF_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every `*_PROMPT.md` file in this packet set must begin with that shell verbatim except for packet number and filename substitutions.
- Packet-specific notes may be appended after the shell when a packet has extra locked constraints.

## Packet Template Rules

- Every implementation packet spec must include: objective, preconditions, execution dependencies, target subsystems, conservative write scope, required behavior, non-goals, verification commands, review gate, expected artifacts, acceptance criteria, and handoff notes.
- Every prompt must tell a fresh-thread agent to read the manifest, status ledger, and packet spec before editing.
- Every prompt must use the standard thread prompt shell defined above.
- `P00` is documentation-only. `P01` through `P09` may change source/test/docs files, but each thread must implement exactly one packet.
- Execution waves are authoritative. Do not start a later wave until every packet in the current wave is `PASS` or `FAIL`.
- Keep the benchmark/report evidence comparable. Packet-owned benchmark refreshes must record graph size, sample size, Qt platform, selected `performance_mode`, scenario, and whether the actual `GraphCanvas.qml` render path was exercised.
- This planning/bootstrap thread ends after `P00` is complete. All later packets must be executed in fresh threads using the generated prompt files or the executor skill.
