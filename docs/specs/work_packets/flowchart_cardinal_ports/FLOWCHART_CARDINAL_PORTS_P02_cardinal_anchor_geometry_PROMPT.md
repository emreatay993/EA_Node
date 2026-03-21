Implement FLOWCHART_CARDINAL_PORTS_P02_cardinal_anchor_geometry.md exactly. Before editing, read FLOWCHART_CARDINAL_PORTS_MANIFEST.md, FLOWCHART_CARDINAL_PORTS_STATUS.md, and FLOWCHART_CARDINAL_PORTS_P02_cardinal_anchor_geometry.md. Implement only P02. Stay inside the packet write scope, preserve locked defaults and public graph/node/QML contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create `docs/specs/work_packets/flowchart_cardinal_ports/P02_cardinal_anchor_geometry_WRAPUP.md`, update FLOWCHART_CARDINAL_PORTS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P02; do not start P03.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/flowchart-cardinal-ports/p02-cardinal-anchor-geometry`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_flowchart_surfaces.py --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/flowchart_cardinal_ports/P02_cardinal_anchor_geometry_WRAPUP.md`
- This packet owns geometry, host rendering, and edge-anchor updates only. Do not widen into gesture-order connect logic or shell quick-insert/drop-connect behavior.
