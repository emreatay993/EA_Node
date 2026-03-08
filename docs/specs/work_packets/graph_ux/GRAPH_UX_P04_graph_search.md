# GRAPH_UX P04: Graph Search and Jump Palette

## Objective
- Add a graph-wide search palette that can jump to nodes across workspaces.

## Preconditions
- `P03` is marked `PASS` in [GRAPH_UX_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/graph_ux/GRAPH_UX_STATUS.md).
- `P01` framing helpers remain the canonical camera API.

## Target Subsystems
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/controllers/workspace_library_controller.py`
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `tests/test_main_window_shell.py`

## Required Behavior
- Add a graph search palette opened by `Ctrl+K`.
- Search scope is all workspaces in the active project.
- Search fields are case-insensitive substring matches against:
  - node title
  - node type display name
  - `type_id`
  - `node_id`
- Ranking order:
  - title/display-name prefix match
  - title/display-name substring match
  - `type_id` match
  - `node_id` match
  - stable tie-break by workspace name then node title
- Show at most `10` results.
- Up/Down changes the highlighted result, Enter jumps, and `Esc` closes the palette.
- Jump behavior must:
  - switch to the containing workspace
  - reveal the parent chain if hidden/collapsed
  - select the node
  - frame the node using the shared camera helper from `P01`
- An empty query shows no results and performs no jump.

## Non-Goals
- No node-library filtering changes.
- No fuzzy-search scoring beyond the ranking order above.
- No saved search history.

## Verification Commands
1. `venv\Scripts\python -m unittest tests.test_main_window_shell -v`

## Acceptance Criteria
- Search finds nodes by title, display name, `type_id`, and `node_id`.
- Ranking prefers human-facing title/display-name matches over internal-id matches.
- Jump switches workspace when needed and frames the correct node.
- Keyboard navigation and close behavior are covered by tests.
- Empty queries and no-result queries are safe no-ops.

## Handoff Notes
- `P05` may reuse search framing helpers but must not move search logic into the minimap.
- Keep the search API callable from shell/controller code so later overlays or menus can reuse it.
