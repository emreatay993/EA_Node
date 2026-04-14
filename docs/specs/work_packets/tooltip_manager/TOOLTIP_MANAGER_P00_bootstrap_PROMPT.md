Implement TOOLTIP_MANAGER_P00_bootstrap.md exactly. Before editing, read TOOLTIP_MANAGER_MANIFEST.md, TOOLTIP_MANAGER_STATUS.md, and TOOLTIP_MANAGER_P00_bootstrap.md. Implement only P00. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact if you rerun bootstrap in a fresh thread, update TOOLTIP_MANAGER_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P00; do not start P01.

Wrap-up and commit requirements for a fresh-thread rerun:
- Create `docs/specs/work_packets/tooltip_manager/P00_bootstrap_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- If the wrap-up or status update lands in a follow-up docs commit, the recorded accepted SHA may still point to the earlier substantive packet commit as long as it remains reachable from the packet branch and the wrap-up `Changed Files` list reflects the full packet-branch diff.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/tooltip-manager/p00-bootstrap` from `main`.
- Review Gate: run the exact `TOOLTIP_MANAGER_P00_STATUS_PASS` inline Python command from `TOOLTIP_MANAGER_P00_bootstrap.md`.
- Expected artifacts:
  - `docs/specs/INDEX.md`
  - `docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_MANIFEST.md`
  - `docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_STATUS.md`
  - `docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_P00_bootstrap.md`
  - `docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_P00_bootstrap_PROMPT.md`
  - `docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_P01_tooltip_preference_and_manager_contract.md`
  - `docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_P01_tooltip_preference_and_manager_contract_PROMPT.md`
  - `docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_P02_view_menu_and_tooltip_surface_adoption.md`
  - `docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_P02_view_menu_and_tooltip_surface_adoption_PROMPT.md`
  - `docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_P03_collision_avoidance_tooltip_copy.md`
  - `docs/specs/work_packets/tooltip_manager/TOOLTIP_MANAGER_P03_collision_avoidance_tooltip_copy_PROMPT.md`
- This packet is documentation-only bootstrap work. Do not edit runtime, shell, bridge, QML, packaging, perf, or requirement files in `P00`.
