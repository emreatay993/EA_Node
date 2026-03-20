Implement GRAPHICS_PERFORMANCE_MODES_P02_graphics_settings_mode_ui.md exactly. Before editing, read GRAPHICS_PERFORMANCE_MODES_MANIFEST.md, GRAPHICS_PERFORMANCE_MODES_STATUS.md, and GRAPHICS_PERFORMANCE_MODES_P02_graphics_settings_mode_ui.md. Implement only P02. Stay inside the packet write scope, preserve locked defaults and public shell/canvas/node SDK contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create `docs/specs/work_packets/graphics_performance_modes/P02_graphics_settings_mode_ui_WRAPUP.md`, update GRAPHICS_PERFORMANCE_MODES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P02; do not start P03.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/graphics-performance-modes/p02-graphics-settings-mode-ui`.
- Review Gate: `./venv/Scripts/python.exe -m pytest tests/test_graphics_settings_dialog.py --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/graphics_performance_modes/P02_graphics_settings_mode_ui_WRAPUP.md`
- Keep this packet focused on the Graphics Settings modal. Do not add the status-strip toggle or any mode-specific canvas behavior here.
