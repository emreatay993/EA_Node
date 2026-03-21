Implement FLOWCHART_CARDINAL_PORTS_P01_neutral_port_contract.md exactly. Before editing, read FLOWCHART_CARDINAL_PORTS_MANIFEST.md, FLOWCHART_CARDINAL_PORTS_STATUS.md, and FLOWCHART_CARDINAL_PORTS_P01_neutral_port_contract.md. Implement only P01. Stay inside the packet write scope, preserve locked defaults and public graph/node/QML contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create `docs/specs/work_packets/flowchart_cardinal_ports/P01_neutral_port_contract_WRAPUP.md`, update FLOWCHART_CARDINAL_PORTS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P01; do not start P02.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/flowchart-cardinal-ports/p01-neutral-port-contract`.
- Review Gate: `./venv/Scripts/python.exe -m pytest tests/test_passive_flowchart_catalog.py --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/flowchart_cardinal_ports/P01_neutral_port_contract_WRAPUP.md`
- This packet owns the neutral flowchart port contract and graph-core acceptance only. Do not widen into anchor geometry, QML wire-drag behavior, or shell quick-insert/drop-connect flows.
