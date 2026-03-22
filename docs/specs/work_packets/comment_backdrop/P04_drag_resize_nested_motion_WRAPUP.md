# P04 Drag/Resize + Nested Motion Wrap-Up

## Implementation Summary

- Packet: `P04`
- Branch Label: `codex/comment-backdrop/p04-drag-resize-nested-motion`
- Commit Owner: `worker`
- Commit SHA: `686619882a9a917f7e267075758a9e8474f264b1`
- Changed Files: `docs/specs/work_packets/comment_backdrop/P04_drag_resize_nested_motion_WRAPUP.md`, `ea_node_editor/ui_qml/components/GraphCanvas.qml`, `tests/main_window_shell/comment_backdrop_workflows.py`, `tests/test_comment_backdrop_interactions.py`
- Artifacts Produced: `docs/specs/work_packets/comment_backdrop/P04_drag_resize_nested_motion_WRAPUP.md`, `ea_node_editor/ui_qml/components/GraphCanvas.qml`, `tests/main_window_shell/comment_backdrop_workflows.py`, `tests/test_comment_backdrop_interactions.py`
- History Grouping Entry Point: `GraphSceneBridge.move_nodes_by_delta(node_ids, dx, dy)` delegates to `GraphSceneMutationHistory.move_nodes_by_delta(...)`, which wraps descendant translation inside `_scene_context.grouped_history_action(ACTION_MOVE_NODE, workspace)`
- Backdrop Drag Expansion: `GraphCanvas.dragNodeIdsForAnchor(nodeId)` now reuses `member_node_ids` plus `member_backdrop_ids` recursively from the `P03` payload contract so backdrop drag preview and commit include descendant trees exactly once

## Verification

- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_comment_backdrop_interactions.py --ignore=venv -q`
- PASS: `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/main_window_shell/comment_backdrop_workflows.py --ignore=venv -k "drag or resize" -q`
- Final Verification Verdict: `PASS`

## Manual Test Directives

Too soon for manual testing.

- Blocker: `P04` makes drag and resize behavior work once comment backdrops already exist, but `P06` still owns the stable shell affordances for creating those backdrops (`C` wrap-selection, library placement, and related user entry points).
- Blocker: there is no packet-owned fixture-loading or creation workflow in the current shell that lets a manual tester reliably author nested backdrops without using internal APIs.
- Next worthwhile milestone: manual smoke testing becomes high-signal once `P06` lands a user-facing creation path or a dedicated sample workspace with nested backdrops is available for exercising drag, resize, and undo/redo from the visible shell.

## Residual Risks

- The packet tests validate the delegate `dragFinished` and `resizeFinished` commit path directly because offscreen Qt event synthesis did not reliably trigger `MouseArea.drag` in this harness; once a stable manual setup exists, a real pointer-path smoke test should confirm there is no gap between emitted host signals and live pointer gestures.
- Backdrop drag expansion currently lives in `GraphCanvas.qml`, so later packets that need descendant sets should continue reusing `dragNodeIdsForAnchor(...)` or the grouped `move_nodes_by_delta(...)` bridge path instead of recomputing containment from raw geometry.

## Ready for Integration

- Yes: backdrop drag now expands across nested descendant trees without altering ordinary node drag semantics, and the packet verification proves grouped undo/redo plus resize-driven membership recompute inside the owned shell and canvas seams.
