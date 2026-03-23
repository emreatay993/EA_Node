# PROJECT_MANAGED_FILES P00: Bootstrap

## Objective
- Establish the `PROJECT_MANAGED_FILES` packet set, initialize the status ledger, register the packet docs in the canonical spec index, and ensure the packet directory is not git-ignored.

## Preconditions
- The canonical spec index exists at [docs/specs/INDEX.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/INDEX.md).
- No `project_managed_files` packet set exists yet under `docs/specs/work_packets/`.

## Execution Dependencies
- none

## Target Subsystems
- `docs/specs/work_packets/project_managed_files/*`
- `docs/specs/INDEX.md`
- `.gitignore`

## Conservative Write Scope
- `.gitignore`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/project_managed_files/**`

## Required Behavior
- Create `docs/specs/work_packets/project_managed_files/`.
- Add `PROJECT_MANAGED_FILES_MANIFEST.md` and `PROJECT_MANAGED_FILES_STATUS.md`.
- Add packet spec and prompt files for `P00` through `P12` using the canonical naming convention.
- Update `docs/specs/INDEX.md` with links to the `PROJECT_MANAGED_FILES` manifest and status ledger.
- Update `.gitignore` so the new packet directory and the future `docs/specs/perf/PROJECT_MANAGED_FILES_QA_MATRIX.md` file are trackable.
- Mark `P00` as `PASS` in `PROJECT_MANAGED_FILES_STATUS.md` and leave `P01` through `P12` as `PENDING`.
- Keep packet order, branch labels, execution waves, locked defaults, review-gate structure, and wrap-up expectations aligned with the approved project-managed-files plan.
- Make no runtime, source, test, or requirement-doc changes outside the documentation bootstrap scope.

## Non-Goals
- No changes under `ea_node_editor/**`.
- No changes under `tests/**`.
- No changes under `scripts/**`.
- No changes to requirements, QA docs, fixtures, `README.md`, or `ARCHITECTURE.md` in this packet.

## Verification Commands
1. `./venv/Scripts/python.exe - <<'PY'
from pathlib import Path
import subprocess

slugs = [
    "P00_bootstrap",
    "P01_artifact_store_foundation",
    "P02_media_resolution_adoption",
    "P03_staging_recovery_lifecycle",
    "P04_save_promotion_prune",
    "P05_save_as_copy_flow",
    "P06_source_import_defaults",
    "P07_file_issue_node_repair",
    "P08_project_files_summary",
    "P09_execution_artifact_refs",
    "P10_generated_output_adoption",
    "P11_process_run_output_mode_ui",
    "P12_docs_traceability_qa",
]
required = [
    "docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_MANIFEST.md",
    "docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_STATUS.md",
]
for slug in slugs:
    required.append(f"docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_{slug}.md")
    required.append(f"docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_{slug}_PROMPT.md")
missing = [path for path in required if not Path(path).exists()]
if missing:
    print("MISSING: " + ", ".join(missing))
    raise SystemExit(1)
for tracked_path in (
    "docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_MANIFEST.md",
    "docs/specs/perf/PROJECT_MANAGED_FILES_QA_MATRIX.md",
):
    check = subprocess.run(
        ["git", "check-ignore", tracked_path],
        capture_output=True,
        text=True,
    )
    if check.returncode == 0:
        print("IGNORED: " + tracked_path)
        raise SystemExit(1)
index_text = Path("docs/specs/INDEX.md").read_text(encoding="utf-8")
for needle in (
    "PROJECT_MANAGED_FILES Work Packet Manifest",
    "PROJECT_MANAGED_FILES Status Ledger",
):
    if needle not in index_text:
        print("INDEX_MISSING: " + needle)
        raise SystemExit(1)
print("PROJECT_MANAGED_FILES_P00_FILE_GATE_PASS")
PY`

## Review Gate
- `./venv/Scripts/python.exe - <<'PY'
from pathlib import Path
text = Path("docs/specs/work_packets/project_managed_files/PROJECT_MANAGED_FILES_STATUS.md").read_text(encoding="utf-8")
if "| P00 Bootstrap | `codex/project-managed-files/p00-bootstrap` | PASS |" not in text:
    raise SystemExit(1)
print("PROJECT_MANAGED_FILES_P00_STATUS_PASS")
PY`

## Expected Artifacts
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

## Acceptance Criteria
- The verification command returns `PROJECT_MANAGED_FILES_P00_FILE_GATE_PASS`.
- The review gate returns `PROJECT_MANAGED_FILES_P00_STATUS_PASS`.
- `PROJECT_MANAGED_FILES_STATUS.md` shows `P00` as `PASS` and every later packet as `PENDING`.
- The only modified tracked paths are `.gitignore`, `docs/specs/INDEX.md`, and the new `project_managed_files` packet docs.

## Handoff Notes
- This thread stops after `P00` bootstrap. Do not continue with `P01` here.
- The next execution thread begins with `P01`.
