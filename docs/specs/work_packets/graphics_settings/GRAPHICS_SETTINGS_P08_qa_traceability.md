# GRAPHICS_SETTINGS P08: QA + Traceability

## Objective
- Register the finished graphics-settings feature set in the requirements and traceability docs, then run the final regression gate.

## Preconditions
- `P07` is marked `PASS` in [GRAPHICS_SETTINGS_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graphics_settings/GRAPHICS_SETTINGS_STATUS.md).
- All earlier graphics-settings packets are already `PASS`.

## Target Subsystems
- `docs/specs/requirements/10_ARCHITECTURE.md`
- `docs/specs/requirements/20_UI_UX.md`
- `docs/specs/requirements/60_PERSISTENCE.md`
- `docs/specs/requirements/90_QA_ACCEPTANCE.md`
- `docs/specs/requirements/TRACEABILITY_MATRIX.md`
- `docs/specs/work_packets/graphics_settings/GRAPHICS_SETTINGS_STATUS.md`

## Required Behavior
- Add these exact new requirement IDs and keep their text aligned to the shipped feature set:
  - `REQ-ARCH-012`: app-wide graphics/theme preferences shall be exposed through a dedicated preferences controller/store and consumed by both QWidget and QML shell surfaces without breaking existing shell/graph canvas integration contracts.
  - `REQ-UI-016`: `ShellWindow` shall expose `show_graphics_settings_dialog()` and the Settings menu shall provide an app-wide Graphics Settings modal covering grid, minimap, snap-to-grid default, and theme selection.
  - `REQ-UI-017`: shell and graph canvas surfaces shall support live application of shared theme tokens for `stitch_dark` and `stitch_light`.
  - `REQ-PERSIST-011`: app-wide graphics preferences shall persist in a versioned app-preferences JSON document under `user_data_dir()` and shall remain separate from `.sfe` project metadata and `last_session.json`.
  - `REQ-QA-009`: a graphics-settings regression gate shall cover app-preferences persistence, settings dialogs, shell menu wiring, theme application, and canvas preference behavior.
- Add these exact new acceptance IDs:
  - `AC-REQ-UI-016-01`: accepting Graphics Settings updates runtime graphics behavior and reopening the application restores the persisted preferences.
  - `AC-REQ-UI-017-01`: `stitch_dark` and `stitch_light` both render shell and graph-canvas surfaces without breaking existing shell/canvas contracts.
  - `AC-REQ-PERSIST-011-01`: app-preferences round-trip preserves graphics settings and does not serialize them into `.sfe` project metadata or `last_session.json`.
  - `AC-REQ-QA-009-01`: `venv/Scripts/python.exe -m unittest tests.test_serializer tests.test_graphics_settings_preferences tests.test_graphics_settings_dialog tests.test_settings_dialog_rc2 tests.test_theme_shell_rc2 tests.test_graph_track_b tests.test_main_window_shell tests.test_shell_project_session_controller -v` passes without regressions.
- Update `TRACEABILITY_MATRIX.md` with implementation/test artifact mappings for the new requirement and acceptance IDs.
- Run the final regression gate command exactly as defined above.
- Do not start another packet set from this thread.

## Non-Goals
- No new feature development beyond requirement/traceability alignment and regression verification.
- No packet-set bootstrap for unrelated follow-on work.

## Verification Commands
1. `venv\Scripts\python.exe -m unittest tests.test_serializer tests.test_graphics_settings_preferences tests.test_graphics_settings_dialog tests.test_settings_dialog_rc2 tests.test_theme_shell_rc2 tests.test_graph_track_b tests.test_main_window_shell tests.test_shell_project_session_controller -v`

## Acceptance Criteria
- The new requirement and acceptance IDs are present in the correct requirement modules.
- `TRACEABILITY_MATRIX.md` maps each new ID to concrete implementation/test artifacts.
- The final regression command passes and is recorded in `GRAPHICS_SETTINGS_STATUS.md`.

## Handoff Notes
- This packet closes the GRAPHICS_SETTINGS packet set.
- Stop after updating the status ledger; do not start any new packet in the same thread.
