Implement PROJECT_MANAGED_FILES_P00_bootstrap.md exactly. Before editing, read PROJECT_MANAGED_FILES_MANIFEST.md, PROJECT_MANAGED_FILES_STATUS.md, and PROJECT_MANAGED_FILES_P00_bootstrap.md. Implement only P00. Stay inside the packet write scope, preserve locked defaults and current public graph/shell/QML/runtime contracts unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact if you rerun bootstrap in a fresh thread, update PROJECT_MANAGED_FILES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P00; do not start P01.

Wrap-up and commit requirements for a fresh-thread rerun:
- Create `docs/specs/work_packets/project_managed_files/P00_bootstrap_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/project-managed-files/p00-bootstrap`.
- Review Gate: run the exact `PROJECT_MANAGED_FILES_P00_STATUS_PASS` inline Python command from `PROJECT_MANAGED_FILES_P00_bootstrap.md`.
- Expected artifacts:
  - `.gitignore`
  - `docs/specs/INDEX.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_MANIFEST.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_STATUS.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P00_bootstrap.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P00_bootstrap_PROMPT.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P01_artifact_store_foundation.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P01_artifact_store_foundation_PROMPT.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P02_media_resolution_adoption.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P02_media_resolution_adoption_PROMPT.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P03_staging_recovery_lifecycle.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P03_staging_recovery_lifecycle_PROMPT.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P04_save_promotion_prune.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P04_save_promotion_prune_PROMPT.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P05_save_as_copy_flow.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P05_save_as_copy_flow_PROMPT.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P06_source_import_defaults.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P06_source_import_defaults_PROMPT.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P07_file_issue_node_repair.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P07_file_issue_node_repair_PROMPT.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P08_project_files_summary.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P08_project_files_summary_PROMPT.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P09_execution_artifact_refs.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P09_execution_artifact_refs_PROMPT.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P10_generated_output_adoption.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P10_generated_output_adoption_PROMPT.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P11_process_run_output_mode_ui.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P11_process_run_output_mode_ui_PROMPT.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P12_docs_traceability_qa.md`
  - `docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_P12_docs_traceability_qa_PROMPT.md`
- This packet is documentation-only bootstrap work, including the `.gitignore` allowlist updates needed to keep the packet docs and future QA matrix trackable.
