# ARCH_THIRD_PASS Work Packet Manifest

- Date: `2026-03-18`
- Scope baseline: targeted follow-up refactor for the remaining architecture hotspots identified after `ARCH_SECOND_PASS`, with no intentional user-visible workflow changes and no planned `.sfe` or app-preferences schema changes.
- Canonical requirements: [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- Primary requirement anchors:
  - [Architecture](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/10_ARCHITECTURE.md)
  - [UI/UX](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/20_UI_UX.md)
  - [Node Execution Model](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/45_NODE_EXECUTION_MODEL.md)
  - [Persistence](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/60_PERSISTENCE.md)
  - [QA + Acceptance](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/90_QA_ACCEPTANCE.md)
- Runtime baseline:
  - `ea_node_editor/ui/shell/window.py` is still a 2268-line host facade that performs constructor/bootstrap wiring, timer setup, service assembly, and broad QML-facing orchestration in one class.
  - `ea_node_editor/ui_qml/shell_context_bootstrap.py` still mixes bridge assembly, context-property registration, image-provider registration, and main-shell source binding.
  - `ea_node_editor/ui/shell/controllers/workspace_library_controller.py` is still an 895-line umbrella controller spanning custom workflow library management, search/focus flows, import/export, and edit-command orchestration.
  - `ea_node_editor/ui_qml/MainShell.qml`, `components/shell/WorkspaceCenterPane.qml`, and `components/GraphCanvas.qml` still expose packet-owned consumers to raw `mainWindow`, `sceneBridge`, and `viewBridge` compatibility paths even though focused bridges exist.
  - `ea_node_editor/ui_qml/graph_scene_bridge.py` remains the public scene bridge while `graph_scene_mutation_history.py` still concentrates mutation, rebuild, layout/history, and selection-adjacent coordination behind internal reach-through.
  - `ea_node_editor/ui_qml/components/graph/passive/GraphMediaPanelSurface.qml` still depends on raw shell/scene objects for packet-owned media flows instead of explicit bridge contracts.
  - `ea_node_editor/execution/worker.py` still combines run control, scheduling, execution, and event publication, and `REQ-NODE-011` remains an explicit tightening target for data-only dependency evaluation.
  - Graph validation and normalization behavior remains split across graph model, normalization, persistence migration/codec, compiler, and registry layers, with final traceability/doc closure still pending after the structural refactors.

## Packet Order (Strict)

1. `ARCH_THIRD_PASS_P00_bootstrap.md`
2. `ARCH_THIRD_PASS_P01_shell_composition_root.md`
3. `ARCH_THIRD_PASS_P02_workspace_library_capabilities.md`
4. `ARCH_THIRD_PASS_P03_bridge_first_shell_canvas.md`
5. `ARCH_THIRD_PASS_P04_scene_mutation_contracts.md`
6. `ARCH_THIRD_PASS_P05_passive_media_bridge_cleanup.md`
7. `ARCH_THIRD_PASS_P06_execution_worker_runtime.md`
8. `ARCH_THIRD_PASS_P07_validation_persistence_centralization.md`
9. `ARCH_THIRD_PASS_P08_verification_traceability.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/arch-third-pass/p00-bootstrap` | Save the packet set into the repo, register it in the spec index, and initialize the status ledger/execution waves |
| P01 Shell Composition Root | `codex/arch-third-pass/p01-shell-composition-root` | Turn `window.py` into a thinner facade by extracting constructor/bootstrap wiring and service assembly helpers |
| P02 Workspace Library Capabilities | `codex/arch-third-pass/p02-workspace-library-capabilities` | Split workspace-library behavior into focused capability owners without changing shell workflows |
| P03 Bridge-First Shell And Canvas Roots | `codex/arch-third-pass/p03-bridge-first-shell-canvas` | Move root shell/canvas QML consumers onto focused bridges first and fence packet-owned QML off raw context fallbacks |
| P04 Scene Mutation Contracts | `codex/arch-third-pass/p04-scene-mutation-contracts` | Introduce explicit scene context/services around mutation, rebuild, selection, and history coordination while preserving the public bridge API |
| P05 Passive Media Bridge Cleanup | `codex/arch-third-pass/p05-passive-media-bridge-cleanup` | Remove raw shell/scene dependence from passive media surfaces and trim packet-owned compatibility exports |
| P06 Execution Worker Runtime | `codex/arch-third-pass/p06-execution-worker-runtime` | Decompose worker runtime seams and make data-only dependency execution explicit under `REQ-NODE-011` |
| P07 Validation And Persistence Centralization | `codex/arch-third-pass/p07-validation-persistence-centralization` | Centralize validation/normalization rules without changing persisted document shape |
| P08 Verification And Traceability | `codex/arch-third-pass/p08-verification-traceability` | Close the packet set with docs, residual-risk reporting, traceability registration, and a focused regression sweep |

## Locked Defaults

- Preserve current user-visible workflows and public QML/object contracts unless a packet explicitly tightens an internal compatibility seam.
- Keep public `ShellWindow` `@pyqtSlot`, `@pyqtProperty`, and signal names stable across the packet set.
- Keep `GraphCanvas.qml` root contracts stable: `objectName: "graphCanvas"`, `toggleMinimapExpanded()`, `clearLibraryDropPreview()`, `updateLibraryDropPreview()`, `isPointInCanvas()`, and `performLibraryDrop()`.
- Keep `GraphSceneBridge` public `@pyqtSlot` / `@pyqtProperty` names stable while `P04` refactors internal ownership behind that surface.
- Keep raw compatibility context properties available until packet-owned consumers migrate off them; later packets may trim only the packet-owned fallback paths they fully replace.
- Do not introduce `.sfe`, project metadata, or app-preferences schema version changes in this packet set.
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

- Spec contract: `ARCH_THIRD_PASS_Pxx_<name>.md`
- Implementation prompt: `ARCH_THIRD_PASS_Pxx_<name>_PROMPT.md`
- Status ledger update in [ARCH_THIRD_PASS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/arch_third_pass/ARCH_THIRD_PASS_STATUS.md):
  - branch label
  - accepted commit sha
  - command history
  - test summary
  - artifact paths
  - residual risks

## Standard Thread Prompt Shell

`Implement ARCH_THIRD_PASS_PXX_<name>.md exactly. Before editing, read ARCH_THIRD_PASS_MANIFEST.md, ARCH_THIRD_PASS_STATUS.md, and ARCH_THIRD_PASS_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve public QML/object contracts unless the packet explicitly changes one, update ARCH_THIRD_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, and stop after PXX; do not start PXX+1.`

- Every `*_PROMPT.md` file in this packet set must begin with that shell verbatim except for packet number and filename substitutions.
- Packet-specific notes may be appended after the shell when a packet has extra locked constraints.

## Packet Template Rules

- Every implementation packet spec must include: objective, preconditions, execution dependencies, target subsystems, conservative write scope, required behavior, non-goals, verification commands, review gate, expected artifacts, acceptance criteria, and handoff notes.
- Every prompt must tell a fresh-thread agent to read the manifest, status ledger, and packet spec before editing.
- Every prompt must tell the agent to run the full `Verification Commands`, run the packet `Review Gate` when it is not `none`, create the packet wrap-up, update the shared status ledger, and stop after that packet.
- `P00` is documentation-only. `P01` through `P08` may change source/test/docs files, but each thread must implement exactly one packet.
- Execution waves are authoritative. Do not start a later wave until every packet in the current wave is `PASS` or `FAIL`.
- This planning/bootstrap thread ends after `P00` is complete. All later packets must be executed in fresh threads using the generated prompt files or the executor skill.
