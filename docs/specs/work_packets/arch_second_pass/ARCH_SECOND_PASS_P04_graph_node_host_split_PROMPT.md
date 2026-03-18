Implement ARCH_SECOND_PASS_P04_graph_node_host_split.md exactly. Before editing, read ARCH_SECOND_PASS_MANIFEST.md, ARCH_SECOND_PASS_STATUS.md, and ARCH_SECOND_PASS_P04_graph_node_host_split.md. Implement only P04. Stay inside the packet write scope, preserve public QML/object contracts unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done, create `docs/specs/work_packets/arch_second_pass/P04_graph_node_host_split_WRAPUP.md`, update ARCH_SECOND_PASS_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P04; do not start P05.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/arch-second-pass/p04-graph-node-host-split`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_passive_graph_surface_host.PassiveGraphSurfaceHostTests.test_graph_node_host_routes_body_click_open_and_context_from_below_surface_layer -v`
- Expected artifacts:
  - `docs/specs/work_packets/arch_second_pass/P04_graph_node_host_split_WRAPUP.md`
- Keep the packet tightly focused on host decomposition. Do not widen into media-surface or inspector-pane cleanup here.
