Implement PROJECT_MANAGED_FILES_P01_artifact_store_foundation.md exactly. Before editing, read PROJECT_MANAGED_FILES_MANIFEST.md, PROJECT_MANAGED_FILES_STATUS.md, and PROJECT_MANAGED_FILES_P01_artifact_store_foundation.md. Implement only P01. Stay inside the packet write scope, preserve locked defaults and current public graph/shell/QML/runtime contracts unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update PROJECT_MANAGED_FILES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P01; do not start P02.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/project-managed-files/p01-artifact-store-foundation`.
- Review Gate: `./venv/Scripts/python.exe -m pytest tests/test_project_artifact_store.py tests/test_project_artifact_resolution.py --ignore=venv -q`
- Expected artifacts:
  - `ea_node_editor/persistence/artifact_store.py`
  - `ea_node_editor/persistence/artifact_refs.py`
  - `ea_node_editor/persistence/artifact_resolution.py`
  - `tests/test_project_artifact_store.py`
  - `tests/test_project_artifact_resolution.py`
  - `docs/specs/work_packets/project_managed_files/P01_artifact_store_foundation_WRAPUP.md`
- Keep this packet at the contract/foundation level. Do not widen into media adoption, staging recovery, save promotion, or execution payload changes.
