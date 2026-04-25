# COREX_NO_LEGACY_ARCHITECTURE_CLEANUP Work Packet Manifest

- Date: `2026-04-24`
- Integration base: `main`
- Published packet window: `P00` through `P14`
- Scope baseline: create a no-legacy architecture cleanup program for COREX now that there is no user/customer migration burden. The current baseline already includes `COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION` through P05, so high-level graph action routing through `GraphActionController` and `GraphActionBridge` is treated as done. This packet set targets the remaining compatibility layers: graph-canvas bridge wrappers and raw QML globals, duplicate `ShellWindow` facade routes, workspace/custom-workflow fallback authority, current-schema-only persistence, graph overlay/mutation duplication, node/plugin/add-on descriptor-only loading, snapshot-only runtime execution, typed viewer transport state, launch/import shims, and traceability closeout.
- Review baseline: source-code exploration performed on current `main` after commit `071f9dd` plus uncommitted user work for `comment_floating_popover` and `embedded_viewer_overlay_manager`; uncommitted files are treated as user-owned and not packet-owned unless a later executor explicitly rebases this packet set.

## Requirement Anchors

- [docs/specs/INDEX.md](../../INDEX.md)
- `ARCHITECTURE.md`
- `README.md`
- `docs/specs/requirements/10_ARCHITECTURE.md`
- `docs/specs/requirements/30_GRAPH_MODEL.md`
- `docs/specs/requirements/40_NODE_SDK.md`
- `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`
- `docs/specs/requirements/50_EXECUTION_ENGINE.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/70_INTEGRATIONS.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_MANIFEST.md`
- `docs/specs/work_packets/architecture_residual_refactor/ARCHITECTURE_RESIDUAL_REFACTOR_MANIFEST.md`
- `docs/specs/work_packets/corex_architecture_entry_point_reduction/COREX_ARCHITECTURE_ENTRY_POINT_REDUCTION_MANIFEST.md`

## Retained Packet Order

1. `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P00_bootstrap.md`
2. `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P01_no_legacy_guardrails.md`
3. `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P02_graph_canvas_bridge_retirement.md`
4. `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P03_shell_graph_action_facade_retirement.md`
5. `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P04_qml_context_source_contract_cleanup.md`
6. `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P05_workspace_custom_workflow_authority.md`
7. `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P06_current_schema_persistence_cleanup.md`
8. `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P07_graph_persistence_overlay_removal.md`
9. `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P08_graph_mutation_and_fragment_consolidation.md`
10. `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P09_node_sdk_registry_cleanup.md`
11. `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P10_plugin_addon_descriptor_only.md`
12. `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P11_runtime_snapshot_only_protocol.md`
13. `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P12_viewer_session_transport_cleanup.md`
14. `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P13_launch_package_import_shim_cleanup.md`
15. `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P14_docs_traceability_closeout.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/corex-no-legacy-architecture-cleanup/p00-bootstrap` | Establish packet docs, status ledger, execution waves, standalone prompts, and spec-index registration |
| P01 No-Legacy Guardrails | `codex/corex-no-legacy-architecture-cleanup/p01-no-legacy-guardrails` | Convert compatibility assertions into no-legacy guardrails before deleting broad surfaces |
| P02 Graph Canvas Bridge Retirement | `codex/corex-no-legacy-architecture-cleanup/p02-graph-canvas-bridge-retirement` | Retire `GraphCanvasBridge`, private canvas bridge aliases, and remaining input-layer command bridge routes |
| P03 Shell Graph Action Facade Retirement | `codex/corex-no-legacy-architecture-cleanup/p03-shell-graph-action-facade-retirement` | Remove duplicate `ShellWindow` graph-action slots after injecting direct graph-action dependencies |
| P04 QML Context Source Contract Cleanup | `codex/corex-no-legacy-architecture-cleanup/p04-qml-context-source-contract-cleanup` | Shrink flat QML globals and remove shell-window fallback discovery from bridge source contracts |
| P05 Workspace Custom Workflow Authority | `codex/corex-no-legacy-architecture-cleanup/p05-workspace-custom-workflow-authority` | Make workspace order and custom workflow operations explicit, scoped, and ID-based |
| P06 Current Schema Persistence Cleanup | `codex/corex-no-legacy-architecture-cleanup/p06-current-schema-persistence-cleanup` | Drop old project/preference/session/artifact input shapes while retaining current schema validation |
| P07 Graph Persistence Overlay Removal | `codex/corex-no-legacy-architecture-cleanup/p07-graph-persistence-overlay-removal` | Remove unresolved persistence overlay state from graph-owned models and normalization |
| P08 Graph Mutation and Fragment Consolidation | `codex/corex-no-legacy-architecture-cleanup/p08-graph-mutation-and-fragment-consolidation` | Collapse duplicated graph mutation/parser/facade paths onto one authoritative domain API |
| P09 Node SDK Registry Cleanup | `codex/corex-no-legacy-architecture-cleanup/p09-node-sdk-registry-cleanup` | Remove registry category aliases, broad node SDK shims, and class-first built-in registration |
| P10 Plugin Add-on Descriptor Only | `codex/corex-no-legacy-architecture-cleanup/p10-plugin-addon-descriptor-only` | Require descriptor/add-on records, retire plugin class probing, DPF alias modules, and add-on ID aliases |
| P11 Runtime Snapshot Only Protocol | `codex/corex-no-legacy-architecture-cleanup/p11-runtime-snapshot-only-protocol` | Make `RuntimeSnapshot` mandatory and delete `project_path` rebuild and old trigger-shape tolerance |
| P12 Viewer Session Transport Cleanup | `codex/corex-no-legacy-architecture-cleanup/p12-viewer-session-transport-cleanup` | Replace viewer session projection aliases and widget property handshakes with typed transport/session state |
| P13 Launch Package Import Shim Cleanup | `codex/corex-no-legacy-architecture-cleanup/p13-launch-package-import-shim-cleanup` | Collapse launch, package, telemetry, lazy import, and packaging path shims onto canonical entry points |
| P14 Docs Traceability Closeout | `codex/corex-no-legacy-architecture-cleanup/p14-docs-traceability-closeout` | Publish no-legacy architecture docs, QA matrix, traceability rows, and hygiene guards |

## Worker Agent Defaults

- Implementation workers for `P01` through `P14` must be spawned with `model="gpt-5.5"` and `reasoning_effort="xhigh"`.
- Exploratory subagents may use `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point discovery.
- Spark may be used only for one exact non-editing lookup in a known file family.

## Locked Defaults

- This packet set intentionally removes internal compatibility layers. Do not preserve fallback paths solely for old project files, old plugin packages, old QML globals, old ShellWindow slots, or historical import paths.
- Preserve current user-visible behavior, menu labels, shortcuts, QML-visible feature affordances, and current `.sfe` schema behavior unless a packet explicitly narrows that contract.
- Treat current-schema files as the only load target. Older schema support may be rejected or moved to a separate offline importer only if a packet explicitly owns that decision.
- High-level graph actions already route through `GraphActionController` and `GraphActionBridge`; do not re-plan that work. Only remaining low-level input-layer, bridge wrapper, and shell facade compatibility belongs to this packet set.
- `RuntimeSnapshot` is the only normal execution payload after `P11`; `project_doc` and project-path rebuild behavior must not remain as ordinary worker startup paths.
- `category_path`, descriptor records, explicit workflow scope, stable workflow IDs, and typed viewer transport/session models are the canonical contracts after the relevant packets land.
- Later packets inherit earlier regression anchors when they change seams already asserted by earlier packets. Update inherited tests inside the later packet instead of leaving stale compatibility assertions behind.
- Uncommitted user work visible during planning, including `comment_floating_popover` and `embedded_viewer_overlay_manager` changes, is not packet-owned by default.

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

### Wave 14
- `P14`

## Retained Handoff Artifacts

- Manifest: `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_MANIFEST.md`
- Status ledger: `docs/specs/work_packets/corex_no_legacy_architecture_cleanup/COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_STATUS.md`
- Packet specs: `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P00_bootstrap.md` through `COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_P14_docs_traceability_closeout.md`
- Packet prompts: matching `*_PROMPT.md` files for `P00` through `P14`
- Packet wrap-ups: `P01_no_legacy_guardrails_WRAPUP.md` through `P14_docs_traceability_closeout_WRAPUP.md`
- Final QA matrix planned by P14: `docs/specs/perf/COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_QA_MATRIX.md`

## Standard Thread Prompt Shell

```text
Implement COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_PXX_<name>.md exactly. Before editing, read COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_MANIFEST.md, COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_STATUS.md, and COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve current user-visible behavior and locked defaults, delete packet-owned internal compatibility seams instead of leaving fallback paths behind, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update COREX_NO_LEGACY_ARCHITECTURE_CLEANUP_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.
```

- Every retained `*_PROMPT.md` file in this packet set begins with that shell except for packet number and file substitutions.
- Executor-spawned implementation workers must use `gpt-5.5` with `xhigh` reasoning for this packet set.
