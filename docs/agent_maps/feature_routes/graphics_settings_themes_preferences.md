# Graphics Settings, Themes, And Preferences

## Purpose
Use this for graph themes, graphics settings, app preferences, theme editor dialogs, and app-wide visual preferences.

## Start Here
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/graph_theme_defaults.py`
- `ea_node_editor/ui/dialogs/graphics_settings_dialog.py`
- `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`
- `ea_node_editor/ui/dialogs/graph_theme_editor_dialog.py`
- `ea_node_editor/ui_qml/graph_canvas_state/`
- `ea_node_editor/ui_qml/graph_canvas_command/`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasOptionsMenu.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphNativeExplorerSurface.qml`
- `ea_node_editor/ui_qml/graph_theme_bridge.py`
- `ea_node_editor/ui_qml/theme_bridge.py`
- `ea_node_editor/text_style.py`

## Common Changes
- Folder Explorer column widths flow through app-wide graphics preferences at `graphics.folder_explorer.column_widths` and are projected to graph-canvas QML state; header resizing persists through the graph-canvas command bridge rather than the Graphics Settings dialog.
- Recent annotation text colors flow through app-wide graphics preferences at `graphics.typography.recent_text_colors` and are projected to graph-canvas QML state for text toolbar swatches.
- Learned radial-menu node choices live app-wide at `graphics.shell.node_library_usage` as a normalized rolling list of the last 64 successful explicit library choices. Repeated ids intentionally encode frequency and recency; this history is not project `.cxproj` state.
- The canvas options menu is a compact QML entry point for graphics preferences, including `graphics.canvas.background_variant` for dark/white canvas fills (plus theme follow); route changes through the graph-canvas command bridge and shell presenters, not project persistence. The top-right gear visibility is app-wide at `graphics.canvas.show_canvas_options_button` and projects through the graph-canvas state bridge.
- Canvas Options has no authoring-mode or connected-control policy. The removed control Settings row has no app preference or per-node expansion state; `solution.default_mode` is owned by the app-preferences/run-controller route rather than Graphics Settings presentation.
- Node elapsed-time units and visibility are app-wide at `graphics.canvas.node_elapsed_time_unit` and `graphics.canvas.node_elapsed_time_visibility`; keep the Graphics Settings Nodes combos, canvas options menu Nodes submenus, graph-canvas state/command bridges, and `GraphNodeHost` footer guards aligned. Visibility values are `off`, `during_run`, and `always`; units remain seconds or milliseconds.
- Notched ports are app-wide at `graphics.canvas.notched_ports`, default on, and intentionally appear only in Graphics Settings > Canvas > Nodes. Keep preference defaulting/normalization, the full-dialog checkbox, shell workspace state, `GraphCanvasPreferenceFacts.notchedPortsEnabled`, and the standard-node QML treatment aligned; do not add a Canvas Options shortcut or project persistence.
- Node comment editor default is app-wide at `graphics.canvas.node_comment_editor_default`; keep the Graphics Settings Nodes combo, canvas options menu Nodes submenu, graph-canvas state/command bridges, `GraphCanvasPreferenceFacts.qml`, and `GraphNodeCommentPopoverLayer.qml` aligned.
- Node floating toolbars open for a single selected node by default. Legacy hover reveal is app-wide and opt-in at `graphics.canvas.node_floating_toolbar_opens_on_hover`; keep the Graphics Settings Floating toolbar checkbox, shell workspace presenter state, graph-canvas state bridge, `GraphCanvasPreferenceFacts.qml`, and `GraphNodeHost.toolbarActiveSource` aligned.
- Image animation autoplay is app-wide at `graphics.image_nodes.autoplay_animations` and defaults to enabled. Keep the Graphics Settings checkbox, app-preference normalizer, shell/graph-canvas state projection, and `GraphCanvasPreferenceFacts.imageNodeAutoplayAnimations` aligned; only the per-node `animation_playback_mode` override belongs in `.cxproj` persistence.
- Outer shell pane collapse state is app-wide at `graphics.shell.panel_collapsed`; keep defaults, normalizers, `ShellWorkspacePresenter`, `ShellWorkspaceBridge`, and the QML pane owners aligned.
- Shell theme tokens in `ea_node_editor/ui/theme/tokens.py` are projected through `ThemeBridge.palette`; QML panel body text should use `panel_fg`, titles should use `panel_title_fg`, and secondary labels should use `muted_fg`.
- Selection envelope toolbar preferences are app-wide under `graphics.canvas.selection_toolbar_mode` and `graphics.canvas.selection_toolbar_minimal_menu_trigger`; keep defaults/normalizers, Graphics Settings combos, shell presenters/window properties, and graph-canvas state/command bridges aligned.
- Graph-theme node tokens are `Passive Node Defaults` only. They keep passive body gradients, title/icon foreground, and `card_selected_border` outline/glow; authored passive `visual_style.border_color` remains idle-only. Active and `compile_only` bodies, outlines, title/port/inline-control foregrounds, and selected fill use the fixed shell-brightness palette in `GraphNodeHostTheme.qml` and ignore custom graph-theme node tokens. Keep `ui/graph_theme` normalization, `GraphThemeEditorDialog` wording/controls, `GraphThemePreviewWidget`, `GraphThemeBridge.node_palette`, and passive QML rendering in sync. Add-on Manager category marks use the shell accent rather than a graph-theme category palette.
- `GraphPortStateTokens` (`port_state_tokens` on `GraphThemeDefinition`, `GraphThemeBridge.port_state_palette`, "Port State Tokens" section in the theme editor) owns valid-green, waiting, idle, and invalid grip colors. These state colors are shared per brightness (`GRAPH_STITCH_DARK/LIGHT_PORT_STATE_TOKENS_V1`); rest-state grips no longer use per-kind colors.
- Keep these visual defaults out of project `.cxproj` persistence.

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_graph_theme_editor_dialog.py tests/test_graphics_settings_dialog.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_app_preferences.py tests/test_graphics_settings_preferences.py tests/test_graphics_settings_dialog.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_app_preferences_import_defaults.py tests/test_workspace_library_controller_unit.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/main_window_shell/bridge_contracts_graph_canvas.py tests/main_window_shell/shell_basics_and_search.py -k "graphics_settings_properties_are_exposed_to_qml or qml_invokable_slots_exist_for_shell_buttons or split_canvas_bridges" --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/graph_track_b/qml_preference_bindings.py --ignore=venv -q
```

## Breadcrumbs
- [App Preferences, Settings, And Platform Paths](../subsystems/app_preferences_settings_platform_paths.md)
- [Assets, Icons, Title Icons, And Theme Assets](../subsystems/assets_icons_theme.md)

## Update Triggers
Update when preferences storage/migration, passive-default graph theme tokens, the fixed active-node palette boundary, theme bridges, graphics dialogs, node-library display or learned-usage preferences, shell pane collapse preferences, node elapsed-time units, notched ports, node comment editor defaults, node floating-toolbar reveal behavior, text toolbar recents, plot/lightweight canvas preferences, or theme tests change.

## 2026-07-11 Performance Ownership

- Palette and tooltip/category projections cache against existing theme/policy revisions only. No new persistence key or invalidation channel was introduced.
