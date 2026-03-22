# COMMENT_BACKDROP P07: Clipboard + Delete + Load Recompute

## Objective
- Lock the expanded versus collapsed clipboard and delete semantics and recompute ownership after paste and load without persisting backdrop membership state.

## Preconditions
- `P06` is marked `PASS` in [COMMENT_BACKDROP_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_STATUS.md).
- No later `COMMENT_BACKDROP` packet is in progress.

## Execution Dependencies
- `P06`

## Target Subsystems
- `ea_node_editor/ui/shell/runtime_clipboard.py`
- `ea_node_editor/graph/transforms.py`
- `ea_node_editor/ui/shell/controllers/workspace_edit_ops.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/persistence/project_codec.py`
- `tests/test_comment_backdrop_clipboard.py`
- `tests/main_window_shell/edit_clipboard_history.py`
- `tests/test_serializer.py`

## Conservative Write Scope
- `ea_node_editor/ui/shell/runtime_clipboard.py`
- `ea_node_editor/graph/transforms.py`
- `ea_node_editor/ui/shell/controllers/workspace_edit_ops.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/persistence/project_codec.py`
- `tests/test_comment_backdrop_clipboard.py`
- `tests/main_window_shell/edit_clipboard_history.py`
- `tests/test_serializer.py`
- `docs/specs/work_packets/comment_backdrop/P07_clipboard_delete_load_recompute_WRAPUP.md`

## Required Behavior
- Expanded backdrop copy and delete must affect only explicitly selected items; descendant items participate only when they are explicitly selected too.
- Collapsed backdrop copy and delete must implicitly include descendant backdrops, descendant nodes, and fully internal edges based on the ownership and collapse rules already established by `P03` through `P05`.
- Paste, duplicate, and project load must recompute backdrop ownership from geometry and collapse state instead of trusting persisted member ids.
- Serializer and fragment workflows must remain schema-compatible by storing only backdrop node geometry and ordinary graph data, not packet-owned membership metadata.
- Existing regular-node and subnode clipboard semantics must remain intact outside the new backdrop-specific rules.

## Non-Goals
- No docs or traceability updates yet. `P08` owns closeout.
- No new creation affordance beyond the `P06` shell paths.
- No alternate persistence format or backdrop-only document storage.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_comment_backdrop_clipboard.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/main_window_shell/edit_clipboard_history.py --ignore=venv -k "comment_backdrop" -q`
3. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_serializer.py --ignore=venv -k "comment_backdrop" -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_comment_backdrop_clipboard.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/comment_backdrop/P07_clipboard_delete_load_recompute_WRAPUP.md`

## Acceptance Criteria
- Expanded versus collapsed clipboard and delete behavior matches the locked semantics from the manifest.
- Paste, duplicate, and load recompute ownership from geometry without persisting member lists.
- Serializer and fragment regressions confirm backdrop nodes remain on the ordinary graph document path.
- Existing non-backdrop clipboard flows remain stable.

## Handoff Notes
- `P08` should cite the exact accepted clipboard and delete semantics from the wrap-up when updating requirements and traceability.
- Record any packet-owned fragment or duplicate helper introduced here so later work does not create a second recompute entry point.
