Implement ARCHITECTURE_FOLLOWUP_REFACTOR_P01_shell_composition_root_collapse.md exactly. Before editing, read ARCHITECTURE_FOLLOWUP_REFACTOR_MANIFEST.md, ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md, and ARCHITECTURE_FOLLOWUP_REFACTOR_P01_shell_composition_root_collapse.md. Implement only P01. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update ARCHITECTURE_FOLLOWUP_REFACTOR_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P01; do not start P02.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- Create `docs/specs/work_packets/architecture_followup_refactor/P01_shell_composition_root_collapse_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/architecture-followup-refactor/p01-shell-composition-root-collapse`.
- Review Gate: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_main_bootstrap.py tests/main_window_shell/shell_runtime_contracts.py --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/architecture_followup_refactor/P01_shell_composition_root_collapse_WRAPUP.md`
- After this packet, `ShellWindow` should be lifecycle-first and host-first. Do not keep packet-owned shell composition or convenience-command surfaces on the host.
