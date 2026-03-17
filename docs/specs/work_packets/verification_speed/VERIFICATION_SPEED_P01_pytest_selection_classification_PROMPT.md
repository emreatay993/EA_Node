Implement VERIFICATION_SPEED_P01_pytest_selection_classification.md exactly. Before editing, read VERIFICATION_SPEED_MANIFEST.md, VERIFICATION_SPEED_STATUS.md, and VERIFICATION_SPEED_P01_pytest_selection_classification.md. Implement only P01. Stay inside the packet write scope, preserve the current shell-isolation defaults unless the packet explicitly changes one, run the full Verification Commands, run the Review Gate before marking the packet done, create `docs/specs/work_packets/verification_speed/P01_pytest_selection_classification_WRAPUP.md`, update VERIFICATION_SPEED_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P01; do not start P02.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/verification-speed/p01-pytest-selection-classification`.
- Review Gate: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_shell_theme.py tests/test_passive_graph_surface_host.py --collect-only -q -m gui`
- Expected artifacts:
  - `docs/specs/work_packets/verification_speed/P01_pytest_selection_classification_WRAPUP.md`
- Keep the change centralized in `tests/conftest.py`; do not hand-mark many modules unless a narrowly justified exception is unavoidable.
- Do not widen into shell-wrapper suppression, runner orchestration, or wait-helper cleanup.
