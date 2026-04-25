# COMMENT_FLOATING_POPOVER P02: Action Wiring and Commit Flow

## Packet Metadata

- Packet: `P02`
- Title: `Action Wiring and Commit Flow`
- Execution Dependencies: `COMMENT_FLOATING_POPOVER_P01_overlay_shell.md`
- Worker model: `gpt-5.5`
- Worker reasoning effort: `xhigh`

## Objective

- Wire the popover shell into comment-backdrop-only action paths and make the popover body editor reuse the existing `body` property commit flow shared by the inline editor and inspector.

## Preconditions

- `P01` is `PASS`.
- The implementation base contains the `GraphCommentFloatingPopover` shell, transient active node id state, and dismiss helpers.
- Existing `Peek Inside` context-menu behavior and comment backdrop inline body editing tests are passing.

## Execution Dependencies

- `COMMENT_FLOATING_POPOVER_P01_overlay_shell.md`

## Target Subsystems

- `ea_node_editor/ui_qml/components/graph/passive/GraphCommentBackdropSurface.qml`
- `ea_node_editor/ui_qml/components/graph/overlay/GraphCommentFloatingPopover.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `tests/main_window_shell/comment_backdrop_workflows.py`
- `tests/test_comment_backdrop_contracts.py`

## Conservative Write Scope

- `docs/specs/work_packets/comment_floating_popover/P02_action_wiring_and_commit_flow_WRAPUP.md`
- `ea_node_editor/ui_qml/components/graph/passive/GraphCommentBackdropSurface.qml`
- `ea_node_editor/ui_qml/components/graph/overlay/GraphCommentFloatingPopover.qml`
- `ea_node_editor/ui_qml/components/graph/GraphNodeSurfaceLoader.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasInteractionState.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `tests/main_window_shell/comment_backdrop_workflows.py`
- `tests/test_comment_backdrop_contracts.py`

## Required Behavior

- Add a comment-backdrop-only surface action, expected id `openCommentPopover`, on `GraphCommentBackdropSurface.qml`.
- Let the existing `GraphNodeSurfaceLoader` -> `GraphNodeHost` -> `GraphNodeFloatingToolbar` -> `GraphCanvasNodeDelegate` fallback path dispatch that surface action without adding it to `commonNodeActions`.
- Add a comment-specific node context menu entry only if it stays scoped to `comment_backdrop` nodes and does not replace or alter `Peek Inside`.
- Opening the action must set the transient active popover node id and close normal context menus.
- Re-triggering the action for the active node may keep the popover open or toggle it closed, but the behavior must be deterministic and covered by the packet-owned tests.
- The popover editor must bind its committed value to the active comment node's normal `properties.body` value and commit through the existing `inlinePropertyCommitted(nodeId, "body", value)` path or the same graph canvas node-surface bridge route.
- Inspector edits and inline editor commits must update the popover editor's committed text without creating a second source of truth.
- The action must be unavailable in read-only graph state and unavailable for non-comment nodes.
- Existing comment `Peek Inside` behavior must continue to use `peek_comment` / `exit_comment_peek` and must not be coupled to `activeCommentPopoverNodeId`.

## Non-Goals

- Do not add new Python command-bridge methods unless QML-only routing is proven insufficient.
- Do not persist popover state into graph scene payloads, app preferences, project documents, or serializer fields.
- Do not generalize the popover to annotation notes or normal nodes.
- Do not change comment backdrop membership, resizing, dragging, collapse, or peek membership logic.
- Do not run broad repo-wide verification in place of the packet-owned commands.

## Verification Commands

1. Full packet verification:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/comment_backdrop_workflows.py tests/test_comment_backdrop_contracts.py --ignore=venv -q
```

## Review Gate

```powershell
$env:QT_QPA_PLATFORM='offscreen'; .\venv\Scripts\python.exe -m pytest tests/main_window_shell/comment_backdrop_workflows.py -k "popover or inline_body_commit or peek_inside" --ignore=venv -q
```

## Expected Artifacts

- `docs/specs/work_packets/comment_floating_popover/P02_action_wiring_and_commit_flow_WRAPUP.md`
- `ea_node_editor/ui_qml/components/graph/passive/GraphCommentBackdropSurface.qml`
- `ea_node_editor/ui_qml/components/graph/overlay/GraphCommentFloatingPopover.qml`
- `ea_node_editor/ui_qml/components/graph_canvas/GraphCanvasContextMenus.qml`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `tests/main_window_shell/comment_backdrop_workflows.py`
- `tests/test_comment_backdrop_contracts.py`

## Acceptance Criteria

- Comment backdrop floating toolbar actions include the popover action and non-comment nodes do not.
- If a context entry is added, it is visible only for eligible comment backdrop nodes and does not remove the existing `Peek Inside` entry.
- Activating the toolbar or context entry opens the floating popover for the target comment node.
- Editing the popover body commits to the same `body` property path used by the existing inline editor and inspector.
- Inspector and inline edits refresh the popover's committed text.
- Existing `Peek Inside` tests still pass.
- The full packet verification command passes.
- The review gate passes.

## Handoff Notes

- `P03` inherits `tests/main_window_shell/comment_backdrop_workflows.py` and `tests/test_comment_backdrop_contracts.py` as regression anchors and may update them to add broader open/close, non-persistence, and final integration assertions.
- Keep any context-menu text short and user-facing; avoid feature-explanation text in the UI.
