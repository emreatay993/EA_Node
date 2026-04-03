Implement ARCHITECTURE_RESIDUAL_REFACTOR_P07_shared_runtime_contract_extraction.md exactly. Before editing, read ARCHITECTURE_RESIDUAL_REFACTOR_MANIFEST.md, ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md, and ARCHITECTURE_RESIDUAL_REFACTOR_P07_shared_runtime_contract_extraction.md. Implement only P07. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update ARCHITECTURE_RESIDUAL_REFACTOR_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P07; do not start P08.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- Create `docs/specs/work_packets/architecture_residual_refactor/P07_shared_runtime_contract_extraction_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/architecture-residual-refactor/p07-shared-runtime-contract-extraction`.
- Review Gate: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_plugin_loader.py tests/test_execution_viewer_service.py --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/architecture_residual_refactor/P07_shared_runtime_contract_extraction_WRAPUP.md`
- Keep documented node SDK imports stable while moving packet-owned internals onto the neutral runtime-contract layer.
