Implement GRAPHICS_PERFORMANCE_MODES_P01_preferences_runtime_contract.md exactly. Before editing, read GRAPHICS_PERFORMANCE_MODES_MANIFEST.md, GRAPHICS_PERFORMANCE_MODES_STATUS.md, and GRAPHICS_PERFORMANCE_MODES_P01_preferences_runtime_contract.md. Implement only P01. Stay inside the packet write scope, preserve locked defaults and public shell/canvas/node SDK contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create `docs/specs/work_packets/graphics_performance_modes/P01_preferences_runtime_contract_WRAPUP.md`, update GRAPHICS_PERFORMANCE_MODES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P01; do not start P02.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/graphics-performance-modes/p01-preferences-runtime-contract`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/main_window_shell/bridge_contracts.py --ignore=venv -k "graphics" -q`
- Expected artifacts:
  - `docs/specs/work_packets/graphics_performance_modes/P01_preferences_runtime_contract_WRAPUP.md`
- This packet owns additive schema/runtime plumbing only. Do not widen into dialog UI, quick-toggle UI, canvas behavior changes, or Node SDK render-quality work.
