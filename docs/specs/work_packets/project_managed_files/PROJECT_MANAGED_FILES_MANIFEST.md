# PROJECT_MANAGED_FILES Work Packet Manifest

- Date: `2026-03-25`
- Published packet window: `P10` through `P12`
- Local archive: older `PROJECT_MANAGED_FILES` packet docs (`P00` through `P09`) and the tracked `pydpf_viewer_v1` wrap-ups were moved to `artifacts/work_packet_archive/2026-03-25/` and are intentionally ignored by Git.
- Scope baseline: keep `.sfe` as the canonical project file while layering managed source assets, staged generated outputs, save-time promotion/pruning, crash-only staged-data recovery, lightweight project-file UX, runtime artifact refs, and one concrete heavy-output adopter without turning the app into a full artifact manager.
- Canonical requirements: [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md)

## Retained Packet Order

1. `PROJECT_MANAGED_FILES_P10_generated_output_adoption.md`
2. `PROJECT_MANAGED_FILES_P11_process_run_output_mode_ui.md`
3. `PROJECT_MANAGED_FILES_P12_docs_traceability_qa.md`

## Branch Labels

| Packet | Branch Label | Intent |
|---|---|---|
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

## Retained Handoff Artifacts

- Spec contract: `PROJECT_MANAGED_FILES_P10_generated_output_adoption.md`, `PROJECT_MANAGED_FILES_P11_process_run_output_mode_ui.md`, `PROJECT_MANAGED_FILES_P12_docs_traceability_qa.md`
- Implementation prompts: matching `*_PROMPT.md` files for `P10` through `P12`
- Packet wrap-ups: `P10_generated_output_adoption_WRAPUP.md`, `P11_process_run_output_mode_ui_WRAPUP.md`, and `P12_docs_traceability_qa_WRAPUP.md`
- Status ledger: [PROJECT_MANAGED_FILES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_STATUS.md)

## Standard Thread Prompt Shell

`Implement PROJECT_MANAGED_FILES_PXX_<name>.md exactly. Before editing, read PROJECT_MANAGED_FILES_MANIFEST.md, PROJECT_MANAGED_FILES_STATUS.md, and PROJECT_MANAGED_FILES_PXX_<name>.md. Implement only PXX. Stay inside the packet write scope, preserve locked defaults and current public graph/shell/QML/runtime contracts unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done when it is not \`none\`, create the required packet wrap-up artifact, update PROJECT_MANAGED_FILES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after PXX; do not start PXX+1.`

- Every retained `*_PROMPT.md` file in this packet window begins with that shell except for packet number and filename substitutions.
- Earlier packet specs remain archived locally for historical reference; the public branch now carries only the retained packet window.
