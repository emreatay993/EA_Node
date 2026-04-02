# ARCHITECTURE_FOLLOWUP_REFACTOR Work Packet Manifest

- Date: `2026-04-01`
- Integration base: `main`
- Published packet window: `P00` through `P08`
- Scope baseline: convert the 2026-04-01 architecture follow-up review into an execution-ready, sequential refactor program that completes shell composition cleanup, retires the remaining broad shell and QML bridge surfaces, removes residual graph or persistence coupling, builds runtime inputs directly from domain models, collapses graph authoring and viewer ownership onto singular authorities, and closes with targeted verification and documentation evidence without regressing shipped user workflows, `.sfe` persistence semantics, node type IDs, or existing viewer-family user-facing behavior.
- Review baseline: [docs/ARCHITECTURE_FOLLOWUP_REVIEW_2026-04-01.md](../../../ARCHITECTURE_FOLLOWUP_REVIEW_2026-04-01.md)

## Requirement Anchors

- [docs/specs/INDEX.md](../../INDEX.md)
- `docs/specs/requirements/10_ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`
- `docs/specs/requirements/50_EXECUTION_ENGINE.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/70_INTEGRATIONS.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`

## Retained Packet Order

1. `ARCHITECTURE_FOLLOWUP_REFACTOR_P00_bootstrap.md`
2. `ARCHITECTURE_FOLLOWUP_REFACTOR_P01_shell_composition_root_collapse.md`
3. `ARCHITECTURE_FOLLOWUP_REFACTOR_P02_shell_controller_surface_narrowing.md`
4. `ARCHITECTURE_FOLLOWUP_REFACTOR_P03_qml_bridge_cleanup_finalization.md`
5. `ARCHITECTURE_FOLLOWUP_REFACTOR_P04_graph_persistence_sidecar_removal.md`
6. `ARCHITECTURE_FOLLOWUP_REFACTOR_P05_runtime_snapshot_direct_builder.md`
7. `ARCHITECTURE_FOLLOWUP_REFACTOR_P06_graph_authoring_boundary_collapse.md`
8. `ARCHITECTURE_FOLLOWUP_REFACTOR_P07_viewer_session_single_authority.md`
9. `ARCHITECTURE_FOLLOWUP_REFACTOR_P08_verification_docs_closeout.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/architecture-followup-refactor/p00-bootstrap` | Establish the review baseline, packet docs, status ledger, spec-index registration, and git tracking for the new packet set |
| P01 Shell Composition Root Collapse | `codex/architecture-followup-refactor/p01-shell-composition-root-collapse` | Reduce `ShellWindow` to host/lifecycle duties and make `composition.py` the sole packet-owned composition root |
| P02 Shell Controller Surface Narrowing | `codex/architecture-followup-refactor/p02-shell-controller-surface-narrowing` | Replace broad shell controller and service host surfaces with focused controller or adapter contracts |
| P03 QML Bridge Cleanup Finalization | `codex/architecture-followup-refactor/p03-qml-bridge-cleanup-finalization` | Retire the remaining graph-canvas compatibility bridge and make packet-owned QML consume only explicit focused bridge contracts |
| P04 Graph Persistence Sidecar Removal | `codex/architecture-followup-refactor/p04-graph-persistence-sidecar-removal` | Remove remaining persistence overlay ownership from graph models and snapshots |
| P05 Runtime Snapshot Direct Builder | `codex/architecture-followup-refactor/p05-runtime-snapshot-direct-builder` | Build runtime snapshot payloads directly from domain objects instead of round-tripping through the project codec |
| P06 Graph Authoring Boundary Collapse | `codex/architecture-followup-refactor/p06-graph-authoring-boundary-collapse` | Establish one packet-owned graph authoring command boundary and remove global boundary-adapter registration |
| P07 Viewer Session Single Authority | `codex/architecture-followup-refactor/p07-viewer-session-single-authority` | Make execution-side viewer session state authoritative and limit bridge and host layers to projection or widget hosting |
| P08 Verification Docs Closeout | `codex/architecture-followup-refactor/p08-verification-docs-closeout` | Publish final QA evidence, update architecture-follow-up traceability, and close the packet set without re-expanding proof machinery |

## Locked Defaults

- This packet set is a cleanup and refactor program, not a feature-expansion program.
- Preserve shipped user-facing workflows, `.sfe` persistence semantics, node type IDs, node package or plugin contracts, and existing viewer-family `output_mode` behavior.
- Later packets run strictly sequentially; no non-bootstrap packet shares a wave.
- After `P01`, `composition.py` is the only packet-owned composition root and `ShellWindow` is no longer a broad application-command hub.
- After `P02`, packet-owned shell bridges, presenters, and services must not depend on broad umbrella facades when focused controller or adapter seams are available.
- After `P03`, packet-owned QML must not depend on `GraphCanvasBridge`; packet-owned QML consumes focused bridge exports only.
- After `P04`, graph-owned models and snapshots do not import or carry persistence overlay ownership directly.
- After `P05`, `build_runtime_snapshot(...)` does not serialize through the project codec on the normal execution path.
- After `P06`, packet-owned graph authoring uses one authoritative command path and does not rely on mutable global boundary-adapter installation.
- After `P07`, `ViewerSessionService` is the sole packet-owned authority for viewer liveness, blocker, transport-revision, and session projection inputs; bridge and host layers do not own a competing state machine.
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

## Retained Handoff Artifacts

- Review baseline: `docs/ARCHITECTURE_FOLLOWUP_REVIEW_2026-04-01.md`
- Spec contract: `ARCHITECTURE_FOLLOWUP_REFACTOR_P00_bootstrap.md` through `ARCHITECTURE_FOLLOWUP_REFACTOR_P08_verification_docs_closeout.md`
- Implementation prompts: matching `*_PROMPT.md` files for `P00` through `P08`
- Packet wrap-ups: `P00_bootstrap_WRAPUP.md` through `P08_verification_docs_closeout_WRAPUP.md`
- Final QA matrix: `docs/specs/perf/ARCHITECTURE_FOLLOWUP_REFACTOR_QA_MATRIX.md`
- Status ledger: [ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md](./ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md)

## Standard Thread Prompt Shell

`Implement ARCHITECTURE_FOLLOWUP_REFACTOR_PXX_<name>.md exactly. Before editing, read ARCHITECTURE_FOLLOWUP_REFACTOR_MANIFEST.md, ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md, and ARCHITECTURE_FOLLOWUP_REFACTOR_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every retained `*_PROMPT.md` file in this packet set begins with that shell except for packet number and file substitutions.
