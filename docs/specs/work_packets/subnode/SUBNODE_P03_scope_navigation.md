# SUBNODE P03: Scope Navigation

## Objective
- Make the graph canvas scope-aware and add breadcrumb-style navigation for nested subnodes.

## Preconditions
- `P02` is marked `PASS` in [SUBNODE_STATUS.md](/c:/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/subnode/SUBNODE_STATUS.md).
- No later Subnode packet is in progress.

## Target Subsystems
- `ea_node_editor/graph/hierarchy.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/MainShell.qml`
- `ea_node_editor/ui/shell/window.py`
- `tests/test_graph_track_b.py`
- `tests/test_main_window_shell.py`

## Required Behavior
- Render only direct children of the active `scope_path` and only edges between visible nodes.
- Add a breadcrumb bar for workspace-root and nested subnode scopes.
- Support double-click or context-menu entry into a subnode shell.
- Support breadcrumb segment navigation, `Alt+Left` to move to the parent scope, and `Alt+Home` to return to workspace root.
- Persist the active `scope_path` per view while keeping per-scope camera restore runtime-only.

## Non-Goals
- No group/ungroup transforms.
- No library publishing or import/export.
- No execution model changes.

## Verification Commands
1. `venv/Scripts/python.exe -m unittest tests.test_graph_track_b tests.test_main_window_shell -v`

## Acceptance Criteria
- Entering/exiting subnodes changes the visible graph scope without mutating workspace membership.
- Breadcrumbs and keyboard actions navigate correctly up to the workspace root.
- Scope changes preserve active selection/camera behavior only within the currently visible scope.

## Handoff Notes
- `P04` must create shells and pin nodes that work inside this scoped canvas.
- `P05` must reuse the scope-opening helper added here for search/failure focus.
