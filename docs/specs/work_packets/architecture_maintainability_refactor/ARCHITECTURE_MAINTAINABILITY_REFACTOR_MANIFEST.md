# ARCHITECTURE_MAINTAINABILITY_REFACTOR Work Packet Manifest

- Date: `2026-03-28`
- Published packet window: `P00` through `P13`
- Scope baseline: convert the 2026-03-28 architecture maintainability review into an execution-ready, sequential refactor program that removes obsolete internal compatibility seams instead of preserving them, while preserving shipped user workflows, `.sfe` persistence semantics, node type IDs, and documented plugin/package contracts. The program shrinks host-centered APIs, hardens bridge ownership, collapses duplicate project/session authority, relocates persistence concerns out of graph core, splits graph and node hot spots into clearer modules, makes runtime and viewer authority singular, and closes with verification/doc/traceability guardrails.
- Review baseline: [docs/ARCHITECTURE_MAINTAINABILITY_REVIEW_2026-03-28.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/ARCHITECTURE_MAINTAINABILITY_REVIEW_2026-03-28.md)

## Requirement Anchors

- [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/40_NODE_SDK.md`
- `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/80_PERFORMANCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`

## Retained Packet Order

1. `ARCHITECTURE_MAINTAINABILITY_REFACTOR_P00_bootstrap.md`
2. `ARCHITECTURE_MAINTAINABILITY_REFACTOR_P01_graph_canvas_compat_retirement.md`
3. `ARCHITECTURE_MAINTAINABILITY_REFACTOR_P02_bridge_source_contract_hardening.md`
4. `ARCHITECTURE_MAINTAINABILITY_REFACTOR_P03_shell_host_api_retirement.md`
5. `ARCHITECTURE_MAINTAINABILITY_REFACTOR_P04_project_session_authority_collapse.md`
6. `ARCHITECTURE_MAINTAINABILITY_REFACTOR_P05_session_envelope_metadata_cleanup.md`
7. `ARCHITECTURE_MAINTAINABILITY_REFACTOR_P06_graph_persistence_boundary_cleanup.md`
8. `ARCHITECTURE_MAINTAINABILITY_REFACTOR_P07_graph_mutation_ops_split.md`
9. `ARCHITECTURE_MAINTAINABILITY_REFACTOR_P08_node_sdk_surface_cleanup.md`
10. `ARCHITECTURE_MAINTAINABILITY_REFACTOR_P09_runtime_protocol_compat_removal.md`
11. `ARCHITECTURE_MAINTAINABILITY_REFACTOR_P10_viewer_session_backend_split.md`
12. `ARCHITECTURE_MAINTAINABILITY_REFACTOR_P11_graph_canvas_scene_decomposition.md`
13. `ARCHITECTURE_MAINTAINABILITY_REFACTOR_P12_geometry_theme_perf_cleanup.md`
14. `ARCHITECTURE_MAINTAINABILITY_REFACTOR_P13_verification_docs_traceability_closeout.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/architecture-maintainability-refactor/p00-bootstrap` | Establish the packet docs, status ledger, spec-index registration, and git tracking for the new packet set |
| P01 Graph Canvas Compat Retirement | `codex/architecture-maintainability-refactor/p01-graph-canvas-compat-retirement` | Remove `graphCanvasBridge` and retire graph-canvas compatibility aliases in the same packet that migrates their callers |
| P02 Bridge Source Contract Hardening | `codex/architecture-maintainability-refactor/p02-bridge-source-contract-hardening` | Replace bridge fallback discovery with explicit injected source contracts and one composition authority |
| P03 Shell Host API Retirement | `codex/architecture-maintainability-refactor/p03-shell-host-api-retirement` | Reduce `ShellWindow` to lifecycle and Qt ownership while deleting pass-through host APIs |
| P04 Project Session Authority Collapse | `codex/architecture-maintainability-refactor/p04-project-session-authority-collapse` | Remove duplicate save/open/recover/project-file authority and make one service path authoritative |
| P05 Session Envelope Metadata Cleanup | `codex/architecture-maintainability-refactor/p05-session-envelope-metadata-cleanup` | Stop duplicating full `project_doc` in recent-session payloads and replace typeless session metadata buses |
| P06 Graph Persistence Boundary Cleanup | `codex/architecture-maintainability-refactor/p06-graph-persistence-boundary-cleanup` | Move persistence/file-repair concerns out of `graph` and keep persistence envelopes outside graph-owned models |
| P07 Graph Mutation Ops Split | `codex/architecture-maintainability-refactor/p07-graph-mutation-ops-split` | Make graph mutation authority singular and split large transform/normalization buckets into focused operations |
| P08 Node SDK Surface Cleanup | `codex/architecture-maintainability-refactor/p08-node-sdk-surface-cleanup` | Split the internal node-type catch-all into focused modules and leave only a curated documented SDK surface |
| P09 Runtime Protocol Compat Removal | `codex/architecture-maintainability-refactor/p09-runtime-protocol-compat-removal` | Remove normal-path `project_doc` execution compatibility and harden protocol correlation/ownership |
| P10 Viewer Session Backend Split | `codex/architecture-maintainability-refactor/p10-viewer-session-backend-split` | Make execution-side viewer session state authoritative and separate generic session core from DPF-specific logic |
| P11 Graph Canvas Scene Decomposition | `codex/architecture-maintainability-refactor/p11-graph-canvas-scene-decomposition` | Decompose graph-canvas scene/history/payload/host modules after compatibility removal is complete |
| P12 Geometry Theme Perf Cleanup | `codex/architecture-maintainability-refactor/p12-geometry-theme-perf-cleanup` | Split geometry, routing, theme, and performance-policy hotspots into clearer helpers without fallback shims |
| P13 Verification Docs Traceability Closeout | `codex/architecture-maintainability-refactor/p13-verification-docs-traceability-closeout` | Replace brittle proof checks, formalize shell-isolation ownership, and publish final docs and QA evidence |

## Locked Defaults

- This packet set is a cleanup and refactor program, not a feature-expansion program.
- Preserve shipped user-facing workflows, `.sfe` persistence semantics, node type IDs, and documented plugin/package descriptor formats.
- Remove undocumented internal compatibility seams in the same packet that migrates the final in-repo caller; do not leave aliases, fallback props, or pass-through wrappers for a later cleanup packet.
- `graphCanvasBridge` is retired in `P01`; packet-owned QML and shell code must use the focused state/command bridges after that packet lands.
- Bridge classes after `P02` depend on one explicit source contract only. Presenter-or-host fallback and dynamic host discovery are not allowed.
- `ShellWindow` remains the top-level Qt object, but after `P03` it is not a general application-command API.
- `ProjectSessionController` becomes facade-only. Save/open/recover/project-file authority belongs to focused services after `P04`.
- Recent-session payloads must not carry a full `project_doc` after `P05`; autosave owns full-document recovery.
- `WorkspaceData` and related graph-owned models are graph-domain structures only after `P06`; persistence envelope state must live outside them.
- The graph write path becomes one mutation authority plus one invariant kernel after `P07`; direct ad hoc graph writes are not an accepted steady-state path.
- `ea_node_editor.nodes.types` may remain only as the curated documented SDK import surface after `P08`; internal code must move to focused modules.
- `RuntimeSnapshot` is the sole normal run payload after `P09`; any remaining `project_doc` compatibility must be a deliberate edge adapter with packet-owned proof.
- Viewer session state has one authority in execution code after `P10`; UI bridges project that state and do not own a competing workflow state machine.
- When a later packet changes an earlier packet's asserted seam, the later packet inherits and updates the earlier regression anchor inside its own write scope.

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

- Spec contract: `ARCHITECTURE_MAINTAINABILITY_REFACTOR_P00_bootstrap.md` through `ARCHITECTURE_MAINTAINABILITY_REFACTOR_P13_verification_docs_traceability_closeout.md`
- Implementation prompts: matching `*_PROMPT.md` files for `P00` through `P13`
- Packet wrap-ups: `P00_bootstrap_WRAPUP.md` through `P13_verification_docs_traceability_closeout_WRAPUP.md`
- Final QA matrix: `docs/specs/perf/ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX.md`
- Status ledger: [ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md)

## Standard Thread Prompt Shell

`Implement ARCHITECTURE_MAINTAINABILITY_REFACTOR_PXX_<name>.md exactly. Before editing, read ARCHITECTURE_MAINTAINABILITY_REFACTOR_MANIFEST.md, ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md, and ARCHITECTURE_MAINTAINABILITY_REFACTOR_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve documented external contracts and locked defaults, delete packet-owned internal compatibility seams rather than leaving fallback paths behind, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every retained `*_PROMPT.md` file in this packet set begins with that shell except for packet number and file substitutions.
