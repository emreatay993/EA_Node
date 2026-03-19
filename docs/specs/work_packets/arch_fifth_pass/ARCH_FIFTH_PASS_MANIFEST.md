# ARCH_FIFTH_PASS Work Packet Manifest

- Date: `2026-03-19`
- Scope baseline: sequential architecture cleanup follow-up after `ARCH_FOURTH_PASS` and the multi-agent architecture review, preserving exact user-facing behavior, UI/UX, and performance while finishing the remaining startup, shell/QML, mutation-boundary, persistence/runtime, plugin-contract, and verification-seam refactors.
- Canonical requirements: [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- Primary requirement anchors:
  - [Architecture](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/10_ARCHITECTURE.md)
  - [UI/UX](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/20_UI_UX.md)
  - [Graph Model](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/30_GRAPH_MODEL.md)
  - [Node SDK](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/40_NODE_SDK.md)
  - [Node Execution Model](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/45_NODE_EXECUTION_MODEL.md)
  - [Execution Engine](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/50_EXECUTION_ENGINE.md)
  - [Persistence](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/60_PERSISTENCE.md)
  - [Performance](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/80_PERFORMANCE.md)
  - [QA + Acceptance](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/90_QA_ACCEPTANCE.md)
  - [Traceability Matrix](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/TRACEABILITY_MATRIX.md)
- Runtime baseline:
  - `ea_node_editor/app.py` still imports `AppPreferencesController` from the UI layer to resolve startup theme selection.
  - `ea_node_editor/ui/shell/window.py` still constructs most runtime collaborators directly and remains the dominant shell/QML integration object.
  - `ea_node_editor/ui/shell/controllers/workspace_library_controller.py` still aggregates workflow publishing, navigation, edit, import/export, and failure-focus responsibilities in one controller surface.
  - `ea_node_editor/ui_qml/shell_context_bootstrap.py`, `ea_node_editor/ui_qml/MainShell.qml`, and `ea_node_editor/ui_qml/components/GraphCanvas.qml` still keep raw compatibility globals and fallback paths beside the bridge-first contract.
  - `ea_node_editor/graph/model.py`, `ea_node_editor/ui_qml/graph_scene_payload_builder.py`, and `ea_node_editor/ui/shell/runtime_history.py` still leave graph writes, payload normalization, and undo-state capture split across multiple layers.
  - `ea_node_editor/persistence/migration.py`, `ea_node_editor/persistence/project_codec.py`, and `ea_node_editor/graph/model.py` still mix live-model ownership with persistence-only unresolved payload concerns and retain pre-current-schema migration complexity.
  - `ea_node_editor/ui/shell/controllers/run_controller.py`, `ea_node_editor/execution/client.py`, and `ea_node_editor/execution/worker.py` still move raw `project_doc` payloads across the run boundary.
  - `ea_node_editor/nodes/plugin_loader.py` and `ea_node_editor/nodes/package_manager.py` still rely on constructor-driven discovery and archive-shape validation instead of a narrower descriptor contract.
  - `scripts/check_traceability.py`, `scripts/verification_manifest.py`, and oversized regression modules still carry more verification/process weight than the current architecture should require.

## Packet Order (Strict)

1. `ARCH_FIFTH_PASS_P00_bootstrap.md`
2. `ARCH_FIFTH_PASS_P01_startup_preferences_boundary.md`
3. `ARCH_FIFTH_PASS_P02_shell_composition_root.md`
4. `ARCH_FIFTH_PASS_P03_shell_controller_surface_split.md`
5. `ARCH_FIFTH_PASS_P04_bridge_contract_foundation.md`
6. `ARCH_FIFTH_PASS_P05_bridge_first_qml_migration.md`
7. `ARCH_FIFTH_PASS_P06_authoring_mutation_service_foundation.md`
8. `ARCH_FIFTH_PASS_P07_authoring_mutation_completion_history.md`
9. `ARCH_FIFTH_PASS_P08_current_schema_persistence_boundary.md`
10. `ARCH_FIFTH_PASS_P09_runtime_snapshot_execution_pipeline.md`
11. `ARCH_FIFTH_PASS_P10_plugin_descriptor_package_contract.md`
12. `ARCH_FIFTH_PASS_P11_regression_suite_modularization.md`
13. `ARCH_FIFTH_PASS_P12_verification_manifest_traceability.md`
14. `ARCH_FIFTH_PASS_P13_docs_traceability_closeout.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/arch-fifth-pass/p00-bootstrap` | Save the packet set into the repo, register it in the spec index, and initialize the status ledger |
| P01 Startup And Preferences Boundary | `codex/arch-fifth-pass/p01-startup-preferences-boundary` | Unify startup entrypoints, isolate startup preferences from UI host logic, and make the performance harness package boundary honest |
| P02 Shell Composition Root | `codex/arch-fifth-pass/p02-shell-composition-root` | Move shell object construction into an explicit composition module and reduce `ShellWindow` to a host/facade |
| P03 Shell Controller Surface Split | `codex/arch-fifth-pass/p03-shell-controller-surface-split` | Break `WorkspaceLibraryController` into focused controllers while preserving its current behavioral surface |
| P04 Bridge Contract Foundation | `codex/arch-fifth-pass/p04-bridge-contract-foundation` | Introduce focused canvas state/command bridges without removing compatibility shims yet |
| P05 Bridge-First QML Migration | `codex/arch-fifth-pass/p05-bridge-first-qml-migration` | Migrate QML off raw compatibility globals and preserve exact shell/canvas behavior and performance |
| P06 Authoring Mutation Service Foundation | `codex/arch-fifth-pass/p06-authoring-mutation-service-foundation` | Introduce the authoritative authoring mutation service and route primary graph edits through it |
| P07 Authoring Mutation Completion And History | `codex/arch-fifth-pass/p07-authoring-mutation-completion-history` | Finish mutation-service adoption for transforms/payload normalization and make history capture full mutable workspace state |
| P08 Current-Schema Persistence Boundary | `codex/arch-fifth-pass/p08-current-schema-persistence-boundary` | Move persistence-only overlay state out of the live graph model and narrow load/save to current-schema ownership |
| P09 Runtime Snapshot Execution Pipeline | `codex/arch-fifth-pass/p09-runtime-snapshot-execution-pipeline` | Replace `project_doc` run transport with a runtime snapshot boundary while preserving exact execution behavior |
| P10 Plugin Descriptor And Package Contract | `codex/arch-fifth-pass/p10-plugin-descriptor-package-contract` | Add descriptor-based plugin loading and semantic package validation with legacy fallback preserved |
| P11 Regression Suite Modularization | `codex/arch-fifth-pass/p11-regression-suite-modularization` | Split oversized regression suites into maintainable modules while keeping current command entrypoints stable |
| P12 Verification Manifest And Traceability | `codex/arch-fifth-pass/p12-verification-manifest-traceability` | Make verification facts declarative and reduce traceability checker duplication without changing verification outcomes |
| P13 Docs And Traceability Closeout | `codex/arch-fifth-pass/p13-docs-traceability-closeout` | Close the packet set with updated architecture docs, QA matrix, and relative-link traceability cleanup |

## Locked Defaults

- Preserve user-facing behavior, UI/UX, and performance exactly throughout this packet set. No intentional workflow, interaction, rendering, or latency changes are allowed.
- Preserve the current schema's `.sfe` behavior. This packet set does not need to preserve support for schemas older than the current repo schema.
- No packet-owned `.sfe` schema version bump is planned. Future forward-compatibility policy for later schemas belongs to a different plan.
- Keep public QML/object names, slot/property/signal surfaces, and current shell/canvas behavioral contracts stable unless a packet explicitly introduces a compatibility-preserving replacement and removes the old path only after migration is complete.
- Prefer internal compatibility shims over public behavior changes while packets migrate boundaries.
- Use the project venv for verification commands: `./venv/Scripts/python.exe`.
- Target merge branch defaults to `main`.

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

## Handoff Artifacts (Mandatory Per Packet)

- Spec contract: `ARCH_FIFTH_PASS_Pxx_<name>.md`
- Implementation prompt: `ARCH_FIFTH_PASS_Pxx_<name>_PROMPT.md`
- Status ledger update in [ARCH_FIFTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_fifth_pass/ARCH_FIFTH_PASS_STATUS.md):
  - branch label
  - accepted commit sha
  - command history
  - test summary
  - artifact paths
  - residual risks

## Standard Thread Prompt Shell

`Implement ARCH_FIFTH_PASS_PXX_<name>.md exactly. Before editing, read ARCH_FIFTH_PASS_MANIFEST.md, ARCH_FIFTH_PASS_STATUS.md, and ARCH_FIFTH_PASS_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve exact user-facing behavior, UI/UX, and performance, preserve current-schema \`.sfe\` behavior while treating pre-current-schema compatibility exactly as the packet specifies, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the packet wrap-up, update ARCH_FIFTH_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every `*_PROMPT.md` file in this packet set must begin with that shell verbatim except for packet number and filename substitutions.
- Packet-specific notes may be appended after the shell when a packet has extra locked constraints.

## Packet Template Rules

- Every implementation packet spec must include: objective, preconditions, execution dependencies, target subsystems, conservative write scope, required behavior, non-goals, verification commands, review gate, expected artifacts, acceptance criteria, and handoff notes.
- Every prompt must tell a fresh-thread agent to read the manifest, status ledger, and packet spec before editing.
- Every prompt must tell the agent to run the full `Verification Commands`, run the packet `Review Gate` when it is not `none`, create the packet wrap-up, update the shared status ledger, and stop after that packet.
- `P00` is documentation-only. `P01` through `P13` may change source/test/docs files, but each thread must implement exactly one packet.
- Execution waves are authoritative. Do not start a later wave until every packet in the current wave is `PASS` or `FAIL`.
- Prefer the narrowest stable verification slice that proves the packet. Do not substitute repo-wide workflows for narrower packet-owned proof unless the packet explicitly requires the broader gate.
- This planning/bootstrap thread ends after `P00` is complete. All later packets must be executed in fresh threads using the generated prompt files or the executor skill.
