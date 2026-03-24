# Project Managed Files QA Matrix

- Updated: `2026-03-24`
- Packet set: `PROJECT_MANAGED_FILES` (`P01` through `P12`)
- Scope: final closeout matrix for the shipped project-managed file, staged-output, and lightweight repair UX model.

## Locked Scope

- `.sfe` remains the canonical project document; saved projects may add a sibling `<project-stem>.data/` sidecar.
- `metadata.artifact_store` is additive only and stores managed/staged maps plus optional staging-root hints.
- Managed/staged refs persist as `artifact://<artifact_id>` and `artifact-stage://<artifact_id>` string values inside ordinary project and node fields.
- Managed imports and stored outputs stage first; explicit Save promotes only referenced staged items, rewrites promoted refs, and prunes orphaned permanent managed files.
- Save As always prompts and defaults to a self-contained copy of referenced managed files without copying staged scratch data.
- The shipped UX is limited to source-import defaults, node-level repair affordances, save/open/recovery prompts, and `Project Files...`; there is no full artifact-manager pane.
- Runtime artifact refs are shipped only where `P09` through `P11` adopted them. Quick heavy-output UI stays limited to `Process Run` `memory` / `stored`.

## Final Regression Commands

| Coverage Area | Primary Requirement Anchors | Command | Expected Coverage |
|---|---|---|---|
| Final packet regression | `REQ-ARCH-014`, `REQ-UI-028`, `REQ-NODE-022`, `REQ-NODE-023`, `REQ-EXEC-010`, `REQ-PERSIST-015`, `REQ-QA-021` | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_project_artifact_store.py tests/test_project_artifact_resolution.py tests/test_pdf_preview_provider.py tests/test_project_save_as_flow.py tests/test_app_preferences_import_defaults.py tests/test_project_file_issues.py tests/test_project_files_dialog.py tests/test_execution_artifact_refs.py tests/test_integrations_track_f.py tests/test_process_run_node.py tests/test_graph_output_mode_ui.py tests/test_shell_project_session_controller.py --ignore=venv -q` | Revalidates the shipped managed-file architecture end to end: artifact-store layout and resolver behavior, save/save-as promotion rules, source-import defaults, repair/project-files UX, runtime artifact refs, managed output writers, and `Process Run` stored transcripts |
| Proof audit / review gate | `REQ-ARCH-015`, `REQ-QA-022` | `./venv/Scripts/python.exe scripts/check_traceability.py` | Confirms the refreshed architecture, requirements, QA matrix, and traceability docs stay aligned with the published proof layer |

## Focused Narrow Reruns

| Coverage Area | Command | When To Use It |
|---|---|---|
| Artifact-store foundation and resolver seams | `./venv/Scripts/python.exe -m pytest tests/test_project_artifact_store.py tests/test_project_artifact_resolution.py --ignore=venv -q` | Use before the final aggregate rerun when edits only touch sidecar layout, metadata normalization, or resolver behavior |
| Save/open/recovery prompts plus project-files summary | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_project_save_as_flow.py tests/test_project_file_issues.py tests/test_project_files_dialog.py tests/test_shell_project_session_controller.py --ignore=venv -q` | Use for dialog copy-choice, repair affordance, save/open prompt text, or project-files summary changes |
| Runtime artifact refs and managed output writers | `./venv/Scripts/python.exe -m pytest tests/test_execution_artifact_refs.py tests/test_integrations_track_f.py tests/test_process_run_node.py --ignore=venv -q` | Use for runtime payload shape, in-run path resolution, or blank-output managed writer changes |
| `Process Run` inline output-mode surface | `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_process_run_node.py tests/test_graph_output_mode_ui.py --ignore=venv -q` | Use for `memory` / `stored` behavior, chip wording, or quick-toggle presentation changes |

## 2026-03-24 Execution Results

| Command | Result | Notes |
|---|---|---|
| `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_project_artifact_store.py tests/test_project_artifact_resolution.py tests/test_pdf_preview_provider.py tests/test_project_save_as_flow.py tests/test_app_preferences_import_defaults.py tests/test_project_file_issues.py tests/test_project_files_dialog.py tests/test_execution_artifact_refs.py tests/test_integrations_track_f.py tests/test_process_run_node.py tests/test_graph_output_mode_ui.py tests/test_shell_project_session_controller.py --ignore=venv -q` | PASS | Final packet regression rerun passed in the project venv and kept the managed-file scope aligned with the shipped `P01` through `P11` behavior |
| `./venv/Scripts/python.exe scripts/check_traceability.py` | PASS | Review-gate proof audit passed after the architecture, requirements, QA matrix, and traceability refresh |

## Remaining Manual Smoke Checks

1. Save/open/recovery: open a project that contains managed media plus staged output, confirm the prompt summary reports staged and broken counts correctly, and verify `Project Files...` lists managed files, staged items, and any broken entries.
2. Save As default: choose the default self-contained copy for a project with referenced managed files and at least one staged ref; confirm the new `<project-stem>.data/` includes the referenced managed files while `.staging/` scratch is not copied.
3. `Process Run` stored mode: switch the inline control from `memory` to `stored`, run a successful command and confirm downstream file-based nodes can consume the staged transcript, then run a failing command and confirm no reusable failed transcript ref remains.

## Future-Scope Deferrals

- This branch still does not ship a full artifact-manager pane, artifact history, or automatic size-based storage policy.
- Quick heavy-output UI remains packet-scoped to `Process Run`; later adopters must add their own explicit UX instead of inheriting it implicitly.
- Blank `Excel Write` output still defaults to a staged CSV artifact; `.xlsx` and `.xlsm` continue to require an explicit output path.
