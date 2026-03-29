Implement CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P04_dpf_widget_binder_transport_adoption.md exactly. Before editing, read CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_MANIFEST.md, CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md, and CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_P04_dpf_widget_binder_transport_adoption.md. Implement only P04. Stay inside the packet write scope, preserve documented external contracts and locked defaults, run the full Verification Commands, run the Review Gate before marking the packet done when it is not `none`, create the required packet wrap-up artifact, update CROSS_PROCESS_VIEWER_BACKEND_FRAMEWORK_STATUS.md with branch label, accepted commit sha, commands, tests, artifacts, and residual risks, commit packet-local changes on the packet branch when you own the final substantive state, and stop after P04; do not start P05.

During development and remediation, prefer the narrowest packet-owned rerun and do not substitute broader repo-wide verification when the packet-local commands already prove the work.

Wrap-up and commit requirements:
- Create `docs/specs/work_packets/cross_process_viewer_backend_framework/P04_dpf_widget_binder_transport_adoption_WRAPUP.md`.
- In `Implementation Summary`, start with `Packet`, `Branch Label`, `Commit Owner`, `Commit SHA`, `Changed Files`, and `Artifacts Produced`.
- Treat `Commit Owner` as a packet-contract token (`worker`, `executor`, or `executor-pending`), not a username or email address.
- Record `Commit SHA` as the full 40-character SHA from `git rev-parse HEAD` for the substantive packet commit, not `HEAD`, `pending`, or placeholder prose.
- Commit the substantive packet changes first, capture `git rev-parse HEAD`, then write or update the wrap-up and status ledger using that real SHA.
- End `Verification` with `Final Verification Verdict: PASS` or `Final Verification Verdict: FAIL`.
- Begin `Ready for Integration` with `Yes:` or `No:`.

Notes:
- Target branch: `codex/cross-process-viewer-backend-framework/p04-dpf-widget-binder-transport-adoption` from `main`.
- Review Gate: `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_dpf_viewer_widget_binder.py --ignore=venv -q`
- Expected artifacts:
  - `docs/specs/work_packets/cross_process_viewer_backend_framework/P04_dpf_widget_binder_transport_adoption_WRAPUP.md`
  - `ea_node_editor/ui_qml/viewer_host*.py`
  - `ea_node_editor/ui_qml/viewer_widget_binder*.py`
  - `ea_node_editor/ui_qml/dpf_viewer*.py`
  - `tests/test_embedded_viewer_overlay_manager.py`
  - `tests/test_viewer_host_service.py`
  - `tests/test_dpf_viewer_widget_binder.py`
- This packet owns the first concrete binder implementation. Do not start bridge copy changes or project-load blocker work here.
