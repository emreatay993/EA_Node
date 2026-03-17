Implement VERIFICATION_SPEED_P02_shell_wrapper_collection_hygiene.md exactly. Before editing, read VERIFICATION_SPEED_MANIFEST.md, VERIFICATION_SPEED_STATUS.md, and VERIFICATION_SPEED_P02_shell_wrapper_collection_hygiene.md. Implement only P02. Stay inside the packet write scope, preserve the current shell-isolation defaults unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done, create `docs/specs/work_packets/verification_speed/P02_shell_wrapper_collection_hygiene_WRAPUP.md`, update VERIFICATION_SPEED_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P02; do not start P03.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/verification-speed/p02-shell-wrapper-collection-hygiene`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest --collect-only -q tests/test_shell_project_session_controller.py`
- Expected artifacts:
  - `docs/specs/work_packets/verification_speed/P02_shell_wrapper_collection_hygiene_WRAPUP.md`
- Preserve the repo's `unittest` wrapper strategy and subprocess behavior.
- Do not widen into marker rollout, runner scripting, or shell-runtime changes.
