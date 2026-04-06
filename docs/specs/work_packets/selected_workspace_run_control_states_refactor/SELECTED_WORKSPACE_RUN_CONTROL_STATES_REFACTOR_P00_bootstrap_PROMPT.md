Implement SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_P00_bootstrap.md exactly. Before editing, read SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_MANIFEST.md, SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_STATUS.md, and SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_P00_bootstrap.md. Implement only P00. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done, create or update the packet docs exactly as required, update SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, and stop after P00; do not start P01.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Notes:
- Target branch: `codex/selected-workspace-run-control-states-refactor/p00-bootstrap`.
- Review Gate: `@'... SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_P00_STATUS_PASS ...'@ | .\venv\Scripts\python.exe -`
- Expected artifacts include `.gitignore`, the spec-index update, the manifest, the status ledger, and the packet specs or prompts for `P00` through `P04`.
- Stop after the bootstrap packet; do not implement any later packet here.
