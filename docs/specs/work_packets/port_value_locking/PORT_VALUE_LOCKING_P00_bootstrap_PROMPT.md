Implement PORT_VALUE_LOCKING_P00_bootstrap.md exactly. Before editing, read PORT_VALUE_LOCKING_MANIFEST.md, PORT_VALUE_LOCKING_STATUS.md, and PORT_VALUE_LOCKING_P00_bootstrap.md. Implement only P00. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact if you rerun bootstrap in a fresh thread, update PORT_VALUE_LOCKING_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P00; do not start P01.

Wrap-up and commit requirements for a fresh-thread rerun:
- Create `docs/specs/work_packets/port_value_locking/P00_bootstrap_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/port-value-locking/p00-bootstrap` from `main`.
- Review Gate: run the exact `PORT_VALUE_LOCKING_P00_STATUS_PASS` inline Python command from `PORT_VALUE_LOCKING_P00_bootstrap.md`.
- Expected artifacts:
  - `.gitignore`
  - `docs/specs/INDEX.md`
  - `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_MANIFEST.md`
  - `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_STATUS.md`
  - `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P00_bootstrap.md`
  - `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P00_bootstrap_PROMPT.md`
  - `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P01_state_contract_and_persistence.md`
  - `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P01_state_contract_and_persistence_PROMPT.md`
  - `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P02_mutation_semantics_and_locked_port_invariants.md`
  - `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P02_mutation_semantics_and_locked_port_invariants_PROMPT.md`
  - `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P03_payload_projection_and_view_filters.md`
  - `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P03_payload_projection_and_view_filters_PROMPT.md`
  - `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P04_locked_port_qml_ux.md`
  - `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P04_locked_port_qml_ux_PROMPT.md`
  - `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P05_canvas_hide_gestures.md`
  - `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P05_canvas_hide_gestures_PROMPT.md`
  - `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P06_verification_docs_traceability_closeout.md`
  - `docs/specs/work_packets/port_value_locking/PORT_VALUE_LOCKING_P06_verification_docs_traceability_closeout_PROMPT.md`
- This packet is documentation-only bootstrap work, including the `.gitignore` allowlist updates needed to keep packet docs, future wrap-ups, and the future QA matrix trackable.
