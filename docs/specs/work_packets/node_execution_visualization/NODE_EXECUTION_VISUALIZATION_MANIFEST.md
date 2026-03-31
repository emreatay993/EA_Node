# NODE_EXECUTION_VISUALIZATION Work Packet Manifest

- Date: `2026-03-31`
- Integration base: `main`
- Published packet window: `P00` through `P04`
- Scope baseline: convert the 2026-03-31 node execution visualization plan into an execution-ready packet set that surfaces run-scoped running and completed node states during workflow execution, reuses the existing failure-pulse architecture and worker protocol, implements the blue running pulse plus green completed flash/border treatment from the visual reference, uses a QML-local elapsed timer for running nodes, preserves failure priority, avoids persistence or protocol expansion, and closes with verification, QA-matrix, and traceability evidence.
- Review baseline: [docs/PLAN_Node_Execution_Visualization.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/PLAN_Node_Execution_Visualization.md)

## Requirement Anchors

- [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- `docs/specs/requirements/10_ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`
- `docs/specs/requirements/50_EXECUTION_ENGINE.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`

## Retained Packet Order

1. `NODE_EXECUTION_VISUALIZATION_P00_bootstrap.md`
2. `NODE_EXECUTION_VISUALIZATION_P01_run_state_execution_projection.md`
3. `NODE_EXECUTION_VISUALIZATION_P02_graph_canvas_execution_bindings.md`
4. `NODE_EXECUTION_VISUALIZATION_P03_node_chrome_execution_highlights.md`
5. `NODE_EXECUTION_VISUALIZATION_P04_verification_docs_traceability_closeout.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/node-execution-visualization/p00-bootstrap` | Establish the packet docs, status ledger, spec-index registration, and git tracking for the new packet set |
| P01 Run State Execution Projection | `codex/node-execution-visualization/p01-run-state-execution-projection` | Add run-scoped running/completed node state to the shell path and expose bridge-level execution lookups without changing worker protocol or QML visuals |
| P02 Graph Canvas Execution Bindings | `codex/node-execution-visualization/p02-graph-canvas-execution-bindings` | Thread the new execution lookup properties through `GraphCanvas.qml` and lock the bridge-first canvas property contract before node-host chrome work begins |
| P03 Node Chrome Execution Highlights | `codex/node-execution-visualization/p03-node-chrome-execution-highlights` | Render running/completed node chrome, timer, z-priority, and failure-priority behavior on top of the packet-owned canvas contracts |
| P04 Verification Docs Traceability Closeout | `codex/node-execution-visualization/p04-verification-docs-traceability-closeout` | Publish QA evidence and requirement/traceability updates for the shipped execution-visualization feature |

## Locked Defaults

- The worker/execution protocol is unchanged in this packet set. `node_started` and `node_completed` events already emitted by the worker are the only event sources for the feature.
- `ShellRunState` owns ephemeral run-scoped execution visualization data only. Do not add `.sfe` persistence fields, schema changes, or execution protocol payload expansion for this feature.
- Running nodes render with a blue pulse. Completed nodes render a one-shot green flash and then keep a static green border until the run ends. Existing failure red remains the highest-priority visual state.
- Running/completed highlights clear on `run_started`, `run_completed`, `run_stopped`, and fatal worker-reset failures. Non-fatal `run_failed` preserves the last execution highlight state so the failure pulse still has execution context.
- Active-workspace filtering remains authoritative in `GraphCanvasStateBridge`. Inactive workspaces must not display foreign run highlights.
- The elapsed timer is QML-local and derives from `isRunningNode` transitions. Do not add Python monotonic timestamp bridges or completed-duration persistence in this packet set.
- The visual reference at `docs/node_execution_visualization_alternatives.html` is authoritative for pulse/flash styling unless a later packet explicitly documents a justified deviation in its wrap-up and the final closeout packet records it.
- Highlight halos may force render-active and stacking exceptions for running/completed nodes, but they must not mutate graph geometry, hit-testing contracts, selection semantics, or cached scene payload structure outside the packet-owned visual state.
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

## Retained Handoff Artifacts

- Spec contract: `NODE_EXECUTION_VISUALIZATION_P00_bootstrap.md` through `NODE_EXECUTION_VISUALIZATION_P04_verification_docs_traceability_closeout.md`
- Implementation prompts: matching `*_PROMPT.md` files for `P00` through `P04`
- Packet wrap-ups: `P00_bootstrap_WRAPUP.md` through `P04_verification_docs_traceability_closeout_WRAPUP.md`
- Final QA matrix: `docs/specs/perf/NODE_EXECUTION_VISUALIZATION_QA_MATRIX.md`
- Status ledger: [NODE_EXECUTION_VISUALIZATION_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/node_execution_visualization/NODE_EXECUTION_VISUALIZATION_STATUS.md)

## Standard Thread Prompt Shell

`Implement NODE_EXECUTION_VISUALIZATION_PXX_<name>.md exactly. Before editing, read NODE_EXECUTION_VISUALIZATION_MANIFEST.md, NODE_EXECUTION_VISUALIZATION_STATUS.md, and NODE_EXECUTION_VISUALIZATION_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update NODE_EXECUTION_VISUALIZATION_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every retained `*_PROMPT.md` file in this packet set begins with that shell except for packet number and file substitutions.
