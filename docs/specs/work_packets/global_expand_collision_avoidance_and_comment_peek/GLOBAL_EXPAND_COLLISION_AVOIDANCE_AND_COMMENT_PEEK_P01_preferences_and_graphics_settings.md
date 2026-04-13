# GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK P01: Preferences and Graphics Settings

## Packet Metadata

- Packet: `P01`
- Title: `Preferences and Graphics Settings`
- Owning Source Subsystem Packet: [Presenters Packet](../ui_context_scalability_refactor/PRESENTERS_PACKET.md)
- Owning Regression Packet: [Track B Test Packet](../ui_context_scalability_refactor/TRACK_B_TEST_PACKET.md)
- Inherited Secondary Subsystem Docs: [Shell Packet](../ui_context_scalability_refactor/SHELL_PACKET.md), [Graph Canvas Packet](../ui_context_scalability_refactor/GRAPH_CANVAS_PACKET.md)
- Inherited Secondary Regression Docs: [Main Window Shell Test Packet](../ui_context_scalability_refactor/MAIN_WINDOW_SHELL_TEST_PACKET.md)
- Execution Dependencies: `GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P00_bootstrap.md`

## Objective

- Add the persistent `expand_collision_avoidance` preference surface, expose it through the active shell and canvas preference path, and add Graphics Settings controls for the default and advanced options without changing collapse or expand behavior yet.

## Preconditions

- `P00` is complete and the packet set is registered in `.gitignore` and `docs/specs/INDEX.md`.
- The implementation base is current `main`.

## Execution Dependencies

- `GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_P00_bootstrap.md`

## Target Subsystems

- `ea_node_editor/settings.py`
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`
- `ea_node_editor/ui/shell/presenters/workspace_presenter.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_state/run_and_style_state.py`
- `ea_node_editor/ui/dialogs/graphics_settings_dialog.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `tests/test_graphics_settings_preferences.py`
- `tests/test_graphics_settings_dialog.py`
- `tests/test_shell_theme.py`
- `tests/graph_track_b/qml_preference_bindings.py`

## Conservative Write Scope

- `ea_node_editor/settings.py`
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`
- `ea_node_editor/ui/shell/presenters/workspace_presenter.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_state/run_and_style_state.py`
- `ea_node_editor/ui/dialogs/graphics_settings_dialog.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `tests/test_graphics_settings_preferences.py`
- `tests/test_graphics_settings_dialog.py`
- `tests/test_shell_theme.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/P01_preferences_and_graphics_settings_WRAPUP.md`

## Source Public Entry Points

- `DEFAULT_GRAPHICS_SETTINGS`
- `normalize_graphics_settings`
- `AppPreferencesController.set_graphics_settings`
- `ShellWindow.apply_graphics_preferences`
- `ShellWorkspacePresenter.apply_graphics_preferences`
- `GraphCanvasStateBridge` graphics-preference projection

## Regression Public Entry Points

- `tests/test_graphics_settings_preferences.py`
- `tests/test_graphics_settings_dialog.py`
- `tests/test_shell_theme.py`
- `tests/graph_track_b/qml_preference_bindings.py`

## State Owner

- The authoritative state remains the app preferences document under `graphics.interaction`. This packet may normalize, persist, and project that state, but it must not introduce project-file persistence or per-node overrides.

## Allowed Dependencies

- [PLANS_TO_IMPLEMENT/Global Expand Collision Avoidance and Comment Peek.md](../../../../PLANS_TO_IMPLEMENT/Global Expand Collision Avoidance and Comment Peek.md)
- [GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_MANIFEST.md](./GLOBAL_EXPAND_COLLISION_AVOIDANCE_AND_COMMENT_PEEK_MANIFEST.md)
- [Presenters Packet](../ui_context_scalability_refactor/PRESENTERS_PACKET.md)
- [Shell Packet](../ui_context_scalability_refactor/SHELL_PACKET.md)
- [Graph Canvas Packet](../ui_context_scalability_refactor/GRAPH_CANVAS_PACKET.md)
- [Track B Test Packet](../ui_context_scalability_refactor/TRACK_B_TEST_PACKET.md)
- [Main Window Shell Test Packet](../ui_context_scalability_refactor/MAIN_WINDOW_SHELL_TEST_PACKET.md)

## Required Invariants

- Missing preference values for both new users and upgraders normalize to the locked defaults from the manifest.
- Graphics Settings must expose a basic section for enable or disable, strategy, and animation, plus an advanced section for scope, gap preset, and reach mode or preset.
- Invalid or partial preference payloads normalize safely back to defaults.
- This packet does not change collapse or expand runtime behavior yet.
- No `.sfe` schema, project persistence, or node payload expansion is allowed.

## Forbidden Shortcuts

- Do not read or write these preferences directly from ad hoc QML globals.
- Do not persist UI-expander-only state such as whether the advanced settings section is currently open.
- Do not implement collision math, object translation, or comment peek behavior in this packet.
- Do not widen write scope into graph-scene mutation files for convenience.

## Required Tests

- `tests/graph_track_b/qml_preference_bindings.py`
- `tests/test_graphics_settings_preferences.py`
- `tests/test_graphics_settings_dialog.py`
- `tests/test_shell_theme.py`

## Verification Commands

1. Full packet verification:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_preferences.py tests/test_graphics_settings_dialog.py tests/test_shell_theme.py tests/graph_track_b/qml_preference_bindings.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/test_graphics_settings_preferences.py tests/test_graphics_settings_dialog.py --ignore=venv -q
```

## Expected Artifacts

- `ea_node_editor/settings.py`
- `ea_node_editor/app_preferences.py`
- `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`
- `ea_node_editor/ui/shell/presenters/workspace_presenter.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/window_state/run_and_style_state.py`
- `ea_node_editor/ui/dialogs/graphics_settings_dialog.py`
- `ea_node_editor/ui_qml/graph_canvas_state_bridge.py`
- `tests/test_graphics_settings_preferences.py`
- `tests/test_graphics_settings_dialog.py`
- `tests/test_shell_theme.py`
- `tests/graph_track_b/qml_preference_bindings.py`
- `docs/specs/work_packets/global_expand_collision_avoidance_and_comment_peek/P01_preferences_and_graphics_settings_WRAPUP.md`

## Acceptance Criteria

- `graphics.interaction.expand_collision_avoidance` exists as a normalized application preference surface with the locked defaults.
- Graphics Settings can display and persist the basic and advanced controls for this feature.
- The live shell or canvas preference path updates the active host state without introducing runtime collision behavior yet.
- The full packet verification command passes.
- The review gate passes.

## Handoff Notes

- Stop after `P01`. Do not start `P02` in the same thread.
- `P02` inherits this packet's normalized settings surface and runtime projection path.
