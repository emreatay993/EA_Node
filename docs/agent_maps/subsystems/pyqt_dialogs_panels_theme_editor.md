# PyQt Dialogs, Theme, And Editor Support

## Purpose
Use this for PyQt dialogs, script/editor support, graph theme editors, and non-QML support widgets.

## Start Here
- `ea_node_editor/ui/dialogs/graphics_settings_dialog.py`
- `ea_node_editor/ui/dialogs/`
- `ea_node_editor/ui/editor/`
- `ea_node_editor/ui/graph_theme/`
- `ea_node_editor/ui/theme/`
- `ea_node_editor/ui/support/`

## Do Not Start Here
- QML shell files for PyQt-only dialogs.
- Shell controllers/presenters or visible QML panes; use the UI shell and QML shell maps.
- Persistence serializers unless a dialog changes saved project data.

## Common Changes
- Keep dialog-specific state inside the dialog/controller pair.
- For theme or style changes, update theme assets and focused dialog tests together.
- App-owned `QDialog`, `QMessageBox`, and `QInputDialog` surfaces inherit their shared adaptive styling from `ea_node_editor/ui/theme/styles.py`. Use `dialogRole` only for semantic muted/error/danger states; keep native `QFileDialog` and `QColorDialog` behavior and native title bars.
- Graph Theme Manager gradient controls are typed node-token editors, not generic hex rows; update color, boolean, and direction handling together.
- Passive Node Style gradients use `Inherit / Custom / Off` so blank per-node style still inherits graph theme defaults.
- For script/editor behavior, check editor tests before broad shell tests.
- Workflow Settings is a PyQt dialog; its Environment Python Executable field is project metadata UI for execution-owned interpreter selection, and its Prepare COREX Runtime button delegates venv/wheel setup to `ea_node_editor.execution.managed_runtime`.
- `CanvasViewExportDialog` is a shell-presenter options dialog only; actual PNG capture, native-overlay compositing, and PowerPoint writing stay in `GraphCanvasPresenter` and UI export helpers.
- `ProjectReviewDeckDialog` is a shell-presenter options dialog for the curated draft tree, global slide order, output deck path, slide size, and optional corporate `.pptx` template. Project/artifact discovery stays in `ui/project_review_deck.py`, not inside the dialog.
- `InputReferenceDialog` owns the Help > Keyboard and Mouse Reference table plus its Context/Action filters; update it when user-facing shortcuts, hidden-port decluttering gestures, focused editor controls, or reference lookup behavior change.

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_graph_theme_editor_dialog.py tests/test_graphics_settings_dialog.py tests/test_script_editor_dock.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_project_review_deck.py --ignore=venv -q
```

## Breadcrumbs
- [Graphics Settings, Themes, And Preferences](../feature_routes/graphics_settings_themes_preferences.md)
- [Surface Input And Inline Controls](../feature_routes/surface_input_and_inline_controls.md)

## Update Triggers
Update when dialog ownership or shared Qt dialog styling, canvas export options, project review deck options, Workflow Settings environment fields, theme editor flows, or editor support routes change.
