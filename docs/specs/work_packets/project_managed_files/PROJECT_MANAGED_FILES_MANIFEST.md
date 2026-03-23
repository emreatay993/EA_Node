# PROJECT_MANAGED_FILES Work Packet Manifest

- Date: `2026-03-23`
- Scope baseline: add a project-managed file and artifact architecture that keeps `.sfe` as the canonical project file while introducing a sibling sidecar data folder, managed source assets for current media nodes, staged generated outputs, save-time promotion/pruning, crash-only staged-data recovery, lightweight project-file UX, and one concrete heavy-output runtime adopter without turning the app into a full artifact manager.
- Canonical requirements: [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)
- Primary requirement anchors:
  - [Architecture](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/10_ARCHITECTURE.md)
  - [UI/UX](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/20_UI_UX.md)
  - [Node SDK](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/40_NODE_SDK.md)
  - [Node Execution Model](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/45_NODE_EXECUTION_MODEL.md)
  - [Execution Engine](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/50_EXECUTION_ENGINE.md)
  - [Persistence](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/60_PERSISTENCE.md)
  - [QA + Acceptance](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/requirements/90_QA_ACCEPTANCE.md)
- Runtime baseline:
  - `.sfe` documents still persist raw string paths and do not have a first-class artifact store; media nodes serialize `source_path` directly and current preview providers accept only absolute local files.
  - `SessionAutosaveStore` persists whole-project snapshots to `last_session.json` and `autosave.sfe`, but it has no staging-root or managed-file recovery contract.
  - `ProjectSessionController` has standard Save/Open flows but no Save As flow, no sidecar data-folder promotion logic, and no project-file summary dialog.
  - `File Read`, `File Write`, `Excel Read`, and `Excel Write` still resolve plain `Path(...)` values from node inputs/properties and return raw file paths rather than managed artifact refs.
  - `Process Run` still captures stdout/stderr inline in worker memory, truncates to `PROCESS_STREAM_CAPTURE_CHAR_LIMIT`, and has no stored-output mode or artifact handle ports.

## Packet Order (Strict)

1. `PROJECT_MANAGED_FILES_P00_bootstrap.md`
2. `PROJECT_MANAGED_FILES_P01_artifact_store_foundation.md`
3. `PROJECT_MANAGED_FILES_P02_media_resolution_adoption.md`
4. `PROJECT_MANAGED_FILES_P03_staging_recovery_lifecycle.md`
5. `PROJECT_MANAGED_FILES_P04_save_promotion_prune.md`
6. `PROJECT_MANAGED_FILES_P05_save_as_copy_flow.md`
7. `PROJECT_MANAGED_FILES_P06_source_import_defaults.md`
8. `PROJECT_MANAGED_FILES_P07_file_issue_node_repair.md`
9. `PROJECT_MANAGED_FILES_P08_project_files_summary.md`
10. `PROJECT_MANAGED_FILES_P09_execution_artifact_refs.md`
11. `PROJECT_MANAGED_FILES_P10_generated_output_adoption.md`
12. `PROJECT_MANAGED_FILES_P11_process_run_output_mode_ui.md`
13. `PROJECT_MANAGED_FILES_P12_docs_traceability_qa.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
| P00 Bootstrap | `codex/project-managed-files/p00-bootstrap` | Save the packet set into the repo, register it in the spec index, and initialize the status ledger |
| P01 Artifact Store Foundation | `codex/project-managed-files/p01-artifact-store-foundation` | Add the managed/staged artifact manifest contract, sidecar path helpers, and central resolver/store foundation |
| P02 Media Resolution Adoption | `codex/project-managed-files/p02-media-resolution-adoption` | Route media preview, sizing, and PDF normalization through the new artifact/path resolver |
| P03 Staging Recovery Lifecycle | `codex/project-managed-files/p03-staging-recovery-lifecycle` | Add temp staging, unsaved-project staging roots, and crash-only staged-data recovery/session plumbing |
| P04 Save Promotion Prune | `codex/project-managed-files/p04-save-promotion-prune` | Commit referenced staged files on Save, replace current managed copies, and prune orphan managed files |
| P05 Save As Copy Flow | `codex/project-managed-files/p05-save-as-copy-flow` | Add Save As plus the self-contained copy flow and managed-data copy-choice dialog |
| P06 Source Import Defaults | `codex/project-managed-files/p06-source-import-defaults` | Add the app-level managed-copy default and the source import/copy service used by media/source nodes |
| P07 File Issue Node Repair | `codex/project-managed-files/p07-file-issue-node-repair` | Surface owner/consumer missing-file warnings and node-level repair/convert actions |
| P08 Project Files Summary | `codex/project-managed-files/p08-project-files-summary` | Add the compact project-files dialog and project-wide staged/broken summaries for save/open/recovery flows |
| P09 Execution Artifact Refs | `codex/project-managed-files/p09-execution-artifact-refs` | Add queue-safe artifact-ref runtime payloads and downstream resolution support in the execution layer |
| P10 Generated Output Adoption | `codex/project-managed-files/p10-generated-output-adoption` | Add artifact-writer helpers and adopt managed generated outputs in file/spreadsheet nodes |
| P11 Process Run Output Mode UI | `codex/project-managed-files/p11-process-run-output-mode-ui` | Add the concrete memory-vs-stored heavy-output adopter on Process Run with inline toggle and status chip UX |
| P12 Docs Traceability QA | `codex/project-managed-files/p12-docs-traceability-qa` | Refresh architecture/requirements/traceability docs and publish the packet-scoped QA matrix |

## Locked Defaults

- `.sfe` remains the canonical project document. Managed files live in a sibling sidecar directory named `<project-stem>.data/`.
- Use additive metadata under `metadata.artifact_store`; do not introduce a schema-version bump in this packet set.
- Persist project-managed file references as stable `artifact://<artifact_id>` strings. External files remain raw absolute paths or file URLs.
- Before the first save, managed imports and stored outputs stage in temp storage. After a project has a real `.sfe` path, stored outputs still stage first and become permanent only on Save.
- Save commits only staged files still referenced by the current project state. Regenerating the same logical output replaces the earlier staged copy. Permanent managed files also replace the current version rather than storing history.
- Crash/autosave recovery may offer staged-data recovery. Clean close without save discards staged scratch data.
- Save As always asks the user what to do. The default selection is a self-contained copy of the project plus currently referenced managed files, without staging.
- Opening a project never blocks on missing external or managed files. Owner nodes and consumer nodes surface warnings, and node-level repair remains available.
- The v1 UX stays lightweight: node-local warnings/actions plus a compact project-files dialog. Do not add a full artifact-manager pane in this packet set.
- The managed/external source-file default is an app preference, defaulting to managed copy.
- Heavy-output nodes are user-controlled. The main quick control is `memory` vs `stored`; advanced settings stay in the inspector.
- This packet set is intentionally sequential because later packets inherit earlier persistence, dialog, and runtime regression anchors.

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

## Handoff Artifacts (Mandatory Per Packet)

- Spec contract: `PROJECT_MANAGED_FILES_Pxx_<name>.md`
- Implementation prompt: `PROJECT_MANAGED_FILES_Pxx_<name>_PROMPT.md`
- Packet wrap-up artifact for each implementation packet: `docs/specs/work_packets/project_managed_files/Pxx_<slug>_WRAPUP.md`
- Status ledger update in [PROJECT_MANAGED_FILES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_STATUS.md):
  - branch label
  - accepted commit sha (or `n/a` when no git metadata is available)
  - command history
  - test summary
  - artifact paths
  - residual risks

## Standard Thread Prompt Shell

`Implement PROJECT_MANAGED_FILES_PXX_<name>.md exactly. Before editing, read PROJECT_MANAGED_FILES_MANIFEST.md, PROJECT_MANAGED_FILES_STATUS.md, and PROJECT_MANAGED_FILES_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve locked defaults and current public graph/shell/QML/runtime contracts unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update PROJECT_MANAGED_FILES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every `*_PROMPT.md` file in this packet set must begin with that shell verbatim except for packet number and filename substitutions.
- Packet-specific notes may be appended after the shell when a packet has extra locked constraints.

## Packet Template Rules

- Every implementation packet spec must include: objective, preconditions, execution dependencies, target subsystems, conservative write scope, required behavior, non-goals, verification commands, review gate, expected artifacts, acceptance criteria, and handoff notes.
- Every prompt must tell a fresh-thread agent to read the manifest, status ledger, and packet spec before editing.
- Every prompt must use the standard thread prompt shell defined above.
- `P00` is documentation-only. `P01` through `P12` may change source/test/docs files, but each thread must implement exactly one packet.
- Execution waves are authoritative. Do not start a later wave until every packet in the current wave is `PASS` or `FAIL`.
- When a later packet changes a packet-owned regression anchor from an earlier wave, that later packet must update the inherited earlier test file in-scope instead of leaving a stale assertion behind.
- Prefer narrow dedicated test modules for new behavior (`tests/test_project_artifact_store.py`, `tests/test_project_artifact_resolution.py`, `tests/test_project_file_issues.py`, `tests/test_project_files_dialog.py`, `tests/test_execution_artifact_refs.py`, and `tests/test_graph_output_mode_ui.py`) and keep later packets reusing those anchors rather than creating duplicates.
- Use the project venv for verification commands (`./venv/Scripts/python.exe`) unless a packet explicitly requires something else.
- This planning/bootstrap thread ends after `P00` is complete. All later packets must be executed in fresh threads using the generated prompt files or the executor skill.
