# App Preferences, Settings, And Platform Paths

## Purpose
Use this for app-wide settings, graphics preferences, solution-mode defaults, selected-run defaults, user data paths, and platform path decisions.

## Start Here
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/settings.py`
- `ea_node_editor/platform_paths.py`
- `ea_node_editor/platform_open.py`
- `ea_node_editor/graph_theme_defaults.py`
- `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`
- `ea_node_editor/ui/dialogs/selected_run_settings_dialog.py`

## Do Not Start Here
- Project `.cxproj` persistence for app-wide preferences.
- Graph domain code for UI preference state.

## Common Changes
- Keep app graphics/preferences outside project documents unless a current spec requires otherwise.
- Route preference dialogs through shell controllers and PyQt dialog code.
- Keep path resolution centralized in `platform_paths.py`.
- Keep OS launch of files/folders centralized in `platform_open.py` (`open_path_with_default_handler` for "Open", `open_path_with_app_chooser` for "Open with..."); the folder-explorer open actions and the Path Pointer toolbar open actions route through it instead of inlining `os.startfile`/`QDesktopServices`/`rundll32` shell logic.
- Managed workflow runtimes live under `user_data_dir() / "runtimes"` and are selected through project workflow metadata, not app preferences.
- Keep app-global plot preferences such as `graphics.plot.lightweight_canvas` and `graphics.plot.plot_default_backend_per_type` in app preferences, not `.cxproj` project documents.
- Keep shell pane collapse state in app preferences as `graphics.shell.panel_collapsed`; it covers only the outer node-library, properties, and output panes, not library categories, inspector groups, selected-node body collapse, output tabs, or output height.
- Keep Folder Explorer details-column defaults in app preferences as `graphics.folder_explorer.column_widths`; the app-wide JSON is the source of truth, not project `.cxproj` files.
- Keep annotation text recent colors in app preferences as `graphics.typography.recent_text_colors`; they are app-wide toolbar history, not project `.cxproj` data.
- Keep radial-menu node usage in app preferences as the bounded `graphics.shell.node_library_usage` list. Record only successful explicit standard/add-on library choices; ranking and stale-id filtering remain presenter-owned, and the list never enters `.cxproj` persistence.
- App preferences v6 owns `solution.default_mode`, normalized to `auto` or `manual` and defaulting to `auto`. Each opened workspace copies that initial mode into runtime-only shell state; Auto/Manual/Pause changes do not enter app preferences or `.cxproj` unless the user changes the app-wide default itself. The retired connected-control-port policy and control-row state are not compatibility surfaces.
- Keep `selected_run.preview_before_run` in app preferences; both the graph canvas options menu and `SelectedRunSettingsDialog` project it. Runtime output caches remain session-only shell state and must not be serialized into app preferences or project `.cxproj` files.
- Keep `graphics.canvas.node_comment_editor_default` in app preferences; the graph canvas options menu and Graphics Settings dialog choose whether node comment badge clicks open the canvas popover or Inspector editor, and this must not be serialized into project `.cxproj` files.
- Keep default-off `graphics.canvas.node_floating_toolbar_opens_on_hover` in app preferences; Graphics Settings exposes the legacy hover reveal while singleton selection remains the default QML behavior, and this must not enter project `.cxproj` files.

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_dialog.py tests/test_graph_theme_editor_dialog.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_app_preferences.py tests/test_graphics_settings_preferences.py tests/test_selected_run_settings_dialog.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_app_preferences_import_defaults.py tests/test_workspace_library_controller_unit.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_app_preferences.py tests/test_run_controller_unit.py -k "solution_default_mode or solution_mode" --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_platform_open.py --ignore=venv -q
```

## Breadcrumbs
- [Graphics Settings, Themes, And Preferences](../feature_routes/graphics_settings_themes_preferences.md)
- [Assets, Icons, Title Icons, And Theme Assets](assets_icons_theme.md)

## Update Triggers
Update when app settings storage/migrations, platform paths, OS file/folder open helpers, preferences controllers, learned node-library usage, solution-mode or selected-run defaults, node comment editor defaults, node floating-toolbar hover preference, plot defaults, or graphics settings routing changes.
