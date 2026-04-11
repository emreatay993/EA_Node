Implement PORT_VALUE_LOCKING_P04_locked_port_qml_ux.md exactly. Before editing, read PORT_VALUE_LOCKING_MANIFEST.md, PORT_VALUE_LOCKING_STATUS.md, and PORT_VALUE_LOCKING_P04_locked_port_qml_ux.md. Implement only P04. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done, create the required packet wrap-up artifact, update PORT_VALUE_LOCKING_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P04; do not start P05.

Wrap-up and commit requirements:
- Create `docs/specs/work_packets/port_value_locking/P04_locked_port_qml_ux_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch label: `codex/port-value-locking/p04-locked-port-qml-ux`.
- Keep this packet on locked-row visuals, manual double-click routing, and locked port interaction suppression only.
- Do not add empty-canvas gesture handling here.
- Expected artifact: `docs/specs/work_packets/port_value_locking/P04_locked_port_qml_ux_WRAPUP.md`.
