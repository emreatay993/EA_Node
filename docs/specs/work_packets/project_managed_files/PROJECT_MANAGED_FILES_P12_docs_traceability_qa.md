# PROJECT_MANAGED_FILES P12: Docs Traceability QA

## Objective
- Refresh architecture, requirements, traceability, and packet-scoped QA evidence so the shipped managed-file and large-data artifact model is documented and the final regression commands are captured in a durable matrix.

## Preconditions
- `P00` is marked `PASS` in [PROJECT_MANAGED_FILES_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_STATUS.md).
- No later `PROJECT_MANAGED_FILES` packet is in progress.

## Execution Dependencies
- `P01`
- `P02`
- `P03`
- `P04`
- `P05`
- `P06`
- `P07`
- `P08`
- `P09`
- `P10`
- `P11`

## Target Subsystems
- `ARCHITECTURE.md`
- `docs/specs/INDEX.md`
- `docs/specs/requirements/10_ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/40_NODE_SDK.md`
- `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`
- `docs/specs/requirements/50_EXECUTION_ENGINE.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/perf/PROJECT_MANAGED_FILES_QA_MATRIX.md`
- `tests/test_traceability_checker.py`

## Conservative Write Scope
- `ARCHITECTURE.md`
- `docs/specs/INDEX.md`
- `docs/specs/requirements/10_ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/40_NODE_SDK.md`
- `docs/specs/requirements/45_NODE_EXECUTION_MODEL.md`
- `docs/specs/requirements/50_EXECUTION_ENGINE.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/perf/PROJECT_MANAGED_FILES_QA_MATRIX.md`
- `tests/test_traceability_checker.py`
- `docs/specs/work_packets/project_managed_files/P12_docs_traceability_qa_WRAPUP.md`

## Required Behavior
- Update architecture and requirements docs so the final shipped behavior is explicitly covered:
  - `.sfe` plus sibling `<project-stem>.data/`
  - additive `metadata.artifact_store`
  - staging-first lifecycle, explicit-save promotion, and Save As self-contained copy default
  - source import defaults and node-level repair UX
  - compact project-files dialog/summaries
  - runtime artifact refs and the Process Run `memory` versus `stored` adopter
- Update the traceability matrix so the new requirements and packet-owned regression anchors are connected clearly.
- Add `docs/specs/perf/PROJECT_MANAGED_FILES_QA_MATRIX.md` with the approved packet-scoped regression commands and any remaining manual QA checks.
- Keep the docs aligned with the actual shipped packet scope; do not invent a full artifact-manager platform, automatic size-based storage, or broader heavy-data UI than `P11`.
- Run the packet-owned final regression and traceability checks instead of widening into unrelated full-repo verification.

## Non-Goals
- No new runtime or UI behavior beyond documentation and QA close-out.
- No new packet planning or feature expansion.
- No new artifact-management scope beyond what `P01` through `P11` actually ship.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_project_artifact_store.py tests/test_project_artifact_resolution.py tests/test_pdf_preview_provider.py tests/test_project_save_as_flow.py tests/test_app_preferences_import_defaults.py tests/test_project_file_issues.py tests/test_project_files_dialog.py tests/test_execution_artifact_refs.py tests/test_integrations_track_f.py tests/test_process_run_node.py tests/test_graph_output_mode_ui.py tests/test_shell_project_session_controller.py --ignore=venv -q`
2. `./venv/Scripts/python.exe scripts/check_traceability.py`

## Review Gate
- `./venv/Scripts/python.exe scripts/check_traceability.py`

## Expected Artifacts
- `docs/specs/perf/PROJECT_MANAGED_FILES_QA_MATRIX.md`
- `docs/specs/work_packets/project_managed_files/P12_docs_traceability_qa_WRAPUP.md`

## Acceptance Criteria
- Architecture and requirement docs accurately describe the final managed-file/artifact design and shipped user-facing UX.
- The traceability matrix covers the new requirement anchors and packet-owned regression files.
- `docs/specs/perf/PROJECT_MANAGED_FILES_QA_MATRIX.md` exists and records the final approved regression commands/manual checks.
- The packet-owned final regression command passes, and `scripts/check_traceability.py` passes.

## Handoff Notes
- This is the final packet in the set. The wrap-up must summarize the final regression commands, QA matrix, and any residual manual checks that still matter before merge.
- If the docs intentionally narrow or defer any future heavy-data scope, call that out explicitly in the wrap-up so follow-on packet sets have a clean starting point.
