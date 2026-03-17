Implement VERIFICATION_SPEED_P03_hybrid_verification_runner.md exactly. Before editing, read VERIFICATION_SPEED_MANIFEST.md, VERIFICATION_SPEED_STATUS.md, and VERIFICATION_SPEED_P03_hybrid_verification_runner.md. Implement only P03. Stay inside the packet write scope, preserve the current shell-isolation defaults unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done, create `docs/specs/work_packets/verification_speed/P03_hybrid_verification_runner_WRAPUP.md`, update VERIFICATION_SPEED_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P03; do not start P04.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/verification-speed/p03-hybrid-verification-runner`.
- Review Gate: `./venv/Scripts/python.exe scripts/run_verification.py --mode full --dry-run`
- Expected artifacts:
  - `docs/specs/work_packets/verification_speed/P03_hybrid_verification_runner_WRAPUP.md`
- Keep the script repo-owned and venv-first.
- Do not widen into doc updates, marker rollout, or baseline serializer repair.
