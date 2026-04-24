# COREX_CLEAN_ARCHITECTURE_RESTRUCTURE P12: Docs Traceability Closeout

## Objective

Close the clean architecture restructure with updated architecture docs, packet traceability, public API notes, QA evidence, and stale launch/import documentation cleanup.

## Model / Context Hint

- Implementation and remediation: `gpt-5.5` with `xhigh`
- Optional exploration: `gpt-5.4-mini` with `xhigh` only for non-editing ownership or insertion-point tracing; Spark only for one exact known-area lookup
- Context scope: manifest, status ledger, this packet spec, assigned worktree, conservative write scope, and docs/tests needed for closeout

## Preconditions

- `P00_bootstrap` is `PASS`.
- `P01` through `P11` are `PASS`.

## Execution Dependencies

- `P01_runtime_contracts`
- `P02_graph_domain_mutation`
- `P03_workspace_custom_workflows`
- `P04_current_schema_persistence`
- `P05_shell_composition`
- `P06_qml_shell_roots`
- `P07_qml_graph_canvas_core`
- `P08_passive_viewer_overlays`
- `P09_nodes_sdk_registry`
- `P10_plugin_addon_descriptor`
- `P11_cross_cutting_services`

## Target Subsystems

- Architecture and spec docs
- Work-packet manifest/status/QA matrix
- Public API and launch docs
- Traceability and markdown hygiene tests

## Conservative Write Scope

- `ARCHITECTURE.md`
- `README.md`
- `docs/GETTING_STARTED.md`
- `docs/PACKAGING_WINDOWS.md`
- `docs/specs/INDEX.md`
- `docs/specs/perf/COREX_CLEAN_ARCHITECTURE_RESTRUCTURE_QA_MATRIX.md`
- `docs/specs/work_packets/corex_clean_architecture_restructure/**`
- `tests/test_traceability_checker.py`
- `tests/test_markdown_hygiene.py`
- `tests/test_run_script.py`
- `docs/specs/work_packets/corex_clean_architecture_restructure/P12_docs_traceability_closeout_WRAPUP.md`

## Required Behavior

- Update architecture documentation to reflect actual final ownership boundaries.
- Update packet status ledger with accepted packet branches, accepted substantive commit SHAs, verification, artifacts, and residual risks.
- Create or update the QA matrix for the packet family.
- Remove stale `main.py` launch expectations where the canonical launch path is `corex-node-editor` / `ea_node_editor.bootstrap:main`.
- Keep docs/index links valid.

## Non-Goals

- Do not make production code changes except tiny stale-doc-test corrections explicitly tied to public launch documentation.
- Do not reopen earlier implementation packets.
- Do not broaden verification beyond closeout/docs unless a closeout test requires it.

## Verification Commands

- `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py tests/test_markdown_hygiene.py tests/test_run_script.py --ignore=venv`
- `.\venv\Scripts\python.exe scripts/check_traceability.py`
- `.\venv\Scripts\python.exe scripts/check_markdown_links.py`

## Review Gate

- `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv`

## Expected Artifacts

- `docs/specs/work_packets/corex_clean_architecture_restructure/P12_docs_traceability_closeout_WRAPUP.md`
- `docs/specs/perf/COREX_CLEAN_ARCHITECTURE_RESTRUCTURE_QA_MATRIX.md`

## Acceptance Criteria

- Architecture docs, index entries, status ledger, QA matrix, and public launch docs match the final packet outcomes.
- Traceability and markdown hygiene pass.
- Verification commands pass or the wrap-up records a terminal failure with residual risk.

## Handoff Notes

Because `ARCHITECTURE.md` and `docs/specs/INDEX.md` may already have user-owned edits, inspect and preserve existing changes before editing.
