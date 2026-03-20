Implement GRAPHICS_PERFORMANCE_MODES_P03_status_strip_quick_toggle.md exactly. Before editing, read GRAPHICS_PERFORMANCE_MODES_MANIFEST.md, GRAPHICS_PERFORMANCE_MODES_STATUS.md, and GRAPHICS_PERFORMANCE_MODES_P03_status_strip_quick_toggle.md. Implement only P03. Stay inside the packet write scope, preserve locked defaults and public shell/canvas/node SDK contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create `docs/specs/work_packets/graphics_performance_modes/P03_status_strip_quick_toggle_WRAPUP.md`, update GRAPHICS_PERFORMANCE_MODES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P03; do not start P04.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/graphics-performance-modes/p03-status-strip-quick-toggle`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/main_window_shell/shell_runtime_contracts.py --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/graphics_performance_modes/P03_status_strip_quick_toggle_WRAPUP.md`
- Keep this packet focused on the shell quick-toggle surface and the already-approved persistence path. Do not start canvas behavior work here.
