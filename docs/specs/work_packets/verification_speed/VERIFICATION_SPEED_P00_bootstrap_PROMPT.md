Implement VERIFICATION_SPEED_P00_bootstrap.md exactly. Before editing, read VERIFICATION_SPEED_MANIFEST.md, VERIFICATION_SPEED_STATUS.md, and VERIFICATION_SPEED_P00_bootstrap.md. Implement only P00. Stay inside the packet write scope, preserve the current shell-isolation defaults unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact if you rerun bootstrap in a fresh thread, update VERIFICATION_SPEED_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P00; do not start P01.

Wrap-up requirements for a fresh-thread rerun:
- Create `docs/specs/work_packets/verification_speed/P00_bootstrap_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/verification-speed/p00-bootstrap`.
- Review Gate: run the exact `VERIFICATION_SPEED_P00_STATUS_PASS` inline Python command from `VERIFICATION_SPEED_P00_bootstrap.md`
- Expected artifacts:
  - `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_MANIFEST.md`
  - `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_STATUS.md`
  - `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P00_bootstrap.md`
  - `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P00_bootstrap_PROMPT.md`
  - `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P01_pytest_selection_classification.md`
  - `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P01_pytest_selection_classification_PROMPT.md`
  - `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P02_shell_wrapper_collection_hygiene.md`
  - `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P02_shell_wrapper_collection_hygiene_PROMPT.md`
  - `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P03_hybrid_verification_runner.md`
  - `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P03_hybrid_verification_runner_PROMPT.md`
  - `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P04_gui_wait_helper_cleanup.md`
  - `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P04_gui_wait_helper_cleanup_PROMPT.md`
  - `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P05_docs_traceability.md`
  - `docs/specs/work_packets/verification_speed/VERIFICATION_SPEED_P05_docs_traceability_PROMPT.md`
- This packet is documentation-only bootstrap work.
- Do not widen into test, runner, or requirement-document changes.
