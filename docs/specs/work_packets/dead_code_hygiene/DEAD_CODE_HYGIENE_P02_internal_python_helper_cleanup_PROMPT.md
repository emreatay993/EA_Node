Implement DEAD_CODE_HYGIENE_P02_internal_python_helper_cleanup.md exactly. Before editing, read DEAD_CODE_HYGIENE_MANIFEST.md, DEAD_CODE_HYGIENE_STATUS.md, and DEAD_CODE_HYGIENE_P02_internal_python_helper_cleanup.md. Implement only P02. Stay inside the packet write scope, preserve public-looking Python surfaces unless the packet explicitly removes an approved internal dead seam, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create `docs/specs/work_packets/dead_code_hygiene/P02_internal_python_helper_cleanup_WRAPUP.md`, update DEAD_CODE_HYGIENE_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P02; do not start P03.

Wrap-up requirements:
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/dead-code-hygiene/p02-internal-python-helper-cleanup`.
- Review Gate: `./venv/Scripts/python.exe -m pytest tests/test_execution_worker.py tests/test_window_library_inspector.py -q`
- Expected artifacts:
  - `docs/specs/work_packets/dead_code_hygiene/P02_internal_python_helper_cleanup_WRAPUP.md`
- Remove only `dict_to_event_type`, `input_port_is_available`, `inline_body_height`, and the directly adjacent imports made dead by those removals.
- Do not widen into other `vulture` findings or remove public-looking/package-surface symbols such as `AsyncNodePlugin`, `icon_names`, `list_installed_packages`, `uninstall_package`, or package `__init__` re-export surfaces.
