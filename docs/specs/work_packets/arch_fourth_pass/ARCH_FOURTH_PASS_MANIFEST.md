# ARCH_FOURTH_PASS Work Packet Manifest

- Date: `2026-03-19`
- Scope baseline: targeted follow-up refactor for the remaining architecture risks after `ARCH_THIRD_PASS` and the multi-agent architecture review, with no intentional user-visible workflow changes and no planned `.sfe` or app-preferences schema version changes.
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
- Runtime baseline:
  - `ea_node_editor/persistence/migration.py` and `ea_node_editor/graph/normalization.py` still drop unresolved plugin nodes instead of preserving them losslessly.
  - `ea_node_editor/nodes/builtins/subnode.py` still owns constants and rules consumed as core graph/runtime semantics by `graph` and `execution`.
  - `ea_node_editor/graph/model.py` still accepts broad mutable state changes while registry-aware validation and normalization remain split across model, persistence, compiler, and UI-layer callers.
  - `ea_node_editor/execution/compiler.py` and `ea_node_editor/execution/worker.py` still compile and execute document-shaped mappings instead of a narrower typed runtime boundary.
  - `ea_node_editor/ui/shell/window.py` remains a large composition root and QML API surface, `ea_node_editor/ui_qml/shell_context_bootstrap.py` still exports raw compatibility objects, and packet-owned QML still falls back to `mainWindow`, `sceneBridge`, and `viewBridge`.
  - `ea_node_editor/ui_qml/graph_scene_payload_builder.py` still imports shell-side helper code, and verification/traceability facts remain duplicated across `tests/conftest.py`, `scripts/run_verification.py`, `scripts/check_traceability.py`, and docs.

## Packet Order (Strict)

1. `ARCH_FOURTH_PASS_P00_bootstrap.md`
2. `ARCH_FOURTH_PASS_P01_unknown_plugin_preservation.md`
3. `ARCH_FOURTH_PASS_P02_subnode_contract_promotion.md`
4. `ARCH_FOURTH_PASS_P03_graph_mutation_validation_boundary.md`
5. `ARCH_FOURTH_PASS_P04_execution_runtime_dto_pipeline.md`
6. `ARCH_FOURTH_PASS_P05_shell_presenter_boundary.md`
7. `ARCH_FOURTH_PASS_P06_bridge_first_qml_contract_cleanup.md`
8. `ARCH_FOURTH_PASS_P07_verification_manifest_consolidation.md`
9. `ARCH_FOURTH_PASS_P08_docs_traceability_closeout.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/arch-fourth-pass/p00-bootstrap` | Save the packet set into the repo, register it in the spec index, and initialize the status ledger/execution waves |
| P01 Unknown Plugin Preservation | `codex/arch-fourth-pass/p01-unknown-plugin-preservation` | Preserve unresolved plugin-authored graph content without making it executable |
| P02 Subnode Contract Promotion | `codex/arch-fourth-pass/p02-subnode-contract-promotion` | Move subnode semantics below the builtin plugin layer and keep builtins as consumers |
| P03 Graph Mutation Validation Boundary | `codex/arch-fourth-pass/p03-graph-mutation-validation-boundary` | Introduce a validated mutation boundary so authoring rules are enforced before persistence/compiler cleanup |
| P04 Execution Runtime DTO Pipeline | `codex/arch-fourth-pass/p04-execution-runtime-dto-pipeline` | Compile and execute against typed runtime DTOs/services instead of document-shaped dict orchestration |
| P05 Shell Presenter Boundary | `codex/arch-fourth-pass/p05-shell-presenter-boundary` | Shrink `ShellWindow` and move packet-owned QML-facing state/commands into focused presenters/models |
| P06 Bridge-First QML Contract Cleanup | `codex/arch-fourth-pass/p06-bridge-first-qml-contract-cleanup` | Finish packet-owned QML migration away from raw compatibility seams and neutralize cross-package helper leakage |
| P07 Verification Manifest Consolidation | `codex/arch-fourth-pass/p07-verification-manifest-consolidation` | Centralize verification phase/traceability facts in one declarative source and remove text-bound duplication |
| P08 Docs And Traceability Closeout | `codex/arch-fourth-pass/p08-docs-traceability-closeout` | Close the packet set with architecture docs, QA matrix, traceability registration, and residual-risk reporting |

## Locked Defaults

- Preserve current user-visible workflows and public QML/object contracts unless a packet explicitly narrows an internal compatibility seam.
- Keep `.sfe` document shape and app-preferences document shape stable across this packet set unless a packet proves a schema change is unavoidable; no schema version bump is planned.
- Preserve unresolved plugin-authored nodes, edges, and metadata losslessly in authored documents even when the runtime cannot execute them.
- Keep public `ShellWindow`, bridge, and `GraphSceneBridge` slot/property/signal names stable unless a packet explicitly introduces a compatibility replacement and migration path.
- Keep the queue boundary dict adapters for process communication, but move typed ownership inward so runtime services do not depend on broad document-shaped mappings.
- Prefer shared support modules below both `ui` and `ui_qml` over bidirectional helper reach-through between those packages.
- Target merge branch defaults to `main`.
- Use the project venv for verification commands: `./venv/Scripts/python.exe`.

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

## Handoff Artifacts (Mandatory Per Packet)

- Spec contract: `ARCH_FOURTH_PASS_Pxx_<name>.md`
- Implementation prompt: `ARCH_FOURTH_PASS_Pxx_<name>_PROMPT.md`
- Status ledger update in [ARCH_FOURTH_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_fourth_pass/ARCH_FOURTH_PASS_STATUS.md):
  - branch label
  - accepted commit sha
  - command history
  - test summary
  - artifact paths
  - residual risks

## Standard Thread Prompt Shell

`Implement ARCH_FOURTH_PASS_PXX_<name>.md exactly. Before editing, read ARCH_FOURTH_PASS_MANIFEST.md, ARCH_FOURTH_PASS_STATUS.md, and ARCH_FOURTH_PASS_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve public QML/object contracts unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the packet wrap-up, update ARCH_FOURTH_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every `*_PROMPT.md` file in this packet set must begin with that shell verbatim except for packet number and filename substitutions.
- Packet-specific notes may be appended after the shell when a packet has extra locked constraints.

## Packet Template Rules

- Every implementation packet spec must include: objective, preconditions, execution dependencies, target subsystems, conservative write scope, required behavior, non-goals, verification commands, review gate, expected artifacts, acceptance criteria, and handoff notes.
- Every prompt must tell a fresh-thread agent to read the manifest, status ledger, and packet spec before editing.
- Every prompt must tell the agent to run the full `Verification Commands`, run the packet `Review Gate` when it is not `none`, create the packet wrap-up, update the shared status ledger, and stop after that packet.
- `P00` is documentation-only. `P01` through `P08` may change source/test/docs files, but each thread must implement exactly one packet.
- Execution waves are authoritative. Do not start a later wave until every packet in the current wave is `PASS` or `FAIL`.
- Prefer the narrowest stable verification slice that proves the packet. Do not substitute `tests/test_shell_isolation_phase.py` or `scripts/run_verification.py --mode full` for narrower shell-scoped proof unless the packet explicitly requires it.
- This planning/bootstrap thread ends after `P00` is complete. All later packets must be executed in fresh threads using the generated prompt files or the executor skill.
