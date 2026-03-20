Implement GRAPHICS_PERFORMANCE_MODES_P07_host_surface_quality_seam.md exactly. Before editing, read GRAPHICS_PERFORMANCE_MODES_MANIFEST.md, GRAPHICS_PERFORMANCE_MODES_STATUS.md, and GRAPHICS_PERFORMANCE_MODES_P07_host_surface_quality_seam.md. Implement only P07. Stay inside the packet write scope, preserve locked defaults and public shell/canvas/node SDK contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create `docs/specs/work_packets/graphics_performance_modes/P07_host_surface_quality_seam_WRAPUP.md`, update GRAPHICS_PERFORMANCE_MODES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P07; do not start P08.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/graphics-performance-modes/p07-host-surface-quality-seam`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_contract.py --ignore=venv -k "render_quality" -q`
- Expected artifacts:
  - `docs/specs/work_packets/graphics_performance_modes/P07_host_surface_quality_seam_WRAPUP.md`
- Keep this packet on the host/surface contract only. Do not start adapting built-in media surfaces here.
