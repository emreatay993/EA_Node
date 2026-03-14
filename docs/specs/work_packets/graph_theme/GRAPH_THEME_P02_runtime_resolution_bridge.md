# GRAPH_THEME P02: Runtime Resolution Bridge

## Objective
- Make runtime graph-theme resolution explicit and expose the resolved graph theme to QML as `graphThemeBridge`.

## Preconditions
- `P01` is marked `PASS` in [GRAPH_THEME_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_theme/GRAPH_THEME_STATUS.md).
- App preferences already persist the v2 `graphics.graph_theme` payload.

## Target Subsystems
- `ea_node_editor/ui_qml/graph_theme_bridge.py` (new)
- `ea_node_editor/ui_qml/__init__.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/app.py`
- `tests/test_graph_theme_shell.py` (new)
- `tests/test_theme_shell_rc2.py`

## Required Behavior
- Add `ea_node_editor/ui_qml/graph_theme_bridge.py` as the canonical QML-facing graph-theme bridge.
- Add runtime graph-theme resolution logic:
  - when `follow_shell_theme` is true, resolve from the active shell theme id
  - when `follow_shell_theme` is false, resolve from `selected_theme_id`
- Expose `graphThemeBridge` to QML alongside the existing `themeBridge`.
- Keep `themeBridge`, shell theme selection, and QApplication stylesheet behavior unchanged.
- Refresh `graphThemeBridge` during shell startup and whenever shell theme or explicit graph-theme settings change.

## Non-Goals
- No node/edge QML adoption yet.
- No graph payload rebuild logic yet.
- No user-facing settings controls yet.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_theme_shell tests.test_theme_shell_rc2 -v`

## Acceptance Criteria
- `graphThemeBridge` resolves a stable graph-theme payload at startup.
- `follow_shell_theme` keeps the graph-theme bridge in sync with shell-theme changes.
- Existing shell-theme behavior is unchanged outside the new bridge surface.

## Handoff Notes
- `P03` consumes the resolved graph theme in the graph presenter/payload path and must not duplicate runtime resolution logic.
