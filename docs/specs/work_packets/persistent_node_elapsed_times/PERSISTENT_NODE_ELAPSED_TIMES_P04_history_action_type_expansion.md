# PERSISTENT_NODE_ELAPSED_TIMES P04: History Action Type Expansion

## Objective
- Expand coarse history action types into a taxonomy that distinguishes execution-affecting edits from cosmetic/layout edits before any centralized elapsed-cache invalidation consumes those action labels.

## Preconditions
- `P03` is marked `PASS` in [PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md](./PERSISTENT_NODE_ELAPSED_TIMES_STATUS.md).
- No later `PERSISTENT_NODE_ELAPSED_TIMES` packet is in progress.

## Execution Dependencies
- `P03`

## Target Subsystems
- `ea_node_editor/ui/shell/runtime_history.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/selection_and_scope_ops.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/alignment_and_distribution_ops.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/grouping_and_subnode_ops.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/clipboard_and_fragment_ops.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/comment_backdrop_ops.py`
- `tests/graph_track_b/runtime_history.py`
- `tests/graph_track_b/scene_model_graph_scene_suite.py`

## Conservative Write Scope
- `ea_node_editor/ui/shell/runtime_history.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/selection_and_scope_ops.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/alignment_and_distribution_ops.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/grouping_and_subnode_ops.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/clipboard_and_fragment_ops.py`
- `ea_node_editor/ui_qml/graph_scene_mutation/comment_backdrop_ops.py`
- `tests/graph_track_b/runtime_history.py`
- `tests/graph_track_b/scene_model_graph_scene_suite.py`
- `docs/specs/work_packets/persistent_node_elapsed_times/P04_history_action_type_expansion_WRAPUP.md`

## Required Behavior
- Expand the packet-owned history action constants so executable node property edits are distinguishable from cosmetic edits such as rename/title-only changes, node style edits, edge style edits, edge-label edits, and port-label edits.
- Keep add/remove, move, resize, collapse, exposed-port, duplicate/paste, group/ungroup, and comment/backdrop flows distinguishable enough for a later invalidation classifier to consume conservatively.
- Update graph-scene mutation call sites to emit the new packet-owned action types without changing the underlying workspace mutation semantics.
- Preserve existing undo/redo snapshot behavior; this packet changes the action taxonomy only, not yet the invalidation side effects.
- Add packet-owned regression tests whose names include `persistent_node_elapsed_action_types` so the targeted verification commands below remain stable.

## Non-Goals
- No centralized elapsed-cache invalidation behavior yet.
- No project/session clearing changes; those remain owned by `P02`.
- No bridge, footer, or docs refresh changes.

## Verification Commands
1. `.\venv\Scripts\python.exe -m pytest tests/graph_track_b/runtime_history.py tests/graph_track_b/scene_model_graph_scene_suite.py -k persistent_node_elapsed_action_types --ignore=venv -q`

## Review Gate
- `.\venv\Scripts\python.exe -m pytest tests/graph_track_b/runtime_history.py -k persistent_node_elapsed_action_types --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/persistent_node_elapsed_times/P04_history_action_type_expansion_WRAPUP.md`

## Acceptance Criteria
- History action types are granular enough to distinguish execution-affecting versus cosmetic/layout edits at the packet-owned mutation boundaries.
- Mutation call sites emit the new action taxonomy without regressing undo/redo snapshot behavior.
- The packet-owned `persistent_node_elapsed_action_types` regressions pass.

## Handoff Notes
- `P05` consumes the action taxonomy established here and should not silently collapse it back into coarse generic labels.
- Any later packet that changes which action type a mutation emits must inherit and update the packet-owned regression anchors in this packet's scope.
