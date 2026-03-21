Implement FLOWCHART_CARDINAL_PORTS_P04_flowchart_drop_connect_insert.md exactly. Before editing, read FLOWCHART_CARDINAL_PORTS_MANIFEST.md, FLOWCHART_CARDINAL_PORTS_STATUS.md, and FLOWCHART_CARDINAL_PORTS_P04_flowchart_drop_connect_insert.md. Implement only P04. Stay inside the packet write scope, preserve locked defaults and public graph/node/QML contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create `docs/specs/work_packets/flowchart_cardinal_ports/P04_flowchart_drop_connect_insert_WRAPUP.md`, update FLOWCHART_CARDINAL_PORTS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P04; do not start P05.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/flowchart-cardinal-ports/p04-flowchart-drop-connect-insert`.
- Review Gate: `./venv/Scripts/python.exe -m pytest tests/test_window_library_inspector.py --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/flowchart_cardinal_ports/P04_flowchart_drop_connect_insert_WRAPUP.md`
- This packet owns shell/library/drop-connect neutral flow behavior only. Do not reopen the core neutral-port contract or silhouette-anchor geometry beyond the packet-local side-selection rule it needs to consume.
