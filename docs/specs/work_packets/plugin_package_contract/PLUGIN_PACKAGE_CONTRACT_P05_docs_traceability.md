# PLUGIN_PACKAGE_CONTRACT P05: Docs And Traceability

## Objective
- Update developer-facing docs and traceability references so the repo describes the repaired `.eanp` contract truthfully and records the focused regression proof that now protects it.

## Preconditions
- `P00` through `P04` are marked `PASS` in [PLUGIN_PACKAGE_CONTRACT_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/plugin_package_contract/PLUGIN_PACKAGE_CONTRACT_STATUS.md).
- No later `PLUGIN_PACKAGE_CONTRACT` packet is in progress.

## Execution Dependencies
- `P04`

## Target Subsystems
- `README.md`
- `docs/GETTING_STARTED.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/work_packets/plugin_package_contract/PLUGIN_PACKAGE_CONTRACT_STATUS.md`
- packet-owned wrap-up/doc outputs under `docs/specs/work_packets/plugin_package_contract/`

## Conservative Write Scope
- `README.md`
- `docs/GETTING_STARTED.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/work_packets/plugin_package_contract/PLUGIN_PACKAGE_CONTRACT_STATUS.md`
- `docs/specs/work_packets/plugin_package_contract/P05_docs_traceability_WRAPUP.md`

## Required Behavior
- Update docs so raw single-file plugin drop-ins, installed `.eanp` package layout, and export/import expectations all match the repaired implementation.
- Correct the current README overclaim that Export Node Package bundles selected nodes unless `P04` makes that exact behavior true.
- Update traceability references so the package contract points at the repaired modules and focused tests.
- Keep the closeout packet scoped to documentation, traceability, and packet-owned status/wrap-up artifacts.

## Non-Goals
- No source-code changes under `ea_node_editor/**`.
- No new package-contract behavior changes.
- No broad verification-runner or shell-isolation workflow changes.

## Verification Commands
1. `./venv/Scripts/python.exe scripts/check_traceability.py`
2. `./venv/Scripts/python.exe -m pytest -n auto tests/test_plugin_loader.py tests/test_package_manager.py tests/test_node_package_io_ops.py -q`

## Review Gate
- `git diff --check -- README.md docs/GETTING_STARTED.md docs/specs/requirements/TRACEABILITY_MATRIX.md docs/specs/work_packets/plugin_package_contract/PLUGIN_PACKAGE_CONTRACT_STATUS.md`

## Expected Artifacts
- `docs/specs/work_packets/plugin_package_contract/P05_docs_traceability_WRAPUP.md`

## Acceptance Criteria
- Package docs describe the actual supported import/export contract after `P04`.
- Traceability checks pass through the project venv.
- Focused package-contract regressions pass through the project venv.

## Handoff Notes
- This is the packet-set closeout. Record any intentionally unsupported export scope, migration caveat, or package backward-compatibility limitation as residual risk instead of leaving the docs ambiguous.
