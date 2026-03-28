Implement ARCHITECTURE_MAINTAINABILITY_REFACTOR_P11_graph_canvas_scene_decomposition.md exactly. Before editing, read ARCHITECTURE_MAINTAINABILITY_REFACTOR_MANIFEST.md, ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md, and ARCHITECTURE_MAINTAINABILITY_REFACTOR_P11_graph_canvas_scene_decomposition.md. Implement only P11. Stay inside the packet write scope, preserve documented external contracts and locked defaults, delete packet-owned internal compatibility seams instead of leaving fallback paths behind, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update ARCHITECTURE_MAINTAINABILITY_REFACTOR_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P11; do not start P12.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/architecture-maintainability-refactor/p11-graph-canvas-scene-decomposition`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_contract.py tests/test_passive_graph_surface_host.py --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/architecture_maintainability_refactor/P11_graph_canvas_scene_decomposition_WRAPUP.md`
- Keep the graph-canvas contract stable while decomposing internals. Do not reintroduce retired compatibility names or fallback props as a shortcut.
