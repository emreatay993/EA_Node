Implement GRAPHICS_PERFORMANCE_MODES_P05_max_performance_canvas_behavior.md exactly. Before editing, read GRAPHICS_PERFORMANCE_MODES_MANIFEST.md, GRAPHICS_PERFORMANCE_MODES_STATUS.md, and GRAPHICS_PERFORMANCE_MODES_P05_max_performance_canvas_behavior.md. Implement only P05. Stay inside the packet write scope, preserve locked defaults and public shell/canvas/node SDK contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create `docs/specs/work_packets/graphics_performance_modes/P05_max_performance_canvas_behavior_WRAPUP.md`, update GRAPHICS_PERFORMANCE_MODES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P05; do not start P06.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/graphics-performance-modes/p05-max-performance-canvas-behavior`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py --ignore=venv -k "max_performance" -q`
- Expected artifacts:
  - `docs/specs/work_packets/graphics_performance_modes/P05_max_performance_canvas_behavior_WRAPUP.md`
- Keep this packet on whole-canvas behavior only. Do not widen into Node SDK metadata, proxy-surface contracts, or benchmark/docs work.
