Implement GRAPHICS_PERFORMANCE_MODES_P06_node_render_quality_contract.md exactly. Before editing, read GRAPHICS_PERFORMANCE_MODES_MANIFEST.md, GRAPHICS_PERFORMANCE_MODES_STATUS.md, and GRAPHICS_PERFORMANCE_MODES_P06_node_render_quality_contract.md. Implement only P06. Stay inside the packet write scope, preserve locked defaults and public shell/canvas/node SDK contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create `docs/specs/work_packets/graphics_performance_modes/P06_node_render_quality_contract_WRAPUP.md`, update GRAPHICS_PERFORMANCE_MODES_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P06; do not start P07.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/graphics-performance-modes/p06-node-render-quality-contract`.
- Review Gate: `./venv/Scripts/python.exe -m pytest tests/test_registry_validation.py --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/graphics_performance_modes/P06_node_render_quality_contract_WRAPUP.md`
- Keep this packet on SDK/payload contract work. Do not consume the new metadata from QML surfaces yet.
