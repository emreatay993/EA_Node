# GRAPH_THEME P01: Graph Theme Foundation

## Objective
- Establish the graph-theme domain package and app-preferences shape without adding runtime apply behavior.

## Preconditions
- `P00` is marked `PASS` in [GRAPH_THEME_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_theme/GRAPH_THEME_STATUS.md).
- No later `GRAPH_THEME` packet is in progress.

## Target Subsystems
- `ea_node_editor/ui/graph_theme/tokens.py` (new)
- `ea_node_editor/ui/graph_theme/registry.py` (new)
- `ea_node_editor/ui/graph_theme/__init__.py` (new)
- `ea_node_editor/settings.py`
- `ea_node_editor/ui/shell/controllers/app_preferences_controller.py`
- `tests/test_graph_theme_preferences.py` (new)
- `tests/test_graphics_settings_preferences.py`

## Required Behavior
- Add `ea_node_editor/ui/graph_theme/*` as the dedicated home for graph-theme definitions.
- Define graph-theme types for node tokens, edge tokens, category accent tokens, port-kind tokens, and the graph-theme definition record.
- Seed built-in graph themes `graph_stitch_dark` and `graph_stitch_light`.
- Add a shell-theme to default-graph-theme mapping helper so `stitch_dark` and `stitch_light` can resolve deterministically to their graph-theme counterparts.
- Bump app preferences to version `2`.
- Add `graphics.graph_theme.follow_shell_theme`, `graphics.graph_theme.selected_theme_id`, and `graphics.graph_theme.custom_themes`.
- Migrate v1 app-preferences documents to the locked v2 defaults from the manifest.
- Normalize `custom_themes` to `[]` only in this packet; do not implement custom-theme CRUD or editing yet.

## Non-Goals
- No `ShellWindow` runtime apply behavior.
- No QML bridge.
- No graph payload adoption.
- No dialog changes.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_theme_preferences tests.test_graphics_settings_preferences -v`

## Acceptance Criteria
- Built-in graph-theme ids resolve deterministically to shared token sets.
- App-preferences v1 documents normalize to v2 with the locked graph-theme defaults.
- No shell startup, QML bridge, or graph-scene behavior changes are introduced yet.

## Handoff Notes
- `P02` wires runtime graph-theme resolution and `graphThemeBridge` on top of the foundation created here.
