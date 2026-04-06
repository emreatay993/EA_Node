Implement SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_P04_qml_toolbar_workspace_run_states.md exactly. Before editing, read SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_MANIFEST.md, SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_STATUS.md, and SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_P04_qml_toolbar_workspace_run_states.md. Implement only P04. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update SELECTED_WORKSPACE_RUN_CONTROL_STATES_REFACTOR_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P04.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- Create `docs/specs/work_packets/selected_workspace_run_control_states_refactor/P04_qml_toolbar_workspace_run_states_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/selected-workspace-run-control-states-refactor/p04-qml-toolbar-workspace-run-states`.
- Review Gate: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_qml_boundaries.py::ShellWorkspaceBridgeQmlBoundaryTests --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/selected_workspace_run_control_states_refactor/P04_qml_toolbar_workspace_run_states_WRAPUP.md`
- Do not broaden the QML boundary command to the whole `bridge_qml_boundaries.py` file; unrelated `GraphCanvasQmlBoundaryTests` are outside this packet's proof surface.
