# ARCHITECTURE_REFACTOR Work Packet Manifest

- Date: `2026-03-25`
- Published packet window: `P00` through `P13`
- Scope baseline: convert the 2026-03-25 architecture audit into an execution-ready, sequential refactor program that preserves shipped product behavior while reducing shell-host bloat, removing graph-domain UI/QML leakage, centralizing graph invariants, making persistence-envelope and document-flavor boundaries explicit, decomposing runtime hotspots, cleaning up plugin and artifact-output API seams, finishing the bridge migration, breaking up `GraphCanvas`/scene/theme hotspots, and restoring docs/release/traceability single-source-of-truth with packet-owned boundary and doc guardrails.
- Audit baseline: [docs/ARCHITECTURE_AUDIT_2026-03-25.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/ARCHITECTURE_AUDIT_2026-03-25.md)

## Requirement Anchors

- [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`

## Retained Packet Order

1. `ARCHITECTURE_REFACTOR_P00_bootstrap.md`
2. `ARCHITECTURE_REFACTOR_P01_shell_host_composition.md`
3. `ARCHITECTURE_REFACTOR_P02_workspace_library_surface.md`
4. `ARCHITECTURE_REFACTOR_P03_project_session_service.md`
5. `ARCHITECTURE_REFACTOR_P04_graph_boundary_adapters.md`
6. `ARCHITECTURE_REFACTOR_P05_graph_invariant_kernel.md`
7. `ARCHITECTURE_REFACTOR_P06_persistence_invariant_adoption.md`
8. `ARCHITECTURE_REFACTOR_P07_runtime_snapshot_context.md`
9. `ARCHITECTURE_REFACTOR_P08_worker_protocol_split.md`
10. `ARCHITECTURE_REFACTOR_P09_dpf_runtime_package.md`
11. `ARCHITECTURE_REFACTOR_P10_dpf_node_viewer_split.md`
12. `ARCHITECTURE_REFACTOR_P11_shell_qml_bridge_retirement.md`
13. `ARCHITECTURE_REFACTOR_P12_graph_canvas_scene_decomposition.md`
14. `ARCHITECTURE_REFACTOR_P13_docs_release_traceability.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/architecture-refactor/p00-bootstrap` | Establish the packet docs, status ledger, spec-index registration, and git tracking |
| P01 Shell Host Composition | `codex/architecture-refactor/p01-shell-host-composition` | Make shell composition/bootstrap authoritative in one place and shrink `ShellWindow` toward a real host boundary |
| P02 Workspace Library Surface | `codex/architecture-refactor/p02-workspace-library-surface` | Narrow `WorkspaceLibraryController` responsibilities and dependency surfaces |
| P03 Project Session Service | `codex/architecture-refactor/p03-project-session-service` | Extract project/session/autosave services from the broad project-session controller |
| P04 Graph Boundary Adapters | `codex/architecture-refactor/p04-graph-boundary-adapters` | Remove UI/QML imports from graph mutation paths by introducing explicit boundary adapters and a packet-owned graph boundary guardrail |
| P05 Graph Invariant Kernel | `codex/architecture-refactor/p05-graph-invariant-kernel` | Centralize graph normalization and invariant policy inside one shared authority |
| P06 Persistence Invariant Adoption | `codex/architecture-refactor/p06-persistence-invariant-adoption` | Make migration and codec paths adopt the shared invariant authority while making persistence-envelope and document-flavor contracts explicit |
| P07 Runtime Snapshot Context | `codex/architecture-refactor/p07-runtime-snapshot-context` | Clarify immutable runtime input versus mutable execution scratch, tighten execution-context typing, and replace private artifact-store reach-ins with public APIs |
| P08 Worker Protocol Split | `codex/architecture-refactor/p08-worker-protocol-split` | Collapse compatibility edges and split worker orchestration into focused runtime modules |
| P09 DPF Runtime Package | `codex/architecture-refactor/p09-dpf-runtime-package` | Break the DPF runtime service into a clearer execution-side package |
| P10 DPF Node Viewer Split | `codex/architecture-refactor/p10-dpf-node-viewer-split` | Separate DPF node-definition, viewer-adapter, and catalog concerns while finishing descriptor-first package-discovery cleanup and keeping shipped type IDs stable |
| P11 Shell QML Bridge Retirement | `codex/architecture-refactor/p11-shell-qml-bridge-retirement` | Finish the shell/QML bridge migration and retire compatibility exports/fallback props |
| P12 Graph Canvas Scene Decomposition | `codex/architecture-refactor/p12-graph-canvas-scene-decomposition` | Break up `GraphCanvas`, scene, host, geometry, and theme hotspots without reopening the graph-surface contract |
| P13 Docs Release Traceability | `codex/architecture-refactor/p13-docs-release-traceability` | Align architecture/spec/release/traceability docs, add doc/link guardrails, and publish the final QA matrix |

## Locked Defaults

- This packet set is a refactor program, not a rewrite.
- Preserve shipped user-facing workflows, `.sfe` persistence semantics, node type IDs, package descriptors, artifact-ref formats, and the current worker command/event vocabulary unless a packet explicitly owns a narrow compatibility change.
- Keep `ShellWindow` as the top-level Qt object, but reduce facade breadth and compatibility indirection over time.
- Keep graph-domain rules authoritative inside `ea_node_editor/graph/` and `ea_node_editor/persistence/`; do not move domain policy into QML helpers.
- Treat `project_doc` compatibility as an edge adapter to be collapsed, not a second permanent runtime API.
- Finish bridge/context retirement only in `P11`; earlier packets may prepare the ground but must not strand current QML consumers.
- When a later packet changes an earlier packet's asserted seam, the later packet inherits and updates the earlier test anchor inside its own write scope.
- Execution is sequential by design: one implementation packet per wave.

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

### Wave 10
- `P10`

### Wave 11
- `P11`

### Wave 12
- `P12`

### Wave 13
- `P13`

## Retained Handoff Artifacts

- Spec contract: `ARCHITECTURE_REFACTOR_P00_bootstrap.md` through `ARCHITECTURE_REFACTOR_P13_docs_release_traceability.md`
- Implementation prompts: matching `*_PROMPT.md` files for `P00` through `P13`
- Packet wrap-ups: `P01_shell_host_composition_WRAPUP.md` through `P13_docs_release_traceability_WRAPUP.md`, plus optional `P00_bootstrap_WRAPUP.md` if bootstrap is replayed in a fresh thread
- Final QA matrix: `docs/specs/perf/ARCHITECTURE_REFACTOR_QA_MATRIX.md`
- Status ledger: [ARCHITECTURE_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_STATUS.md)

## Standard Thread Prompt Shell

`Implement ARCHITECTURE_REFACTOR_PXX_<name>.md exactly. Before editing, read ARCHITECTURE_REFACTOR_MANIFEST.md, ARCHITECTURE_REFACTOR_STATUS.md, and ARCHITECTURE_REFACTOR_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve locked defaults and current public graph/shell/QML/runtime contracts unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update ARCHITECTURE_REFACTOR_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every retained `*_PROMPT.md` file in this packet set begins with that shell except for packet number and filename substitutions.
- `P00` remains orchestrator-owned bootstrap work and should stop after packet-doc creation, status initialization, and index registration.
