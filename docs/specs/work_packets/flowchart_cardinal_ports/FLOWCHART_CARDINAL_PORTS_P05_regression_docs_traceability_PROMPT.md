Implement FLOWCHART_CARDINAL_PORTS_P05_regression_docs_traceability.md exactly. Before editing, read FLOWCHART_CARDINAL_PORTS_MANIFEST.md, FLOWCHART_CARDINAL_PORTS_STATUS.md, and FLOWCHART_CARDINAL_PORTS_P05_regression_docs_traceability.md. Implement only P05. Stay inside the packet write scope, preserve locked defaults and public graph/node/QML contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create `docs/specs/work_packets/flowchart_cardinal_ports/P05_regression_docs_traceability_WRAPUP.md`, update FLOWCHART_CARDINAL_PORTS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P05.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/flowchart-cardinal-ports/p05-regression-docs-traceability`.
- Review Gate: `./venv/Scripts/python.exe scripts/check_traceability.py`
- Expected artifacts:
  - `docs/specs/work_packets/flowchart_cardinal_ports/P05_regression_docs_traceability_WRAPUP.md`
- This packet owns docs, fixture, and final focused regression/traceability alignment only. Do not introduce new runtime behavior in this packet.
