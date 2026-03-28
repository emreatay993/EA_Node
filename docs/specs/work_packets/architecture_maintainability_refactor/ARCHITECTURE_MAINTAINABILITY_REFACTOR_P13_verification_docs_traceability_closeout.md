# ARCHITECTURE_MAINTAINABILITY_REFACTOR P13: Verification Docs Traceability Closeout

## Objective
- Replace brittle string-token architecture checks with parsed or AST-backed checks where practical, eliminate scattered shell-isolation workaround knowledge behind one explicit runner or contract, refresh architecture and traceability docs, and publish the final QA matrix.

## Preconditions
- `P00` is marked `PASS` in [ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/architecture_maintainability_refactor/ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md).
- No later `ARCHITECTURE_MAINTAINABILITY_REFACTOR` packet is in progress.

## Execution Dependencies
- `P12`

## Target Subsystems
- `ARCHITECTURE.md`
- `README.md`
- `docs/specs/INDEX.md`
- `docs/specs/requirements/*.md`
- `docs/specs/perf/*.md`
- `scripts/verification_manifest.py`
- `scripts/run_verification.py`
- `scripts/check_traceability.py`
- `scripts/check_markdown_links.py`
- `tests/test_dead_code_hygiene.py`
- `tests/test_run_verification.py`
- `tests/test_traceability_checker.py`
- `tests/test_markdown_hygiene.py`
- `tests/test_shell_isolation_phase.py`
- `tests/shell_isolation_runtime.py`
- `tests/shell_isolation_main_window_targets.py`
- `tests/shell_isolation_controller_targets.py`

## Conservative Write Scope
- `ARCHITECTURE.md`
- `README.md`
- `docs/specs/INDEX.md`
- `docs/specs/requirements/*.md`
- `docs/specs/perf/*.md`
- `scripts/verification_manifest.py`
- `scripts/run_verification.py`
- `scripts/check_traceability.py`
- `scripts/check_markdown_links.py`
- `tests/test_dead_code_hygiene.py`
- `tests/test_run_verification.py`
- `tests/test_traceability_checker.py`
- `tests/test_markdown_hygiene.py`
- `tests/test_shell_isolation_phase.py`
- `tests/shell_isolation_runtime.py`
- `tests/shell_isolation_main_window_targets.py`
- `tests/shell_isolation_controller_targets.py`
- `docs/specs/perf/ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX.md`
- `docs/specs/work_packets/architecture_maintainability_refactor/P13_verification_docs_traceability_closeout_WRAPUP.md`

## Required Behavior
- Replace packet-owned exact-string or token-fragile architecture checks with parsed-manifest, AST, or similarly structure-aware checks where practical.
- Make shell-isolation ownership explicit through one runner, manifest contract, or similarly centralized proof path rather than scattered workaround knowledge.
- Refresh architecture, requirements, spec-index, and traceability docs so they describe the cleaned architecture and the intentional seam removals without overstating proof.
- Publish `docs/specs/perf/ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX.md` with the final approved reruns, review gates, and remaining manual checks.
- Keep docs aligned with the actual cleaned architecture; do not re-document deleted compatibility seams as if they still exist.

## Non-Goals
- No new product behavior or feature planning.
- No reopening of runtime, QML, graph, or persistence refactors beyond doc/proof fallout.
- No repo-wide verification expansion beyond the packet-owned proof set.

## Verification Commands
1. `./venv/Scripts/python.exe -m pytest tests/test_dead_code_hygiene.py tests/test_run_verification.py tests/test_traceability_checker.py tests/test_markdown_hygiene.py tests/test_shell_isolation_phase.py --ignore=venv -q`
2. `./venv/Scripts/python.exe scripts/check_traceability.py`
3. `./venv/Scripts/python.exe scripts/check_markdown_links.py`

## Review Gate
- `./venv/Scripts/python.exe scripts/check_traceability.py`

## Expected Artifacts
- `docs/specs/perf/ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX.md`
- `docs/specs/work_packets/architecture_maintainability_refactor/P13_verification_docs_traceability_closeout_WRAPUP.md`

## Acceptance Criteria
- Architecture, verification, and traceability guardrails stop depending on brittle string-token checks where a more structural proof is practical.
- Shell-isolation ownership is centralized and clearly documented.
- `docs/specs/perf/ARCHITECTURE_MAINTAINABILITY_REFACTOR_QA_MATRIX.md` exists and records the final approved reruns and manual checks.
- The packet-owned verification commands and traceability/link checks pass.

## Handoff Notes
- This is the final packet in the set. The wrap-up must summarize the final proof command set, any remaining manual checks, and any intentionally deferred verification debt explicitly.
