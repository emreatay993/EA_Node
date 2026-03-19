Implement ARCH_FIFTH_PASS_P03_shell_controller_surface_split.md exactly. Before editing, read ARCH_FIFTH_PASS_MANIFEST.md, ARCH_FIFTH_PASS_STATUS.md, and ARCH_FIFTH_PASS_P03_shell_controller_surface_split.md. Implement only P03. Stay inside the packet write scope, preserve exact user-facing behavior, UI/UX, and performance, preserve current-schema `.sfe` behavior while treating pre-current-schema compatibility exactly as the packet specifies, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the packet wrap-up, update ARCH_FIFTH_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P03; do not start P04.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/arch-fifth-pass/p03-shell-controller-surface-split`
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_workspace_library_controller_unit.py -q`
- Expected artifacts:
  - `docs/specs/work_packets/arch_fifth_pass/P03_shell_controller_surface_split_WRAPUP.md`
- Keep `WorkspaceLibraryController` as a compatibility facade in this packet. `P04` and `P05` own the bridge/QML call-site migration.
