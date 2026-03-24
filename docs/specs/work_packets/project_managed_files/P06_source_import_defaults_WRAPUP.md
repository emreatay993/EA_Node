# P06 Source Import Defaults Wrap-Up

## Implementation Summary

- Packet: `P06`
- Branch Label: `codex/project-managed-files/p06-source-import-defaults`
- Commit Owner: `worker`
- Commit SHA: `efa8cc29ad512c374e413ceec7261199500de4e2`
- Changed Files: `ea_node_editor/app_preferences.py`, `ea_node_editor/settings.py`, `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`, `ea_node_editor/ui/shell/host_presenter.py`, `tests/test_app_preferences_import_defaults.py`, `tests/test_graph_surface_input_contract.py`, `tests/test_pdf_preview_provider.py`, `docs/specs/work_packets/project_managed_files/P06_source_import_defaults_WRAPUP.md`
- Artifacts Produced: `docs/specs/work_packets/project_managed_files/P06_source_import_defaults_WRAPUP.md`, `ea_node_editor/app_preferences.py`, `ea_node_editor/settings.py`, `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`, `ea_node_editor/ui/shell/host_presenter.py`, `tests/test_app_preferences_import_defaults.py`, `tests/test_graph_surface_input_contract.py`, `tests/test_pdf_preview_provider.py`
- Preference Key: `source_import.default_mode`
- Default Value: `managed_copy`

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_app_preferences_import_defaults.py tests/test_graph_surface_input_contract.py tests/test_pdf_preview_provider.py --ignore=venv -q`
- PASS: `./venv/Scripts/python.exe -m pytest tests/test_app_preferences_import_defaults.py --ignore=venv -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Ready for manual testing.

- Prerequisite: launch this branch with a writable project location and leave `source_import.default_mode` unset in `app_preferences.json` to exercise the default.
- Managed-copy default: add an Image Panel or PDF Panel, browse a local source file, and confirm the property stores an `artifact-stage://...` ref while the preview still resolves immediately.
- External-link override: set `source_import.default_mode` in `app_preferences.json` to `external_link`, restart the app, browse the same source property again, and confirm it stores the raw file path instead of an artifact ref.
- Managed re-import replacement: with a saved project that already has a managed image or PDF source, browse the same property again and confirm the node keeps a single staged ref for that logical source instead of accumulating multiple staged entries.

## Residual Risks

- Source import routing currently keys off the existing source-property labels (`Image Source`, `PDF Source`, and `File Path`), so later source-like nodes must reuse those labels or extend the mapping deliberately.
- There is still no in-app UI for toggling the preference; until a later packet exposes one, changing the default outside tests requires editing `app_preferences.json`.

## Ready for Integration

- Yes: packet-owned code, preference normalization, and import-flow regressions are committed and passing within the P06 write scope.
