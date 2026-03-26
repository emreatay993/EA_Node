# ARCHITECTURE_REFACTOR P13: Docs Release Traceability

## Objective
- Align release packaging/signing truth, the spec index, architecture/requirements docs, traceability, and the final QA matrix with the refactored codebase so documentation stops claiming stale or missing artifacts, and add semantic doc/link guardrails so the same drift is caught automatically.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_refactor/ARCHITECTURE_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_REFACTOR` packet is in progress.

## Execution Dependencies
- `P12`

## Target Subsystems
- `pyproject.toml`
- `ea_node_editor.spec`
- `ARCHITECTURE.md`
- `README.md`
- `docs/GETTING_STARTED.md`
- `docs/PACKAGING_WINDOWS.md`
- `docs/PILOT_RUNBOOK.md`
- `docs/specs/INDEX.md`
- `docs/specs/requirements/*.md`
- `docs/specs/perf/*.md`
- `scripts/build_windows_package.ps1`
- `scripts/build_windows_installer.ps1`
- `scripts/check_markdown_links.py`
- `scripts/sign_release_artifacts.ps1`
- `scripts/verification_manifest.py`
- `scripts/check_traceability.py`
- `tests/test_markdown_hygiene.py`
- `tests/test_packaging_configuration.py`
- `tests/test_traceability_checker.py`
- `tests/test_run_verification.py`
- `tests/test_dead_code_hygiene.py`

## Conservative Write Scope
- `pyproject.toml`
- `ea_node_editor.spec`
- `ARCHITECTURE.md`
- `README.md`
- `docs/GETTING_STARTED.md`
- `docs/PACKAGING_WINDOWS.md`
- `docs/PILOT_RUNBOOK.md`
- `docs/specs/INDEX.md`
- `docs/specs/requirements/*.md`
- `docs/specs/perf/*.md`
- `scripts/build_windows_package.ps1`
- `scripts/build_windows_installer.ps1`
- `scripts/check_markdown_links.py`
- `scripts/sign_release_artifacts.ps1`
- `scripts/verification_manifest.py`
- `scripts/check_traceability.py`
- `tests/test_markdown_hygiene.py`
- `tests/test_packaging_configuration.py`
- `tests/test_traceability_checker.py`
- `tests/test_run_verification.py`
- `tests/test_dead_code_hygiene.py`
- `docs/specs/perf/ARCHITECTURE_REFACTOR_QA_MATRIX.md`
- `docs/specs/work_packets/architecture_refactor/P13_docs_release_traceability_WRAPUP.md`

## Required Behavior
- Reconcile packaging and signing scripts, packaging docs, and package-manifest truth so release instructions match the actual build flow.
- Update `docs/specs/INDEX.md` and related docs so missing or stale packet-set references are removed or restored cleanly rather than left as broken claims.
- Add packet-owned markdown link and canonical-doc drift checks so active docs stop passing traceability while still pointing at stale, missing, or archival-only artifacts.
- Refresh architecture, requirements, and proof docs so the final refactored boundaries are documented without overstating coverage or green status.
- Keep archived process history clearly separated from canonical active docs and QA claims.
- Publish `docs/specs/perf/ARCHITECTURE_REFACTOR_QA_MATRIX.md` with the final approved reruns, focused follow-up commands, and any remaining manual or Windows-only checks.
- Keep documentation aligned with actual shipped scope; do not claim broader runtime, packaging, or UI guarantees than the packet set proved.

## Non-Goals
- No new product behavior beyond doc/script truth cleanup.
- No new feature planning or additional packet sets.
- No further runtime or QML refactors except direct fallout from stale doc or packaging references.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_run_verification.py tests/test_traceability_checker.py tests/test_packaging_configuration.py tests/test_dead_code_hygiene.py tests/test_markdown_hygiene.py --ignore=venv -q`
2. `./venv/Scripts/python.exe scripts/check_traceability.py`
3. `./venv/Scripts/python.exe scripts/check_markdown_links.py`

## Review Gate
- `./venv/Scripts/python.exe scripts/check_traceability.py`

## Expected Artifacts
- `docs/specs/perf/ARCHITECTURE_REFACTOR_QA_MATRIX.md`
- `docs/specs/work_packets/architecture_refactor/P13_docs_release_traceability_WRAPUP.md`

## Acceptance Criteria
- Packaging/signing docs and scripts agree on the actual release flow.
- Spec index and traceability docs no longer claim missing packet sets or stale proof artifacts without resolving them cleanly.
- Markdown-link and canonical-doc guardrails exist and fail when active docs point at stale or missing artifacts.
- `docs/specs/perf/ARCHITECTURE_REFACTOR_QA_MATRIX.md` exists and records the final approved reruns and manual checks.
- The packet-owned verification commands and the traceability and markdown-link checks all pass.

## Handoff Notes
- This is the final packet in the set. The wrap-up must summarize the final proof command set, remaining manual Windows-only checks, and any still-deferred documentation debt explicitly.
