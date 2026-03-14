# GRAPH_THEME P08: Custom Theme Editing + Live Apply

## Objective
- Finish the full custom graph-theme editor by enabling token editing for custom themes and live runtime apply.

## Preconditions
- `P07` is marked `PASS` in [GRAPH_THEME_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_theme/GRAPH_THEME_STATUS.md).
- The graph-theme manager/editor shell and custom-theme CRUD helpers already exist.

## Target Subsystems
- `ea_node_editor/ui/dialogs/graph_theme_editor_dialog.py`
- `ea_node_editor/ui/graph_theme/*`
- `ea_node_editor/ui_qml/graph_theme_bridge.py`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_graph_theme_editor_dialog.py`
- `tests/test_graph_track_b.py`
- `tests/test_theme_shell_rc2.py`

## Required Behavior
- Enable editing for custom graph themes only.
- Add editable sections for:
  - node tokens
  - edge tokens
  - category accent tokens
  - port-kind tokens
- Validate hex color inputs before save.
- Persist saved custom themes into app preferences.
- If the edited custom theme is the active explicit graph theme and `follow_shell_theme` is false, apply it live to `graphThemeBridge` and rebuild graph payloads.
- Built-in themes remain read-only; editing them requires duplication to a custom theme first.

## Non-Goals
- No import/export of theme files.
- No shell-theme editing.
- No expansion of graph-theme scope beyond nodes and edges.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_theme_editor_dialog tests.test_graph_track_b tests.test_theme_shell_rc2 -v`

## Acceptance Criteria
- Custom graph themes can be edited, validated, persisted, and reapplied across restarts.
- Built-in themes remain immutable in the editor workflow.
- Active explicit graph-theme edits can restyle nodes and edges live without touching shell-theme behavior.

## Handoff Notes
- `P09` closes the roadmap with docs, traceability, and the final regression gate.
