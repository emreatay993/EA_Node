Implement GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P02_expand_collision_avoidance.md exactly. Before editing, read GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_MANIFEST.md, GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_STATUS.md, and GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P02_expand_collision_avoidance.md. Implement only P02. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done, create the required packet wrap-up artifact, update GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P02; do not start P03.

Wrap-up and commit requirements:
- Create `docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/P02_expand_collision_avoidance_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/global-expand-collision-avoidance-and-comment-peek/p02-expand-collision-avoidance` from `main`.
- Keep scope on the graph-scene mutation path, grouped history application, occupied-bounds computation, and packet-owned regression anchors only.
- Do not implement comment peek mode or any lock or pin model here.
- Expected artifact: `docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/P02_expand_collision_avoidance_WRAPUP.md`.
