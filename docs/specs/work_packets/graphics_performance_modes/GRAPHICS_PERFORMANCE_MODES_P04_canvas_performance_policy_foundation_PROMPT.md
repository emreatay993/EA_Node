Implement GRAPHICS_PERFORMANCE_MODES_P04_canvas_performance_policy_foundation.md exactly. Before editing, read GRAPHICS_PERFORMANCE_MODES_MANIFEST.md, GRAPHICS_PERFORMANCE_MODES_STATUS.md, and GRAPHICS_PERFORMANCE_MODES_P04_canvas_performance_policy_foundation.md. Implement only P04. Stay inside the packet write scope, preserve locked defaults and public shell/canvas/node SDK contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create `docs/specs/work_packets/graphics_performance_modes/P04_canvas_performance_policy_foundation_WRAPUP.md`, update GRAPHICS_PERFORMANCE_MODES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P04; do not start P05.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/graphics-performance-modes/p04-canvas-performance-policy-foundation`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flow_edge_labels.py --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/graphics_performance_modes/P04_canvas_performance_policy_foundation_WRAPUP.md`
- Keep this packet on policy/state plumbing and invisible full-fidelity optimization only. Do not apply whole-canvas max-performance simplifications yet.
