# PERSISTENT_NODE_ELAPSED_TIMES Work Packet Manifest

- Date: `2026-04-08`
- Integration base: `main`
- Published packet window: `P00` through `P07`
- Scope baseline: convert `PLANS_TO_IMPLEMENT/in_progress/Persistent_Node_Elapsed_Times.md` into an execution-ready, strictly sequential packet set that extends the shipped node-execution visualization with session-only, workspace-scoped cached node elapsed times; adds additive worker timing metadata plus shell-side fallbacks; keeps cached elapsed data separate from running/completed chrome state; invalidates timings only on execution-affecting workflow changes; preserves active-workspace-filtered in-memory ownership with no `.sfe` persistence changes; and closes by updating the retained `NODE_EXECUTION_VISUALIZATION` QA/traceability home instead of creating a competing matrix.
- Review baseline: [PLANS_TO_IMPLEMENT/in_progress/Persistent_Node_Elapsed_Times.md](../../../../PLANS_TO_IMPLEMENT/in_progress/Persistent_Node_Elapsed_Times.md)

## Requirement Anchors

- [docs/specs/INDEX.md](../../INDEX.md)
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`
- `docs/specs/requirements/50_EXECUTION_ENGINE.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/work_packets/node_execution_visualization/NODE_EXECUTION_VISUALIZATION_MANIFEST.md`
- `docs/specs/work_packets/execution_edge_progress_visualization/EXECUTION_EDGE_PROGRESS_VISUALIZATION_MANIFEST.md`
- `docs/specs/perf/NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md`

## Retained Packet Order

1. `PERSISTENT_NODE_ELAPSED_TIMES_P00_bootstrap.md`
2. `PERSISTENT_NODE_ELAPSED_TIMES_P01_worker_timing_protocol_projection.md`
3. `PERSISTENT_NODE_ELAPSED_TIMES_P02_shell_elapsed_cache_projection.md`
4. `PERSISTENT_NODE_ELAPSED_TIMES_P03_graph_canvas_elapsed_bindings.md`
5. `PERSISTENT_NODE_ELAPSED_TIMES_P04_history_action_type_expansion.md`
6. `PERSISTENT_NODE_ELAPSED_TIMES_P05_timing_cache_invalidation_hooks.md`
7. `PERSISTENT_NODE_ELAPSED_TIMES_P06_node_footer_persistent_elapsed_rendering.md`
8. `PERSISTENT_NODE_ELAPSED_TIMES_P07_verification_docs_traceability_closeout.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/persistent-node-elapsed-times/p00-bootstrap` | Establish the packet docs, status ledger, and spec-index registration for the persistent elapsed-time follow-up set |
| P01 Worker Timing Protocol Projection | `codex/persistent-node-elapsed-times/p01-worker-timing-protocol-projection` | Add additive worker timing metadata on `node_started` and `node_completed` around real plugin execution time without changing shell or QML yet |
| P02 Shell Elapsed Cache Projection | `codex/persistent-node-elapsed-times/p02-shell-elapsed-cache-projection` | Extend shell run state and run handling with transient started-at tracking, per-workspace elapsed caching, and backward-compatible fallback timing behavior |
| P03 Graph Canvas Elapsed Bindings | `codex/persistent-node-elapsed-times/p03-graph-canvas-elapsed-bindings` | Expose active-workspace timing lookups through the bridge-first GraphCanvas contract before renderer work consumes them |
| P04 History Action Type Expansion | `codex/persistent-node-elapsed-times/p04-history-action-type-expansion` | Split coarse history action types so execution-affecting and cosmetic edits become distinguishable before centralized invalidation consumes that taxonomy |
| P05 Timing Cache Invalidation Hooks | `codex/persistent-node-elapsed-times/p05-timing-cache-invalidation-hooks` | Add the centralized elapsed-cache invalidation hook on commit/undo/redo using the packet-owned action taxonomy from `P04` |
| P06 Node Footer Persistent Elapsed Rendering | `codex/persistent-node-elapsed-times/p06-node-footer-persistent-elapsed-rendering` | Render live and cached elapsed footer text from the packet-owned timing lookups while preserving stable probe names and failure-priority behavior |
| P07 Verification Docs Traceability Closeout | `codex/persistent-node-elapsed-times/p07-verification-docs-traceability-closeout` | Update the retained node-execution QA matrix, requirements, and traceability evidence for the shipped persistent elapsed-time extension |

## Locked Defaults

- This packet set extends the retained node-execution visualization closeout path. Update `docs/specs/perf/NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md` rather than creating a second elapsed-time QA matrix.
- Cached node elapsed values are session-only and workspace-scoped. Do not add `.sfe` persistence fields, project-file schema changes, or session-restore payloads for this feature.
- Worker timing metadata is additive and backward compatible. If `started_at_epoch_ms` or `elapsed_ms` is absent, the shell path computes elapsed time from its own packet-owned fallback state.
- Cached elapsed data stays separate from `running_node_ids`, `completed_node_ids`, and authored execution-edge progress so completed chrome still clears at terminal events while the footer can remain visible.
- `run_started` clears transient running/completed visualization and transient started-at state for the new run, but it does not clear cached elapsed data for an otherwise unchanged workspace.
- `node_completed` overwrites the cached elapsed value for that node only. Stopped or failed runs update only the nodes that actually reached completion; untouched nodes keep their prior cached elapsed value.
- Active-workspace filtering remains authoritative in `GraphCanvasStateBridge`, and the packet set must reuse the existing `node_execution_state_changed` plus `node_execution_revision` invalidation path rather than introducing a second execution-visualization signal or revision channel.
- Execution-affecting edits invalidate cached elapsed data. Cosmetic/layout edits such as move, resize, collapse, rename/title-only changes, style edits, edge-label edits, port-label edits, comment-only changes, selection changes, scope changes, workspace switching, or theme/performance changes preserve the cache.
- Project replacement, new-project install, and equivalent session replacement flows clear all cached elapsed timing data.
- Bridge property exposure lands before renderer work: `P03` owns the bridge/canvas timing contract, and `P06` owns the end-user footer rendering that consumes that contract.
- History action-type expansion lands before centralized invalidation: `P04` owns the taxonomy split, and `P05` consumes that taxonomy at the history commit/undo/redo seam.
- Later packets run strictly sequentially; no non-bootstrap packet shares a wave.
- When a later packet changes a seam already asserted by an earlier packet's regression anchor, that later packet inherits and updates the earlier test file inside its own write scope.

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

- Review baseline: `PLANS_TO_IMPLEMENT/in_progress/Persistent_Node_Elapsed_Times.md`
- Spec contract: `PERSISTENT_NODE_ELAPSED_TIMES_P00_bootstrap.md` through `PERSISTENT_NODE_ELAPSED_TIMES_P07_verification_docs_traceability_closeout.md`
- Implementation prompts: matching `*_PROMPT.md` files for `P00` through `P07`
- Packet wrap-ups: `P00_bootstrap_WRAPUP.md` through `P07_verification_docs_traceability_closeout_WRAPUP.md`
- Final QA matrix: `docs/specs/perf/NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md`
- Status ledger: [PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md](./PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md)

## Standard Thread Prompt Shell

`Implement PERSISTENT_NODE_ELAPSED_TIMES_PXX_<name>.md exactly. Before editing, read PERSISTENT_NODE_ELAPSED_TIMES_MANIFEST.md, PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md, and PERSISTENT_NODE_ELAPSED_TIMES_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every retained `*_PROMPT.md` file in this packet set begins with that shell except for packet number, slug, and packet-local substitutions.
