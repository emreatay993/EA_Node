# GRAPH_THEME P04: Graph QML Theme Adoption

## Objective
- Migrate node and edge rendering onto `graphThemeBridge` while preserving existing `GraphCanvas` contracts and graph semantics.

## Preconditions
- `P03` is marked `PASS` in [GRAPH_THEME_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_theme/GRAPH_THEME_STATUS.md).
- Graph payload color semantics already resolve through the graph-theme presentation path.

## Target Subsystems
- `ea_node_editor/ui_qml/components/graph/NodeCard.qml`
- `ea_node_editor/ui_qml/components/graph/EdgeLayer.qml`
- `tests/test_graph_track_b.py`
- `tests/test_theme_shell_rc2.py`
- `tests/test_main_window_shell.py`

## Required Behavior
- Move `NodeCard.qml` neutral node colors from `themeBridge` to `graphThemeBridge`.
- Move `EdgeLayer.qml` selected, preview, live-drag, invalid-drag, and fallback colors to `graphThemeBridge`.
- Move port-kind colors used in `NodeCard.qml` to `graphThemeBridge`.
- Preserve `GraphCanvas.qml` public object, method, and interaction contracts.
- Preserve the semantic meaning of node/edge/port colors while changing only the source of truth.

## Non-Goals
- No canvas background/grid/minimap/drop-preview migration.
- No settings dialog work.
- No custom-theme UI.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m unittest tests.test_graph_track_b tests.test_theme_shell_rc2 tests.test_main_window_shell -v`

## Acceptance Criteria
- Node and edge QML rendering reads graph-theme tokens from `graphThemeBridge`.
- Existing GraphCanvas tests still locate the same objects and public contracts.
- Canvas chrome remains on the existing shell theme path.

## Handoff Notes
- `P05` adds user-facing settings controls for choosing the active graph-theme mode and built-in graph theme.
