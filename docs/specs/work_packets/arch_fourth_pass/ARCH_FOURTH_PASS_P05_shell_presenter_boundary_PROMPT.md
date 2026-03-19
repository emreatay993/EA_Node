Implement ARCH_FOURTH_PASS_P05_shell_presenter_boundary.md exactly. Before editing, read ARCH_FOURTH_PASS_MANIFEST.md, ARCH_FOURTH_PASS_STATUS.md, and ARCH_FOURTH_PASS_P05_shell_presenter_boundary.md. Implement only P05. Stay inside the packet write scope, preserve public shell/QML contracts unless the packet explicitly introduces a compatibility replacement, run the full Verification Commands, run the Review Gate before marking the packet done, create `docs/specs/work_packets/arch_fourth_pass/P05_shell_presenter_boundary_WRAPUP.md`, update ARCH_FOURTH_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P05; do not start P06.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/arch-fourth-pass/p05-shell-presenter-boundary`
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_bootstrap -v`
- Expected artifacts:
  - `docs/specs/work_packets/arch_fourth_pass/P05_shell_presenter_boundary_WRAPUP.md`
- Keep this packet focused on presenter/state ownership. Do not widen into packet-owned QML compatibility removal yet.
