Implement FLOWCHART_CARDINAL_PORTS_P00_bootstrap.md exactly. Before editing, read FLOWCHART_CARDINAL_PORTS_MANIFEST.md, FLOWCHART_CARDINAL_PORTS_STATUS.md, and FLOWCHART_CARDINAL_PORTS_P00_bootstrap.md. Implement only P00. Stay inside the packet write scope, preserve locked defaults and public graph/node/QML contracts unless the packet explicitly changes them, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact if you rerun bootstrap in a fresh thread, update FLOWCHART_CARDINAL_PORTS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P00; do not start P01.

Wrap-up requirements for a fresh-thread rerun:
- Create `docs/specs/work_packets/flowchart_cardinal_ports/P00_bootstrap_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/flowchart-cardinal-ports/p00-bootstrap`.
- Review Gate: run the exact `FLOWCHART_CARDINAL_PORTS_P00_STATUS_PASS` inline Python command from `FLOWCHART_CARDINAL_PORTS_P00_bootstrap.md`.
- Expected artifacts:
  - `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_MANIFEST.md`
  - `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_STATUS.md`
  - `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P00_bootstrap.md`
  - `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P00_bootstrap_PROMPT.md`
  - `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P01_neutral_port_contract.md`
  - `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P01_neutral_port_contract_PROMPT.md`
  - `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P02_cardinal_anchor_geometry.md`
  - `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P02_cardinal_anchor_geometry_PROMPT.md`
  - `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P03_canvas_neutral_interaction.md`
  - `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P03_canvas_neutral_interaction_PROMPT.md`
  - `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P04_flowchart_drop_connect_insert.md`
  - `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P04_flowchart_drop_connect_insert_PROMPT.md`
  - `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P05_regression_docs_traceability.md`
  - `docs/specs/work_packets/flowchart_cardinal_ports/FLOWCHART_CARDINAL_PORTS_P05_regression_docs_traceability_PROMPT.md`
- This packet is documentation-only bootstrap work.
