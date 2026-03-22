# COMMENT_BACKDROP P06: Editing + Shell Creation Affordances

## Objective
- Wire the new backdrop into normal authoring flows through library placement, wrap-selection creation with shortcut `C`, and inline plus inspector editing while preserving the current subnode grouping affordances.

## Preconditions
- `P05` is marked `PASS` in [COMMENT_BACKDROP_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_STATUS.md).
- No later `COMMENT_BACKDROP` packet is in progress.

## Execution Dependencies
- `P05`

## Target Subsystems
- `ea_node_editor/ui/shell/window_actions.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/controllers/workspace_edit_ops.py`
- `ea_node_editor/ui/shell/controllers/workspace_graph_edit_controller.py`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphCommentBackdropSurface.qml`
- `tests/main_window_shell/comment_backdrop_workflows.py`
- `tests/test_graph_surface_input_inline.py`

## Conservative Write Scope
- `ea_node_editor/ui/shell/window_actions.py`
- `ea_node_editor/ui/shell/window.py`
- `ea_node_editor/ui/shell/controllers/workspace_edit_ops.py`
- `ea_node_editor/ui/shell/controllers/workspace_graph_edit_controller.py`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/passive/GraphCommentBackdropSurface.qml`
- `tests/main_window_shell/comment_backdrop_workflows.py`
- `tests/test_graph_surface_input_inline.py`
- `docs/specs/work_packets/comment_backdrop/P06_editing_shell_creation_affordances_WRAPUP.md`

## Required Behavior
- Expose normal library placement for `passive.annotation.comment_backdrop` through the existing node library and drop paths.
- Add a dedicated wrap-selection-in-comment action bound to shortcut `C`, leaving `Ctrl+G` and `Ctrl+Shift+G` untouched for structural subnode grouping.
- Route the wrap-selection action through the backend transaction from `P03` rather than inventing a second creation path.
- Support inline body editing on the canvas plus inspector editing for the backdrop body, while title editing continues to reuse the shared header editor.
- Keep backdrop body interaction inside the graph-surface input ownership pattern so editing focus does not leak into body drag, open-scope, or context-menu behavior.
- Empty-selection wrap requests must be a no-op or a packet-owned user-facing rejection with no graph mutation.

## Non-Goals
- No clipboard or delete semantics yet. `P07` owns those lifecycle rules.
- No docs or traceability updates yet. `P08` owns closeout.
- No connectable backdrop variant. The dedicated backdrop stays zero-port in this packet set.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/main_window_shell/comment_backdrop_workflows.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_graph_surface_input_inline.py --ignore=venv -k "comment_backdrop" -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/main_window_shell/comment_backdrop_workflows.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/comment_backdrop/P06_editing_shell_creation_affordances_WRAPUP.md`

## Acceptance Criteria
- Users can create a backdrop through both the node library and the new wrap-selection action.
- Shortcut `C` creates a padded backdrop around the current selection without colliding with existing grouping shortcuts.
- Backdrop title and body editing stay synchronized between inline and inspector paths.
- Pointer-routing regressions confirm backdrop text editing does not reintroduce drag or click-swallowing bugs.

## Handoff Notes
- `P07` must reuse the same wrap-selection and editing authorities rather than adding separate clipboard-only or delete-only backdrop helpers.
- Record the exact shell action names and shortcut bindings in the wrap-up so later docs and traceability use the landed names verbatim.
