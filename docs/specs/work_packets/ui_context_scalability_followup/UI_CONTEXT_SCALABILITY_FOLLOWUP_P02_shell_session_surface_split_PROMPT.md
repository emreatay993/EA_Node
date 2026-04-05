Implement UI_CONTEXT_SCALABILITY_FOLLOWUP_P02_shell_session_surface_split.md exactly. Before editing, read UI_CONTEXT_SCALABILITY_FOLLOWUP_MANIFEST.md, UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md, and UI_CONTEXT_SCALABILITY_FOLLOWUP_P02_shell_session_surface_split.md. Implement only P02. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create `docs/specs/work_packets/ui_context_scalability_followup/P02_shell_session_surface_split_WRAPUP.md`, update UI_CONTEXT_SCALABILITY_FOLLOWUP_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P02; do not start P03.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/ui-context-scalability-followup/p02-shell-session-surface-split`.
- Review Gate: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_shell_project_session_controller.py tests/test_project_save_as_flow.py --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/ui_context_scalability_followup/P02_shell_session_surface_split_WRAPUP.md`
  - `ea_node_editor/ui/shell/window_state/context_properties.py`
  - `ea_node_editor/ui/shell/controllers/project_session_services_support/project_files_service.py`
- Keep `window_state_helpers.py` and `project_session_services.py` as stable facade entrypoints; do not delete or bypass them.
