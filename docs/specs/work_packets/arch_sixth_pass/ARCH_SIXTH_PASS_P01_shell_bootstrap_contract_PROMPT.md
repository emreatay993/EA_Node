Implement ARCH_SIXTH_PASS_P01_shell_bootstrap_contract.md exactly. Before editing, read ARCH_SIXTH_PASS_MANIFEST.md, ARCH_SIXTH_PASS_STATUS.md, and ARCH_SIXTH_PASS_P01_shell_bootstrap_contract.md. Implement only P01. Stay inside the packet write scope, preserve exact user-facing behavior, UI/UX, runtime semantics, and current-schema `.sfe` behavior, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the packet wrap-up, update ARCH_SIXTH_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P01; do not start P02.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/arch-sixth-pass/p01-shell-bootstrap-contract`
- Review Gate: `./venv/Scripts/python.exe -m pytest tests/test_main_bootstrap.py -q`
- Expected artifacts:
  - `docs/specs/work_packets/arch_sixth_pass/P01_shell_bootstrap_contract_WRAPUP.md`
- Keep this packet focused on composition and bootstrap contract cleanup. `P02` owns `ShellWindow` facade reduction.
