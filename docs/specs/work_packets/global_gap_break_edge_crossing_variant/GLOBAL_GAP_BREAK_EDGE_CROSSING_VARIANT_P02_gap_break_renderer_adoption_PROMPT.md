Implement GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_P02_gap_break_renderer_adoption.md exactly. Before editing, read GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_MANIFEST.md, GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_STATUS.md, and GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_P02_gap_break_renderer_adoption.md. Implement only P02. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done, create the required packet wrap-up artifact, update GLOBAL_GAP_BREAK_EDGE_CROSSING_VARIANT_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P02; do not start P03.

Wrap-up and commit requirements:
- Create `docs/specs/work_packets/global_gap_break_edge_crossing_variant/P02_gap_break_renderer_adoption_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/global-gap-break-edge-crossing-variant/p02-gap-break-renderer-adoption` from `main`.
- Keep hit testing, culling, arrowheads, and label anchors on the original edge geometry.
- Do not add `.sfe` persistence fields, per-edge style overrides, or settings-dialog work in this packet.
- Expected artifact: `docs/specs/work_packets/global_gap_break_edge_crossing_variant/P02_gap_break_renderer_adoption_WRAPUP.md`.
