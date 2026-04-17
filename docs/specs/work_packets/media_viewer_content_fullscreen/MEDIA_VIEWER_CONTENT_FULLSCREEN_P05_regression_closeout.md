# MEDIA_VIEWER_CONTENT_FULLSCREEN P05: Regression Closeout

## Objective

- Lock the integrated media/viewer fullscreen behavior with focused regression coverage, QA evidence, manual smoke directives, and traceability updates after `P01` through `P04` are complete.

## Preconditions

- `P00` is marked `PASS` in [MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md](./MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md).
- `P01` is marked `PASS` in [MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md](./MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md).
- `P02` is marked `PASS` in [MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md](./MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md).
- `P03` is marked `PASS` in [MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md](./MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md).
- `P04` is marked `PASS` in [MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md](./MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md).
- No later `MEDIA_VIEWER_CONTENT_FULLSCREEN` packet is in progress.

## Execution Dependencies

- `P01`
- `P02`
- `P03`
- `P04`

## Target Subsystems

- `tests/test_content_fullscreen_bridge.py`
- `tests/test_shell_window_lifecycle.py`
- `tests/test_graph_surface_input_controls.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_viewer_surface_contract.py`
- `tests/test_viewer_host_service.py`
- `tests/test_embedded_viewer_overlay_manager.py`
- `docs/specs/perf/MEDIA_VIEWER_CONTENT_FULLSCREEN_QA_MATRIX.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/70_INTEGRATIONS.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/INDEX.md`

## Conservative Write Scope

- `tests/test_content_fullscreen_bridge.py`
- `tests/test_shell_window_lifecycle.py`
- `tests/test_graph_surface_input_controls.py`
- `tests/test_graph_surface_input_contract.py`
- `tests/test_viewer_surface_contract.py`
- `tests/test_viewer_host_service.py`
- `tests/test_embedded_viewer_overlay_manager.py`
- `docs/specs/perf/MEDIA_VIEWER_CONTENT_FULLSCREEN_QA_MATRIX.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/70_INTEGRATIONS.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/INDEX.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/MEDIA_VIEWER_CONTENT_FULLSCREEN_STATUS.md`
- `docs/specs/work_packets/media_viewer_content_fullscreen/P05_regression_closeout_WRAPUP.md`

## Required Behavior

- Add or adjust only focused regression coverage needed to prove the integrated media/viewer fullscreen path after `P01` through `P04`.
- Prefer updating inherited packet-owned tests when they are the canonical regression anchor. Do not duplicate identical assertions in a new file.
- Verify that fullscreen remains transient and is absent from project persistence.
- Verify the media overlay path for image and PDF payloads, crop-mode suppression, close paths, and background interaction blocking.
- Verify viewer fullscreen retarget/restore behavior, blocked viewer fallback, workspace switch cleanup, and no orphaned native viewer state.
- Review shortcut conflicts for `F11` and ensure the behavior remains content fullscreen only.
- Publish `docs/specs/perf/MEDIA_VIEWER_CONTENT_FULLSCREEN_QA_MATRIX.md` with automated verification, manual smoke checklist, residual risks, and packet evidence links.
- Update requirement and traceability docs only where needed to reflect the shipped fullscreen behavior.
- Add the QA matrix link to `docs/specs/INDEX.md` if it is not already present.
- Keep this packet as regression/docs closeout. Do not perform broad implementation refactors.

## Non-Goals

- No new product feature beyond the behavior already delivered by `P01` through `P04`.
- No broad UI refactor.
- No new viewer backend.
- No new persistence schema.
- No packet doc generation outside the wrap-up/status/QA artifacts listed here.

## Verification Commands

1. `$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_content_fullscreen_bridge.py tests/test_shell_window_lifecycle.py tests/test_graph_surface_input_controls.py tests/test_graph_surface_input_contract.py tests/test_viewer_surface_contract.py tests/test_viewer_host_service.py tests/test_embedded_viewer_overlay_manager.py --ignore=venv -q`
2. `.\venv\Scripts\python.exe -m pytest tests/test_traceability_checker.py --ignore=venv -q`
3. `.\venv\Scripts\python.exe scripts/check_traceability.py`

## Review Gate

- `.\venv\Scripts\python.exe scripts/check_traceability.py`

## Expected Artifacts

- `docs/specs/work_packets/media_viewer_content_fullscreen/P05_regression_closeout_WRAPUP.md`
- `docs/specs/perf/MEDIA_VIEWER_CONTENT_FULLSCREEN_QA_MATRIX.md`

## Acceptance Criteria

- The targeted fullscreen regression command passes.
- Traceability tests and `scripts/check_traceability.py` pass.
- The QA matrix records automated verification, manual smoke directives, produced artifacts, and residual risks.
- Requirement and traceability docs reference the content fullscreen behavior without introducing unrelated requirement churn.
- The packet wrap-up clearly states whether manual smoke remains pending or completed.

## Handoff Notes

- This is the final packet. It must not start new implementation work that belongs in `P01` through `P04`.
- If a regression failure requires source changes outside this packet's write scope, stop and report the required handoff instead of silently expanding scope.
