# COMMENT_BACKDROP P04: Drag/Resize + Nested Motion

## Objective
- Make backdrop drag and resize move descendant content correctly, support nested backdrop trees without double translation, and keep the resulting history and selection behavior coherent.

## Preconditions
- `P03` is marked `PASS` in [COMMENT_BACKDROP_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_STATUS.md).
- No later `COMMENT_BACKDROP` packet is in progress.

## Execution Dependencies
- `P03`

## Target Subsystems
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `tests/test_comment_backdrop_interactions.py`
- `tests/main_window_shell/comment_backdrop_workflows.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeHost.qml`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_scene_mutation_history.py`
- `tests/test_comment_backdrop_interactions.py`
- `tests/main_window_shell/comment_backdrop_workflows.py`
- `docs/specs/work_packets/comment_backdrop/P04_drag_resize_nested_motion_WRAPUP.md`

## Required Behavior
- Dragging a selected backdrop must translate its direct and transitive descendants while preserving each descendant's relative offset inside the backdrop.
- Nested backdrop motion must use direct-owner relationships from `P03` so a descendant node or nested backdrop never receives the same delta twice.
- Backdrop resize commits must recompute membership after the final geometry update and keep unrelated nodes untouched.
- Backdrop drag and descendant motion must record as a single grouped history action suitable for undo and redo.
- Selecting a backdrop must not implicitly select descendants, and ordinary node drag and resize behavior must remain unchanged.

## Non-Goals
- No collapse hiding or edge rerouting yet. `P05` owns collapsed behavior.
- No shell shortcut, library placement, or inline body editing yet. `P06` owns those user-facing entry points.
- No clipboard or load semantics yet. `P07` owns those lifecycle rules.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_comment_backdrop_interactions.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/main_window_shell/comment_backdrop_workflows.py --ignore=venv -k "drag or resize" -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_comment_backdrop_interactions.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/comment_backdrop/P04_drag_resize_nested_motion_WRAPUP.md`

## Acceptance Criteria
- Dragging a backdrop moves descendants and nested backdrops as one coherent authored unit.
- Undo and redo treat one backdrop drag with descendant motion as one grouped graph action.
- Resizing a backdrop recomputes membership deterministically without mutating unrelated node positions.
- Selection remains backdrop-local rather than auto-expanding to descendants.

## Handoff Notes
- `P05` may assume backdrop motion and nested direct-owner trees are already stable.
- Record the exact multi-node history grouping entry point in the wrap-up so `P07` can reuse it when collapsed clipboard and delete semantics need descendant sets.
