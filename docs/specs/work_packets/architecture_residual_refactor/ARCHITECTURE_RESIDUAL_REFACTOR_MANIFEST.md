# ARCHITECTURE_RESIDUAL_REFACTOR Work Packet Manifest

- Date: `2026-04-03`
- Integration base: `main`
- Published packet window: `P00` through `P08`
- Scope baseline: convert the 2026-04-03 residual architecture review into an execution-ready, sequential refactor program that finishes shell host reduction, hardens shell lifecycle isolation, decomposes oversized graph-scene and viewer-session bridge surfaces, decouples execution-side runtime snapshot assembly from persistence-oriented normalization, removes the graph model-to-mutation-service construction cycle, extracts shared runtime contracts out of the `nodes` versus `execution` knot, and closes with semantic verification plus docs evidence without regressing shipped user workflows, `.sfe` persistence semantics, node type IDs, plugin or package contracts, or the documented cross-process viewer contract.
- Review baseline: [docs/ARCHITECTURE_RESIDUAL_REVIEW_2026-04-03.md](../../../ARCHITECTURE_RESIDUAL_REVIEW_2026-04-03.md)

## Requirement Anchors

- [docs/specs/INDEX.md](../../INDEX.md)
- `docs/specs/requirements/10_ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/40_NODE_SDK.md`
- `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`
- `docs/specs/requirements/50_EXECUTION_ENGINE.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/70_INTEGRATIONS.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`

## Retained Packet Order

1. `ARCHITECTURE_RESIDUAL_REFACTOR_P00_bootstrap.md`
2. `ARCHITECTURE_RESIDUAL_REFACTOR_P01_shell_host_surface_retirement.md`
3. `ARCHITECTURE_RESIDUAL_REFACTOR_P02_shell_lifecycle_isolation_hardening.md`
4. `ARCHITECTURE_RESIDUAL_REFACTOR_P03_graph_scene_bridge_decomposition.md`
5. `ARCHITECTURE_RESIDUAL_REFACTOR_P04_viewer_projection_authority_split.md`
6. `ARCHITECTURE_RESIDUAL_REFACTOR_P05_runtime_snapshot_boundary_decoupling.md`
7. `ARCHITECTURE_RESIDUAL_REFACTOR_P06_graph_mutation_service_decoupling.md`
8. `ARCHITECTURE_RESIDUAL_REFACTOR_P07_shared_runtime_contract_extraction.md`
9. `ARCHITECTURE_RESIDUAL_REFACTOR_P08_verification_architecture_closeout.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/architecture-residual-refactor/p00-bootstrap` | Establish the review baseline, packet docs, status ledger, spec-index registration, and git tracking for the new packet set |
| P01 Shell Host Surface Retirement | `codex/architecture-residual-refactor/p01-shell-host-surface-retirement` | Finish reducing `ShellWindow` to lifecycle, Qt ownership, and focused event wiring while narrowing packet-owned controller or presenter host contracts |
| P02 Shell Lifecycle Isolation Hardening | `codex/architecture-residual-refactor/p02-shell-lifecycle-isolation-hardening` | Make packet-owned shell construction and teardown deterministic enough for repeated in-process lifecycle regression coverage |
| P03 Graph Scene Bridge Decomposition | `codex/architecture-residual-refactor/p03-graph-scene-bridge-decomposition` | Split broad graph-scene projection and command responsibilities into narrower packet-owned seams without re-expanding QML globals |
| P04 Viewer Projection Authority Split | `codex/architecture-residual-refactor/p04-viewer-projection-authority-split` | Make viewer-session authority singular and keep bridge or host layers on projection and widget-hosting duties only |
| P05 Runtime Snapshot Boundary Decoupling | `codex/architecture-residual-refactor/p05-runtime-snapshot-boundary-decoupling` | Remove persistence-oriented normalization from the normal execution-side runtime-snapshot path |
| P06 Graph Mutation Service Decoupling | `codex/architecture-residual-refactor/p06-graph-mutation-service-decoupling` | Remove graph-domain service construction knowledge from `GraphModel` and inject mutation authority from composition-level seams |
| P07 Shared Runtime Contract Extraction | `codex/architecture-residual-refactor/p07-shared-runtime-contract-extraction` | Extract runtime handle, artifact, and viewer contracts into a neutral package consumed by both `nodes` and `execution` |
| P08 Verification Architecture Closeout | `codex/architecture-residual-refactor/p08-verification-architecture-closeout` | Replace brittle architecture and shell-catalog proof with semantic packet-owned enforcement and publish final QA evidence |

## Locked Defaults

- This packet set is a cleanup and refactor program, not a feature-expansion program.
- Preserve shipped user-facing workflows, `.sfe` persistence semantics, node type IDs, documented plugin or package contracts, and the REQ-ARCH-016 viewer backend contract.
- Later packets run strictly sequentially; no non-bootstrap packet shares a wave.
- `ShellWindow` remains the top-level Qt object, but after `P01` it is not a broad packet-owned application-command hub.
- After `P02`, packet-owned shell lifecycle tests can create and close multiple `ShellWindow` instances in one interpreter process without relying on hidden global cleanup.
- After `P03`, packet-owned graph-scene QML surfaces consume narrower read-model or command seams rather than one omnibus graph-scene authority.
- After `P04`, viewer-session authority is singular; bridge and host layers project or host that state and do not own a competing workflow state machine.
- After `P05`, the normal execution-side runtime-snapshot builder does not import persistence migration or persistence-envelope helpers.
- After `P06`, `GraphModel` does not manufacture `WorkspaceMutationService`; packet-owned callers obtain mutation authority through composition or a dedicated factory seam.
- After `P07`, packet-owned shared runtime contracts live in a neutral package consumed by `nodes` and `execution`; documented node SDK import surfaces may remain as curated re-export facades where needed.
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

- Review baseline: `docs/ARCHITECTURE_RESIDUAL_REVIEW_2026-04-03.md`
- Spec contract: `ARCHITECTURE_RESIDUAL_REFACTOR_P00_bootstrap.md` through `ARCHITECTURE_RESIDUAL_REFACTOR_P08_verification_architecture_closeout.md`
- Implementation prompts: matching `*_PROMPT.md` files for `P00` through `P08`
- Packet wrap-ups: `P01_shell_host_surface_retirement_WRAPUP.md` through `P08_verification_architecture_closeout_WRAPUP.md`
- Final QA matrix: `docs/specs/perf/ARCHITECTURE_RESIDUAL_REFACTOR_QA_MATRIX.md`
- Status ledger: [ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md](./ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md)

## Standard Thread Prompt Shell

`Implement ARCHITECTURE_RESIDUAL_REFACTOR_PXX_<name>.md exactly. Before editing, read ARCHITECTURE_RESIDUAL_REFACTOR_MANIFEST.md, ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md, and ARCHITECTURE_RESIDUAL_REFACTOR_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every retained `*_PROMPT.md` file in this packet set begins with that shell except for packet number and file substitutions.
