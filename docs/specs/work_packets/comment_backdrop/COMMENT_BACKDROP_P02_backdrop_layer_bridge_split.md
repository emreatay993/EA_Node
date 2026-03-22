# COMMENT_BACKDROP P02: Backdrop Layer + Bridge Split

## Objective
- Split comment backdrops into a dedicated scene and canvas payload path that renders below edges and regular nodes while keeping the regular node path unchanged for all other families.

## Preconditions
- `P01` is marked `PASS` in [COMMENT_BACKDROP_STATUS.md](/mnt/c/Users/emre_/PycharmProjects/EA_Node_Editor/docs/specs/work_packets/comment_backdrop/COMMENT_BACKDROP_STATUS.md).
- No later `COMMENT_BACKDROP` packet is in progress.

## Execution Dependencies
- `P01`

## Target Subsystems
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/GraphCommentBackdrop*.qml`
- `tests/test_comment_backdrop_layer.py`
- `tests/main_window_shell/bridge_contracts.py`

## Conservative Write Scope
- `ea_node_editor/ui_qml/graph_scene_payload_builder.py`
- `ea_node_editor/ui_qml/graph_scene_bridge.py`
- `ea_node_editor/ui_qml/graph_canvas_bridge.py`
- `ea_node_editor/ui_qml/components/GraphCanvas.qml`
- `ea_node_editor/ui_qml/components/graph/GraphCommentBackdrop*.qml`
- `tests/test_comment_backdrop_layer.py`
- `tests/main_window_shell/bridge_contracts.py`
- `docs/specs/work_packets/comment_backdrop/P02_backdrop_layer_bridge_split_WRAPUP.md`

## Required Behavior
- Publish a dedicated backdrop payload model from the scene builder and bridge surfaces instead of leaving backdrop instances mixed into the regular node model.
- Add a dedicated backdrop canvas layer or repeater beneath `graphCanvasEdgeLayer` and the regular node repeater.
- Ensure the new backdrop layer continues to support selection, context-menu routing, drag-start, drag-finish, resize, and inline title interaction through the existing host contracts or packet-owned packet-local adapters.
- Keep all non-backdrop nodes, existing annotation cards, edge rendering, and current public canvas object names stable.
- Make the split authoritative: once this packet lands, comment backdrops must no longer render through the regular node repeater.

## Non-Goals
- No geometry-owned membership or wrap-selection transaction yet. `P03` owns ownership semantics.
- No descendant motion yet. `P04` owns backdrop drag and resize propagation.
- No collapse hiding or boundary-edge rerouting yet. `P05` owns those behaviors.

## Verification Commands
1. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_comment_backdrop_layer.py --ignore=venv -q`
2. `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/main_window_shell/bridge_contracts.py --ignore=venv -k "comment_backdrop or backdrop" -q`

## Review Gate
- `QT_QPA_PLATFORM=offscreen ./venv/Scripts/python.exe -m pytest tests/test_comment_backdrop_layer.py --ignore=venv -q`

## Expected Artifacts
- `docs/specs/work_packets/comment_backdrop/P02_backdrop_layer_bridge_split_WRAPUP.md`

## Acceptance Criteria
- Comment backdrops render on a dedicated under-edge layer while regular nodes stay on the existing node layer.
- The regular node payload no longer duplicates comment backdrop instances after the split.
- Canvas and bridge discoverability contracts remain stable for non-backdrop consumers.
- Targeted bridge and canvas regressions confirm the dedicated backdrop layer is active and interactive.

## Handoff Notes
- `P03` may assume a dedicated backdrop payload model already exists and must reuse it rather than reintroducing regular-node special cases.
- Record any new bridge property or object name in the wrap-up so later packets reuse the same surface.
