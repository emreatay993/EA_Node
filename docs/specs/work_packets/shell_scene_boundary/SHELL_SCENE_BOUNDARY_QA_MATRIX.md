# SHELL_SCENE_BOUNDARY QA Matrix

## Approved Regression Commands

1. `P10 closeout aggregate`
   Command: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graphics_settings_preferences tests.test_graph_theme_preferences tests.test_shell_project_session_controller tests.test_main_window_shell tests.test_shell_run_controller tests.test_workspace_library_controller_unit tests.test_graph_track_b tests.test_inspector_reflection tests.test_graph_surface_input_contract tests.test_graph_surface_input_inline tests.test_passive_graph_surface_host tests.test_passive_property_editors tests.test_passive_image_nodes tests.test_flow_edge_labels tests.test_flowchart_surfaces tests.test_graph_theme_shell tests.test_pdf_preview_provider -v`
   Coverage: closeout aggregate for settings/theme normalization, shell/QML host loading, workspace/run/inspector bridge flows, GraphCanvas boundary behavior, graph-scene scope/mutation/payload ownership, and passive graph-surface/media paths touched by the refactor.
   Result: PASS on `2026-03-17` (`288` tests, `217.110s`).

2. `P01 settings/theme defaults`
   Command: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graphics_settings_preferences tests.test_graph_theme_preferences tests.test_shell_project_session_controller -v`
   Coverage: app-preferences graphics normalization, graph-theme default normalization, and project/session isolation from app-wide settings.

3. `P02 QML context bootstrap`
   Command: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell tests.test_graph_scene_bridge_bind_regression -v`
   Coverage: QML host registration, context bootstrap, shell bridge registration, and bind/regression coverage for the initial boundary split.

4. `P03 shell library/search bridge`
   Command: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell tests.test_workspace_library_controller_unit -v`
   Coverage: node-library search/filter flows, graph search overlay routing, quick-insert and hint bridge behavior, and workspace-library controller integration.

5. `P04 shell workspace/run bridge`
   Command: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell tests.test_shell_run_controller tests.test_workspace_manager tests.test_script_editor_dock -v`
   Coverage: workspace tabs, run/title/console flows, script-editor bridge ownership, and shell-backed controller integration.

6. `P05 shell inspector bridge`
   Command: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_inspector_reflection tests.test_passive_property_editors tests.test_main_window_shell -v`
   Coverage: inspector property reflection, exposed-port presentation, passive property editor modes, and inspector QML boundary routing.

7. `P06 GraphCanvas boundary bridge`
   Command: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_main_window_shell tests.test_workspace_library_controller_unit tests.test_graph_surface_input_contract tests.test_passive_graph_surface_host -v`
   Coverage: GraphCanvas host integration, shell-owned canvas bridge routing, graph-surface input ownership contract, and passive-host drag/discoverability behavior.

8. `P07 graph-scene scope/selection split`
   Command: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_scene_bridge_bind_regression tests.test_graph_track_b tests.test_inspector_reflection tests.test_main_window_shell -v`
   Coverage: workspace binding, scope path, selection updates, bounds helpers, and shell/scene interactions that depend on scope navigation.

9. `P08 graph-scene mutation/history split`
   Command: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_track_b tests.test_graph_surface_input_inline tests.test_passive_property_editors tests.test_passive_image_nodes -v`
   Coverage: mutation/layout/history grouping, inline graph-surface editing, passive property flows, and image-panel mutation paths.

10. `P09 graph-scene payload/theme/media split`
    Command: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_flow_edge_labels tests.test_flowchart_surfaces tests.test_graph_theme_shell tests.test_passive_visual_metadata tests.test_pdf_preview_provider -v`
    Coverage: scene payload construction, graph-theme resolution, passive flow/media payload normalization, and PDF preview integration.

## Environment Notes

- Use the project-local interpreter: `./venv/Scripts/python.exe`. The repo uses a Windows-style virtual environment layout even when invoked from `bash`.
- Export `QT_QPA_PLATFORM=offscreen` for the approved shell/QML regression commands when running headless, from WSL, or in CI-style environments.
- Run each command in a fresh process. Some shell-backed suites intentionally use subprocess-isolation loaders to avoid the known Windows Qt/QML multi-`ShellWindow()` lifetime issue.
- Prefer the targeted packet commands above for investigation before rerunning the full aggregate closeout slice.

## Known Baseline Exclusions

- The passive image-panel serializer regression from the packet manifest remains separate from `SHELL_SCENE_BOUNDARY`. Treat `./venv/Scripts/python.exe -m pytest tests/test_serializer.py -k passive_image_panel_properties_and_size -q` as a persistence follow-up, not a boundary closeout failure.
- The Windows Qt/QML multi-`ShellWindow()` lifetime instability remains an environment constraint for shell-backed tests. The approved mitigation for this packet set is fresh-process execution plus the existing subprocess-isolation loaders already present in affected suites.
