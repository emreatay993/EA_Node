# P01 Settings Defaults Boundary Wrap-Up

## Implementation Summary

- Added a neutral shared-defaults module at `ea_node_editor/graph_theme_defaults.py` and moved `DEFAULT_GRAPH_THEME_ID` ownership there so `ea_node_editor/settings.py` no longer imports from `ea_node_editor.ui.graph_theme`.
- Repointed `ea_node_editor/ui/graph_theme/registry.py` to consume and re-export the shared default constant, preserving the existing public UI import surface.
- Repointed `ea_node_editor/ui/shell/controllers/app_preferences_controller.py` to use the neutral default constant while leaving app-preferences normalization, versions, and document shape unchanged.
- Updated preference tests to assert against the current locked defaults shape instead of a stale partial literal.
- Stabilized `tests/test_shell_project_session_controller.py` by running each `ShellWindow` scenario in a fresh subprocess; this avoids a Windows/QML access violation when the suite constructs multiple shell windows sequentially in one interpreter.
- Per the task constraint, `SHELL_SCENE_BOUNDARY_STATUS.md` was not modified.

## Verification

- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graphics_settings_preferences tests.test_graph_theme_preferences tests.test_shell_project_session_controller -v`
  Result: PASS (`21` tests, `14.791s`)
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_theme_preferences.GraphThemePreferencesTests.test_v1_preferences_normalize_to_v2_graph_theme_defaults -v`
  Result: PASS
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -X faulthandler -m unittest tests.test_shell_project_session_controller -v`
  Result: PASS after the subprocess-isolation test harness change (`7` tests, `15.220s`). Before that harness change, the same suite exposed a Windows access violation in `ea_node_editor/ui/shell/window.py::_build_qml_shell` during the second in-process `ShellWindow()` construction.

## Manual Test Directives

Ready for manual testing

- Launch the application normally and confirm the main shell loads without a QML/UI load error dialog.
- In the existing graphics/preferences UI, change one canvas toggle such as grid or minimap visibility, then restart the app and confirm the setting persists.
- In the same preferences flow, switch between shell theme follow/default graph-theme behavior and a manually selected graph theme, restart, and confirm the restored theme state matches what was saved.
- If you can use a disposable preferences file/profile, start once with no existing app-preferences document and confirm the app boots cleanly with the default shell-theme and graph-theme pairing.

## Residual Risks

- The shell-session unittest coverage now relies on subprocess isolation because sequential in-process `ShellWindow()` construction still triggers a Windows/QML access violation in `_build_qml_shell`. That lifetime issue is outside the P01 code boundary and remains for later investigation if shared-process coverage becomes necessary.
- No broader non-packet regression slice was run here; `P10` still owns the wider boundary regression pass.

## Ready for Integration

Yes. P01 is ready for integration within its packet scope.
